from datetime import UTC, datetime, timedelta
from typing import get_args

import pytest
from conftest import Clock
from sqlalchemy.exc import IntegrityError
from test_api import FACTS, make_extraction

from kansei import save_postings
from kansei.db import Stage, Tracked, User

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


def test_a_tracked_posting_kansei_hasnt_seen_for_two_days_is_no_longer_listed(client, session, log_in_as, make_posting):
    now = datetime.now(UTC)
    seen_at = [now, now - timedelta(days=2) + timedelta(minutes=1), now - timedelta(days=2, minutes=1), SEEN_AT]
    urls = [f"https://example.com/{n}" for n in range(len(seen_at))]
    ids = [save_postings(session, [make_posting(id=url, url=url)], when)[url] for url, when in zip(urls, seen_at)]
    log_in_as("ada@example.com")
    for posting_id in ids:
        client.post("/api/me/tracked", json={"posting_id": posting_id})

    response = client.get("/api/me/tracked")

    assert [(row["posting"]["id"], row["posting"]["listed"]) for row in response.json()] == [
        (ids[3], False),
        (ids[2], False),
        (ids[1], True),
        (ids[0], True),
    ]


def test_a_tracked_posting_carries_the_facts_of_its_newest_extraction_under_any_model_or_prompt(
    client, session, log_in_as, posting_ids
):
    session.add_all([
        make_extraction(posting_ids[0], 5, "Current model and prompt."),
        make_extraction(posting_ids[0], 6, "Old prompt.", prompt_sha="70b7a0b0"),
        make_extraction(posting_ids[0], 7, "Other model.", model="gpt-5.6-luna"),
        make_extraction(posting_ids[1], 5, "Current model and prompt."),
        make_extraction(posting_ids[1], 6, "Old prompt.", prompt_sha="70b7a0b0"),
        make_extraction(posting_ids[2], 5, "Untracked posting."),
    ])
    session.flush()
    log_in_as("ada@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})
    client.post("/api/me/tracked", json={"posting_id": posting_ids[1]})

    response = client.get("/api/me/tracked")

    assert [row["facts"] for row in response.json()] == [
        FACTS.model_copy(update={"role_summary": "Old prompt."}).model_dump(mode="json"),
        FACTS.model_copy(update={"role_summary": "Other model."}).model_dump(mode="json"),
    ]


def test_a_tracked_posting_with_no_extraction_has_null_facts(client, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})

    response = client.get("/api/me/tracked")

    assert [row["facts"] for row in response.json()] == [None]


def test_facts_that_dont_fit_the_current_schema_are_null_without_breaking_the_list(
    client, session, log_in_as, posting_ids
):
    old_schema = FACTS.model_dump(mode="json", exclude={"remote_policy"})
    session.add_all([
        make_extraction(posting_ids[0], 5, "Fits."),
        make_extraction(posting_ids[1], 5, "Old schema.", prompt_sha="70b7a0b0", facts=old_schema),
    ])
    session.flush()
    log_in_as("ada@example.com")
    client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})
    client.post("/api/me/tracked", json={"posting_id": posting_ids[1]})

    response = client.get("/api/me/tracked")

    assert [(row["posting"]["id"], row["facts"]) for row in response.json()] == [
        (posting_ids[1], None),
        (posting_ids[0], FACTS.model_copy(update={"role_summary": "Fits."}).model_dump(mode="json")),
    ]


def test_a_tracked_posting_carries_the_japanese_requirement_of_its_facts_or_null_without_them(
    client, session, log_in_as, posting_ids
):
    required = {"japanese_required": "required", "jlpt": "N3"}
    old_schema = FACTS.model_dump(mode="json", exclude={"remote_policy"}) | required
    session.add_all([
        make_extraction(posting_ids[0], 5, "Older.", facts=FACTS.model_dump(mode="json")),
        make_extraction(posting_ids[0], 6, "Newest.", facts=FACTS.model_copy(update=required).model_dump(mode="json")),
        make_extraction(posting_ids[2], 5, "Old schema.", prompt_sha="70b7a0b0", facts=old_schema),
    ])
    session.flush()
    log_in_as("ada@example.com")
    created = [client.post("/api/me/tracked", json={"posting_id": posting_id}).json() for posting_id in posting_ids]

    response = client.get("/api/me/tracked")

    assert [row["japanese_requirement"] for row in created] == ["conversational", None, None]
    assert [(row["posting"]["id"], row["japanese_requirement"]) for row in response.json()] == [
        (posting_ids[2], None),
        (posting_ids[1], None),
        (posting_ids[0], "conversational"),
    ]


