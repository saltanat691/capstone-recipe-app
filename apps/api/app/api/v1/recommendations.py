"""
Recipe recommendation API endpoints.

Backed by the LangGraph workflow (ingredient agent + RAG retrieval +
nutrition agent).
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.agents.graph import get_agent_graph
from app.observability import get_logger
from app.observability.tracing import get_current_trace_id
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse

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
async def create_recommendations(
    request_data: RecommendationRequest,
    request: Request,
) -> RecommendationResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    trace_id = get_current_trace_id() or ""

    logger.info(
        "Received recommendation request",
        extra={
            "request_id": request_id,
            "message_length": len(request_data.message),
            "ingredients": len(request_data.available_ingredients or []),
            "restrictions": len(request_data.dietary_restrictions or []),
            "days": request_data.days,
        },
    )

    explicit_inputs: dict = {
        "available_ingredients": request_data.available_ingredients,
        "dietary_restrictions": request_data.dietary_restrictions,
        "cuisine_preferences": request_data.cuisine_preferences,
        "servings": request_data.servings,
        "days": request_data.days,
    }

    try:
        graph = get_agent_graph()
        final_state = await graph.invoke(
            raw_user_input=request_data.message,
            explicit_inputs=explicit_inputs,
            request_id=request_id,
            trace_id=trace_id,
        )
    except RuntimeError as e:
        # Surfaced by IngredientAgent / rag_recipe_service when configuration
        # (e.g. OPENAI_API_KEY) or the LLM call itself fails.
        message = str(e)
        logger.error(
            "Workflow runtime error",
            extra={"request_id": request_id, "error": message},
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
            "Workflow unexpected error",
            extra={"request_id": request_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to generate recommendations. Please try again.",
        ) from e

    response: Optional[RecommendationResponse] = final_state.get("final_response")
    if response is None:
        logger.error(
            "Workflow produced no final_response",
            extra={"request_id": request_id},
        )
        raise HTTPException(
            status_code=500,
            detail="Workflow did not produce a response.",
        )

    # menu_plan, grocery_list, and nutrition_notes are populated by their
    # respective agents in the graph; nothing needs to be zeroed here.

    if not response.recommendations and not response.warnings:
        response.warnings = ["No recipes found matching your criteria"]

    if not response.trace_id:
        response.trace_id = trace_id

    logger.info(
        "Recommendation request complete",
        extra={
            "request_id": request_id,
            "recipe_count": len(response.recommendations),
            "warnings": len(response.warnings),
        },
    )
    return response