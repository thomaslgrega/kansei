import asyncio
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
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from kansei.config import settings
from kansei.db import Posting, engine
from kansei.llm import PostingFacts, cost_usd, extract
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


def is_candidate(job: JobPosting) -> bool:
    engineering = re.compile(r"engineer|developer|エンジニア|開発", re.IGNORECASE)
    reachable = re.compile(r"japan|tokyo|remote|日本|東京", re.IGNORECASE)
    return bool(engineering.search(job.title) and reachable.search(job.location))


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


def save_postings(session: Session, jobs: list[JobPosting], seen_at: datetime) -> None:
    if not jobs: 
        return

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
    )
    session.execute(statement)


def show(facts: PostingFacts) -> None:
    print(f"  japanese: {facts.japanese_required}, level {facts.japanese_level}, jlpt {facts.jlpt}")
    print(f"            {facts.japanese_as_written or '(says nothing)'}")
    print(f"  remote:   {facts.remote_policy}")
    print(f"  skills:   {', '.join(facts.must_have_skills) or '(none)'}")
    print(f"  summary:  {facts.role_summary}")


async def model_input(http: httpx.AsyncClient, job: JobPosting) -> str:
    posting = job.description or await fetch_posting(http, job.token, job.id)
    return f"{job.title}\n\n{posting}"


async def extract_one(
    http: httpx.AsyncClient,
    llm: AsyncOpenAI,
    limit: asyncio.Semaphore,
    job: JobPosting,
) -> tuple[ParsedResponse[PostingFacts], float]:
    async with limit:
        text = await model_input(http, job)
        started = time.perf_counter()
        response = await extract(llm, text)
        return response, time.perf_counter() - started


async def extract_batch(
    selected: list[JobPosting],
) -> dict[str, tuple[ParsedResponse[PostingFacts], float] | Exception]:
    limit = asyncio.Semaphore(settings.llm_concurrency)
    llm = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.llm_timeout,
    )
    async with httpx.AsyncClient(timeout=settings.request_timeout) as http:
        results = await asyncio.gather(
            *(extract_one(http, llm, limit, job) for job in selected),
            return_exceptions=True,
        )
    return {job.id: result for job, result in zip(selected, results)}


async def amain() -> None:
    started = time.perf_counter()
    results = await fetch_all(settings.boards)
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
    candidates = [job for job in postings if is_candidate(job)]

    with Session(engine) as session, session.begin():
        save_postings(session, postings, datetime.now(UTC))
        
    total = total_passed + total_failed
    print(f"{total} jobs from {len(boards)}/{len(results)} boards in {elapsed:.2f}s")
    for token, exc in failed.items():
        print(f"  skipped {token}: {type(exc).__name__}")
    print(f"{total_passed} validated, {total_failed} invalid")

    selected = candidates[: settings.llm_max_postings]
    print(f"{len(candidates)} candidates, sending {len(selected)} to {settings.openai_model}")

    started = time.perf_counter()
    summaries = await extract_batch(selected)
    wall = time.perf_counter() - started

    done = {i: r for i, r in summaries.items() if not isinstance(r, Exception)}
    errors = {i: r for i, r in summaries.items() if isinstance(r, Exception)}

    print(f"\n{len(done)}/{len(summaries)} summarized in {wall:.1f}s")
    for job_id, exc in errors.items():
        code = getattr(exc, "code", None) or ""
        print(f"  failed {job_id}: {type(exc).__name__} {code}")
    by_id = {job.id: job for job in selected}
    for job_id, (response, _) in done.items():
        facts = response.output_parsed
        print(f"\n{by_id[job_id].title}")
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

        llm = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.llm_timeout,
        )
        response, seconds = await extract_one(http, llm, asyncio.Semaphore(1), job)

    show(response.output_parsed)
    print(f"{response.usage.input_tokens} input tokens, ${cost_usd(response.usage, response.model):.6f}, {seconds:.1f}s")


def main() -> None:
    if len(sys.argv) > 1:
        asyncio.run(ingest_url(sys.argv[1]))
    else:
        asyncio.run(amain())

