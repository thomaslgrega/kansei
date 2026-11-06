from typing import get_args

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

import kansei
from kansei import boards_to_fetch, fill_board_names
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


async def test_fill_board_names_fetches_only_unnamed_boards_and_keeps_failures_null(session):
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

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        unnamed = await fill_board_names(session, client)

    assert sorted(requested) == [
        "https://boards-api.greenhouse.io/v1/boards/gone",
        "https://jobs.lever.co/mujininc",
    ]
    assert unnamed == ["greenhouse:gone"]
    assert session.execute(select(Board.source, Board.token, Board.name).order_by(Board.id)).all() == [
        ("greenhouse", "anthropic", "Anthropic"),
        ("lever", "mujininc", "Mujin"),
        ("greenhouse", "gone", None),
    ]


def test_the_database_rejects_a_board_named_the_empty_string(session):
    session.add(Board(source="greenhouse", token="a", name=""))

    with pytest.raises(IntegrityError, match="ck_boards_name"):
        session.flush()
