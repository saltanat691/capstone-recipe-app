# Observability

## Overview

The Recipe AI System implements comprehensive observability using the OpenTelemetry standard with Grafana, Tempo, and Loki for visualization and storage, plus LangSmith for LLM-specific observability.

## Observability Stack

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Applications                          │
│  ┌────────────┐              ┌────────────┐            │
│  │  Next.js   │              │  FastAPI   │            │
│  │  (web)     │              │   (api)    │            │
│  └──────┬─────┘              └──────┬─────┘            │
│         │                           │                   │
│         └─────────────┬─────────────┘                   │
│                       │                                  │
│              OpenTelemetry SDK                           │
│                       │                                  │
└───────────────────────┼──────────────────────────────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
    ┌──────▼───┐  ┌────▼────┐  ┌───▼────┐
    │  Tempo   │  │  Loki   │  │ Grafana│
    │ (Traces) │  │  (Logs) │  │(Dashboards)
    └──────────┘  └─────────┘  └────────┘

    ┌──────────────┐
    │  LangSmith   │  (LLM Tracing)
    └──────────────┘
```

## Components

### OpenTelemetry

OpenTelemetry provides vendor-neutral instrumentation for traces, metrics, and logs.

**Configuration** (Backend - FastAPI):

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter — Tempo's OTLP HTTP receiver runs on port 4318.
# (Port 4317 is the gRPC receiver; we use the HTTP exporter here.)
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4318/v1/traces",
)

# Add span processor
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

**Configuration** (Frontend - Next.js):

```typescript
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-base';

const provider = new WebTracerProvider();
const exporter = new OTLPTraceExporter({
  url: 'http://localhost:4318/v1/traces',
});

provider.addSpanProcessor(new BatchSpanProcessor(exporter));
provider.register();
```

### Tempo (Distributed Tracing)

Tempo stores and queries distributed traces.

**Location**: `infra/tempo/`

**Features**:
- High-scale trace storage
- Native Grafana integration
- Efficient query performance
- No index required

**Key Concepts**:
- **Trace**: End-to-end journey of a request
- **Span**: Single operation within a trace
- **Trace ID**: Unique identifier propagated across services

### Loki (Log Aggregation)

Loki aggregates logs from all services.

**Location**: `infra/loki/`

**Features**:
- Label-based log organization
- Efficient storage (no full-text indexing)
- LogQL query language
- Grafana integration

**Log Levels**:
- ERROR: Critical errors requiring attention
- WARN: Warning messages
- INFO: Informational messages
- DEBUG: Detailed debugging information

### Grafana (Visualization)

Grafana provides dashboards and visualization for all observability data.

**Location**: `infra/grafana/`

**Access**: http://localhost:3001 (credentials: admin / admin)

**Dashboard Categories**:
1. **System Overview**: High-level system health
2. **API Performance**: Request rates, latencies, errors
3. **Database**: Query performance, connection pool stats
4. **AI Agents**: LangGraph execution metrics
5. **Traces**: Distributed trace visualization

### LangSmith (LLM Observability)

LangSmith provides specialized observability for LLM and agent operations.

**Features**:
- Trace LLM calls with full context
- View prompts and completions
- Track token usage and costs
- Debug agent decision making
- Compare prompt variations

**Access**: https://smith.langchain.com

**Configuration**:

```python
import os

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "recipe-ai-system"
os.environ["LANGCHAIN_API_KEY"] = "your_api_key"
```

## Instrumentation Best Practices

### Adding Custom Spans

**Python (Backend)**:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_recipe")
def process_recipe(recipe_id: str):
    span = trace.get_current_span()
    span.set_attribute("recipe.id", recipe_id)

    # Your logic here

    span.add_event("recipe_processed")
    return result
```

**TypeScript (Frontend)**:

```typescript
import { trace } from '@opentelemetry/api';

const tracer = trace.getTracer('recipe-web');

async function fetchRecipes() {
  return tracer.startActiveSpan('fetch-recipes', async (span) => {
    span.setAttribute('user.id', userId);

    try {
      const response = await fetch('/api/recipes');
      span.addEvent('recipes-fetched');
      return response.json();
    } finally {
      span.end();
    }
  });
}
```

### Structured Logging

The backend uses `python-json-logger` with trace context correlation. Every log line is JSON and includes `trace_id` and `span_id` automatically.

**Python**:

```python
from app.observability import get_logger

logger = get_logger(__name__)

logger.info(
    "recipe_retrieved",
    extra={
        "recipe_id": recipe_id,
        "duration_ms": duration,
        "score": score,
    }
)
```

