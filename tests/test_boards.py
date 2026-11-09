from datetime import UTC, datetime
from typing import get_args

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

import kansei
from kansei import (
    boards_to_fetch,
    fetch_board_names,
    remove_board,
    save_board_names,
    save_postings,
    unnamed_boards,
)
from kansei.db import Board, BoardSource, Follow, Posting, Tracked, User


def test_boards_to_fetch_reads_the_table_in_id_order(session, monkeypatch):
    monkeypatch.setattr(kansei.settings, "boards", None)
    session.execute(delete(Board))
    session.add(Board(source="lever", token="b"))
    session.flush()
    session.add(Board(source="greenhouse", token="a"))
    session.flush()

    assert boards_to_fetch(session) == ["lever:b", "greenhouse:a"]


def test_boards_to_fetch_skips_removed_boards(session, monkeypatch):
    monkeypatch.setattr(kansei.settings, "boards", None)
    session.execute(delete(Board))
    session.add_all([
        Board(source="lever", token="a"),
        Board(source="greenhouse", token="b", status="removed"),
        Board(source="ashby", token="c"),
    ])
    session.flush()

    assert boards_to_fetch(session) == ["lever:a", "ashby:c"]


def test_unnamed_boards_skips_removed_boards(session):
    session.execute(delete(Board))
    session.add_all([
        Board(source="lever", token="a"),
        Board(source="greenhouse", token="b", status="removed"),
    ])
    session.flush()

    assert [(board.source, board.token) for board in unnamed_boards(session)] == [("lever", "a")]


def test_a_new_board_is_active(session):
    session.execute(delete(Board))
    session.add(Board(source="lever", token="a"))
    session.flush()

    assert session.scalars(select(Board.status)).all() == ["active"]


def test_the_database_rejects_an_unknown_board_status(session):
    session.add(Board(source="lever", token="a", status="deleted"))

    with pytest.raises(IntegrityError, match="ck_boards_status"):
        session.flush()


def test_boards_to_fetch_returns_the_override_whatever_the_table_holds(session, monkeypatch):
    monkeypatch.setattr(kansei.settings, "boards", ["lever:mujininc"])
    session.add(Board(source="greenhouse", token="a"))
    session.flush()

    assert boards_to_fetch(session) == ["lever:mujininc"]


@pytest.mark.parametrize("source", get_args(BoardSource))
def test_the_database_accepts_every_board_source(session, source):
    session.execute(delete(Board))
    session.add(Board(source=source, token="a"))
    session.flush()

    assert session.execute(select(Board.source, Board.token)).all() == [(source, "a")]


async def test_naming_fetches_only_unnamed_boards_and_keeps_failures_null(session):
    session.execute(delete(Board))
    session.add_all([
        Board(source="greenhouse", token="anthropic", name="Anthropic"),
        Board(source="lever", token="mujininc"),
        Board(source="greenhouse", token="gone"),
    ])
    session.flush()
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.host == "jobs.lever.co":
            return httpx.Response(200, text="<html><head><title>Mujin</title></head></html>")
        return httpx.Response(404, json={"name": "Gone"})

    unnamed = unnamed_boards(session)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        names = await fetch_board_names(client, unnamed)
    save_board_names(session, names)

    assert sorted(requested) == [
        "https://boards-api.greenhouse.io/v1/boards/gone",
        "https://jobs.lever.co/mujininc",
    ]
    assert {f"{board.source}:{board.token}": name for board, name in names.items()} == {
        "lever:mujininc": "Mujin",
        "greenhouse:gone": None,
    }
    assert session.execute(select(Board.source, Board.token, Board.name).order_by(Board.id)).all() == [
        ("greenhouse", "anthropic", "Anthropic"),
        ("lever", "mujininc", "Mujin"),
        ("greenhouse", "gone", None),
    ]


def test_save_board_names_never_overwrites_a_name_set_after_the_read(session):
    session.execute(delete(Board))
    renamed = Board(source="lever", token="mujininc")
    failed = Board(source="greenhouse", token="gone")
    fetched = Board(source="greenhouse", token="anthropic")
    session.add_all([renamed, failed, fetched])
    session.flush()
    session.execute(update(Board).where(Board.id == renamed.id).values(name="Mujin Inc."))

    save_board_names(session, {renamed: "Mujin", failed: None, fetched: "Anthropic"})

    assert session.execute(select(Board.source, Board.token, Board.name).order_by(Board.id)).all() == [
        ("lever", "mujininc", "Mujin Inc."),
        ("greenhouse", "gone", None),
        ("greenhouse", "anthropic", "Anthropic"),
    ]


def test_the_database_rejects_a_board_named_the_empty_string(session):
    session.add(Board(source="greenhouse", token="a", name=""))

    with pytest.raises(IntegrityError, match="ck_boards_name"):
        session.flush()


def test_removing_a_board_deletes_only_its_follows_and_keeps_its_postings_and_tracked_rows(session, make_posting):
    session.execute(delete(Board))
    junk = Board(source="greenhouse", token="kansei-junk")
    kept = Board(source="lever", token="kansei-kept")
    ada = User(email="ada@example.com", password_hash="not a real hash")
    bob = User(email="bob@example.com", password_hash="not a real hash")
    session.add_all([junk, kept, ada, bob])
    session.flush()
    session.add_all([
        Follow(user_id=ada.id, board_id=junk.id),
        Follow(user_id=bob.id, board_id=junk.id),
        Follow(user_id=ada.id, board_id=kept.id),
    ])
    ids = save_postings(
        session,
        [make_posting(token="kansei-junk", url="https://example.com/junk")],
        datetime(2026, 11, 1, tzinfo=UTC),
    )
    session.add(Tracked(user_id=ada.id, posting_id=ids["https://example.com/junk"], status="applied", note="Called back"))
    session.flush()

    remove_board(session, "greenhouse:kansei-junk")

    assert session.execute(select(Board.source, Board.token, Board.status).order_by(Board.id)).all() == [
        ("greenhouse", "kansei-junk", "removed"),
        ("lever", "kansei-kept", "active"),
    ]
    user_ids = [ada.id, bob.id]
    assert session.execute(select(Follow.user_id, Follow.board_id).where(Follow.user_id.in_(user_ids))).all() == [
        (ada.id, kept.id),
    ]
    assert session.execute(select(Posting.url, Posting.token).where(Posting.token == "kansei-junk")).all() == [
        ("https://example.com/junk", "kansei-junk"),
    ]
    assert session.execute(
        select(Tracked.user_id, Tracked.posting_id, Tracked.status, Tracked.note).where(Tracked.user_id.in_(user_ids))
    ).all() == [
        (ada.id, ids["https://example.com/junk"], "applied", "Called back"),
    ]


@pytest.mark.parametrize("board", ["greenhouse:kansei-missing", "lever:kansei-junk", "kansei-junk"])
def test_removing_a_board_that_isnt_on_kansei_fails_and_changes_nothing(session, board):
    session.execute(delete(Board))
    session.add(Board(source="greenhouse", token="kansei-junk"))
    session.flush()

    with pytest.raises(LookupError, match=f"^no board {board} on kansei$"):
        remove_board(session, board)
    assert session.execute(select(Board.source, Board.token, Board.status)).all() == [
        ("greenhouse", "kansei-junk", "active"),
    ]
