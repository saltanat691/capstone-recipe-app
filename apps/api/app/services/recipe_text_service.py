"""
Build searchable text from a Recipe for embedding generation.

Pure function: no I/O, no DB access. Given a Recipe (or any object with the
expected attributes), return a single string suitable for passing to an
embedding model.
"""

from typing import Any


def build_searchable_text(recipe: Any) -> str:
    """
    Convert a Recipe-like object into a single descriptive sentence string.

    Skips any section whose source field is missing, None, or empty so the
    output stays clean for embedding.
    """
    parts: list[str] = []

    name = _clean(getattr(recipe, "name", None))
    if name:
        parts.append(name)

    cuisine = _clean(getattr(recipe, "cuisine", None))
    if cuisine:
        parts.append(f"Cuisine: {cuisine}")

    meal_type = _clean(getattr(recipe, "meal_type", None))
    if meal_type:
        parts.append(f"Meal type: {meal_type}")

    ingredient_names = _ingredient_names(getattr(recipe, "ingredients", None))
    if ingredient_names:
        parts.append(f"Ingredients: {', '.join(ingredient_names)}")

    diet_tags = _tag_list(getattr(recipe, "dietary_tags", None))
    if diet_tags:
        parts.append(f"Diet tags: {', '.join(diet_tags)}")

    allergen_tags = _tag_list(getattr(recipe, "allergen_tags", None))
    if allergen_tags:
        parts.append(f"Allergen tags: {', '.join(allergen_tags)}")

    cooking_minutes = _cooking_time_minutes(recipe)
    if cooking_minutes is not None:
        parts.append(f"Cooking time: {cooking_minutes} minutes")

    instructions = _instructions_text(getattr(recipe, "instructions", None))
    if instructions:
        parts.append(f"Instructions: {instructions}")

    return ". ".join(parts) + "." if parts else ""


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _ingredient_names(ingredients: Any) -> list[str]:
    if not ingredients:
        return []
    names: list[str] = []
    for ing in ingredients:
        name = _clean(getattr(ing, "name", None))
        if name:
            names.append(name)
    return names


def _tag_list(tags: Any) -> list[str]:
    if not tags:
        return []
    if isinstance(tags, (list, tuple)):
        return [_clean(t) for t in tags if _clean(t)]
    if isinstance(tags, dict):
        return [_clean(t) for t in tags.keys() if _clean(t)]
    cleaned = _clean(tags)
    return [cleaned] if cleaned else []


def _cooking_time_minutes(recipe: Any) -> int | None:
    total = getattr(recipe, "total_time", None)
    if isinstance(total, int) and total > 0:
        return total
    prep = getattr(recipe, "prep_time", None) or 0
    cook = getattr(recipe, "cook_time", None) or 0
    summed = (prep if isinstance(prep, int) else 0) + (cook if isinstance(cook, int) else 0)
    return summed if summed > 0 else None


def _instructions_text(instructions: Any) -> str:
    if not instructions:
        return ""
    if isinstance(instructions, list):
        steps = [_clean(s) for s in instructions if _clean(s)]
        return " ".join(steps)
    if isinstance(instructions, dict):
        steps_field = instructions.get("steps") if "steps" in instructions else None
        if isinstance(steps_field, list):
            return " ".join(_clean(s) for s in steps_field if _clean(s))
        return _clean(instructions)
    return _clean(instructions)