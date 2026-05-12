# Observability Guide

This guide explains how to use the observability features in the Recipe AI System backend, including OpenTelemetry tracing, structured logging, and trace correlation.

## Overview

The backend is instrumented with:
- **OpenTelemetry** for distributed tracing
- **Structured JSON logging** with trace correlation
- **Request ID tracking** for request correlation
- **Automatic instrumentation** for FastAPI, SQLAlchemy, and asyncpg

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
│                                                          │
│  ┌────────────────┐  ┌──────────────────────────────┐ │
│  │ Request ID     │  │ OpenTelemetry                │ │
│  │ Middleware     │  │ FastAPI Instrumentation      │ │
│  └────────────────┘  └──────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Structured JSON Logging with Trace Correlation     │ │
│  └────────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────────┘
                        │
           ┌────────────┴────────────┐
           │                         │
    ┌──────▼────────┐         ┌─────▼──────┐
    │     Tempo     │         │    Loki    │
    │   (Traces)    │         │   (Logs)   │
    └───────────────┘         └────────────┘
           │                         │
           └─────────┬───────────────┘
                     │
              ┌──────▼──────┐
              │   Grafana   │
              │ (Dashboards)│
              └─────────────┘
```

## Quick Start

### 1. Start Observability Stack

First, ensure the infrastructure is running:

```bash
cd infra/docker
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see:
- `recipe-grafana` on port 3001
- `recipe-tempo` on port 3200 (and 4318 for OTLP HTTP)
- `recipe-loki` on port 3100

### 2. Start the API

```bash
cd apps/api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

You should see observability initialization messages:
```
✓ Structured logging initialized (level: DEBUG)
✓ OpenTelemetry tracing initialized
  Service: recipe-api
  Endpoint: http://localhost:4318/v1/traces
✓ Database instrumented with OpenTelemetry
============================================================
Starting Recipe AI System API v0.1.0
Environment: development
Debug mode: True
API available at: http://0.0.0.0:4000
API docs at: http://localhost:4000/docs
============================================================
✓ FastAPI instrumented with OpenTelemetry
```

### 3. Generate a Trace

Make a request to generate traces and logs:

```bash
# Simple health check
curl http://localhost:4000/health

# Or visit in browser
open http://localhost:4000/health
```

### 4. View Traces in Grafana

1. Open Grafana: http://localhost:3001
2. Login: `admin` / `admin`
3. Go to **Explore** (compass icon)
4. Select **Tempo** data source
5. Click **Search** tab
6. Set filters:
   - Service Name: `recipe-api`
7. Click **Run Query**

You should see traces from your API requests!

### 5. View Logs in Grafana

1. In Grafana Explore
2. Select **Loki** data source
3. Use LogQL query:
   ```logql
   {service="recipe-api"}
   ```
4. Click **Run Query**

You should see structured JSON logs from your API!

### 6. Correlate Traces and Logs

Logs include `trace_id` and `span_id` fields that match OpenTelemetry traces:

1. Find a trace in Tempo
2. Copy the trace ID
3. In Loki, query:
   ```logql
   {service="recipe-api"} | json | trace_id="<paste-trace-id>"
   ```

You'll see all logs for that specific trace!

## Features

### 1. Distributed Tracing

All requests are automatically traced with OpenTelemetry:

- **HTTP requests**: Method, path, status code, duration
- **Database queries**: SQL statements, connection info
- **Custom spans**: Add your own spans for specific operations

#### Viewing Traces

Traces show:
- Request flow through the application
- Database query performance
- Error stack traces
- Timing for each operation

#### Custom Spans

Add custom spans to your code:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@router.get("/recipes/{recipe_id}")
async def get_recipe(recipe_id: int):
    with tracer.start_as_current_span("fetch_recipe") as span:
        span.set_attribute("recipe.id", recipe_id)

        # Your code here
        recipe = await fetch_recipe(recipe_id)

        span.set_attribute("recipe.name", recipe.name)
        return recipe
```

### 2. Structured JSON Logging

All logs are output as JSON with consistent fields:

```json
{
  "timestamp": "2024-05-09T16:30:00",
  "level": "INFO",
  "logger": "app.api.v1.router",
  "message": "Request completed",
  "service": "recipe-api",
  "environment": "development",
  "trace_id": "d4a8c8f2e3b1a9d7c6e5f4a3b2c1d0e9",
  "span_id": "a1b2c3d4e5f6a7b8",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/api/v1/recipes",
  "status_code": 200,
  "duration_ms": 45.23
}
```

#### Log Fields

- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logger`: Logger name (module path)
- `message`: Log message
- `service`: Service name (recipe-api)
- `environment`: Environment (development, staging, production)
- `trace_id`: OpenTelemetry trace ID (for correlation)
- `span_id`: OpenTelemetry span ID
- `request_id`: Unique request identifier
- Custom fields: Any additional data passed via `extra`

#### Using Structured Logging

```python
from app.observability import get_logger

logger = get_logger(__name__)

# Simple log
logger.info("Processing recipe")

# Log with extra fields
logger.info(
    "Recipe created",
    extra={
        "recipe_id": recipe.id,
        "user_id": user_id,
        "cuisine": recipe.cuisine,
    }
)

# Error with exception
try:
    result = await process_recipe()
except Exception as e:
    logger.error(
        "Failed to process recipe",
        extra={"recipe_id": recipe_id},
        exc_info=True
    )
```

### 3. Request ID Tracking

Every request gets a unique request ID:

- Generated automatically or from `X-Request-ID` header
- Returned in response `X-Request-ID` header
- Included in all logs for that request
- Useful for debugging and support

#### Using Request IDs

```bash
# Send custom request ID
curl -H "X-Request-ID: my-custom-id-123" http://localhost:4000/health

