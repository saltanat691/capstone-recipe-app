"""
Script to seed the database with recipe data.

Usage:
    python scripts/seed_recipes.py
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe, recipe_ingredients
from app.observability.logging import get_logger

logger = get_logger(__name__)


async def get_or_create_ingredient(
    session,
    ingredient_name: str,
    ingredient_cache: dict[str, int],
) -> int:
    """
    Get or create an ingredient and return its ID.

    Args:
        session: Database session
        ingredient_name: Name of the ingredient
        ingredient_cache: Cache of ingredient names to IDs

    Returns:
        int: Ingredient ID
    """
    # Check cache first
    if ingredient_name in ingredient_cache:
        return ingredient_cache[ingredient_name]

    # Check if ingredient exists in database
    result = await session.execute(
        select(Ingredient).where(Ingredient.name == ingredient_name)
    )
    ingredient = result.scalar_one_or_none()

    if ingredient:
        ingredient_cache[ingredient_name] = ingredient.id
        return ingredient.id

    # Create new ingredient
    new_ingredient = Ingredient(name=ingredient_name)
    session.add(new_ingredient)
    await session.flush()  # Get the ID without committing

    ingredient_cache[new_ingredient.name] = new_ingredient.id
    logger.info(f"Created ingredient: {ingredient_name} (ID: {new_ingredient.id})")

    return new_ingredient.id


async def seed_recipes():
    """
    Seed the database with recipes from JSON file.
    """
    logger.info("Starting recipe seeding process")

    # Load recipes from JSON file
    json_path = Path(__file__).parent.parent / "data" / "recipes_seed.json"

    if not json_path.exists():
        logger.error(f"Recipe data file not found: {json_path}")
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading recipe data file: {e}")
        return

    recipes_data = data.get("recipes", [])
    logger.info(f"Loaded {len(recipes_data)} recipes from JSON file")

    async with AsyncSessionLocal() as session:
        ingredient_cache: dict[str, int] = {}
        recipes_created = 0
        recipes_skipped = 0

        try:
            for recipe_data in recipes_data:
                recipe_name = recipe_data.get("name")

                # Check if recipe already exists
                result = await session.execute(
                    select(Recipe).where(Recipe.name == recipe_name)
                )
                existing_recipe = result.scalar_one_or_none()

                if existing_recipe:
                    logger.info(f"Recipe already exists, skipping: {recipe_name}")
                    recipes_skipped += 1
                    continue

                # Extract ingredients data before creating recipe
                ingredients_data = recipe_data.pop("ingredients", [])

                # Create recipe
                recipe = Recipe(
                    name=recipe_data.get("name"),
                    description=recipe_data.get("description"),
                    cuisine=recipe_data.get("cuisine"),
                    meal_type=recipe_data.get("meal_type"),
                    difficulty=recipe_data.get("difficulty"),
                    prep_time=recipe_data.get("prep_time"),
                    cook_time=recipe_data.get("cook_time"),
                    total_time=recipe_data.get("total_time"),
                    servings=recipe_data.get("servings"),
                    instructions=recipe_data.get("instructions"),
                    dietary_tags=recipe_data.get("diet_tags"),
                    source="seed_data",
                )

                session.add(recipe)
                await session.flush()  # Get recipe ID

                logger.info(f"Created recipe: {recipe.name} (ID: {recipe.id})")

                # Process ingredients and create associations
                for ingredient_data in ingredients_data:
                    ingredient_name = ingredient_data.get("name")
                    quantity = ingredient_data.get("quantity")
                    unit = ingredient_data.get("unit")

                    # Get or create ingredient
                    ingredient_id = await get_or_create_ingredient(
                        session, ingredient_name, ingredient_cache
                    )

                    # Create recipe-ingredient association
                    stmt = recipe_ingredients.insert().values(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient_id,
                        quantity=quantity,
                        unit=unit,
                    )
                    await session.execute(stmt)

                recipes_created += 1

            # Commit all changes
            await session.commit()

            logger.info("=" * 60)
            logger.info(f"Recipe seeding completed!")
            logger.info(f"  Recipes created: {recipes_created}")
            logger.info(f"  Recipes skipped: {recipes_skipped}")
            logger.info(f"  Unique ingredients: {len(ingredient_cache)}")
            logger.info("=" * 60)

        except IntegrityError as e:
            await session.rollback()
            logger.error(f"Database integrity error: {e}")
        except Exception as e:
            await session.rollback()
            logger.error(f"Error seeding recipes: {e}")
            raise


async def main():
    """
    Main entry point for the seeding script.
    """
    try:
        await seed_recipes()
    except KeyboardInterrupt:
        logger.info("Seeding interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error during seeding: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())