"""
LangGraph workflow.

Linear pipeline:
    START -> ingredient_agent_node -> recipe_retrieval_node
          -> nutrition_agent_node -> menu_planner_agent_node
          -> grocery_list_agent_node -> final_response_node -> END
"""

import uuid
from typing import Any, Optional

from app.agents.grocery_list_agent import (
    GroceryListAgent,
    GroceryListAgentInput,
)
from app.agents.ingredient_agent import IngredientAgent, IngredientAgentInput
from app.agents.menu_planner_agent import (
    MenuPlannerAgent,
    MenuPlannerAgentInput,
)
from app.agents.nutrition_agent import NutritionAgent, NutritionAgentInput
from app.agents.state import State
from app.observability import get_logger
from app.schemas.grocery_list import GroceryList as AgentGroceryList
from app.schemas.menu_plan import MenuPlan as AgentMenuPlan
from app.schemas.nutrition import NutritionNote
from app.schemas.recommendation import (
    GroceryItem as ResponseGroceryItem,
    GroceryList as ResponseGroceryList,
    MenuDay as ResponseMenuDay,
    MenuPlan as ResponseMenuPlan,
    RecipeRecommendation,
    RecommendationResponse,
)
from app.services.rag_recipe_service import (
    RecipeSearchFilters,
    RetrievedRecipe,
    retrieve_recipes,
)

logger = get_logger(__name__)