# Response includes the same ID
# X-Request-ID: my-custom-id-123
```

All logs for this request will include `"request_id": "my-custom-id-123"`.

### 4. Automatic Instrumentation

The following are automatically instrumented:

#### FastAPI
- All routes
- Request/response headers
- Status codes
- Exceptions

#### SQLAlchemy
- Database connections
- Query execution
- Transaction management

#### asyncpg
- PostgreSQL operations
- Connection pooling

## Configuration

### Environment Variables

Configure observability via `.env`:

```env
# Service identification
OTEL_SERVICE_NAME=recipe-api
ENVIRONMENT=development

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_TRACES_EXPORTER=otlp
OTEL_METRICS_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp

# Logging
DEBUG=true
```

### Log Levels

Log level is determined by `DEBUG`:
- `DEBUG=true`: Log level is DEBUG (verbose)
- `DEBUG=false`: Log level is INFO (production)

## Querying Traces and Logs

### Tempo (TraceQL)

Find traces by various criteria:

```traceql
# All traces from recipe-api
{service.name="recipe-api"}

# Slow requests (>1 second)
{service.name="recipe-api"} && duration > 1s

# Failed requests
{service.name="recipe-api" && status=error}

# Specific endpoint
{service.name="recipe-api" && name="/api/v1/recipes"}

# Database operations
{service.name="recipe-api" && span.kind="database"}
```

### Loki (LogQL)

Query logs with LogQL:

```logql
# All logs from recipe-api
{service="recipe-api"}

# Error logs only
{service="recipe-api"} | json | level="ERROR"

# Logs for specific request
{service="recipe-api"} | json | request_id="550e8400-e29b-41d4-a716-446655440000"

# Logs with trace correlation
{service="recipe-api"} | json | trace_id=~".+"

# Rate of errors
rate({service="recipe-api"} | json | level="ERROR" [5m])

# Search by message
{service="recipe-api"} |= "Recipe created"

# Filter by custom field
{service="recipe-api"} | json | recipe_id="123"
```

## Grafana Dashboards

### Create a Dashboard

1. Open Grafana: http://localhost:3001
2. Click **+** → **Dashboard**
3. Click **Add visualization**
4. Select data source (Tempo or Loki)
5. Configure query
6. Save dashboard

### Useful Panels

#### Request Rate
```logql
rate({service="recipe-api"} [1m])
```

#### Error Rate
```logql
rate({service="recipe-api"} | json | level="ERROR" [5m])
```

#### Response Time (p95)
```logql
quantile_over_time(0.95, {service="recipe-api"} | json | unwrap duration_ms [5m])
```

#### Active Requests
Use Tempo service graph feature.

## Troubleshooting

### No Traces Appearing

1. **Check Tempo is running:**
   ```bash
   curl http://localhost:3200/ready
   ```

2. **Check OTLP endpoint:**
   ```bash
   curl http://localhost:4318/v1/traces
   ```

3. **Verify API configuration:**
   Check startup messages show correct endpoint.

4. **Check Grafana data source:**
   - Go to Configuration → Data Sources
   - Verify Tempo is configured
   - Test connection

### No Logs Appearing

1. **Check Loki is running:**
   ```bash
   curl http://localhost:3100/ready
   ```

2. **Verify logs are being generated:**
   Check API console output (should see JSON logs)

3. **Check Grafana data source:**
   - Verify Loki is configured
   - Test connection

### Traces Not Correlated with Logs

1. **Verify trace_id in logs:**
   ```bash
   curl http://localhost:4000/health
   # Check console output for trace_id field
   ```

2. **Check OpenTelemetry is working:**
   Startup should show "✓ OpenTelemetry tracing initialized"

### High Overhead

If observability is causing performance issues:

1. **Reduce log level:**
   Set `DEBUG=false` in `.env`

2. **Sample traces:**
   Modify `app/observability/tracing.py` to add sampling

3. **Adjust batch size:**
   Tune `BatchSpanProcessor` settings

## Best Practices

### 1. Use Structured Logging

Always use structured fields instead of string formatting:

**Good:**
```python
logger.info("Recipe created", extra={"recipe_id": 123, "name": "Pasta"})
```

**Bad:**
```python
logger.info(f"Recipe created: {recipe_id} - {name}")
```

### 2. Add Context to Spans

```python
with tracer.start_as_current_span("complex_operation") as span:
    span.set_attribute("user_id", user_id)
    span.set_attribute("operation_type", "create")
    span.add_event("validation_started")
    # ... operation ...
    span.add_event("validation_completed")
```

### 3. Log at Appropriate Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages for unexpected situations
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical issues requiring immediate attention

### 4. Include Request Context

When logging, include the request ID:
```python
logger.info("Processing request", extra={"request_id": request.state.request_id})
```

### 5. Don't Log Sensitive Data

Never log:
- Passwords
- API keys
- Personal information (PII)
- Credit card numbers
- Session tokens

## Performance Impact

Observability has minimal performance impact:

- **Tracing**: ~1-2% overhead
- **Logging**: ~2-3% overhead
- **Total**: ~3-5% overhead

This is acceptable for the debugging and monitoring benefits.

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Tempo Documentation](https://grafana.com/docs/tempo/)
- [Grafana Loki Documentation](https://grafana.com/docs/loki/)
- [LogQL Reference](https://grafana.com/docs/loki/latest/logql/)
- [TraceQL Reference](https://grafana.com/docs/tempo/latest/traceql/)