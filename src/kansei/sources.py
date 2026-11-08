import html
import json
import re
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


def hiring_organization_name(posting: dict) -> str | None:
    organization = posting.get("hiringOrganization")
    name = organization.get("name") if isinstance(organization, dict) else None
    if not isinstance(name, str):
        return None
    return name.strip() or None


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
GREENHOUSE_BOARD_INFO = "https://boards-api.greenhouse.io/v1/boards/{token}"
LEVER_BOARD_PAGE = "https://jobs.lever.co/{token}"
ASHBY_BOARD = "https://api.ashbyhq.com/posting-api/job-board/{token}"
ASHBY_GRAPHQL = "https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiOrganizationFromHostedJobsPageName"
ASHBY_ORGANIZATION_QUERY = """
query ApiOrganizationFromHostedJobsPageName(
  $organizationHostedJobsPageName: String!, $searchContext: OrganizationSearchContext
) {
  organization: organizationFromHostedJobsPageName(
    organizationHostedJobsPageName: $organizationHostedJobsPageName,
    searchContext: $searchContext
  ) { name }
}
"""


def from_greenhouse(raw: dict, token: str) -> dict:
    return {
        "source": "greenhouse",
        "token": token,
        "id": str(raw["id"]),
        "title": raw["title"],
        "url": raw["absolute_url"],
        "posted_at": raw["updated_at"],
        "location": raw["location"]["name"],
        "company_name": None,
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
        "company_name": None,
        "description": lever_text(raw),
    }


def from_ashby(raw: dict, token: str) -> dict:
    locations = [raw["location"], *(secondary["location"] for secondary in raw["secondaryLocations"])]
    return {
        "source": "ashby",
        "token": token,
        "id": raw["id"],
        "title": raw["title"],
        "url": raw["jobUrl"],
        "posted_at": raw["publishedAt"],
        "location": " / ".join(locations),
        "company_name": None,
        "description": raw["descriptionPlain"],
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
        "company_name": hiring_organization_name(posting),
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


async def fetch_ashby(client: httpx.AsyncClient, token: str) -> list[dict]:
    response = await client.get(ASHBY_BOARD.format(token=token))
    response.raise_for_status()
    return [from_ashby(raw, token) for raw in response.json()["jobs"]]


async def fetch_url(client: httpx.AsyncClient, url: str) -> dict:
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    if response.url.path != httpx.URL(url).path:
        raise ValueError(f"{url} redirected to {response.url}")
    if "text/html" not in content_type:
        raise ValueError(f"{url} returned {content_type or 'no content type'}, not HTML")
    return from_url(response.text, url)


async def greenhouse_name(client: httpx.AsyncClient, token: str) -> str:
    response = await client.get(GREENHOUSE_BOARD_INFO.format(token=token))
    response.raise_for_status()
    board = response.json()
    name = board.get("name") if isinstance(board, dict) else None
    return name if isinstance(name, str) else ""


async def lever_name(client: httpx.AsyncClient, token: str) -> str:
    response = await client.get(LEVER_BOARD_PAGE.format(token=token))
    response.raise_for_status()
    title = BeautifulSoup(response.text, "html.parser").title
    return title.get_text() if title else ""


async def ashby_name(client: httpx.AsyncClient, token: str) -> str:
    response = await client.post(ASHBY_GRAPHQL, json={
        "operationName": "ApiOrganizationFromHostedJobsPageName",
        "variables": {"organizationHostedJobsPageName": token, "searchContext": "JobBoard"},
        "query": ASHBY_ORGANIZATION_QUERY,
    })
    response.raise_for_status()
    body = response.json()
    data = body.get("data") if isinstance(body, dict) else None
    organization = data.get("organization") if isinstance(data, dict) else None
    name = organization.get("name") if isinstance(organization, dict) else None
    return name if isinstance(name, str) else ""


async def fetch_board_name(client: httpx.AsyncClient, source: str, token: str) -> str | None:
    try:
        name = await NAMES[source](client, token)
    except (httpx.HTTPError, ValueError):
        return None
    return name.strip() or None


SOURCES = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby}
NAMES = {"greenhouse": greenhouse_name, "lever": lever_name, "ashby": ashby_name}

BOARD_HOSTS = {
    "boards.greenhouse.io": "greenhouse",
    "job-boards.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "jobs.ashbyhq.com": "ashby",
}
# Starts with a letter or digit, so `.` and `..` can't walk up the ATS's API paths.
SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")


class NotABoard(ValueError):
    pass


def parse_board_url(url: str) -> tuple[str, str]:
    url = url.strip()
    parts = urlsplit(url if "://" in url else f"https://{url}")
    source = BOARD_HOSTS.get((parts.hostname or "").lower())
    if source is None:
        raise NotABoard(
            "kansei can only add boards on boards.greenhouse.io, job-boards.greenhouse.io, "
            "jobs.lever.co and jobs.ashbyhq.com."
        )
    token = parts.path.split("/")[1] if parts.path.startswith("/") else ""
    if not SLUG.fullmatch(token):
        raise NotABoard("That URL doesn't name a board.")
    return source, token
