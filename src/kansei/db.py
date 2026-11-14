from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
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
    exists,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    column_property,
    mapped_column,
    relationship,
)

from kansei.config import settings


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


BoardSource = Literal["greenhouse", "lever", "ashby", "hrmos"]
BoardStatus = Literal["active", "removed"]


class Board(Base):
    __tablename__ = "boards"
    __table_args__ = (
        UniqueConstraint("source", "token"),
        CheckConstraint(column("source").in_(get_args(BoardSource)), name="source"),
        CheckConstraint(column("name") != "", name="name"),
        CheckConstraint(column("status").in_(get_args(BoardStatus)), name="status"),
        CheckConstraint(column("logo_url") != "", name="logo_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[BoardSource] = mapped_column(String)
    token: Mapped[str]
    name: Mapped[str | None]
    logo_url: Mapped[str | None]
    status: Mapped[BoardStatus] = mapped_column(String, server_default="active")
    # Empty for seeded boards.
    added_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def company(self) -> str:
        return self.name or self.token


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

OPEN_FOR = timedelta(days=2)
NEW_FOR = timedelta(days=2)


class Posting(Base):
    __tablename__ = "postings"
    __table_args__ = (CheckConstraint(column("company_name") != "", name="company_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(unique=True)
    # Assigned so `company` below can refer to them in the class body.
    source: Mapped[str] = mapped_column()
    token: Mapped[str] = mapped_column()
    title: Mapped[str]
    location: Mapped[str]
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Only pasted postings set it, from their page; a board posting's name comes from its board.
    company_name: Mapped[str | None] = mapped_column()
    headline: Mapped[str | None]
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    company: Mapped[str] = column_property(
        func.coalesce(
            select(Board.name).where(Board.source == source, Board.token == token).scalar_subquery(),
            company_name,
            token,
        )
    )
    logo_url: Mapped[str | None] = column_property(
        select(Board.logo_url).where(Board.source == source, Board.token == token).scalar_subquery()
    )
    has_board: Mapped[bool] = column_property(
        exists().where(Board.source == source, Board.token == token, Board.status == "active")
    )

    @hybrid_property
    def listed(self) -> bool:
        return self.last_seen_at > datetime.now(UTC) - OPEN_FOR

    @hybrid_property
    def new(self) -> bool:
        return self.first_seen_at > datetime.now(UTC) - NEW_FOR


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


Stage = Literal["saved", "applied", "interviewing", "offer"]


class Tracked(Base):
    __tablename__ = "tracked"
    __table_args__ = (
        UniqueConstraint("user_id", "posting_id"),
        CheckConstraint(column("stage").in_(get_args(Stage)), name="stage")
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    posting_id: Mapped[int] = mapped_column(ForeignKey("postings.id"))
    stage: Mapped[Stage] = mapped_column(String)
    note: Mapped[str]
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    posting: Mapped[Posting] = relationship(lazy="joined")


class Follow(Base):
    __tablename__ = "follows"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    board_id: Mapped[int] = mapped_column(ForeignKey("boards.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RateLimit(Base):
    __tablename__ = "rate_limits"

    key: Mapped[str] = mapped_column(primary_key=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, index=True)
    count: Mapped[int]


engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
