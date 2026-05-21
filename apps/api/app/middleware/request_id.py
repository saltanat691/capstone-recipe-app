"""
Request ID middleware for tracking requests across logs and traces.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.observability.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds a unique request ID to each request.

    The request ID is:
    - Generated if not provided in X-Request-ID header
    - Added to response headers
    - Attached to log records via contextvars
    - Used for correlating logs and traces
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and add request ID.

        Args:
            request: Incoming request
            call_next: Next middleware or route handler

        Returns:
            Response: Response with request ID header
        """
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Store request ID in request state
        request.state.request_id = request_id

        # Add request ID to log context
        log_extra = {"request_id": request_id}

        # Log request start
        start_time = time.time()
        logger.info(
            "Request started",
            extra={
                **log_extra,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log request completion
            logger.info(
                "Request completed",
                extra={
                    **log_extra,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                "Request failed",
                extra={
                    **log_extra,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration * 1000, 2),
                },
                exc_info=True,
            )

            raise


def get_request_id() -> str:
    """
    Get the current request ID from the request state.

    This is a utility function that can be used in route handlers
    to access the request ID.

    Returns:
        str: Request ID or empty string if not available
    """

    # This would need to be implemented with contextvars for proper access
    # For now, return empty string as a placeholder
    return ""