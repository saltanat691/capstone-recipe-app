# Executive Summary — Recipe AI System

**Project:** AI-Powered Recipe Recommendation and Meal Planning Platform  
**Version:** 0.1.0  
**Author:** Saltanat  
**Date:** May 2026

---

## Problem Statement

Home cooks and busy families face a daily friction point: deciding what to eat given what they have on hand, their dietary needs, and how much time they have. Generic recipe search engines return static, keyword-matched results with no awareness of personal preferences, nutritional goals, or the week ahead. Meal planning remains a manual, time-consuming activity that most people abandon.

---

## Solution Overview

The Recipe AI System is a full-stack, AI-powered platform that turns a conversational request into a complete meal plan — from personalized recipe recommendations through nutritional guidance to a categorized grocery list — in a single interaction.

Users describe what they want in plain language ("I have chicken and some vegetables, planning for the week, gluten-free"). The system responds with tailored recipe recommendations, per-recipe nutrition notes, a structured day-by-day menu, and a ready-to-use shopping list.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Semantic Recipe Search** | pgvector cosine-similarity search over 237 recipes, re-ranked by cuisine preference and ingredient overlap |
| **Five-Agent AI Pipeline** | Ingredient extraction → RAG retrieval → Nutrition analysis → Menu planning → Grocery list generation |
| **Multi-Day Meal Planning** | 1–7 day menu generation with LLM-backed planning and deterministic fallback |
| **Dietary & Allergy Filtering** | Hard filters for 7 restriction categories (vegan, keto, gluten-free, etc.) applied before serving any result |
| **Nutrition Intelligence** | Per-recipe calorie/macro estimates with USDA grounding; health and safety warnings surfaced to users |
| **Content Safety** | OpenAI Moderation API integration; adversarial prompt injection blocked; PII scrubbed from inputs |
| **Authenticated & Guest Access** | API-key authentication with optional guest mode; keys stored as SHA-256 hashes |

---

## Technical Architecture

The system is built on a modern, production-ready stack chosen for reliability and observability:

- **Frontend:** Next.js 15 (React, Tailwind CSS) with API-key auth gate and guest mode
- **Backend:** FastAPI (Python 3.11) with async throughout; 10 req/min rate limiting
- **AI Orchestration:** LangGraph multi-agent workflow; GPT-4.1-mini for reasoning
- **Vector Search:** PostgreSQL + pgvector (HNSW index) with OpenAI `text-embedding-3-small` (1536 dimensions)
- **Observability:** OpenTelemetry traces → Grafana Tempo; metrics (9 instruments including process CPU/memory) → Grafana; structured JSON logs → Loki; LangSmith for LLM call tracing
- **Infrastructure:** Docker Compose; Alembic database migrations; Redis-optional embedding cache

---

## Scale and Quality

- **Recipe dataset:** 237 recipes spanning 14 cuisines (Central Asian, Italian, Mediterranean, Asian, Mexican, Indian, and more)
- **RAG retrieval quality (evaluated):** Mean Recall@5 ≥ 0.61, MRR ≥ 0.71 against a 20-query golden evaluation set
- **Test coverage:** 56 adversarial and safety tests (schema validation, PII scrubbing, prompt injection, harmful content); 43 RAG quality integration tests
- **Response time:** End-to-end latency tracked per agent node; rate limited at 10 req/min to ensure consistent performance

---

## Business Value

**For end users:** A frictionless, conversational interface replaces 30+ minutes of weekly meal planning with a single natural-language request.

**For operators:** The system collects structured feedback, retains user preferences for 90 days, and exposes full observability — enabling data-driven improvement of recommendation quality and agent behavior.

**For the business:** The architecture supports easy dataset expansion, model upgrades (model name is a single config value), and white-label deployment. The authenticated API layer enables monetization through tiered access.

---

## Potential Next Steps

1. **User accounts with persistent preferences** — replace API keys with username/password registration and user profile storage
2. **Expanded recipe dataset** — scale to 1,000+ recipes with community contributions and web scraping from licensed sources
3. **Mobile application** — the REST API is already mobile-ready; a React Native client would extend reach significantly
4. **Personalized re-ranking** — incorporate user feedback signals (likes/dislikes) into the retrieval scoring model
5. **Grocery integration** — connect the grocery list output to retail APIs (Instacart, Kroger) for direct cart population

---

## Conclusion

The Recipe AI System demonstrates that a well-orchestrated multi-agent AI pipeline — combining semantic search, structured reasoning, and nutritional intelligence — can deliver a compelling, production-quality user experience around a concrete everyday problem. The system is observable, safe, and extensible, providing a strong foundation for a commercial product.
