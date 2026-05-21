"""
Unit tests for the Grocery List Agent — focused on the ingredient
normalization / matching logic. No OpenAI required.
"""

import pytest

from app.agents.grocery_list_agent import (
    GroceryListAgent,
    GroceryListAgentInput,
    _matches_available,
    _normalize_ingredient,
    _singularize,
    categorize_ingredient,
)
from app.schemas.menu_plan import MenuDay, MenuMeal, MenuPlan
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


def _plan(meals: list[tuple[int, str]]) -> MenuPlan:
    """Build a MenuPlan from (day, recipe_id) tuples — one dinner per day."""
    days = [
        MenuDay(
            day=day,
            meals=[
                MenuMeal(
                    day=day,
                    meal_type="dinner",
                    recipe_id=rid,
                    recipe_name=f"recipe-{rid}",
                )
            ],
        )
        for day, rid in meals
    ]
    return MenuPlan(days=days)


class TestSingularize:
    @pytest.mark.parametrize(
        "word,expected",
        [
            ("carrots", "carrot"),
            ("onions", "onion"),
            ("tomatoes", "tomato"),
            ("berries", "berry"),
            ("dishes", "dish"),
            ("boxes", "box"),
            # invariant on short words and irregulars we don't try to handle
            ("rice", "rice"),
            ("ass", "ass"),  # 'ss' protected
            ("is", "is"),  # too short
        ],
    )
    def test_singularize_cases(self, word, expected):
        assert _singularize(word) == expected


class TestNormalize:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Chicken Thighs", "chicken thigh"),
            ("long-grain rice", "rice"),
            ("Fresh Tomatoes", "tomato"),
            ("Boneless Skinless Chicken Breast", "chicken breast"),
            ("CARROTS", "carrot"),
            ("Whole Onions", "onion"),
            ("low-fat milk", "milk"),
            ("extra-virgin olive oil", "olive oil"),
            ("  ", ""),
            ("", ""),
        ],
    )
    def test_normalize_cases(self, raw, expected):
        assert _normalize_ingredient(raw) == expected


class TestMatchesAvailable:
    """Direct tests of the matcher with pre-normalized availability sets."""

    @pytest.mark.parametrize(
        "user_says,recipe_says",
        [
            ("chicken", "chicken thighs"),
            ("rice", "long-grain rice"),
            ("carrot", "carrots"),
            ("onion", "onions"),
            ("tomato", "fresh tomatoes"),
            ("CHICKEN", "boneless skinless chicken breast"),
            ("chickens", "chicken thighs"),  # asymmetric plural
        ],
    )
    def test_should_match(self, user_says, recipe_says):
        available = {_normalize_ingredient(user_says)}
        assert _matches_available(recipe_says, available) is True

    @pytest.mark.parametrize(
        "user_says,recipe_says",
        [
            ("chicken", "fish"),
            ("rice", "pasta"),
            ("milk", "egg"),
        ],
    )
    def test_should_not_match(self, user_says, recipe_says):
        available = {_normalize_ingredient(user_says)}
        assert _matches_available(recipe_says, available) is False

    def test_empty_availability_never_matches(self):
        assert _matches_available("chicken", set()) is False

    def test_empty_name_never_matches(self):
        assert _matches_available("", {"chicken"}) is False


class TestCategorize:
    @pytest.mark.parametrize(
        "name,expected",
        [
            # meat
            ("chicken", "meat"),
            ("chicken thighs", "meat"),
            ("beef", "meat"),
            ("ground beef", "meat"),
            ("fish", "meat"),
            ("lamb", "meat"),
            # vegetables
            ("carrot", "vegetables"),
            ("carrots", "vegetables"),
            ("onion", "vegetables"),
            ("celery", "vegetables"),
            ("tomato", "vegetables"),
            ("bell pepper", "vegetables"),
            ("garlic", "vegetables"),
            # grains
            ("rice", "grains"),
            ("long-grain rice", "grains"),
            ("noodles", "grains"),
            ("flour", "grains"),
            ("buckwheat", "grains"),
            # dairy
            ("milk", "dairy"),
            ("cheese", "dairy"),
            ("yogurt", "dairy"),
            ("butter", "dairy"),
            # spices
            ("salt", "spices"),
            ("black pepper", "spices"),
            ("cumin", "spices"),
            ("coriander", "spices"),
            ("bay leaves", "spices"),
            # pantry
            ("oil", "pantry"),
            ("olive oil", "pantry"),
            ("soy sauce", "pantry"),
            ("broth", "pantry"),
            # fallback
            ("quinoa-bowl-mystery", "grains"),  # 'quinoa' is in grains
            ("something_unrecognizable", "other"),
            ("", "other"),
            ("   ", "other"),
        ],
    )
    def test_categorize_examples(self, name, expected):
        assert categorize_ingredient(name) == expected

    def test_black_pepper_does_not_collide_with_bell_pepper(self):
        """Compound spice keyword wins; plain 'pepper' still falls to vegetables."""
        assert categorize_ingredient("black pepper") == "spices"
        assert categorize_ingredient("bell pepper") == "vegetables"
        assert categorize_ingredient("red pepper") == "vegetables"

    def test_case_insensitive(self):
        assert categorize_ingredient("CHICKEN") == "meat"
        assert categorize_ingredient("Bay Leaves") == "spices"


