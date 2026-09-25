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

Kansei is currently a CLI. Next I'm building a labeled evaluation set to measure extraction accuracy, followed by storage and a web interface.
