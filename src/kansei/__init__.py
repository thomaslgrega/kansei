import asyncio
import hashlib
import re
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Literal

import httpx
from openai import AsyncOpenAI
from openai.types.responses import ParsedResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from kansei.config import settings
from kansei.db import Board, Extraction, Posting, engine
from kansei.llm import PostingFacts, cost_usd, extract, openai_client, prompt_snapshot
from kansei.sources import (
    SOURCES,
    fetch_posting,
    fetch_url,
)


class JobPosting(BaseModel):
    source: Literal["greenhouse", "lever", "url"]
    token: str
    id: str
    title: str
    url: HttpUrl
    posted_at: datetime | None
    location: str
    description: str | None = None


def is_candidate(title: str, location: str) -> bool:
    engineering = re.compile(r"engineer|developer|エンジニア|開発", re.IGNORECASE)
    in_japan = re.compile(
        r"japan|tokyo|osaka|kyoto|fukuoka|nagoya|yokohama|sapporo|kobe"
        r"|日本|東京|大阪|京都|福岡|名古屋|横浜|札幌|神戸|北海道|県",
        re.IGNORECASE,
    )
    open_remote = re.compile(r"^remote$|anywhere|worldwide|global|apac|asia", re.IGNORECASE)
    location = location.strip()
    reachable = in_japan.search(location) or open_remote.search(location)
    return bool(engineering.search(title) and reachable)


def is_sales_or_support(title: str) -> bool:
    customer_facing = re.compile(
        r"\b(sales|support|solutions?|field|customer success)\b|セールス|サポート|カスタマーサクセス",
        re.IGNORECASE,
    )
    return bool(customer_facing.search(title))


def boards_to_fetch(session: Session) -> list[str]:
    if settings.boards is not None:
        return settings.boards
    boards = session.scalars(select(Board).order_by(Board.id))
    return [f"{board.source}:{board.token}" for board in boards]


async def fetch_all(boards: list[str]) -> dict[str, list[dict] | Exception]:
    parsed = [board.split(":", 1) for board in boards]
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        results = await asyncio.gather(
            *(SOURCES[source](client, token) for source, token in parsed),
            return_exceptions=True,
        )
    return dict(zip(boards, results))


def validate(jobs: list[dict]) -> tuple[list[JobPosting], list[tuple[int, str]]]:
    passed, failed = [], []
    for job in jobs:
        try:
            passed.append(JobPosting.model_validate(job))
        except ValidationError as exc:
            failed.append((job.get("id", "unknown"), exc.errors()[0]["msg"]))
    return passed, failed


def save_postings(session: Session, jobs: list[JobPosting], seen_at: datetime) -> dict[str, int]:
    if not jobs:
        return {}

    rows = [
        {
            "url": str(job.url),
            "source": job.source,
            "token": job.token,
            "title": job.title,
            "location": job.location,
            "posted_at": job.posted_at,
            "first_seen_at": seen_at,
            "last_seen_at": seen_at,
        }
        for job in jobs
    ]
    statement = insert(Posting).values(rows)
    statement = statement.on_conflict_do_update(
        index_elements=[Posting.url],
        set_={
            "title": statement.excluded.title,
            "location": statement.excluded.location,
            "posted_at": statement.excluded.posted_at,
            "last_seen_at": statement.excluded.last_seen_at,
        },
    ).returning(Posting.url, Posting.id)
    return {url: posting_id for url, posting_id in session.execute(statement)}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extracted(session: Session, model: str, prompt_sha: str) -> set[tuple[int, str]]:
    statement = select(Extraction.posting_id, Extraction.text_sha256).where(
        Extraction.model == model,
        Extraction.prompt_sha == prompt_sha,
    )
    return {(posting_id, text_sha256) for posting_id, text_sha256 in session.execute(statement)}


def pending_extractions(
    texts: dict[str, str | Exception],
    ids: dict[str, int],
    cached: set[tuple[int, str]],
    cap: int,
) -> tuple[dict[str, str], int]:
    pending = [
        (url, text)
        for url, text in texts.items()
        if not isinstance(text, Exception) and (ids[url], sha256(text)) not in cached
    ]
    return dict(pending[:cap]), len(pending)


def show(facts: PostingFacts) -> None:
    print(f"  japanese: {facts.japanese_required}, level {facts.japanese_level}, jlpt {facts.jlpt}")
    print(f"            {facts.japanese_as_written or '(says nothing)'}")
    print(f"  remote:   {facts.remote_policy}")
    print(f"  skills:   {', '.join(facts.must_have_skills) or '(none)'}")
    print(f"  summary:  {facts.role_summary}")


async def model_input(http: httpx.AsyncClient, job: JobPosting) -> str:
    posting = job.description or await fetch_posting(http, job.token, job.id)
    return f"{job.title}\n\n{posting}"


async def fetch_texts(jobs: list[JobPosting]) -> list[str | Exception]:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as http:
        return await asyncio.gather(
            *(model_input(http, job) for job in jobs),
            return_exceptions=True,
        )


async def extract_one(
    llm: AsyncOpenAI,
    limit: asyncio.Semaphore,
    text: str,
) -> tuple[ParsedResponse[PostingFacts], float]:
    async with limit:
        started = time.perf_counter()
        response = await extract(llm, text)
        return response, time.perf_counter() - started


