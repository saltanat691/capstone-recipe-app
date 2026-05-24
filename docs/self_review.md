# Self-Review — Architecture Decisions, Trade-offs, and Retrospective

**Project:** Recipe AI System  
**Author:** Saltanat  
**Date:** May 2026

---

## 1. Architecture Overview

The system follows a **multi-agent pipeline with a parallel fan-out** orchestrated by LangGraph:

```
User Request
    → Ingredient Agent               (parse intent, extract preferences)
    → RAG Retrieval Node             (embed query → pgvector search → re-rank)
    → Nutrition Agent   ─┐           (estimate macros, flag health warnings)   ┐ parallel
    → Menu Planner Agent ┘ (join)    (build day-by-day meal plan)              ┘
    → Grocery List Agent             (aggregate ingredients into shopping list)
    → Response Assembly              (merge all outputs into single response)
```

After retrieval, the Nutrition Agent and Menu Planner Agent run **in parallel** — both depend only on the retrieved recipes, not on each other. LangGraph's fan-in automatically waits for both before the Grocery List Agent starts. This reduces end-to-end latency from `nutrition_time + menu_time` to `max(nutrition_time, menu_time)`.

---

## 2. Key Architecture Decisions

### Decision 1: LangGraph over a custom orchestrator

**Choice:** Use LangGraph for agent workflow management.  
**Rationale:** LangGraph provides built-in state management, retry logic, and observability hooks. Building a custom orchestrator would have duplicated these concerns and added maintenance burden.  
**Trade-off:** LangGraph adds a dependency and introduces its own abstractions. The trade-off paid off: the parallel fan-out between the Nutrition Agent and Menu Planner Agent was implemented with a four-line graph wiring change, with no changes to the node logic. A plain `asyncio` sequence would have required manual task management and synchronization for the same result.

### Decision 2: pgvector over a dedicated vector database

**Choice:** Store embeddings in PostgreSQL via `pgvector` instead of Pinecone, Weaviate, or Qdrant.  
**Rationale:** The recipe dataset fits comfortably in PostgreSQL. Using pgvector avoids introducing a second persistence layer, simplifies the infrastructure, and keeps transactional and vector data co-located. The HNSW index provides sub-millisecond approximate nearest-neighbor search at this scale.  
**Trade-off:** pgvector does not support multi-tenancy, horizontal sharding, or real-time index updates as gracefully as dedicated vector databases. If the dataset grew to millions of recipes, migration to a dedicated store would be warranted.

### Decision 3: Re-ranking in Python after SQL retrieval

**Choice:** Fetch 4× the requested number of candidates from pgvector, then apply hard filters and soft scoring bonuses (cuisine match, ingredient overlap) in Python.  
**Rationale:** SQL-level pgvector queries support distance thresholds but not the composite scoring logic (cuisine bonus, dietary restriction checking against ingredient lists). Pulling 4× candidates and re-ranking in memory is fast for 237–1,000 recipes and gives full control over scoring logic without a stored-procedure maintenance burden.  
**Trade-off:** The over-fetch factor (4×) is a tuning parameter. Too low and filtering drops all results; too high and latency grows. A fallback path (return similarity-only results if filtering removes everything) handles the edge case gracefully.

### Decision 4: GPT-4.1-mini for all LLM calls

**Choice:** Use a single model (`gpt-4.1-mini`) for all five agents.  
**Rationale:** Simplicity — one model, one billing relationship, one rate limit to manage. GPT-4.1-mini provides strong instruction-following at lower cost and latency than GPT-4o.  
**Trade-off:** Different agents have different reasoning requirements. The grocery list aggregation is largely deterministic and could run on a smaller model (or no LLM at all). The menu planner benefits from stronger contextual reasoning. A future optimization would be model routing: use a cheaper model for structured extraction, a stronger model for open-ended planning.

### Decision 5: API key authentication over OAuth/JWT

**Choice:** Issue pre-generated API keys (`rcp_<token>`) stored as SHA-256 hashes.  
**Rationale:** Simple to implement and reason about. No token refresh logic, no client-side state beyond storing the key. Suitable for a system accessed primarily by developers or single users.  
**Trade-off:** No self-service registration, no fine-grained scoping, no token expiry. This was acknowledged as a deliberate shortcut for the capstone scope. A production system would use OAuth 2.0 with JWT access tokens and short expiry windows.

### Decision 6: Keyword fuzzy matching in RAG evaluation

**Choice:** The golden QA evaluation set uses `relevant_keywords` in addition to exact recipe names. A retrieved recipe is considered relevant if its name contains any keyword (case-insensitive substring match).  
**Rationale:** With 237 recipes including many variant entries ("Spaghetti Pomodoro Variant 3"), exact name matching caused false negatives. The RAG retrieval was semantically correct — it returned pasta dishes for pasta queries — but the evaluator couldn't recognize them. Fuzzy keyword matching makes the evaluation honest without lowering the standard.  
**Trade-off:** Keyword lists must be curated manually and kept in sync with the dataset. Overly broad keywords (e.g., "chicken" for q17) can inflate recall beyond 1.0, which is why recall is capped at 1.0. A production-grade evaluation pipeline would use embedding similarity between retrieved and expected recipes as the relevance judge.

