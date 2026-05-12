"""
Script to test the recommendations endpoint.
"""

import asyncio
import json

import httpx


async def test_recommendations():
    """
    Test the recommendations endpoint with sample data.
    """
    base_url = "http://localhost:4000"

    print("Testing Recipe Recommendations API")
    print("=" * 60)

    # Test data
    test_cases = [
        {
            "name": "Basic request with ingredients",
            "data": {
                "message": "I have chicken and rice, what can I make?",
                "available_ingredients": ["chicken breast", "rice", "broccoli"],
                "servings": 4,
                "days": 7,
            },
        },
        {
            "name": "Request with dietary restrictions",
            "data": {
                "message": "I need vegetarian meals for the week",
                "available_ingredients": ["rice", "beans", "vegetables"],
                "dietary_restrictions": ["vegetarian"],
                "cuisine_preferences": ["asian", "mediterranean"],
                "servings": 2,
                "days": 5,
            },
        },
        {
            "name": "Simple message only",
            "data": {
                "message": "Plan healthy meals for my family",
                "servings": 4,
                "days": 7,
            },
        },
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['name']}")
            print("-" * 60)

            try:
                response = await client.post(
                    f"{base_url}/api/v1/recommendations",
                    json=test_case["data"],
                )

                if response.status_code == 200:
                    result = response.json()

                    print(f"✓ Status: {response.status_code}")
                    print(f"✓ Recipes found: {len(result['recommendations'])}")
                    print(f"✓ Menu days: {len(result.get('menu_plan', {}).get('days', []))}")
                    print(f"✓ Grocery items: {result.get('grocery_list', {}).get('total_items', 0)}")
                    print(f"✓ Warnings: {len(result.get('warnings', []))}")
                    print(f"✓ Trace ID: {result.get('trace_id', 'N/A')}")

                    # Show first recipe
                    if result["recommendations"]:
                        recipe = result["recommendations"][0]
                        print(f"\nFirst recipe: {recipe['name']}")
                        print(f"  Cuisine: {recipe.get('cuisine', 'N/A')}")
                        print(f"  Time: {recipe.get('total_time', 'N/A')} minutes")
                        print(f"  Difficulty: {recipe.get('difficulty', 'N/A')}")

                    # Show nutrition notes
                    if result.get("nutrition_notes"):
                        print(f"\nNutrition: {result['nutrition_notes'][:100]}...")

                else:
                    print(f"✗ Status: {response.status_code}")
                    print(f"✗ Error: {response.text}")

            except Exception as e:
                print(f"✗ Error: {e}")

    print("\n" + "=" * 60)
    print("Testing completed!")
    print("\nTo view detailed response, use:")
    print('curl -X POST http://localhost:4000/api/v1/recommendations \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"message": "Plan meals for the week", "days": 7}\'')
    print("\nOr visit API docs: http://localhost:4000/docs")


if __name__ == "__main__":
    asyncio.run(test_recommendations())