# Testing Guide

Quick reference for testing the Recipe AI System. Follow these steps in order.

## Prerequisites Check

```bash
# Verify installations
docker --version          # Should be 20.10+
docker-compose --version  # Should be 1.29+
python --version         # Should be 3.11+
node --version          # Should be 18+
npm --version
psql --version          # Optional, for direct DB access
```

## 1. Start Docker Infrastructure

```bash
# Navigate to docker directory
cd infra/docker

# Start all services (PostgreSQL, Grafana, Tempo, Loki)
docker-compose up -d

# Verify all containers are running
docker-compose ps
```

**Expected output:**
```
NAME                STATUS              PORTS
recipe-postgres     Up                  0.0.0.0:5432->5432/tcp
recipe-grafana      Up                  0.0.0.0:3001->3001/tcp
recipe-tempo        Up                  0.0.0.0:3200->3200/tcp, 0.0.0.0:4317-4318->4317-4318/tcp
recipe-loki         Up                  0.0.0.0:3100->3100/tcp
```

**Check logs if any service fails:**
```bash
docker-compose logs postgres
docker-compose logs grafana
```

## 2. Setup Backend Environment

```bash
# Navigate to API directory
cd apps/api

# Create virtual environment (if not exists)
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure Environment Variables

The API reads from `<repo-root>/.env`. Create it from the monorepo template
once, from the repo root:

```bash
# From the repo root
cp .env.example .env

# Verify DATABASE_URL is set correctly
grep DATABASE_URL .env
```

**Expected content in .env:**
```bash
DATABASE_URL=postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai
ALEMBIC_DATABASE_URL=postgresql+psycopg://recipe_user:recipe_password@localhost:5432/recipe_ai
```

## 4. Run Database Migrations

```bash
# Still in apps/api with venv activated

# Run migrations to create tables
alembic upgrade head
```

**Expected output:** four migrations applied in order

```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial
INFO  [alembic.runtime.migration] Running upgrade 001_initial -> 002_recipe_embedding_hnsw
INFO  [alembic.runtime.migration] Running upgrade 002_recipe_embedding_hnsw -> 003_auth_and_retention
INFO  [alembic.runtime.migration] Running upgrade 003_auth_and_retention -> 004_feedback
```

**Verify tables were created:**
```bash
# From infra/docker directory
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c '\dt'
```

**Expected tables:**
- agents_runs
- alembic_version
- grocery_lists
- ingredients
- menu_days
- menus
- recipe_ingredients
- recipes
- user_preferences

## 5. Seed Database with Recipes

```bash
# In apps/api with .venv activated
python scripts/seed_recipes.py
```

**Expected output:**
```
INFO     Starting recipe seeding process
INFO     Loaded 20 recipes from JSON file
INFO     Created recipe: Chicken Plov (ID: 1)
...
============================================================
Recipe seeding completed!
  Recipes created: 20
  Recipes skipped: 0
  Unique ingredients: 45
============================================================
```

**Verify recipes were inserted:**
```bash
# From infra/docker directory
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'
```

**Expected:** 20 recipes

### 5b. Generate embeddings (required for RAG retrieval)

The RAG agent looks up recipes by vector similarity in `pgvector`. Without embeddings, every query returns nothing.

```bash
# In apps/api with .venv activated
python scripts/embed_recipes.py
```

**Expected output:** `Embedded 20 recipes.` (subsequent runs print `Embedded 0 recipes.` because the script only touches rows where `embedding IS NULL`. Add `--force` to re-embed.)

**Verify embeddings exist:**
```bash
docker-compose exec postgres psql -U recipe_user -d recipe_ai \
  -c "SELECT COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS with_emb, COUNT(*) AS total FROM recipes;"
```
Expected: `with_emb = 20, total = 20`.

## 6. Run Backend API

```bash
# In apps/api with .venv activated
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

