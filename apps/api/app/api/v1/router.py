"""
API v1 router - main router for v1 endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.v1.auth import router as auth_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.recommendations import router as recommendations_router

router = APIRouter()

# Include sub-routers
router.include_router(auth_router)
router.include_router(feedback_router)
router.include_router(recommendations_router)


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


@router.get("/", response_model=MessageResponse, tags=["General"])
async def api_root() -> MessageResponse:
    """
    API v1 root endpoint.

    Returns:
        MessageResponse: Welcome message
    """
    return MessageResponse(message="Welcome to Recipe AI System API v1")


@router.get("/status", response_model=MessageResponse, tags=["General"])
async def api_status() -> MessageResponse:
    """
    API status endpoint.

    Returns:
        MessageResponse: API status message
    """
    return MessageResponse(message="API v1 is operational")