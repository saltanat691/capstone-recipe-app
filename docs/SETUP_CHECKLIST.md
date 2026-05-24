# Setup Checklist

Complete verification checklist for setting up the Recipe AI System.

## Prerequisites

Before starting, ensure you have:

- [ ] Docker and Docker Compose installed
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ and npm installed
- [ ] Git installed

**Verify prerequisites:**

```bash
# Check Docker
docker --version
docker-compose --version

# Check Python
python --version

# Check Node.js and npm
node --version
npm --version
```

## Quick Start

Run all services at once:

```bash
# From project root
./scripts/start-all.sh  # If script exists

# Or manually:
# 1. Start Docker services
cd infra/docker && docker-compose up -d

# 2. Start API (in new terminal)
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

# 3. Start Frontend (in new terminal)
cd apps/web
npm run dev
```

## Verification Steps

### 1. Docker Infrastructure

**Start Docker services:**

```bash
cd infra/docker
docker-compose up -d
```

**Verify containers are running:**

```bash
docker-compose ps
```

**Expected output:**
```
NAME                STATUS              PORTS
postgres            running             0.0.0.0:5432->5432/tcp
grafana             running             0.0.0.0:3001->3000/tcp
tempo               running             0.0.0.0:3200->3200/tcp, 0.0.0.0:4318->4318/tcp
loki                running             0.0.0.0:3100->3100/tcp
```

**Check logs (if needed):**

```bash
docker-compose logs -f postgres
docker-compose logs -f grafana
docker-compose logs -f tempo
```

✅ **Pass criteria:** All containers show "running" status

---

### 2. PostgreSQL Database

**Test database connection:**

```bash
# From infra/docker directory
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c '\dt'
```

**Expected output:**
```
                List of relations
 Schema |        Name         | Type  |    Owner
--------+---------------------+-------+-------------
 public | agent_runs          | table | recipe_user
 public | alembic_version     | table | recipe_user
 public | grocery_lists       | table | recipe_user
 public | ingredients         | table | recipe_user
 public | menu_days           | table | recipe_user
 public | menus               | table | recipe_user
 public | recipe_ingredients  | table | recipe_user
 public | recipes             | table | recipe_user
 public | user_preferences    | table | recipe_user
```

**Verify pgvector extension:**

```bash
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c '\dx'
```

**Expected output should include:**
```
 pgvector | ... | vector data type and ivfflat access method
```

**Alternative connection test from host:**

```bash
# Requires psql client installed locally
psql -h localhost -p 5432 -U recipe_user -d recipe_ai -c 'SELECT version();'
# Password: recipe_password
```

✅ **Pass criteria:** Can connect and see all tables listed

---

### 3. Backend API Setup

**Navigate to API directory:**

```bash
cd apps/api
```

**Create and activate virtual environment (if not done):**

```bash
# Create venv
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows)
# .venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Setup environment variables:**

The API reads from `<repo-root>/.env`. Create it once from the monorepo
template at the repo root:

```bash
# From the repo root (not apps/api)
cp .env.example .env

# Verify .env contains correct values
cat .env | grep DATABASE_URL
```

**Run database migrations:**

```bash
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial
INFO  [alembic.runtime.migration] Running upgrade 001_initial -> 002_recipe_embedding_hnsw
INFO  [alembic.runtime.migration] Running upgrade 002_recipe_embedding_hnsw -> 003_auth_and_retention
INFO  [alembic.runtime.migration] Running upgrade 003_auth_and_retention -> 004_feedback
```

✅ **Pass criteria:** Migrations complete without errors

---

### 4. API Server Start

**Start the API server:**

```bash
# From apps/api directory
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

**Expected output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
```

**Verify server is listening:**

```bash
# In a new terminal
lsof -i :4000
# Or
netstat -an | grep 4000
```

✅ **Pass criteria:** Server starts without errors and listens on port 4000

---

### 5. Health Endpoint

**Test health endpoint:**

```bash
curl http://localhost:4000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "Recipe AI System API",
  "version": "0.1.0",
  "timestamp": "2024-05-09T..."
}
```

**Test root endpoint:**

```bash
curl http://localhost:4000/
```

**Expected output:**
```json
{
  "message": "Welcome to Recipe AI System API",
  "version": "0.1.0",
  "docs_url": "/docs"
}
```

✅ **Pass criteria:** Both endpoints return 200 status with expected JSON

---

### 6. API Documentation

**Open API docs in browser:**

```bash
# macOS
open http://localhost:4000/docs

