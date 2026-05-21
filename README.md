# Recipe AI System

An intelligent recipe management and recommendation system powered by AI agents, built with modern observability and scalability in mind.

## Architecture Overview

This is a monorepo project using a microservices architecture with AI orchestration, full-stack observability, and vector-based search capabilities.

### Tech Stack

#### Frontend
- **Next.js 14+** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling

#### Backend
- **FastAPI** - High-performance Python API framework
- **LangGraph** - AI agent orchestration and workflows
- **PostgreSQL** - Primary relational database
- **pgvector** - Vector embeddings for semantic search

#### Observability
- **OpenTelemetry** - Distributed tracing, metrics, and logs
- **Grafana** - Visualization and dashboards
- **Tempo** - Distributed tracing backend
- **Loki** - Log aggregation system
- **LangSmith** - LLM observability and tracing

## Project Structure

```
recipe-ai-system/
├── apps/
│   ├── web/              # Next.js frontend application
│   └── api/              # FastAPI backend application
├── packages/
│   └── shared/           # Shared types, utilities, and constants
├── infra/
│   ├── docker/           # Docker compose and container configs
│   ├── grafana/          # Grafana dashboards and config
│   ├── tempo/            # Tempo tracing configuration
│   └── loki/             # Loki logging configuration
├── docs/                 # Project documentation
├── .env.example          # Example environment variables
├── .gitignore           # Git ignore patterns
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose
- Git

### Quick Setup

For a comprehensive step-by-step setup guide with verification commands, see **[Setup Checklist](docs/SETUP_CHECKLIST.md)**.

**Quick start commands:**

```bash
# 1. Start infrastructure
cd infra/docker
docker-compose up -d

# 2. Setup and start backend
cd ../../apps/api
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_recipes.py
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

# 3. Setup and start frontend (in new terminal)
cd apps/web
npm install
npm run dev
```

**Access points:**
- **API**: http://localhost:4000 (docs at http://localhost:4000/docs)
- **Frontend**: http://localhost:3000
- **Grafana**: http://localhost:3001 (admin/admin)
- **PostgreSQL**: localhost:5432 (recipe_user/recipe_password)

### Verification

Quick verification that everything is working:

```bash
# Check API health
curl http://localhost:4000/health

# Check database
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'
# Should return: 20

