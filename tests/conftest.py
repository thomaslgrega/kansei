import httpx
import pytest

from kansei import JobPosting


@pytest.fixture
def make_posting():
    def build(title: str = "Software Engineer", location: str = "Tokyo, Japan", **overrides) -> JobPosting:
        return JobPosting(**{
            "source": "greenhouse",
            "token": "stripe",
            "id": "1",
            "title": title,
            "url": "https://example.com/1",
            "posted_at": "2026-09-19T00:00:00Z",
            "location": location,
            **overrides,
        })

    return build


@pytest.fixture
def make_board():
    def build(content: str = "We need a Python engineer in Tokyo.") -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"content": content})
        ))

    return build