**Expected output:**
```
✓ OpenTelemetry tracing initialized
  Service: recipe-api
  Endpoint: http://localhost:4318/v1/traces
✓ Database instrumented with OpenTelemetry
...
============================================================
Starting Recipe AI System API v0.1.0
Environment: development
Debug mode: True
API available at: http://0.0.0.0:4000
API docs at: http://localhost:4000/docs
============================================================
INFO:     Uvicorn running on http://0.0.0.0:4000 (Press CTRL+C to quit)
```

**Leave this terminal running. Open a new terminal for testing.**

## 7. Test Health Endpoint

```bash
# In a new terminal
curl http://localhost:4000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "Recipe AI System API",
  "version": "0.1.0",
  "timestamp": "2024-05-11T..."
}
```

**Test root endpoint:**
```bash
curl http://localhost:4000/
```

**Expected response:**
```json
{
  "message": "Welcome to Recipe AI System API",
  "docs": "/docs",
  "health": "/health",
  "api_v1": "/api/v1"
}
```

### 7b. Test Readiness Endpoint (DB ping)

```bash
curl -s http://localhost:4000/readiness | jq
```

**Expected (Postgres up):**
```json
{ "status": "ready", "checks": { "database": "ok" } }
```

**Expected (Postgres down):** HTTP 503 with `checks.database: "error: …"`. Try it by `docker stop recipe-postgres` and then re-running the curl; restart with `docker start recipe-postgres` afterwards.

## 8. Test API Documentation

**Open in browser:**
```bash
# Swagger UI
open http://localhost:4000/docs
# OR
xdg-open http://localhost:4000/docs  # Linux
# OR
start http://localhost:4000/docs     # Windows
```

**Verify:**
- Swagger UI loads
- See all endpoints listed
- Can expand and test endpoints

## 9. Test Recommendations Endpoint

**Basic test with curl:**
```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need meal ideas for the week",
    "days": 7
  }'
```

**Expected response structure** (six top-level fields; `metadata` is internal-only and not serialized):

```json
{
  "recommendations": [
    {
      "id": 1,
      "name": "Chicken Plov",
      "cuisine": "Central Asian",
      "ingredients": ["chicken thighs", "rice", "carrots", "onion", "cumin"],
      "instructions": ["…"]
    }
  ],
  "menu_plan": {
    "days": [
      { "day": 1, "meals": { "dinner": { "name": "Chicken Plov" } } }
    ],
    "total_days": 7,
    "servings": 2
  },
  "grocery_list": {
    "items": [
      {
        "ingredient": "chicken thighs",
        "quantity": 800,
        "unit": "g",
        "category": "meat",
        "already_available": false
      }
    ],
    "categories": { "meat": [/*…*/], "grains": [/*…*/] },
    "total_items": 15
  },
  "nutrition_notes": "All nutritional values are rough estimates and not medical advice. …",
  "warnings": [
    "Quantities are estimates because recipe ingredient amounts are incomplete."
  ],
  "trace_id": "abc123…"
}
```

Notes:
- `menu_plan` is `null` when the request did not ask for a multi-day plan (no `days`, no "week"/"weekly" intent).
- `grocery_list` is `null` whenever `menu_plan` is `null`.
- `nutrition_notes` is always a string; empty when no recipes were returned.
- Safety / fallback warnings from the nutrition and menu validators merge into the top-level `warnings`.

**Test with ingredients:**
```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What can I make with chicken and rice?",
    "available_ingredients": ["chicken", "rice", "onions"],
    "days": 3
  }'
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

**Test with cuisine preferences:**
```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Plan Asian cuisine meals",
    "cuisine_preferences": ["Asian", "Central Asian"],
    "days": 7
  }'
```

**Use test script:**
```bash
# In apps/api with .venv activated
python scripts/test_recommendations.py
```

## 10. Run Frontend

**In a new terminal:**
```bash
# Navigate to frontend directory
cd apps/web

# Install dependencies (if not done)
npm install

# Start development server
npm run dev
```

**Expected output:**
```
▲ Next.js 16.2.6
- Local:        http://localhost:3000
- Network:      http://192.168.x.x:3000

