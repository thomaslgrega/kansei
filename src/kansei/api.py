from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, tuple_
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.exc import IntegrityError

from kansei import auth, is_candidate, is_sales_or_support
from kansei.auth import CurrentUser, SessionCookie, current_user
from kansei.config import settings
from kansei.db import (
    Board,
    BoardSource,
    Extraction,
    Follow,
    Posting,
    SessionDep,
    Tracked,
    TrackStatus,
)
from kansei.llm import PostingFacts, prompt_snapshot

api = APIRouter(prefix="/api")
api.include_router(auth.router)


class PostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    source: str
    token: str
    company: str
    has_board: bool
    title: str
    location: str
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    model: str
    prompt_sha: str
    created_at: datetime
    facts: PostingFacts


class PostingDetail(BaseModel):
    posting: PostingOut
    extraction: ExtractionOut | None


class PostingWithFacts(BaseModel):
    posting: PostingOut
    facts: PostingFacts
    sales_or_support: bool


OPEN_FOR = timedelta(days=2)


@api.get("/postings")
def list_postings(
    session: SessionDep, token: str | None = None, following: bool = False, cookie: SessionCookie = None
) -> list[PostingWithFacts]:
    prompt_sha, _ = prompt_snapshot()
    newest = (
        select(Extraction.posting_id, Extraction.facts)
        .where(Extraction.model == settings.openai_model, Extraction.prompt_sha == prompt_sha)
        .ext(distinct_on(Extraction.posting_id))
        .order_by(Extraction.posting_id, Extraction.created_at.desc(), Extraction.id.desc())
        .subquery()
    )
    statement = (
        select(Posting, newest.c.facts)
        .join(newest, newest.c.posting_id == Posting.id)
        .where(Posting.last_seen_at > datetime.now(UTC) - OPEN_FOR)
        .order_by(Posting.first_seen_at.desc(), Posting.id.desc())
    )
    if token is not None:
        statement = statement.where(Posting.token == token)
    if following:
        user = current_user(session, cookie)
        followed = (
            select(Board.source, Board.token)
            .join(Follow, Follow.board_id == Board.id)
            .where(Follow.user_id == user.id)
        )
        statement = statement.where(tuple_(Posting.source, Posting.token).in_(followed))
    return [
        PostingWithFacts(
            posting=PostingOut.model_validate(posting),
            facts=facts,
            sales_or_support=is_sales_or_support(posting.title),
        )
        for posting, facts in session.execute(statement)
        if is_candidate(posting.title, posting.location)
    ]


@api.get("/postings/{posting_id}")
def get_posting(posting_id: int, session: SessionDep) -> PostingDetail:
    posting = session.get(Posting, posting_id)
    if posting is None:
        raise HTTPException(status_code=404, detail="Posting not found")

    prompt_sha, _ = prompt_snapshot()
    extraction = session.scalars(
        select(Extraction)
        .where(
            Extraction.posting_id == posting_id,
            Extraction.model == settings.openai_model,
            Extraction.prompt_sha == prompt_sha,
        )
        .order_by(Extraction.created_at.desc(), Extraction.id.desc())
        .limit(1)
    ).first()

    return PostingDetail(
        posting=PostingOut.model_validate(posting),
        extraction=ExtractionOut.model_validate(extraction) if extraction else None
    )


class TrackIn(BaseModel):
    posting_id: int
    status: TrackStatus = "saved"
    note: str = Field("", max_length=2000)


class TrackUpdate(BaseModel):
    status: TrackStatus | None = None
    note: str | None = Field(None, max_length=2000)


class TrackedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TrackStatus
    note: str
    created_at: datetime
    posting: PostingOut


@api.get("/me/tracked")
def list_tracked(user: CurrentUser, session: SessionDep) -> list[TrackedOut]:
    tracked = session.scalars(
        select(Tracked)
        .where(Tracked.user_id == user.id)
        .order_by(Tracked.created_at.desc(), Tracked.id.desc())
    )
    return [TrackedOut.model_validate(row) for row in tracked]


@api.post("/me/tracked", status_code=201)
def track(body: TrackIn, user: CurrentUser, session: SessionDep) -> TrackedOut:
    if session.get(Posting, body.posting_id) is None:
        raise HTTPException(status_code=404, detail="Posting not found")
    tracked = Tracked(user_id=user.id, **body.model_dump())
    session.add(tracked)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Posting already tracked")
    return TrackedOut.model_validate(tracked)


@api.patch("/me/tracked/{tracked_id}")
def update_tracked(tracked_id: int, body: TrackUpdate, user: CurrentUser, session: SessionDep) -> TrackedOut:
    tracked = session.scalar(
        select(Tracked)
        .where(
            Tracked.id == tracked_id,
            Tracked.user_id == user.id
        )
    )
    if tracked is None:
        raise HTTPException(status_code=404, detail="Tracked posting not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tracked, field, value)
    session.commit()
    return TrackedOut.model_validate(tracked)


@api.delete("/me/tracked/{tracked_id}", status_code=204)
def untrack(tracked_id: int, user: CurrentUser, session: SessionDep) -> None:
    result = session.execute(
        delete(Tracked)
        .where(Tracked.id == tracked_id, Tracked.user_id == user.id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Tracked posting not found")
    session.commit()


class BoardIn(BaseModel):
    source: BoardSource
    token: str


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: BoardSource
    token: str
    company: str


@api.get("/me/follows")
def list_follows(user: CurrentUser, session: SessionDep) -> list[BoardOut]:
    boards = session.scalars(select(Board).join(Follow, Follow.board_id == Board.id).where(Follow.user_id == user.id))
    return [BoardOut.model_validate(board) for board in sorted(boards, key=lambda board: (board.company.lower(), board.id))]


@api.post("/me/follows", status_code=201)
def follow(body: BoardIn, user: CurrentUser, session: SessionDep, response: Response) -> BoardOut:
    board = session.scalar(select(Board).where(Board.source == body.source, Board.token == body.token))
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    created = session.scalar(
        insert(Follow)
        .values(user_id=user.id, board_id=board.id)
        .on_conflict_do_nothing()
        .returning(Follow.board_id)
    )
    session.commit()
    if created is None:
        response.status_code = 200
    return BoardOut.model_validate(board)


# Not `{token}`: current_user already takes a parameter by that name, for the session cookie.
@api.delete("/me/follows/{source}/{board_token}", status_code=204)
def unfollow(source: BoardSource, board_token: str, user: CurrentUser, session: SessionDep) -> None:
    board_id = select(Board.id).where(Board.source == source, Board.token == board_token).scalar_subquery()
    result = session.execute(delete(Follow).where(Follow.user_id == user.id, Follow.board_id == board_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Board not followed")
    session.commit()


app = FastAPI(title="kansei")
app.include_router(api)

WEB_DIST = Path(__file__).parents[2] / "web" / "dist"
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
