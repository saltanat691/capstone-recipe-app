"""
Application configuration using Pydantic settings.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo layout:
#   <repo-root>/.env                  <- primary, monorepo-wide
#   <repo-root>/apps/api/.env         <- optional local override (legacy)
# Both paths are resolved from this file so the API picks up the same
# values regardless of cwd.
_THIS_FILE = Path(__file__).resolve()
_ROOT_ENV = _THIS_FILE.parents[4] / ".env"
_LOCAL_ENV = _THIS_FILE.parents[2] / ".env"


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
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
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

    model_config = SettingsConfigDict(
        env_file=(_ROOT_ENV, _LOCAL_ENV),  # later wins; local overrides root
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()