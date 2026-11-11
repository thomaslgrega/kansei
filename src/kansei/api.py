import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Select, delete, func, select, tuple_
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from kansei import JobPosting, auth, board_jobs, is_candidate, is_sales_or_support
from kansei.auth import CurrentUser, SessionCookie, current_user
from kansei.config import settings
from kansei.db import (
    Board,
    BoardSource,
    Extraction,
    Follow,
    Posting,
    SessionDep,
    Stage,
    Tracked,
)
from kansei.llm import PostingFacts, prompt_snapshot
from kansei.ratelimit import PROBE_PER_USER, Now, rate_limit
from kansei.sources import (
    SLUG,
    SOURCES,
    NotABoard,
    fetch_board_name,
    looks_like_url,
    name_slugs,
    parse_board_url,
)

api = APIRouter(prefix="/api")
api.include_router(auth.router)


async def get_http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        yield client


HttpDep = Annotated[httpx.AsyncClient, Depends(get_http)]


class PostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    source: str
    token: str
    company: str
    logo_url: str | None
    has_board: bool
    title: str
    location: str
    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime
    listed: bool


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
        .where(Posting.listed)
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
        if is_candidate(posting)
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
    stage: Stage = "saved"
    note: str = Field("", max_length=2000)


class TrackUpdate(BaseModel):
    stage: Stage | None = None
    note: str | None = Field(None, max_length=2000)


class TrackedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: Stage
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
    token: str = Field(pattern=rf"^{SLUG.pattern}$")


class BoardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: BoardSource
    token: str
    company: str


class ProbeHit(BaseModel):
    source: BoardSource
    token: str
    company: str | None
    titles: list[str]
    candidates: int
    state: Literal["not_on_kansei", "on_kansei", "removed"]
    following: bool


class ProbeOut(BaseModel):
    hits: list[ProbeHit]
    message: str | None = None


def board_named(source: str, token: str) -> Select[tuple[Board]]:
    # Ignores case, so pasting `Acme` can't add a second copy of a removed `acme`.
    return select(Board).where(Board.source == source, func.lower(Board.token) == token.lower())


NO_BOARD_AT_URL = "No board found at that URL."
TRY_THE_URL = "No board found for that name. Try pasting its Greenhouse, Lever, Ashby or HRMOS board URL."


async def fetch_board(http: httpx.AsyncClient, source: str, token: str) -> tuple[list[JobPosting], str | None] | None:
    jobs = await board_jobs(http, source, token)
    if jobs is None:
        return None
    return jobs, await fetch_board_name(http, source, token)


def probe_hit(session: Session, user_id: int, source: str, token: str, jobs: list[JobPosting], name: str | None) -> ProbeHit:
    board = session.scalar(board_named(source, token))
    return ProbeHit(
        source=source,
        token=board.token if board else token,
        company=(board.name if board else None) or name,
        titles=[job.title for job in jobs[:5]],
        candidates=sum(is_candidate(job) for job in jobs),
        state="not_on_kansei" if board is None else "removed" if board.status == "removed" else "on_kansei",
        following=board is not None and session.get(Follow, (user_id, board.id)) is not None,
    )


@api.get("/probe")
async def probe(q: str, user: CurrentUser, session: SessionDep, http: HttpDep, now: Now) -> ProbeOut:
    user_id = user.id
    rate_limit(session, PROBE_PER_USER, str(user_id), now)
    if looks_like_url(q):
        try:
            guesses = [parse_board_url(q)]
        except NotABoard as error:
            return ProbeOut(hits=[], message=str(error))
        miss = NO_BOARD_AT_URL
    else:
        # Probing an HRMOS board fetches its job pages, too many requests for a guess.
        guesses = [(source, slug) for source in SOURCES if source != "hrmos" for slug in name_slugs(q)]
        miss = TRY_THE_URL
    session.rollback()
    found = await asyncio.gather(*(fetch_board(http, source, token) for source, token in guesses))
    hits = [
        probe_hit(session, user_id, source, token, *fetched)
        for (source, token), fetched in zip(guesses, found, strict=True)
        if fetched is not None
    ]
    return ProbeOut(hits=hits, message=None if hits else miss)


@api.get("/me/follows")
def list_follows(user: CurrentUser, session: SessionDep) -> list[BoardOut]:
    boards = session.scalars(select(Board).join(Follow, Follow.board_id == Board.id).where(Follow.user_id == user.id))
    return [BoardOut.model_validate(board) for board in sorted(boards, key=lambda board: (board.company.lower(), board.id))]


def locked_board(session: Session, source: str, token: str) -> Board | None:
    # FOR SHARE waits out a concurrent removal, so no follow lands after its DELETE.
    return session.scalar(board_named(source, token).with_for_update(read=True))


@api.post("/me/follows", status_code=201)
async def follow(body: BoardIn, user: CurrentUser, session: SessionDep, http: HttpDep, response: Response) -> BoardOut:
    user_id = user.id
    board = locked_board(session, body.source, body.token)
    if board is None:
        session.rollback()
        if await board_jobs(http, body.source, body.token) is None:
            raise HTTPException(status_code=404, detail=f"No board {body.token} on {body.source}.")
        name = await fetch_board_name(http, body.source, body.token)
        session.execute(
            insert(Board)
            .values(source=body.source, token=body.token, name=name, added_by=user_id)
            .on_conflict_do_nothing()
        )
        board = locked_board(session, body.source, body.token)
    if board.status == "removed":
        raise HTTPException(status_code=409, detail="This company was removed from kansei and can't be added.")
    created = session.scalar(
        insert(Follow)
        .values(user_id=user_id, board_id=board.id)
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


class SinglePageApp(StaticFiles):
    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != 404 or path == "api" or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)


def create_app(web_dist: Path) -> FastAPI:
    app = FastAPI(title="kansei")
    app.include_router(api)
    if web_dist.is_dir():
        app.mount("/", SinglePageApp(directory=web_dist, html=True), name="web")
    return app


app = create_app(Path(__file__).parents[2] / "web" / "dist")
