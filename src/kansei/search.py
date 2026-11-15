import re

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

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff\uff66-\uff9f]")


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
    starts_a_word = rf"(?<![[:alnum:]_]){re.escape(word)}"
    skill_words = func.string_to_array(func.lower(skill), " ", type_=ARRAY(String))
    return or_(
        *(text.regexp_match(starts_a_word, "i") for text in texts),
        exists().where(func.lower(literal(word)) == any_(skill_words)),
    )