# Test recommendations
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan meals for the week", "days": 7}'
```

For detailed verification steps and troubleshooting, see **[Setup Checklist](docs/SETUP_CHECKLIST.md)**.

### Detailed Setup Guides

For component-specific setup instructions:

- **Backend API**: See `apps/api/README.md`
- **Frontend**: See `apps/web/README.md`
- **Infrastructure**: See `infra/docker/README.md`

## Development Workflow

### Monorepo Structure

This project uses a monorepo structure to maintain:
- Shared code between frontend and backend
- Consistent tooling and configuration
- Simplified dependency management

### Observability Stack

The observability stack provides:
- **Distributed Tracing**: Track requests across services with Tempo
- **Log Aggregation**: Centralized logging with Loki
- **Metrics & Dashboards**: Visualization with Grafana
- **LLM Tracing**: Debug and optimize AI agents with LangSmith

## Features

### Current Features ✅

- **Recipe Database**: 20 seed recipes with Central Asian and international cuisines
- **AI-powered recommendations**: LangGraph workflow with 5 wired agents — `ingredient → retrieval → nutrition → menu_planner → grocery_list → final_response` — each with structured-output Pydantic schemas and deterministic fallbacks
- **RAG retrieval**: OpenAI embeddings + pgvector cosine similarity with HNSW index; deterministic re-ranking on cuisine/ingredient overlap; safety filters for excluded ingredients and dietary restrictions
- **Menu planning**: n-day plans with LLM-driven scheduling, requested meal types, and deterministic validation (restriction conflicts, consecutive-day repeats, day-count mismatches)
- **Grocery lists**: ingredient aggregation across the plan, deterministic categorization, plural/descriptor-aware matching for `already_available`, optional LLM quantity estimation with practical units
- **Nutrition estimates**: per-recipe macros + confidence + deterministic safety warnings for the user's stated restrictions
- **API Documentation**: Interactive Swagger UI and ReDoc
- **Observability Stack**:
  - Distributed tracing with OpenTelemetry and Tempo
  - Structured JSON logging with Loki
  - Grafana dashboards for visualization
  - Request ID tracking and trace correlation
- **Database**: PostgreSQL with pgvector extension and Alembic migrations
- **Next.js Frontend (scaffold only)**: App Router + Tailwind CSS skeleton at `apps/web/`. The recommendation form and API integration are not yet implemented — current `app/page.tsx` is the default Next.js landing page.

### In Progress 🚧

- Frontend-to-API integration (`apps/web` is currently a Next.js scaffold)
- Production hardening: containerization, rate limiting, CI/CD

### Planned 📋

- USDA FoodData Central integration wired into the Nutrition Agent for grounded estimates (client library is shipped; agent integration pending)
- Safety validation agent (deterministic checks are inlined into Nutrition and Menu agents today)
- User authentication and preferences
- Recipe CRUD operations
- Recipe ratings and reviews

## Nutrition Agent

The Nutrition Agent enriches each retrieved recipe with an estimated per-serving nutrition profile and safety warnings. The current workflow is:

```
START → ingredient_agent → recipe_retrieval → nutrition_agent → final_response → END
```

### What it produces

For every recipe returned by retrieval, the Nutrition Agent emits a structured `NutritionNote`:

- **Estimated macros per serving:** `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg` (any field may be `null`)
- **`health_notes`:** short, factual observations (e.g. "High in carbohydrates from rice.")
- **`warnings`:** restriction / allergen conflicts surfaced by the deterministic safety check **and** the LLM
- **`confidence`:** one of `"low" | "medium" | "high"` — typically `"low"` or `"medium"` because seed recipes don't carry exact ingredient quantities

A deduped human-readable summary is set on `response.nutrition_notes`. Structured per-recipe nutrition (full `NutritionNote` objects) is kept internally on `response.metadata` for server-side logging, tracing, and debugging only — it is not serialized in API responses.

### Important caveats

- **Values are estimates, not measurements.** The system prompt forbids precision claims; every `health_notes` block leads with the disclaimer:
  > _All nutritional values are rough estimates and not medical advice._
- **No medical advice.** The agent will not recommend specific health actions.
- **Allergens are not invented.** Warnings only surface ingredients the user explicitly flagged or that match the deterministic blocklist (pork, alcohol, gluten, dairy, nuts, shellfish, etc.).

### LLM fallback behavior

The Nutrition Agent is resilient: requests never fail because of a nutrition call.

- **No `OPENAI_API_KEY` set** → returns one low-confidence `NutritionNote` per recipe with `warnings: ["Estimation failed: OPENAI_API_KEY is not set …"]`. The deterministic safety check still runs.
- **Per-recipe LLM error (rate limit, transient 5xx, timeout)** → that one recipe gets a fallback note; the other recipes return normal estimates. One bad call never poisons the batch.
- **No recipes retrieved** → `nutrition_notes` is empty; no LLM call is issued.

### How to test the endpoint

Make sure the API is running, recipes are embedded (`python scripts/embed_recipes.py`), and `OPENAI_API_KEY` is set.

```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "halal weeknight dinner with chicken and rice",
    "available_ingredients": ["chicken", "rice"]
  }' \
  | jq '{
      names: [.recommendations[].name],
      nutrition_notes,
      warnings
    }'
```

Expected output:
- `nutrition_notes` is a non-empty string opening with the disclaimer
- `warnings` is `[]` (no pork in this query)
- Structured per-recipe nutrition (macros, confidence, warnings) is logged server-side; tail the API logs to inspect it

Restriction-warning test (deterministic check should fire even on close-call recipes):
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"pasta carbonara with bacon","dietary_restrictions":["no pork"]}' \
  | jq '.warnings'
```
Expect at least one entry containing `"Recipe may conflict with restriction: no_pork."` if any returned recipe contains pork-family ingredients.

