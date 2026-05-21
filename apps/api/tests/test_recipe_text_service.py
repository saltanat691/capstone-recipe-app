"""
Unit tests for recipe_text_service.build_searchable_text — pure function,
no DB and no OpenAI required.
"""

from types import SimpleNamespace

from app.services.recipe_text_service import build_searchable_text


def _ing(name: str) -> SimpleNamespace:
    """Stub for SQLAlchemy Ingredient (only .name is read)."""
    return SimpleNamespace(name=name)


def _recipe(**overrides) -> SimpleNamespace:
    defaults = dict(
        name=None,
        cuisine=None,
        meal_type=None,
        ingredients=None,
        dietary_tags=None,
        allergen_tags=None,
        total_time=None,
        prep_time=None,
        cook_time=None,
        instructions=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestHappyPath:
    def test_full_recipe_includes_all_sections(self):
        recipe = _recipe(
            name="Chicken Plov",
            cuisine="Central Asian",
            meal_type="dinner",
            ingredients=[_ing("chicken"), _ing("rice"), _ing("carrot"), _ing("onion")],
            dietary_tags=["halal-friendly"],
            total_time=60,
            instructions=["Step 1.", "Step 2."],
        )
        text = build_searchable_text(recipe)
        assert "Chicken Plov" in text
        assert "Cuisine: Central Asian" in text
        assert "Meal type: dinner" in text
        assert "Ingredients: chicken, rice, carrot, onion" in text
        assert "Diet tags: halal-friendly" in text
        assert "Cooking time: 60 minutes" in text
        assert "Instructions: Step 1. Step 2." in text


class TestMissingFields:
    def test_skips_missing_fields(self):
        text = build_searchable_text(_recipe(name="Toast"))
        assert text == "Toast."

    def test_empty_recipe_returns_empty_string(self):
        assert build_searchable_text(_recipe()) == ""

    def test_skips_blank_string_fields(self):
        text = build_searchable_text(
            _recipe(name="Toast", cuisine="   ", meal_type="")
        )
        assert "Cuisine" not in text
        assert "Meal type" not in text
        assert "Toast" in text


class TestCookingTime:
    def test_uses_total_time_when_present(self):
        text = build_searchable_text(
            _recipe(name="X", total_time=45, prep_time=10, cook_time=10)
        )
        assert "Cooking time: 45 minutes" in text

    def test_falls_back_to_sum_of_prep_and_cook(self):
        text = build_searchable_text(_recipe(name="X", prep_time=10, cook_time=20))
        assert "Cooking time: 30 minutes" in text

    def test_omits_when_no_times(self):
        text = build_searchable_text(_recipe(name="X"))
        assert "Cooking time" not in text


class TestInstructionsFormats:
    def test_list_of_strings(self):
        text = build_searchable_text(
            _recipe(name="X", instructions=["one", "two", "three"])
        )
        assert "Instructions: one two three" in text

    def test_dict_with_steps_field(self):
        text = build_searchable_text(
            _recipe(name="X", instructions={"steps": ["one", "two"]})
        )
        assert "Instructions: one two" in text

    def test_plain_string(self):
        text = build_searchable_text(_recipe(name="X", instructions="cook it"))
        assert "Instructions: cook it" in text


class TestTags:
    def test_dietary_tags_as_list(self):
        text = build_searchable_text(
            _recipe(name="X", dietary_tags=["vegan", "gluten-free"])
        )
        assert "Diet tags: vegan, gluten-free" in text

    def test_allergen_tags_appear_when_present(self):
        text = build_searchable_text(
            _recipe(name="X", allergen_tags=["nuts", "soy"])
        )
        assert "Allergen tags: nuts, soy" in text

    def test_no_allergen_section_when_missing(self):
        text = build_searchable_text(_recipe(name="X"))
        assert "Allergen tags" not in text