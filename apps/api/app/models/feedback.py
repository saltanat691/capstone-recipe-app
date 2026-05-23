"""Feedback model for collecting per-recommendation quality ratings."""

from typing import Optional

from sqlalchemy import Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Ties back to RecommendationResponse.trace_id so it can be correlated
    # with LangSmith traces and OpenTelemetry spans.
    trace_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # 1 (poor) – 5 (excellent)
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Free-text comment (optional)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Owner of the API key that submitted feedback, for aggregation.
    owner_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<Feedback(id={self.id}, trace_id='{self.trace_id}', rating={self.rating})>"
