"""
API key authentication dependency.

Usage:
    # Require auth (raises 401/403 when key is missing/invalid):
    @router.post("/endpoint")
    async def handler(api_key: ApiKey = Depends(require_api_key)):
        ...

    # Optional auth (returns None in dev when REQUIRE_AUTH=False):
    @router.post("/endpoint")
    async def handler(api_key: Optional[ApiKey] = Depends(get_api_key)):
        ...

Key format:  rcp_<url-safe-random-32-bytes>
Stored as:   SHA-256(plaintext_key)  in api_keys.key_hash
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.observability import get_logger

logger = get_logger(__name__)

_KEY_PREFIX = "rcp_"


def generate_api_key() -> str:
    """Return a new plaintext API key.  Call once; hash before storing."""
    return _KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(plaintext: str) -> str:
    """SHA-256 hex digest used for storage and lookup."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


async def get_api_key(
    x_api_key: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[ApiKey]:
    """
    Resolve an API key from the X-API-Key header.

    - When REQUIRE_AUTH=False (development) and no header is supplied,
      returns None so endpoints work without a key.
    - When REQUIRE_AUTH=True, absence of the header raises 401.
    - A present but invalid/expired key always raises 403.
    """
    if x_api_key is None:
        if not settings.REQUIRE_AUTH:
            return None
        raise HTTPException(
            status_code=401,
            detail="X-API-Key header is required.",
        )

    key_hash = hash_key(x_api_key)
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        logger.warning("api_auth_failed", extra={"reason": "key_not_found"})
        raise HTTPException(status_code=403, detail="Invalid or inactive API key.")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        logger.warning(
            "api_auth_failed",
            extra={"reason": "key_expired", "owner": api_key.owner_id},
        )
        raise HTTPException(status_code=403, detail="API key has expired.")

    return api_key


async def require_api_key(
    api_key: Optional[ApiKey] = Depends(get_api_key),
) -> ApiKey:
    """Strict variant — raises 401 when auth is disabled and no key supplied."""
    if api_key is None:
        raise HTTPException(
            status_code=401,
            detail="X-API-Key header is required for this endpoint.",
        )
    return api_key