✓ Ready in 2.3s
```

**Open in browser:**
```bash
open http://localhost:3000
```

**Verify:**
- Form loads with all fields
- Ingredient input field
- Dietary restriction buttons
- Cuisine preference buttons
- Servings and days sliders
- Submit button

## 11. Test Observability Stack

### Test Grafana

**Open Grafana:**
```bash
open http://localhost:3001
```

**Login:**
- Username: `admin`
- Password: `admin`
- Skip password change (optional)

**Verify data sources:**
1. Go to: Configuration → Data Sources
2. Should see:
   - Tempo (http://tempo:3200)
   - Loki (http://loki:3100)
3. Click each and test connection

### Test Tempo (Distributed Tracing)

**Generate some traces:**
```bash
# Make several API requests
for i in {1..5}; do
  curl http://localhost:4000/health
  sleep 1
done

curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan meals", "days": 7}'
```

**View traces in Grafana:**
1. Open Grafana: http://localhost:3001
2. Click "Explore" (compass icon)
3. Select "Tempo" data source
4. Search for:
   - Service: `recipe-api`
   - Or use "Search" tab
5. Click a trace to view details

**Verify Tempo health:**
```bash
curl http://localhost:3200/ready
```

**Expected:** `ready`

### Test Loki (Structured Logging)

> ⚠️ **Logs only flow to Loki when running the API via `docker-compose --profile apps up`.** The default infra-only stack starts Loki but no log shipper. Promtail (added under the `apps` profile) is what tails container stdout and pushes JSON log lines to Loki. If you're running the API locally via `./run.sh` or `uvicorn`, logs go only to stdout — you can `grep` them there, but Grafana's Loki datasource will be empty.

**View logs in Grafana:**
1. Open Grafana: http://localhost:3001
2. Click "Explore"
3. Select "Loki" data source
4. Query: `{service="recipe-api"}`
5. Should see JSON-formatted logs

Useful LogQL queries (with the structured event labels):
```logql
{service="recipe-api", event="node_complete"}              # per-node latency events
{service="recipe-api", event="llm_fallback"}               # agents that fell back
{service="recipe-api", event="api_error"}                  # request failures
{service="recipe-api"} | json | request_id=`<your-id>`     # all logs for one request
```

**Verify Loki health:**
```bash
curl http://localhost:3100/ready
```

**Expected:** `ready`

**Query logs via API:**
```bash
curl -G -s "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service="recipe-api"}' \
  --data-urlencode 'limit=10'
```

## 12. Run Additional Tests

### Test Recipe Search

```bash
# In apps/api with .venv activated
python scripts/test_search.py
```

**Expected output:**
- Multiple test scenarios
- Recipe matches with scores
- Dietary restriction filtering
- Cuisine preference matching

### Verify Database Connection

```bash
# In apps/api with .venv activated
python scripts/verify_db.py
```

### Check LLM Configuration

```bash
# In apps/api with .venv activated
python scripts/check_llm_config.py
```

## 13. Test New API Endpoints

### Feedback (rate a prior recommendation)

```bash
# Use the trace_id from a /api/v1/recommendations response
curl -s -X POST http://localhost:4000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{"trace_id":"<paste-trace-id-here>","rating":5,"comment":"great plov"}' | jq
```

Expected: HTTP 201, JSON containing the stored feedback record (id, trace_id, rating, comment, created_at).

### Auth — issue an API key

```bash
curl -s -X POST http://localhost:4000/api/v1/auth/api-keys \
  -H "Content-Type: application/json" \
  -d '{"owner_id":"alice","name":"local-test","tracing_consent":true}' | jq
```

Expected: HTTP 201 with the plaintext `api_key` (returned **once** — copy it). Consumers send `X-API-Key: <key>` on subsequent requests. Enforcement is gated by `REQUIRE_AUTH=true` in `.env`; by default the API is open.

## 14. Test Production Safety

### Rate limit (10 req/min/IP on `/recommendations`)

```bash
seq 1 15 | xargs -P 15 -I{} curl -s -o /dev/null -w "%{http_code}\n" \
  -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" -d '{"message":"x"}'
