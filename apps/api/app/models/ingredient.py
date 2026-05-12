"""
Ingredient model.
"""

from typing import Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.recipe import recipe_ingredients


class Ingredient(Base, TimestampMixin):
    """
    Ingredient model representing individual ingredients.
    """

    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Nutritional information (optional)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Common unit for this ingredient
    common_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    recipes = relationship(
        "Recipe",
        secondary=recipe_ingredients,
        back_populates="ingredients",
    )

    def __repr__(self) -> str:
        return f"<Ingredient(id={self.id}, name='{self.name}', category='{self.category}')>"