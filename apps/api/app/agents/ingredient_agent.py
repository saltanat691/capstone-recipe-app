"""
Ingredient Agent: convert a user request into structured planning JSON.

Merges explicit API-provided fields with information extracted from the user's
free-text message via an OpenAI chat model with structured output.
"""

from typing import Optional

from pydantic import BaseModel, Field

from app.core.config import settings
from app.observability import get_logger

logger = get_logger(__name__)


class IngredientAgentInput(BaseModel):
    """Fields supplied by the API caller. All optional except message."""

    message: str
    available_ingredients: Optional[list[str]] = None
    dietary_restrictions: Optional[list[str]] = None
    cuisine_preferences: Optional[list[str]] = None
    servings: Optional[int] = None
    days: Optional[int] = None


class IngredientAgentOutput(BaseModel):
    """Structured planning intake produced by the agent."""

    available_ingredients: list[str] = Field(default_factory=list)
    dietary_restrictions: list[str] = Field(default_factory=list)
    excluded_ingredients: list[str] = Field(default_factory=list)
    cuisine_preferences: list[str] = Field(default_factory=list)
    meal_type: Optional[str] = None
    requested_meal_types: list[str] = Field(default_factory=list)
    servings: int = 2
    days: Optional[int] = None
    max_cooking_time_minutes: Optional[int] = None
    user_intent: str = ""
    wants_grocery_list: bool = False


_SYSTEM_PROMPT = """You convert a user's free-text recipe request into a structured JSON intake.

Hard rules:
- Never invent allergies or dietary restrictions the user did not state.
- available_ingredients: only items the user says they have on hand.
- excluded_ingredients: items the user explicitly does not want.
- cuisine_preferences: only cuisines the user names (e.g. "italian", "central asian").
- meal_type: one of breakfast, lunch, dinner, snack, dessert — only if a single
  meal is clearly stated, else null. For multi-meal requests use
  requested_meal_types and leave meal_type null.
- requested_meal_types: a list of meal types the user is asking for when they
  want a plan or multi-meal output. Use only these tokens:
      "breakfast", "lunch", "dinner", "full_day"
  Examples:
    "3-day dinner menu"          -> ["dinner"]
    "weekly dinners"             -> ["dinner"]
    "menu for next week"         -> ["breakfast", "lunch", "dinner"]
    "full-day plan"              -> ["full_day"]
    "lunch and dinner for 5 days"-> ["lunch", "dinner"]
  If the user only asks for a single recipe (no plan, no menu), leave this
  list empty.
- days: integer if the user asks for a multi-day plan.
  Common phrasings to recognize:
    "3-day"           -> 3
    "for 5 days"      -> 5
    "next week" / "this week" / "weekly" / "weekly menu" -> 7
    "two weeks"       -> 14
  Else null.
- max_cooking_time_minutes: integer if the user gives a time limit; else null.
- servings: integer only if the user states it; otherwise omit (the system defaults to 2).
- user_intent: one short sentence summarizing what the user wants.
- wants_grocery_list: true if the user explicitly asks for a grocery list,
  shopping list, or what they should buy. Trigger phrases include:
    "grocery list", "shopping list", "what should I buy",
    "what do I need to buy", "buy list", "ingredients to buy".
  Otherwise false. Set independently of `days` — a user can ask for a
  grocery list without specifying days.

Normalize dietary_restrictions to lowercase snake_case:
  "no pork"      -> "no_pork"
  "halal"        -> "halal"
  "vegetarian"   -> "vegetarian"
  "gluten free"  -> "gluten_free"
  "gluten-free"  -> "gluten_free"
"""


class IngredientAgent:
    """
    LLM-backed agent that extracts a structured planning intake from a user
    message and merges it with explicit API fields.
    """

    def __init__(self, model: Optional[str] = None) -> None:
        self.name = "ingredient_agent"
        self._model_name = model or settings.LLM_MODEL
        self._structured_llm = None  # lazy: don't require key at import time
        logger.info(f"Initialized {self.name} with model={self._model_name}")

    def _get_structured_llm(self):
        if self._structured_llm is not None:
            return self._structured_llm

        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY is not set; IngredientAgent cannot call the LLM."
            )

        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise RuntimeError(
                "langchain-openai is not installed; run `pip install -r requirements.txt`."
            ) from e

        llm = ChatOpenAI(
            model=self._model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
        self._structured_llm = llm.with_structured_output(IngredientAgentOutput)
        return self._structured_llm

    async def run(self, agent_input: IngredientAgentInput) -> IngredientAgentOutput:
        """
        Extract structured intake from the user message and merge with
        explicit API fields. Explicit fields take precedence over extracted
        values for servings and days; lists are unioned and de-duplicated.
        """
        structured_llm = self._get_structured_llm()

        try:
            from langchain_core.prompts import ChatPromptTemplate

            prompt = ChatPromptTemplate.from_messages(
                [("system", _SYSTEM_PROMPT), ("human", "{message}")]
            )
            chain = prompt | structured_llm
            extracted: IngredientAgentOutput = await chain.ainvoke(
                {"message": agent_input.message}
            )
        except Exception as e:
            logger.error(
                "IngredientAgent LLM call failed",
                extra={"error": str(e), "model": self._model_name},
            )
            raise RuntimeError(f"IngredientAgent failed to extract intake: {e}") from e

        return self._merge(agent_input, extracted)

    @staticmethod
    def _merge(
        agent_input: IngredientAgentInput, extracted: IngredientAgentOutput
    ) -> IngredientAgentOutput:
        merged = IngredientAgentOutput(
            available_ingredients=_dedupe(
                (agent_input.available_ingredients or [])
                + extracted.available_ingredients
            ),
            dietary_restrictions=_dedupe(
                _normalize_restrictions(
                    (agent_input.dietary_restrictions or [])
                    + extracted.dietary_restrictions
                )
            ),
            excluded_ingredients=_dedupe(extracted.excluded_ingredients),
            cuisine_preferences=_dedupe(
                (agent_input.cuisine_preferences or []) + extracted.cuisine_preferences
            ),
            meal_type=extracted.meal_type,
            requested_meal_types=_dedupe_meal_types(extracted.requested_meal_types),
            servings=(
                agent_input.servings
                if agent_input.servings is not None
                else extracted.servings
            ),
            days=agent_input.days if agent_input.days is not None else extracted.days,
            max_cooking_time_minutes=extracted.max_cooking_time_minutes,
            user_intent=extracted.user_intent,
            wants_grocery_list=bool(extracted.wants_grocery_list),
        )

        # Defensive default: servings must be a positive int.
        if not merged.servings or merged.servings <= 0:
            merged.servings = 2

        return merged


_ALLOWED_MEAL_TYPES = {"breakfast", "lunch", "dinner", "full_day"}


def _dedupe_meal_types(items: list[str]) -> list[str]:
    """Normalize to the allowed set, preserve order, drop unknowns."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in items or []:
        key = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not key or key in seen:
            continue
        if key not in _ALLOWED_MEAL_TYPES:
            continue
        seen.add(key)
        out.append(key)
    return out


def _normalize_restrictions(items: list[str]) -> list[str]:
    return [_normalize_one(i) for i in items if i and i.strip()]


def _normalize_one(s: str) -> str:
    return s.strip().lower().replace("-", "_").replace(" ", "_")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if not item:
            continue
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item.strip())
    return out