Log lines look like:
```json
{"timestamp": "2026-05-24T10:00:00Z", "level": "INFO", "message": "recipe_retrieved",
 "recipe_id": 42, "duration_ms": 120, "trace_id": "abc123", "span_id": "def456"}
```

### Metrics Instruments

All instruments live in `app/observability/metrics.py` and are exported every 30 seconds over OTLP HTTP.

| Instrument | Type | Description |
|---|---|---|
| `recipe_requests_total` | Counter | Total recommendation requests (`status` attribute) |
| `recipe_recommendations_returned` | Histogram | Recipe count per request |
| `recipe_request_latency_ms` | Histogram | End-to-end latency in ms |
| `embedding_cache_hits_total` | Counter | Redis embedding cache hits |
| `embedding_cache_misses_total` | Counter | Redis embedding cache misses |
| `content_filter_rejections_total` | Counter | Requests rejected by content moderation |
| `cuisine_diversity_warnings_total` | Counter | Cuisine-skew warnings (`cuisine` attribute) |
| `process_memory_rss_mb` | Observable Gauge | Process RSS memory (MB) via psutil |
| `process_cpu_percent` | Observable Gauge | Process CPU usage (%) via psutil |

Use the helper functions — never call instruments directly:

```python
from app.observability.metrics import (
    record_request, record_recommendations, record_latency,
    record_cache_hit, record_cache_miss,
    record_filter_rejection, record_diversity_warning,
)

record_request(status="success")
record_recommendations(count=5)
record_latency(ms=342.1)
record_diversity_warning(dominant_cuisine="Italian")
```

The process gauges (`process_memory_rss_mb`, `process_cpu_percent`) are polled automatically — no manual recording needed.
## Common Queries

### LogQL (Loki)

```logql
# All logs from API service
{service="recipe-api"}

# Error logs only
{service="recipe-api"} |= "ERROR"

# Logs for specific user
{service="recipe-api"} | json | user_id="123"

# Rate of errors over time
rate({service="recipe-api"} |= "ERROR" [5m])
```

### TraceQL (Tempo)

```traceql
# Traces with errors
status=error

# Slow traces (>1s)
duration > 1s

# Traces for specific endpoint
resource.service.name="recipe-api" && name="/recipes"

# Traces with specific attribute
span.recipe.id="abc123"
```

## Dashboard Setup

### Key Metrics to Monitor

**API Metrics**:
- Request rate (requests/sec)
- Error rate (%)
- Response time (p50, p95, p99)
- Active connections

**Database Metrics**:
- Query duration
- Connection pool usage
- Cache hit rate
- Slow query count

**AI/LLM Metrics**:
- Agent execution time
- Token usage
- LLM API latency
- Cost per request

**System Metrics**:
- CPU usage
- Memory usage
- Disk I/O
- Network traffic

### Creating Custom Dashboards

1. Access Grafana at http://localhost:3001
2. Click "+" → "Dashboard"
3. Add panels with desired visualizations
4. Save dashboard with descriptive name

**Panel Types**:
- Time series: For metrics over time
- Table: For structured data
- Logs: For log exploration
- Trace: For trace visualization

## Alerting

### Alert Rules

Configure alerts in Grafana for:

- High error rate (>5% for 5 minutes)
- Slow response times (p95 > 1s)
- High memory usage (>80%)
- Database connection pool exhausted
- LLM API failures

### Alert Channels

Configure notification channels:
- Email
- Slack
- PagerDuty
- Webhook

## Troubleshooting

### No Traces Appearing

1. Check OpenTelemetry configuration
2. Verify Tempo is running: `docker ps | grep tempo`
3. Check collector endpoint is correct
4. Verify network connectivity

### Missing Logs

1. Check Loki is running and accessible
2. Verify log labels are correctly configured
3. Check application logging configuration
4. Review Loki retention settings

### Dashboard Not Loading

1. Verify Grafana is running
2. Check data source configuration
3. Review browser console for errors
4. Verify query syntax

## Performance Considerations

### Sampling

For high-traffic applications, implement trace sampling:

```python
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# Sample 10% of traces
sampler = TraceIdRatioBased(0.1)
```

### Batch Processing

Use batch processors to reduce overhead:

```python
BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    schedule_delay_millis=5000
)
```

### Resource Limits

Set appropriate resource limits for observability services in Docker/Kubernetes.

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)