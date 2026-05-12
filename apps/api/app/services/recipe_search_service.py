"""
Recipe search service for matching recipes based on ingredients and preferences.

This service provides basic recipe search functionality without AI/RAG.
It uses simple scoring to rank recipes based on ingredient matches,
cuisine preferences, and dietary restrictions.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.observability import get_logger

logger = get_logger(__name__)


class RecipeSearchService:
    """
    Service for searching and ranking recipes.

    Scoring system:
    - +2 points for each matching ingredient
    - +3 points for matching cuisine preference
    - -100 points for dietary restriction conflict
    """

    # Mapping of common dietary restrictions to diet tags
    DIETARY_RESTRICTIONS_MAP = {
        "vegetarian": ["vegetarian"],
        "vegan": ["vegan"],
        "gluten-free": ["gluten-free", "gluten free"],
        "dairy-free": ["dairy-free", "dairy free"],
        "nut-free": ["nut-free", "nut free"],
        "egg-free": ["egg-free", "egg free"],
        "soy-free": ["soy-free", "soy free"],
        "paleo": ["paleo"],
        "keto": ["keto", "low-carb"],
        "low-carb": ["low-carb", "keto"],
    }

    # Common allergen keywords to check in ingredient names
    ALLERGEN_KEYWORDS = {
        "dairy": ["milk", "cheese", "butter", "cream", "yogurt", "dairy"],
        "gluten": ["wheat", "flour", "bread", "pasta", "noodle"],
        "nuts": ["nut", "almond", "walnut", "cashew", "pecan", "peanut"],
        "eggs": ["egg"],
        "soy": ["soy", "tofu", "tempeh"],
        "shellfish": ["shrimp", "crab", "lobster", "shellfish"],
        "fish": ["fish", "salmon", "tuna", "cod"],
    }

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the search service.

        Args:
            db_session: Database session for queries
        """
        self.db_session = db_session

    async def search_recipes(
        self,
        available_ingredients: Optional[list[str]] = None,
        dietary_restrictions: Optional[list[str]] = None,
        cuisine_preferences: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[tuple[Recipe, float]]:
        """
        Search and rank recipes based on criteria.

        Args:
            available_ingredients: List of ingredients user has
            dietary_restrictions: List of dietary restrictions
            cuisine_preferences: List of preferred cuisines
            limit: Maximum number of recipes to return

        Returns:
            List of (Recipe, score) tuples, sorted by score descending
        """
        logger.info(
            "Searching recipes",
            extra={
                "ingredients_count": len(available_ingredients or []),
                "restrictions_count": len(dietary_restrictions or []),
                "cuisines_count": len(cuisine_preferences or []),
                "limit": limit,
            },
        )

        # Normalize inputs to lowercase for matching
        available_ingredients_lower = (
            [ing.lower().strip() for ing in available_ingredients]
            if available_ingredients
            else []
        )
        dietary_restrictions_lower = (
            [rest.lower().strip() for rest in dietary_restrictions]
            if dietary_restrictions
            else []
        )
        cuisine_preferences_lower = (
            [cui.lower().strip() for cui in cuisine_preferences]
            if cuisine_preferences
            else []
        )

        # Query all recipes with their ingredients
        stmt = select(Recipe).options(selectinload(Recipe.ingredients))
        result = await self.db_session.execute(stmt)
        recipes = result.scalars().all()

        logger.info(f"Found {len(recipes)} total recipes in database")

        # Score each recipe
        scored_recipes: list[tuple[Recipe, float]] = []
        for recipe in recipes:
            score = await self._calculate_recipe_score(
                recipe,
                available_ingredients_lower,
                dietary_restrictions_lower,
                cuisine_preferences_lower,
            )

            # Only include recipes with positive scores
            # (negative score means dietary restriction violation)
            if score > 0:
                scored_recipes.append((recipe, score))

        # Sort by score descending
        scored_recipes.sort(key=lambda x: x[1], reverse=True)

        # Return top N recipes
        top_recipes = scored_recipes[:limit]

        logger.info(
            "Recipe search completed",
            extra={
                "total_recipes": len(recipes),
                "matched_recipes": len(scored_recipes),
                "returned_recipes": len(top_recipes),
                "top_score": top_recipes[0][1] if top_recipes else 0,
            },
        )

        return top_recipes

    async def _calculate_recipe_score(
        self,
        recipe: Recipe,
        available_ingredients: list[str],
        dietary_restrictions: list[str],
        cuisine_preferences: list[str],
    ) -> float:
        """
        Calculate score for a single recipe.

        Args:
            recipe: Recipe to score
            available_ingredients: User's available ingredients (lowercase)
            dietary_restrictions: User's dietary restrictions (lowercase)
            cuisine_preferences: User's cuisine preferences (lowercase)

        Returns:
            Score for the recipe (can be negative if restrictions violated)
        """
        score = 0.0

        # Check dietary restrictions first (-100 if violated)
        if dietary_restrictions:
            if self._violates_dietary_restrictions(recipe, dietary_restrictions):
                logger.debug(
                    f"Recipe '{recipe.name}' violates dietary restrictions",
                    extra={"recipe_id": recipe.id, "restrictions": dietary_restrictions},
                )
                return -100.0

        # Add points for matching ingredients (+2 each)
        if available_ingredients:
            ingredient_matches = self._count_ingredient_matches(
                recipe, available_ingredients
            )
            score += ingredient_matches * 2
            logger.debug(
                f"Recipe '{recipe.name}' has {ingredient_matches} ingredient matches",
                extra={"recipe_id": recipe.id, "matches": ingredient_matches},
            )

        # Add points for matching cuisine (+3)
        if cuisine_preferences and recipe.cuisine:
            recipe_cuisine = recipe.cuisine.lower().strip()
            if recipe_cuisine in cuisine_preferences:
                score += 3
                logger.debug(
                    f"Recipe '{recipe.name}' matches cuisine preference",
                    extra={"recipe_id": recipe.id, "cuisine": recipe.cuisine},
                )

        return score

    def _count_ingredient_matches(
        self, recipe: Recipe, available_ingredients: list[str]
    ) -> int:
        """
        Count how many recipe ingredients match user's available ingredients.

        Uses fuzzy matching - checks if available ingredient is contained
        in recipe ingredient name or vice versa.

        Args:
            recipe: Recipe to check
            available_ingredients: User's available ingredients (lowercase)

        Returns:
            Number of matching ingredients
        """
        matches = 0

        for recipe_ingredient in recipe.ingredients:
            recipe_ingredient_name = recipe_ingredient.name.lower().strip()

            for available_ingredient in available_ingredients:
                # Check if either ingredient contains the other
                # This handles variations like "chicken" matching "chicken breast"
                if (
                    available_ingredient in recipe_ingredient_name
                    or recipe_ingredient_name in available_ingredient
                ):
                    matches += 1
                    break  # Count each recipe ingredient only once

        return matches

    def _violates_dietary_restrictions(
        self, recipe: Recipe, dietary_restrictions: list[str]
    ) -> bool:
        """
        Check if recipe violates any dietary restrictions.

        Checks both the recipe's dietary tags and ingredient names.

        Args:
            recipe: Recipe to check
            dietary_restrictions: User's dietary restrictions (lowercase)

        Returns:
            True if recipe violates any restriction, False otherwise
        """
        # Check if recipe explicitly supports the diet
        # For example, if user is vegetarian and recipe is tagged vegetarian, it's OK
        if recipe.dietary_tags:
            recipe_tags_lower = [tag.lower() for tag in recipe.dietary_tags]

            for restriction in dietary_restrictions:
                # Map the restriction to possible tag variations
                possible_tags = self.DIETARY_RESTRICTIONS_MAP.get(restriction, [restriction])

                # If recipe has a tag that matches the restriction, it's compliant
                if any(tag in recipe_tags_lower for tag in possible_tags):
                    # Recipe explicitly supports this diet
                    continue
                else:
                    # Recipe doesn't claim to support this diet
                    # Check if ingredients violate the restriction
                    if self._check_ingredients_for_allergens(recipe, restriction):
                        return True
        else:
            # No dietary tags, check ingredients for all restrictions
            for restriction in dietary_restrictions:
                if self._check_ingredients_for_allergens(recipe, restriction):
                    return True

        return False

    def _check_ingredients_for_allergens(
        self, recipe: Recipe, restriction: str
    ) -> bool:
        """
        Check if recipe ingredients contain allergens for a dietary restriction.

        Args:
            recipe: Recipe to check
            restriction: Dietary restriction (lowercase)

        Returns:
            True if ingredients contain restricted items, False otherwise
        """
        # Map dietary restriction to allergen category
        allergen_category = None

        if "dairy" in restriction or "lactose" in restriction:
            allergen_category = "dairy"
        elif "gluten" in restriction:
            allergen_category = "gluten"
        elif "nut" in restriction:
            allergen_category = "nuts"
        elif "egg" in restriction:
            allergen_category = "eggs"
        elif "soy" in restriction:
            allergen_category = "soy"
        elif "shellfish" in restriction:
            allergen_category = "shellfish"
        elif "fish" in restriction:
            allergen_category = "fish"
        elif restriction == "vegetarian":
            # Check for meat/fish ingredients
            meat_keywords = [
                "chicken",
                "beef",
                "pork",
                "lamb",
                "turkey",
                "duck",
                "fish",
                "salmon",
                "tuna",
                "shrimp",
                "meat",
            ]
            for ingredient in recipe.ingredients:
                ingredient_name_lower = ingredient.name.lower()
                if any(keyword in ingredient_name_lower for keyword in meat_keywords):
                    return True
            return False
        elif restriction == "vegan":
            # Check for any animal products
            animal_keywords = [
                "chicken",
                "beef",
                "pork",
                "lamb",
                "turkey",
                "duck",
                "fish",
                "salmon",
                "tuna",
                "shrimp",
                "meat",
                "egg",
                "milk",
                "cheese",
                "butter",
                "cream",
                "yogurt",
                "honey",
            ]
            for ingredient in recipe.ingredients:
                ingredient_name_lower = ingredient.name.lower()
                if any(keyword in ingredient_name_lower for keyword in animal_keywords):
                    return True
            return False

        # Check ingredients for allergen keywords
        if allergen_category and allergen_category in self.ALLERGEN_KEYWORDS:
            keywords = self.ALLERGEN_KEYWORDS[allergen_category]
            for ingredient in recipe.ingredients:
                ingredient_name_lower = ingredient.name.lower()
                if any(keyword in ingredient_name_lower for keyword in keywords):
                    return True

        return False


async def search_recipes(
    db_session: AsyncSession,
    available_ingredients: Optional[list[str]] = None,
    dietary_restrictions: Optional[list[str]] = None,
    cuisine_preferences: Optional[list[str]] = None,
    limit: int = 10,
) -> list[tuple[Recipe, float]]:
    """
    Convenience function to search recipes.

    Args:
        db_session: Database session
        available_ingredients: List of ingredients user has
        dietary_restrictions: List of dietary restrictions
        cuisine_preferences: List of preferred cuisines
        limit: Maximum number of recipes to return

    Returns:
        List of (Recipe, score) tuples, sorted by score descending
    """
    service = RecipeSearchService(db_session)
    return await service.search_recipes(
        available_ingredients=available_ingredients,
        dietary_restrictions=dietary_restrictions,
        cuisine_preferences=cuisine_preferences,
        limit=limit,
    )