# Linux
xdg-open http://localhost:4000/docs

# Windows
start http://localhost:4000/docs
```

**Or manually navigate to:**
- Swagger UI: http://localhost:4000/docs
- ReDoc: http://localhost:4000/redoc
- OpenAPI schema: http://localhost:4000/openapi.json

**Verify documentation loads:**

You should see:
- All endpoints listed (Health, Recommendations, etc.)
- Request/response schemas
- Interactive "Try it out" buttons

✅ **Pass criteria:** Documentation UI loads and displays all endpoints

---

### 7. Seed Database

**Run seed script:**

```bash
# From apps/api directory (with venv activated)
python scripts/seed_recipes.py
```

**Expected output:**
```
INFO     Starting recipe seeding process
INFO     Loaded 20 recipes from JSON file
INFO     Created recipe: Chicken Plov (ID: 1)
INFO     Created ingredient: chicken thighs (ID: 1)
...
============================================================
Recipe seeding completed!
  Recipes created: 20
  Recipes skipped: 0
  Unique ingredients: 45
============================================================
```

**Verify recipes in database:**

```bash
# From infra/docker directory
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'
```

**Expected output:**
```
 count
-------
    20
```

**Check specific recipe:**

```bash
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c "SELECT name, cuisine FROM recipes LIMIT 5;"
```

✅ **Pass criteria:** 20 recipes inserted successfully

---

### 8. Recommendations Endpoint

**Test recommendations endpoint:**

```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need meal ideas for the week",
    "available_ingredients": ["chicken", "rice", "vegetables"],
    "dietary_restrictions": [],
    "cuisine_preferences": ["asian"],
    "servings": 4,
    "days": 7
  }'
```

**Expected output (truncated):**
```json
{
  "recommendations": [
    {
      "id": 1,
      "name": "Chicken Plov",
      "cuisine": "Central Asian",
      "prep_time": 20,
      "cook_time": 60,
      ...
    }
  ],
  "menu_plan": {
    "days": [...],
    "total_days": 7
  },
  "grocery_list": {
    "items": [...],
    "total_items": 15
  },
  "trace_id": "..."
}
```

**Test with dietary restrictions:**

```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need vegetarian meals",
    "dietary_restrictions": ["vegetarian"],
    "days": 5
  }'
```

**Use test script:**

```bash
python scripts/test_recommendations.py
```

✅ **Pass criteria:** Returns recommendations with menu plan and grocery list

---

### 9. Frontend Setup

**Navigate to frontend directory:**

```bash
cd apps/web
```

**Install dependencies:**

```bash
npm install
```

**Expected output:**
```
added 234 packages, and audited 235 packages in 15s
```

**Start development server:**

```bash
npm run dev
```

**Expected output:**
```
   ▲ Next.js 15.0.0
   - Local:        http://localhost:3000
   - Network:      http://192.168.1.x:3000

 ✓ Ready in 2.3s
```

✅ **Pass criteria:** Server starts on port 3000

---

### 10. Frontend Access

**Open frontend in browser:**

```bash
# macOS
open http://localhost:3000

# Linux
xdg-open http://localhost:3000

# Windows
start http://localhost:3000
```

**Verify page loads:**

You should see:
- Recipe recommendation form
- Ingredient input field
- Dietary restriction buttons
- Cuisine preference buttons
- Servings slider
- Days slider
- Submit button

**Test form interaction:**
1. Enter some ingredients
2. Select dietary restrictions
3. Choose cuisine preferences
4. Adjust servings and days
5. Click "Get Recommendations"

✅ **Pass criteria:** Form loads and accepts input (may not submit to API yet)

---

### 11. Grafana Dashboard

**Open Grafana in browser:**

```bash
# macOS
open http://localhost:3001

# Linux
xdg-open http://localhost:3001

# Windows
start http://localhost:3001
```

**Login credentials:**
- Username: `admin`
- Password: `admin`

**Verify Grafana loads:**
- Login page appears
- Can login successfully
- Prompted to change password (can skip)

**Check data sources:**

1. Navigate to: Configuration → Data Sources
2. Verify data sources exist:
   - Tempo (connected to http://tempo:3200)
   - Loki (connected to http://loki:3100)

✅ **Pass criteria:** Grafana loads and data sources are connected

---

### 12. Distributed Tracing (Tempo)

**Generate traces by making API requests:**

```bash
# Make several requests to generate traces
for i in {1..5}; do
  curl http://localhost:4000/health
  sleep 1
