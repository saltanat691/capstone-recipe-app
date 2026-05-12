# Recipe AI System

An intelligent recipe management and recommendation system powered by AI agents, built with modern observability and scalability in mind.

## Architecture Overview

This is a monorepo project using a microservices architecture with AI orchestration, full-stack observability, and vector-based search capabilities.

### Tech Stack

#### Frontend
- **Next.js 14+** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling

#### Backend
- **FastAPI** - High-performance Python API framework
- **LangGraph** - AI agent orchestration and workflows
- **PostgreSQL** - Primary relational database
- **pgvector** - Vector embeddings for semantic search

#### Observability
- **OpenTelemetry** - Distributed tracing, metrics, and logs
- **Grafana** - Visualization and dashboards
- **Tempo** - Distributed tracing backend
- **Loki** - Log aggregation system
- **LangSmith** - LLM observability and tracing

## Project Structure

```
recipe-ai-system/
├── apps/
│   ├── web/              # Next.js frontend application
│   └── api/              # FastAPI backend application
├── packages/
│   └── shared/           # Shared types, utilities, and constants
├── infra/
│   ├── docker/           # Docker compose and container configs
│   ├── grafana/          # Grafana dashboards and config
│   ├── tempo/            # Tempo tracing configuration
│   └── loki/             # Loki logging configuration
├── docs/                 # Project documentation
├── .env.example          # Example environment variables
├── .gitignore           # Git ignore patterns
└── README.md            # This file
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose
- Git

### Quick Setup

For a comprehensive step-by-step setup guide with verification commands, see **[Setup Checklist](docs/SETUP_CHECKLIST.md)**.

**Quick start commands:**

```bash
# 1. Start infrastructure
cd infra/docker
docker-compose up -d

# 2. Setup and start backend
cd ../../apps/api
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_recipes.py
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

# 3. Setup and start frontend (in new terminal)
cd apps/web
npm install
npm run dev
```

**Access points:**
- **API**: http://localhost:4000 (docs at http://localhost:4000/docs)
- **Frontend**: http://localhost:3000
- **Grafana**: http://localhost:3001 (admin/admin)
- **PostgreSQL**: localhost:5432 (recipe_user/recipe_password)

### Verification

Quick verification that everything is working:

```bash
# Check API health
curl http://localhost:4000/health

# Check database
docker-compose exec postgres psql -U recipe_user -d recipe_ai -c 'SELECT COUNT(*) FROM recipes;'
# Should return: 20

# Test recommendations
curl -X POST http://localhost:4000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"message": "Plan meals for the week", "days": 7}'
```

For detailed verification steps and troubleshooting, see **[Setup Checklist](docs/SETUP_CHECKLIST.md)**.

### Detailed Setup Guides

For component-specific setup instructions:

- **Backend API**: See `apps/api/README.md`
- **Frontend**: See `apps/web/README.md`
- **Infrastructure**: See `infra/docker/README.md`

## Development Workflow

### Monorepo Structure

This project uses a monorepo structure to maintain:
- Shared code between frontend and backend
- Consistent tooling and configuration
- Simplified dependency management

### Observability Stack

The observability stack provides:
- **Distributed Tracing**: Track requests across services with Tempo
- **Log Aggregation**: Centralized logging with Loki
- **Metrics & Dashboards**: Visualization with Grafana
- **LLM Tracing**: Debug and optimize AI agents with LangSmith

## Features

### Current Features ✅

- **Recipe Database**: 20 seed recipes with Central Asian and international cuisines
- **Recipe Search**: Score-based search with ingredient matching, dietary restrictions, and cuisine preferences
- **Menu Planning**: Automated multi-day meal plan generation
- **Shopping Lists**: Organized grocery lists by category
- **API Documentation**: Interactive Swagger UI and ReDoc
- **Observability Stack**:
  - Distributed tracing with OpenTelemetry and Tempo
  - Structured JSON logging with Loki
  - Grafana dashboards for visualization
  - Request ID tracking and trace correlation
- **Database**: PostgreSQL with pgvector extension and Alembic migrations
- **Next.js Frontend**: Recipe recommendation form with Tailwind CSS

### In Progress 🚧

- Frontend-to-API integration
- RAG (Retrieval-Augmented Generation) with vector embeddings
- Semantic search using pgvector

### Planned 📋

- AI-powered recipe recommendations with LangGraph agents:
  - Ingredient analysis agent
  - Recipe recommendation agent
  - Nutrition analysis agent
  - Menu planning agent
  - Shopping list agent
  - Safety validation agent
- LLM integration (OpenAI/Anthropic)
- LangSmith LLM observability
- User authentication and preferences
- Recipe CRUD operations
- Nutritional information and tracking
- Recipe ratings and reviews

## Documentation

### Quick Start Guides

- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - ⭐ **Start here!** Quick testing commands for all services
- **[Setup Checklist](docs/SETUP_CHECKLIST.md)** - Complete setup verification and troubleshooting
- **[Consistency Check](CONSISTENCY_CHECK.md)** - Project configuration verification results

### Detailed Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design and component interactions
- **[Development Guide](docs/DEVELOPMENT.md)** - Development setup and guidelines
- **[Observability](docs/OBSERVABILITY.md)** - Monitoring and tracing setup

Component-specific documentation:

- **Backend API**: `apps/api/README.md` - FastAPI setup, endpoints, agents
  - Database: `apps/api/DATABASE.md`
  - Agents: `apps/api/AGENTS.md`
  - Observability: `apps/api/OBSERVABILITY.md`
  - LangSmith: `apps/api/LANGSMITH.md`
- **Frontend**: `apps/web/README.md` - Next.js app setup and structure
- **Infrastructure**: `infra/docker/README.md` - Docker services configuration

## License

See [LICENSE](LICENSE) file for details.