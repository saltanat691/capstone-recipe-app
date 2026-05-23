"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter
from app.api.health import router as health_router
from app.api.v1.router import router as api_v1_router

# Observability imports
from app.observability.logging import setup_logging
from app.observability.tracing import (
    setup_tracing,
    instrument_fastapi,
    instrument_database,
)
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.request_size import RequestSizeLimitMiddleware

# LLM configuration
from app.core.llm_config import setup_langsmith, check_llm_configuration

# Initialize observability and LLM tracing early
setup_logging()
setup_tracing()
instrument_database()
setup_langsmith()
check_llm_configuration()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    print("=" * 60)
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Debug mode: {settings.DEBUG}")
    print(f"API available at: http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"API docs at: http://localhost:{settings.API_PORT}/docs")
    print("=" * 60)

    yield

    # Shutdown
    print(f"\nShutting down {settings.APP_NAME}")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-powered recipe management and recommendation system",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Wire the rate limiter and its exception handler.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)

    # Reject oversized request bodies before they hit the handler.
    app.add_middleware(
        RequestSizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BYTES
    )

    # Add Request ID middleware (before other middleware)
    app.add_middleware(RequestIDMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Instrument FastAPI with OpenTelemetry
    instrument_fastapi(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    return app


# Create application instance
app = create_application()


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns:
        dict: Welcome message and links
    """
    return {
        "message": "Welcome to Recipe AI System API",
        "docs": "/docs",
        "health": "/health",
        "api_v1": settings.API_V1_PREFIX,
    }