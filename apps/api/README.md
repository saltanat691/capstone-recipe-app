# Recipe AI System - Backend API

FastAPI backend for the Recipe AI System, providing RESTful APIs for recipe management and AI-powered recommendations.

## Tech Stack

- **FastAPI** - Modern, high-performance Python web framework
- **Uvicorn** - ASGI server for production
- **Pydantic** - Data validation and settings management
- **SQLAlchemy** - ORM for database interactions
- **PostgreSQL** - Primary database with pgvector extension

## Project Structure

```
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Pydantic settings
│   └── api/
│       ├── __init__.py
│       ├── health.py        # Health check endpoint
│       └── v1/
│           ├── __init__.py
│           └── router.py    # API v1 routes
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip (Python package installer)
- PostgreSQL 15+ (optional for now, required later)

### Installation

1. **Navigate to the API directory:**
   ```bash
   cd apps/api
   ```

2. **Create a virtual environment:**
   ```bash
   # Using venv (built-in)
   python -m venv .venv

   # Or using virtualenv
   virtualenv venv

   # Or using conda
   conda create -n recipe-api python=3.11
   ```

3. **Activate the virtual environment:**

   On macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

   On Windows:
   ```cmd
   .venv\Scripts\activate
   ```

   With conda:
   ```bash
   conda activate recipe-api
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**

   The API reads from `<repo-root>/.env`. Create it once from the monorepo
   template at the repo root, then edit with your real values:
   ```bash
   # From the repo root
   cp .env.example .env
   # Edit .env with your real OPENAI_API_KEY, USDA_API_KEY, etc.
   ```

6. **Set up the database:**

   Make sure PostgreSQL is running (via Docker):
   ```bash
   cd ../../infra/docker
   docker-compose up -d postgres
   cd ../../apps/api
   ```

   Run database migrations:
   ```bash
   alembic upgrade head
   ```

   This will:
   - Enable the pgvector extension
   - Create all database tables
   - Set up indexes

   For detailed database documentation, see [DATABASE.md](DATABASE.md).

   **Seed the database with sample recipes:**
   ```bash
   python scripts/seed_recipes.py
   ```

   This will insert 20 recipes (including Central Asian/Kazakh recipes) and their ingredients into the database.

7. **Configure LangSmith (Optional - for LLM tracing):**

   LangSmith provides observability for LLM calls and AI agents. To enable:

   Add to `.env`:
   ```env
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your_api_key_here
   LANGSMITH_PROJECT=recipe-ai-system-dev
   ```

   Get your API key from https://smith.langchain.com

   Verify configuration:
   ```bash
   python scripts/check_llm_config.py
   ```

   For detailed LangSmith documentation, see [LANGSMITH.md](LANGSMITH.md).

### Running the API

**Development mode (with auto-reload):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

**Alternative using the configured settings:**
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

The API will be available at:
- **Base URL**: http://localhost:4000
- **Interactive API docs (Swagger UI)**: http://localhost:4000/docs
- **Alternative docs (ReDoc)**: http://localhost:4000/redoc
- **OpenAPI schema**: http://localhost:4000/openapi.json

### Accessing the API Documentation

Once the server is running, open your browser and navigate to:

**Swagger UI (Recommended):**
```
http://localhost:4000/docs
```

This provides an interactive interface where you can:
- View all available endpoints
- Test API calls directly from the browser
- See request/response schemas
- Explore API documentation

**ReDoc (Alternative):**
```
http://localhost:4000/redoc
```

A cleaner, read-only documentation interface.

## Available Endpoints

### Root
- `GET /` - Root endpoint with API information

### Health
- `GET /health` - Health check endpoint

### API v1

**General:**
- `GET /api/v1/` - API v1 root
- `GET /api/v1/status` - API status check

**Recommendations:**
- `POST /api/v1/recommendations` - Generate recipe recommendations

### Testing the Recommendations Endpoint

**Using curl:**
```bash
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have chicken and rice, what can I make?",
    "available_ingredients": ["chicken", "rice", "broccoli"],
    "dietary_restrictions": ["gluten-free"],
    "servings": 4,
    "days": 7
  }'
```

**Using the test script:**
```bash
python scripts/test_recommendations.py
```

**Using Swagger UI:**
1. Open http://localhost:4000/docs
2. Find the "Recommendations" section
3. Click "POST /api/v1/recommendations"
4. Click "Try it out"
5. Edit the request body
6. Click "Execute"

**Response includes:**
- List of recommended recipes ranked by relevance
- Multi-day menu plan
- Shopping list organized by category
- Nutritional analysis
- Safety warnings (if any)
- Trace ID for debugging

