"""
Nutrition Agent.

For each retrieved recipe, asks an LLM (via langchain-openai structured output)
to produce an estimated nutrition profile + health/safety notes. Per-recipe
calls are issued in parallel; any single failure falls back to a
low-confidence placeholder so one bad call doesn't break the whole batch.

USDA grounding (optional):
    When USDA_API_KEY is set the agent first calls the USDA Nutrition MCP
    server (apps/api/app/mcp_server.py) via stdio to fetch authoritative
    per-100 g macros for the leading ingredients of each recipe.  These
    values are injected into the LLM prompt so the model can scale them to
    per-serving estimates, raising confidence from "low" to at least
    "medium".  The NutritionNote.usda_grounded flag is set when USDA data
    was used.  The MCP call is best-effort: any failure silently falls back
    to pure LLM estimation.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.observability import get_logger
from app.schemas.nutrition import NutritionEstimate, NutritionNote
from app.services.rag_recipe_service import (
    _DIET_INGREDIENT_BLOCKLIST,
    RetrievedRecipe,
)

logger = get_logger(__name__)

# Absolute path to the MCP server script (sibling of this file's package root).
_MCP_SERVER_SCRIPT = str(Path(__file__).parent.parent / "mcp_server.py")


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
- When USDA reference data is provided below, use it to scale per-serving
  estimates. Prefer those values over pure guesses; set confidence="high"
  if the USDA data covers the main ingredients.

You output structured data only. health_notes should be short, factual,
non-prescriptive observations (e.g. "High in carbohydrates from rice.").
"""


class NutritionAgent:
    """LLM-backed per-recipe nutrition estimator with USDA grounding via MCP."""

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
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        self._structured_llm = llm.with_structured_output(_LLMNutritionEstimate)
        return self._structured_llm

    # ---- Public entrypoint ---------------------------------------------

    async def enrich_recipes(
        self, agent_input: NutritionAgentInput
    ) -> NutritionAgentOutput:
        if not agent_input.recipes:
            return NutritionAgentOutput(notes=[])

        # Fetch USDA reference data via MCP (best-effort; returns {} if
        # USDA_API_KEY is unset or the subprocess fails).
        usda_nutrients = await self._fetch_usda_data_via_mcp(agent_input.recipes)

        try:
            structured_llm = self._get_structured_llm()
        except RuntimeError as e:
            logger.warning(
                "llm_event",
                extra={
                    "event": "llm_fallback",
                    "agent": "nutrition_agent",
                    "scope": "batch",
                    "reason": str(e),
                },
            )
            return NutritionAgentOutput(
                notes=[
                    self._fallback_note(recipe, agent_input, reason=str(e))
                    for recipe in agent_input.recipes
                ]
            )

        tasks = [
            self._estimate_one(structured_llm, recipe, agent_input, usda_nutrients)
            for recipe in agent_input.recipes
        ]
        notes = await asyncio.gather(*tasks)

        logger.info(
            "NutritionAgent.enrich_recipes complete",
            extra={
                "recipe_count": len(notes),
                "usda_grounded": sum(1 for n in notes if n.usda_grounded),
                "fallbacks": sum(
                    1
                    for n in notes
                    if any(w.startswith("Estimation failed") for w in n.warnings)
                ),
            },
        )
        return NutritionAgentOutput(notes=list(notes))

    # ---- MCP / USDA data fetch -----------------------------------------

    async def _fetch_usda_data_via_mcp(
        self, recipes: list[RetrievedRecipe]
    ) -> dict[str, dict]:
        """
        Open one MCP stdio session and look up per-100 g nutrients for the
        leading ingredients of every recipe in parallel.

        Returns {ingredient_name_lower: nutrients_dict}.
        Returns {} silently when USDA_API_KEY is unset or anything fails.
        """
        if not settings.USDA_API_KEY:
            return {}

        # Collect up to 2 unique ingredients per recipe (deduped, lowercase key).
        unique_ingredients: list[str] = []
        seen: set[str] = set()
        for recipe in recipes:
            for ing in recipe.ingredients[:2]:
                key = ing.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    unique_ingredients.append(ing.strip())

        if not unique_ingredients:
            return {}

        try:
            from mcp import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client

            params = StdioServerParameters(
                command=sys.executable,
                args=[_MCP_SERVER_SCRIPT],
                env=dict(os.environ),
            )

            results: dict[str, dict] = {}
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    # Fire all ingredient lookups in parallel within one session.
                    calls = [
                        session.call_tool(
                            "get_ingredient_nutrients",
                            {"ingredient_name": ing},
                        )
                        for ing in unique_ingredients
                    ]
                    responses = await asyncio.gather(*calls, return_exceptions=True)

            for ing, resp in zip(unique_ingredients, responses):
                if isinstance(resp, BaseException):
                    continue
                text = ""
                content = getattr(resp, "content", None)
                if content:
                    text = getattr(content[0], "text", "")
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and data:
                        results[ing.strip().lower()] = data
                except (json.JSONDecodeError, ValueError):
                    pass

            logger.info(
                "mcp_usda_batch_complete",
                extra={
                    "ingredients_queried": len(unique_ingredients),
                    "ingredients_found": len(results),
                },
            )
            return results

        except Exception as exc:
            logger.warning(
                "mcp_usda_fetch_failed",
                extra={"reason": str(exc)},
            )
            return {}

    # ---- Per-recipe call -----------------------------------------------

    async def _estimate_one(
        self,
        structured_llm,
        recipe: RetrievedRecipe,
        agent_input: NutritionAgentInput,
        usda_nutrients: dict[str, dict],
    ) -> NutritionNote:
        # Gather USDA data for this recipe's top ingredients.
        recipe_usda: dict[str, dict] = {}
        for ing in recipe.ingredients[:3]:
            key = ing.strip().lower()
            if key in usda_nutrients:
                recipe_usda[ing] = usda_nutrients[key]

        prompt = self._build_prompt(recipe, agent_input, recipe_usda)
        try:
            estimate: _LLMNutritionEstimate = await structured_llm.ainvoke(prompt)
        except Exception as e:
            logger.warning(
                "llm_event",
                extra={
                    "event": "llm_fallback",
                    "agent": "nutrition_agent",
                    "scope": "recipe",
                    "recipe_id": recipe.id,
                    "reason": str(e),
                },
            )
            return self._fallback_note(recipe, agent_input, reason=str(e))

        safety_warnings = _deterministic_safety_warnings(recipe, agent_input)

        # When USDA data was available, upgrade a "low" confidence to "medium"
        # and note the authoritative source.
        confidence = estimate.confidence
        health_notes = list(estimate.health_notes)
        if recipe_usda:
            if confidence == "low":
                confidence = "medium"
            health_notes = [
                "Macronutrient estimate grounded with USDA FoodData Central data.",
                *health_notes,
            ]

        # Independently verify the LLM-reported confidence using deterministic
        # rules — override downward when the estimate looks unreliable.
        confidence, verification_warnings = _verify_confidence(
            estimate, recipe, recipe_usda, confidence
        )

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
            health_notes=_dedupe(_ensure_estimate_disclaimer(health_notes)),
            warnings=_dedupe([*safety_warnings, *estimate.warnings, *verification_warnings]),
            confidence=confidence,
            usda_grounded=bool(recipe_usda),
        )

    # ---- Prompt + fallback helpers --------------------------------------

    def _build_prompt(
        self,
        recipe: RetrievedRecipe,
        agent_input: NutritionAgentInput,
        recipe_usda: dict[str, dict],
    ) -> str:
        ingredients = ", ".join(recipe.ingredients) or "(unknown)"
        instructions_preview = ""
        if recipe.instructions:
            instructions_preview = " ".join(recipe.instructions)[:400]

        restrictions = ", ".join(agent_input.dietary_restrictions) or "(none)"
        preferences = agent_input.user_preferences or "(none)"

        usda_section = ""
        if recipe_usda:
            lines: list[str] = []
            for ing, nutrients in recipe_usda.items():
                parts: list[str] = []
                if "calories_kcal" in nutrients:
                    parts.append(f"{nutrients['calories_kcal']} kcal")
                if "protein_g" in nutrients:
                    parts.append(f"{nutrients['protein_g']} g protein")
                if "fat_g" in nutrients:
                    parts.append(f"{nutrients['fat_g']} g fat")
                if "carbs_g" in nutrients:
                    parts.append(f"{nutrients['carbs_g']} g carbs")
                if parts:
                    lines.append(f"  - {ing} (per 100 g): {', '.join(parts)}")
            if lines:
                usda_section = (
                    "\nUSDA FoodData Central reference data"
                    " (scale by estimated quantity per serving):\n"
                    + "\n".join(lines)
                    + "\n"
                )

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
            f"{usda_section}"
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
            usda_grounded=False,
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


_CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}
_CONFIDENCE_LEVELS: list[Literal["low", "medium", "high"]] = ["low", "medium", "high"]


def _downgrade(
    current: Literal["low", "medium", "high"],
) -> Literal["low", "medium", "high"]:
    idx = max(0, _CONFIDENCE_ORDER[current] - 1)
    return _CONFIDENCE_LEVELS[idx]


def _verify_confidence(
    estimate: "_LLMNutritionEstimate",
    recipe: "RetrievedRecipe",
    recipe_usda: dict[str, dict],
    current: Literal["low", "medium", "high"],
) -> tuple[Literal["low", "medium", "high"], list[str]]:
    """
    Deterministically check the LLM-reported confidence and lower it when
    the estimate shows clear signs of unreliability.

    Rules (applied in order; each may downgrade by one level):
      1. Macro completeness  — if calories AND protein_g are both None, force "low".
      2. Calorie sanity      — per-serving calories outside [50, 2 500] kcal triggers
                               a one-level downgrade + warning.
      3. "High" without USDA — LLM cannot claim "high" confidence without USDA
                               grounding; capped at "medium".
    """
    warnings: list[str] = []
    confidence = current

    # Rule 1: not enough macro data to trust even a "medium" rating.
    if estimate.calories is None and estimate.protein_g is None:
        confidence = "low"
        warnings.append(
            "Confidence downgraded: calories and protein could not be estimated."
        )
        return confidence, warnings

    # Rule 2: calorie sanity bounds (per-serving, typical main meal).
    if estimate.calories is not None:
        if estimate.calories < 50:
            confidence = _downgrade(confidence)
            warnings.append(
                f"Estimated calories ({estimate.calories} kcal) are unusually low "
                "for a single serving; estimate may be unreliable."
            )
        elif estimate.calories > 2500:
            confidence = _downgrade(confidence)
            warnings.append(
                f"Estimated calories ({estimate.calories} kcal) are unusually high "
                "for a single serving; estimate may be unreliable."
            )

    # Rule 3: "high" without USDA grounding is not independently verifiable.
    if confidence == "high" and not recipe_usda:
        confidence = "medium"
        warnings.append(
            "Confidence capped at 'medium': 'high' requires USDA-grounded data."
        )

    return confidence, warnings


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
