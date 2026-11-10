import math
from datetime import UTC, datetime, timedelta
from typing import Annotated, NamedTuple

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from kansei.db import RateLimit


class Limit(NamedTuple):
    name: str
    count: int
    per: timedelta


LOGIN_PER_IP = Limit("login-ip", 10, timedelta(minutes=1))
LOGIN_PER_EMAIL = Limit("login-email", 10, timedelta(hours=1))
SIGNUP_PER_IP = Limit("signup-ip", 5, timedelta(hours=1))
PROBE_PER_USER = Limit("probe-user", 30, timedelta(minutes=1))


def utcnow() -> datetime:
    return datetime.now(UTC)


Now = Annotated[datetime, Depends(utcnow)]


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded is None:
        return request.client.host if request.client else "unknown"
    # Clients can prepend entries; Google's front end appends the address it saw.
    return forwarded.split(",")[-1].strip()


def window_end(now: datetime, per: timedelta) -> datetime:
    seconds = per.total_seconds()
    return datetime.fromtimestamp((now.timestamp() // seconds + 1) * seconds, UTC)


def rate_limit(session: Session, limit: Limit, key: str, now: datetime) -> None:
    ends_at = window_end(now, limit.per)
    count = session.scalar(
        insert(RateLimit)
        .values(key=f"{limit.name}:{key}", ends_at=ends_at, count=1)
        .on_conflict_do_update(index_elements=["key", "ends_at"], set_={"count": RateLimit.count + 1})
        .returning(RateLimit.count)
    )
    # SKIP LOCKED, so instances cleaning up at once never wait on or deadlock with each other.
    expired = select(RateLimit.key, RateLimit.ends_at).where(RateLimit.ends_at <= now).with_for_update(skip_locked=True)
    session.execute(delete(RateLimit).where(tuple_(RateLimit.key, RateLimit.ends_at).in_(expired)))
    session.commit()
    if count > limit.count:
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(math.ceil((ends_at - now).total_seconds()))},
        )
