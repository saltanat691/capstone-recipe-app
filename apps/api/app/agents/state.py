"""
Shared state model for the recipe AI agent workflow.

This module defines the state that is passed between agents in the LangGraph workflow.
Each agent reads from and writes to this shared state.
"""

from typing import Any, Optional

from typing_extensions import TypedDict


class RecipeAgentState(TypedDict, total=False):
    """
    Shared state for the recipe AI agent workflow.

    This state is passed between all agents in the LangGraph workflow.
    Agents can read from any field and write to relevant fields.

    Attributes:
        raw_user_input: Original user input with all requirements
        available_ingredients: List of ingredients the user has available
        dietary_restrictions: List of dietary restrictions (vegetarian, vegan, etc.)
        cuisine_preferences: List of preferred cuisines (Italian, Mexican, etc.)
        servings: Number of servings needed
        days: Number of days to plan meals for
        candidate_recipes: List of potential recipes found by recipe agent
        selected_recipes: Final list of recipes selected for the menu
        nutrition_notes: Nutritional analysis and recommendations
        menu_plan: Complete menu plan with recipes organized by day
        grocery_list: Shopping list with ingredients and quantities
        validation_warnings: Safety warnings or validation issues
        metadata: Additional metadata (agent run ID, timestamps, etc.)
    """

    # User input fields
    raw_user_input: str
    available_ingredients: list[str]
    dietary_restrictions: list[str]
    cuisine_preferences: list[str]
    servings: int
    days: int

    # Agent processing fields
    candidate_recipes: list[dict[str, Any]]
    selected_recipes: list[dict[str, Any]]
    nutrition_notes: str
    menu_plan: dict[str, Any]
    grocery_list: dict[str, Any]
    validation_warnings: list[str]

    # Metadata
    metadata: dict[str, Any]


# Type alias for convenience
State = RecipeAgentState