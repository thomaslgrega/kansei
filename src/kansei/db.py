from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Literal, get_args

from fastapi import Depends
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    UniqueConstraint,
    column,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from kansei.config import settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


BoardSource = Literal["greenhouse", "lever"]


class Board(Base):
    __tablename__ = "boards"
    __table_args__ = (
        UniqueConstraint("source", "token"),
        CheckConstraint(column("source").in_(get_args(BoardSource)), name="source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[BoardSource] = mapped_column(String)
    token: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Extraction(Base):
    __tablename__ = "extractions"
    __table_args__ = (UniqueConstraint("posting_id", "text_sha256", "model", "prompt_sha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"))
    text: Mapped[str]
    text_sha256: Mapped[str]
    model: Mapped[str]
    prompt_sha: Mapped[str]
    facts: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Posting(Base):
    __tablename__ = "postings"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(unique=True)
    source: Mapped[str]
    token: Mapped[str]
    title: Mapped[str]
    location: Mapped[str]
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


TrackStatus = Literal["saved", "applied", "interviewing", "offer", "rejected"]


class Tracked(Base):
    __tablename__ = "tracked"
    __table_args__ = (
        UniqueConstraint("user_id", "posting_id"),
        CheckConstraint(column("status").in_(get_args(TrackStatus)), name="status")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"))
    status: Mapped[TrackStatus] = mapped_column(String)
    note: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posting: Mapped[Posting] = relationship(lazy="joined")


engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
