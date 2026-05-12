"""
Application configuration using Pydantic settings.
"""

from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # LangSmith (LLM Observability)
    LANGSMITH_TRACING: bool = True
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "recipe-ai-system-dev"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()