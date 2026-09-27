# Kansei

Kansei is a small Python tool I'm building to make engineering job postings in Japan easier to understand, whether they're written in Japanese or English. It started with a practical question from my own job search: what does a posting actually require, and is it a role I can apply for?

## What it does

- Reads postings from public Greenhouse and Lever boards, or from a job page URL you provide.
- Cleans up HTML and brings the different sources into one validated posting format. For job pages, it also uses `JobPosting` structured data when available.
- Uses OpenAI structured output to extract a role summary, seniority, required skills, Japanese language requirements, and remote work availability.
- Processes board postings concurrently and reports API cost and latency.

## Run it

You'll need Python 3.13, [uv](https://docs.astral.sh/uv/), and an OpenAI API key.

```sh
cp .env.example .env
# Add your OPENAI_API_KEY to .env
uv sync
```

To try a single posting, replace this example with a public job posting URL:

```sh
uv run kansei "https://jobs.lever.co/company/posting-id"
```

To process the configured boards, start with a small limit:

```sh
LLM_MAX_POSTINGS=5 uv run kansei
```

These commands call the OpenAI API and may incur a charge. The default boards and other settings are in `src/kansei/config.py`.

## Evaluation

To measure extraction accuracy, I label postings by hand and compare the model's answers against those labels, field by field.

- **The input is frozen.** Job boards change daily: postings are edited or taken down. So every posting in the evaluation set is saved as the exact text the model reads, and freezing only ever adds new postings. It never replaces one that's already been labeled.
- **The labels follow written rules.** Each field has a fixed set of values, and each value has a rule for when it applies. The rules live in the schema descriptions in `src/kansei/llm.py`, so the model and I work from the same definitions.
- **The posting text isn't published.** Job postings are written by the companies that post them, so this repo doesn't redistribute them. What's here:
  - `evals/manifest.jsonl` lists every frozen posting: its URL, title, length, a SHA-256 hash of the exact text, and when it was frozen.
  - `evals/labels.jsonl` holds my labels.

  The frozen text (`evals/postings.jsonl`) is kept outside the repo. A test checks that the local copy matches the manifest's hashes, so the labels can't silently end up pointing at different text.

```sh
uv run kansei-eval freeze [URL ...]   # add Japan-located board postings, plus any URLs given
uv run kansei-eval label [URL ...]    # label unlabeled postings (all of them, or just the URLs given)
uv run kansei-eval manifest           # rebuild the manifest from the local frozen text
```

Kansei is currently a CLI. Next come the first accuracy scores, followed by storage and a web interface.
