import asyncio
import html
import httpx
import re
import statistics
import time

from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, HttpUrl
from openai import AsyncOpenAI
from openai.types.responses import ParsedResponse, Response
from typing import Literal

from kansei.config import settings
from kansei.llm import PostingFacts, extract, cost_usd
from kansei.sources import SOURCES, fetch_posting


class JobPosting(BaseModel):
    source: Literal["greenhouse", "lever"]
    token: str
    id: str
    title: str
    url: HttpUrl
    posted_at: datetime
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


async def extract_one(
    http: httpx.AsyncClient,
    llm: AsyncOpenAI,
    limit: asyncio.Semaphore,
    job: JobPosting,
) -> tuple[ParsedResponse[PostingFacts], float]:
    async with limit:
        posting = job.description or await fetch_posting(http, job.token, job.id)
        started = time.perf_counter()
        response = await extract(llm, posting)
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
    return {job.id: result for (_, job), result in zip(selected, results)}


async def amain() -> None:
    started = time.perf_counter()
    results = await fetch_all(settings.boards)
    elapsed = time.perf_counter() - started

    boards = {t: r for t, r in results.items() if not isinstance(r, Exception)}
    failed = {t: r for t, r in results.items() if isinstance(r, Exception)}

    total_passed, total_failed = 0, 0
    candidates: list[JobPosting] = []

    for token, jobs in boards.items():
        passed_jobs, failed_jobs = validate(jobs)
        total_passed += len(passed_jobs)
        total_failed += len(failed_jobs)
        candidates += [(token, job) for job in passed_jobs if is_candidate(job)]
        
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

    print(f"\n{len(done)}/{len(summaries)} summarised in {wall:.1f}s")
    for job_id, exc in errors.items():
        code = getattr(exc, "code", None) or ""
        print(f"  failed {job_id}: {type(exc).__name__} {code}")
    if len(done) < 2:
        return

    costs = [cost_usd(response.usage) for response, _ in done.values()]
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
    needs_jp = sum(1 for f in facts if f.japanese_required == "yes")
    remote = sum(1 for f in facts if f.remote_allowed)
    print(f"{needs_jp}/{len(facts)} require Japanese, {remote}/{len(facts)} allow remote")


def main() -> None:
    asyncio.run(amain())

