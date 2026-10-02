# Kansei

Kansei is a Python CLI that reads engineering job postings in Japanese and English. I'm building it for my own job search in Japan, where I want to quickly find the skills, Japanese level, and work arrangements a role requires.

## What it does

- Reads postings from Greenhouse, Lever, or a job page URL.
- Removes HTML and converts each source into the same posting format, checked with Pydantic.
- Uses OpenAI structured outputs to extract a role summary, seniority, required skills, Japanese requirements, and remote work policy.
- Processes several postings at a time, limits concurrent requests, and reports failures for individual postings.
- Reports API cost and median and p95 request times.

## Run it

You'll need Python 3.13, [uv](https://docs.astral.sh/uv/), and an OpenAI API key.

```sh
git clone https://github.com/thomaslgrega/kansei.git
cd kansei
cp .env.example .env
# Add your OPENAI_API_KEY to .env
uv sync
```

To read one posting, replace the example URL with a real job posting:

```sh
uv run kansei "https://jobs.lever.co/company/posting-id"
```

To read the configured job boards, start with a small limit:

```sh
LLM_MAX_POSTINGS=5 uv run kansei
```

These commands make paid OpenAI API calls. The boards, model, request limits, and timeouts are set in [config.py](src/kansei/config.py).

## Evaluation

I label postings by hand and compare the model's answers with those labels. Seniority, Japanese requirements, and remote policy are scored by field. Required skills are scored with precision, recall, and F1, using exact skill names.

Each posting is saved as the exact text sent to the model. Freezing more postings adds new ones without changing existing text. The labeling rules live in [llm.py](src/kansei/llm.py), so the model and I use the same definitions. Each run saves its answers and a hash of the instructions and schema, with a copy of that prompt saved separately.

### Current results

As of October 1, 2026, the development set has 24 labeled postings with 104 required skill names. After reviewing errors, I changed two rules: split slash-joined software names into separate items, and leave out a bare "Shell" because it doesn't name a specific shell.

| Prompt | Skills F1 in each run |
| --- | --- |
| Before the rule changes (`a6e2b6c3`) | 93.1%, 92.8% |
| After the rule changes (`a56fba4b`) | 98.6%, 100.0%, 100.0% |

These are micro-F1 scores: matches, extra names, and missed names are counted across all 24 postings before calculating the score. I repeat runs to see how much the model's answers vary.

These postings helped shape the rules, so the scores show improvement on the development set. They don't yet show how well the rules work on new postings. Another 12 postings from four different companies are frozen as a held-out set. They haven't been labeled or scored in the current repo.

### Saved data and commands

The repo includes:

- `evals/manifest.jsonl`: posting URLs, titles, text lengths, SHA-256 hashes, freeze dates, and development or held-out split.
- `evals/labels.jsonl`: my labels.
- `evals/prompts/`: saved instructions and schemas.
- `evals/runs/`: model answers from each run.

The full posting text stays in a local, gitignored file, `evals/postings.jsonl`. It isn't published because the employers wrote it. Tests check that the local text matches the manifest and that development runs contain no held-out postings.

To check the saved results without making API calls:

```sh
uv run kansei-eval score
uv run kansei-eval compare a6e2b6c3 a56fba4b
```

With the local posting text and labels, you can make a new model run:

```sh
uv run kansei-eval run
uv run kansei-eval score
```

The `run` command makes paid API calls. Cloning the repo gives you the saved results, but not the full posting text needed to repeat those calls.

## Tests

```sh
uv run pytest
uv run ruff check .
```

The tests cover parsing, validation, the code around model calls, cost calculations, and evaluation scoring. Model answers are checked through the evaluations above.

## What's next

Kansei is currently a CLI. Next are labeling and scoring the held-out postings, then adding storage and a web interface.
