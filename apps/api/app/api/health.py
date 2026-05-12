"""
Health check endpoint.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify the API is running.

    Returns:
        HealthResponse: Service health status
    """
    return HealthResponse(
        status="healthy",
        service="Recipe AI System API",
        version="0.1.0",
    )