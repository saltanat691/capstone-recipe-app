"""
Unit tests for the Ingredient Agent — covers the pure normalization and merge
logic without calling OpenAI.
"""

from app.agents.ingredient_agent import (
    IngredientAgent,
    IngredientAgentInput,
    IngredientAgentOutput,
    _dedupe,
    _normalize_one,
    _normalize_restrictions,
)


class TestNormalization:
    def test_normalize_one_lowercases_and_underscores_spaces(self):
        assert _normalize_one("No Pork") == "no_pork"

    def test_normalize_one_collapses_hyphens(self):
        assert _normalize_one("gluten-free") == "gluten_free"

    def test_normalize_one_handles_mixed_separators(self):
        assert _normalize_one("Gluten Free") == "gluten_free"

    def test_normalize_one_preserves_simple_tag(self):
        assert _normalize_one("halal") == "halal"
        assert _normalize_one("vegetarian") == "vegetarian"

    def test_normalize_one_strips_whitespace(self):
        assert _normalize_one("  no pork  ") == "no_pork"

    def test_normalize_restrictions_skips_empty(self):
        out = _normalize_restrictions(["halal", "", "  ", "no pork"])
        assert out == ["halal", "no_pork"]


class TestDedupe:
    def test_dedupe_case_insensitive(self):
        out = _dedupe(["Chicken", "chicken", "CHICKEN"])
        assert out == ["Chicken"]

    def test_dedupe_preserves_first_casing_and_order(self):
        out = _dedupe(["Rice", "chicken", "rice", "Onion"])
        assert out == ["Rice", "chicken", "Onion"]

    def test_dedupe_drops_blank(self):
        assert _dedupe(["", "  ", "rice"]) == ["rice"]


class TestMerge:
    """
    The _merge step is the contract the agent guarantees regardless of what
    the LLM returns. Exercising it directly lets us test merge behavior with
    zero network calls.
    """

    def test_explicit_servings_wins(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x", servings=6),
            IngredientAgentOutput(servings=3, user_intent=""),
        )
        assert merged.servings == 6

    def test_servings_falls_back_to_extracted(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x"),
            IngredientAgentOutput(servings=4, user_intent=""),
        )
        assert merged.servings == 4

    def test_servings_defaults_to_two_when_both_missing(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x"),
            IngredientAgentOutput(servings=0, user_intent=""),
        )
        assert merged.servings == 2

    def test_explicit_days_wins(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x", days=7),
            IngredientAgentOutput(days=3, user_intent=""),
        )
        assert merged.days == 7

    def test_days_can_remain_null(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x"),
            IngredientAgentOutput(user_intent=""),
        )
        assert merged.days is None

    def test_ingredients_are_unioned_and_deduped(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x", available_ingredients=["Rice"]),
            IngredientAgentOutput(
                available_ingredients=["rice", "chicken"], user_intent=""
            ),
        )
        # case-insensitive dedupe preserves first occurrence; order is union
        assert [i.lower() for i in merged.available_ingredients] == ["rice", "chicken"]

    def test_dietary_restrictions_are_normalized_then_deduped(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x", dietary_restrictions=["No Pork"]),
            IngredientAgentOutput(
                dietary_restrictions=["no_pork", "halal"], user_intent=""
            ),
        )
        assert "no_pork" in merged.dietary_restrictions
        assert "halal" in merged.dietary_restrictions
        assert len(merged.dietary_restrictions) == 2  # deduped

    def test_meal_type_passes_through_from_llm(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x"),
            IngredientAgentOutput(meal_type="dinner", user_intent=""),
        )
        assert merged.meal_type == "dinner"

    def test_wants_grocery_list_passes_through_from_llm(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x"),
            IngredientAgentOutput(wants_grocery_list=True, user_intent=""),
        )
        assert merged.wants_grocery_list is True

    def test_wants_grocery_list_defaults_false(self):
        merged = IngredientAgent._merge(
            IngredientAgentInput(message="x"),
            IngredientAgentOutput(user_intent=""),
        )
        assert merged.wants_grocery_list is False