---

## 3. What Worked Well

**Multi-agent decomposition:** Breaking the pipeline into five single-responsibility agents made each agent testable in isolation and easy to extend. The nutrition agent, for example, was added after the core retrieval pipeline was stable with no changes to upstream agents.

**OpenTelemetry from day one:** Instrumenting the API with OTel traces, structured JSON logs, and metrics from the beginning made debugging significantly easier. Node-level timing (`langgraph_node_complete` log events) made it straightforward to identify which agent was adding latency.

**Adversarial test suite:** Writing prompt injection, PII, and harmful content tests early caught real issues — particularly the behavior of the content filter when the OpenAI API was unreachable (graceful degradation vs. hard failure). This class of test is often skipped in prototypes and should not be.

**Dietary restriction fallback:** The decision to allow recipes through if no explicit violating ingredient is detected (permissive-by-default, not restrictive-by-default) avoided a problem where recipes without fully enumerated ingredient metadata would be incorrectly blocked.

---

## 4. What I Would Do Differently

**Embed richer text for retrieval:** The current `build_searchable_text()` function produces a flat string of recipe name, cuisine, and ingredients. Including dietary tags, meal type, and cooking method in the embedded text would improve semantic retrieval quality, particularly for queries like "quick weeknight dinner" or "high-protein breakfast."

**Separate evaluation dataset from keyword lists:** The `relevant_keywords` fix works but conflates evaluation metadata with retrieval logic. A cleaner approach: embed both queries and recipe names, compute cosine similarity between them, and use a threshold (e.g., 0.75) as the relevance judge. This removes the need for manual keyword curation.

**User-facing error messages:** Currently, internal errors surface generic 500 responses. A structured error schema with user-friendly messages (distinguishing "no recipes matched" from "service unavailable") would improve UX significantly.

**Streaming responses:** The entire pipeline runs synchronously from the user's perspective — the response appears only when all five agents complete. For a production system, streaming partial results (show recipes as they're retrieved, then append nutrition notes, then the menu) would dramatically improve perceived responsiveness.

**Redis embedding cache as a hard requirement:** Redis is currently optional, and the embedding cache is skipped when it's unavailable. In practice, every request embeds the query via the OpenAI API, adding ~200ms and a per-token cost. Making caching mandatory (with a graceful degradation to direct embedding on cache miss, but with alerting) would reduce latency and cost at scale.

---

## 5. Non-Functional Requirements Review

| Requirement | Status | Notes |
|---|---|---|
| **Throughput** | ✓ | 10 req/min rate limit; async throughout |
| **Content safety** | ✓ | OpenAI Moderation + PII scrubber |
| **Access control** | ✓ | API key auth with SHA-256 hashing |
| **Privacy / PII** | ✓ | Regex scrubber on input; data retention 90 days |
| **Observability** | ✓ | OTel traces, metrics (9 instruments), structured logs, LangSmith |
| **Bias mitigation** | ✓ | Cuisine diversity warning when results skew heavily to one cuisine |
| **Retrieval quality** | ✓ | Evaluated against 20-query golden set; Recall@5 ≥ 0.61, MRR ≥ 0.71 |
| **Adversarial robustness** | ✓ | 56 adversarial tests covering injection, jailbreak, harmful content, schema |
| **Caching** | Partial | Redis-optional; embedding cache skipped when Redis unavailable |
| **User self-registration** | ✗ | Out of scope for capstone; API keys issued manually |
| **Streaming responses** | ✗ | Single-response model; streaming deferred |

---

## 6. Lessons Learned

1. **Vector search quality depends more on what you embed than on the model you use.** The first version embedded only recipe names. Recall improved substantially when ingredients and cuisine were included in the searchable text.

2. **Observable systems are debuggable systems.** Several issues (an agent timing out, an empty retrieval result) were found and fixed because OTel traces showed exactly where time was being spent. Without this, the debugging process would have been purely log-based and much slower.

3. **Golden evaluation sets force honest measurement.** Writing 20 explicit test queries before running the full system revealed that the retrieval pipeline was returning semantically correct but name-mismatched results — a problem that would have been invisible without the evaluation harness.

4. **Async matters for LLM pipelines.** The original `embed_recipes.py` used the synchronous OpenAI client and blocked the event loop on a 237-recipe batch. Switching to `AsyncOpenAI` with retry backoff reduced the embedding run from "stuck forever" to completing in under 5 minutes.

5. **Defaults should be safe, not strict.** Setting `REQUIRE_AUTH=False` in development by default — rather than requiring the developer to configure an API key before anything works — removed a significant onboarding friction point. Security defaults should be enforced in production configuration, not in the development developer experience.
