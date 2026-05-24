# Development Guide

## Development Environment Setup

### Prerequisites

Ensure you have the following installed:

- **Node.js**: v18+ (recommended: use nvm or fnm)
- **Python**: 3.11+ (recommended: use pyenv)
- **PostgreSQL**: 15+ with pgvector extension
- **Docker & Docker Compose**: Latest stable version
- **Git**: For version control

### Initial Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd recipe-ai-system
   ```

2. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. Install dependencies:
   ```bash
   # Frontend
   cd apps/web
   npm install

   # Backend
   cd ../api
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Set up the database:
   ```bash
   # Start PostgreSQL with Docker (or use local installation)
   docker run --name recipe-postgres \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=recipe_ai \
     -p 5432:5432 \
     -d pgvector/pgvector:pg15

   # Run migrations (once implemented)
   cd apps/api
   alembic upgrade head
   ```

## Project Structure

### Monorepo Layout

```
recipe-ai-system/
├── apps/
│   ├── web/              # Next.js 15 frontend
│   │   ├── app/          # Next.js app directory (page.tsx, layout.tsx)
│   │   │   └── lib/      # auth.ts, api.ts helpers
│   │   └── package.json
│   │
│   └── api/              # FastAPI backend
│       ├── app/
│       │   ├── agents/   # LangGraph agents (5 agents + graph.py + state.py)
│       │   ├── api/v1/   # Route handlers (recommendations, health, auth)
│       │   ├── core/     # Config, security
│       │   ├── db/       # Session, base
│       │   ├── models/   # SQLAlchemy models (Recipe, User, AgentRun…)
│       │   ├── observability/ # OTel setup (metrics, tracing, logging)
│       │   ├── schemas/  # Pydantic request/response schemas
│       │   └── services/ # RAG retrieval, recipe text, content filter, PII
│       ├── alembic/      # Database migrations
│       ├── data/         # recipes_seed.json, rag_golden_qa.json
│       ├── scripts/      # seed_recipes.py, embed_recipes.py, evaluate_rag.py
│       ├── tests/        # pytest test suite
│       └── requirements.txt
│
├── infra/                # Docker Compose, Grafana, Tempo, Loki, Promtail configs
├── docs/                 # Documentation
└── .env                  # Root env file (loaded by both api and infra)
```

## Development Workflow

### Frontend Development (Next.js)

```bash
cd apps/web
npm run dev
```

The development server will start at `http://localhost:3000`.

**Key Commands**:
- `npm run dev` - Start development server
- `npm run build` - Build production bundle
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - TypeScript type checking

### Backend Development (FastAPI)

```bash
cd apps/api
source venv/bin/activate
uvicorn src.main:app --reload --port 4000
```

The API will be available at `http://localhost:4000`.
API documentation at `http://localhost:4000/docs`.

**Key Commands**:
- `uvicorn app.main:app --reload --port 4000` - Start dev server with hot reload
- `pytest` - Run all tests
- `pytest -m "not integration"` - Skip tests that need OpenAI/DB
- `black .` - Format code
- `ruff check .` - Lint code
- `mypy .` - Type checking

## Code Style and Standards

### TypeScript/JavaScript (Frontend)

- Use TypeScript for all new code
- Follow Airbnb style guide
- Use functional components with hooks
- Prefer named exports over default exports
- Use Prettier for formatting
- ESLint for linting

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints for all functions
- Use Black for code formatting
- Use Ruff for linting
- Docstrings for all public functions/classes
- Maximum line length: 88 characters

## Testing

### Frontend Tests

```bash
cd apps/web
npm run test          # Run unit tests
npm run test:watch    # Watch mode
npm run test:e2e      # End-to-end tests (when implemented)
```

**Testing Stack**:
- Jest for unit tests
- React Testing Library
- Playwright or Cypress for E2E tests

### Backend Tests

```bash
cd apps/api
pytest                              # Run all tests
pytest -m "not integration"         # Unit/mocked tests only (no OpenAI/DB needed)
pytest -m integration               # Integration tests (require OPENAI_API_KEY + DB)
pytest tests/test_adversarial.py    # Adversarial & safety tests (32 non-integration)
pytest tests/test_rag_evaluation.py # RAG retrieval quality tests (43 integration tests)
pytest --cov                        # With coverage report
```

**Test files**:
- `test_recommendations_endpoint.py` — API endpoint tests (mocked)
- `test_adversarial.py` — schema validation, PII scrubbing, prompt injection, harmful content
- `test_rag_evaluation.py` — RAG Precision@K, Recall@K, MRR against golden QA set (integration)
- `test_rag_recipe_service.py` — retrieval service unit tests
- `test_nutrition_agent.py`, `test_menu_planner_agent.py`, `test_grocery_list_agent.py` — agent unit tests

**Testing Stack**:
- pytest + pytest-asyncio for async tests
- httpx for API testing

## Database Management

### Migrations

Using Alembic for database migrations:

```bash
cd apps/api

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current version
alembic current
```

### Database Seeding and Embeddings

```bash
cd apps/api

# 1. Seed recipe data (237 recipes from data/recipes_seed.json)
python scripts/seed_recipes.py

# 2. Generate OpenAI embeddings (requires OPENAI_API_KEY)
python scripts/embed_recipes.py
python scripts/embed_recipes.py --force        # Re-embed all
python scripts/embed_recipes.py --batch-size 16 --sleep 2.0  # Slower for free-tier

# 3. Evaluate RAG retrieval quality
python scripts/evaluate_rag.py                 # Prints Precision@K, Recall@K, MRR
python scripts/evaluate_rag.py --output results/rag_eval.json
python scripts/evaluate_rag.py --fail-below-threshold  # Exit 1 if metrics fail
```

## Working with AI Agents

### LangGraph Development

Agent definitions will be in `apps/api/src/agents/`.

**Best Practices**:
- Keep agents focused on single responsibilities
- Use structured outputs with Pydantic models
- Implement proper error handling
- Add comprehensive logging
- Test agents in isolation

### LangSmith Integration

To trace agent executions:

1. Set environment variables in `.env`:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_key
   ```

2. View traces at https://smith.langchain.com

## Git Workflow

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(api): add recipe recommendation endpoint

Implement endpoint for AI-powered recipe recommendations
using LangGraph orchestration.

Closes #123
```

## Debugging

### Frontend Debugging

- Use React DevTools browser extension
- Next.js DevTools (built-in)
- Browser DevTools for network and console
- VS Code debugger configuration

### Backend Debugging

- Use `breakpoint()` for pdb debugger
- VS Code Python debugger
- FastAPI debug mode with `--reload`
- Print debugging with structured logging

## Common Issues and Solutions

### Port Already in Use

```bash
# Frontend (port 3000)
lsof -ti:3000 | xargs kill -9

# Backend (port 4000)
lsof -ti:4000 | xargs kill -9
```

### Database Connection Issues

- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Ensure pgvector extension is installed

### Module Not Found

```bash
# Frontend
rm -rf node_modules package-lock.json
npm install

# Backend
pip install -r requirements.txt --force-reinstall
```

## Performance Optimization

### Frontend
- Use Next.js Image component for images
- Implement code splitting and lazy loading
- Optimize bundle size with tree shaking
- Use React.memo for expensive components

### Backend
- Use async operations for I/O
- Implement database query optimization
- Add caching for frequently accessed data
- Use connection pooling for database

## Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph)
- [PostgreSQL Documentation](https://www.postgresql.org/docs)