# Docker Infrastructure

This directory contains the Docker Compose setup for the Recipe AI System infrastructure, including database, observability, and monitoring services.

## Services

### PostgreSQL with pgvector
- **Image**: `pgvector/pgvector:pg16`
- **Port**: 5432
- **Database**: `recipe_ai`
- **User**: `recipe_user`
- **Password**: `recipe_password`
- **Purpose**: Primary database with vector embeddings support for semantic search

### Grafana
- **Image**: `grafana/grafana:11.0.0`
- **Port**: 3001
- **Credentials**: `admin` / `admin`
- **Purpose**: Visualization and dashboards for observability data

### Tempo
- **Image**: `grafana/tempo:2.4.1`
- **Ports**:
  - 3200: Tempo HTTP API/UI
  - 4317: OTLP gRPC endpoint
  - 4318: OTLP HTTP endpoint
- **Purpose**: Distributed tracing backend for OpenTelemetry traces

### Loki
- **Image**: `grafana/loki:3.0.0`
- **Port**: 3100
- **Purpose**: Log aggregation system

## Quick Start

### Start All Services

From the project root:

```bash
cd infra/docker
docker-compose up -d
```

Or from any directory:

```bash
docker-compose -f infra/docker/docker-compose.yml up -d
```

### Check Service Status

```bash
docker-compose ps
```

Expected output:
```
NAME               IMAGE                        STATUS         PORTS
recipe-grafana     grafana/grafana:11.0.0       Up             0.0.0.0:3001->3001/tcp
recipe-loki        grafana/loki:3.0.0           Up             0.0.0.0:3100->3100/tcp
recipe-postgres    pgvector/pgvector:pg16       Up (healthy)   0.0.0.0:5432->5432/tcp
recipe-tempo       grafana/tempo:2.4.1          Up             0.0.0.0:3200->3200/tcp, 0.0.0.0:4317-4318->4317-4318/tcp
```

### View Logs

View logs for all services:
```bash
docker-compose logs -f
```

View logs for a specific service:
```bash
docker-compose logs -f postgres
docker-compose logs -f grafana
docker-compose logs -f tempo
docker-compose logs -f loki
```

## Accessing Services

### PostgreSQL

**Connection details:**
- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `recipe_ai`
- **User**: `recipe_user`
- **Password**: `recipe_password`

**Connection string:**
```
postgresql://recipe_user:recipe_password@localhost:5432/recipe_ai
```

**Connect with psql:**
```bash
psql -h localhost -p 5432 -U recipe_user -d recipe_ai
```

**Enable pgvector extension:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Grafana

**Access**: http://localhost:3001

**Credentials**:
- Username: `admin`
- Password: `admin`

**Pre-configured data sources**:
- Loki (default)
- Tempo

### Tempo

**API/UI**: http://localhost:3200

**OTLP Endpoints**:
- gRPC: `http://localhost:4317`
- HTTP: `http://localhost:4318`

**Send traces from your application**:
```python
# Python example
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="http://localhost:4317",
    insecure=True
)
```

### Loki

**API**: http://localhost:3100

**Send logs**:
```bash
curl -X POST http://localhost:3100/loki/api/v1/push \
  -H "Content-Type: application/json" \
  -d '{"streams": [{"stream": {"job": "test"}, "values": [["1234567890000000000", "test log message"]]}]}'
```

## Managing Services

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove Volumes (Clean Start)

```bash
docker-compose down -v
```

**Warning**: This will delete all data including database contents.

### Restart a Specific Service

```bash
docker-compose restart postgres
docker-compose restart grafana
docker-compose restart tempo
docker-compose restart loki
```

### Rebuild Services

If you've made changes to configuration files:

```bash
docker-compose down
docker-compose up -d --force-recreate
```

## Data Persistence

All data is persisted in Docker volumes:

- `postgres-data`: PostgreSQL database files
- `grafana-data`: Grafana dashboards and settings
- `tempo-data`: Tempo trace data
- `loki-data`: Loki log data

### View Volumes

```bash
docker volume ls | grep recipe
```

### Backup Database

```bash
docker exec recipe-postgres pg_dump -U recipe_user recipe_ai > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker exec -i recipe-postgres psql -U recipe_user -d recipe_ai
```

## Health Checks

### PostgreSQL Health