done
```

**View traces in Grafana:**

1. Open Grafana: http://localhost:3001
2. Go to: Explore (compass icon in left sidebar)
3. Select: Tempo data source
4. Search for traces:
   - Service: `recipe-api`
   - Or search by TraceID from API response

**Expected result:**
- Traces appear in Tempo
- Can view trace details showing:
  - Request spans
  - Database query spans
  - Duration timings

**Check Tempo health:**

```bash
curl http://localhost:3200/ready
```

**Expected output:**
```
ready
```

✅ **Pass criteria:** Traces visible in Grafana and Tempo is healthy

---

### 13. Structured Logging (Loki)

**View logs in Grafana:**

1. Open Grafana: http://localhost:3001
2. Go to: Explore
3. Select: Loki data source
4. Query: `{service="recipe-api"}`

**Expected result:**
- Log entries appear
- Structured JSON format
- Contains trace_id, request_id, etc.

**Check Loki health:**

```bash
curl http://localhost:3100/ready
```

**Expected output:**
```
ready
```

**Query logs via API:**

```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="recipe-api"}' \
  --data-urlencode 'limit=5' | jq
```

✅ **Pass criteria:** Logs visible in Grafana and Loki is healthy

---

## Quick Verification Summary

Run these commands in sequence to verify everything:

```bash
# 1. Check Docker services
cd infra/docker && docker-compose ps

# 2. Check database
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c '\dt'

# 3. Check API health
curl http://localhost:4000/health

# 4. Check seed data
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'

# 5. Test recommendations
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan meals for the week", "days": 7}'

# 6. Check frontend
curl http://localhost:3000

# 7. Check Grafana
curl http://localhost:3001/api/health

# 8. Check Tempo
curl http://localhost:3200/ready

# 9. Check Loki
curl http://localhost:3100/ready
```

---

## Common Troubleshooting

### Problem: Port already in use

**Error:**
```
Error: address already in use
Error starting userland proxy: listen tcp4 0.0.0.0:5432: bind: address already in use
```

**Solution:**

```bash
# Find process using the port
lsof -i :5432  # or :4000, :3000, :3001, etc.

# Kill the process
kill -9 <PID>

# Or use a different port in docker-compose.yml or config
```

---

### Problem: Docker containers not starting

**Error:**
```
Container exited with code 1
```

**Solution:**

```bash
# Check container logs
cd infra/docker
docker-compose logs <service-name>

# Remove containers and volumes, start fresh
docker-compose down -v
docker-compose up -d

# Check Docker disk space
docker system df
docker system prune  # If needed
```

---

### Problem: Database migration fails

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**

```bash
# Verify PostgreSQL is running
cd infra/docker
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Wait a few seconds, then retry migration
cd ../../apps/api
alembic upgrade head

# Verify DATABASE_URL in .env is correct
cat .env | grep DATABASE_URL
```

---

### Problem: API won't start - Import errors

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solution:**

```bash
# Verify you're in the correct directory
cd apps/api

# Verify virtual environment is activated
which python  # Should point to venv/bin/python

# If not activated:
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
```

---

### Problem: API starts but /health returns 404

**Error:**
```
{"detail":"Not Found"}
```

**Solution:**

```bash
# Check API is running
curl http://localhost:4000/

# If root works but /health doesn't, check router configuration
# Verify in app/main.py that health router is included

# Restart API with reload enabled
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

# Check API logs for errors
```

---

### Problem: Seed script fails

**Error:**
```
sqlalchemy.exc.IntegrityError: duplicate key value violates unique constraint
```

**Solution:**

```bash
# Recipes already exist - this is normal on second run
# To reseed, clear database first:

cd infra/docker
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'DELETE FROM recipes;'
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'DELETE FROM ingredients;'

# Or reset entire database:
cd ../../apps/api
alembic downgrade base
alembic upgrade head
python scripts/seed_recipes.py
```

---

### Problem: Frontend won't start

**Error:**
```
Error: ENOENT: no such file or directory
```

**Solution:**

```bash
# Remove node_modules and reinstall
cd apps/web
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+

