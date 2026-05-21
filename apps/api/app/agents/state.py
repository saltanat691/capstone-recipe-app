"""
Shared state for the recipe AI agent workflow.

Passed between nodes in the LangGraph workflow. All fields are optional
(`total=False`) so nodes can write only what they produce and LangGraph
merges partial updates into the running state.
"""

from typing import Any

from typing_extensions import TypedDict


class RecipeAgentState(TypedDict, total=False):
    """
    Workflow state. Field types kept loose (Any) to avoid import coupling
    between this module and the agents/services that produce the values.

    Core fields:
        request_id: Stable per-request identifier (string UUID).
        raw_user_input: The user's free-text message.
        explicit_inputs: Optional dict of API-supplied structured fields
            (available_ingredients, dietary_restrictions, cuisine_preferences,
            servings, days).
        ingredient_agent_output: IngredientAgentOutput from the ingredient
            agent node.
        retrieved_recipes: list[RetrievedRecipe] from the RAG retrieval node.
        nutrition_notes: list[NutritionNote] from the Nutrition Agent.
        menu_plan: MenuPlan | None from the Menu Planner Agent.
        grocery_list: GroceryList | None from the Grocery List Agent.
        final_response: RecommendationResponse produced by the final node.
        warnings: Accumulated non-fatal warnings.
        trace_id: External trace identifier for observability.

    Legacy fields (kept for compatibility with the placeholder agents that
    are not wired into the current graph; safe to remove once those agents
    are reimplemented):
        available_ingredients, dietary_restrictions, cuisine_preferences,
        servings, days, candidate_recipes, selected_recipes,
        validation_warnings, metadata.
    """

    # Core workflow fields
    request_id: str
    raw_user_input: str
    explicit_inputs: dict[str, Any]
    ingredient_agent_output: Any  # IngredientAgentOutput
    retrieved_recipes: list[Any]  # list[RetrievedRecipe]
    nutrition_notes: list[Any]  # list[NutritionNote] from NutritionAgent
    menu_plan: Any  # app.schemas.menu_plan.MenuPlan | None from MenuPlannerAgent
    grocery_list: Any  # app.schemas.grocery_list.GroceryList | None
    final_response: Any  # RecommendationResponse
    warnings: list[str]
    trace_id: str

    # Legacy fields (still referenced by stub agents elsewhere)
    available_ingredients: list[str]
    dietary_restrictions: list[str]
    cuisine_preferences: list[str]
    servings: int
    days: int
    candidate_recipes: list[dict[str, Any]]
    selected_recipes: list[dict[str, Any]]
    validation_warnings: list[str]
    metadata: dict[str, Any]


State = RecipeAgentState