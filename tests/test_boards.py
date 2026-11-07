from typing import get_args

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

import kansei
from kansei import boards_to_fetch, fetch_board_names, save_board_names, unnamed_boards
from kansei.db import Board, BoardSource


def test_boards_to_fetch_reads_the_table_in_id_order(session, monkeypatch):
    monkeypatch.setattr(kansei.settings, "boards", None)
    session.execute(delete(Board))
    session.add(Board(source="lever", token="b"))
    session.flush()
    session.add(Board(source="greenhouse", token="a"))
    session.flush()

    assert boards_to_fetch(session) == ["lever:b", "greenhouse:a"]


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