# Use correct Node version (if using nvm)
nvm use 18
npm install
```

---

### Problem: Frontend shows "Cannot connect to API"

**Error (in browser console):**
```
Failed to fetch
net::ERR_CONNECTION_REFUSED
```

**Solution:**

```bash
# Verify API is running
curl http://localhost:4000/health

# Check if API is accessible from frontend
# In apps/web, check API URL configuration
# May need to update API_URL in .env.local

# If using Docker, ensure containers are on same network

# Check CORS configuration in API
# Verify app/main.py includes CORS middleware with correct origins
```

---

### Problem: No traces appearing in Tempo

**Issue:**
Traces not showing in Grafana despite API requests

**Solution:**

```bash
# 1. Verify Tempo is running
curl http://localhost:3200/ready

# 2. Check Tempo is receiving traces
docker-compose logs tempo | grep -i "received"

# 3. Verify API is sending traces
# Check API logs for OpenTelemetry messages

# 4. Test trace export endpoint
curl http://localhost:4318/v1/traces

# 5. Restart Tempo
cd infra/docker
docker-compose restart tempo

# 6. Check Grafana data source connection
# Grafana → Configuration → Data Sources → Tempo → Test
```

---

### Problem: Grafana shows "Data source not found"

**Solution:**

```bash
# 1. Verify Grafana can reach Tempo/Loki
cd infra/docker
docker-compose exec grafana ping tempo -c 2
docker-compose exec grafana ping loki -c 2

# 2. Recreate data sources
# Delete existing data sources in Grafana UI
# Add new data sources:
# - Tempo: http://tempo:3200
# - Loki: http://loki:3100

# 3. Check docker-compose network
docker network ls
docker network inspect docker_default

