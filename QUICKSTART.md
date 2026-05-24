# Quick Start

Minimal happy path to get the full stack running locally. For deeper troubleshooting, see [`TESTING_GUIDE.md`](TESTING_GUIDE.md) or [`docs/SETUP_CHECKLIST.md`](docs/SETUP_CHECKLIST.md).

## Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.11+**
- **Node.js 20+** and **npm**
- An **OpenAI API key** (the LLM-backed agents won't run without it; non-LLM tests still pass)

## 1. Configure env

```bash
# From the repo root — single monorepo template, copied to .env
cp .env.example .env
# Edit .env: paste your real OPENAI_API_KEY. Optionally set USDA_API_KEY,
# LANGSMITH_API_KEY, etc. Defaults are fine for local dev.
```

The API reads `<repo-root>/.env` first, falling back to a legacy `apps/api/.env` if you have one. New developers only need root `.env`.

## 2. Start infrastructure (Postgres + Grafana + Tempo + Loki)

```bash
cd infra/docker
docker-compose up -d
docker-compose ps     # all four containers should be Up
```

## 3. Backend — install, migrate, seed, embed

```bash
cd ../../apps/api
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt

alembic upgrade head                # applies migrations 001–004
python scripts/seed_recipes.py      # 20 seed recipes
python scripts/embed_recipes.py     # one-time: populates pgvector embeddings
```

## 4. Run the API

```bash
# Still in apps/api with .venv active
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

Access:
- API: <http://localhost:4000>
- Swagger UI: <http://localhost:4000/docs>
- Liveness: <http://localhost:4000/health>
- Readiness (DB ping): <http://localhost:4000/readiness>

## 5. Run the frontend

In a new terminal:

```bash
cd apps/web
cp .env.local.example .env.local    # exposes NEXT_PUBLIC_API_URL
npm install
npm run dev
```

Open <http://localhost:3000> — the form is wired to `POST /api/v1/recommendations` and renders all six response fields with loading and error states.

## 6. Smoke-test the API

```bash
# Single-recipe suggestion
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"chicken and rice dinner"}' | jq '.recommendations[].name'

# 3-day menu plan + grocery list
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message":"3-day dinner menu with chicken and rice",
    "available_ingredients":["chicken","rice"],
    "days":3
  }' | jq '{
      recipes:[.recommendations[].name],
      days:(.menu_plan.days|length),
      grocery:.grocery_list.total_items,
      warnings
    }'
```

Also available:
- `POST /api/v1/auth/api-keys` — issue an API key (consumers send `X-API-Key`, enforcement gated by `REQUIRE_AUTH=true`)
- `POST /api/v1/feedback` — rate a previous response 1–5 stars via its `trace_id`

## Alternative — full stack in Docker

If you prefer everything containerized (API + web + Promtail log shipper joining the infra services):

```bash
cd infra/docker
docker-compose --profile apps up -d --build
```

Then open the same URLs. Promtail will start scraping container stdout and shipping to Loki.

## Observability

- Grafana: <http://localhost:3001> (admin/admin)
  - Tempo datasource — traces (`service=recipe-api`)
  - Loki datasource — logs (only populated when running via `--profile apps`; see [README → Observability Stack](README.md#observability-stack))

## Run the test suite

```bash
cd apps/api && source .venv/bin/activate
pytest -m "not integration" -v      # fast unit tests, no API keys required
pytest -v                           # full suite; integration tests skip cleanly without OPENAI_API_KEY
```

## Stop everything

```bash
# Frontend / API: Ctrl-C in their terminals
# Infra:
cd infra/docker && docker-compose down
# Full stack (apps profile):
docker-compose --profile apps down
```

## Need help?

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** — endpoint-by-endpoint walkthroughs, observability checks, common errors
- **[docs/SETUP_CHECKLIST.md](docs/SETUP_CHECKLIST.md)** — exhaustive setup verification with expected outputs
- **[README.md](README.md)** — architecture, features, agent details
