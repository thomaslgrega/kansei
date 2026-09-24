import html
import json
from html.parser import HTMLParser
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup


class TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in {"br", "p", "div", "li", "tr"}:
            self.parts.append("\n")


def html_to_text(fragment: str) -> str:
    parser = TextOnly()
    parser.feed(fragment)
    lines = (line.strip() for line in "".join(parser.parts).splitlines())
    return "\n".join(line for line in lines if line)


def page_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def job_posting_ld(soup: BeautifulSoup) -> dict:
    for block in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(block.get_text())
        except json.JSONDecodeError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else data
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "JobPosting":
                return node
    return {}
            

def lever_text(raw: dict) -> str:
    parts = [raw["descriptionPlain"]]
    for section in raw.get("lists", []):
        parts.append(section.get("text", ""))
        parts.append(html_to_text(section.get("content", "")))
    parts.append(raw.get("additionalPlain", ""))
    return "\n\n".join(part for part in parts if part)


GREENHOUSE_BOARD = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
GREENHOUSE_JOB = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"
LEVER_BOARD = "https://api.lever.co/v0/postings/{token}?mode=json"


def from_greenhouse(raw: dict, token: str) -> dict:
    return {
        "source": "greenhouse",
        "token": token,
        "id": str(raw["id"]),
        "title": raw["title"],
        "url": raw["absolute_url"],
        "posted_at": raw["updated_at"],
        "location": raw["location"]["name"],
        "description": None,
    }


def from_lever(raw: dict, token: str) -> dict:
    return {
        "source": "lever",
        "token": token,
        "id": raw["id"],
        "title": raw["text"],
        "url": raw["hostedUrl"],
        "posted_at": raw["createdAt"],
        "location": raw["categories"]["location"],
        "description": lever_text(raw),
    }


def from_url(page: str, url: str) -> dict:
    soup = BeautifulSoup(page, "html.parser")
    posting = job_posting_ld(soup)
    address = (posting.get("jobLocation") or {}).get("address") or {}
    heading = soup.h1 or soup.title
    return {
        "source": "url",
        "token": urlsplit(url).netloc,
        "id": url,
        "title": posting.get("title") or (heading.get_text(strip=True) if heading else ""),
        "url": url,
        "posted_at": posting.get("datePosted"),
        "location": address.get("addressLocality") or address.get("addressCountry") or "",
        "description": page_text(soup)
    }


async def fetch_posting(client: httpx.AsyncClient, token: str, job_id: str) -> str:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"
    response = await client.get(url)
    response.raise_for_status()
    return html_to_text(html.unescape(response.json()["content"]))


async def fetch_greenhouse(client: httpx.AsyncClient, token: str) -> list[dict]:
    response = await client.get(GREENHOUSE_BOARD.format(token=token))
    response.raise_for_status()
    return [from_greenhouse(raw, token) for raw in response.json()["jobs"]]


async def fetch_lever(client: httpx.AsyncClient, token: str) -> list[dict]:
    response = await client.get(LEVER_BOARD.format(token=token))
    response.raise_for_status()
    return [from_lever(raw, token) for raw in response.json()]


async def fetch_url(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type")
    if "text/html" not in content_type:
        raise ValueError(f"{url} returned {content_type or 'no content type'}, not HTML")
    return from_url(response.text, url)


SOURCES = {"greenhouse": fetch_greenhouse, "lever": fetch_lever}
