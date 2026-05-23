"""
Database models.

Import all models here for Alembic discovery.
"""

from app.models.agent_run import AgentRun
from app.models.api_key import ApiKey
from app.models.ingredient import Ingredient
from app.models.menu import GroceryList, Menu, MenuDay
from app.models.recipe import Recipe, recipe_ingredients
from app.models.user_preference import UserPreference

__all__ = [
    "Recipe",
    "Ingredient",
    "UserPreference",
    "Menu",
    "MenuDay",
    "GroceryList",
    "AgentRun",
    "ApiKey",
    "recipe_ingredients",
]