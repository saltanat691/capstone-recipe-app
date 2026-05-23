"""
LLM and LangSmith configuration for AI agent tracing.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from app.core.config import settings
from app.observability import get_logger

logger = get_logger(__name__)


def setup_langsmith() -> None:
    """
    Configure LangSmith for LLM observability and tracing.

    This sets up environment variables required by LangChain/LangGraph
    to send traces to LangSmith for debugging and monitoring LLM calls.

    LangSmith will automatically trace:
    - LLM calls (prompts, responses, token usage)
    - Agent executions (tool calls, reasoning steps)
    - Chain invocations
    - Errors and exceptions

    No code changes needed - just configure environment variables.
    """
    if not settings.LANGSMITH_TRACING:
        logger.info("LangSmith tracing is disabled")
        return

    # Check if API key is provided
    if not settings.LANGSMITH_API_KEY:
        logger.warning(
            "LangSmith tracing enabled but LANGSMITH_API_KEY not set. "
            "Traces will not be sent to LangSmith."
        )
        return

    # Set environment variables for LangChain
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT

    logger.info(
        "✓ LangSmith tracing configured",
        extra={
            "project": settings.LANGSMITH_PROJECT,
            "endpoint": settings.LANGSMITH_ENDPOINT,
        },
    )


@asynccontextmanager
async def tracing_scope(enabled: bool) -> AsyncGenerator[None, None]:
    """Temporarily disable LangSmith tracing for a single request when consent is False."""
    if enabled:
        yield
        return
    old = os.environ.get("LANGCHAIN_TRACING_V2")
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("LANGCHAIN_TRACING_V2", None)
        else:
            os.environ["LANGCHAIN_TRACING_V2"] = old


def get_llm_api_key(provider: str = "openai") -> Optional[str]:
    """
    Get LLM API key for the specified provider.

    Args:
        provider: LLM provider ("openai" or "anthropic")

    Returns:
        str: API key if configured, None otherwise

    Raises:
        ValueError: If provider is not supported
    """
    if provider.lower() == "openai":
        key = settings.OPENAI_API_KEY
        if not key:
            logger.warning("OpenAI API key not configured")
        return key or None

    elif provider.lower() == "anthropic":
        key = settings.ANTHROPIC_API_KEY
        if not key:
            logger.warning("Anthropic API key not configured")
        return key or None

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def check_llm_configuration() -> dict[str, bool]:
    """
    Check which LLM providers are configured.

    Returns:
        dict: Dictionary with provider availability status

    Example:
        {
            "openai": True,
            "anthropic": False,
            "langsmith": True
        }
    """
    status = {
        "openai": bool(settings.OPENAI_API_KEY),
        "anthropic": bool(settings.ANTHROPIC_API_KEY),
        "langsmith": settings.LANGSMITH_TRACING and bool(settings.LANGSMITH_API_KEY),
    }

    logger.info(
        "LLM configuration status",
        extra={
            "openai_configured": status["openai"],
            "anthropic_configured": status["anthropic"],
            "langsmith_enabled": status["langsmith"],
        },
    )

    return status


def get_langsmith_url(run_id: Optional[str] = None) -> str:
    """
    Get the LangSmith URL for viewing traces.

    Args:
        run_id: Optional specific run ID to link to

    Returns:
        str: URL to LangSmith project or specific run
    """
    base_url = "https://smith.langchain.com"
    project = settings.LANGSMITH_PROJECT

    if run_id:
        return f"{base_url}/o/recipe-ai/projects/p/{project}/r/{run_id}"
    else:
        return f"{base_url}/o/recipe-ai/projects/p/{project}"


# LLM Configuration Documentation
LLM_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
        "embedding_models": ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"],
        "required_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "name": "Anthropic",
        "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "embedding_models": [],  # Anthropic doesn't provide embeddings
        "required_key": "ANTHROPIC_API_KEY",
    },
}