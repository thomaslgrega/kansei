import html
import httpx

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
        "description": raw["descriptionPlain"],
    }


async def fetch_posting(client: httpx.AsyncClient, token: str, job_id: str) -> str:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{job_id}"
    response = await client.get(url)
    response.raise_for_status()
    return html.unescape(response.json()["content"])


async def fetch_greenhouse(client: httpx.AsyncClient, token: str) -> list[dict]:
    response = await client.get(GREENHOUSE_BOARD.format(token=token))
    response.raise_for_status()
    return [from_greenhouse(raw, token) for raw in response.json()["jobs"]]


async def fetch_lever(client: httpx.AsyncClient, token: str) -> list[dict]:
    response = await client.get(LEVER_BOARD.format(token=token))
    response.raise_for_status()
    return [from_lever(raw, token) for raw in response.json()]


SOURCES = {"greenhouse": fetch_greenhouse, "lever": fetch_lever}
