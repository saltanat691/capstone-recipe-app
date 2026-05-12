"""
Menu and meal planning models.
"""

from datetime import date
from typing import Optional, List

from sqlalchemy import JSON, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Menu(Base, TimestampMixin):
    """
    Menu model representing a meal plan.
    """

    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # User identifier
    user_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Menu details
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Date range
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Number of days
    days_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Agent run that generated this menu
    agent_run_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    menu_days: Mapped[List["MenuDay"]] = relationship(
        "MenuDay",
        back_populates="menu",
        cascade="all, delete-orphan",
    )
    grocery_lists: Mapped[List["GroceryList"]] = relationship(
        "GroceryList",
        back_populates="menu",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Menu(id={self.id}, name='{self.name}', user_id='{self.user_id}')>"


class MenuDay(Base, TimestampMixin):
    """
    MenuDay model representing a single day in a menu.
    """

    __tablename__ = "menu_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Parent menu
    menu_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("menus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Day information
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-based
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Meal assignments stored as JSON
    # Example: {
    #   "breakfast": {"recipe_id": 1, "recipe_name": "Omelette"},
    #   "lunch": {"recipe_id": 2, "recipe_name": "Caesar Salad"},
    #   "dinner": {"recipe_id": 3, "recipe_name": "Grilled Chicken"}
    # }
    meals: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Notes for this day
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    menu: Mapped["Menu"] = relationship("Menu", back_populates="menu_days")

    def __repr__(self) -> str:
        return f"<MenuDay(id={self.id}, menu_id={self.menu_id}, day={self.day_number})>"


class GroceryList(Base, TimestampMixin):
    """
    GroceryList model for storing shopping lists generated from menus.
    """

    __tablename__ = "grocery_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Parent menu
    menu_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("menus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # List details
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Items stored as JSON
    # Example: [
    #   {"ingredient": "chicken", "quantity": 2, "unit": "lbs", "category": "meat"},
    #   {"ingredient": "tomatoes", "quantity": 5, "unit": "pcs", "category": "produce"}
    # ]
    items: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Total estimated cost (optional)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    menu: Mapped["Menu"] = relationship("Menu", back_populates="grocery_lists")

    def __repr__(self) -> str:
        return f"<GroceryList(id={self.id}, name='{self.name}', menu_id={self.menu_id})>"