class RecipeAgentGraph:
    """
    LangGraph workflow that turns a free-text user message into a
    RecommendationResponse via a linear chain of nodes.
    """

    def __init__(self) -> None:
        logger.info("Initializing RecipeAgentGraph (linear)")
        self.ingredient_agent = IngredientAgent()
        self.nutrition_agent = NutritionAgent()
        self.menu_planner_agent = MenuPlannerAgent()
        self.grocery_list_agent = GroceryListAgent()
        self.graph = None

    # ---- Nodes ---------------------------------------------------------

    async def _ingredient_agent_node(self, state: State) -> dict[str, Any]:
        """Run the ingredient agent over the raw message + explicit inputs."""
        explicit = state.get("explicit_inputs") or {}
        agent_input = IngredientAgentInput(
            message=state.get("raw_user_input", "") or "",
            available_ingredients=explicit.get("available_ingredients"),
            dietary_restrictions=explicit.get("dietary_restrictions"),
            cuisine_preferences=explicit.get("cuisine_preferences"),
            servings=explicit.get("servings"),
            days=explicit.get("days"),
        )
        output = await self.ingredient_agent.run(agent_input)
        logger.info(
            "ingredient_agent_node complete",
            extra={
                "request_id": state.get("request_id"),
                "intent": output.user_intent,
                "ingredients": len(output.available_ingredients),
                "restrictions": len(output.dietary_restrictions),
            },
        )
        return {"ingredient_agent_output": output}

    async def _recipe_retrieval_node(self, state: State) -> dict[str, Any]:
        """Build a retrieval query from the intake and call the RAG service."""
        intake = state.get("ingredient_agent_output")
        warnings = list(state.get("warnings") or [])

        if intake is None:
            warnings.append("recipe_retrieval skipped: no ingredient agent output")
            return {"retrieved_recipes": [], "warnings": warnings}

        query = _build_query(state.get("raw_user_input", "") or "", intake)
        filters = RecipeSearchFilters(
            dietary_restrictions=intake.dietary_restrictions,
            excluded_ingredients=intake.excluded_ingredients,
            cuisine_preferences=intake.cuisine_preferences,
            available_ingredients=intake.available_ingredients,
            max_cooking_time_minutes=intake.max_cooking_time_minutes,
            meal_type=intake.meal_type,
        )

        recipes: list[RetrievedRecipe] = await retrieve_recipes(query, filters, limit=5)
        if not recipes:
            warnings.append("No recipes matched the request")

        logger.info(
            "recipe_retrieval_node complete",
            extra={
                "request_id": state.get("request_id"),
                "query_len": len(query),
                "results": len(recipes),
            },
        )
        return {"retrieved_recipes": recipes, "warnings": warnings}

    async def _nutrition_agent_node(self, state: State) -> dict[str, Any]:
        """Enrich the retrieved recipes with nutrition notes."""
        retrieved: list[RetrievedRecipe] = state.get("retrieved_recipes") or []
        if not retrieved:
            return {"nutrition_notes": []}

        intake = state.get("ingredient_agent_output")
        agent_input = NutritionAgentInput(
            recipes=retrieved,
            dietary_restrictions=list(getattr(intake, "dietary_restrictions", []) or []),
            excluded_ingredients=list(getattr(intake, "excluded_ingredients", []) or []),
            servings=int(getattr(intake, "servings", 2) or 2),
            user_preferences=getattr(intake, "user_intent", None),
        )
        output = await self.nutrition_agent.enrich_recipes(agent_input)
        logger.info(
            "nutrition_agent_node complete",
            extra={
                "request_id": state.get("request_id"),
                "notes": len(output.notes),
            },
        )
        return {"nutrition_notes": output.notes}

    async def _menu_planner_agent_node(self, state: State) -> dict[str, Any]:
        """Build an n-day menu plan from the retrieved recipes."""
        retrieved: list[RetrievedRecipe] = state.get("retrieved_recipes") or []
        intake = state.get("ingredient_agent_output")
        notes: list[NutritionNote] = state.get("nutrition_notes") or []

        agent_input = MenuPlannerAgentInput(
            recipes=retrieved,
            nutrition_notes=notes,
            available_ingredients=list(getattr(intake, "available_ingredients", []) or []),
            dietary_restrictions=list(getattr(intake, "dietary_restrictions", []) or []),
            excluded_ingredients=list(getattr(intake, "excluded_ingredients", []) or []),
            cuisine_preferences=list(getattr(intake, "cuisine_preferences", []) or []),
            requested_meal_types=list(getattr(intake, "requested_meal_types", []) or []),
            servings=int(getattr(intake, "servings", 2) or 2),
            days=getattr(intake, "days", None),
            user_intent=getattr(intake, "user_intent", None),
        )
        output = await self.menu_planner_agent.create_menu_plan(agent_input)
        logger.info(
            "menu_planner_agent_node complete",
            extra={
                "request_id": state.get("request_id"),
                "days": getattr(output.menu_plan, "days", None)
                and len(output.menu_plan.days),
            },
        )
        return {"menu_plan": output.menu_plan}

    async def _grocery_list_agent_node(self, state: State) -> dict[str, Any]:
        """Generate a grocery list from the menu plan and retrieved recipes."""
        agent_menu_plan: Optional[AgentMenuPlan] = state.get("menu_plan")
        retrieved: list[RetrievedRecipe] = state.get("retrieved_recipes") or []
        intake = state.get("ingredient_agent_output")
        warnings = list(state.get("warnings") or [])

        wants_grocery = bool(getattr(intake, "wants_grocery_list", False))

        # The rule: grocery_list is generated only when menu_plan exists.
        # If the user explicitly asked for a grocery list but no menu_plan
        # was produced (no `days` provided or inferred), surface a clear
        # warning so the caller knows why grocery_list is null.
        if agent_menu_plan is None:
            if wants_grocery:
                warnings.append(
                    "Grocery list requested but no menu plan was produced. "
                    "Provide `days` or describe a multi-day plan to receive "
                    "a grocery list."
                )
            logger.info(
                "grocery_list_agent_node skipped: no menu_plan",
                extra={
                    "request_id": state.get("request_id"),
                    "wants_grocery_list": wants_grocery,
                },
            )
            return {"grocery_list": None, "warnings": warnings}

        agent_input = GroceryListAgentInput(
            menu_plan=agent_menu_plan,
            recipes=retrieved,
            available_ingredients=list(
                getattr(intake, "available_ingredients", []) or []
            ),
            servings=int(getattr(intake, "servings", 2) or 2),
            days=getattr(intake, "days", None),
        )
        output = await self.grocery_list_agent.create_grocery_list(agent_input)
        logger.info(
            "grocery_list_agent_node complete",
            extra={
                "request_id": state.get("request_id"),
                "items": (
                    len(output.grocery_list.items) if output.grocery_list else 0
                ),
                "wants_grocery_list": wants_grocery,
            },
        )
        return {"grocery_list": output.grocery_list, "warnings": warnings}

    async def _final_response_node(self, state: State) -> dict[str, Any]:
        """Format retrieved recipes, nutrition, menu plan, and grocery list."""
        retrieved: list[RetrievedRecipe] = state.get("retrieved_recipes") or []
        intake = state.get("ingredient_agent_output")
        notes: list[NutritionNote] = state.get("nutrition_notes") or []
        agent_menu_plan: Optional[AgentMenuPlan] = state.get("menu_plan")
        agent_grocery_list: Optional[AgentGroceryList] = state.get("grocery_list")

        recommendations = [
            RecipeRecommendation(
                id=r.id,
                name=r.name,
                cuisine=r.cuisine,
                ingredients=r.ingredients,
                instructions=r.instructions,
            )
            for r in retrieved
        ]

        warnings = list(state.get("warnings") or [])
        for note in notes:
            warnings.extend(note.warnings)
        servings = int(getattr(intake, "servings", 2) or 2)
        response_menu_plan: Optional[ResponseMenuPlan] = None
        menu_metadata: Optional[dict[str, Any]] = None
        if agent_menu_plan is not None:
            response_menu_plan = _to_response_menu_plan(
                agent_menu_plan, retrieved, servings
            )
            warnings.extend(agent_menu_plan.warnings)
            menu_metadata = agent_menu_plan.model_dump()

        response_grocery_list: Optional[ResponseGroceryList] = None
        grocery_metadata: Optional[dict[str, Any]] = None
        if agent_grocery_list is not None:
            response_grocery_list = _to_response_grocery_list(agent_grocery_list)
            warnings.extend(agent_grocery_list.warnings)
            grocery_metadata = agent_grocery_list.model_dump()

        warnings = _dedupe_strs(warnings)

        response = RecommendationResponse(
            recommendations=recommendations,
            warnings=warnings,
            trace_id=state.get("trace_id"),
            nutrition_notes=_summarize_health_notes(notes),
            menu_plan=response_menu_plan,
            grocery_list=response_grocery_list,
            metadata={
                "request_id": state.get("request_id"),
                "user_intent": intake.user_intent if intake else None,
                "scores": [r.score for r in retrieved],
                "match_reasons": [r.match_reason for r in retrieved],
                "nutrition": [n.model_dump() for n in notes],
                "menu_plan": menu_metadata,
                "grocery_list": grocery_metadata,
            },
        )

        logger.info(
            "final_response_node complete",
            extra={
                "request_id": state.get("request_id"),
                "recommendations": len(recommendations),
                "nutrition_notes": len(notes),
                "menu_days": len(response_menu_plan.days)
                if response_menu_plan
                else 0,
                "grocery_items": len(response_grocery_list.items)
                if response_grocery_list
                else 0,
            },
        )
        return {"final_response": response}

    # ---- Graph wiring --------------------------------------------------

    def build_graph(self) -> None:
        """Compile the linear LangGraph workflow."""
        from langgraph.graph import END, START, StateGraph

        builder = StateGraph(State)
        builder.add_node("ingredient_agent_node", self._ingredient_agent_node)
        builder.add_node("recipe_retrieval_node", self._recipe_retrieval_node)
        builder.add_node("nutrition_agent_node", self._nutrition_agent_node)
        builder.add_node("menu_planner_agent_node", self._menu_planner_agent_node)
        builder.add_node("grocery_list_agent_node", self._grocery_list_agent_node)
        builder.add_node("final_response_node", self._final_response_node)

        builder.add_edge(START, "ingredient_agent_node")
        builder.add_edge("ingredient_agent_node", "recipe_retrieval_node")
        builder.add_edge("recipe_retrieval_node", "nutrition_agent_node")
        builder.add_edge("nutrition_agent_node", "menu_planner_agent_node")
        builder.add_edge("menu_planner_agent_node", "grocery_list_agent_node")
        builder.add_edge("grocery_list_agent_node", "final_response_node")
        builder.add_edge("final_response_node", END)

        self.graph = builder.compile()
        logger.info("RecipeAgentGraph compiled")

    async def invoke(
        self,
        *,
        raw_user_input: str,
        explicit_inputs: Optional[dict[str, Any]] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> State:
        """
        Run the workflow end-to-end. Returns the final State; the
        RecommendationResponse is at state["final_response"].
        """
        if self.graph is None:
            self.build_graph()

        initial: State = {
            "request_id": request_id or str(uuid.uuid4()),
            "raw_user_input": raw_user_input,
            "explicit_inputs": explicit_inputs or {},
            "warnings": [],
            "trace_id": trace_id or "",
        }
        return await self.graph.ainvoke(initial)


# ---- Module-level helpers ---------------------------------------------


def _summarize_health_notes(notes: list[NutritionNote]) -> str:
    """Collapse per-recipe health notes into a single deduped string."""
    if not notes:
        return ""
    seen: set[str] = set()
    ordered: list[str] = []
    for note in notes:
        for line in note.health_notes:
            text = line.strip()
            if text and text not in seen:
                seen.add(text)
                ordered.append(text)
    return " ".join(ordered)


def _to_response_menu_plan(
    agent_menu_plan: AgentMenuPlan,
    retrieved: list[RetrievedRecipe],
    servings: int,
) -> ResponseMenuPlan:
    """
    Convert the Menu Planner Agent's MenuPlan into the public API response
    shape, looking up retrieved-recipe details by id.
    """
    by_id = {str(r.id): r for r in retrieved}
    response_days: list[ResponseMenuDay] = []
    for agent_day in agent_menu_plan.days:
        meals: dict[str, RecipeRecommendation] = {}
        for meal in agent_day.meals:
            retrieved_recipe = by_id.get(meal.recipe_id) if meal.recipe_id else None
            recipe_id = (
                int(meal.recipe_id)
                if meal.recipe_id and meal.recipe_id.isdigit()
                else None
            )
            meals[meal.meal_type] = RecipeRecommendation(
                id=recipe_id,
                name=meal.recipe_name,
                cuisine=retrieved_recipe.cuisine if retrieved_recipe else None,
                ingredients=retrieved_recipe.ingredients
                if retrieved_recipe
                else None,
                instructions=retrieved_recipe.instructions
                if retrieved_recipe
                else None,
            )
        response_days.append(
            ResponseMenuDay(
                day=agent_day.day,
                date=None,
                meals=meals,
                notes=None,
            )
        )

    return ResponseMenuPlan(
        days=response_days,
        total_days=len(response_days),
        servings=servings,
    )


def _to_response_grocery_list(
    agent_grocery_list: AgentGroceryList,
) -> ResponseGroceryList:
    """
    Convert the Grocery List Agent's GroceryList into the public API response
    shape. The richer fields (recipes_used_in, already_available, notes) are
    preserved server-side via `metadata["grocery_list"]`.
    """
    items: list[ResponseGroceryItem] = []
    categories: dict[str, list[ResponseGroceryItem]] = {}
    for item in agent_grocery_list.items:
        category = item.category or "other"
        response_item = ResponseGroceryItem(
            ingredient=item.name,
            quantity=item.quantity,
            unit=item.unit,
            category=category,
            estimated_cost=None,
            already_available=item.already_available,
        )
        items.append(response_item)
        categories.setdefault(category, []).append(response_item)

    return ResponseGroceryList(
        items=items,
        categories=categories,
        total_items=len(items),
        estimated_total_cost=None,
    )


def _dedupe_strs(items: list[str]) -> list[str]:
    """Preserve order, drop empty + duplicate (case-insensitive) entries."""
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        text = (raw or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out


def _build_query(raw_user_input: str, intake: Any) -> str:
    """Compose a natural-language retrieval query from the intake."""
    parts: list[str] = []
    intent = getattr(intake, "user_intent", "") or ""
    if intent:
        parts.append(intent)
    elif raw_user_input:
        parts.append(raw_user_input)

    if getattr(intake, "available_ingredients", None):
        parts.append(f"with {', '.join(intake.available_ingredients)}")
    if getattr(intake, "cuisine_preferences", None):
        parts.append(f"cuisine: {', '.join(intake.cuisine_preferences)}")
    if getattr(intake, "meal_type", None):
        parts.append(f"meal: {intake.meal_type}")

    return ". ".join(parts) if parts else raw_user_input


# ---- Singleton accessor -----------------------------------------------

_graph_instance: Optional[RecipeAgentGraph] = None


def get_agent_graph() -> RecipeAgentGraph:
    """Return the process-wide RecipeAgentGraph, building it on first use."""
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = RecipeAgentGraph()
        _graph_instance.build_graph()
        logger.info("Created global RecipeAgentGraph instance")
    return _graph_instance