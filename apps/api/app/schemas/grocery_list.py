"""
Pydantic schemas for grocery-list planning.

Pure data shapes used by the Grocery List Agent. Distinct from the API
response schemas in `app/schemas/recommendation.py` (which carry a different
`GroceryItem` / `GroceryList` shape consumed by the public endpoint).
Import these types via their qualified path:

    from app.schemas.grocery_list import GroceryItem, GroceryList
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


GroceryCategory = Literal[
    "meat",
    "vegetables",
    "fruits",
    "dairy",
    "grains",
    "pantry",
    "spices",
    "other",
]


class GroceryItem(BaseModel):
    """A single grocery line item, with provenance back to the recipes that
    use it and a flag for items the user already has on hand."""

    name: str
    category: Optional[GroceryCategory] = None
    quantity: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    recipes_used_in: list[str] = Field(default_factory=list)
    already_available: bool = False
    notes: list[str] = Field(default_factory=list)


class GroceryList(BaseModel):
    """A complete grocery list produced by the Grocery List Agent."""

    items: list[GroceryItem] = Field(default_factory=list)
    summary: str = ""
    warnings: list[str] = Field(default_factory=list)