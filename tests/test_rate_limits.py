from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from kansei.api import app
from kansei.db import RateLimit
from kansei.ratelimit import utcnow

PASSWORD = "correct password"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 10, 9, 0, 5, tzinfo=UTC)

    def advance(self, by: timedelta) -> None:
        self.now += by


@pytest.fixture
def clock(client):
    clock = Clock()
    app.dependency_overrides[utcnow] = lambda: clock.now
    return clock


def log_in(client, email: str = "ada@example.com", ip: str | None = None) -> int:
    headers = {"X-Forwarded-For": ip} if ip else {}
    return client.post("/api/login", json={"email": email, "password": PASSWORD}, headers=headers).status_code


def test_the_11th_login_within_a_minute_from_one_ip_is_429(client, clock):
    codes = [log_in(client, f"user{n}@example.com") for n in range(11)]

    assert codes == [401] * 10 + [429]


def test_a_forged_leftmost_forwarded_for_entry_is_ignored(client, clock):
    codes = [log_in(client, f"user{n}@example.com", ip=f"198.51.100.{n}, 203.0.113.7") for n in range(11)]

    assert codes == [401] * 10 + [429]


def test_a_forged_forwarded_for_header_line_before_the_front_ends_is_ignored(client, clock):
    codes = [
        client.post(
            "/api/login",
            json={"email": f"user{n}@example.com", "password": PASSWORD},
            headers=[("X-Forwarded-For", f"198.51.100.{n}"), ("X-Forwarded-For", "203.0.113.7")],
        ).status_code
        for n in range(11)
    ]

    assert codes == [401] * 10 + [429]


def test_without_forwarded_for_the_socket_address_is_counted(client, clock):
    codes = [log_in(client, f"user{n}@example.com") for n in range(10)]
    codes.append(log_in(client, "other@example.com", ip="203.0.113.7"))
    codes.append(log_in(client, "last@example.com"))

    assert codes == [401] * 10 + [401, 429]


def test_the_11th_login_within_an_hour_for_one_email_from_different_ips_is_429(client, clock):
    codes = []
    for n in range(11):
        codes.append(log_in(client, "Ada@example.com" if n % 2 else "ada@example.com", ip=f"203.0.113.{n}"))
        clock.advance(timedelta(minutes=5))

    assert codes == [401] * 10 + [429]


def test_login_counts_reset_when_the_minute_ends(client, clock):
    codes = [log_in(client, f"user{n}@example.com") for n in range(11)]
    clock.advance(timedelta(seconds=54))
    codes.append(log_in(client, "late@example.com"))
    clock.advance(timedelta(seconds=1))
    codes.append(log_in(client, "next@example.com"))

    assert codes == [401] * 10 + [429, 429, 401]


def test_ended_windows_are_deleted(client, clock, session):
    log_in(client, "ada@example.com")
    clock.advance(timedelta(minutes=59, seconds=55))
    log_in(client, "grace@example.com")

    windows = session.execute(select(RateLimit.key, RateLimit.ends_at).order_by(RateLimit.key)).all()
    assert windows == [
        ("login-email:grace@example.com", datetime(2026, 11, 10, 11, 0, tzinfo=UTC)),
        ("login-ip:testclient", datetime(2026, 11, 10, 10, 1, tzinfo=UTC)),
    ]


def sign_up(client, email: str) -> int:
    return client.post("/api/signup", json={"email": email, "password": PASSWORD}).status_code


def test_the_6th_signup_within_an_hour_from_one_ip_is_429(client, clock):
    codes = []
    for n in range(6):
        codes.append(sign_up(client, f"user{n}@example.com"))
        clock.advance(timedelta(minutes=10))

    assert codes == [201] * 5 + [429]


def test_the_31st_probe_within_a_minute_for_one_user_is_429(client, clock, log_in_as):
    log_in_as("ada@example.com")

    codes = [client.get("/api/probe", params={"q": "https://example.com/careers"}).status_code for _ in range(31)]

    assert codes == [200] * 30 + [429]
