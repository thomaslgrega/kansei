from typing import Literal, get_args

from sqlalchemy import ColumnElement, case, null, true, type_coerce
from sqlalchemy.dialects.postgresql import JSONB

from kansei.llm import Jlpt

Level = Literal["basic", "conversational", "business", "native"]
JapaneseRequirement = Literal[Level, "none", "not_stated"]

LEVELS: tuple[Level, ...] = get_args(Level)

JLPT_LEVELS: dict[Jlpt, Level] = {
    "N1": "business",
    "N2": "business",
    "N3": "conversational",
    "N4": "basic",
    "N5": "basic",
}


def japanese_requirement(facts: ColumnElement[dict | None]) -> ColumnElement[str | None]:
    facts = type_coerce(facts, JSONB)
    required = facts["japanese_required"].astext
    level = facts["japanese_level"].astext
    jlpt = facts["jlpt"].astext
    return case(
        (required.is_(None), null()),
        (required == "not_stated", "not_stated"),
        (required != "required", "none"),
        (level.in_(LEVELS), level),
        *((jlpt == name, jlpt_level) for name, jlpt_level in JLPT_LEVELS.items()),
        else_="business",
    )


def passes_japanese(requirement: ColumnElement[str], choice: str) -> ColumnElement[bool]:
    # An unknown choice passes everything, as `any` does.
    if choice == "none":
        return requirement.in_(["none", "not_stated"])
    if choice in LEVELS:
        return requirement.in_(["none", "not_stated", *LEVELS[: LEVELS.index(choice) + 1]])
    return true()
