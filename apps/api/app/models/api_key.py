"""
API key model for authentication and consent management.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ApiKey(Base, TimestampMixin):
    """
    Hashed API keys used to authenticate requests.

    The plaintext key is returned once at creation and never stored.
    key_hash is SHA-256(plaintext_key).
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # SHA-256 hex digest of the plaintext key — never store the raw key.
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    # Human-readable owner identifier (email, username, etc.).
    owner_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # Friendly label so owners can distinguish their keys.
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Whether the owner has consented to LLM/LangSmith tracing.
    tracing_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Soft-delete / revocation flag.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Null means the key never expires.
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<ApiKey(id={self.id}, owner_id='{self.owner_id}', "
            f"name='{self.name}', active={self.is_active})>"
        )