# 4. Restart all observability services
docker-compose restart grafana tempo loki
```

---

### Problem: Permission denied errors

**Error:**
```
Permission denied: '/path/to/file'
```

**Solution:**

```bash
# Fix file permissions
chmod +x scripts/*.sh  # Make scripts executable
chmod 755 apps/api/scripts/*.py  # Python scripts

# Fix directory permissions
chmod 755 apps/api/data

# Check user ownership
ls -la

# If Docker permission issues
sudo chmod 666 /var/run/docker.sock
```

---

### Problem: Virtual environment activation fails

**Error (Windows):**
```
cannot be loaded because running scripts is disabled on this system
```

**Solution (Windows PowerShell):**

```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then retry activation
.venv\Scripts\activate
```

**Solution (macOS/Linux):**

```bash
# If .venv doesn't exist, create it
python -m venv .venv

# Source it (activate scripts ship executable by default — no chmod needed)
source .venv/bin/activate
```

---

### Problem: Recommendations return empty results

**Issue:**
API returns empty recommendations array

**Solution:**

```bash
# 1. Verify recipes exist in database
cd infra/docker
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'

# If count is 0, seed the database:
cd ../../apps/api
python scripts/seed_recipes.py

# 2. Test search directly
python scripts/test_search.py

# 3. Check API logs for errors
# Look for warnings like "No recipes found matching criteria"

# 4. Try a broader search
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Any recipes", "days": 7}'

# 5. Check dietary restrictions aren't too restrictive
# Try without restrictions first
```

---

## Environment Variables Reference

### API (.env)

```bash
# Required
DATABASE_URL=postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai
API_PORT=4000
ENVIRONMENT=development

# Optional - OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=recipe-api

# Optional - LangSmith
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=recipe-ai-system-dev

# Optional - LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:4000
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check logs:**
   - API: uvicorn output in terminal
   - Docker: `docker-compose logs <service>`
   - Frontend: npm dev server output

2. **Verify configuration:**
   - `.env` files have correct values
   - Ports are not blocked by firewall
   - All services can reach each other

3. **Search documentation:**
   - Check `README.md` in each app directory
   - Review `ARCHITECTURE.md` for system overview
   - Read specific docs: `DATABASE.md`, `OBSERVABILITY.md`, `AGENTS.md`

4. **Clean slate restart:**
   ```bash
   # Stop everything
   docker-compose down -v

   # Start fresh
   docker-compose up -d
   alembic upgrade head
   python scripts/seed_recipes.py
   uvicorn app.main:app --reload
   ```

---

## Success Indicators

Your setup is complete when:

- ✅ All Docker containers running
- ✅ Database has 20 recipes
- ✅ API responds on http://localhost:4000
- ✅ `/health` returns healthy status
- ✅ `/docs` shows API documentation
- ✅ Recommendations endpoint returns results
- ✅ Frontend loads on http://localhost:3000
- ✅ Grafana accessible on http://localhost:3001
- ✅ Traces visible in Tempo
- ✅ Logs visible in Loki

**Final test - Full flow:**

```bash
# Make a request
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Healthy meals", "days": 7}' | jq

# Check it appears in logs (Grafana → Loki)
# Check it appears in traces (Grafana → Tempo)
# Verify recipes are relevant to request
```

---

## Nutrition Agent

The Nutrition Agent sits in the LangGraph workflow at:
`ingredient → recipe_retrieval → nutrition → final_response`.

### What it does

Enriches each recommended recipe with an estimated per-serving nutrition profile (`calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g`, `sugar_g`, `sodium_mg`), a `confidence` level (`low` / `medium` / `high`), and safety `warnings`.

**Important:**
- All nutrition values are **estimates**, not measurements. Every `health_notes` block opens with the disclaimer: _"All nutritional values are rough estimates and not medical advice."_
- The agent does **not provide medical advice**.
- A **deterministic safety check** runs alongside the LLM and adds warnings like `"Recipe may conflict with restriction: no_pork."` whenever an ingredient matches the dietary-restriction blocklist or an `excluded_ingredients` entry — even if the LLM missed it.

### LLM fallback behavior

The endpoint **never fails because of nutrition**:
- No `OPENAI_API_KEY` set → low-confidence fallback notes with the safety warnings still attached.
- Per-recipe LLM error → only that recipe gets a fallback note; the others return normal estimates.
- No retrieved recipes → `nutrition_notes` is empty, no LLM call is issued.

### Prerequisites

- ✅ `OPENAI_API_KEY` set in `apps/api/.env`
- ✅ Recipes embedded: `cd apps/api && python scripts/embed_recipes.py`
- ✅ API restarted so it picks up `.env`

### Test the endpoint

**Happy path:**

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

Expected:
- `nutrition_notes` non-empty, opening with the disclaimer
- `warnings` is `[]` for a clean request (per-recipe macros, confidence levels, and structured nutrition entries are logged server-side rather than returned in the API response)

**Restriction warning path:**

```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"pasta carbonara with bacon","dietary_restrictions":["no pork"]}' \
  | jq '.warnings'
```
Expected: at least one entry contains `"Recipe may conflict with restriction: no_pork."` if any returned recipe carries a pork-family ingredient.

**LLM-down (fallback) path** — temporarily unset the key:

```bash
cd apps/api && source .venv/bin/activate
OPENAI_API_KEY= python -c "
import asyncio
from app.agents.nutrition_agent import NutritionAgent, NutritionAgentInput
from app.services.rag_recipe_service import RetrievedRecipe
r = RetrievedRecipe(id=1, name='Bacon Bowl', cuisine='Italian',
                    ingredients=['bacon','eggs'], score=0.5, match_reason='x')
out = asyncio.run(NutritionAgent().enrich_recipes(NutritionAgentInput(
    recipes=[r], dietary_restrictions=['no pork']
)))
print(out.notes[0].model_dump_json(indent=2))
"
```
Expected: `confidence="low"`, `warnings` contains both `"Recipe may conflict with restriction: no_pork."` and `"Estimation failed: ..."`.

### Run the test suite

```bash
cd apps/api && source .venv/bin/activate && pytest -v
```
- `tests/test_nutrition_agent.py` — fallback + deterministic safety (no OpenAI required)
- `tests/test_recommendations_endpoint.py::test_recommendations_endpoint_exposes_nutrition_notes` — end-to-end (requires `OPENAI_API_KEY`; otherwise skipped)

✅ **Pass criteria:** every successful `/recommendations` response includes a non-empty `nutrition_notes` string, and restriction conflicts always surface in the top-level `warnings` array (structured per-recipe nutrition stays in server logs).

---

## Menu Planner Agent

The Menu Planner Agent sits in the LangGraph workflow at:
`ingredient → recipe_retrieval → nutrition → menu_planner → final_response`.

### What it does

- Builds an n-day menu plan from the retrieved recipes using `langchain-openai` structured output.
- Reads `days` and `requested_meal_types` from the Ingredient Agent (e.g. "3-day dinner menu" → `days=3`, `requested_meal_types=["dinner"]`).
- Prefers cuisine matches, uses available ingredients early, avoids same-recipe consecutive days.
- Falls back to a deterministic round-robin if the LLM is unavailable.
- Runs a **deterministic validator** on every plan (LLM or fallback) that adds warnings for: restricted-ingredient conflicts, excluded-ingredient conflicts, consecutive-day repeats, and day-count mismatches.

### When you get a menu plan

| Request shape | `menu_plan` in response |
|---|---|
| No `days` field, no multi-day intent in the message | `null` — recommendations only |
| `days` provided, OR message says "week"/"weekly"/"N days" | Populated `MenuPlan` with the requested number of days |
| LLM fails / unavailable | Round-robin fallback with a `"Menu planner LLM unavailable: ..."` warning |

### Example request

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
      warnings,
      grocery_list
    }'
```

Expected:
- `menu_days: 3`
- `first_day_meals: ["dinner"]`
- `summary` non-empty
- `menu_warnings` empty (or `"Recipe 'X' appears on consecutive days N and N+1."` if there were few recipes)
- `grocery_list: null` (not implemented yet)

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
    "servings": 2
  },
  "grocery_list": null,
  "warnings": []
}
```

Note: structured agent diagnostics (the menu summary, per-meal `reason`, validator warnings) live on `response.metadata` server-side for logging, tracing, and debugging. They are not serialized in the public API response. Safety warnings from the nutrition and menu validators are merged into the top-level `warnings`.

### Test multi-meal and multi-day intents

**Multi-meal-type:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"plan breakfast lunch and dinner for 3 days"}' \
  | jq '.menu_plan.days[0].meals | keys'
```
Expected: `["breakfast","dinner","lunch"]`.

**Inferred from text:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"plan a week of dinners"}' \
  | jq '.menu_plan.days | length'
```
Expected: `7`.

**No menu without days:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"what can I make with chicken and rice for dinner?"}' \
  | jq '.menu_plan'
```
Expected: `null`.

### Run the test suite

```bash
cd apps/api && source .venv/bin/activate && pytest -v
```
- `tests/test_menu_planner_agent.py` — short-circuit, fallback, validator, restriction handling (no OpenAI required)
- `tests/test_recommendations_endpoint.py::test_recommendations_endpoint_returns_menu_plan_when_days_provided` — end-to-end with days (integration; requires `OPENAI_API_KEY`)
- `tests/test_recommendations_endpoint.py::test_recommendations_endpoint_keeps_menu_plan_null_without_days` — end-to-end without days (integration)

### Current limitations

- **Menu planning runs only when `days` is provided** (explicitly via the API field or implied in the message like "week"/"weekly"/"N days"). Pure recommendation requests skip the planner and `menu_plan` stays `null`.
- **No date assignments.** Only day numbers (1-based) are produced.
- **`meal_type` defaults to `"dinner"`** when retrieved recipes don't carry meal-type metadata.
- **The Menu Planner has graceful LLM fallback**, but the upstream Ingredient Agent does not — if `OPENAI_API_KEY` is missing the request fails with HTTP 500 before reaching the planner.

✅ **Pass criteria:** with `days` provided, `menu_plan` is non-null and has exactly the requested number of days; without `days`, `menu_plan` is `null`.

---

## Grocery List Agent

The Grocery List Agent sits in the LangGraph workflow at:
`ingredient → recipe_retrieval → nutrition → menu_planner → grocery_list → final_response`.

### What it does

- Aggregates ingredients from every recipe referenced by the menu plan (deduped, case-insensitive).
- Marks user-supplied ingredients as `already_available: true` using a deterministic normalizer that handles plurals and common descriptors. So `"chicken"` matches `"chicken thighs"`, `"rice"` matches `"long-grain rice"`, `"carrot"` matches `"carrots"`, etc.
- Categorizes each item into one of: `meat`, `vegetables`, `fruits`, `dairy`, `grains`, `pantry`, `spices`, `other`.
- When `OPENAI_API_KEY` is configured, asks the LLM to estimate per-ingredient quantities and units. Allowed units are `kg`, `g`, `pcs`, `bunch`, `tbsp`, `tsp`, `liters`. Estimates always carry the warning *"Quantities are estimates because recipe ingredient amounts are incomplete."*
- Falls back gracefully if the LLM is unavailable: items still appear, but `quantity` and `unit` are `null` and no estimate warning is added.

### When you get a grocery list

The simple rule: **`grocery_list` is populated only when `menu_plan` exists.**

| Request | `grocery_list` |
|---|---|
| `days` provided (or multi-day intent like "week"/"N days") | populated |
| No `days`, no multi-day intent | `null` |
| User asks "grocery list" / "shopping list" without `days` | `null` + a warning telling them to provide `days` |
| LLM unavailable | populated, but with `quantity: null` / `unit: null` |

### Prerequisites

- ✅ `OPENAI_API_KEY` set in `apps/api/.env`
- ✅ Recipes embedded (`cd apps/api && python scripts/embed_recipes.py`)
- ✅ API restarted so it picks up `.env`

### Test the endpoint

**Happy path:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "3-day dinner menu with chicken and rice",
    "available_ingredients": ["chicken", "rice", "carrot"],
    "days": 3,
    "servings": 4
  }' \
  | jq '{
      total: .grocery_list.total_items,
      categories: (.grocery_list.categories | keys),
      on_hand: [.grocery_list.items[] | select(.already_available) | .ingredient],
      first_three: .grocery_list.items[:3],
      warnings
    }'
```

Expected:
- `total > 0`
- `categories` contains at least `meat`, `grains`, `vegetables` (categorizer working).
- `on_hand` lists items matched by normalization (e.g. `"chicken thighs"`, `"long-grain rice"`, `"carrots"`).
- `first_three` items have `category`, `already_available`, and (when the LLM ran) `quantity` + `unit`.
- `warnings` may contain `"Quantities are estimates because recipe ingredient amounts are incomplete."`.

**No menu without days:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"what can I make with chicken and rice for dinner?"}' \
  | jq '{menu_plan, grocery_list}'
```
Expected: both `null`.

**Grocery list requested without days surfaces a warning:**
```bash
curl -s -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message":"Give me a grocery list"}' \
  | jq '{grocery_list, warnings}'
```
Expected: `grocery_list: null`, `warnings` contains `"Grocery list requested but no menu plan was produced. Provide \`days\` or describe a multi-day plan to receive a grocery list."`.

### Run the test suite

```bash
cd apps/api && source .venv/bin/activate && pytest -v
```
- `tests/test_grocery_list_agent.py` — null short-circuit, ingredient inclusion, normalization-driven matching, categorization, deterministic fallback (no OpenAI required)
- `tests/test_grocery_list_agent.py::TestLLMQuantityLayer` — LLM quantity estimation (integration; requires `OPENAI_API_KEY`)
- `tests/test_recommendations_endpoint.py::test_recommendations_endpoint_returns_grocery_list_when_days_provided` — end-to-end with days (integration)
- `tests/test_recommendations_endpoint.py::test_recommendations_endpoint_keeps_grocery_list_null_without_days` — end-to-end without days (integration)

### Current limitations

- **Generated only when `menu_plan` exists.** No menu plan → no grocery list.
- **Quantities are estimates** — never treat them as exact shopping amounts. The estimate disclaimer is always present when the LLM populated quantities.
- **Already-available items stay in the list** with `already_available: true` (not silently removed) so callers can render an explicit "you already have this" indicator.
- **No quantity aggregation across recipes.** Each unique ingredient gets one estimate that combines all uses; not a literal sum.
- **No cost estimation.** `estimated_cost` / `estimated_total_cost` are always `null`.
- **Units limited** to the seven practical units listed above; anything else from the LLM is dropped to `null`.
- **Categorization is keyword-based.** Unrecognized ingredients land in `"other"`.

✅ **Pass criteria:** with `days` provided, `grocery_list` is non-null, has at least one item, `total_items == len(items)`, and on-hand ingredients are flagged `already_available: true`; without `days`, `grocery_list` is `null`.

---

🎉 **Congratulations! Your Recipe AI System is ready!**

---

## Next Steps

After successful setup:

1. **Explore the API:**
   - Try different ingredient combinations
   - Test dietary restrictions
   - Experiment with cuisine preferences

2. **View observability:**
   - Check traces in Tempo
   - View logs in Loki
   - Create Grafana dashboards

3. **Start development:**
   - Add new endpoints
   - Implement AI agents
   - Build frontend integration
   - Add RAG with vector search

4. **Run tests:**
   ```bash
   cd apps/api
   pytest
   ```

5. **Read additional documentation:**
   - `docs/ARCHITECTURE.md` - System design
   - `docs/DEVELOPMENT.md` - Development workflow
   - `apps/api/AGENTS.md` - AI agent architecture
   - `apps/api/DATABASE.md` - Database schema