```bash
docker exec recipe-postgres pg_isready -U recipe_user -d recipe_ai
```

### Grafana Health

```bash
curl http://localhost:3001/api/health
```

### Tempo Health

```bash
curl http://localhost:3200/ready
```

### Loki Health

```bash
curl http://localhost:3100/ready
```

## Configuration Files

### Tempo Configuration

Located at: `infra/tempo/tempo.yml`

Key settings:
- OTLP receivers on ports 4317 (gRPC) and 4318 (HTTP)
- Local storage backend
- Block retention: 1 hour
- Metrics generator enabled

### Loki Configuration

Located at: `infra/loki/loki.yml`

Key settings:
- Retention period: 7 days (168 hours)
- Filesystem storage
- TSDB schema (v13)
- Ingestion rate: 16 MB/s

### Grafana Data Sources

Located at: `infra/grafana/provisioning/datasources/datasources.yml`

Pre-configured data sources:
- Loki (default) with trace correlation
- Tempo with logs integration

## Troubleshooting

### Port Already in Use

If you get port conflicts, check what's using the ports:

```bash
# PostgreSQL (5432)
lsof -i :5432

# Grafana (3001)
lsof -i :3001

# Tempo (3200, 4317, 4318)
lsof -i :3200
lsof -i :4317
lsof -i :4318

# Loki (3100)
lsof -i :3100
```

Kill the process or modify ports in `docker-compose.yml`.

### Container Won't Start

Check logs:
```bash
docker-compose logs [service-name]
```

Check container status:
```bash
docker ps -a | grep recipe
```

### Database Connection Issues

1. Verify PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Check PostgreSQL logs:
   ```bash
   docker-compose logs postgres
   ```

3. Test connection:
   ```bash
   psql -h localhost -p 5432 -U recipe_user -d recipe_ai
   ```

### Grafana Not Showing Data Sources

1. Restart Grafana:
   ```bash
   docker-compose restart grafana
   ```

2. Check provisioning logs:
   ```bash
   docker-compose logs grafana | grep provisioning
   ```

3. Manually verify data sources at: http://localhost:3001/datasources

### Tempo Not Receiving Traces

1. Verify Tempo is running:
   ```bash
   curl http://localhost:3200/ready
   ```

2. Check your application's OTLP endpoint configuration

3. Review Tempo logs:
   ```bash
   docker-compose logs tempo
   ```

### Loki Not Receiving Logs

1. Test Loki endpoint:
   ```bash
   curl http://localhost:3100/ready
   ```

2. Send a test log:
   ```bash
   curl -X POST http://localhost:3100/loki/api/v1/push \
     -H "Content-Type: application/json" \
     -d '{"streams": [{"stream": {"job": "test"}, "values": [["'$(date +%s)000000000'", "test message"]]}]}'
   ```

3. Query in Grafana Explore: http://localhost:3001/explore

## Network

All services are on the `recipe-network` bridge network, allowing them to communicate using service names:

- `postgres:5432`
- `grafana:3001`
- `tempo:3200`
- `loki:3100`

Applications running on the host should use `localhost` instead.

## Security Notes

**These settings are for local development only:**

- Default passwords are used (not secure for production)
- Anonymous access enabled in Grafana
- No authentication on Tempo/Loki
- Services exposed on all interfaces (0.0.0.0)

**For production deployment:**
- Use strong passwords
- Enable authentication
- Use secrets management
- Restrict network access
- Enable TLS/SSL
- Configure proper retention policies

## Next Steps

After starting the infrastructure:

1. **Access Grafana**: http://localhost:3001
2. **Explore data sources** in Grafana (Configuration → Data Sources)
3. **Configure your applications** to send traces to `http://localhost:4318`
4. **Configure your applications** to send logs to `http://localhost:3100`
5. **Create dashboards** in Grafana for your metrics
6. **Set up alerts** for important metrics

## Additional Commands

### Remove Everything (Clean Slate)

```bash
docker-compose down -v
docker network prune -f
docker volume prune -f
```

### Export Logs to File

```bash
docker-compose logs > docker-logs.txt
```

### Monitor Resource Usage

```bash
docker stats
```

### Update Images

```bash
docker-compose pull
docker-compose up -d
```

## Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Tempo Documentation](https://grafana.com/docs/tempo/latest/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)