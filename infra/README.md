# Infrastructure

This directory contains the infrastructure configuration for the Recipe AI System, including Docker Compose setup and observability stack configurations.

## Directory Structure

```
infra/
├── docker/
│   ├── docker-compose.yml      # Main Docker Compose configuration
│   └── README.md               # Detailed Docker setup guide
├── grafana/
│   └── provisioning/
│       └── datasources/
│           └── datasources.yml # Auto-configured data sources
├── tempo/
│   └── tempo.yml               # Tempo distributed tracing config
└── loki/
    └── loki.yml                # Loki log aggregation config
```

## Services Overview

| Service | Port | Purpose | Access |
|---------|------|---------|--------|
| **PostgreSQL** | 5432 | Database with pgvector | `postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai` |
| **Grafana** | 3001 | Observability dashboards | http://localhost:3001 (admin/admin) |
| **Tempo** | 3200, 4317, 4318 | Distributed tracing | http://localhost:3200 |
| **Loki** | 3100 | Log aggregation | http://localhost:3100 |

## Quick Start

### Start Infrastructure

```bash
# From project root
cd infra/docker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Stop Infrastructure

```bash
cd infra/docker
docker-compose down

# Remove all data (clean start)
docker-compose down -v
```

## Configuration Files

### Docker Compose (`docker/docker-compose.yml`)

Main orchestration file defining all services, networks, and volumes.

### Tempo Configuration (`tempo/tempo.yml`)

Distributed tracing configuration:
- OTLP receivers (HTTP/gRPC)
- Local storage backend
- 1-hour trace retention
- Metrics generator enabled

### Loki Configuration (`loki/loki.yml`)

Log aggregation configuration:
- 7-day log retention
- Filesystem storage
- TSDB schema
- 16 MB/s ingestion rate

### Grafana Data Sources (`grafana/provisioning/datasources/datasources.yml`)

Auto-provisioned data sources:
- Loki (default)
- Tempo with log correlation

## Integration with Applications

### Backend API (FastAPI)

Update `apps/api/.env`:
```env
DATABASE_URL=postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

### Frontend (Next.js)

The frontend can optionally send client-side traces to:
```env
NEXT_PUBLIC_OTEL_ENDPOINT=http://localhost:4318
```

## Data Persistence

All data is stored in Docker volumes:
- `postgres-data`: Database files
- `grafana-data`: Dashboards and settings
- `tempo-data`: Trace data
- `loki-data`: Log data

Volumes persist between container restarts but can be removed with `docker-compose down -v`.

## Health Checks

Verify all services are healthy:

```bash
# PostgreSQL
docker exec recipe-postgres pg_isready -U recipe_user -d recipe_ai

# Grafana
curl http://localhost:3001/api/health

# Tempo
curl http://localhost:3200/ready

# Loki
curl http://localhost:3100/ready
```

## Grafana Setup

1. Access Grafana: http://localhost:3001
2. Login: `admin` / `admin`
3. Data sources are pre-configured:
   - Loki (logs)
   - Tempo (traces)
4. Start creating dashboards or use Explore view

## Common Operations

### View PostgreSQL Database

```bash
# Connect to database
docker exec -it recipe-postgres psql -U recipe_user -d recipe_ai

# Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# List tables
\dt
```

### Query Traces in Tempo

1. Open Grafana: http://localhost:3001
2. Go to Explore
3. Select "Tempo" data source
4. Search for traces by:
   - Trace ID
   - Service name
   - Duration
   - Tags

### Query Logs in Loki

1. Open Grafana: http://localhost:3001
2. Go to Explore
3. Select "Loki" data source
4. Use LogQL queries:
   ```logql
   {job="recipe-api"}
   {job="recipe-api"} |= "error"
   rate({job="recipe-api"}[5m])
   ```

## Troubleshooting

See the detailed troubleshooting section in `docker/README.md`.

Common issues:
- **Port conflicts**: Check if ports are already in use
- **Container won't start**: Check logs with `docker-compose logs [service]`
- **No traces appearing**: Verify OTLP endpoint configuration
- **No logs appearing**: Test Loki endpoint connectivity

## Development vs Production

**Current setup is for local development only.**

For production deployment, consider:
- Using Kubernetes instead of Docker Compose
- Enabling authentication on all services
- Using managed services (RDS, Cloud SQL, etc.)
- Implementing proper secrets management
- Enabling TLS/SSL
- Configuring proper retention policies
- Setting up backups
- Implementing high availability

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL + pgvector](https://github.com/pgvector/pgvector)
- [Grafana Documentation](https://grafana.com/docs/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)