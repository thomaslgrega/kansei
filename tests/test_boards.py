from typing import get_args

import pytest
from sqlalchemy import delete, select

import kansei
from kansei import boards_to_fetch
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