**Recipe Search Algorithm:**

The endpoint uses a scoring-based search algorithm:

- **+2 points** for each matching ingredient
- **+3 points** for matching cuisine preference
- **-100 points** for dietary restriction violation

**How it works:**

1. **Ingredient Matching**: Uses fuzzy matching to find recipes that use ingredients you have available
2. **Dietary Restrictions**: Automatically filters out recipes containing restricted ingredients (e.g., meat for vegetarians, gluten for gluten-free diets)
3. **Cuisine Preferences**: Boosts recipes from preferred cuisines
4. **Menu Planning**: Generates a balanced menu by rotating through top-ranked recipes
5. **Grocery List**: Aggregates all unique ingredients from selected recipes

**Example scores:**
- Recipe with 3 matching ingredients + cuisine match = 2×3 + 3 = **9 points**
- Recipe with 5 matching ingredients = 2×5 = **10 points**
- Recipe with dietary restriction conflict = **-100 points** (filtered out)

## Seed Data

The API includes seed data with 20 diverse recipes:

**Central Asian/Kazakh Recipes (10):**
- Chicken Plov
- Beef Plov
- Lentil Soup
- Chicken Noodle Soup
- Buckwheat with Chicken
- Fish with Vegetables
- Egg Breakfast Plate
- Lagman-style Noodles
- Beshbarmak-style Chicken
- Vegetable Stew

**International Recipes (10):**
- Chicken Stir Fry
- Greek Salad
- Spaghetti Bolognese
- Vegetable Curry
- Chicken Tacos
- Salmon Teriyaki
- Mushroom Risotto
- Shakshuka
- Thai Green Curry
- Quinoa Buddha Bowl

Each recipe includes:
- Detailed ingredients with quantities and units
- Step-by-step instructions
- Cooking times (prep, cook, total)
- Difficulty level
- Cuisine type and meal type
- Dietary and allergen tags

**To seed the database:**
```bash
python scripts/seed_recipes.py
```

**To re-seed (drop and recreate):**
```bash
alembic downgrade base
alembic upgrade head
python scripts/seed_recipes.py
```

## Development

### Code Formatting

**Format code with Black:**
```bash
black app/
```

### Linting

**Lint code with Ruff:**
```bash
ruff check app/
```

**Auto-fix issues:**
```bash
ruff check --fix app/
```

### Type Checking

**Check types with mypy:**
```bash
mypy app/
```

### Testing

**Run tests with pytest:**
```bash
pytest
```

**With coverage:**
```bash
pytest --cov=app tests/
```

## Configuration

The application uses Pydantic settings for configuration management. Settings can be configured via:

1. Environment variables
2. `.env` file
3. Default values in `app/core/config.py`

### Key Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | Recipe AI System API |
| `APP_VERSION` | API version | 0.1.0 |
| `API_PORT` | Server port | 4000 |
| `API_HOST` | Server host | 0.0.0.0 |
| `API_RELOAD` | Auto-reload on changes | true |
| `ENVIRONMENT` | Environment (development/staging/production) | development |
| `DEBUG` | Debug mode | true |
| `DATABASE_URL` | PostgreSQL connection string | postgresql://user:password@localhost:5432/recipe_ai |
| `USDA_API_KEY` | USDA FoodData Central API key (optional) | _empty_ |
| `USDA_API_BASE_URL` | USDA FDC base URL | https://api.nal.usda.gov/fdc/v1 |

## USDA FoodData Central Integration (Optional)

The Nutrition Agent currently produces per-recipe nutrition estimates via the LLM alone. Estimates are labeled as approximate and tagged with a `confidence` field.

For improved accuracy, the project ships an optional integration with the USDA FoodData Central (FDC) API. When enabled, agents can ground LLM estimates with authoritative per-100g nutrient data for individual ingredients.

**This integration is opt-in.** The app runs without it; the Nutrition Agent simply uses LLM-only estimates.

### Enabling

1. Get a free API key at https://fdc.nal.usda.gov/api-key-signup.html (no credit card required).
2. Add it to `apps/api/.env`:
   ```
   USDA_API_KEY=your_key_here
   ```
3. Restart the API.

### Available client

Located at `app/services/nutrition_data_service.py`:

```python
from app.services import NutritionDataService, search_food, get_food_details

# One-shot helpers
results = await search_food("chicken breast")
detail = await get_food_details(results[0]["fdcId"])

# Or reuse an httpx connection across calls
async with NutritionDataService() as svc:
    a = await svc.search_food("rice")
    b = await svc.get_food_details(a[0]["fdcId"])
```

