# Database Setup Guide

This guide covers the database setup for the Recipe AI System backend, including SQLAlchemy models, Alembic migrations, and pgvector configuration.

## Overview

### Technology Stack

- **SQLAlchemy 2.0**: Modern Python ORM with async support
- **Alembic**: Database migration tool
- **asyncpg**: High-performance async PostgreSQL driver
- **pgvector**: PostgreSQL extension for vector similarity search
- **PostgreSQL 16**: Relational database with vector support

## Database Schema

### Tables

#### `recipes`
Stores recipe information with vector embeddings for semantic search.

**Columns**:
- `id` (PK): Recipe identifier
- `name`: Recipe name
- `description`: Recipe description
- `cuisine`: Cuisine type (Italian, Mexican, etc.)
- `meal_type`: breakfast, lunch, dinner, snack
- `difficulty`: easy, medium, hard
- `prep_time`, `cook_time`, `total_time`: Time in minutes
- `servings`: Number of servings
- `instructions`: JSON array of step-by-step instructions
- `nutrition`: JSON object with nutritional information
- `dietary_tags`: JSON array (vegetarian, vegan, gluten-free, etc.)
- `embedding`: Vector(1536) for semantic search
- `source`, `source_url`: Recipe source information
- `created_at`, `updated_at`: Timestamps

#### `ingredients`
Stores ingredient information.

**Columns**:
- `id` (PK): Ingredient identifier
- `name`: Ingredient name (unique)
- `category`: Ingredient category
- `description`: Ingredient description
- `common_unit`: Default measurement unit
- `created_at`, `updated_at`: Timestamps

#### `recipe_ingredients`
Many-to-many association table linking recipes and ingredients.

**Columns**:
- `recipe_id` (FK): Reference to recipe
- `ingredient_id` (FK): Reference to ingredient
- `quantity`: Amount of ingredient
- `unit`: Measurement unit
- `preparation`: Preparation notes (chopped, diced, etc.)

#### `user_preferences`
Stores user dietary preferences and restrictions.

**Columns**:
- `id` (PK): Preference identifier
- `user_id`: User identifier (unique)
- `dietary_restrictions`: JSON array
- `cuisine_preferences`: JSON array
- `allergies`: JSON array
- `disliked_ingredients`: JSON array
- `max_cooking_time`: Maximum cooking time in minutes
- `skill_level`: beginner, intermediate, advanced
- `notes`: Additional notes
- `created_at`, `updated_at`: Timestamps

#### `menus`
Stores meal plans.

**Columns**:
- `id` (PK): Menu identifier
- `user_id`: User identifier
- `name`: Menu name
- `description`: Menu description
- `start_date`, `end_date`: Date range
- `days_count`: Number of days
- `agent_run_id` (FK): Reference to agent run that created this menu
- `created_at`, `updated_at`: Timestamps

#### `menu_days`
Stores individual days in a menu.

**Columns**:
- `id` (PK): Menu day identifier
- `menu_id` (FK): Reference to menu
- `day_number`: Day number (1-based)
- `date`: Date for this day
- `meals`: JSON object with meal assignments
- `notes`: Notes for this day
- `created_at`, `updated_at`: Timestamps

#### `grocery_lists`
Stores shopping lists generated from menus.

**Columns**:
- `id` (PK): Grocery list identifier
- `menu_id` (FK): Reference to menu
- `name`: List name
- `items`: JSON array of grocery items
- `estimated_cost`: Total estimated cost
- `notes`: Additional notes
- `created_at`, `updated_at`: Timestamps

#### `agent_runs`
Tracks AI agent executions for observability.

**Columns**:
- `id` (PK): Agent run identifier
- `run_id`: Unique run identifier
- `agent_type`: Type of agent
- `user_id`: User identifier
- `status`: pending, running, completed, failed
- `input_data`, `output_data`: JSON objects
- `error_message`, `error_traceback`: Error information
- `started_at`, `completed_at`: Timestamps
- `duration_seconds`: Execution duration
- `total_tokens`, `prompt_tokens`, `completion_tokens`: LLM usage
- `estimated_cost`: Cost estimation
- `langsmith_trace_id`: LangSmith correlation ID
- `otel_trace_id`: OpenTelemetry correlation ID
- `metadata`: Additional metadata as JSON
- `created_at`, `updated_at`: Timestamps

## Setup Instructions

### 1. Start PostgreSQL with pgvector

Make sure the infrastructure is running:

```bash
cd infra/docker
docker-compose up -d postgres
```

Verify PostgreSQL is running:

```bash
docker-compose ps postgres
```

### 2. Install Dependencies

```bash
cd apps/api
pip install -r requirements.txt
```

This installs:
- `sqlalchemy` - ORM
- `asyncpg` - Async PostgreSQL driver
- `alembic` - Migration tool
- `pgvector` - Vector extension support

### 3. Configure Database Connection

Update `apps/api/.env`:

```env
DATABASE_URL=postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai
```

### 4. Run Migrations

Apply all migrations to create tables:

```bash
cd apps/api

# Run migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial migration with pgvector extension and all tables
```

### 5. Verify Setup

Connect to the database and verify tables were created:

```bash
docker exec -it recipe-postgres psql -U recipe_user -d recipe_ai
```

In psql:

```sql
-- List all tables
\dt

-- Check if pgvector is enabled
\dx vector

-- Describe a table
\d recipes

-- Exit
\q
```

