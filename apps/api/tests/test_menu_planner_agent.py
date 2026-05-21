"""
Unit tests for the Menu Planner Agent.

These tests exercise the days-null short-circuit, the deterministic fallback
path, and the deterministic validator — none require OpenAI.

The full LLM-backed path is covered by the integration tests in
`tests/test_recommendations_endpoint.py`.
"""

import pytest

from app.agents.menu_planner_agent import (
    MenuPlannerAgent,
    MenuPlannerAgentInput,
    _validate_plan,
)
from app.schemas.menu_plan import MenuDay, MenuMeal
from app.services.rag_recipe_service import RetrievedRecipe


def _recipe(**overrides) -> RetrievedRecipe:
    defaults = dict(
        id=1,
        name="Test Recipe",
        cuisine="Test",
        ingredients=[],
        instructions=None,
        score=0.5,
        match_reason="x",
    )
    defaults.update(overrides)
    return RetrievedRecipe(**defaults)


@pytest.fixture
def _force_fallback(monkeypatch):
    """Force the LLM path to fail so we exercise the deterministic fallback."""
    monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestDaysShortCircuit:
    async def test_days_none_returns_null_menu_plan(self):
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(days=None, recipes=[_recipe()])
        )
        assert out.menu_plan is None

    async def test_days_zero_returns_null_menu_plan(self):
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(days=0, recipes=[_recipe()])
        )
        assert out.menu_plan is None


class TestFallbackPlan:
    async def test_3_day_plan_has_3_days(self, _force_fallback):
        recipes = [
            _recipe(id=1, name="A", ingredients=["chicken"]),
            _recipe(id=2, name="B", ingredients=["rice"]),
            _recipe(id=3, name="C", ingredients=["carrot"]),
        ]
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(recipes=recipes, days=3, servings=4)
        )
        assert out.menu_plan is not None
        assert len(out.menu_plan.days) == 3

    async def test_each_day_has_at_least_one_meal(self, _force_fallback):
        recipes = [_recipe(id=1, name="A", ingredients=["chicken"])]
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(recipes=recipes, days=3, servings=4)
        )
        assert out.menu_plan is not None
        for day in out.menu_plan.days:
            assert day.meals  # non-empty

    async def test_requested_meal_types_drive_meal_count(self, _force_fallback):
        recipes = [_recipe(id=1, name="A", ingredients=["chicken"])]
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(
                recipes=recipes,
                days=2,
                requested_meal_types=["breakfast", "dinner"],
            )
        )
        assert out.menu_plan is not None
        for day in out.menu_plan.days:
            meal_types = {m.meal_type for m in day.meals}
            assert meal_types == {"breakfast", "dinner"}

    async def test_no_recipes_returns_empty_days_with_warning(self, _force_fallback):
        # No recipes short-circuits before the fallback; same result either way.
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(recipes=[], days=3)
        )
        assert out.menu_plan is not None
        assert out.menu_plan.days == []
        assert any("No recipes available" in w for w in out.menu_plan.warnings)


class TestRestrictedIngredients:
    """
    With pork-free retrieved recipes and a 'no pork' restriction, the plan
    must not include any pork-family ingredient, and no restriction-warning
    should be emitted.
    """

    async def test_plan_contains_no_restricted_ingredients(self, _force_fallback):
        clean_recipes = [
            _recipe(id=1, name="Plov", ingredients=["chicken", "rice", "carrot"]),
            _recipe(id=2, name="Lagman", ingredients=["beef", "noodles", "onion"]),
        ]
        out = await MenuPlannerAgent().create_menu_plan(
            MenuPlannerAgentInput(
                recipes=clean_recipes,
                days=3,
                dietary_restrictions=["no pork"],
            )
        )
        assert out.menu_plan is not None

        for day in out.menu_plan.days:
            for meal in day.meals:
                names = " ".join(meal.recipe_name.lower().split())
                assert "pork" not in names
                assert "bacon" not in names

        # And the validator should not have flagged any restriction conflict.
        assert not any(
            "may conflict with restriction" in w for w in out.menu_plan.warnings
        )


class TestValidatePlan:
    """Unit tests for the deterministic validator. No agent, no LLM."""

    def test_excluded_ingredient_warning(self):
        recipe = _recipe(id=1, name="Carbonara", ingredients=["bacon", "egg"])
        days = [
            MenuDay(
                day=1,
                meals=[
                    MenuMeal(day=1, meal_type="dinner", recipe_id="1", recipe_name="Carbonara")
                ],
            )
        ]
        warnings = _validate_plan(
            days,
            MenuPlannerAgentInput(
                recipes=[recipe], days=1, excluded_ingredients=["bacon"]
            ),
        )
        assert any(
            "Day 1 dinner 'Carbonara' contains excluded ingredient: bacon." in w
            for w in warnings
        )

    def test_restriction_warning(self):
        recipe = _recipe(id=1, name="Carbonara", ingredients=["bacon", "egg"])
        days = [
            MenuDay(
                day=1,
                meals=[
                    MenuMeal(day=1, meal_type="dinner", recipe_id="1", recipe_name="Carbonara")
                ],
            )
        ]
        warnings = _validate_plan(
            days,
            MenuPlannerAgentInput(
                recipes=[recipe], days=1, dietary_restrictions=["no pork"]
            ),
        )
        assert any(
            "may conflict with restriction: no_pork" in w for w in warnings
        )

    def test_consecutive_day_repeat_warning(self):
        recipe = _recipe(id=1, name="Plov", ingredients=["chicken", "rice"])
        days = [
            MenuDay(
                day=1,
                meals=[MenuMeal(day=1, meal_type="dinner", recipe_id="1", recipe_name="Plov")],
            ),
            MenuDay(
                day=2,
                meals=[MenuMeal(day=2, meal_type="dinner", recipe_id="1", recipe_name="Plov")],
            ),
        ]
        warnings = _validate_plan(
            days, MenuPlannerAgentInput(recipes=[recipe], days=2)
        )
        assert any(
            "appears on consecutive days 1 and 2" in w for w in warnings
        )

    def test_day_count_mismatch_warning(self):
        recipe = _recipe(id=1, name="Plov", ingredients=["chicken", "rice"])
        days = [
            MenuDay(
                day=1,
                meals=[MenuMeal(day=1, meal_type="dinner", recipe_id="1", recipe_name="Plov")],
            )
        ]
        warnings = _validate_plan(
            days, MenuPlannerAgentInput(recipes=[recipe], days=5)
        )
        assert any(
            "Plan has 1 day(s); 5 were requested." in w for w in warnings
        )

    def test_no_warnings_for_clean_plan(self):
        r1 = _recipe(id=1, name="Plov", ingredients=["chicken", "rice"])
        r2 = _recipe(id=2, name="Lagman", ingredients=["beef", "noodles"])
        days = [
            MenuDay(
                day=1,
                meals=[MenuMeal(day=1, meal_type="dinner", recipe_id="1", recipe_name="Plov")],
            ),
            MenuDay(
                day=2,
                meals=[MenuMeal(day=2, meal_type="dinner", recipe_id="2", recipe_name="Lagman")],
            ),
        ]
        warnings = _validate_plan(
            days,
            MenuPlannerAgentInput(
                recipes=[r1, r2],
                days=2,
                dietary_restrictions=["no pork"],
                excluded_ingredients=["egg"],
            ),
        )
        assert warnings == []