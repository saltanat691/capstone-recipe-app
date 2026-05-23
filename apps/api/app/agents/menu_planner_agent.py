"""
Menu Planner Agent.

Builds an n-day menu plan from retrieved recipes. Prefers an LLM-backed plan
(via langchain-openai structured output); falls back to a deterministic
round-robin when the LLM is unavailable or returns an unusable plan.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.observability import get_logger
from app.schemas.menu_plan import MenuDay, MenuMeal, MenuPlan
from app.schemas.nutrition import NutritionNote
from app.services.rag_recipe_service import (
    _DIET_INGREDIENT_BLOCKLIST,
    RetrievedRecipe,
)

logger = get_logger(__name__)


class MenuPlannerAgentInput(BaseModel):
    """Recipes + user context for menu planning."""

    recipes: list[RetrievedRecipe] = Field(default_factory=list)
    nutrition_notes: list[NutritionNote] = Field(default_factory=list)
    available_ingredients: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    cuisine_preferences: list[str] = Field(default_factory=list)
    requested_meal_types: list[str] = Field(default_factory=list)
    servings: int = 2
    days: Optional[int] = None
    user_intent: Optional[str] = None


class MenuPlannerAgentOutput(BaseModel):
    """Menu plan result. `menu_plan` is None when `days` was not requested."""

    menu_plan: Optional[MenuPlan] = None


_SYSTEM_PROMPT = """You are a menu-planning assistant.

You produce structured n-day menu plans grounded in a list of retrieved
recipes. Follow these rules strictly:

- Prefer the supplied recipes. Do not invent recipes unless there are
  fewer recipes than days and you must fill all days.
- Respect every dietary restriction. Do not place a recipe whose
  ingredients clearly violate a restriction.
- Prefer recipes that match the user's cuisine preferences.
- Use available ingredients in the early days of the plan when possible.
- Avoid placing the same recipe on consecutive days.
- Pick meal_type to match what the user asked for. If the user mentioned
  "dinner menu", set every meal_type to "dinner". If they mentioned
  breakfast/lunch/dinner, use those. Default to "dinner" if no signal.
- `reason` is one short sentence explaining why this recipe was chosen
  for this day. `notes` is a short list of brief, factual remarks (e.g.
  nutrition or batch-cook hints); keep nutrition references brief, never
  medical advice.
- `summary` is one to two sentences summarizing the plan.
- Use `warnings` to flag limited variety (too few recipes for days),
  dietary risks, or any tradeoff you made. Add a warning if you had to
  invent recipes or repeat one on consecutive days.

Set `recipe_id` to the exact id (as a string) of one of the supplied
recipes. If you invent a new recipe to fill a day, leave `recipe_id`
null and set `recipe_name` to a clear short name.

