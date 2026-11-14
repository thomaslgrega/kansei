from datetime import UTC, datetime, timedelta

import pytest
from test_api import FACTS, make_extraction

from kansei import save_postings
from kansei.db import Board


@pytest.fixture
def boards(session):
    session.add_all([
        Board(source="greenhouse", token="kansei-test", name="Kansei Test K.K."),
        Board(source="lever", token="kansei-unnamed"),
    ])
    session.flush()


def test_following_a_board_twice_leaves_one_follow(client, log_in_as, boards):
    log_in_as("ada@example.com")

    first = client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    second = client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json() == {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None}
    assert client.get("/api/me/follows").json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None},
    ]


def test_following_a_removed_board_is_409_and_follows_nothing(client, session, log_in_as, boards):
    session.add(Board(source="ashby", token="kansei-removed", status="removed"))
    session.flush()
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "ashby", "token": "kansei-removed"})

    assert response.status_code == 409
    assert response.json() == {"detail": "This company was removed from kansei and can't be added."}
    assert client.get("/api/me/follows").json() == []


def test_unfollowing_removes_only_that_follow(client, log_in_as, boards):
    log_in_as("bob@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    log_in_as("ada@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    client.post("/api/me/follows", json={"source": "lever", "token": "kansei-unnamed"})

    response = client.delete("/api/me/follows/greenhouse/kansei-test")

    assert response.status_code == 204
    assert client.get("/api/me/follows").json() == [
        {"source": "lever", "token": "kansei-unnamed", "company": "kansei-unnamed", "logo_url": None},
    ]
    client.post("/api/login", json={"email": "bob@example.com", "password": "correct password"})
    assert client.get("/api/me/follows").json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None},
    ]


def test_follows_lists_only_your_boards_by_company_name_even_without_open_candidates(
    client, session, log_in_as, make_posting, boards
):
    session.add(Board(source="greenhouse", token="kansei-other", name="Other Co"))
    closed = make_posting(source="lever", token="kansei-unnamed", url="https://example.com/closed")
    save_postings(session, [closed], datetime.now(UTC) - timedelta(days=3))
    log_in_as("bob@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-other"})
    log_in_as("ada@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    client.post("/api/me/follows", json={"source": "lever", "token": "kansei-unnamed"})

    response = client.get("/api/me/follows")

    assert response.json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None},
        {"source": "lever", "token": "kansei-unnamed", "company": "kansei-unnamed", "logo_url": None},
    ]


def test_follows_give_each_boards_logo_in_company_order_ignoring_case(client, session, log_in_as, boards):
    session.add_all([
        Board(source="ashby", token="kansei-mercari", name="mercari", logo_url="https://example.com/mercari.png"),
        Board(source="hrmos", token="kansei-zeta", name="Zeta"),
    ])
    session.flush()
    log_in_as("ada@example.com")
    for source, token in [("hrmos", "kansei-zeta"), ("greenhouse", "kansei-test"), ("ashby", "kansei-mercari")]:
        client.post("/api/me/follows", json={"source": source, "token": token})

    response = client.get("/api/me/follows")

    assert response.json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K.", "logo_url": None},
        {"source": "ashby", "token": "kansei-mercari", "company": "mercari", "logo_url": "https://example.com/mercari.png"},
        {"source": "hrmos", "token": "kansei-zeta", "company": "Zeta", "logo_url": None},
    ]


def test_following_lists_only_open_candidates_with_an_extraction_from_followed_boards(
    client, session, log_in_as, make_posting, boards
):
    now = datetime.now(UTC)
    ids = save_postings(
        session,
        [
            make_posting(token="kansei-test", url="https://example.com/followed"),
            make_posting(token="kansei-test", title="Account Executive", url="https://example.com/not-a-candidate"),
            make_posting(token="kansei-test", url="https://example.com/no-extraction"),
            make_posting(source="lever", token="kansei-unnamed", url="https://example.com/not-followed"),
            make_posting(source="url", token="kansei-test", url="https://example.com/pasted"),
        ],
        now,
    )
    ids |= save_postings(session, [make_posting(token="kansei-test", url="https://example.com/closed")], now - timedelta(days=3))
    session.add_all(
        make_extraction(posting_id, 6, url) for url, posting_id in ids.items() if url != "https://example.com/no-extraction"
    )
    log_in_as("bob@example.com")
    client.post("/api/me/follows", json={"source": "lever", "token": "kansei-unnamed"})
    log_in_as("ada@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    response = client.get("/api/postings", params={"following": "true"})

    assert response.status_code == 200
    assert [row["posting"]["url"] for row in response.json()["postings"]] == ["https://example.com/followed"]


def test_following_applies_my_japanese_and_specialty_too(client, session, log_in_as, make_posting, boards):
    cases = [
        ("followed", "greenhouse", "kansei-test", ["backend"], "not_required"),
        ("needs-japanese", "greenhouse", "kansei-test", ["backend"], "required"),
        ("frontend", "greenhouse", "kansei-test", ["frontend"], "not_required"),
        ("not-followed", "lever", "kansei-unnamed", ["backend"], "not_required"),
    ]
    for name, source, token, specialties, required in cases:
        url = f"https://example.com/{name}"
        ids = save_postings(session, [make_posting(source=source, token=token, id=name, url=url)], datetime.now(UTC))
        facts = FACTS.model_copy(update={"specialties": specialties, "japanese_required": required})
        session.add(make_extraction(ids[url], 6, name, facts=facts.model_dump(mode="json")))
    log_in_as("ada@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})

    body = client.get("/api/postings", params={"following": "true", "japanese": "none", "specialty": "backend"}).json()

    assert ([row["posting"]["url"] for row in body["postings"]], body["total"]) == (["https://example.com/followed"], 1)


def test_following_postings_while_logged_out_is_401(client):
    response = client.get("/api/postings", params={"following": "true"})

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), [
    ("GET", "/api/me/follows", None),
    ("POST", "/api/me/follows", {"source": "greenhouse", "token": "kansei-test"}),
    ("POST", "/api/me/follows", {"source": "lever", "token": "kansei-missing"}),
    ("DELETE", "/api/me/follows/greenhouse/kansei-test", None),
    ("GET", "/api/probe?q=https://jobs.lever.co/kansei-missing", None),
])
def test_follow_endpoints_refuse_a_logged_out_user(client, ats, boards, method, path, body):
    response = client.request(method, path, json=body)

    assert response.status_code == 401
    assert ats.requested == []


def test_a_posting_says_whether_it_has_a_board_to_follow(client, session, make_posting, boards):
    session.add(Board(source="ashby", token="kansei-removed", status="removed"))
    ids = save_postings(
        session,
        [
            make_posting(token="kansei-test", url="https://example.com/board"),
            make_posting(source="url", token="kansei-test", url="https://example.com/pasted"),
            make_posting(source="ashby", token="kansei-removed", url="https://example.com/removed"),
        ],
        datetime.now(UTC),
    )

    has_board = {url: client.get(f"/api/postings/{posting_id}").json()["posting"]["has_board"] for url, posting_id in ids.items()}

    assert has_board == {
        "https://example.com/board": True,
        "https://example.com/pasted": False,
        "https://example.com/removed": False,
    }


def test_unfollowing_a_board_you_dont_follow_is_404(client, log_in_as, boards):
    log_in_as("ada@example.com")

    response = client.delete("/api/me/follows/greenhouse/kansei-test")

    assert response.status_code == 404
