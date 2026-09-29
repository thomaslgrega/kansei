import asyncio
import hashlib
import json
import random
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel

from kansei import JobPosting, fetch_all, is_candidate, model_input, validate
from kansei.config import settings
from kansei.llm import (
    INSTRUCTIONS,
    JapaneseLevel,
    JapaneseRequired,
    Jlpt,
    PostingFacts,
    RemotePolicy,
    Seniority,
    cost_usd,
    extract,
)
from kansei.sources import fetch_url

EVALS = Path(__file__).resolve().parents[2] / "evals"
POSTINGS = EVALS / "postings.jsonl"
MANIFEST = EVALS / "manifest.jsonl"
LABELS = EVALS / "labels.jsonl"
RUNS = EVALS / "runs"
PROMPTS = EVALS / "prompts"

IN_JAPAN = re.compile(r"japan|tokyo|日本|東京", re.IGNORECASE)
MARK = re.compile(
    r"japanese|日本語|jlpt|remote|hybrid|on-?site|office|リモート|在宅|出社|ハイブリッド|オフィス|勤務"
    r"|senior|junior|staff|principal|シニア|ジュニア"
    r"|qualifications|nice to have|what you.ll need|必須条件|歓迎条件",
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
    must_have_skills: list[str] | None = None

FIELDS = [name for name in Label.model_fields if name not in {"url", "must_have_skills"}]


def score(labels: list[Label], predictions: list[Label]) -> dict[str, list[str]]:
    predicted = {p.url: p for p in predictions}
    missing = [label.url for label in labels if label.url not in predicted]
    if missing:
        raise ValueError(f"no prediction for {', '.join(missing)}")
    return {
        field: [
            label.url for label in labels
            if getattr(label, field) != getattr(predicted[label.url], field)
        ]
        for field in FIELDS
    }


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


def ask_skills(text: str) -> list[str]:
    while True:
        answer = input("must_have_skills    comma-separated, exactly as written, empty for none\n ")
        skills = [skill.strip() for skill in re.split(r"[,、，]", answer) if skill.strip()]
        missing = [skill for skill in skills if skill not in text]
        if not missing:
            return skills
        print(f"not in the posting as written: {', '.join(missing)}")


async def predict(llm: AsyncOpenAI, limit: asyncio.Semaphore, posting: FrozenPosting) -> tuple[Label, float]:
    async with limit:
        response = await extract(llm, posting.text)
        facts = response.output_parsed.model_dump(include=set(FIELDS))
        return Label(url=posting.url, **facts), cost_usd(response.usage, response.model)


async def run() -> None:
    labeled = {label.url for label in load(LABELS, Label)}
    postings = [p for p in load(POSTINGS, FrozenPosting) if p.url in labeled]
    llm = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value(), timeout=settings.llm_timeout)
    limit = asyncio.Semaphore(settings.llm_concurrency)
    results = await asyncio.gather(*(predict(llm, limit, p) for p in postings))

    sha, prompt = prompt_snapshot()
    PROMPTS.mkdir(parents=True, exist_ok=True)
    (PROMPTS / f"{sha}.json").write_text(prompt + "\n", encoding="utf-8")
    path = RUNS / f"{datetime.now(UTC):%Y-%m-%dT%H%M%S}-{settings.openai_model}-{sha}.jsonl"
    save(path, [prediction for prediction, _ in results])
    print(f"{len(results)} postings, ${sum(cost for _, cost in results):.4f}, saved {path.name}")


def print_posting(posting: FrozenPosting) -> None:
    print("\n" + "=" * 72)
    for line in posting.text.splitlines():
        print(("» " if MARK.search(line) else "  ") + line)
    print(f"\n{posting.url}")


def show(urls: list[str]) -> None:
    for posting in load(POSTINGS, FrozenPosting):
        if posting.url in urls:
            print_posting(posting)


def report(run: Path) -> None:
    predicted = {p.url: p for p in load(run, Label)}
    everything = load(LABELS, Label)
    labels = [label for label in everything if label.url in predicted]
    wrong = score(labels, list(predicted.values()))
    titles = {entry.url: entry.title for entry in load(MANIFEST, ManifestEntry)}
    n = len(labels)

    print(f"{run.name} against {n} of {len(everything)} labels\n")
    for field, urls in wrong.items():
        value, count = Counter(getattr(label, field) for label in labels).most_common(1)[0]
        right = n - len(urls)
        print(f"{field:18} {right:2}/{n}    {right / n:4.0%}    always {value}: {count / n:4.0%}")

    by_url = {label.url: label for label in labels}
    for field, urls in wrong.items():
        for url in urls:
            print(f"\n{field}: you {getattr(by_url[url], field)}, model {getattr(predicted[url], field)}")
            print(f"  {titles[url]}\n  {url}")


def prompt_snapshot() -> tuple[str, str]:
    text = json.dumps(
        {"instructions": INSTRUCTIONS, "schema": PostingFacts.model_json_schema()},
        ensure_ascii=False,
        indent=2,
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], text


def label(urls: list[str]) -> None:
    fields = {name: get_args(Label.model_fields[name].annotation) for name in FIELDS}
    done = {label.url for label in load(LABELS, Label)}
    todo = [p for p in load(POSTINGS, FrozenPosting) if p.url not in done and (not urls or p.url in urls)]

    for posting in todo:
        print_posting(posting)
        answers = {name: ask(name, values) for name, values in fields.items()}
        answers["must_have_skills"] = ask_skills(posting.text)
        with LABELS.open("a", encoding="utf-8") as f:
            f.write(Label(url=posting.url, **answers).model_dump_json() + "\n")
        done.add(posting.url)
        print(f"saved: {len(done)} labeled")


def label_skills(urls: list[str]) -> None:
    labels = {label.url: label for label in load(LABELS, Label)}
    todo = [
        p for p in load(POSTINGS, FrozenPosting)
        if p.url in labels and labels[p.url].must_have_skills is None and (not urls or p.url in urls)
    ]

    for posting in todo:
        print_posting(posting)
        labels[posting.url].must_have_skills = ask_skills(posting.text)
        save(LABELS, list(labels.values()))
        done = sum(label.must_have_skills is not None for label in labels.values())
        print(f"saved: {done} of {len(labels)} have skills")


def main() -> None:
    match sys.argv[1:]:
        case ["freeze", *urls]:
            asyncio.run(freeze(urls))
        case ["manifest"]:
            write_manifest()
        case ["run"]:
            asyncio.run(run())
        case ["score"]:
            report(max(RUNS.glob("*.jsonl")))
        case ["score", path]:
            report(Path(path))
        case ["show", *urls]:
            show(urls)
        case ["label", *urls]:
            try:
                label(urls)
            except (KeyboardInterrupt, EOFError):
                print("\nstopped. Every label you finished is saved.")
        case ["skills", *urls]:
            try:
                label_skills(urls)
            except (KeyboardInterrupt, EOFError):
                print("\nstopped. Every posting you finished is saved.")
        case _:
            sys.exit("usage: kansei-eval freeze [URL ...] | label [URL ...] | skills [URL ...] | manifest | run | score [RUN] | show URL ...")