Unit + integration test suite:
```bash
cd apps/api && source .venv/bin/activate && pytest -v
```
- `tests/test_nutrition_agent.py` — fallback path, deterministic safety warnings (no OpenAI required)
- `tests/test_recommendations_endpoint.py::test_recommendations_endpoint_exposes_nutrition_notes` — end-to-end (marked `integration`; skipped without `OPENAI_API_KEY`)

## Menu Planner Agent

The Menu Planner Agent turns the retrieved recipes into an n-day menu plan. It runs after retrieval and nutrition:

```
START → ingredient_agent → recipe_retrieval → nutrition_agent
      → menu_planner_agent → final_response → END
```

### What it does

- Reads `days` and `requested_meal_types` extracted by the Ingredient Agent (e.g. `"3-day dinner menu"` → `days=3`, `requested_meal_types=["dinner"]`).
- Asks the LLM (via `langchain-openai` structured output) to schedule retrieved recipes across the requested days using the requested meal types.
- Prefers cuisine matches and uses available ingredients earlier in the plan.
- Avoids placing the same recipe on consecutive days.
- Falls back to a deterministic round-robin if the LLM is unavailable or the structured output fails.
- Runs a **deterministic validator** on every plan (LLM or fallback) that adds warnings for: restricted-ingredient conflicts, excluded-ingredient conflicts, consecutive-day repeats, and day-count mismatches. The validator never mutates the plan — it surfaces issues in `menu_plan.warnings`.

### When the plan is produced

| Request | Result |
|---|---|
| `days` is `null` (default) and no multi-day intent in the message | `menu_plan: null` — recommendations only |
| `days` provided OR text says "week"/"weekly"/"N days" | LLM-built plan with `days` MenuDay entries |
| `days` provided but no recipes retrieved | `menu_plan` with `days: []` and a warning |
| LLM fails / unavailable | Deterministic round-robin fallback, warning attached |

### Example request

```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "3-day dinner menu with chicken and rice, no pork",
    "available_ingredients": ["chicken", "rice"],
    "days": 3
  }'
```

### Example response (trimmed)

```json
{
  "recommendations": [
    { "id": 1, "name": "Chicken Plov", "cuisine": "Central Asian" }
  ],
  "menu_plan": {
    "days": [
      {
        "day": 1,
        "meals": {
          "dinner": { "id": 1, "name": "Chicken Plov", "cuisine": "Central Asian" }
        }
      },
      { "day": 2, "meals": { "dinner": { "id": 2, "name": "Lagman" } } },
      { "day": 3, "meals": { "dinner": { "id": 3, "name": "Manti" } } }
    ],
    "total_days": 3,
    "servings": 2
  },
  "nutrition_notes": "All nutritional values are rough estimates and not medical advice. ...",
  "grocery_list": null,
  "warnings": []
}
```

`menu_plan` matches the existing API schema (`days[].meals` is a `dict[meal_type, RecipeRecommendation]`). The richer agent output — including `reason`, per-meal `notes`, the agent `summary`, and deterministic validation warnings — is retained server-side on `response.metadata` for logging, tracing, and debugging only; it is not serialized in the public API response. Safety-related warnings from the nutrition and menu validators are merged into the top-level `warnings` array.

### How to test with curl

**With explicit days:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "3-day dinner menu with chicken and rice, no pork",
    "available_ingredients": ["chicken", "rice"],
    "days": 3
  }' \
  | jq '{
      menu_days: (.menu_plan.days | length),
      first_day_meals: (.menu_plan.days[0].meals | keys),
      total_days: .menu_plan.total_days,
      warnings
    }'
```

**Inferred multi-day intent ("week"):**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"plan a week of healthy dinners with chicken and rice"}' \
  | jq '.menu_plan.days | length'
```
Expected: `7`.

