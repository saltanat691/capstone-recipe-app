"""
Nutrition Agent.

For each retrieved recipe, asks an LLM (via langchain-openai structured output)
to produce an estimated nutrition profile + health/safety notes. Per-recipe
calls are issued in parallel; any single failure falls back to a
low-confidence placeholder so one bad call doesn't break the whole batch.
"""

from typing import Literal, Optional

import asyncio

from pydantic import BaseModel, Field

from app.core.config import settings
from app.observability import get_logger
from app.schemas.nutrition import NutritionEstimate, NutritionNote
from app.services.rag_recipe_service import (
    _DIET_INGREDIENT_BLOCKLIST,
    RetrievedRecipe,
)

logger = get_logger(__name__)


class NutritionAgentInput(BaseModel):
    """Inputs to the nutrition agent: recipes + relevant user context."""

    recipes: list[RetrievedRecipe] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    servings: int = 2
    user_preferences: Optional[str] = None


class NutritionAgentOutput(BaseModel):
    """A NutritionNote per input recipe, in the same order."""

    notes: list[NutritionNote] = Field(default_factory=list)


class _LLMNutritionEstimate(BaseModel):
    """
    Schema requested from the LLM. Kept separate from NutritionNote so the
    model only fills nutritional fields (recipe identity is set in code).
    """

    calories: Optional[int] = None
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    health_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"


_SYSTEM_PROMPT = """You estimate nutrition for cooking recipes.

Hard rules:
- All numerical values are ESTIMATES, not measured. Never claim precision.
- NEVER provide medical advice or recommend specific health actions.
- Quantities are usually missing from the recipe text — when so, set
  confidence="low" or "medium" and add a health_note that the estimate is
  rough.
- Use per-serving values (assume the recipe is divided into the given number
  of servings).
- Only emit a `warnings` entry when an ingredient conflicts with a
  restriction or allergen the user EXPLICITLY listed. Never volunteer
  warnings about "common allergens" the user did not mention (e.g. do NOT
  warn about dairy, alcohol, gluten, nuts, or shellfish unless those are
  in the user's dietary_restrictions). If the user listed nothing, leave
  `warnings` empty.
- Use sensible bounds. Reject negatives. Use null when you genuinely cannot
  estimate a field.

You output structured data only. health_notes should be short, factual,
non-prescriptive observations (e.g. "High in carbohydrates from rice.").
"""


