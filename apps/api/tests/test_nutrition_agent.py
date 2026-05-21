"""
Unit tests for the Nutrition Agent.

These tests cover the deterministic safety check and the fallback note path —
neither requires the OpenAI API.
"""

import pytest

from app.agents.nutrition_agent import (
    NutritionAgent,
    NutritionAgentInput,
    _deterministic_safety_warnings,
)
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


class TestFallbackNote:
    """The fallback path is taken when the LLM is unavailable. It must still
    produce a well-formed NutritionNote so the rest of the pipeline keeps
    working."""

    def test_fallback_returns_low_confidence(self):
        recipe = _recipe()
        note = NutritionAgent._fallback_note(
            recipe, NutritionAgentInput(recipes=[recipe]), reason="no key"
        )
        assert note.confidence == "low"

    def test_fallback_estimate_is_empty(self):
        recipe = _recipe()
        note = NutritionAgent._fallback_note(
            recipe, NutritionAgentInput(recipes=[recipe]), reason="no key"
        )
        assert note.estimate.calories is None
        assert note.estimate.protein_g is None
        assert note.estimate.carbs_g is None
        assert note.estimate.fat_g is None

    def test_fallback_carries_reason_in_warnings(self):
        recipe = _recipe()
        note = NutritionAgent._fallback_note(
            recipe,
            NutritionAgentInput(recipes=[recipe]),
            reason="OPENAI_API_KEY is not set",
        )
        assert any(
            w.startswith("Estimation failed") and "OPENAI_API_KEY" in w
            for w in note.warnings
        )

    def test_fallback_carries_recipe_identity(self):
        recipe = _recipe(id=42, name="Plov")
        note = NutritionAgent._fallback_note(
            recipe, NutritionAgentInput(recipes=[recipe]), reason="x"
        )
        assert note.recipe_id == "42"
        assert note.recipe_name == "Plov"

    def test_fallback_includes_deterministic_safety_warnings(self):
        """
        Even when the LLM is unavailable, deterministic restriction checks
        must still fire.
        """
        recipe = _recipe(ingredients=["bacon", "eggs"])
        note = NutritionAgent._fallback_note(
            recipe,
            NutritionAgentInput(recipes=[recipe], dietary_restrictions=["no pork"]),
            reason="x",
        )
        assert any("no_pork" in w for w in note.warnings)


class TestDeterministicSafetyWarnings:
    """The deterministic check must catch restrictions, excluded ingredients,
    and explicit allergens — independent of the LLM."""

    def test_no_warnings_when_no_conflicts(self):
        recipe = _recipe(ingredients=["chicken", "rice", "carrot"])
        warnings = _deterministic_safety_warnings(
            recipe,
            NutritionAgentInput(recipes=[recipe], dietary_restrictions=["no pork"]),
        )
        assert warnings == []

    def test_dietary_restriction_no_pork(self):
        recipe = _recipe(ingredients=["bacon", "eggs"])
        warnings = _deterministic_safety_warnings(
            recipe,
            NutritionAgentInput(recipes=[recipe], dietary_restrictions=["no pork"]),
        )
        assert "Recipe may conflict with restriction: no_pork." in warnings

    def test_dietary_restriction_normalization(self):
        """'gluten-free', 'gluten free', and 'gluten_free' must all be
        treated as the same restriction key."""
        recipe = _recipe(ingredients=["wheat flour"])
        for spelling in ["gluten-free", "gluten free", "gluten_free"]:
            warnings = _deterministic_safety_warnings(
                recipe,
                NutritionAgentInput(
                    recipes=[recipe], dietary_restrictions=[spelling]
                ),
            )
            assert any("gluten_free" in w for w in warnings), (
                f"Failed for spelling: {spelling!r}"
            )

    def test_excluded_ingredient_warning(self):
        recipe = _recipe(ingredients=["bacon", "eggs"])
        warnings = _deterministic_safety_warnings(
            recipe,
            NutritionAgentInput(recipes=[recipe], excluded_ingredients=["bacon"]),
        )
        assert "Recipe contains excluded ingredient: bacon." in warnings

    def test_allergen_warning(self):
        recipe = _recipe(ingredients=["peanut butter", "bread"])
        warnings = _deterministic_safety_warnings(
            recipe,
            NutritionAgentInput(recipes=[recipe], allergens=["peanut"]),
        )
        assert "Recipe may contain allergen: peanut." in warnings

    def test_unknown_restriction_is_ignored(self):
        """Unknown restriction keys must not raise and must not over-warn."""
        recipe = _recipe(ingredients=["chicken", "rice"])
        warnings = _deterministic_safety_warnings(
            recipe,
            NutritionAgentInput(
                recipes=[recipe], dietary_restrictions=["something_weird"]
            ),
        )
        # No deterministic mapping → no deterministic warning
        assert all("something_weird" not in w for w in warnings)

    def test_warnings_are_deduplicated(self):
        recipe = _recipe(ingredients=["bacon", "ham", "prosciutto"])
        warnings = _deterministic_safety_warnings(
            recipe,
            NutritionAgentInput(recipes=[recipe], dietary_restrictions=["no_pork"]),
        )
        # All three ingredients map to no_pork but we should see one warning.
        no_pork_warnings = [w for w in warnings if "no_pork" in w]
        assert len(no_pork_warnings) == 1


class TestEnrichRecipesNoKey:
    """End-to-end test of enrich_recipes in fallback mode (no OPENAI key).
    This exercises the contract clients depend on: enrich_recipes never
    raises, always returns one NutritionNote per input recipe."""

    async def test_returns_one_fallback_note_per_recipe(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.OPENAI_API_KEY", "")
        # Belt-and-suspenders: also clear the env so anything reading os.environ
        # at construction time doesn't sneak past.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        agent = NutritionAgent()
        recipes = [
            _recipe(id=1, name="Plov", ingredients=["chicken", "rice"]),
            _recipe(id=2, name="Bacon Bowl", ingredients=["bacon"]),
        ]
        out = await agent.enrich_recipes(
            NutritionAgentInput(recipes=recipes, dietary_restrictions=["no pork"])
        )

        assert len(out.notes) == 2
        for note in out.notes:
            assert note.confidence == "low"
            assert note.estimate.calories is None
            assert any("Estimation failed" in w for w in note.warnings)

        # And the recipe with bacon must carry the deterministic restriction warning.
        bacon_note = next(n for n in out.notes if n.recipe_name == "Bacon Bowl")
        assert any("no_pork" in w for w in bacon_note.warnings)

    async def test_empty_input_returns_empty(self):
        out = await NutritionAgent().enrich_recipes(NutritionAgentInput(recipes=[]))
        assert out.notes == []