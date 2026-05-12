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
│   ├── web/              # Frontend application
│   │   ├── src/
│   │   │   ├── app/      # Next.js app directory
│   │   │   ├── components/
│   │   │   ├── lib/
│   │   │   └── types/
│   │   ├── public/
│   │   └── package.json
│   │
│   └── api/              # Backend application
│       ├── src/
│       │   ├── routes/   # API endpoints
│       │   ├── services/ # Business logic
│       │   ├── agents/   # LangGraph agents
│       │   ├── models/   # Database models
│       │   └── utils/
│       ├── tests/
│       └── requirements.txt
│
├── packages/
│   └── shared/           # Shared code between apps
│       ├── types/        # TypeScript types
│       └── constants/    # Shared constants
│
├── infra/                # Infrastructure configurations
├── docs/                 # Documentation
└── ...
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
uvicorn src.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
API documentation at `http://localhost:8000/docs`.

**Key Commands**:
- `uvicorn src.main:app --reload` - Start dev server with hot reload
- `pytest` - Run tests
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
pytest                    # Run all tests
pytest tests/unit/        # Unit tests only
pytest tests/integration/ # Integration tests
pytest --cov              # With coverage report
```

**Testing Stack**:
- pytest for test framework
- pytest-asyncio for async tests
- httpx for API testing
- factory_boy for test fixtures

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

### Database Seeding

```bash
cd apps/api
python scripts/seed_database.py
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

# Backend (port 8000)
lsof -ti:8000 | xargs kill -9
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