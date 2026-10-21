# Kansei

Kansei is a Python CLI that reads engineering job postings in Japanese and English. I'm building it for my own job search in Japan, where I want to quickly find the skills, Japanese level, and work arrangements a role requires.

## What it does

- Reads postings from Greenhouse, Lever, or a job page URL.
- Removes HTML and converts each source into the same posting format, checked with Pydantic.
- Uses OpenAI structured outputs to extract a role summary, seniority, required skills, Japanese requirements, and remote work policy.
- Processes several postings at a time, limits concurrent requests, and reports failures for individual postings.
- Reports API cost and median and p95 request times.

## Run it

You'll need Python 3.13, [uv](https://docs.astral.sh/uv/), Docker, and an OpenAI API key.

```sh
git clone https://github.com/thomaslgrega/kansei.git
cd kansei
cp .env.example .env
# Add your OPENAI_API_KEY to .env
uv sync
docker compose up -d --wait
uv run alembic upgrade head
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

Every run stores the fetched postings in Postgres, which runs locally from `compose.yaml`. A posting is identified by its URL, so running again updates the same rows: `first_seen_at` keeps the day it first appeared and `last_seen_at` moves to the latest run. `LLM_MAX_POSTINGS=0 uv run kansei` fetches and stores postings without calling the model.

Extractions are stored too, with the exact text the model read. A posting is sent to the model only when its text, the model or the prompt has changed since it was last extracted, so running again costs nothing for postings that haven't changed. `kansei-eval run` doesn't use this cache: every eval run calls the model, because repeated runs are how run-to-run variation is measured.

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

These postings helped shape the rules, so these scores show improvement on the development
set. They don't show how well the rules work on new postings. That's what the test set is
for.

### Test set

Twelve postings from four companies the rules were never written against: Mujin, Databricks, Datadog and PayPay Card, three from each. The postings were committed before I labeled them, and the labels were committed before any model run. The prompt was scored on them once, with three runs of `a56fba4b`.

| Set | Postings | Skills F1 in each run |
| --- | --- | --- |
| Development | 24 | 98.6%, 100.0%, 100.0% |
| Test | 12 | 94%, 94%, 94% |

In every run, the other fields matched my labels on 12 of 12 postings. Postings with a skills disagreement, out of 9 posting-runs per company: Mujin 0, Datadog 0, Databricks 1, PayPay Card 3.

The biggest cause of the gap was a case the rules didn't decide: whether hardware vendors count as required skills. Rescored with those vendors labeled the way the rule now says, the same three runs score 99%, 99%, 99%.

This is the number I report for `a56fba4b`. If I change a rule because of these errors, these 12 become development postings, and the next test number needs new postings.

### After the test set

I turned the test-set errors into four rule sentences: named hardware counts as a skill, a
required certification counts as the product it names, a company-wide hybrid statement means
hybrid, and Sr./Jr. mean senior and junior. Those decisions came from the 12 test-set
postings, so they are development postings now, and the development set has 36.

| Prompt | Postings | Skills F1 in each run |
| --- | --- | --- |
| `a56fba4b` | 24 | 98.6%, 100.0%, 100.0% |
| `c876fc21` | 36 | 99.0%, 99.0%, 99.0% |

The remaining errors are skills not being split (e.g. "MATLAB/Simulink" vs "MATLAB, Simulink") and ETL being added even though it is a process and not a tool. These errors are run-to-run variations.

`c876fc21` has no test number yet. The next one needs postings from companies the rules haven't seen, frozen and labeled before the next change I report.

### Saved data and commands

The repo includes:

- `evals/manifest.jsonl`: posting URLs, titles, text lengths, SHA-256 hashes, freeze dates, and development or test split.
- `evals/labels.jsonl`: my labels.
- `evals/prompts/`: saved instructions and schemas.
- `evals/runs/`: model answers from each run.

The full posting text stays in a local, gitignored file, `evals/postings.jsonl`. It isn't published because the employers wrote it. Tests check that the local text matches the manifest and that development runs contain no test-set postings.

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

## API

`uv run fastapi dev` serves a JSON API under `/api` at http://127.0.0.1:8000, with interactive documentation at `/docs`.

- `GET /api/postings` lists stored postings, newest first. Filter by board with `token`, and page with `limit` (up to 100) and `offset`.
- `GET /api/postings/{id}` returns one posting with its newest extraction for the configured model and prompt, or `null` if it hasn't been extracted.
- `POST /api/signup` and `POST /api/login` take `{"email", "password"}`. Passwords need at least 15 characters and are stored as Argon2id hashes. Login sets an `HttpOnly`, `Secure`, `SameSite=Lax` session cookie that lasts 14 days.
- `GET /api/me` returns the logged-in user, or 401. `POST /api/logout` deletes the session on the server, so a copied cookie stops working.
- `GET /api/me/tracked` lists the postings you're tracking, newest first. `POST /api/me/tracked` takes `{"posting_id", "status", "note"}`, `PATCH /api/me/tracked/{id}` changes the status or note, and `DELETE /api/me/tracked/{id}` stops tracking a posting. Status is one of `saved`, `applied`, `interviewing`, `offer`, `rejected`, and Postgres enforces it too. Another user's tracked posting returns the same 404 as one that doesn't exist.

## Web app

The frontend is a Vite + React + TypeScript app in `web/`. FastAPI serves the built app from the same origin as the API, so the session cookie works with no CORS setup.

```
cd web && npm install
npm run dev     # http://localhost:5173, proxies /api to the API on port 8000
npm run build   # writes web/dist, which uv run fastapi dev serves at http://127.0.0.1:8000
```

## Deploy

Kansei runs on Railway as one service built from the `Dockerfile`. A Node stage builds `web/dist`, a uv stage builds the virtual environment, and the final image, which has neither Node nor uv, runs `fastapi run`, which listens on the port Railway injects as `PORT` (8080). Postgres 18 with pgvector runs as a second service, from Railway's pgvector template.

- The app reaches Postgres over Railway's private network. `DATABASE_URL` is built from the database's private host, with the `postgresql+psycopg` scheme: `postgresql+psycopg://${{pgvector.PGUSER}}:${{pgvector.PGPASSWORD}}@${{pgvector.PGHOST_PRIVATE}}:${{pgvector.PGPORT_PRIVATE}}/${{pgvector.PGDATABASE}}`.
- Migrations run as the pre-deploy command, `alembic upgrade head`. If one fails, the new version doesn't start and the running one keeps serving.
- The public domain targets port 8080, the value of Railway's `PORT`. `railway up` deploys the working directory.

## Tests

```sh
uv run pytest
uv run ruff check .
```

The tests cover parsing, validation, the code around model calls, cost calculations, and evaluation scoring. Model answers are checked through the evaluations above.

## What's next

Kansei is a web app with an API, user accounts and per-user tracked postings, deployed on Railway with Postgres. Next is a sample workspace for visitors and signup in the web app.