**Multi-meal-type plan:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"plan breakfast lunch and dinner for 3 days"}' \
  | jq '.menu_plan.days[0].meals | keys'
```
Expected: `["breakfast","dinner","lunch"]` (alphabetical from `jq | keys`).

**No menu when no days requested:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"I have chicken and rice, what can I make for dinner?"}' \
  | jq '.menu_plan'
```
Expected: `null`.

### Current limitations

- **Menu planning runs only when `days` is provided** (explicitly via the API field or implied in the message like "week"/"weekly"/"5 days"). Recommendation-only requests skip the planner and `menu_plan` stays `null`.
- **No date assignments.** `MenuDay.date` is always `null`; only day numbers (1-based) are produced.
- **`meal_type` defaults to `"dinner"`** when retrieved recipes don't carry meal-type metadata. The `RetrievedRecipe` schema doesn't expose `meal_type` today.
- **The Menu Planner has full LLM fallback**, but the upstream Ingredient Agent does not — if `OPENAI_API_KEY` is missing the request fails with HTTP 500 before reaching the planner.

## Grocery List Agent

The Grocery List Agent runs after the Menu Planner and turns the planned recipes into a shopping list:

```
START → ingredient_agent → recipe_retrieval → nutrition_agent
      → menu_planner_agent → grocery_list_agent → final_response → END
```

### What it does

- **Aggregates ingredients** from every recipe referenced by the menu plan, deduped case-insensitively. Each item carries the recipe ids that use it.
- **Marks user-supplied ingredients as `already_available`** using a deterministic normalizer that handles plurals and common descriptors. `"chicken"` matches `"chicken thighs"`, `"rice"` matches `"long-grain rice"`, `"carrot"` matches `"carrots"`, etc.
- **Categorizes** items deterministically into `meat`, `vegetables`, `fruits`, `dairy`, `grains`, `pantry`, `spices`, or `other`.
- **Estimates quantities and units** via the LLM when `OPENAI_API_KEY` is configured. Allowed units are `kg`, `g`, `pcs`, `bunch`, `tbsp`, `tsp`, `liters`. Values are always labeled as estimates.
- **Falls back gracefully** if the LLM is unavailable: the list still appears, but `quantity` and `unit` are `null` and no estimate warning is added.

### When it runs

The simple rule: **`grocery_list` is populated only when `menu_plan` exists.**

| Request | Result |
|---|---|
| `days` provided (or multi-day intent like "week"/"weekly"/"N days") | `menu_plan` populated → `grocery_list` populated |
| No `days`, no multi-day intent | `menu_plan: null` → `grocery_list: null` |
| User asks "grocery list" / "shopping list" without `days` | `grocery_list: null` + a warning telling them to provide `days` |
| LLM unavailable or quantity call fails | Grocery list still returned, but with `quantity: null` / `unit: null` |

### Example request

```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "3-day dinner menu with chicken and rice, no pork",
    "available_ingredients": ["chicken", "rice", "carrot"],
    "dietary_restrictions": ["no pork"],
    "days": 3,
    "servings": 4
  }'
```

### Example response (trimmed)

```json
{
  "menu_plan": {
    "days": [
      { "day": 1, "meals": { "dinner": { "name": "Chicken Plov" } } },
      { "day": 2, "meals": { "dinner": { "name": "Lagman" } } },
      { "day": 3, "meals": { "dinner": { "name": "Manti" } } }
    ],
    "total_days": 3,
    "servings": 4
  },
  "grocery_list": {
    "items": [
      { "ingredient": "chicken thighs", "quantity": 800, "unit": "g",
        "category": "meat", "already_available": true },
      { "ingredient": "long-grain rice", "quantity": 600, "unit": "g",
        "category": "grains", "already_available": true },
      { "ingredient": "carrots", "quantity": 4, "unit": "pcs",
        "category": "vegetables", "already_available": true },
      { "ingredient": "onion", "quantity": 2, "unit": "pcs",
        "category": "vegetables", "already_available": false },
      { "ingredient": "cumin", "quantity": 2, "unit": "tsp",
        "category": "spices", "already_available": false }
    ],
    "categories": {
      "meat": [ /* ... */ ],
      "grains": [ /* ... */ ],
      "vegetables": [ /* ... */ ],
      "spices": [ /* ... */ ]
    },
    "total_items": 5,
    "estimated_total_cost": null
  },
  "warnings": [
    "Quantities are estimates because recipe ingredient amounts are incomplete."
  ]
}
```

