"""
Application configuration using Pydantic settings.
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo layout when running from source:
#   <repo-root>/.env                  <- primary, monorepo-wide
#   <repo-root>/apps/api/.env         <- optional local override (legacy)
# Both paths are resolved from this file so the API picks up the same
# values regardless of cwd. Inside the Docker image the layout is flatter
# (/app/app/core/config.py) and these parents do not exist — in that case
# we silently skip the .env files and rely on environment variables
# injected by docker-compose / the container runtime.
_THIS_FILE = Path(__file__).resolve()


def _safe_parent_env(parents_index: int) -> Optional[Path]:
    try:
        candidate = _THIS_FILE.parents[parents_index] / ".env"
    except IndexError:
        return None
    return candidate


_ROOT_ENV = _safe_parent_env(4)
_LOCAL_ENV = _safe_parent_env(2)
_ENV_FILES = tuple(p for p in (_ROOT_ENV, _LOCAL_ENV) if p is not None)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    # Application
    APP_NAME: str = "Recipe AI System API"
    APP_VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True

    # Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 4000
    API_RELOAD: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:4000"]

    # Database
    DATABASE_URL: str

    # OpenTelemetry
    # Default endpoint is the OTLP HTTP receiver on Tempo (port 4318).
    # If you change this, point it at the *HTTP* receiver, not the gRPC one.
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"
    OTEL_SERVICE_NAME: str = "recipe-api"
    OTEL_TRACES_EXPORTER: str = "otlp"
    OTEL_METRICS_EXPORTER: str = "otlp"
    OTEL_LOGS_EXPORTER: str = "otlp"

    # LLM / AI Configuration
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4.1-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # LangSmith (LLM Observability)
    LANGSMITH_TRACING: bool = True
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "recipe-ai-system-dev"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    # USDA FoodData Central (optional — improves nutrition accuracy)
    USDA_API_KEY: str = ""
    USDA_API_BASE_URL: str = "https://api.nal.usda.gov/fdc/v1"

    # Redis — optional embedding cache (leave blank to disable)
    REDIS_URL: str = ""

    # Auth
    REQUIRE_AUTH: bool = False

    # Data retention (days until agent_runs / user_preferences are purged)
    DATA_RETENTION_DAYS: int = 90

    # Production safety
    LLM_TIMEOUT_SECONDS: float = 30.0
    MAX_REQUEST_BYTES: int = 1_048_576  # 1 MB
    RATE_LIMIT_PER_MINUTE: int = 10

    model_config = SettingsConfigDict(
        # None entries are filtered out; later entries win. Inside Docker
        # both come back empty and Settings reads from os.environ only.
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()