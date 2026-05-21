"""
Integration test for POST /api/v1/recommendations.

Requires:
  - OPENAI_API_KEY in the environment
  - DATABASE_URL with at least a few recipes embedded
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.recipe import Recipe


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


async def test_recommendations_happy_path(require_openai_key):
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    payload = {
        "message": "Easy dinner with chicken and rice",
        "available_ingredients": ["chicken", "rice"],
        "servings": 4,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()

    # Schema invariants — not brittle assertions about specific recipes.
    assert "recommendations" in body
    assert isinstance(body["recommendations"], list)
    assert "warnings" in body
    assert isinstance(body["warnings"], list)

    # menu_plan and grocery_list are still zeroed; nutrition_notes is
    # populated by the Nutrition Agent.
    assert body.get("menu_plan") is None
    assert body.get("grocery_list") is None

    nutrition_notes = body.get("nutrition_notes")
    assert isinstance(nutrition_notes, str)
    if body["recommendations"]:
        assert nutrition_notes  # non-empty when we have recipes

    # `metadata` is intentionally not part of the public API response;
    # internal diagnostics (scores, match_reasons, structured nutrition) are
    # available on `response.metadata` server-side via the graph logs.
    assert "metadata" not in body


async def test_recommendations_endpoint_returns_grocery_list_when_days_provided(
    require_openai_key,
):
    """
    With an explicit `days` value, the endpoint should produce a populated
    grocery_list with at least one item.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    payload = {
        "message": "3-day dinner menu with chicken and rice",
        "available_ingredients": ["chicken", "rice"],
        "days": 3,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()

    if not body.get("recommendations"):
        pytest.skip("Retrieval returned no recipes — cannot exercise grocery agent.")

    assert body.get("grocery_list") is not None
    assert isinstance(body["grocery_list"]["items"], list)
    assert len(body["grocery_list"]["items"]) >= 1
    assert body["grocery_list"]["total_items"] == len(body["grocery_list"]["items"])


async def test_recommendations_endpoint_keeps_grocery_list_null_without_days(
    require_openai_key,
):
    """
    Without an explicit `days` and without multi-day intent, both menu_plan
    and grocery_list must remain null.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    payload = {
        "message": "I have chicken and rice, what can I make for dinner?",
        "available_ingredients": ["chicken", "rice"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("menu_plan") is None
    assert body.get("grocery_list") is None


async def test_recommendations_endpoint_returns_menu_plan_when_days_provided(
    require_openai_key,
):
    """
    With an explicit `days` value, the endpoint should return a populated
    menu_plan whose day count matches the request.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    payload = {
        "message": "3-day dinner menu with chicken and rice, no pork",
        "available_ingredients": ["chicken", "rice"],
        "days": 3,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()

    if not body.get("recommendations"):
        pytest.skip("Retrieval returned no recipes — cannot exercise menu planner.")

    assert body.get("menu_plan") is not None
    assert isinstance(body["menu_plan"]["days"], list)
    assert len(body["menu_plan"]["days"]) == 3
    assert body["menu_plan"]["total_days"] == 3


async def test_recommendations_endpoint_keeps_menu_plan_null_without_days(
    require_openai_key,
):
    """
    Without an explicit `days` and without multi-day intent in the message,
    menu_plan must remain null.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    payload = {
        "message": "I have chicken and rice, what can I make for dinner?",
        "available_ingredients": ["chicken", "rice"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("menu_plan") is None


async def test_recommendations_endpoint_exposes_nutrition_notes(require_openai_key):
    """
    Focused regression: the endpoint must always include the nutrition_notes
    field in the response body — string type, populated whenever recipes
    were returned.
    """
    if await _embedded_recipe_count() == 0:
        pytest.skip("No embedded recipes in database; run scripts/embed_recipes.py.")

    payload = {
        "message": "halal weeknight dinner with chicken and rice",
        "available_ingredients": ["chicken", "rice"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/recommendations", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()

    assert "nutrition_notes" in body
    assert isinstance(body["nutrition_notes"], str)
    if body.get("recommendations"):
        assert body["nutrition_notes"]  # non-empty when recipes were returned

    # Each recommendation must have the core identifying fields.
    for rec in body["recommendations"]:
        assert "name" in rec and rec["name"]
        # id, cuisine, ingredients, instructions are optional on the schema
        # but if present should have the right types
        if rec.get("ingredients") is not None:
            assert isinstance(rec["ingredients"], list)