from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError

from kansei import auth, is_candidate, is_sales_or_support
from kansei.auth import CurrentUser
from kansei.config import settings
from kansei.db import Extraction, Posting, SessionDep, Tracked, TrackStatus
from kansei.llm import PostingFacts, prompt_snapshot

api = APIRouter(prefix="/api")
api.include_router(auth.router)


class PostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    source: str
    token: str
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
def list_postings(session: SessionDep, token: str | None = None) -> list[PostingWithFacts]:
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

app = FastAPI(title="kansei")
app.include_router(api)

WEB_DIST = Path(__file__).parents[2] / "web" / "dist"
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
