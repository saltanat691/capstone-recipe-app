"""
Health and readiness endpoints.

- /health   — liveness: the process is running and serving HTTP.
- /readiness — readiness: dependencies (currently Postgres) are reachable.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.observability import get_logger

logger = get_logger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Liveness response."""

    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    """Readiness response (HTTP 200 = all dependencies reachable)."""

    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Liveness probe — returns 200 as long as the process is serving."""
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
    )


@router.get("/readiness", response_model=ReadinessResponse, tags=["Health"])
async def readiness_check() -> ReadinessResponse:
    """
    Readiness probe — returns 200 only when dependencies pass their checks.
    Currently checks Postgres connectivity via `SELECT 1`. Returns 503 with a
    `checks` map describing which dependency failed.
    """
    checks: dict[str, str] = {}
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Readiness DB check failed", extra={"error": str(e)})
        checks["database"] = f"error: {e}"
        raise HTTPException(status_code=503, detail={"status": "not_ready", "checks": checks})

    return ReadinessResponse(status="ready", checks=checks)