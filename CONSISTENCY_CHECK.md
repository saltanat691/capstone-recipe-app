# Project Consistency Check

Results of consistency verification across the Recipe AI System codebase.

## ✅ Verified Consistent

### Ports
- **Frontend**: 3000 (consistent across all configs)
- **Backend API**: 4000 (consistent across all configs)
- **PostgreSQL**: 5432 (consistent across all configs)
- **Grafana**: 3001 (consistent - note: uses non-standard port internally too via `GF_SERVER_HTTP_PORT=3001`)
- **Tempo**: 3200 (HTTP), 4317 (gRPC), 4318 (HTTP OTLP)
- **Loki**: 3100

### Database Credentials
- **Username**: `recipe_user` (consistent)
- **Password**: `recipe_password` (consistent)
- **Database**: `recipe_ai` (consistent)

### Docker Service Names
- `recipe-postgres` (container: postgres, service: postgres)
- `recipe-grafana` (container: grafana, service: grafana)
- `recipe-tempo` (container: tempo, service: tempo)
- `recipe-loki` (container: loki, service: loki)
- Network: `recipe-network`

### Environment Variables
All `.env.example` files are consistent:
- `DATABASE_URL` format matches expected patterns
- `ALEMBIC_DATABASE_URL` added correctly
- OpenTelemetry endpoints consistent
- LangSmith configuration consistent

### File Structure
- All config files in correct locations
- Docker compose in `infra/docker/`
- Grafana provisioning exists: `infra/grafana/provisioning/`
- Tempo config exists: `infra/tempo/tempo.yml`
- Loki config exists: `infra/loki/loki.yml`

## ⚠️ Observations (Not Issues)

### Grafana Port Configuration
**Location**: `infra/docker/docker-compose.yml`

Grafana is configured to use port 3001 internally:
```yaml
environment:
  - GF_SERVER_HTTP_PORT=3001
ports:
  - "3001:3001"
```

**Note**: This is intentional to avoid conflict with Next.js default port (3000). Standard Grafana uses port 3000 internally, but this configuration explicitly sets it to 3001 both internally and externally. This is **correct and intentional**.

### DATABASE_URL Formats
Different tools require different driver formats:

- **AsyncPG** (API runtime): `postgresql+asyncpg://...`
- **psycopg** (Alembic migrations): `postgresql+psycopg://...`
- **Base format** (config default): `postgresql://...`

**Status**: ✅ All correctly configured:
- `apps/api/.env.example`: Specifies both `DATABASE_URL` and `ALEMBIC_DATABASE_URL`
- `app/core/config.py`: Removed fallback default (now requires env var)
- `app/db/session.py`: Converts to asyncpg format
- `alembic/env.py`: Uses `ALEMBIC_DATABASE_URL` with psycopg

## ✅ Fixed Issues

### 1. SQLAlchemy Reserved Attribute
**Issue**: AgentRun model used `metadata` attribute (reserved by SQLAlchemy)
**Status**: ✅ FIXED
**Location**: `apps/api/app/models/agent_run.py:61`
```python
# Fixed to:
extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
```

### 2. OTLPSpanExporter Endpoint Access
**Issue**: Code accessed private `_endpoint` attribute
**Status**: ✅ FIXED
**Location**: `apps/api/app/observability/tracing.py:52`
```python
# Fixed to use config value directly:
print(f"  Endpoint: {settings.OTEL_EXPORTER_OTLP_ENDPOINT.replace(':4317', ':4318')}/v1/traces")
```

### 3. Alembic .env Loading
**Issue**: Alembic didn't load .env file
**Status**: ✅ FIXED
**Location**: `apps/api/alembic/env.py`
- Now loads `.env` file using `python-dotenv`
- Reads `ALEMBIC_DATABASE_URL` from environment
- Uses correct psycopg driver

### 4. Database URL Fallback
**Issue**: config.py had incorrect fallback `postgresql://user:password@...`
**Status**: ✅ FIXED
**Location**: `apps/api/app/core/config.py:30`
```python
# Fixed - no fallback, requires env var:
DATABASE_URL: str
```

