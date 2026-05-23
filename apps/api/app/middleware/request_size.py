"""
Request size limit middleware.

Rejects requests whose `Content-Length` header exceeds a configurable
maximum (default 1 MB) with HTTP 413. Streaming clients that omit the
header are allowed through — Starlette enforces an internal cap on the
chunk size as a secondary guard.
"""

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies with HTTP 413."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                size = int(content_length)
            except ValueError:
                size = None
            if size is not None and size > self.max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": (
                            f"Request body too large: {size} bytes "
                            f"(max {self.max_bytes})."
                        ),
                    },
                )
        return await call_next(request)