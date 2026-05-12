"""
User preferences model.
"""

from typing import Optional

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserPreference(Base, TimestampMixin):
    """
    User preferences model for storing dietary restrictions and preferences.
    """

    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User identifier (can be session ID, user ID, or any identifier)
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)

    # Dietary restrictions stored as JSON array
    # Example: ["vegetarian", "gluten-free", "dairy-free"]
    dietary_restrictions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Cuisine preferences stored as JSON array
    # Example: ["italian", "mexican", "asian"]
    cuisine_preferences: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Allergies stored as JSON array
    # Example: ["peanuts", "shellfish", "eggs"]
    allergies: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Disliked ingredients stored as JSON array
    disliked_ingredients: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Preferred cooking time in minutes
    max_cooking_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Skill level: "beginner", "intermediate", "advanced"
    skill_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Additional notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<UserPreference(id={self.id}, user_id='{self.user_id}')>"