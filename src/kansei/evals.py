import asyncio
import hashlib
import random
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import httpx
from pydantic import BaseModel

from kansei import JobPosting, fetch_all, is_candidate, model_input, validate
from kansei.config import settings
from kansei.llm import JapaneseLevel, JapaneseRequired, Jlpt, RemotePolicy, Seniority
from kansei.sources import fetch_url

EVALS = Path(__file__).resolve().parents[2] / "evals"
POSTINGS = EVALS / "postings.jsonl"
MANIFEST = EVALS / "manifest.jsonl"
LABELS = EVALS / "labels.jsonl"

IN_JAPAN = re.compile(r"japan|tokyo|日本|東京", re.IGNORECASE)
MARK = re.compile(
    r"japanese|日本語|jlpt|remote|hybrid|on-?site|office|リモート|在宅|出社|ハイブリッド"
    r"|senior|junior|staff|principal|シニア|ジュニア",
    re.IGNORECASE,
)


class FrozenPosting(BaseModel):
    url: str
    title: str
    text: str
    frozen_at: datetime


class ManifestEntry(BaseModel):
    url: str
    title: str
    chars: int
    sha256: str
    frozen_at: datetime


class Label(BaseModel):
    url: str
    seniority: Seniority
    japanese_required: JapaneseRequired
    japanese_level: JapaneseLevel
    jlpt: Jlpt
    remote_policy: RemotePolicy


def add_new(frozen: list[FrozenPosting], fetched: list[FrozenPosting]) -> list[FrozenPosting]:
    seen = {posting.url for posting in frozen}
    new = {posting.url: posting for posting in fetched if posting.url not in seen}
    return frozen + list(new.values())


def manifest_entry(posting: FrozenPosting) -> ManifestEntry:
    return ManifestEntry(
        url=posting.url,
        title=posting.title,
        chars=len(posting.text),
        sha256=hashlib.sha256(posting.text.encode("utf-8")).hexdigest(),
        frozen_at=posting.frozen_at,
    )


def write_manifest() -> None:
    postings = load(POSTINGS, FrozenPosting)
    save(MANIFEST, [manifest_entry(posting) for posting in postings])
    print(f"{len(postings)} postings in {MANIFEST.name}")


def load[T: BaseModel](path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [model.model_validate_json(line) for line in lines if line.strip()]


def save(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(exist_ok=True)
    path.write_text("".join(r.model_dump_json() + "\n" for r in records), encoding="utf-8")


async def freeze(urls: list[str]) -> None:
    results = await fetch_all(settings.boards)
    jobs = [job for r in results.values() if not isinstance(r, Exception) for job in validate(r)[0]]
    in_japan = [job for job in jobs if is_candidate(job) and IN_JAPAN.search(job.location)]
    random.Random(17).shuffle(in_japan)

    async with httpx.AsyncClient(timeout=settings.request_timeout) as http:
        pasted = [JobPosting.model_validate(await fetch_url(http, url)) for url in urls]
        selected = in_japan + pasted
        texts = await asyncio.gather(*(model_input(http, job) for job in selected))

    now = datetime.now(UTC)
    fetched = [
        FrozenPosting(url=str(job.url), title=job.title, text=text, frozen_at=now)
        for job, text in zip(selected, texts)
    ]
    frozen = load(POSTINGS, FrozenPosting)
    merged = add_new(frozen, fetched)
    save(POSTINGS, merged)
    print(f"{len(merged) - len(frozen)} new, {len(frozen)} already frozen, {len(merged)} in {POSTINGS.name}")
    write_manifest()


def ask(field: str, values: tuple[str, ...]) -> str:
    options = "  ".join(f"{i}={value}" for i, value in enumerate(values, 1))
    while True:
        answer = input(f"{field}   {options}\n> ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(values):
            return values[int(answer) - 1]


def label(urls: list[str]) -> None:
    fields = {name: get_args(f.annotation) for name, f in Label.model_fields.items() if name != "url"}
    done = {label.url for label in load(LABELS, Label)}
    todo = [p for p in load(POSTINGS, FrozenPosting) if p.url not in done and (not urls or p.url in urls)]

    for posting in todo:
        print("\n" + "=" * 72)
        for line in posting.text.splitlines():
            print(("» " if MARK.search(line) else "  ") + line)
        print(f"\n{posting.url}")
        answers = {name: ask(name, values) for name, values in fields.items()}
        with LABELS.open("a", encoding="utf-8") as f:
            f.write(Label(url=posting.url, **answers).model_dump_json() + "\n")
        done.add(posting.url)
        print(f"saved: {len(done)} labeled")


def main() -> None:
    match sys.argv[1:]:
        case ["freeze", *urls]:
            asyncio.run(freeze(urls))
        case ["manifest"]:
            write_manifest()
        case ["label", *urls]:
            try:
                label(urls)
            except (KeyboardInterrupt, EOFError):
                print("\nstopped. Every label you finished is saved.")
        case _:
            sys.exit("usage: kansei-eval freeze [URL ...] | kansei-eval label [URL ...] | kansei-eval manifest")