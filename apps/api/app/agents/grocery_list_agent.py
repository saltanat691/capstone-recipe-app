"""
Grocery List Agent.

Builds a grocery list from a menu plan plus the retrieved recipes referenced
by that plan. Aggregation, categorization, and the `already_available` flag
are always deterministic. When an OpenAI key is configured, the agent
additionally asks an LLM to estimate quantities and units for each
ingredient; on any LLM failure it gracefully falls back to a list without
quantities.
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.observability import get_logger
from app.schemas.grocery_list import GroceryItem, GroceryList
from app.schemas.menu_plan import MenuPlan
from app.services.rag_recipe_service import RetrievedRecipe

logger = get_logger(__name__)


class GroceryListAgentInput(BaseModel):
    """Menu plan + recipe catalog + the ingredients the user already has."""

    menu_plan: Optional[MenuPlan] = None
    recipes: list[RetrievedRecipe] = Field(default_factory=list)
    available_ingredients: list[str] = Field(default_factory=list)
    servings: int = 2
    days: Optional[int] = None


class GroceryListAgentOutput(BaseModel):
    """`grocery_list` is None when no menu plan was provided."""

    grocery_list: Optional[GroceryList] = None


# Practical units the LLM may use. Anything else is dropped to None.
_ALLOWED_UNITS = frozenset({"kg", "g", "pcs", "bunch", "tbsp", "tsp", "liters"})


class _LLMQuantityEstimate(BaseModel):
    """Per-ingredient quantity estimate from the LLM."""

    name: str
    quantity: Optional[float] = Field(default=None, ge=0)
    unit: Optional[
        Literal["kg", "g", "pcs", "bunch", "tbsp", "tsp", "liters"]
    ] = None


class _LLMQuantities(BaseModel):
    """Structured-output schema for the quantity-estimation call."""

    estimates: list[_LLMQuantityEstimate] = Field(default_factory=list)


_ESTIMATE_WARNING = (
    "Quantities are estimates because recipe ingredient amounts are incomplete."
)


_LLM_SYSTEM_PROMPT = """You estimate grocery quantities for a meal plan.

Hard rules:
- Every numeric value is an ESTIMATE. Never claim precision.
- Do NOT provide medical advice or recommend specific health actions.
- Quantities scale with the number of servings and the number of days/meals
  the ingredient appears in.
- Use only these units: kg, g, pcs, bunch, tbsp, tsp, liters. Choose the
  most practical unit per ingredient. If you cannot estimate, return null
  for `quantity` and `unit`.
- Combine totals across multiple recipes — return one entry per
  ingredient name from the input list.
- Return entries that use EXACTLY the input ingredient names (case
  preserved) so downstream code can match them.
