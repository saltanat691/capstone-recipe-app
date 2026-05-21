"""
Pydantic schemas for menu planning.

Pure data shapes used by the Menu Planner Agent. Distinct from the API
response schemas in `app/schemas/recommendation.py` (which carry a richer
`MenuDay` / `MenuPlan` shape used by the public endpoint). Import these
types via their qualified path:

    from app.schemas.menu_plan import MenuMeal, MenuDay, MenuPlan
"""

from typing import Optional

from pydantic import BaseModel, Field


class MenuMeal(BaseModel):
    """One scheduled meal within a menu day."""

    day: int = Field(..., ge=1)
    meal_type: str
    recipe_id: Optional[str] = None
    recipe_name: str
    reason: str = ""
    notes: list[str] = Field(default_factory=list)


class MenuDay(BaseModel):
    """All meals planned for a single day."""

    day: int = Field(..., ge=1)
    meals: list[MenuMeal] = Field(default_factory=list)


class MenuPlan(BaseModel):
    """A multi-day menu plan plus an optional summary and warnings."""

    days: list[MenuDay] = Field(default_factory=list)
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)