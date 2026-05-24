"""
RAG retrieval quality tests — golden QA set.

Each test runs a query from data/rag_golden_qa.json through the live retrieval
pipeline and asserts that Precision@K, Recall@K, and MRR meet the thresholds
defined in that same file.

These are integration tests: they require OPENAI_API_KEY (for query embedding)
and a Postgres database with embedded recipes.

Run:
    pytest tests/test_rag_evaluation.py                         # all
    pytest tests/test_rag_evaluation.py -k q01                  # single query
    pytest tests/test_rag_evaluation.py --tb=short -q           # compact output
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pytest

from app.db.session import engine
from app.services.rag_recipe_service import RecipeSearchFilters, retrieve_recipes

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Load golden QA set
# ---------------------------------------------------------------------------

_GOLDEN_PATH = Path(__file__).parent.parent / "data" / "rag_golden_qa.json"
_GOLDEN = json.loads(_GOLDEN_PATH.read_text())
_K: int = _GOLDEN["k"]
_THRESHOLDS: dict = _GOLDEN["thresholds"]
_QUERIES: list[dict] = _GOLDEN["queries"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def _dispose_engine():
    """Prevent asyncpg 'attached to different loop' errors between tests."""
    await engine.dispose()
    yield
    await engine.dispose()


def _is_relevant(name: str, expected: list[str], keywords: list[str]) -> bool:
    name_lower = name.lower()
    if name_lower in {e.lower() for e in expected}:
        return True
    return any(kw.lower() in name_lower for kw in keywords)


def _precision(retrieved: list[str], expected: list[str], keywords: list[str]) -> float:
    if not retrieved:
        return 0.0
    hits = sum(1 for r in retrieved if _is_relevant(r, expected, keywords))
    return hits / len(retrieved)


def _recall(retrieved: list[str], expected: list[str], keywords: list[str]) -> float:
    if not expected:
        return 1.0
    hits = sum(1 for r in retrieved if _is_relevant(r, expected, keywords))
    return min(hits / len(expected), 1.0)


def _reciprocal_rank(retrieved: list[str], expected: list[str], keywords: list[str]) -> float:
    for rank, name in enumerate(retrieved, start=1):
        if _is_relevant(name, expected, keywords):
            return 1.0 / rank
    return 0.0


async def _retrieve(entry: dict) -> list[str]:
    filters_raw = entry.get("filters", {})
    filters = RecipeSearchFilters(
        dietary_restrictions=filters_raw.get("dietary_restrictions", []),
        excluded_ingredients=filters_raw.get("excluded_ingredients", []),
        cuisine_preferences=filters_raw.get("cuisine_preferences", []),
        available_ingredients=filters_raw.get("available_ingredients", []),
        max_cooking_time_minutes=filters_raw.get("max_cooking_time_minutes"),
        meal_type=filters_raw.get("meal_type"),
    )
    hits = await retrieve_recipes(entry["query"], filters, limit=_K)
    return [h.name for h in hits]


# ---------------------------------------------------------------------------
# Per-query tests  (parametrized over every entry in the golden set)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "entry",
    _QUERIES,
    ids=[q["id"] for q in _QUERIES],
)
async def test_query_has_nonzero_recall(require_openai_key, entry: dict):
    """At least one expected recipe must appear in the top-K results."""
    retrieved = await _retrieve(entry)
    keywords = entry.get("relevant_keywords", [])
    rr = _reciprocal_rank(retrieved, entry["expected_recipes"], keywords)

    assert rr > 0, (
        f"[{entry['id']}] {entry['description']}\n"
        f"  Query    : {entry['query']}\n"
        f"  Expected : {entry['expected_recipes']}\n"
        f"  Got      : {retrieved}\n"
        f"  No relevant recipe found in top {_K} results."
    )


@pytest.mark.parametrize(
    "entry",
    _QUERIES,
    ids=[q["id"] for q in _QUERIES],
)
async def test_query_recall_at_k(require_openai_key, entry: dict):
    """Recall@K must be >= 0.5 for every individual query (at least half of
    expected recipes appear in top K)."""
    retrieved = await _retrieve(entry)
    keywords = entry.get("relevant_keywords", [])
    r = _recall(retrieved, entry["expected_recipes"], keywords)

    assert r >= 0.5, (
        f"[{entry['id']}] {entry['description']}\n"
        f"  Recall@{_K}={r:.2f} < 0.50\n"
        f"  Expected : {entry['expected_recipes']}\n"
        f"  Got      : {retrieved}"
    )


# ---------------------------------------------------------------------------
# Aggregate metric tests  (run once over all queries)
# ---------------------------------------------------------------------------

async def test_aggregate_precision_at_k(require_openai_key):
    """Mean Precision@K across all queries must meet the golden-set threshold."""
    threshold = _THRESHOLDS["precision_at_k"]
    scores = []
    for entry in _QUERIES:
        retrieved = await _retrieve(entry)
        keywords = entry.get("relevant_keywords", [])
        scores.append(_precision(retrieved, entry["expected_recipes"], keywords))

    mean_p = sum(scores) / len(scores)
    assert mean_p >= threshold, (
        f"Mean Precision@{_K} = {mean_p:.3f} < threshold {threshold:.2f}\n"
        f"Per-query: {[f'{s:.2f}' for s in scores]}"
    )


async def test_aggregate_recall_at_k(require_openai_key):
    """Mean Recall@K across all queries must meet the golden-set threshold."""
    threshold = _THRESHOLDS["recall_at_k"]
    scores = []
    for entry in _QUERIES:
        retrieved = await _retrieve(entry)
        keywords = entry.get("relevant_keywords", [])
        scores.append(_recall(retrieved, entry["expected_recipes"], keywords))

    mean_r = sum(scores) / len(scores)
    assert mean_r >= threshold, (
        f"Mean Recall@{_K} = {mean_r:.3f} < threshold {threshold:.2f}\n"
        f"Per-query: {[f'{s:.2f}' for s in scores]}"
    )


async def test_aggregate_mrr(require_openai_key):
    """Mean Reciprocal Rank across all queries must meet the golden-set threshold."""
    threshold = _THRESHOLDS["mrr"]
    scores = []
    for entry in _QUERIES:
        retrieved = await _retrieve(entry)
        keywords = entry.get("relevant_keywords", [])
        scores.append(_reciprocal_rank(retrieved, entry["expected_recipes"], keywords))

    mrr = sum(scores) / len(scores)
    assert mrr >= threshold, (
        f"MRR = {mrr:.3f} < threshold {threshold:.2f}\n"
        f"Per-query RR: {[f'{s:.2f}' for s in scores]}"
    )