def tracked_fields(row: dict) -> dict:
    return {
        "id": row["id"],
        "stage": row["stage"],
        "archived": row["archived"],
        "note": row["note"],
        "tracked_at": datetime.fromisoformat(row["tracked_at"]),
        "moved_at": datetime.fromisoformat(row["moved_at"]),
    }


def test_tracking_starts_at_saved_with_both_dates_now(client, clock, log_in_as, posting_ids):
    log_in_as("ada@example.com")

    response = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})

    assert response.status_code == 201
    assert tracked_fields(response.json()) == {
        "id": response.json()["id"],
        "stage": "saved",
        "archived": False,
        "note": "",
        "tracked_at": clock.now,
        "moved_at": clock.now,
    }


def test_the_list_shows_stage_archived_and_both_dates_moved_newest_first(client, clock, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    tracked_at = []
    ids = []
    for posting_id in posting_ids:
        tracked_at.append(clock.now)
        ids.append(client.post("/api/me/tracked", json={"posting_id": posting_id}).json()["id"])
        clock.advance(timedelta(days=1))
    client.patch(f"/api/me/tracked/{ids[0]}", json={"stage": "applied", "note": "Sent CV"})
    clock.advance(timedelta(days=1))
    client.patch(f"/api/me/tracked/{ids[1]}", json={"archived": True})

    response = client.get("/api/me/tracked")

    assert [tracked_fields(row) for row in response.json()] == [
        {
            "id": ids[1],
            "stage": "saved",
            "archived": True,
            "note": "",
            "tracked_at": tracked_at[1],
            "moved_at": tracked_at[0] + timedelta(days=4),
        },
        {
            "id": ids[0],
            "stage": "applied",
            "archived": False,
            "note": "Sent CV",
            "tracked_at": tracked_at[0],
            "moved_at": tracked_at[0] + timedelta(days=3),
        },
        {
            "id": ids[2],
            "stage": "saved",
            "archived": False,
            "note": "",
            "tracked_at": tracked_at[2],
            "moved_at": tracked_at[2],
        },
    ]


def test_tracked_postings_that_moved_at_the_same_time_list_newest_id_first(client, clock, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    ids = [client.post("/api/me/tracked", json={"posting_id": posting_id}).json()["id"] for posting_id in posting_ids]

    response = client.get("/api/me/tracked")

    assert [row["id"] for row in response.json()] == ids[::-1]


TRACKED, EARLIER, NOW = (Clock().now + timedelta(days=n) for n in range(3))


@pytest.mark.parametrize(("earlier", "patch", "expected"), [
    ([], {"stage": "applied"}, ("applied", False, "", NOW)),
    ([], {"stage": "saved"}, ("saved", False, "", TRACKED)),
    ([], {"note": "Call on Friday"}, ("saved", False, "Call on Friday", TRACKED)),
    ([{"archived": True}], {"note": "Call on Friday"}, ("saved", True, "Call on Friday", EARLIER)),
    ([], {"archived": True}, ("saved", True, "", NOW)),
    ([{"archived": True}], {"archived": False}, ("saved", False, "", NOW)),
    ([{"archived": True}], {"archived": True}, ("saved", True, "", EARLIER)),
    ([], {"archived": False}, ("saved", False, "", TRACKED)),
    ([{"stage": "interviewing", "archived": True}], {"stage": "offer"}, ("offer", False, "", NOW)),
    ([{"stage": "interviewing", "archived": True}], {"stage": "interviewing"}, ("interviewing", False, "", NOW)),
    ([], {"stage": "offer", "archived": True}, ("offer", True, "", NOW)),
    ([{"archived": True}], {"stage": "applied", "archived": True}, ("applied", True, "", NOW)),
], ids=[
    "new stage moves",
    "same stage doesnt move",
    "note alone doesnt move",
    "note alone keeps an archived posting archived",
    "archiving moves",
    "unarchiving moves",
    "archiving an archived posting doesnt move it",
    "unarchiving an unarchived posting doesnt move it",
    "a stage unarchives",
    "the same stage unarchives",
    "a stage with archived true archives at that stage",
    "a stage change on an archived posting with archived true moves it",
])
def test_a_tracked_posting_moves_only_when_its_stage_or_archive_changes(
    client, clock, log_in_as, posting_ids, earlier, patch, expected
):
    log_in_as("ada@example.com")
    clock.now = TRACKED
    tracked = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]}).json()["id"]
    clock.now = EARLIER
    for body in earlier:
        client.patch(f"/api/me/tracked/{tracked}", json=body)
    clock.now = NOW

    response = client.patch(f"/api/me/tracked/{tracked}", json=patch)

    row = tracked_fields(response.json())
    assert (row["stage"], row["archived"], row["note"], row["moved_at"]) == expected
    assert row["tracked_at"] == TRACKED


