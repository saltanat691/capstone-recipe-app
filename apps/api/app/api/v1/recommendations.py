"""
Recipe recommendation API endpoints.

This module provides endpoints for generating recipe recommendations,
meal plans, and shopping lists using AI agents.
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.recipe import Recipe
from app.observability import get_logger
from app.observability.tracing import get_current_trace_id
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RecipeRecommendation,
    MenuPlan,
    MenuDay,
    GroceryList,
    GroceryItem,
)
from app.services.recipe_search_service import search_recipes

logger = get_logger(__name__)

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Generate recipe recommendations",
    description="Generate personalized recipe recommendations, meal plans, and shopping lists based on available ingredients and preferences",
)
async def create_recommendations(
    request_data: RecommendationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """
    Generate recipe recommendations using database search.

    This endpoint will:
    1. Search for recipes matching available ingredients
    2. Filter by dietary restrictions
    3. Prefer cuisine preferences
    4. Create a simple menu plan
    5. Generate a basic shopping list

    Args:
        request_data: User request with ingredients and preferences
        request: FastAPI request object for metadata
        db: Database session

    Returns:
        Complete recommendations with menu plan and shopping list

    Raises:
        HTTPException: If request processing fails
    """
    logger.info(
        "Received recommendation request",
        extra={
            "message_length": len(request_data.message),
            "ingredients": len(request_data.available_ingredients or []),
            "restrictions": len(request_data.dietary_restrictions or []),
            "days": request_data.days,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

    try:
        # Get trace ID for observability
        trace_id = get_current_trace_id()

        # Search recipes using the search service
        scored_recipes = await search_recipes(
            db_session=db,
            available_ingredients=request_data.available_ingredients,
            dietary_restrictions=request_data.dietary_restrictions,
            cuisine_preferences=request_data.cuisine_preferences,
            limit=15,  # Get more recipes for variety
        )

        # Check if we found any recipes
        if not scored_recipes:
            logger.warning("No recipes found matching criteria")
            return RecommendationResponse(
                recommendations=[],
                menu_plan=None,
                grocery_list=None,
                nutrition_notes="No recipes found matching your criteria. Try adjusting your preferences or dietary restrictions.",
                warnings=["No recipes found matching your criteria"],
                trace_id=trace_id,
                metadata={"total_recipes_in_db": 0},
            )

        # Convert recipes to schema format
        recommendations = [
            _convert_recipe_to_recommendation(recipe, score)
            for recipe, score in scored_recipes
        ]

        # Generate menu plan
        menu_plan = _generate_menu_plan(
            recommendations, request_data.days or 7, request_data.servings or 4
        )

        # Generate grocery list
        grocery_list = _generate_grocery_list(
            recommendations[: request_data.days or 7]  # Use top N recipes for N days
        )

        # Generate nutrition notes
        nutrition_notes = _generate_nutrition_notes(recommendations, request_data.days or 7)

        # Generate warnings
        warnings = []
        if len(scored_recipes) < 5:
            warnings.append(
                f"Limited recipe selection found ({len(scored_recipes)} recipes). "
                "Consider expanding your ingredient list or adjusting restrictions."
            )

        logger.info(
            "Generated recommendations",
            extra={
                "recipe_count": len(recommendations),
                "days": request_data.days,
                "warnings": len(warnings),
                "trace_id": trace_id,
                "top_score": scored_recipes[0][1] if scored_recipes else 0,
            },
        )

        return RecommendationResponse(
            recommendations=recommendations,
            menu_plan=menu_plan,
            grocery_list=grocery_list,
            nutrition_notes=nutrition_notes,
            warnings=warnings,
            trace_id=trace_id,
            metadata={
                "total_recipes_searched": len(scored_recipes),
                "search_method": "basic_scoring",
                "top_score": scored_recipes[0][1] if scored_recipes else 0,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to generate recommendations",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate recommendations. Please try again.",
        ) from e


def _convert_recipe_to_recommendation(recipe: Recipe, score: float) -> RecipeRecommendation:
    """
    Convert a Recipe model to a RecipeRecommendation schema.

    Args:
        recipe: Recipe model from database
        score: Search score for this recipe

    Returns:
        RecipeRecommendation schema
    """
    # Format ingredients as strings
    ingredient_strings = []
    for ingredient in recipe.ingredients:
        # Get the quantity and unit from the association table
        # This requires accessing the relationship data
        ingredient_strings.append(ingredient.name)

    # Format instructions
    instructions = []
    if recipe.instructions and isinstance(recipe.instructions, list):
        instructions = recipe.instructions
    elif recipe.instructions and isinstance(recipe.instructions, dict):
        # Handle if stored as dict
        instructions = recipe.instructions.get("steps", [])

    # Extract tags from dietary_tags
    tags = []
    if recipe.dietary_tags:
        tags = recipe.dietary_tags if isinstance(recipe.dietary_tags, list) else []

    return RecipeRecommendation(
        id=recipe.id,
        name=recipe.name,
        description=recipe.description,
        cuisine=recipe.cuisine,
        prep_time=recipe.prep_time,
        cook_time=recipe.cook_time,
        total_time=recipe.total_time,
        servings=recipe.servings,
        difficulty=recipe.difficulty,
        ingredients=ingredient_strings,
        instructions=instructions,
        nutrition=recipe.nutrition,
        tags=tags,
    )


def _generate_menu_plan(
    recommendations: list[RecipeRecommendation], days: int, servings: int
) -> MenuPlan:
    """
    Generate a simple menu plan from recommendations.

    Args:
        recommendations: List of recipe recommendations
        days: Number of days to plan
        servings: Servings per meal

    Returns:
        MenuPlan with daily meals
    """
    if not recommendations:
        return MenuPlan(days=[], total_days=days, servings=servings)

    menu_days = []
    start_date = datetime.now().date()

    # Simple rotation through recommendations
    for day_num in range(1, days + 1):
        # Rotate through recipes
        lunch_idx = (day_num - 1) % len(recommendations)
        dinner_idx = (day_num + len(recommendations) // 2 - 1) % len(recommendations)

        # Ensure different recipes for lunch and dinner
        if lunch_idx == dinner_idx and len(recommendations) > 1:
            dinner_idx = (dinner_idx + 1) % len(recommendations)

        day_date = start_date + timedelta(days=day_num - 1)

        menu_days.append(
            MenuDay(
                day=day_num,
                date=day_date.isoformat(),
                meals={
                    "lunch": recommendations[lunch_idx],
                    "dinner": recommendations[dinner_idx],
                },
                notes=f"Day {day_num}",
            )
        )

    return MenuPlan(days=menu_days, total_days=days, servings=servings)


def _generate_grocery_list(recommendations: list[RecipeRecommendation]) -> GroceryList:
    """
    Generate a simple grocery list from recommendations.

    Args:
        recommendations: List of recipe recommendations

    Returns:
        GroceryList with items organized by category
    """
    if not recommendations:
        return GroceryList(items=[], categories={}, total_items=0, estimated_total_cost=0.0)

    # Collect all unique ingredients
    ingredient_set = set()
    for recipe in recommendations:
        if recipe.ingredients:
            for ingredient in recipe.ingredients:
                ingredient_set.add(ingredient.lower().strip())

    # Create grocery items (simple version without quantities)
    grocery_items = []
    for ingredient_name in sorted(ingredient_set):
        # Simple category assignment based on keywords
        category = _categorize_ingredient(ingredient_name)

        grocery_items.append(
            GroceryItem(
                ingredient=ingredient_name.title(),
                quantity=None,  # Quantity aggregation would be more complex
                unit=None,
                category=category,
                estimated_cost=None,
            )
        )

    # Organize by category
    categories: dict[str, list[GroceryItem]] = {}
    for item in grocery_items:
        category = item.category or "Other"
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    return GroceryList(
        items=grocery_items,
        categories=categories,
        total_items=len(grocery_items),
        estimated_total_cost=None,
    )


def _categorize_ingredient(ingredient_name: str) -> str:
    """
    Categorize an ingredient into a grocery store section.

    Args:
        ingredient_name: Name of the ingredient (lowercase)

    Returns:
        Category name
    """
    # Meat & Poultry
    if any(
        word in ingredient_name
        for word in ["chicken", "beef", "pork", "lamb", "turkey", "duck", "meat", "thigh", "breast"]
    ):
        return "Meat & Poultry"

    # Seafood
    if any(
        word in ingredient_name
        for word in ["fish", "salmon", "tuna", "shrimp", "cod", "tilapia", "seafood"]
    ):
        return "Seafood"

    # Produce
    if any(
        word in ingredient_name
        for word in [
            "carrot",
            "onion",
            "tomato",
            "potato",
            "broccoli",
            "lettuce",
            "pepper",
            "garlic",
            "vegetable",
            "fruit",
            "apple",
            "banana",
            "spinach",
            "cucumber",
            "mushroom",
        ]
    ):
        return "Produce"

    # Dairy
    if any(
        word in ingredient_name
        for word in ["milk", "cheese", "butter", "cream", "yogurt", "egg"]
    ):
        return "Dairy & Eggs"

    # Pantry
    if any(
        word in ingredient_name
        for word in [
            "rice",
            "pasta",
            "flour",
            "sugar",
            "salt",
            "pepper",
            "oil",
            "vinegar",
            "sauce",
            "spice",
            "bean",
            "lentil",
            "noodle",
            "cumin",
            "coriander",
        ]
    ):
        return "Pantry"

    # Bakery
    if any(word in ingredient_name for word in ["bread", "tortilla", "pita", "bun"]):
        return "Bakery"

    return "Other"


def _generate_nutrition_notes(
    recommendations: list[RecipeRecommendation], days: int
) -> str:
    """
    Generate nutrition notes from recommendations.

    Args:
        recommendations: List of recipe recommendations
        days: Number of days planned

    Returns:
        Nutrition notes string
    """
    if not recommendations:
        return "No recipes available for nutritional analysis."

    # Calculate average nutrition if available
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    recipes_with_nutrition = 0

    for recipe in recommendations:
        if recipe.nutrition:
            total_calories += recipe.nutrition.get("calories", 0)
            total_protein += recipe.nutrition.get("protein", 0)
            total_carbs += recipe.nutrition.get("carbs", 0)
            total_fat += recipe.nutrition.get("fat", 0)
            recipes_with_nutrition += 1

    if recipes_with_nutrition > 0:
        avg_calories = total_calories / recipes_with_nutrition
        avg_protein = total_protein / recipes_with_nutrition
        avg_carbs = total_carbs / recipes_with_nutrition
        avg_fat = total_fat / recipes_with_nutrition

        return (
            f"Based on your {days}-day meal plan with {len(recommendations)} recipes, "
            f"the average meal contains approximately {avg_calories:.0f} calories, "
            f"{avg_protein:.0f}g protein, {avg_carbs:.0f}g carbohydrates, and {avg_fat:.0f}g fat. "
            "This analysis is based on available nutritional data. "
            "Please consult with a nutritionist for personalized dietary advice."
        )
    else:
        return (
            f"Your {days}-day meal plan includes {len(recommendations)} diverse recipes. "
            "Detailed nutritional information is not available for all recipes. "
            "We recommend tracking your meals and consulting with a nutritionist "
            "for personalized dietary guidance."
        )


def _create_mock_response(
    request_data: RecommendationRequest,
    trace_id: str,
) -> RecommendationResponse:
    """
    Create a mock response for testing.

    This will be replaced with real agent-generated recommendations.

    Args:
        request_data: User request
        trace_id: OpenTelemetry trace ID

    Returns:
        Mock recommendation response
    """
    # Mock recipe recommendations
    recommendations = [
        RecipeRecommendation(
            id=1,
            name="Chicken Stir Fry with Vegetables",
            description="A quick and healthy Asian-inspired stir fry with chicken and fresh vegetables",
            cuisine="Asian",
            prep_time=15,
            cook_time=12,
            total_time=27,
            servings=request_data.servings or 4,
            difficulty="easy",
            ingredients=[
                "500g chicken breast, sliced",
                "2 cups broccoli florets",
                "1 bell pepper, sliced",
                "3 cloves garlic, minced",
                "2 tbsp soy sauce",
                "1 tbsp sesame oil",
                "Cooked rice for serving",
            ],
            instructions=[
                "Heat sesame oil in a large wok or skillet over high heat",
                "Add chicken and cook until browned, about 5-6 minutes",
                "Add garlic and cook for 30 seconds until fragrant",
                "Add vegetables and stir fry for 4-5 minutes",
                "Add soy sauce and toss to combine",
                "Serve hot over cooked rice",
            ],
            nutrition={
                "calories": 320,
                "protein": 35,
                "carbs": 25,
                "fat": 10,
                "fiber": 4,
            },
            tags=["quick", "healthy", "high-protein"],
        ),
        RecipeRecommendation(
            id=2,
            name="Mediterranean Grilled Chicken",
            description="Herb-marinated grilled chicken with Mediterranean flavors",
            cuisine="Mediterranean",
            prep_time=10,
            cook_time=20,
            total_time=30,
            servings=request_data.servings or 4,
            difficulty="easy",
            ingredients=[
                "4 chicken breasts",
                "3 tbsp olive oil",
                "2 cloves garlic, minced",
                "1 lemon, juiced",
                "Fresh herbs (oregano, thyme)",
                "Salt and pepper to taste",
            ],
            instructions=[
                "Mix olive oil, garlic, lemon juice, herbs in a bowl",
                "Marinate chicken for at least 30 minutes",
                "Preheat grill to medium-high heat",
                "Grill chicken for 8-10 minutes per side",
                "Let rest for 5 minutes before serving",
            ],
            nutrition={
                "calories": 280,
                "protein": 40,
                "carbs": 3,
                "fat": 12,
                "fiber": 0,
            },
            tags=["grilled", "mediterranean", "lean"],
        ),
        RecipeRecommendation(
            id=3,
            name="Vegetable Fried Rice",
            description="Colorful and flavorful fried rice packed with vegetables",
            cuisine="Asian",
            prep_time=10,
            cook_time=10,
            total_time=20,
            servings=request_data.servings or 4,
            difficulty="easy",
            ingredients=[
                "3 cups cooked rice (day-old works best)",
                "2 cups mixed vegetables (peas, carrots, corn)",
                "3 eggs, beaten",
                "3 tbsp soy sauce",
                "2 green onions, sliced",
                "2 cloves garlic, minced",
                "2 tbsp vegetable oil",
            ],
            instructions=[
                "Heat oil in a large wok over high heat",
                "Add garlic and stir fry for 30 seconds",
                "Push garlic to the side, add eggs and scramble",
                "Add vegetables and stir fry for 3-4 minutes",
                "Add rice and break up any clumps",
                "Add soy sauce and green onions, toss well",
                "Serve hot",
            ],
            nutrition={
                "calories": 290,
                "protein": 10,
                "carbs": 45,
                "fat": 8,
                "fiber": 3,
            },
            tags=["vegetarian", "quick", "budget-friendly"],
        ),
    ]

    # Filter by dietary restrictions if provided
    if request_data.dietary_restrictions:
        if "vegetarian" in [r.lower() for r in request_data.dietary_restrictions]:
            recommendations = [r for r in recommendations if r.id == 3]

    # Mock menu plan
    days = request_data.days or 7
    menu_days = []
    for day in range(1, min(days + 1, 4)):  # Mock only 3 days
        menu_days.append(
            MenuDay(
                day=day,
                date=f"2024-05-{9 + day:02d}",
                meals={
                    "lunch": recommendations[0] if day % 2 == 1 else recommendations[1],
                    "dinner": recommendations[(day - 1) % len(recommendations)],
                },
                notes=f"Day {day} meals",
            )
        )

    menu_plan = MenuPlan(
        days=menu_days,
        total_days=days,
        servings=request_data.servings or 4,
    )

    # Mock grocery list
    grocery_items = [
        GroceryItem(
            ingredient="Chicken breast",
            quantity=1.5,
            unit="kg",
            category="Meat & Poultry",
            estimated_cost=12.99,
        ),
        GroceryItem(
            ingredient="Broccoli",
            quantity=500,
            unit="g",
            category="Produce",
            estimated_cost=3.49,
        ),
        GroceryItem(
            ingredient="Bell peppers",
            quantity=3,
            unit="pcs",
            category="Produce",
            estimated_cost=4.99,
        ),
        GroceryItem(
            ingredient="Garlic",
            quantity=1,
            unit="head",
            category="Produce",
            estimated_cost=0.99,
        ),
        GroceryItem(
            ingredient="Rice",
            quantity=1,
            unit="kg",
            category="Pantry",
            estimated_cost=5.99,
        ),
        GroceryItem(
            ingredient="Soy sauce",
            quantity=1,
            unit="bottle",
            category="Pantry",
            estimated_cost=3.49,
        ),
    ]

    # Organize by category
    categories = {}
    for item in grocery_items:
        category = item.category or "Other"
        if category not in categories:
            categories[category] = []
        categories[category].append(item)

    grocery_list = GroceryList(
        items=grocery_items,
        categories=categories,
        total_items=len(grocery_items),
        estimated_total_cost=sum(item.estimated_cost or 0 for item in grocery_items),
    )

    # Mock nutrition notes
    nutrition_notes = (
        f"Based on your request for {days} days of meals, "
        "the recommended menu provides a balanced distribution of macronutrients. "
        "Average daily intake: 890 calories from lunch and dinner, with 85g protein, "
        "73g carbohydrates, and 30g fat. "
        "The meal plan includes a good variety of vegetables and lean proteins."
    )

    # Mock warnings
    warnings = []
    if request_data.dietary_restrictions:
        restrictions = ", ".join(request_data.dietary_restrictions)
        warnings.append(f"Filtered recipes to match dietary restrictions: {restrictions}")

    # Create response
    return RecommendationResponse(
        recommendations=recommendations,
        menu_plan=menu_plan,
        grocery_list=grocery_list,
        nutrition_notes=nutrition_notes,
        warnings=warnings,
        trace_id=trace_id,
        metadata={
            "processing_time_ms": 150,
            "agent_version": "mock",
            "request_message": request_data.message,
        },
    )