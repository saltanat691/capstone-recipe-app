"""
User feedback endpoint.

POST /feedback  — submit a 1-5 star rating for a recommendation response,
                  identified by the trace_id returned in that response.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_api_key
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.feedback import Feedback
from app.observability import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Feedback"])


class FeedbackRequest(BaseModel):
    trace_id: str = Field(
        ...,
        description="trace_id from the RecommendationResponse you are rating.",
    )
    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Quality rating: 1 (poor) to 5 (excellent).",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional free-text feedback.",
    )


class FeedbackResponse(BaseModel):
    id: int
    trace_id: str
    rating: int
    message: str


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=201,
    summary="Submit recommendation feedback",
    description=(
        "Rate a previous recommendation response (1–5 stars). "
        "Use the `trace_id` field from the recommendation response to link "
        "your rating to the exact request."
    ),
)
async def submit_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    api_key: Optional[ApiKey] = Depends(get_api_key),
) -> FeedbackResponse:
    if not body.trace_id.strip():
        raise HTTPException(status_code=422, detail="trace_id must not be blank.")

    record = Feedback(
        trace_id=body.trace_id.strip(),
        rating=body.rating,
        comment=body.comment,
        owner_id=api_key.owner_id if api_key else None,
    )
    db.add(record)
    await db.flush()

    logger.info(
        "feedback_received",
        extra={
            "trace_id": record.trace_id,
            "rating": record.rating,
            "owner_id": record.owner_id,
        },
    )
    return FeedbackResponse(
        id=record.id,
        trace_id=record.trace_id,
        rating=record.rating,
        message="Thank you for your feedback!",
    )
