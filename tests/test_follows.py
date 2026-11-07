from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_api import make_extraction

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
    assert second.json() == {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K."}
    assert client.get("/api/me/follows").json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K."},
    ]


def test_following_a_board_that_isnt_on_kansei_is_404_and_follows_nothing(client, session, log_in_as):
    log_in_as("ada@example.com")

    response = client.post("/api/me/follows", json={"source": "lever", "token": "kansei-missing"})

    assert response.status_code == 404
    assert client.get("/api/me/follows").json() == []
    assert session.scalar(select(Board).where(Board.token == "kansei-missing")) is None


def test_unfollowing_removes_only_that_follow(client, log_in_as, boards):
    log_in_as("bob@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    log_in_as("ada@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    client.post("/api/me/follows", json={"source": "lever", "token": "kansei-unnamed"})

    response = client.delete("/api/me/follows/greenhouse/kansei-test")

    assert response.status_code == 204
    assert client.get("/api/me/follows").json() == [
        {"source": "lever", "token": "kansei-unnamed", "company": "kansei-unnamed"},
    ]
    client.post("/api/login", json={"email": "bob@example.com", "password": "correct password"})
    assert client.get("/api/me/follows").json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K."},
    ]


def test_follows_lists_only_your_boards_by_company_name_even_without_open_candidates(client, session, log_in_as, boards):
    session.add(Board(source="greenhouse", token="kansei-other", name="Other Co"))
    session.flush()
    log_in_as("bob@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-other"})
    log_in_as("ada@example.com")
    client.post("/api/me/follows", json={"source": "greenhouse", "token": "kansei-test"})
    client.post("/api/me/follows", json={"source": "lever", "token": "kansei-unnamed"})

    response = client.get("/api/me/follows")

    assert response.json() == [
        {"source": "greenhouse", "token": "kansei-test", "company": "Kansei Test K.K."},
        {"source": "lever", "token": "kansei-unnamed", "company": "kansei-unnamed"},
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
    assert [row["posting"]["url"] for row in response.json()] == ["https://example.com/followed"]


def test_following_postings_while_logged_out_is_401(client):
    response = client.get("/api/postings", params={"following": "true"})

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), [
    ("GET", "/api/me/follows", None),
    ("POST", "/api/me/follows", {"source": "greenhouse", "token": "kansei-test"}),
    ("DELETE", "/api/me/follows/greenhouse/kansei-test", None),
])
def test_follow_endpoints_refuse_a_logged_out_user(client, boards, method, path, body):
    response = client.request(method, path, json=body)

    assert response.status_code == 401


def test_a_posting_says_whether_it_has_a_board_to_follow(client, session, make_posting, boards):
    ids = save_postings(
        session,
        [
            make_posting(token="kansei-test", url="https://example.com/board"),
            make_posting(source="url", token="kansei-test", url="https://example.com/pasted"),
        ],
        datetime.now(UTC),
    )

    has_board = {url: client.get(f"/api/postings/{posting_id}").json()["posting"]["has_board"] for url, posting_id in ids.items()}

    assert has_board == {"https://example.com/board": True, "https://example.com/pasted": False}


def test_unfollowing_a_board_you_dont_follow_is_404(client, log_in_as, boards):
    log_in_as("ada@example.com")

    response = client.delete("/api/me/follows/greenhouse/kansei-test")

    assert response.status_code == 404