Errors are raised explicitly:
- `USDAConfigError` — `USDA_API_KEY` is missing or the API rejects it (`401`/`403`)
- `USDAApiError` — transport, HTTP, or payload errors

### Status

The client is implemented but **not yet wired into the agent graph**. A follow-up will use it inside the Nutrition Agent to anchor estimates with USDA per-100g data and bump `confidence` to `"medium"`/`"high"` when ingredient quantities are available.

## Project Guidelines

### Adding New Endpoints

1. Create a new router file in `app/api/v1/`
2. Define your routes using FastAPI decorators
3. Use Pydantic models for request/response validation
4. Import and include the router in `app/main.py`

Example:
```python
# app/api/v1/recipes.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Recipe(BaseModel):
    id: int
    name: str

@router.get("/recipes", response_model=list[Recipe])
async def get_recipes():
    return []
```

Then in `app/main.py`:
```python
from app.api.v1.recipes import router as recipes_router
app.include_router(recipes_router, prefix=settings.API_V1_PREFIX)
```

### Code Style

- Follow PEP 8 style guide
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use async/await for I/O operations

## Troubleshooting

### Port Already in Use

If port 4000 is already in use:
```bash
# Find the process using port 4000
lsof -ti:4000

# Kill the process
lsof -ti:4000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --port 4001 --reload
```

### Module Not Found Error

Make sure you're in the correct directory and virtual environment is activated:
```bash
cd apps/api
source .venv/bin/activate  # or the appropriate activation command
pip install -r requirements.txt
```

### Import Errors

Ensure you're running uvicorn from the `apps/api` directory:
```bash
cd apps/api
uvicorn app.main:app --reload
```

## Observability

The API is fully instrumented with OpenTelemetry for distributed tracing and structured JSON logging.

### Features

- **Distributed Tracing**: All requests, database queries, and operations are traced
- **Structured Logging**: JSON logs with trace correlation
- **Request Tracking**: Unique request IDs for debugging
- **Automatic Instrumentation**: FastAPI, SQLAlchemy, and asyncpg

### Quick Start

1. **Start observability stack:**
   ```bash
   cd ../../infra/docker
   docker-compose up -d grafana tempo loki
   ```

2. **Run the API:**
   ```bash
   cd ../../apps/api
   uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
   ```

3. **Generate traces:**
   ```bash
   curl http://localhost:4000/health
   ```

4. **View traces in Grafana:**
   - Open http://localhost:3001 (admin/admin)
   - Go to Explore → Tempo
   - Search for service: `recipe-api`

5. **View logs in Grafana:**
   - Go to Explore → Loki
   - Query: `{service="recipe-api"}`

### Log Example

All logs are structured JSON with trace correlation:

```json
{
  "timestamp": "2024-05-09T16:30:00",
  "level": "INFO",
  "message": "Request completed",
  "service": "recipe-api",
  "trace_id": "d4a8c8f2e3b1a9d7c6e5f4a3b2c1d0e9",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/health",
  "status_code": 200,
  "duration_ms": 12.45
}
```

### Trace Correlation

Logs include `trace_id` that matches OpenTelemetry traces. Find logs for a specific trace:

```logql
{service="recipe-api"} | json | trace_id="<trace-id>"
```

### Custom Logging

```python
from app.observability import get_logger

logger = get_logger(__name__)

logger.info(
    "Recipe created",
    extra={
        "recipe_id": recipe.id,
        "user_id": user_id,
    }
)
```

For detailed observability documentation, see [OBSERVABILITY.md](OBSERVABILITY.md).

## LangSmith (LLM Observability)

LangSmith provides specialized observability for LLM calls and AI agents. It's configured but will only activate when LangGraph agents are implemented.

### Configuration Status

Check your LangSmith setup:

```bash
python scripts/check_llm_config.py
```

Output shows:
- Which LLM providers are configured (OpenAI, Anthropic)
- LangSmith tracing status
- Configuration recommendations

### Quick Setup

1. **Get LangSmith API key:**
   - Sign up at https://smith.langchain.com
   - Go to Settings → API Keys
   - Create a new API key

2. **Configure in `.env`:**
   ```env
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=lsv2_pt_...
   LANGSMITH_PROJECT=recipe-ai-system-dev
   ```

3. **Add LLM provider key:**
   ```env
   # Choose one or both
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   ```