@pytest.mark.parametrize("method", ["post", "patch"])
def test_rejected_is_no_longer_a_stage(client, log_in_as, posting_ids, method):
    log_in_as("ada@example.com")
    tracked = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]}).json()["id"]

    if method == "post":
        response = client.post("/api/me/tracked", json={"posting_id": posting_ids[1], "stage": "rejected"})
    else:
        response = client.patch(f"/api/me/tracked/{tracked}", json={"stage": "rejected"})

    assert response.status_code == 422
    assert [row["stage"] for row in client.get("/api/me/tracked").json()] == ["saved"]


def test_a_note_holds_2000_characters_and_no_more(client, log_in_as, posting_ids):
    log_in_as("ada@example.com")

    posted = [
        client.post("/api/me/tracked", json={"posting_id": posting_ids[0], "note": "x" * 2001}).status_code,
        client.post("/api/me/tracked", json={"posting_id": posting_ids[0], "note": "x" * 2000}).status_code,
    ]
    tracked = client.get("/api/me/tracked").json()[0]["id"]
    patched = [
        client.patch(f"/api/me/tracked/{tracked}", json={"note": "y" * 2001}).status_code,
        client.patch(f"/api/me/tracked/{tracked}", json={"note": "y" * 2000}).status_code,
    ]

    assert (posted, patched) == ([422, 201], [422, 200])
    assert [row["note"] for row in client.get("/api/me/tracked").json()] == ["y" * 2000]


def test_tracking_a_posting_that_is_no_longer_listed_says_so(client, log_in_as, posting_ids):
    log_in_as("ada@example.com")

    response = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]})

    assert response.json()["posting"]["listed"] is False


def test_another_users_tracked_posting_looks_like_one_that_doesnt_exist(client, session, log_in_as, posting_ids):
    log_in_as("bob@example.com")
    bobs = client.post("/api/me/tracked", json={"posting_id": posting_ids[0]}).json()["id"]
    log_in_as("ada@example.com")

    response = client.patch(f"/api/me/tracked/{bobs}", json={"stage": "applied"})
    missing = client.patch("/api/me/tracked/0", json={"stage": "applied"})

    assert response.status_code == 404
    assert response.json() == missing.json()
    assert session.get(Tracked, bobs).stage == "saved"


def test_patch_changes_only_the_fields_it_sends(client, log_in_as, posting_ids):
    log_in_as("ada@example.com")
    tracked = client.post("/api/me/tracked", json={"posting_id": posting_ids[0], "note": "Recruiter reached out"}).json()

    response = client.patch(f"/api/me/tracked/{tracked['id']}", json={"stage": "applied"})

    assert response.json()["stage"] == "applied"
    assert response.json()["note"] == "Recruiter reached out"


@pytest.mark.parametrize("stage", get_args(Stage))
def test_the_database_accepts_every_stage_the_api_does(session, posting_ids, stage):
    user = User(email="ada@example.com", password_hash="not a real hash")
    session.add(user)
    session.flush()
    session.add(Tracked(user_id=user.id, posting_id=posting_ids[0], stage=stage, note="", moved_at=SEEN_AT))
    session.flush()


def test_the_database_refuses_the_old_rejected_stage(session, posting_ids):
    user = User(email="ada@example.com", password_hash="not a real hash")
    session.add(user)
    session.flush()
    session.add(Tracked(user_id=user.id, posting_id=posting_ids[0], stage="rejected", note="", moved_at=SEEN_AT))

    with pytest.raises(IntegrityError):
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
