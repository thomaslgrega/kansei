from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from kansei.config import settings
from kansei.db import Extraction, Posting, SessionDep
from kansei.llm import PostingFacts, prompt_snapshot

app = FastAPI(title="kansei")


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


@app.get("/postings")
def list_postings(
    session: SessionDep,
    token: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PostingOut]:
    statement = select(Posting).order_by(Posting.first_seen_at.desc(), Posting.id.desc())
    if token is not None:
        statement = statement.where(Posting.token == token)
    postings = session.scalars(statement.limit(limit).offset(offset))
    return [PostingOut.model_validate(posting) for posting in postings]

@app.get("/postings/{posting_id}")
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