class NutritionAgent:
    """LLM-backed per-recipe nutrition estimator with graceful fallback."""

    def __init__(self, model: Optional[str] = None) -> None:
        self.name = "nutrition_agent"
        self._model_name = model or settings.LLM_MODEL
        self._structured_llm = None  # lazy init
        logger.info(f"Initialized {self.name} with model={self._model_name}")

    # ---- LLM client -----------------------------------------------------

    def _get_structured_llm(self):
        if self._structured_llm is not None:
            return self._structured_llm
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; NutritionAgent cannot call the LLM."
            )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise RuntimeError(
                "langchain-openai is not installed; "
                "run `pip install -r requirements.txt`."
            ) from e

        llm = ChatOpenAI(
            model=self._model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        self._structured_llm = llm.with_structured_output(_LLMNutritionEstimate)
        return self._structured_llm

    # ---- Public entrypoint ---------------------------------------------

    async def enrich_recipes(
        self, agent_input: NutritionAgentInput
    ) -> NutritionAgentOutput:
        if not agent_input.recipes:
            return NutritionAgentOutput(notes=[])

        try:
            structured_llm = self._get_structured_llm()
        except RuntimeError as e:
            logger.warning(f"NutritionAgent unavailable: {e}")
            return NutritionAgentOutput(
                notes=[
                    self._fallback_note(recipe, agent_input, reason=str(e))
                    for recipe in agent_input.recipes
                ]
            )

        tasks = [
            self._estimate_one(structured_llm, recipe, agent_input)
            for recipe in agent_input.recipes
        ]
        notes = await asyncio.gather(*tasks)

        logger.info(
            "NutritionAgent.enrich_recipes complete",
            extra={
                "recipe_count": len(notes),
                "fallbacks": sum(
                    1
                    for n in notes
                    if any(w.startswith("Estimation failed") for w in n.warnings)
                ),
            },
        )
        return NutritionAgentOutput(notes=notes)

    # ---- Per-recipe call -----------------------------------------------

    async def _estimate_one(
        self,
        structured_llm,
        recipe: RetrievedRecipe,
        agent_input: NutritionAgentInput,
    ) -> NutritionNote:
        prompt = self._build_prompt(recipe, agent_input)
        try:
            estimate: _LLMNutritionEstimate = await structured_llm.ainvoke(prompt)
        except Exception as e:
            logger.error(
                "NutritionAgent LLM call failed",
                extra={"recipe_id": recipe.id, "error": str(e)},
            )
            return self._fallback_note(recipe, agent_input, reason=str(e))

        safety_warnings = _deterministic_safety_warnings(recipe, agent_input)
        return NutritionNote(
            recipe_id=str(recipe.id),
            recipe_name=recipe.name,
            estimate=NutritionEstimate(
                calories=estimate.calories,
                protein_g=estimate.protein_g,
                carbs_g=estimate.carbs_g,
                fat_g=estimate.fat_g,
                fiber_g=estimate.fiber_g,
                sugar_g=estimate.sugar_g,
                sodium_mg=estimate.sodium_mg,
            ),
            health_notes=_dedupe(_ensure_estimate_disclaimer(estimate.health_notes)),
            warnings=_dedupe([*safety_warnings, *estimate.warnings]),
            confidence=estimate.confidence,
        )

    # ---- Prompt + fallback helpers --------------------------------------

    def _build_prompt(
        self, recipe: RetrievedRecipe, agent_input: NutritionAgentInput
    ) -> str:
        ingredients = ", ".join(recipe.ingredients) or "(unknown)"
        instructions_preview = ""
        if recipe.instructions:
            joined = " ".join(recipe.instructions)
            instructions_preview = joined[:400]

        restrictions = ", ".join(agent_input.dietary_restrictions) or "(none)"
        preferences = agent_input.user_preferences or "(none)"

        return (
            f"{_SYSTEM_PROMPT}\n"
            f"---\n"
            f"Recipe name: {recipe.name}\n"
            f"Cuisine: {recipe.cuisine or 'unknown'}\n"
            f"Ingredients: {ingredients}\n"
            f"Instructions (excerpt): {instructions_preview}\n"
            f"Servings target: {agent_input.servings}\n"
            f"User dietary restrictions: {restrictions}\n"
            f"User preferences: {preferences}\n"
            f"---\n"
            f"Produce a per-serving nutrition estimate following the rules."
        )

    @staticmethod
    def _fallback_note(
        recipe: RetrievedRecipe,
        agent_input: NutritionAgentInput,
        *,
        reason: str,
    ) -> NutritionNote:
        safety = _deterministic_safety_warnings(recipe, agent_input)
        return NutritionNote(
            recipe_id=str(recipe.id),
            recipe_name=recipe.name,
            estimate=NutritionEstimate(),
            health_notes=["Nutrition estimate unavailable for this recipe."],
            warnings=_dedupe([*safety, f"Estimation failed: {reason}"]),
            confidence="low",
        )


# ---- Module-level helpers ------------------------------------------------


_ESTIMATE_DISCLAIMER = (
    "All nutritional values are rough estimates and not medical advice."
)


def _ensure_estimate_disclaimer(health_notes: list[str]) -> list[str]:
    if any("estimate" in n.lower() for n in health_notes):
        return list(health_notes)
    return [_ESTIMATE_DISCLAIMER, *health_notes]


def _deterministic_safety_warnings(
    recipe: RetrievedRecipe, agent_input: NutritionAgentInput
) -> list[str]:
    """
    Scan recipe ingredients for conflicts that should never depend on the LLM
    to catch: explicit excluded ingredients, normalized dietary restrictions
    via the shared blocklist, and any caller-supplied allergens.
    """
    ingredient_names_lower = {n.strip().lower() for n in recipe.ingredients if n.strip()}
    warnings: list[str] = []

    for excluded in agent_input.excluded_ingredients:
        match = _find_match(ingredient_names_lower, excluded.strip().lower())
        if match:
            warnings.append(
                f"Recipe contains excluded ingredient: {excluded.strip()}."
            )

    for restriction in agent_input.dietary_restrictions:
        key = _normalize_restriction(restriction)
        blocklist = _DIET_INGREDIENT_BLOCKLIST.get(key)
        if not blocklist:
            continue
        for blocked in blocklist:
            if _find_match(ingredient_names_lower, blocked):
                warnings.append(
                    f"Recipe may conflict with restriction: {key}."
                )
                break

    for allergen in agent_input.allergens:
        allergen_clean = allergen.strip().lower()
        if allergen_clean and _find_match(ingredient_names_lower, allergen_clean):
            warnings.append(
                f"Recipe may contain allergen: {allergen.strip()}."
            )

    return _dedupe(warnings)


def _normalize_restriction(s: str) -> str:
    return s.strip().lower().replace("-", "_").replace(" ", "_")


def _find_match(ingredient_names_lower: set[str], needle: str) -> bool:
    if not needle:
        return False
    for name in ingredient_names_lower:
        if needle in name or name in needle:
            return True
    return False


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = item.strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out