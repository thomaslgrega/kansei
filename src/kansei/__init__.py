import asyncio
import httpx
import time
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError, HttpUrl


class Location(BaseModel):
    name: str

class JobPosting(BaseModel):
    id: int
    title: str = Field(description="The title of the position")
    absolute_url: HttpUrl
    updated_at: datetime
    location: Location
    education: str | None = None


COMPANIES = ["stripe", "anthropic", "figma", "airtable", "discord", "gitlab", "ramp"]


async def fetch_board(client: httpx.AsyncClient, token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
    response = await client.get(url)
    response.raise_for_status()
    return response.json()["jobs"]


async def fetch_all(tokens: list[str]) -> dict[str, list[dict] | Exception]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        results = await asyncio.gather(
            *(fetch_board(client, token) for token in tokens),
            return_exceptions=True,
        )
    return dict(zip(tokens, results))


def validate(jobs: list[dict]) -> tuple[list[JobPosting], list[tuple[int, str]]]:
    passed, failed = [], []
    for job in jobs:
        try:
            passed.append(JobPosting.model_validate(job))
        except ValidationError as exc:
            failed.append((job.get("id", -1), exc.errors()[0]["msg"]))
    return passed, failed


async def amain() -> None:
    started = time.perf_counter()
    results = await fetch_all(COMPANIES)
    elapsed = time.perf_counter() - started

    boards = {t: r for t, r in results.items() if not isinstance(r, Exception)}
    failed = {t: r for t, r in results.items() if isinstance(r, Exception)}

    total_passed, total_failed = 0, 0

    for _, jobs in boards.items():
        passed_jobs, failed_jobs = validate(jobs)
        total_passed += len(passed_jobs)
        total_failed += len(failed_jobs)
        
    total = total_passed + total_failed
    print(f"{total} jobs from {len(boards)}/{len(results)} boards in {elapsed:.2f}s")
    for token, exc in failed.items():
        print(f"  skipped {token}: {type(exc).__name__}")
    print(f"{total_passed} validated, {total_failed} invalid")


def main() -> None:
    asyncio.run(amain())

