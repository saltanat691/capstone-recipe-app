"""
Redis-backed async cache helpers.

All functions are no-ops when REDIS_URL is unset, so the app works fine
without Redis in development.
"""

import hashlib
import json
from typing import Optional

from app.core.config import settings
from app.observability import get_logger

logger = get_logger(__name__)

_EMBEDDING_TTL = 86_400  # 24 hours


def _embedding_key(query: str) -> str:
    digest = hashlib.sha256(query.encode()).hexdigest()
    return f"emb:v1:{digest}"


async def get_embedding(query: str) -> Optional[list[float]]:
    """Return cached embedding for *query*, or None on miss / Redis unavailable."""
    if not settings.REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        raw = await client.get(_embedding_key(query))
        await client.aclose()
        if raw:
            logger.debug("embedding_cache_hit", extra={"query_len": len(query)})
            return json.loads(raw)
    except Exception as exc:
        logger.warning("embedding_cache_get_failed", extra={"error": str(exc)})
    return None


async def set_embedding(query: str, embedding: list[float]) -> None:
    """Store *embedding* in Redis with a 24-hour TTL. Silent on failure."""
    if not settings.REDIS_URL:
        return
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.setex(_embedding_key(query), _EMBEDDING_TTL, json.dumps(embedding))
        await client.aclose()
        logger.debug("embedding_cache_set", extra={"query_len": len(query)})
    except Exception as exc:
        logger.warning("embedding_cache_set_failed", extra={"error": str(exc)})