Output structured JSON only; no extra prose.
"""


class MenuPlannerAgent:
    """LLM-backed menu planner with a deterministic round-robin fallback."""

    def __init__(self, model: Optional[str] = None) -> None:
        self.name = "menu_planner_agent"
        self._model_name = model or settings.LLM_MODEL
        self._structured_llm = None  # lazy init
        logger.info(f"Initialized {self.name} with model={self._model_name}")

    # ---- LLM client ----------------------------------------------------

    def _get_structured_llm(self):
        if self._structured_llm is not None:
            return self._structured_llm
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; MenuPlannerAgent cannot call the LLM."
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
        self._structured_llm = llm.with_structured_output(MenuPlan)
        return self._structured_llm

    # ---- Public entrypoint --------------------------------------------

    async def create_menu_plan(
        self, agent_input: MenuPlannerAgentInput
    ) -> MenuPlannerAgentOutput:
        days = agent_input.days
        if not days or days < 1:
            logger.info(
                "MenuPlannerAgent skipped: no days requested",
                extra={"requested_days": days},
            )
            return MenuPlannerAgentOutput(menu_plan=None)

        recipes = agent_input.recipes
        if not recipes:
            return MenuPlannerAgentOutput(
                menu_plan=MenuPlan(
                    days=[],
                    summary="",
                    warnings=["No recipes available for menu planning."],
                )
            )

        try:
            structured_llm = self._get_structured_llm()
            prompt = self._build_prompt(agent_input)
            plan: MenuPlan = await structured_llm.ainvoke(prompt)
            sanitized = self._sanitize(plan, agent_input)
            logger.info(
                "MenuPlannerAgent.create_menu_plan complete (LLM)",
                extra={
                    "days": days,
                    "result_days": len(sanitized.days),
                    "warnings": len(sanitized.warnings),
                },
            )
            return MenuPlannerAgentOutput(menu_plan=sanitized)
        except Exception as e:
            logger.warning(
                "llm_event",
                extra={
                    "event": "llm_fallback",
                    "agent": "menu_planner_agent",
                    "reason": str(e),
                },
            )
            return MenuPlannerAgentOutput(
                menu_plan=self._deterministic_fallback(agent_input, reason=str(e))
            )

    # ---- Prompt + sanitation ------------------------------------------

    def _build_prompt(self, agent_input: MenuPlannerAgentInput) -> str:
        recipe_lines = []
        for r in agent_input.recipes:
            ingredients = ", ".join(r.ingredients) or "(unknown)"
            recipe_lines.append(
                f"- id={r.id} | name={r.name} | cuisine={r.cuisine or 'unknown'} "
                f"| ingredients: {ingredients}"
            )
        recipes_block = "\n".join(recipe_lines) or "(none)"

        nutrition_lines = []
        for note in agent_input.nutrition_notes:
            cal = note.estimate.calories
            cal_str = f"{cal} kcal" if cal is not None else "calories unknown"
            nutrition_lines.append(
                f"- {note.recipe_name}: {cal_str} (confidence={note.confidence})"
            )
        nutrition_block = "\n".join(nutrition_lines) or "(none)"

        available = ", ".join(agent_input.available_ingredients) or "(none)"
        restrictions = ", ".join(agent_input.dietary_restrictions) or "(none)"
        cuisines = ", ".join(agent_input.cuisine_preferences) or "(none)"
        meal_types = (
            ", ".join(agent_input.requested_meal_types)
            if agent_input.requested_meal_types
            else "(unspecified — default to dinner)"
        )
        intent = agent_input.user_intent or "(unspecified)"

        return (
            f"{_SYSTEM_PROMPT}\n"
            f"---\n"
            f"User intent: {intent}\n"
            f"Days to plan: {agent_input.days}\n"
            f"Requested meal types: {meal_types}\n"
            f"Servings per meal: {agent_input.servings}\n"
            f"Dietary restrictions: {restrictions}\n"
            f"Cuisine preferences: {cuisines}\n"
            f"Available ingredients: {available}\n"
            f"Retrieved recipes ({len(agent_input.recipes)}):\n"
            f"{recipes_block}\n"
            f"Nutrition notes:\n"
            f"{nutrition_block}\n"
            f"---\n"
            f"Produce a {agent_input.days}-day plan that satisfies the rules. "
            f"Use exactly the requested meal types for each day."
        )

    @staticmethod
    def _sanitize(plan: MenuPlan, agent_input: MenuPlannerAgentInput) -> MenuPlan:
        """
        Defensive cleanup of LLM output:
        - Replace recipe_ids the LLM hallucinated with None.
        - Re-stamp `MenuMeal.day` to match its enclosing `MenuDay`.
        - Add a warning if the plan has fewer days than requested.
        """
        valid_ids = {str(r.id) for r in agent_input.recipes}
        warnings = list(plan.warnings or [])

        cleaned_days: list[MenuDay] = []
        for day in plan.days:
            cleaned_meals: list[MenuMeal] = []
            for meal in day.meals:
                recipe_id = meal.recipe_id
                if recipe_id and recipe_id not in valid_ids:
                    recipe_id = None  # LLM invented an id that doesn't exist
                cleaned_meals.append(
                    MenuMeal(
                        day=day.day,
                        meal_type=meal.meal_type or "dinner",
                        recipe_id=recipe_id,
                        recipe_name=meal.recipe_name,
                        reason=meal.reason or "",
                        notes=meal.notes or [],
                    )
                )
            cleaned_days.append(MenuDay(day=day.day, meals=cleaned_meals))

        warnings.extend(_validate_plan(cleaned_days, agent_input))

        return MenuPlan(
            days=cleaned_days,
            summary=plan.summary or "",
            warnings=_dedupe(warnings),
        )

    # ---- Deterministic fallback ---------------------------------------

    @staticmethod
    def _deterministic_fallback(
        agent_input: MenuPlannerAgentInput, *, reason: str
    ) -> MenuPlan:
        days = agent_input.days or 1
        recipes = agent_input.recipes
        warnings: list[str] = [f"Menu planner LLM unavailable: {reason}"]

        if len(recipes) < days:
            warnings.append(
                f"Only {len(recipes)} unique recipe(s) available for a {days}-day "
                f"plan; recipes will repeat."
            )

        meal_types = agent_input.requested_meal_types or ["dinner"]

        menu_days: list[MenuDay] = []
        rotation = 0
        for day_num in range(1, days + 1):
            meals: list[MenuMeal] = []
            for meal_type in meal_types:
                recipe = recipes[rotation % len(recipes)]
                rotation += 1
                meals.append(
                    MenuMeal(
                        day=day_num,
                        meal_type=meal_type,
                        recipe_id=str(recipe.id),
                        recipe_name=recipe.name,
                        reason=recipe.match_reason
                        or "Selected by retrieval ranking",
                        notes=[],
                    )
                )
            menu_days.append(MenuDay(day=day_num, meals=meals))

        warnings.extend(_validate_plan(menu_days, agent_input))

        summary = (
            f"{days}-day fallback plan using {min(len(recipes), days * len(meal_types))} "
            f"unique recipe(s)"
            + (" (rotated)" if len(recipes) < days * len(meal_types) else "")
            + f" for {agent_input.servings} servings per meal."
        )
        return MenuPlan(days=menu_days, summary=summary, warnings=_dedupe(warnings))


def _validate_plan(
    days: list[MenuDay], agent_input: MenuPlannerAgentInput
) -> list[str]:
    """
    Deterministic checks that run regardless of which path produced the plan
    (LLM or fallback). Returns a list of warnings; never raises and never
    mutates the plan.
    """
    warnings: list[str] = []

    recipes_by_id: dict[str, RetrievedRecipe] = {
        str(r.id): r for r in agent_input.recipes
    }
    excluded_lower = {
        e.strip().lower() for e in agent_input.excluded_ingredients if e and e.strip()
    }
    diet_keys = {
        _normalize_restriction(r)
        for r in agent_input.dietary_restrictions
        if r and r.strip()
    }

    # 1 & 2 & 3: dietary restriction + excluded-ingredient checks per meal.
    for day in days:
        for meal in day.meals:
            recipe = recipes_by_id.get(meal.recipe_id) if meal.recipe_id else None
            ingredient_names = (
                {n.strip().lower() for n in recipe.ingredients if n.strip()}
                if recipe
                else set()
            )
            if not ingredient_names:
                # Invented or unmatched recipe — can't check, skip silently.
                continue

            for excluded in excluded_lower:
                if _find_match(ingredient_names, excluded):
                    warnings.append(
                        f"Day {day.day} {meal.meal_type} '{meal.recipe_name}' "
                        f"contains excluded ingredient: {excluded}."
                    )

            for restriction in diet_keys:
                blocklist = _DIET_INGREDIENT_BLOCKLIST.get(restriction)
                if not blocklist:
                    continue
                for blocked in blocklist:
                    if _find_match(ingredient_names, blocked):
                        warnings.append(
                            f"Day {day.day} {meal.meal_type} '{meal.recipe_name}' "
                            f"may conflict with restriction: {restriction}."
                        )
                        break

    # 4. Consecutive-day repeat of the same recipe.
    for prev, curr in zip(days, days[1:]):
        prev_ids = {m.recipe_id for m in prev.meals if m.recipe_id}
        for meal in curr.meals:
            if meal.recipe_id and meal.recipe_id in prev_ids:
                warnings.append(
                    f"Recipe '{meal.recipe_name}' appears on consecutive days "
                    f"{prev.day} and {curr.day}."
                )

    # 5. Day count mismatch.
    if agent_input.days and len(days) != agent_input.days:
        warnings.append(
            f"Plan has {len(days)} day(s); {agent_input.days} were requested."
        )

    return warnings


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
        text = (item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out