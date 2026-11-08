import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kansei import JobPosting
from kansei.api import app, get_http
from kansei.db import engine, get_session


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


@pytest.fixture
def session():
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


class FakeAts:
    def __init__(self) -> None:
        self.pages: dict[str, httpx.Response] = {}
        self.requested: list[str] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requested.append(str(request.url))
        return self.pages.get(str(request.url), httpx.Response(404))


@pytest.fixture
def ats():
    return FakeAts()


@pytest.fixture
def client(session, ats):
    async def fake_http():
        async with httpx.AsyncClient(transport=httpx.MockTransport(ats.handle)) as http:
            yield http

    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_http] = fake_http
    yield TestClient(app, base_url="https://testserver")
    app.dependency_overrides = {}


@pytest.fixture
def log_in_as(client):
    def log_in(email: str) -> None:
        credentials = {"email": email, "password": "correct password"}
        response = client.post("/api/signup", json=credentials)
        assert response.status_code == 201, response.text
        response = client.post("/api/login", json=credentials)
        assert response.status_code == 204, response.text

    return log_in
