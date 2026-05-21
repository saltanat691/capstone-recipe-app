# Quick Start Guide

Get the Recipe AI System up and running in minutes.

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker and Docker Compose
- Git

## 1. Clone and Setup

```bash
# If not already cloned
git clone <repository-url>
cd recipe-ai-system

# Copy environment variables
cp .env.example .env
```

## 2. Start Infrastructure

Start PostgreSQL, Grafana, Tempo, and Loki:

```bash
cd infra/docker
docker-compose up -d

# Verify services are running
docker-compose ps
```

You should see all 4 services as "Up":
- recipe-postgres
- recipe-grafana
- recipe-tempo
- recipe-loki

## 3. Start Backend API

```bash
# Navigate to API directory
cd ../../apps/api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# The API reads from <repo-root>/.env — set that up from the repo root if
# you haven't already (`cp .env.example .env` at the repo root). No
# additional file is needed inside apps/api.

# Run the API
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

**Backend will be available at:**
- API: http://localhost:4000
- Swagger Docs: http://localhost:4000/docs

## 4. Start Frontend

Open a new terminal:

```bash
# Navigate to web directory
cd apps/web

# Install dependencies
npm install

# Run the frontend
npm run dev
```

**Frontend will be available at:** http://localhost:3000

## 5. Access Services

Now you can access:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | - |
| **Backend API** | http://localhost:4000 | - |
| **API Docs** | http://localhost:4000/docs | - |
| **Grafana** | http://localhost:3001 | admin / admin |
| **Tempo** | http://localhost:3200 | - |
| **PostgreSQL** | localhost:5432 | recipe_user / recipe_password |

## 6. Test the Application

1. Open http://localhost:3000 in your browser
2. You should see the "Recipe AI System" interface
3. Fill out the form:
   - Add some ingredients
   - Select dietary restrictions
   - Choose cuisine preferences
   - Set number of days
4. Click "Generate Recipe Recommendations"
5. Check browser console for logged data (API integration coming soon)

## 7. Verify Backend

1. Open http://localhost:4000/docs
2. Try the `/health` endpoint
3. Try the `/api/v1/status` endpoint

## 8. Check Observability

1. Open Grafana: http://localhost:3001
2. Login with `admin` / `admin`
3. Go to **Explore**
4. Select **Loki** data source
5. You can query logs (once applications start sending them)

## Stopping Services

### Stop Frontend
In the frontend terminal: `Ctrl+C`

### Stop Backend
In the backend terminal: `Ctrl+C`

### Stop Infrastructure
```bash
cd infra/docker
docker-compose down

# To remove all data as well:
docker-compose down -v
```

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using the port
lsof -i :3000  # Frontend
lsof -i :4000  # Backend
lsof -i :5432  # PostgreSQL
lsof -i :3001  # Grafana

# Kill the process
lsof -ti :PORT | xargs kill -9
```

### Docker Services Won't Start

```bash
# Check Docker is running
docker ps

# View logs
cd infra/docker
docker-compose logs

# Restart services
docker-compose restart
```

### Backend Module Not Found

Make sure you're in the correct directory and virtual environment is activated:

```bash
cd apps/api
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Module Not Found

```bash
cd apps/web
rm -rf node_modules package-lock.json
npm install
```

## Next Steps

- Explore the API documentation at http://localhost:4000/docs
- Read `docs/ARCHITECTURE.md` for system design
- Read `docs/DEVELOPMENT.md` for development guidelines
- Read `docs/OBSERVABILITY.md` for monitoring setup
- Check individual README files in:
  - `apps/web/README.md` - Frontend details
  - `apps/api/README.md` - Backend details
  - `infra/README.md` - Infrastructure details

## Development Workflow

### Making Changes

1. **Frontend changes**: Files in `apps/web/app/` - hot reload enabled
2. **Backend changes**: Files in `apps/api/app/` - hot reload enabled
3. **Infrastructure changes**: Restart Docker Compose services

### Viewing Logs

```bash
# Backend logs: Check terminal where API is running
# Frontend logs: Check terminal where Next.js is running
# Infrastructure logs:
cd infra/docker
docker-compose logs -f [service-name]
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it recipe-postgres psql -U recipe_user -d recipe_ai

# Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

# List tables (once created)
\dt

# Exit
\q
```

## Quick Commands Reference

```bash
# Start everything
cd infra/docker && docker-compose up -d
cd apps/api && source venv/bin/activate && uvicorn app.main:app --port 4000 --reload &
cd apps/web && npm run dev

# Stop everything
# Ctrl+C in terminals
cd infra/docker && docker-compose down

# View all running services
docker-compose ps
lsof -i :3000 -i :4000 -i :3001 -i :5432

# Reset database
cd infra/docker
docker-compose down -v
docker-compose up -d postgres
```

## Need Help?

- Check detailed README files in each directory
- Review documentation in `docs/` folder
- Check GitHub issues
- Review error logs in terminals and Docker