## 📋 Required .env Configuration

### apps/api/.env (Minimum Required)
```bash
# Database - REQUIRED
DATABASE_URL=postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai
ALEMBIC_DATABASE_URL=postgresql+psycopg://recipe_user:recipe_password@localhost:5432/recipe_ai

# Optional (have sensible defaults)
API_HOST=0.0.0.0
API_PORT=4000
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=recipe-api
```

### Project Root .env (Optional)
The root `.env.example` is for documentation only. The actual configuration is in `apps/api/.env`.

## 📁 Directory Structure Verification

```
✅ /infra/docker/docker-compose.yml
✅ /infra/grafana/provisioning/datasources/
✅ /infra/grafana/provisioning/dashboards/
✅ /infra/tempo/tempo.yml
✅ /infra/loki/loki.yml
✅ /apps/api/.env.example
✅ /apps/api/requirements.txt
✅ /apps/api/alembic/versions/001_initial_migration.py
✅ /apps/api/app/main.py
✅ /apps/api/app/core/config.py
✅ /apps/api/app/db/session.py
✅ /apps/api/scripts/seed_recipes.py
✅ /apps/api/scripts/test_recommendations.py
✅ /apps/api/scripts/test_search.py
✅ /apps/api/data/recipes_seed.json
✅ /apps/web/package.json
✅ /apps/web/app/page.tsx
✅ /docs/SETUP_CHECKLIST.md
✅ /TESTING_GUIDE.md (just created)
✅ /README.md
```

## 🔍 Scripts Verification

All scripts exist and are functional:

```bash
✅ scripts/seed_recipes.py          # Seeds 20 recipes
✅ scripts/test_recommendations.py  # Tests recommendations endpoint
✅ scripts/test_search.py          # Tests recipe search
✅ scripts/check_llm_config.py     # Checks LLM configuration
✅ scripts/verify_db.py            # Verifies database connection
✅ scripts/test_observability.py   # Tests observability setup
```

## 🔄 Import Paths

All Python imports are consistent and correct:
- `from app.core.config import settings` ✅
- `from app.db.session import AsyncSessionLocal` ✅
- `from app.models.*` ✅
- `from app.schemas.*` ✅
- `from app.services.*` ✅
- `from app.observability.*` ✅

## 📦 Dependencies

**Python** (`apps/api/requirements.txt`):
- All dependencies properly versioned ✅
- FastAPI, SQLAlchemy, Alembic, OpenTelemetry ✅
- LangChain/LangSmith ready but optional ✅
- pytest and httpx for testing ✅

**Node.js** (`apps/web/package.json`):
- Next.js 16.2.6 ✅
- React 19.2.4 ✅
- Tailwind CSS 4 ✅
- TypeScript 5 ✅

## 🎯 Recommendations

### No Changes Needed
The project is consistent and properly configured. All previously identified issues have been fixed.

### Optional Enhancements (Future)
These are suggestions for future improvements, not required fixes:

1. **Add pytest configuration**
   - Create `apps/api/pytest.ini` or `pyproject.toml` with test settings
   - Add `tests/` directory with actual test files

2. **Add GitHub Actions CI/CD**
   - Create `.github/workflows/test.yml` for automated testing
   - Add linting and type checking

3. **Add Docker Compose for Full Stack**
   - Create `docker-compose.fullstack.yml` that includes API and frontend
   - Useful for production-like testing

4. **Add Health Check Script**
   - The script in TESTING_GUIDE.md could be added as `scripts/health_check.sh`

5. **Add .env Validation Script**
   - Script to validate all required env vars are set
   - Could run before starting services

## ✅ Summary

**Status**: Project is consistent and ready for testing

**Critical Fixes Applied**:
- SQLAlchemy metadata attribute conflict
- OTLPSpanExporter endpoint access
- Alembic .env loading
- Database URL fallback removal

**All Verified**:
- Ports are consistent
- Database credentials match
- Environment variables align
- Docker services configured correctly
- File structure complete
- Dependencies properly specified

**Next Step**: Follow TESTING_GUIDE.md to verify the entire system.