```

Expected: at least five `429 Too Many Requests` responses among the 15 attempts.

Override the limit via `.env`:

```env
RATE_LIMIT_PER_MINUTE=10
```

### Request size limit (default 1 MB)

```bash
python3 -c 'import json;print(json.dumps({"message":"x"*(2*1024*1024)}))' | \
  curl -i -X POST http://localhost:4000/api/v1/recommendations \
    -H "Content-Type: application/json" --data-binary @-
```

Expected: HTTP 413 with body `"Request body too large: <N> bytes (max 1048576)."`. Tune via `MAX_REQUEST_BYTES`.

### LLM timeout

Default: `LLM_TIMEOUT_SECONDS=30.0`. Lower it to verify the timeout actually kicks in:

```bash
LLM_TIMEOUT_SECONDS=0.001 ./run.sh  # in a fresh terminal
# Then POST any /recommendations request — expect HTTP 500 with a timeout
# in the logs, not a 60-second hang.
```

Restore the value afterwards.

## 15. Run the Python Test Suite

```bash
# In apps/api with .venv activated

# Fast unit tests (no DB, no LLM, no API keys required)
pytest -m "not integration" -v

# Full suite (integration tests auto-skip when OPENAI_API_KEY is unset)
pytest -v

# Static checks
ruff check app
mypy app
```

Expected: **164 unit tests pass**, mypy `Success: no issues found`, ruff `All checks passed!`. Integration tests are marked with `@pytest.mark.integration` and require a populated DB + `OPENAI_API_KEY`.

## Common Issues and Fixes

### Issue 1: Port Already in Use

**Error:**
```
Error: address already in use
```

**Fix:**
```bash
# Find process using the port
lsof -i :4000  # or :3000, :5432, :3001, etc.

# Kill the process
kill -9 <PID>

# Or change port in .env or docker-compose.yml
```

### Issue 2: Docker Containers Not Starting

**Error:**
```
Container exited with code 1
```

**Fix:**
```bash
# Check logs
cd infra/docker
docker-compose logs <service-name>

# Remove and restart
docker-compose down -v
docker-compose up -d

# Check disk space
docker system df
```

### Issue 3: Database Connection Failed

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Fix:**
```bash
# Verify PostgreSQL is running
cd infra/docker
docker-compose ps postgres

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres

# Wait 5 seconds then retry
sleep 5
```

### Issue 4: Password Authentication Failed

**Error:**
```
password authentication failed for user "user"
```

**Fix:**
```bash
# Verify DATABASE_URL in .env
cd apps/api
cat .env | grep DATABASE_URL

# Should be:
# DATABASE_URL=postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai

# NOT:
# DATABASE_URL=postgresql://user:password@localhost:5432/recipe_ai

# Update .env if needed, then restart API
```

### Issue 5: Alembic Migration Fails

**Error:**
```
alembic.util.exc.CommandError: Can't locate revision
```

**Fix:**
```bash
# Reset database
cd infra/docker
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

# Re-run migrations
cd ../../apps/api
alembic upgrade head
```

### Issue 6: Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Fix:**
```bash
# Verify venv is activated
which python  # Should show venv path

# If not activated
cd apps/api
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue 7: Seed Script Fails

**Error:**
```
IntegrityError: duplicate key value violates unique constraint
```

**Fix:**
```bash
# Recipes already exist - this is normal on second run
# To reseed, clear database first:

cd infra/docker
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'DELETE FROM recipes CASCADE;'
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'DELETE FROM ingredients CASCADE;'

# Re-run seed script
cd ../../apps/api
python scripts/seed_recipes.py
```

### Issue 8: No Traces in Tempo

