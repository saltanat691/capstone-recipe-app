"""
Recipe model and related tables.
"""

from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Table,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


# Association table for many-to-many relationship between recipes and ingredients
recipe_ingredients = Table(
    "recipe_ingredients",
    Base.metadata,
    Column("recipe_id", Integer, ForeignKey("recipes.id", ondelete="CASCADE"), primary_key=True),
    Column("ingredient_id", Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), primary_key=True),
    Column("quantity", Float, nullable=True),
    Column("unit", String(50), nullable=True),
    Column("preparation", String(200), nullable=True),
)


class Recipe(Base, TimestampMixin):
    """
    Recipe model representing individual recipes.
    """

    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Recipe details
    cuisine: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    meal_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # breakfast, lunch, dinner, snack
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # easy, medium, hard

    # Time in minutes
    prep_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cook_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Servings
    servings: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Instructions stored as JSON array
    instructions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Nutrition information (stored as JSON)
    nutrition: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Dietary tags (stored as JSON array)
    dietary_tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Vector embedding for semantic search (1536 dimensions for OpenAI embeddings)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)

    # Source information
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    ingredients = relationship(
        "Ingredient",
        secondary=recipe_ingredients,
        back_populates="recipes",
    )

    def __repr__(self) -> str:
        return f"<Recipe(id={self.id}, name='{self.name}', cuisine='{self.cuisine}')>"