4. **Restart API:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
   ```

### What Gets Traced

Once LangGraph agents are implemented, LangSmith automatically captures:
- LLM prompts and completions
- Token usage and costs
- Agent reasoning steps
- Tool calls and results
- Errors and exceptions

### Viewing Traces

1. Go to https://smith.langchain.com
2. Select your project
3. View traces in real-time
4. Debug prompts and optimize performance

For detailed LangSmith documentation, see [LANGSMITH.md](LANGSMITH.md).

## AI Agents

The API includes a multi-agent system for recipe recommendations built with LangGraph.

### Agent Architecture

Six specialized agents work together:

1. **Ingredient Agent** - Analyzes and validates user ingredients
2. **Recipe Agent** - Finds and recommends recipes
3. **Nutrition Agent** - Analyzes nutritional content
4. **Menu Planner Agent** - Creates multi-day meal plans
5. **Grocery List Agent** - Generates shopping lists
6. **Safety Agent** - Validates recommendations for safety

### Current Status

✅ Agent skeleton structure created
✅ Shared state model defined
✅ Logging and observability integrated
⏳ LLM integration pending
⏳ LangGraph workflow pending

### Agent Structure

```
app/agents/
├── state.py                    # Shared state model
├── ingredient_agent.py         # Ingredient analysis
├── recipe_agent.py             # Recipe recommendations
├── nutrition_agent.py          # Nutritional analysis
├── menu_planner_agent.py       # Meal planning
├── grocery_list_agent.py       # Shopping list generation
├── safety_agent.py             # Safety validation
└── graph.py                    # LangGraph orchestration
```

### Usage (Future)

Once implemented, agents will be invoked via:

```python
from app.agents import get_agent_graph

graph = get_agent_graph()
result = await graph.invoke({
    "available_ingredients": ["chicken", "rice", "broccoli"],
    "dietary_restrictions": ["gluten-free"],
    "cuisine_preferences": ["asian"],
    "servings": 4,
    "days": 7
})

# Access results
menu_plan = result["menu_plan"]
grocery_list = result["grocery_list"]
nutrition_notes = result["nutrition_notes"]
```

For detailed agent documentation, see [AGENTS.md](AGENTS.md).

## Recipe Search Service

The API includes a basic recipe search service that ranks recipes based on ingredient matches, dietary restrictions, and cuisine preferences.

### Service Location

```
app/services/recipe_search_service.py
```

### Key Features

1. **Ingredient Matching**
   - Fuzzy matching for ingredient names
   - Handles variations (e.g., "chicken" matches "chicken breast")
   - Scores based on number of matching ingredients

2. **Dietary Restrictions**
   - Supports common restrictions: vegetarian, vegan, gluten-free, dairy-free, nut-free
   - Checks both recipe tags and ingredient names
   - Automatically filters out incompatible recipes

3. **Cuisine Preferences**
   - Boosts recipes from preferred cuisines
   - Supports multiple cuisine preferences

4. **Scoring System**
   - Simple, transparent scoring algorithm
   - +2 points per matching ingredient
   - +3 points for cuisine match
   - -100 points for dietary restriction violation

### Testing the Search Service

**Run the search test script:**
```bash
python scripts/test_search.py
```

This script tests various search scenarios:
- Ingredient-based search
- Dietary restriction filtering
- Cuisine preference matching
- Combined criteria

**Test via API:**
```bash
python scripts/test_recommendations.py
```

### Usage Example

```python
from app.services import search_recipes
from app.db.session import AsyncSessionLocal

async with AsyncSessionLocal() as db:
    results = await search_recipes(
        db_session=db,
        available_ingredients=["chicken", "rice", "broccoli"],
        dietary_restrictions=["gluten-free"],
        cuisine_preferences=["asian"],
        limit=10
    )

    for recipe, score in results:
        print(f"{recipe.name}: {score} points")
```

### Future Enhancements

- [ ] Add RAG (Retrieval-Augmented Generation) with vector embeddings
- [ ] Implement semantic search using pgvector
- [ ] Add nutritional scoring
- [ ] Consider user preferences and history
- [ ] Integrate with AI agents for advanced recommendations

## Next Steps

- [x] Add database models with SQLAlchemy
- [x] Implement database migrations with Alembic
- [x] Add OpenTelemetry instrumentation
- [x] Configure LangSmith for LLM tracing
- [x] Create AI agent module structure
- [x] Add seed data with 20 recipes
- [x] Implement basic recipe search with scoring
- [ ] Add RAG with vector embeddings
- [ ] Implement LLM calls in agents
- [ ] Build LangGraph workflow
- [ ] Add authentication and authorization
- [ ] Create recipe CRUD endpoints
- [ ] Implement comprehensive testing

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)