- Output structured JSON only; no extra prose.
"""


class GroceryListAgent:
    """Deterministic grocery-list builder with optional LLM quantity layer."""

    def __init__(self, model: Optional[str] = None) -> None:
        self.name = "grocery_list_agent"
        self._model_name = model or settings.LLM_MODEL
        self._structured_llm = None  # lazy
        logger.info(f"Initialized {self.name} with model={self._model_name}")

    # ---- LLM client ----------------------------------------------------

    def _get_structured_llm(self):
        if self._structured_llm is not None:
            return self._structured_llm
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; GroceryListAgent cannot call the LLM."
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
        self._structured_llm = llm.with_structured_output(_LLMQuantities)
        return self._structured_llm

    # ---- Public entrypoint --------------------------------------------

    async def create_grocery_list(
        self, agent_input: GroceryListAgentInput
    ) -> GroceryListAgentOutput:
        if agent_input.menu_plan is None:
            logger.info("GroceryListAgent skipped: no menu_plan in input")
            return GroceryListAgentOutput(grocery_list=None)

        items, warnings = self._build_deterministic_items(agent_input)

        # If we have no items, skip the LLM entirely.
        if items:
            try:
                items, llm_warning = await self._fill_quantities(items, agent_input)
                if llm_warning:
                    warnings.append(llm_warning)
            except Exception as e:
                logger.warning(
                    f"GroceryListAgent quantity LLM failed ({e}); "
                    "returning list without quantities"
                )

        items.sort(key=lambda i: (i.already_available, i.name.lower()))

        to_buy = sum(1 for i in items if not i.already_available)
        on_hand = sum(1 for i in items if i.already_available)
        if not items:
            warnings.append("No ingredients found from the menu plan.")
            summary = "Empty grocery list."
        else:
            summary = (
                f"{len(items)} unique ingredient(s); "
                f"{to_buy} to buy, {on_hand} already on hand."
            )

        logger.info(
            "GroceryListAgent.create_grocery_list complete",
            extra={
                "items": len(items),
                "to_buy": to_buy,
                "already_available": on_hand,
                "warnings": len(warnings),
            },
        )
        return GroceryListAgentOutput(
            grocery_list=GroceryList(items=items, summary=summary, warnings=warnings)
        )

    # ---- Deterministic builder -----------------------------------------

    @staticmethod
    def _build_deterministic_items(
        agent_input: GroceryListAgentInput,
    ) -> tuple[list[GroceryItem], list[str]]:
        recipes_by_id = {str(r.id): r for r in agent_input.recipes}
        available_norm: set[str] = {
            _normalize_ingredient(a)
            for a in agent_input.available_ingredients
            if a and a.strip()
        }
        available_norm.discard("")

        aggregated: dict[str, dict] = {}
        warnings: list[str] = []
        unresolved_recipe_ids: set[str] = set()

        for day in agent_input.menu_plan.days:  # type: ignore[union-attr]
            for meal in day.meals:
                if not meal.recipe_id:
                    continue
                recipe = recipes_by_id.get(meal.recipe_id)
                if recipe is None:
                    unresolved_recipe_ids.add(meal.recipe_id)
                    continue
                for raw_name in recipe.ingredients:
                    name = (raw_name or "").strip()
                    if not name:
                        continue
                    key = name.lower()
                    entry = aggregated.setdefault(
                        key,
                        {
                            "name": name,
                            "recipes_used_in": [],
                            "seen_recipes": set(),
                        },
                    )
                    if meal.recipe_id not in entry["seen_recipes"]:
                        entry["seen_recipes"].add(meal.recipe_id)
                        entry["recipes_used_in"].append(meal.recipe_id)

        if unresolved_recipe_ids:
            warnings.append(
                "Some menu items reference recipes not in the retrieved set: "
                + ", ".join(sorted(unresolved_recipe_ids))
            )

        items: list[GroceryItem] = []
        for entry in aggregated.values():
            already = _matches_available(entry["name"], available_norm)
            items.append(
                GroceryItem(
                    name=entry["name"],
                    category=categorize_ingredient(entry["name"]),
                    quantity=None,
                    unit=None,
                    recipes_used_in=entry["recipes_used_in"],
                    already_available=already,
                    notes=[],
                )
            )
        return items, warnings

    # ---- LLM quantity layer --------------------------------------------

    async def _fill_quantities(
        self,
        items: list[GroceryItem],
        agent_input: GroceryListAgentInput,
    ) -> tuple[list[GroceryItem], Optional[str]]:
        """
        Ask the LLM for per-ingredient quantity estimates and stamp them onto
        the items in place. Returns (items, warning) where `warning` is the
        estimate disclaimer string when any quantity was set, else None.
        """
        structured_llm = self._get_structured_llm()
        prompt = self._build_prompt(items, agent_input)
        estimates: _LLMQuantities = await structured_llm.ainvoke(prompt)

        by_name = {item.name.strip().lower(): item for item in items}
        applied = 0
        for est in estimates.estimates:
            target = by_name.get(est.name.strip().lower())
            if target is None:
                continue
            if est.quantity is not None and est.quantity > 0:
                target.quantity = est.quantity
            if est.unit and est.unit in _ALLOWED_UNITS:
                target.unit = est.unit
            if target.quantity is not None or target.unit is not None:
                applied += 1

        warning = _ESTIMATE_WARNING if applied > 0 else None
        return items, warning

    @staticmethod
    def _build_prompt(
        items: list[GroceryItem], agent_input: GroceryListAgentInput
    ) -> str:
        # Provide minimal context the LLM needs to scale quantities.
        recipe_lines: list[str] = []
        for r in agent_input.recipes:
            recipe_lines.append(
                f"- id={r.id} | name={r.name} | "
                f"ingredients: {', '.join(r.ingredients) or '(unknown)'}"
            )
        recipes_block = "\n".join(recipe_lines) or "(none)"

        ingredient_lines = "\n".join(
            f"- {item.name} (used in recipe(s): {', '.join(item.recipes_used_in) or 'n/a'})"
            for item in items
        )

        days = agent_input.days if agent_input.days is not None else 1
        return (
            f"{_LLM_SYSTEM_PROMPT}\n"
            f"---\n"
            f"Servings per meal: {agent_input.servings}\n"
            f"Days in plan: {days}\n"
            f"Recipes referenced:\n{recipes_block}\n"
            f"Ingredients to estimate (one entry per name, exact spelling):\n"
            f"{ingredient_lines}\n"
            f"---\n"
            f"Return one `estimates` entry per ingredient above."
        )


# Category lookup table. Order matters:
#   - Compound keys (e.g. "black pepper", "soy sauce", "bay leaves") must sit
#     in their intended category *before* an ambiguous single-word key reaches
#     the same string. Concretely, "spices" is checked before "vegetables" so
#     that "black pepper" is classified as a spice; a recipe ingredient like
#     "bell pepper" still falls through to "vegetables".
#   - "pantry" sits after "vegetables" so that compound items like
#     "tomato sauce" prefer "vegetables" only when there's no clearer pantry
#     keyword; the dedicated "soy sauce" / "broth" keys still win.
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (
        "meat",
        (
            "chicken", "beef", "fish", "lamb", "pork", "turkey", "duck",
            "bacon", "ham", "sausage", "veal", "mutton", "salmon", "tuna",
            "shrimp", "meat",
        ),
    ),
    (
        "spices",
        (
            "black pepper", "bay leaves", "bay leaf", "salt", "cumin",
            "coriander", "paprika", "chili", "turmeric", "cinnamon",
            "ginger", "cardamom", "saffron", "oregano", "basil", "thyme",
            "rosemary", "clove", "nutmeg", "spice", "herb",
        ),
    ),
    (
        "vegetables",
        (
            "onion", "carrot", "celery", "tomato", "potato", "garlic",
            "pepper", "broccoli", "cucumber", "lettuce", "spinach",
            "mushroom", "zucchini", "eggplant", "cabbage", "leek", "kale",
            "vegetable",
        ),
    ),
    (
        "grains",
        (
            "rice", "noodles", "noodle", "pasta", "flour", "buckwheat",
            "oat", "barley", "couscous", "quinoa", "bread", "tortilla",
            "bun", "wheat",
        ),
    ),
    (
        "dairy",
        ("milk", "cheese", "yogurt", "butter", "cream", "dairy"),
    ),
    (
        "fruits",
        (
            "apple", "banana", "lemon", "lime", "orange", "berry",
            "strawberry", "raspberry", "blueberry", "grape", "pear",
            "peach", "mango", "pineapple", "fruit",
        ),
    ),
    (
        "pantry",
        (
            "soy sauce", "broth", "stock", "oil", "vinegar", "sauce",
            "soy", "sugar", "honey", "bean", "lentil", "chickpea",
        ),
    ),
]


def categorize_ingredient(name: str) -> str:
    """Return a grocery category for an ingredient name.

    Deterministic, case-insensitive keyword match against the table above.
    Returns ``"other"`` when no keyword matches.
    """
    needle = (name or "").strip().lower()
    if not needle:
        return "other"
    for category, keywords in _CATEGORY_KEYWORDS:
        for keyword in keywords:
            if keyword in needle:
                return category
    return "other"


# Descriptors stripped during normalization so "long-grain rice" → "rice",
# "fresh boneless chicken thighs" → "chicken thigh", etc.
_DESCRIPTORS: frozenset[str] = frozenset(
    {
        "fresh", "whole", "raw", "cooked", "uncooked", "ripe", "dried",
        "canned", "frozen", "organic", "extra", "virgin", "unsalted",
        "salted", "lean", "boneless", "skinless", "ground", "diced",
        "chopped", "sliced", "minced", "shredded", "grated", "crushed",
        "peeled", "long", "short", "grain", "low", "fat", "free",
    }
)


def _singularize(word: str) -> str:
    """Trim simple English plurals. Conservative — keeps short words intact."""
    if len(word) <= 3:
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if (
        word.endswith(("ses", "xes", "zes", "ches", "shes"))
        and not word.endswith("sses")
    ):
        return word[:-2]
    if word.endswith("oes") and len(word) >= 5:
        # tomatoes -> tomato, potatoes -> potato, heroes -> hero
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _normalize_ingredient(name: str) -> str:
    """
    Lowercase, strip punctuation, drop common descriptors, singularize each
    word. Returns a space-joined canonical form like 'chicken thigh' for
    'Fresh Boneless Chicken Thighs'.
    """
    s = (name or "").strip().lower()
    if not s:
        return ""
    # treat hyphens, slashes, and commas as word separators
    s = re.sub(r"[-/,]+", " ", s)
    tokens = [t for t in re.split(r"\s+", s) if t and t not in _DESCRIPTORS]
    tokens = [_singularize(t) for t in tokens]
    return " ".join(tokens).strip()


def _matches_available(name: str, available_normalized: set[str]) -> bool:
    """
    Match against pre-normalized user availability list. Both sides go
    through `_normalize_ingredient`, then we do bidirectional substring
    matching so "chicken" matches "chicken thigh" and vice versa.
    """
    needle = _normalize_ingredient(name)
    if not needle:
        return False
    for avail in available_normalized:
        if not avail:
            continue
        if avail in needle or needle in avail:
            return True
    return False