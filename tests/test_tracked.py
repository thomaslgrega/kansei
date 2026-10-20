from datetime import UTC, datetime
from typing import get_args

import pytest

from kansei import save_postings
from kansei.db import Tracked, TrackStatus, User

SEEN_AT = datetime(2026, 10, 18, tzinfo=UTC)


@pytest.fixture
def posting_ids(session, make_posting):
    urls = [f"https://example.com/{n}" for n in range(1, 4)]
    ids = save_postings(session, [make_posting(id=url, url=url) for url in urls], SEEN_AT)
    return [ids[url] for url in urls]


def test_tracked_without_a_cookie_is_401(client):
    response = client.get("/api/me/tracked")

    assert response.status_code == 401


def test_tracking_a_posting_that_doesnt_exist_is_404(client, log_in_as):
    log_in_as("ada@example.com")

    response = client.post("/api/me/tracked", json={"posting_id": 0})

    assert response.status_code == 404


def test_tracking_the_same_posting_twice_is_409(client, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})

    response = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})

    assert response.status_code == 409


def test_a_user_sees_only_their_own_tracked_postings_newest_first(client, log_in_as, posting_ids):
    log_in_as("bob@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})
    log_in_as("ada@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_ids[1]})
    client.post("/api/me/tracked", json={"posting_id": posting_ids[2]})

    response = client.get("/api/me/tracked")

    assert [row["posting"]["id"] for row in response.json()] == [posting_ids[2], posting_ids[1]]


def test_another_users_tracked_posting_looks_like_one_that_doesnt_exist(client, session, log_in_as, posting_ids):
    log_in_as("bob@example.com")
    bobs = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]}).json()["id"]
    log_in_as("ada@example.com")

    response = client.patch(f"/api/me/tracked/{bobs}", json={"status": "rejected"})
    missing = client.patch("/api/me/tracked/0", json={"status": "rejected"})

    assert response.status_code == 404
    assert response.json() == missing.json()
    assert session.get(Tracked, bobs).status == "saved"


def test_patch_changes_only_the_fields_it_sends(client, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    tracked = client.post("/api/me/tracked", json={"posting_id": posting_ids[0], "note": "Recruiter reached out"}).json()

    response = client.patch(f"/api/me/tracked/{tracked['id']}", json={"status": "applied"})

    assert response.json()["status"] == "applied"
    assert response.json()["note"] == "Recruiter reached out"


@pytest.mark.parametrize("status", get_args(TrackStatus))
def test_the_database_accepts_every_status_the_api_does(session, posting_ids, status):
    user = User(email="ada@example.com", password_hash="not a real hash")
    session.add(user)
    session.flush()
    session.add(Tracked(user_id=user.id, posting_id=posting_ids[0], status=status, note=""))
    session.flush()


def test_a_user_cant_delete_another_users_tracked_posting(client, session, log_in_as, posting_ids):
    log_in_as("bob@example.com")
    bobs = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]}).json()["id"]
    log_in_as("ada@example.com")

    response = client.delete(f"/api/me/tracked/{bobs}")

    assert response.status_code == 404
    assert session.get(Tracked, bobs) is not None


def test_deleting_your_tracked_posting_is_204_with_no_body(client, session, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    tracked = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]}).json()["id"]

    response = client.delete(f"/api/me/tracked/{tracked}")

    assert response.status_code == 204
    assert response.content == b""
    assert session.get(Tracked, tracked) is None