`grocery_list` matches the existing API schema (`items` array + a `categories` dict grouped by category + `total_items`). The richer agent output — including `recipes_used_in`, `summary`, and per-item `notes` — is retained server-side on `response.metadata` for logging, tracing, and debugging only; it is not serialized in the public API response.

### How to test with curl

**With explicit days (grocery list populates):**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "3-day dinner menu with chicken and rice",
    "available_ingredients": ["chicken", "rice"],
    "days": 3
  }' \
  | jq '{
      total: .grocery_list.total_items,
      categories: (.grocery_list.categories | keys),
      on_hand: [.grocery_list.items[] | select(.already_available) | .ingredient],
      warnings
    }'
```

**Without days (grocery list is null):**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"what can I make with chicken and rice for dinner?"}' \
  | jq '{menu_plan, grocery_list, warnings}'
```
Expected: both `menu_plan` and `grocery_list` are `null`.

**Grocery list requested but no days — surfaced warning:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"Give me a grocery list"}' \
  | jq '{grocery_list, warnings}'
```
Expected: `grocery_list: null`, `warnings` contains `"Grocery list requested but no menu plan was produced. Provide \`days\` or describe a multi-day plan to receive a grocery list."`.

### Current limitations

- **Generated only when `menu_plan` exists.** No menu plan → no grocery list.
- **Quantities are estimates.** When the LLM populates them, every response carries the warning `"Quantities are estimates because recipe ingredient amounts are incomplete."` Don't treat them as exact shopping amounts.
- **Already-available items remain in the list.** The list flags them with `already_available: true` rather than removing them, so callers can render an explicit "you already have this" badge instead of silently dropping ingredients.
- **No quantity aggregation across recipes.** If two recipes both need rice, the grocery item appears once with a single quantity estimate from the LLM — not the literal sum (the LLM is asked to combine totals, but the result is still an estimate).
- **No cost estimation.** `estimated_cost` and `estimated_total_cost` are always `null` — a future integration with a price source would populate them.
- **Units constrained to a small set.** Only `kg`, `g`, `pcs`, `bunch`, `tbsp`, `tsp`, `liters` are accepted; anything else from the LLM is dropped to `null`.
- **Categorization is keyword-based**, not exhaustive. Unrecognized ingredients fall into `"other"`.

## Documentation

### Quick Start Guides

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - ⭐ **Start here!** Quick testing commands for all services
- **[Setup Checklist](docs/SETUP_CHECKLIST.md)** - Complete setup verification and troubleshooting
- **[Consistency Check](CONSISTENCY_CHECK.md)** - Project configuration verification results

### Detailed Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design and component interactions
- **[Development Guide](docs/DEVELOPMENT.md)** - Development setup and guidelines
- **[Observability](docs/OBSERVABILITY.md)** - Monitoring and tracing setup

Component-specific documentation:

- **Backend API**: `apps/api/README.md` - FastAPI setup, endpoints, agents
  - Database: `apps/api/DATABASE.md`
  - Agents: `apps/api/AGENTS.md`
  - Observability: `apps/api/OBSERVABILITY.md`
  - LangSmith: `apps/api/LANGSMITH.md`
- **Frontend**: `apps/web/README.md` - Next.js app setup and structure
- **Infrastructure**: `infra/docker/README.md` - Docker services configuration

## License

See [LICENSE](LICENSE) file for details.