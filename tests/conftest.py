import httpx
import pytest

from kansei import JobPosting


@pytest.fixture
def make_posting():
    def build(title: str = "Software Engineer", location: str = "Tokyo, Japan") -> JobPosting:
        return JobPosting(
            id=1,
            title=title,
            absolute_url="https://example.com/1",
            updated_at="2026-09-19T00:00:00Z",
            location={"name": location},
        )

    return build


@pytest.fixture
def make_board():
    def build(content: str = "We need a Python engineer in Tokyo.") -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"content": content})
        ))

    return build