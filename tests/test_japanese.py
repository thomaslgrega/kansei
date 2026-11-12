from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import JSONB

from kansei.japanese import japanese_requirement


def requirements(session, cases: list[tuple[str, str, str]]) -> list[str]:
    return [
        session.scalar(select(japanese_requirement(literal(
            {"japanese_required": required, "japanese_level": level, "jlpt": jlpt}, JSONB
        ))))
        for required, level, jlpt in cases
    ]


def test_a_named_level_wins_over_jlpt_and_jlpt_stands_in_when_no_level_is_named(session):
    cases = [
        ("required", "basic", "N1"),
        ("required", "conversational", "N1"),
        ("required", "business", "N5"),
        ("required", "native", "N3"),
        ("required", "not_stated", "N1"),
        ("required", "not_stated", "N2"),
        ("required", "not_stated", "N3"),
        ("required", "not_stated", "N4"),
        ("required", "not_stated", "N5"),
    ]

    assert requirements(session, cases) == [
        "basic", "conversational", "business", "native",
        "business", "business", "conversational", "basic", "basic",
    ]


def test_required_japanese_with_neither_a_level_nor_jlpt_is_business(session):
    assert requirements(session, [("required", "not_stated", "not_stated")]) == ["business"]


def test_preferred_and_not_required_are_none_whatever_level_they_name(session):
    cases = [
        ("preferred", "business", "N2"),
        ("preferred", "not_stated", "not_stated"),
        ("not_required", "conversational", "N3"),
        ("not_required", "not_stated", "not_stated"),
    ]

    assert requirements(session, cases) == ["none", "none", "none", "none"]


def test_not_stated_is_not_stated_whatever_level_or_jlpt_it_names(session):
    cases = [
        ("not_stated", "not_stated", "not_stated"),
        ("not_stated", "business", "not_stated"),
        ("not_stated", "not_stated", "N3"),
    ]

    assert requirements(session, cases) == ["not_stated", "not_stated", "not_stated"]
