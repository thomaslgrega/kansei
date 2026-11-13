from sqlalchemy import ColumnElement, false, or_, true, type_coerce
from sqlalchemy.dialects.postgresql import JSONB, array

from kansei.llm import SPECIALTIES


def passes_specialty(facts: ColumnElement[dict], choice: str | None) -> ColumnElement[bool]:
    # Unknown values are dropped, so a choice of only unknown values keeps nothing.
    if choice is None:
        return true()
    picked = set(choice.split(","))
    specialties = type_coerce(facts, JSONB)["specialties"]
    named = [specialty for specialty in SPECIALTIES if specialty in picked]
    conditions = []
    if named:
        conditions.append(specialties.has_any(array(named)))
    if "other" in picked:
        conditions.append(specialties == type_coerce([], JSONB))
    return or_(false(), *conditions)
