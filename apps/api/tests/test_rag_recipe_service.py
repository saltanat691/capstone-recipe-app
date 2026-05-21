"""
Integration tests for the RAG retrieval service.

Requires:
  - OPENAI_API_KEY in the environment (used to embed the query)
  - DATABASE_URL pointing at a Postgres with pgvector and at least a few
    recipes embedded (run scripts/embed_recipes.py first)
"""

import pytest
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.recipe import Recipe
from app.services.rag_recipe_service import (
    RecipeSearchFilters,
    RetrievedRecipe,
    retrieve_recipes,
)


pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
async def _isolate_db_engine():
    """
    Dispose the global async engine before and after each test so asyncpg
    connections pooled on one pytest-asyncio event loop are not reused on
    the next test's loop (which raises 'attached to a different loop').
    """
    from app.db.session import engine
    await engine.dispose()
    yield
    await engine.dispose()


async def _embedded_recipe_count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(func.count(Recipe.id)).where(Recipe.embedding.is_not(None))
        )
        return int(result.scalar_one())


async def test_empty_query_raises(require_openai_key):
    with pytest.raises(ValueError):
        await retrieve_recipes("", RecipeSearchFilters())


async def test_basic_retrieval_returns_recipes(require_openai_key):
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    results = await retrieve_recipes(
        "easy dinner with rice and chicken",
        RecipeSearchFilters(),
        limit=5,
    )

    assert isinstance(results, list)
    assert len(results) >= 1
    assert len(results) <= 5
    for r in results:
        assert isinstance(r, RetrievedRecipe)
        assert r.id > 0
        assert r.name
        assert r.score is not None
        assert r.match_reason  # never empty for returned items


async def test_results_sorted_by_score_descending(require_openai_key):
    if await _embedded_recipe_count() < 2:
        pytest.skip("Need at least 2 embedded recipes for ordering test.")

    results = await retrieve_recipes(
        "dinner ideas",
        RecipeSearchFilters(),
        limit=5,
    )
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


async def test_limit_respected(require_openai_key):
    if await _embedded_recipe_count() < 2:
        pytest.skip("Need at least 2 embedded recipes for limit test.")

    results = await retrieve_recipes(
        "dinner",
        RecipeSearchFilters(),
        limit=1,
    )
    assert len(results) <= 1


async def test_central_asian_dinner_returns_at_least_one(require_openai_key):
    """
    Regression: a realistic query should never return an empty list when
    the DB has embedded recipes — the dietary filter must not over-exclude,
    and the cuisine/ingredient signals must not be hard requirements.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    results = await retrieve_recipes(
        "I have chicken rice and carrots, no pork, Central Asian dinner",
        RecipeSearchFilters(
            dietary_restrictions=["no_pork"],
            cuisine_preferences=["central asian"],
            available_ingredients=["chicken", "rice", "carrots"],
        ),
        limit=5,
    )
    assert len(results) >= 1
    # And no result should contain a pork-family ingredient.
    for r in results:
        names = " ".join(r.ingredients).lower()
        assert "pork" not in names
        assert "bacon" not in names
        assert "ham" not in names


async def test_excluded_ingredients_drop_matches(require_openai_key):
    """
    Whatever the highest-ranked unfiltered result contains, asking again with
    one of its ingredients excluded must drop it. This avoids brittle
    assertions about specific recipes in the DB.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database.")

    baseline = await retrieve_recipes(
        "hearty dinner",
        RecipeSearchFilters(),
        limit=1,
    )
    if not baseline or not baseline[0].ingredients:
        pytest.skip("Top result has no ingredients to exclude against.")

    top = baseline[0]
    excluded_ingredient = top.ingredients[0]

    filtered = await retrieve_recipes(
        "hearty dinner",
        RecipeSearchFilters(excluded_ingredients=[excluded_ingredient]),
        limit=5,
    )
    assert top.id not in [r.id for r in filtered]