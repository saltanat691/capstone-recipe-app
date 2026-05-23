"""
Recipe recommendation API endpoints.

Backed by the LangGraph workflow (ingredient agent + RAG retrieval +
nutrition agent).
"""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.agents.graph import get_agent_graph
from app.core.auth import get_api_key
from app.core.config import settings
from app.core.llm_config import tracing_scope
from app.core.rate_limit import limiter
from app.models.api_key import ApiKey
from app.observability import get_logger
from app.observability.metrics import (
    record_filter_rejection,
    record_latency,
    record_recommendations,
    record_request,
)
from app.observability.tracing import get_current_trace_id
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.services.content_filter import ContentPolicyViolation, check as content_check
from app.services.diversity import cuisine_diversity_warning
from app.services.pii_scrubber import scrub, scrub_list

logger = get_logger(__name__)

router = APIRouter(tags=["Recommendations"])


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Generate recipe recommendations",
    description=(
        "Generate personalized recipe recommendations via the LangGraph "
        "workflow (ingredient agent + RAG retrieval + nutrition agent)."
    ),
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_recommendations(
    request: Request,
    request_data: RecommendationRequest,
    api_key: Optional[ApiKey] = Depends(get_api_key),
) -> RecommendationResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    trace_id = get_current_trace_id() or ""
    _t0 = time.monotonic()

    # Scrub PII before it reaches any LLM or tracer.
    safe_message = scrub(request_data.message)
    safe_ingredients = scrub_list(request_data.available_ingredients)

    # Content moderation — reject flagged input before touching any agent.
    try:
        await content_check(safe_message)
    except ContentPolicyViolation as exc:
        record_filter_rejection()
        record_request(status="rejected")
        raise HTTPException(
            status_code=400,
            detail=f"Request contains content that violates usage policy: {', '.join(exc.categories)}.",
        ) from exc

    logger.info(
        "Received recommendation request",
        extra={
            "request_id": request_id,
            "message_length": len(safe_message),
            "ingredients": len(safe_ingredients or []),
            "restrictions": len(request_data.dietary_restrictions or []),
            "days": request_data.days,
        },
    )

    explicit_inputs: dict = {
        "available_ingredients": safe_ingredients,
        "dietary_restrictions": request_data.dietary_restrictions,
        "cuisine_preferences": request_data.cuisine_preferences,
        "servings": request_data.servings,
        "days": request_data.days,
    }

    # Honour per-key tracing consent (default True when no key supplied).
    tracing_allowed = api_key.tracing_consent if api_key else True

    try:
        graph = get_agent_graph()
        async with tracing_scope(tracing_allowed):
            final_state = await graph.invoke(
                raw_user_input=safe_message,
                explicit_inputs=explicit_inputs,
                request_id=request_id,
                trace_id=trace_id,
            )
    except RuntimeError as e:
        # Surfaced by IngredientAgent / rag_recipe_service when configuration
        # (e.g. OPENAI_API_KEY) or the LLM call itself fails.
        message = str(e)
        logger.error(
            "api_event",
            extra={
                "event": "api_error",
                "kind": "workflow_runtime_error",
                "request_id": request_id,
                "trace_id": trace_id,
                "error": message,
            },
            exc_info=True,
        )
        if "OPENAI_API_KEY" in message:
            raise HTTPException(
                status_code=500,
                detail="OPENAI_API_KEY is not configured on the server.",
            ) from e
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation workflow failed: {message}",
        ) from e
    except Exception as e:
        logger.error(
            "api_event",
            extra={
                "event": "api_error",
                "kind": "workflow_unexpected_error",
                "request_id": request_id,
                "trace_id": trace_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate recommendations. Please try again.",
        ) from e

    response: Optional[RecommendationResponse] = final_state.get("final_response")
    if response is None:
        logger.error(
            "api_event",
            extra={
                "event": "api_error",
                "kind": "no_final_response",
                "request_id": request_id,
                "trace_id": trace_id,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Workflow did not produce a response.",
        )

    # menu_plan, grocery_list, and nutrition_notes are populated by their
    # respective agents in the graph; nothing needs to be zeroed here.

    if not response.recommendations and not response.warnings:
        response.warnings = ["No recipes found matching your criteria"]

    # Cuisine diversity check — warn when results are geographically skewed.
    cuisines = [r.cuisine for r in response.recommendations]
    diversity_warn = cuisine_diversity_warning(cuisines)
    if diversity_warn:
        response.warnings = [*response.warnings, diversity_warn]

    if not response.trace_id:
        response.trace_id = trace_id

    record_request(status="success")
    record_recommendations(len(response.recommendations))
    record_latency((time.monotonic() - _t0) * 1000)

    logger.info(
        "Recommendation request complete",
        extra={
            "request_id": request_id,
            "recipe_count": len(response.recommendations),
            "warnings": len(response.warnings),
        },
    )
    return response