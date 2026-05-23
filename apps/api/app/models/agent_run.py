"""
Agent run model for tracking AI agent executions.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AgentRun(Base, TimestampMixin):
    """
    AgentRun model for tracking LangGraph agent executions.
    """

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Run identification
    run_id: Mapped[str] = mapped_column(String(200), nullable=False, unique=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # User context
    user_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)

    # Run status: "pending", "running", "completed", "failed"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    # Input data stored as JSON
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Output data stored as JSON
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing information
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # LLM usage tracking
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # LangSmith trace ID for correlation
    langsmith_trace_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # OpenTelemetry trace ID for correlation
    otel_trace_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Metadata stored as JSON (flexible for additional information)
    extra_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    # Retention: NULL means keep forever; set to enforce automated cleanup.
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    def __repr__(self) -> str:
        return f"<AgentRun(id={self.id}, run_id='{self.run_id}', agent_type='{self.agent_type}', status='{self.status}')>"