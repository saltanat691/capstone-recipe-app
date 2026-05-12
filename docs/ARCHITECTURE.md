# Architecture

## System Overview

The Recipe AI System is built as a modern microservices architecture with AI agent orchestration, vector-based semantic search, and comprehensive observability.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                      (Next.js + TS)                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   UI Layer   │  │  State Mgmt  │  │  API Client  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                    HTTP/REST
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                      Backend API                             │
│                   (FastAPI + Python)                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ REST Routes  │  │   Services   │  │  AI Agents   │     │
│  └──────────────┘  └──────────────┘  │ (LangGraph)  │     │
│                                       └──────────────┘     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │         │
         ┌──────────▼─┐   ┌───▼──────────┐
         │ PostgreSQL │   │     LLMs     │
         │ + pgvector │   │ (OpenAI/etc) │
         └────────────┘   └──────────────┘
```

## Component Details

### Frontend (Next.js)

**Location**: `apps/web/`

The frontend is a server-side rendered React application built with Next.js 14+ using the App Router.

**Responsibilities**:
- User interface and interactions
- Client-side state management
- API communication
- Server-side rendering for performance

**Key Technologies**:
- Next.js 14+ with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- React Query or SWR for data fetching

### Backend API (FastAPI)

**Location**: `apps/api/`

A high-performance Python API server handling business logic and orchestrating AI agents.

**Responsibilities**:
- RESTful API endpoints
- Business logic execution
- Database operations
- AI agent orchestration
- Authentication and authorization

**Key Technologies**:
- FastAPI for async API framework
- SQLAlchemy for ORM
- Pydantic for data validation
- LangGraph for AI orchestration

### AI Orchestration Layer

**Framework**: LangGraph

LangGraph manages complex AI agent workflows, enabling:
- Multi-step reasoning
- Tool calling and function execution
- State management across agent interactions
- Conditional routing and decision making

**Agent Types** (to be implemented):
- Recipe recommendation agent
- Ingredient substitution agent
- Meal planning agent
- Nutrition analysis agent

### Database Layer

**Primary Database**: PostgreSQL with pgvector extension

**Schema Design**:
- Relational data for structured information (users, recipes, ingredients)
- Vector embeddings for semantic search
- JSONB for flexible metadata storage

**Vector Search**:
- pgvector extension for similarity search
- Embeddings generated from recipe descriptions
- Semantic recipe discovery

### Observability Stack

#### OpenTelemetry
- Distributed tracing across services
- Metrics collection and export
- Structured logging

#### Grafana
- Central dashboard for all observability data
- Custom dashboards for system health
- Alerting and notifications

#### Tempo
- Distributed tracing backend
- Stores and queries trace data
- Integrated with Grafana

#### Loki
- Log aggregation system
- Efficient log storage and querying
- Label-based log organization

#### LangSmith
- LLM-specific observability
- Trace agent executions
- Debug and optimize prompts
- Cost tracking for LLM calls

## Data Flow

### Typical Request Flow

1. User interacts with Next.js frontend
2. Frontend makes API request to FastAPI backend
3. Backend authenticates and validates request
4. If AI processing needed:
   - LangGraph orchestrates agent workflow
   - Agents make LLM calls (traced by LangSmith)
   - Agents query database or external APIs
5. Response assembled and returned to frontend
6. Frontend updates UI with results

### Observability Flow

All requests are instrumented with:
- Trace IDs propagated across service boundaries
- Spans for each operation
- Logs tagged with trace context
- Metrics collected at each layer

## Security Considerations

- API key management via environment variables
- Database credentials stored securely
- CORS configuration for frontend access
- Rate limiting on API endpoints
- Input validation at all boundaries

## Scalability Considerations

- Stateless API design for horizontal scaling
- Database connection pooling
- Caching strategies for common queries
- Async operations where possible
- Vector index optimization for search performance

## Future Enhancements

- Kubernetes deployment for container orchestration
- Redis for caching and session management
- Message queue (RabbitMQ/Redis) for async tasks
- CDN for static asset delivery
- Multi-region database replication