## Using the Database in Code

### Example: Creating a Recipe

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models import Recipe, Ingredient

async def create_recipe(db: AsyncSession):
    # Create a new recipe
    recipe = Recipe(
        name="Spaghetti Carbonara",
        description="Classic Italian pasta dish",
        cuisine="Italian",
        meal_type="dinner",
        difficulty="medium",
        prep_time=10,
        cook_time=20,
        total_time=30,
        servings=4,
        instructions={
            "steps": [
                "Boil water and cook pasta",
                "Mix eggs and cheese",
                "Combine with pasta and bacon"
            ]
        },
        dietary_tags=["contains_dairy", "contains_gluten"],
    )

    db.add(recipe)
    await db.commit()
    await db.refresh(recipe)

    return recipe
```

### Example: Querying Recipes

```python
from sqlalchemy import select
from app.models import Recipe

async def get_recipes_by_cuisine(db: AsyncSession, cuisine: str):
    result = await db.execute(
        select(Recipe).where(Recipe.cuisine == cuisine)
    )
    return result.scalars().all()
```

### Example: Vector Similarity Search

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import func

async def search_similar_recipes(
    db: AsyncSession,
    query_embedding: list[float],
    limit: int = 10
):
    result = await db.execute(
        select(Recipe)
        .order_by(Recipe.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return result.scalars().all()
```

## Alembic Commands

### Create a New Migration

After modifying models:

```bash
cd apps/api

# Auto-generate migration
alembic revision --autogenerate -m "Description of changes"

# Review the generated migration file in alembic/versions/

# Apply the migration
alembic upgrade head
```

### Check Current Version

```bash
alembic current
```

### View Migration History

```bash
alembic history
```

### Rollback Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

### Upgrade to Latest

```bash
alembic upgrade head
```

## Database Models Location

Models are organized in `app/models/`:

- `app/models/recipe.py` - Recipe and recipe_ingredients
- `app/models/ingredient.py` - Ingredient
- `app/models/user_preference.py` - UserPreference
- `app/models/menu.py` - Menu, MenuDay, GroceryList
- `app/models/agent_run.py` - AgentRun

All models are imported in `app/models/__init__.py` for Alembic discovery.

## Database Session Management

### Dependency Injection

Use the `get_db()` dependency in FastAPI endpoints:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db

@router.get("/recipes")
async def get_recipes(db: AsyncSession = Depends(get_db)):
    # Use db here
    pass
```

### Session Configuration

Session is configured in `app/db/session.py`:
- Auto-commit disabled
- Auto-flush disabled
- Connection pooling enabled
- Automatic rollback on errors

## pgvector Usage

### Generating Embeddings

```python
from openai import OpenAI

client = OpenAI(api_key="your-key")

def generate_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding
```

### Storing Embeddings

```python
async def create_recipe_with_embedding(db: AsyncSession, recipe_data: dict):
    # Generate embedding from recipe description
    embedding = generate_embedding(recipe_data["description"])

    recipe = Recipe(
        **recipe_data,
        embedding=embedding
    )

    db.add(recipe)
    await db.commit()
```

### Similarity Search

```python
async def find_similar_recipes(
    db: AsyncSession,
    query: str,
    limit: int = 10
):
    # Generate embedding for query
    query_embedding = generate_embedding(query)

    # Find similar recipes using cosine distance
    result = await db.execute(
        select(Recipe)
        .where(Recipe.embedding.is_not(None))
        .order_by(Recipe.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )

    return result.scalars().all()
```

## Troubleshooting

### Migration Fails

```bash
# Check current state
alembic current

# Check database connection
psql -h localhost -p 5432 -U recipe_user -d recipe_ai

# Reset database (WARNING: deletes all data)
alembic downgrade base
alembic upgrade head
```

### pgvector Not Found

```sql
-- Enable extension manually
psql -h localhost -p 5432 -U recipe_user -d recipe_ai
CREATE EXTENSION IF NOT EXISTS vector;
```

### Connection Errors

Check that:
1. PostgreSQL container is running
2. DATABASE_URL in `.env` is correct
3. Port 5432 is not blocked

```bash
# Test connection
docker exec -it recipe-postgres pg_isready -U recipe_user -d recipe_ai
```

### Import Errors

Make sure you're in the correct directory and virtual environment:

```bash
cd apps/api
source venv/bin/activate
python -c "from app.models import Recipe; print('OK')"
```

## Database Best Practices

1. **Always use async/await** for database operations
2. **Use transactions** for multiple related operations
3. **Index frequently queried columns** (already configured in models)
4. **Use connection pooling** (configured in session.py)
5. **Handle database errors** gracefully
6. **Use migrations** for all schema changes
7. **Back up data** before major migrations

## Performance Tips

1. **Use indexes** for columns in WHERE clauses
2. **Limit query results** with `.limit()`
3. **Use select() instead of Query** (SQLAlchemy 2.0 style)
4. **Eager load relationships** when needed with `selectinload()`
5. **Use vector indexes** for similarity search:

```sql
-- Create IVFFLAT index for faster vector search
CREATE INDEX ON recipes USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Next Steps

- Implement CRUD operations for each model
- Add data validation with Pydantic schemas
- Create seed data for testing
- Set up database backups
- Add database health checks to API
- Implement soft deletes if needed
- Add audit logging

## Additional Resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)