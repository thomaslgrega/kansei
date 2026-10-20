import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from kansei import JobPosting
from kansei.api import app
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


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
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
