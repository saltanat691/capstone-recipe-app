"""
Structured logging configuration with JSON output and trace correlation.
"""

import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.config import settings
from app.observability.tracing import get_current_trace_id, get_current_span_id


class TraceContextFilter(logging.Filter):
    """
    Filter that adds OpenTelemetry trace context to log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add trace_id and span_id to the log record.

        Args:
            record: Log record to filter

        Returns:
            bool: Always True (don't filter out any records)
        """
        record.trace_id = get_current_trace_id()
        record.span_id = get_current_span_id()
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that includes trace context and standard fields.
    """

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """
        Add custom fields to the log record.

        Args:
            log_record: Dictionary to be logged as JSON
            record: Original log record
            message_dict: Additional message data
        """
        super().add_fields(log_record, record, message_dict)

        # Add standard fields
        log_record["timestamp"] = self.formatTime(record, self.datefmt)
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["service"] = settings.OTEL_SERVICE_NAME
        log_record["environment"] = settings.ENVIRONMENT

        # Add trace context if available
        if hasattr(record, "trace_id") and record.trace_id:
            log_record["trace_id"] = record.trace_id
        if hasattr(record, "span_id") and record.span_id:
            log_record["span_id"] = record.span_id

        # Add request ID if available (from middleware)
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)


def setup_logging() -> None:
    """
    Configure structured JSON logging with trace correlation.

    Sets up:
    - JSON formatter for structured logs
    - Trace context filter for OpenTelemetry correlation
    - Console handler for stdout
    - Log level based on environment
    """
    # Determine log level
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Create JSON formatter
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Add trace context filter
    trace_filter = TraceContextFilter()
    handler.addFilter(trace_filter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    print(f"✓ Structured logging initialized (level: {logging.getLevelName(log_level)})")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        logging.Logger: Configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info("Processing request", extra={"user_id": 123})
    """
    return logging.getLogger(name)