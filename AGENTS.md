# kansei

A job board for engineers in Japan, filled from companies' Greenhouse and Lever boards. The
ingest (`uv run kansei`) fetches postings, keeps the Japan engineering candidates, and sends new
or changed ones to OpenAI for extraction. The web app (`uv run fastapi dev` plus `web/`) shows
them.

## Done means green

A change is done when all of these pass:

    uv run ruff check --fix .
    uv run pytest -q
    uv run alembic check                       # when db.py or migrations/ changed
    cd web && npm run build && npm run lint    # when web/ changed

Tests use the local compose database (`docker compose up -d db`, then
`uv run alembic upgrade head`). A fresh worktree needs `cp .env.example .env` first. Tests that
touch the database take the `session` fixture, which rolls back.

## Conventions

- Tests cover deterministic code: pure functions, and what the code sends to a model or does with
  its answer. The model's answers are measured by `kansei-eval`. In pytest, fake the network with
  `httpx.MockTransport` and the model with a stub client.
- A test pins the exact result (`==` on the whole list or value), so a plausible wrong
  implementation fails it.
- A column with a fixed set of values is a `Literal` plus a `CheckConstraint`, like
  `Tracked.status`. Alembic autogenerate misses a changed CHECK, so changing the `Literal` needs a
  hand-written migration step.
- Migrations start from `uv run alembic revision --autogenerate -m "..."`, then get read and
  edited.
- Posting text belongs to the employers. Commits, issues, PRs and docs quote short lines at
  most, and `evals/postings.jsonl` stays gitignored.
- `uv run kansei` and `uv run kansei-eval run` make paid OpenAI calls. To try the ingest, run
  `LLM_MAX_POSTINGS=0 uv run kansei`. Ask before running anything that reaches the model.
- Ask before adding a dependency.

## Git and pull requests

- One issue per branch and per pull request. Branch from an up-to-date `main`, named for the
  issue (`12-cap-counts-uncached`), and commit there.
- Commit subjects are plain imperative sentences, like `Track postings per user`.
- Open the PR with `gh pr create`, with `Closes #N` in the body.
- Write the PR description as a reading order: the tests first, then the core change, then the
  plumbing. Name the lines most likely to be wrong.
- A mechanical change (a rename, a move, formatting) gets its own PR, apart from logic changes.
- I review and merge every PR, and I release (`scripts/release.sh`) myself.

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `thomaslgrega/kansei`, used through the `gh` CLI. See
`docs/agents/issue-tracker.md`.

### Triage labels

The default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`,
`wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