**Fix:**
```bash
# 1. Verify Tempo is running
curl http://localhost:3200/ready

# 2. Check API is sending traces
# Look for "OpenTelemetry tracing initialized" in API logs

# 3. Restart Tempo
cd infra/docker
docker-compose restart tempo

# 4. Make test requests
curl http://localhost:4000/health

# 5. Wait 10 seconds for traces to appear
sleep 10
```

### Issue 9: Frontend Won't Start

**Error:**
```
Error: ENOENT: no such file or directory
```

**Fix:**
```bash
# Remove and reinstall
cd apps/web
rm -rf node_modules package-lock.json
npm install

# Verify Node version
node --version  # Should be 18+

# Start dev server
npm run dev
```

### Issue 10: Empty Recommendations

**Issue:** API returns empty recommendations array

**Fix:**
```bash
# 1. Verify recipes exist
cd infra/docker
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'

# If count is 0, seed the database:
cd ../../apps/api
python scripts/seed_recipes.py

# 2. Test with broader search
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Any recipes", "days": 7}'

# 3. Test search directly
python scripts/test_search.py
```

## Quick Health Check Script

**Save this as `health_check.sh` in project root:**

```bash
#!/bin/bash

echo "=== Recipe AI System Health Check ==="
echo ""

# Check Docker services
echo "1. Docker Services:"
cd infra/docker
docker-compose ps | grep -E "recipe-postgres|recipe-grafana|recipe-tempo|recipe-loki"
echo ""

# Check database
echo "2. Database:"
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) as recipe_count FROM recipes;' 2>&1 | grep -E "recipe_count|[0-9]+"
echo ""

# Check API
echo "3. API Health:"
curl -s http://localhost:4000/health | jq -r '.status' || echo "API not responding"
echo ""

# Check Grafana
echo "4. Grafana:"
curl -s http://localhost:3001/api/health | jq -r '.database' || echo "Grafana not responding"
echo ""

# Check Tempo
echo "5. Tempo:"
curl -s http://localhost:3200/ready
echo ""

# Check Loki
echo "6. Loki:"
curl -s http://localhost:3100/ready
echo ""

# Check Frontend
echo "7. Frontend:"
curl -s http://localhost:3000 > /dev/null && echo "Frontend running" || echo "Frontend not running"
echo ""

echo "=== Health Check Complete ==="
```

**Make it executable and run:**
```bash
chmod +x health_check.sh
./health_check.sh
```

## Success Checklist

Your system is fully operational when:

- ✅ All Docker containers are running
- ✅ Database has 20 recipes
- ✅ API responds on http://localhost:4000
- ✅ `/health` returns `{"status":"healthy"}`
- ✅ `/docs` shows API documentation
- ✅ Recommendations endpoint returns recipes
- ✅ Frontend loads on http://localhost:3000
- ✅ Grafana accessible on http://localhost:3001
- ✅ Traces visible in Tempo
- ✅ Logs visible in Loki

## Next Steps

After verification:

1. **Integrate Frontend with Backend**
   - Update frontend to call API
   - Display recommendations in UI

2. **Add Tests**
   - Write pytest tests
   - Test recipe search logic
   - Test database operations

3. **Implement AI Agents**
   - Add LLM integration
   - Build LangGraph workflows
   - Enable LangSmith tracing

4. **Add RAG**
   - Generate recipe embeddings
   - Implement vector search
   - Use pgvector for similarity search

## Additional Resources

- **Setup Checklist**: `docs/SETUP_CHECKLIST.md` - Detailed setup guide with troubleshooting
- **API README**: `apps/api/README.md` - Backend documentation
- **Frontend README**: `apps/web/README.md` - Frontend documentation
- **Architecture**: `docs/ARCHITECTURE.md` - System design
- **Observability**: `docs/OBSERVABILITY.md` - Monitoring and tracing

## Support

If you encounter issues not covered here:

1. Check logs: `docker-compose logs <service>`
2. Review documentation in `/docs` folder
3. Verify environment variables in `.env` files
4. Ensure all prerequisites are installed and at correct versions