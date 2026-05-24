"""
Pydantic schemas for nutrition estimation.

Pure data shapes — no LLM calls live here.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class NutritionEstimate(BaseModel):
    """
    Estimated macro- and micronutrient values for a single recipe serving.

    All fields are optional so partial estimates (e.g. only calories +
    protein) are representable.
    """

    calories: Optional[int] = Field(default=None, ge=0)
    protein_g: Optional[float] = Field(default=None, ge=0)
    carbs_g: Optional[float] = Field(default=None, ge=0)
    fat_g: Optional[float] = Field(default=None, ge=0)
    fiber_g: Optional[float] = Field(default=None, ge=0)
    sugar_g: Optional[float] = Field(default=None, ge=0)
    sodium_mg: Optional[float] = Field(default=None, ge=0)


class NutritionNote(BaseModel):
    """
    Per-recipe nutrition output from the Nutrition Agent.

    `confidence` indicates how trustworthy the estimate is given the
    available data (e.g. how many ingredients had quantity info).
    """

    recipe_id: str
    recipe_name: str
    estimate: NutritionEstimate
    health_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "low"
    usda_grounded: bool = Field(
        default=False,
        description="True when authoritative USDA reference data was injected into the estimate.",
    )