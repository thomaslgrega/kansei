from datetime import UTC, datetime

from kansei import sha256
from kansei.auth import COOKIE, password_hash
from kansei.db import User, UserSession

EMAIL = "ada@example.com"
PASSWORD = "correct password"

def sign_up(client, email: str = EMAIL) -> None:
    response = client.post("/api/signup", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201, response.text


def log_in(client) -> str:
    response = client.post("/api/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 204, response.text
    return client.cookies[COOKIE]


def test_me_without_a_cookie_is_401(client):
    response = client.get("/api/me")

    assert response.status_code == 401


def test_wrong_password_is_401_and_sets_no_cookie(client):
    sign_up(client)

    response = client.post("/api/login", json={"email": EMAIL, "password": "wrong password"})

    assert response.status_code == 401
    assert COOKIE not in client.cookies


def test_me_returns_the_logged_in_user_not_another(client):
    sign_up(client, "someone.else@example.com")
    sign_up(client)
    log_in(client)

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_the_login_cookie_is_httponly_secure_and_lax(client):
    sign_up(client)

    response = client.post("/api/login", json={"email": EMAIL, "password": PASSWORD})

    attributes = {part.strip() for part in response.headers["set-cookie"].split(";")}
    assert {"HttpOnly", "Secure", "SameSite=lax"} <= attributes


def test_a_logged_out_token_is_rejected(client):
    sign_up(client)
    token = log_in(client)
    client.post("/api/logout")

    client.cookies.set(COOKIE, token)
    response = client.get("/api/me")

    assert response.status_code == 401


def test_an_expired_session_is_rejected(client, session):
    user = User(email=EMAIL, password_hash=password_hash.hash(PASSWORD))
    session.add(user)
    session.flush()
    session.add(UserSession(id=sha256("old-token"), user_id=user.id, expires_at=datetime(2026, 1, 1, tzinfo=UTC)))

    client.cookies.set(COOKIE, "old-token")
    response = client.get("/api/me")

    assert response.status_code == 401


def test_the_database_stores_only_a_hash_of_the_token(client, session):
    sign_up(client)
    token = log_in(client)

    assert session.get(UserSession, sha256(token)) is not None
    assert session.get(UserSession, token) is None
