"""
Test script for recipe search functionality.

Usage:
    python scripts/test_search.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.services.recipe_search_service import search_recipes


async def test_search():
    """
    Test the recipe search service with different scenarios.
    """
    print("=" * 80)
    print("Recipe Search Service Test")
    print("=" * 80)

    test_cases = [
        {
            "name": "Search with chicken and rice",
            "ingredients": ["chicken", "rice"],
            "restrictions": [],
            "cuisines": [],
        },
        {
            "name": "Vegetarian search",
            "ingredients": ["rice", "vegetables"],
            "restrictions": ["vegetarian"],
            "cuisines": [],
        },
        {
            "name": "Central Asian cuisine preference",
            "ingredients": ["beef", "rice", "carrots"],
            "restrictions": [],
            "cuisines": ["Central Asian"],
        },
        {
            "name": "Gluten-free with chicken",
            "ingredients": ["chicken"],
            "restrictions": ["gluten-free"],
            "cuisines": [],
        },
        {
            "name": "Asian cuisine with multiple ingredients",
            "ingredients": ["chicken", "rice", "soy sauce", "garlic"],
            "restrictions": [],
            "cuisines": ["Asian"],
        },
    ]

    async with AsyncSessionLocal() as db:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'─' * 80}")
            print(f"Test {i}: {test_case['name']}")
            print(f"{'─' * 80}")
            print(f"Ingredients: {', '.join(test_case['ingredients'])}")
            if test_case["restrictions"]:
                print(f"Restrictions: {', '.join(test_case['restrictions'])}")
            if test_case["cuisines"]:
                print(f"Cuisines: {', '.join(test_case['cuisines'])}")
            print()

            try:
                results = await search_recipes(
                    db_session=db,
                    available_ingredients=test_case["ingredients"],
                    dietary_restrictions=test_case["restrictions"],
                    cuisine_preferences=test_case["cuisines"],
                    limit=5,
                )

                if results:
                    print(f"Found {len(results)} recipes:\n")
                    for idx, (recipe, score) in enumerate(results, 1):
                        print(f"{idx}. {recipe.name}")
                        print(f"   Cuisine: {recipe.cuisine or 'N/A'}")
                        print(f"   Score: {score:.1f} points")
                        print(f"   Difficulty: {recipe.difficulty or 'N/A'}")
                        print(f"   Time: {recipe.total_time or 'N/A'} minutes")
                        if recipe.dietary_tags:
                            print(f"   Tags: {', '.join(recipe.dietary_tags)}")
                        print()
                else:
                    print("No recipes found matching criteria.")

            except Exception as e:
                print(f"✗ Error: {e}")

    print("=" * 80)
    print("Test completed!")
    print("=" * 80)


async def main():
    """
    Main entry point.
    """
    try:
        await test_search()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())