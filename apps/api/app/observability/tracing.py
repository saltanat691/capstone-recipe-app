"""
OpenTelemetry tracing configuration for FastAPI.
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import settings


def setup_tracing() -> None:
    """
    Initialize OpenTelemetry tracing with OTLP exporter.

    This sets up:
    - TracerProvider with service name and version
    - OTLP HTTP exporter to send traces to Tempo
    - Batch span processor for efficient trace export
    """
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Create OTLP exporter (HTTP to Tempo on port 4318)
    otlp_exporter = OTLPSpanExporter(
        endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.replace(':4317', ':4318')}/v1/traces",
    )

    # Add batch span processor
    processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(processor)

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    print("✓ OpenTelemetry tracing initialized")
    print(f"  Service: {settings.OTEL_SERVICE_NAME}")
    print(f"  Endpoint: {settings.OTEL_EXPORTER_OTLP_ENDPOINT.replace(':4317', ':4318')}/v1/traces")


def instrument_fastapi(app) -> None:
    """
    Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
    """
    FastAPIInstrumentor.instrument_app(app)
    print("✓ FastAPI instrumented with OpenTelemetry")


def instrument_database() -> None:
    """
    Instrument database connections with OpenTelemetry.

    Instruments:
    - SQLAlchemy (ORM operations)
    - asyncpg (PostgreSQL driver)
    """
    SQLAlchemyInstrumentor().instrument()
    AsyncPGInstrumentor().instrument()
    print("✓ Database instrumented with OpenTelemetry")


def get_current_trace_id() -> str:
    """
    Get the current trace ID if available.

    Returns:
        str: Trace ID in hex format, or empty string if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return ""


def get_current_span_id() -> str:
    """
    Get the current span ID if available.

    Returns:
        str: Span ID in hex format, or empty string if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return ""