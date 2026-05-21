"""
Pydantic schemas for recipe recommendation requests and responses.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class RecommendationRequest(BaseModel):
    """
    Request schema for recipe recommendations.

    Users can provide a natural language message and/or structured preferences.
    """

    message: str = Field(
        ...,
        description="Natural language request describing what the user wants",
        min_length=1,
        max_length=1000,
        examples=["I have chicken and rice, what can I make for dinner?"],
    )

    available_ingredients: Optional[list[str]] = Field(
        default=None,
        description="List of ingredients the user has available",
        examples=[["chicken breast", "rice", "broccoli", "garlic"]],
    )

    dietary_restrictions: Optional[list[str]] = Field(
        default=None,
        description="List of dietary restrictions (vegetarian, vegan, gluten-free, etc.)",
        examples=[["vegetarian", "gluten-free"]],
    )

    cuisine_preferences: Optional[list[str]] = Field(
        default=None,
        description="List of preferred cuisines (Italian, Mexican, Asian, etc.)",
        examples=[["italian", "mediterranean"]],
    )

    servings: Optional[int] = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of servings needed",
        examples=[4],
    )

    days: Optional[int] = Field(
        default=None,
        ge=1,
        le=30,
        description=(
            "Number of days to plan meals for. Omit to skip menu planning; "
            "the Menu Planner Agent will set menu_plan to null."
        ),
        examples=[7],
    )

    @field_validator("available_ingredients", "dietary_restrictions", "cuisine_preferences")
    @classmethod
    def validate_list_items(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate list items are not empty strings."""
        if v is not None:
            # Filter out empty strings and strip whitespace
            cleaned = [item.strip() for item in v if item and item.strip()]
            return cleaned if cleaned else None
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "I want to make healthy meals for the week",
                    "available_ingredients": ["chicken", "rice", "broccoli", "tomatoes"],
                    "dietary_restrictions": ["gluten-free"],
                    "cuisine_preferences": ["asian", "mediterranean"],
                    "servings": 4,
                    "days": 7,
                }
            ]
        }
    }


class RecipeRecommendation(BaseModel):
    """Individual recipe recommendation."""

    id: Optional[int] = Field(None, description="Recipe ID from database")
    name: str = Field(..., description="Recipe name")
    description: Optional[str] = Field(None, description="Recipe description")
    cuisine: Optional[str] = Field(None, description="Cuisine type")
    prep_time: Optional[int] = Field(None, description="Preparation time in minutes")
    cook_time: Optional[int] = Field(None, description="Cooking time in minutes")
    total_time: Optional[int] = Field(None, description="Total time in minutes")
    servings: Optional[int] = Field(None, description="Number of servings")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    ingredients: Optional[list[str]] = Field(None, description="List of ingredients")
    instructions: Optional[list[str]] = Field(None, description="Cooking instructions")
    nutrition: Optional[dict[str, Any]] = Field(None, description="Nutritional information")
    tags: Optional[list[str]] = Field(None, description="Recipe tags")


class MenuDay(BaseModel):
    """Single day in a menu plan."""

    day: int = Field(..., description="Day number (1-based)")
    date: Optional[str] = Field(None, description="Date in ISO format")
    meals: dict[str, RecipeRecommendation] = Field(
        ...,
        description="Meals for this day (breakfast, lunch, dinner, snack)",
    )
    notes: Optional[str] = Field(None, description="Notes for this day")


class MenuPlan(BaseModel):
    """Complete menu plan."""

    days: list[MenuDay] = Field(..., description="List of days in the menu plan")
    total_days: int = Field(..., description="Total number of days")
    servings: int = Field(..., description="Servings per meal")


class GroceryItem(BaseModel):
    """Individual grocery item."""

    ingredient: str = Field(..., description="Ingredient name")
    quantity: Optional[float] = Field(None, description="Quantity needed")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    category: Optional[str] = Field(None, description="Store category")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost in dollars")
    already_available: bool = Field(
        False,
        description="True if the user already has this ingredient on hand.",
    )


class GroceryList(BaseModel):
    """Shopping list organized by category."""

    items: list[GroceryItem] = Field(..., description="List of grocery items")
    categories: dict[str, list[GroceryItem]] = Field(
        ...,
        description="Items organized by category",
    )
    total_items: int = Field(..., description="Total number of items")
    estimated_total_cost: Optional[float] = Field(
        None,
        description="Total estimated cost in dollars",
    )


class RecommendationResponse(BaseModel):
    """
    Response schema for recipe recommendations.

    Contains complete recommendations including recipes, menu plan, shopping list,
    and nutritional information.
    """

    recommendations: list[RecipeRecommendation] = Field(
        ...,
        description="List of recommended recipes",
    )

    menu_plan: Optional[MenuPlan] = Field(
        None,
        description="Complete menu plan organized by days",
    )

    grocery_list: Optional[GroceryList] = Field(
        None,
        description="Shopping list with categorized items",
    )

    nutrition_notes: Optional[str] = Field(
        None,
        description="Nutritional analysis and recommendations",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="Safety warnings or validation issues",
    )

    trace_id: Optional[str] = Field(
        None,
        description="Trace ID for observability and debugging",
    )

    # Internal-only: populated by the graph for logging, tracing, and
    # debugging (request_id, similarity scores, match reasons, structured
    # nutrition / menu_plan diagnostics). `exclude=True` keeps the attribute
    # accessible in Python but drops it from API serialization.
    metadata: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Internal diagnostics; not serialized in API responses.",
        exclude=True,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "recommendations": [
                        {
                            "name": "Chicken Stir Fry",
                            "description": "Quick and healthy chicken stir fry with vegetables",
                            "cuisine": "Asian",
                            "prep_time": 15,
                            "cook_time": 15,
                            "total_time": 30,
                            "servings": 4,
                            "difficulty": "easy",
                        }
                    ],
                    "menu_plan": {
                        "days": [],
                        "total_days": 7,
                        "servings": 4,
                    },
                    "grocery_list": {
                        "items": [],
                        "categories": {},
                        "total_items": 0,
                    },
                    "nutrition_notes": "Balanced meals with adequate protein and vegetables",
                    "warnings": [],
                    "trace_id": "abc123",
                }
            ]
        }
    }