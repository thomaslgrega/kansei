import re
from typing import Literal

from sqlalchemy import (
    ColumnElement,
    String,
    and_,
    any_,
    exists,
    func,
    literal,
    or_,
    true,
    type_coerce,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from kansei.db import Posting

CJK = re.compile(r"[\u3005\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff66-\uff9f]")


def matches_search(facts: ColumnElement[dict], q: str) -> ColumnElement[bool]:
    facts = type_coerce(facts, JSONB)
    texts = [Posting.company, Posting.token, Posting.title, Posting.headline, facts["role_summary"].astext]
    skills = func.jsonb_array_elements_text(facts["must_have_skills"]).table_valued("value").render_derived("skill")
    return and_(true(), *(matches_word(word, texts, skills.c.value) for word in q.split()))


def matches_word(word: str, texts: list[ColumnElement[str]], skill: ColumnElement[str]) -> ColumnElement[bool]:
    if CJK.search(word):
        return or_(
            *(text.icontains(word, autoescape=True) for text in texts),
            exists().where(skill.icontains(word, autoescape=True)),
        )
    # Only a Latin letter or digit joins a word, so "ruby" starts a word in シニアRubyエンジニア.
    starts_a_word = rf"(?<![0-9a-z\u00c0-\u024f_]){re.escape(word)}"
    skill_words = func.string_to_array(func.lower(skill), " ", type_=ARRAY(String))
    return or_(
        *(text.regexp_match(starts_a_word, "i") for text in texts),
        exists().where(func.lower(literal(word)) == any_(skill_words)),
    )


BoardMatch = Literal["exact", "partial"]


def board_match(q: str, company: str, token: str) -> BoardMatch | None:
    query = words(q)
    if not query:
        return None
    names = [name for name in (words(company), words(token)) if name]
    if any(query[i:i + len(name)] == name for name in names for i in range(len(query))):
        return "exact"
    *whole, start = query
    if any(
        name[i:i + len(whole)] == whole and len(name) > i + len(whole) and name[i + len(whole)].startswith(start)
        for name in names
        for i in range(len(name))
    ):
        return "partial"
    return None


def words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())
