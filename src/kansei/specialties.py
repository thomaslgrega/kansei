from sqlalchemy import ColumnElement, false, or_, true, type_coerce
from sqlalchemy.dialects.postgresql import JSONB, array

from kansei.llm import SPECIALTIES


def passes_specialty(facts: ColumnElement[dict], specialty: str | None) -> ColumnElement[bool]:
    # Unknown values, fullstack among them, are dropped, so a list of only those keeps nothing.
    if specialty is None:
        return true()
    picked = set(specialty.split(","))
    specialties = type_coerce(facts, JSONB)["specialties"]
    named = [name for name in SPECIALTIES if name in picked and name != "fullstack"]
    conditions = []
    if named:
        conditions.append(specialties.has_any(array(named)))
    if "other" in picked:
        conditions.append(specialties == type_coerce([], JSONB))
    return or_(false(), *conditions)