async def extract_batch(
    todo: dict[str, str],
) -> dict[str, tuple[ParsedResponse[PostingFacts], float] | Exception]:
    if not todo:
        return {}
    limit = asyncio.Semaphore(settings.llm_concurrency)
    llm = openai_client()
    results = await asyncio.gather(
        *(extract_one(llm, limit, text) for text in todo.values()),
        return_exceptions=True,
    )
    return dict(zip(todo, results))


async def amain() -> None:
    with Session(engine) as session:
        to_fetch = boards_to_fetch(session)
    started = time.perf_counter()
    results = await fetch_all(to_fetch)
    elapsed = time.perf_counter() - started

    boards = {t: r for t, r in results.items() if not isinstance(r, Exception)}
    failed = {t: r for t, r in results.items() if isinstance(r, Exception)}

    total_failed = 0
    postings: list[JobPosting] = []

    for token, jobs in boards.items():
        passed_jobs, failed_jobs = validate(jobs)
        postings += passed_jobs
        total_failed += len(failed_jobs)
    total_passed = len(postings)
    candidates = [job for job in postings if is_candidate(job.title, job.location)]

    with Session(engine) as session, session.begin():
        ids = save_postings(session, postings, datetime.now(UTC))

    total = total_passed + total_failed
    print(f"{total} jobs from {len(boards)}/{len(results)} boards in {elapsed:.2f}s")
    for token, exc in failed.items():
        print(f"  skipped {token}: {type(exc).__name__}")
    print(f"{total_passed} validated, {total_failed} invalid")

    texts = dict(zip((str(job.url) for job in candidates), await fetch_texts(candidates)))
    for url, text in texts.items():
        if isinstance(text, Exception):
            print(f"    could not fetch {url}: {type(text).__name__}")
    fetched = sum(not isinstance(text, Exception) for text in texts.values())

    prompt_sha, _ = prompt_snapshot()
    with Session(engine) as session:
        before = extracted(session, settings.openai_model, prompt_sha)
    todo, pending_count = pending_extractions(texts, ids, before, settings.llm_max_postings)
    print(
        f"{len(candidates)} candidates, {fetched - pending_count} already extracted with "
        f"{settings.openai_model} and prompt {prompt_sha}, {pending_count} need the model, "
        f"sending {len(todo)} (LLM_MAX_POSTINGS={settings.llm_max_postings})"
    )

    started = time.perf_counter()
    summaries = await extract_batch(todo)
    wall = time.perf_counter() - started

    done = {url: r for url, r in summaries.items() if not isinstance(r, Exception)}
    errors = {url: r for url, r in summaries.items() if isinstance(r, Exception)}

    with Session(engine) as session, session.begin():
        session.add_all(
            Extraction(
                posting_id=ids[url],
                text=todo[url],
                text_sha256=sha256(todo[url]),
                model=settings.openai_model,
                prompt_sha=prompt_sha,
                facts=response.output_parsed.model_dump(mode="json"),
            )
            for url, (response, _) in done.items()
        )

    print(f"\n{len(done)}/{len(summaries)} summarized in {wall:.1f}s")
    for url, exc in errors.items():
        code = getattr(exc, "code", None) or ""
        print(f"    failed {url}: {type(exc).__name__} {code}")
    by_url = {str(job.url): job for job in candidates}
    for url, (response, _) in done.items():
        facts = response.output_parsed
        print(f"\n{by_url[url].title}")
        show(facts)

    if len(done) < 2:
        return

    costs = [cost_usd(response.usage, response.model) for response, _ in done.values()]
    usages = [response.usage for response, _ in done.values()]
    print(
        f"\ntokens: {sum(u.input_tokens for u in usages)} in "
        f"({sum(u.input_tokens_details.cached_tokens for u in usages)} cached), "
        f"{sum(u.output_tokens for u in usages)} out "
        f"({sum(u.output_tokens_details.reasoning_tokens for u in usages)} reasoning)"
    )
    latencies = [seconds for _, seconds in done.values()]
    p95 = statistics.quantiles(latencies, n=20)[-1]

    mean_cost = statistics.mean(costs)
    print(
        f"cost: ${sum(costs):.6f} total, ${mean_cost:.6f} mean, "
        f"${mean_cost * len(candidates):.6f} projected for {len(candidates)} candidates"
    )
    print(
        f"latency: p50 {statistics.median(latencies):.2f}s, p95 {p95:.2f}s, "
        f"sum {sum(latencies):.1f}s, wall {wall:.1f}s"
    )

    facts = [response.output_parsed for response, _ in done.values()]
    print(f"japanese: {dict(Counter(f.japanese_required for f in facts))}")
    print(f"remote:   {dict(Counter(f.remote_policy for f in facts))}")


async def ingest_url(url: str) -> None:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as http:
        job = JobPosting.model_validate(await fetch_url(http, url))
        print(f"{job.title} [{job.source}:{job.token}]")
        print(f"{len(job.description)} chars of posting text")

        llm = openai_client()
        text = await model_input(http, job)
        response, seconds = await extract_one(llm, asyncio.Semaphore(1), text)

    show(response.output_parsed)
    print(f"{response.usage.input_tokens} input tokens, ${cost_usd(response.usage, response.model):.6f}, {seconds:.1f}s")


def main() -> None:
    if len(sys.argv) > 1:
        asyncio.run(ingest_url(sys.argv[1]))
    else:
        asyncio.run(amain())