@pytest.fixture
def _force_fallback(monkeypatch):
    """Force the LLM quantity layer to fail so unit tests stay deterministic
    and never call OpenAI."""
    monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", "")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


class TestMenuPlanShortCircuit:
    async def test_menu_plan_null_returns_null_grocery_list(self, _force_fallback):
        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(menu_plan=None)
        )
        assert out.grocery_list is None


class TestIncludesIngredients:
    async def test_menu_plan_exists_includes_planned_recipe_ingredients(
        self, _force_fallback
    ):
        r1 = _recipe(
            id=1, name="Plov", ingredients=["chicken", "rice", "carrot", "onion"]
        )
        r2 = _recipe(
            id=2, name="Lagman", ingredients=["beef", "noodles", "onion", "tomato"]
        )

        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(
                menu_plan=_plan([(1, "1"), (2, "2")]),
                recipes=[r1, r2],
            )
        )

        assert out.grocery_list is not None
        names = {i.name.lower() for i in out.grocery_list.items}
        # Every ingredient from both recipes is present, deduped.
        for expected in {
            "chicken", "rice", "carrot", "onion", "beef", "noodles", "tomato"
        }:
            assert expected in names, f"missing ingredient: {expected}"

    async def test_shared_ingredient_is_deduped_with_recipe_provenance(
        self, _force_fallback
    ):
        r1 = _recipe(id=1, name="Plov", ingredients=["onion", "rice"])
        r2 = _recipe(id=2, name="Lagman", ingredients=["onion", "noodles"])

        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(
                menu_plan=_plan([(1, "1"), (2, "2")]),
                recipes=[r1, r2],
            )
        )

        assert out.grocery_list is not None
        by_name = {i.name.lower(): i for i in out.grocery_list.items}
        assert sorted(by_name["onion"].recipes_used_in) == ["1", "2"]


class TestAlreadyAvailableFlag:
    """Verifies normalization-driven matching: 'chicken' vs 'chicken thighs',
    'rice' vs 'long-grain rice', etc."""

    async def test_already_available_flags_set_via_normalization(
        self, _force_fallback
    ):
        recipe = _recipe(
            id=1,
            name="Plov",
            ingredients=[
                "chicken thighs",
                "long-grain rice",
                "carrots",
                "fresh onions",
                "cumin",
            ],
        )

        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(
                menu_plan=_plan([(1, "1")]),
                recipes=[recipe],
                available_ingredients=["chicken", "rice", "carrot", "onions"],
            )
        )

        assert out.grocery_list is not None
        by_name = {i.name: i for i in out.grocery_list.items}
        assert by_name["chicken thighs"].already_available is True
        assert by_name["long-grain rice"].already_available is True
        assert by_name["carrots"].already_available is True
        assert by_name["fresh onions"].already_available is True
        assert by_name["cumin"].already_available is False

    async def test_no_match_when_availability_is_unrelated(self, _force_fallback):
        recipe = _recipe(id=1, name="Plov", ingredients=["chicken", "rice"])
        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(
                menu_plan=_plan([(1, "1")]),
                recipes=[recipe],
                available_ingredients=["broccoli", "tofu"],
            )
        )
        assert out.grocery_list is not None
        assert all(not i.already_available for i in out.grocery_list.items)


class TestFallbackHasNoQuantities:
    """Without the LLM, items must have null quantity/unit and no estimate
    warning — proves the deterministic path is being exercised."""

    async def test_fallback_quantities_are_null(self, _force_fallback):
        r1 = _recipe(id=1, name="Plov", ingredients=["chicken", "rice"])
        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(menu_plan=_plan([(1, "1")]), recipes=[r1])
        )
        assert out.grocery_list is not None
        for item in out.grocery_list.items:
            assert item.quantity is None
            assert item.unit is None
        assert not any(
            "Quantities are estimates" in w for w in out.grocery_list.warnings
        )


@pytest.mark.integration
class TestLLMQuantityLayer:
    """Exercises the LLM quantity layer end-to-end. Requires OPENAI_API_KEY."""

    async def test_llm_populates_quantities_and_warns(self, require_openai_key):
        r1 = _recipe(
            id=1,
            name="Plov",
            ingredients=["chicken", "rice", "carrot", "onion", "cumin"],
        )
        out = await GroceryListAgent().create_grocery_list(
            GroceryListAgentInput(
                menu_plan=_plan([(1, "1")]),
                recipes=[r1],
                servings=4,
                days=1,
            )
        )
        assert out.grocery_list is not None
        # The LLM should have populated at least one quantity / unit.
        assert any(
            item.quantity is not None or item.unit is not None
            for item in out.grocery_list.items
        )
        # And the estimate disclaimer must be present.
        assert any(
            "Quantities are estimates" in w for w in out.grocery_list.warnings
        )
        # Units (when present) must be from the allowed set.
        allowed_units = {"kg", "g", "pcs", "bunch", "tbsp", "tsp", "liters"}
        for item in out.grocery_list.items:
            if item.unit is not None:
                assert item.unit in allowed_units, item.unit