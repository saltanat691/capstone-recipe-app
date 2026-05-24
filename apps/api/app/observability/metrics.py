"""
OpenTelemetry metrics — counters and histograms for Grafana dashboards.

Exported over OTLP HTTP to the same collector that receives traces.
All instruments are module-level singletons; call setup_metrics() once
at startup before using record_* helpers.
"""

import psutil
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

from app.core.config import settings
from app.observability import get_logger

logger = get_logger(__name__)

_process = psutil.Process()  # cache once; safe to reuse across threads


def _observe_memory_rss(options: CallbackOptions):
    yield Observation(_process.memory_info().rss / 1024 / 1024)


def _observe_cpu_percent(options: CallbackOptions):
    # interval=None returns a non-blocking reading relative to the last call
    yield Observation(_process.cpu_percent(interval=None))


_meter = None  # set by setup_metrics()

# ---- Instruments -----------------------------------------------------------
_req_counter = None          # total recommendation requests
_rec_histogram = None        # recommendations returned per request
_latency_histogram = None    # end-to-end latency in ms
_cache_hit_counter = None    # embedding cache hits
_cache_miss_counter = None   # embedding cache misses
_filter_reject_counter = None  # content-filter rejections
_diversity_warn_counter = None  # cuisine-skew warnings emitted


def setup_metrics() -> None:
    """Initialize MeterProvider and create all instruments. Call once at startup."""
    global _meter, _req_counter, _rec_histogram, _latency_histogram
    global _cache_hit_counter, _cache_miss_counter
    global _filter_reject_counter, _diversity_warn_counter

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.ENVIRONMENT,
        }
    )

    exporter = OTLPMetricExporter(
        endpoint=f"{settings.OTEL_EXPORTER_OTLP_ENDPOINT.rstrip('/')}/v1/metrics",
    )
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=30_000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    _meter = metrics.get_meter("recipe-api", settings.APP_VERSION)

    _req_counter = _meter.create_counter(
        "recipe_requests_total",
        description="Total recommendation requests received",
    )
    _rec_histogram = _meter.create_histogram(
        "recipe_recommendations_returned",
        description="Number of recipes returned per request",
        unit="recipes",
    )
    _latency_histogram = _meter.create_histogram(
        "recipe_request_latency_ms",
        description="End-to-end recommendation request latency",
        unit="ms",
    )
    _cache_hit_counter = _meter.create_counter(
        "embedding_cache_hits_total",
        description="Embedding vector cache hits",
    )
    _cache_miss_counter = _meter.create_counter(
        "embedding_cache_misses_total",
        description="Embedding vector cache misses",
    )
    _filter_reject_counter = _meter.create_counter(
        "content_filter_rejections_total",
        description="Requests rejected by the content moderation filter",
    )
    _diversity_warn_counter = _meter.create_counter(
        "cuisine_diversity_warnings_total",
        description="Requests where cuisine skew warning was added",
    )

    _meter.create_observable_gauge(
        "process_memory_rss_mb",
        callbacks=[_observe_memory_rss],
        description="Process RSS memory usage",
        unit="MB",
    )
    _meter.create_observable_gauge(
        "process_cpu_percent",
        callbacks=[_observe_cpu_percent],
        description="Process CPU usage",
        unit="%",
    )

    logger.info(
        "otel_metrics_initialized",
        extra={"endpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT},
    )


# ---- Public record helpers -------------------------------------------------

def record_request(status: str = "success") -> None:
    if _req_counter:
        _req_counter.add(1, {"status": status})


def record_recommendations(count: int) -> None:
    if _rec_histogram:
        _rec_histogram.record(count)


def record_latency(ms: float) -> None:
    if _latency_histogram:
        _latency_histogram.record(ms)


def record_cache_hit() -> None:
    if _cache_hit_counter:
        _cache_hit_counter.add(1)


def record_cache_miss() -> None:
    if _cache_miss_counter:
        _cache_miss_counter.add(1)


def record_filter_rejection() -> None:
    if _filter_reject_counter:
        _filter_reject_counter.add(1)


def record_diversity_warning(dominant_cuisine: str) -> None:
    if _diversity_warn_counter:
        _diversity_warn_counter.add(1, {"cuisine": dominant_cuisine})
