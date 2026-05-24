"""
RAG Retrieval Quality Evaluation
=================================
Measures Precision@K, Recall@K, and MRR against a hand-curated golden QA set.

Usage
-----
    # From apps/api/
    python scripts/evaluate_rag.py
    python scripts/evaluate_rag.py --k 3
    python scripts/evaluate_rag.py --k 5 --output results/rag_eval.json
    python scripts/evaluate_rag.py --fail-below-threshold   # exits 1 if metrics miss target

Requirements
------------
    OPENAI_API_KEY must be set (used to embed each query).
    DATABASE_URL must point at a Postgres instance with embedded recipes.
    Run scripts/seed_recipes.py + scripts/embed_recipes.py first.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path / env bootstrap  (must happen before any app import)
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_API_ROOT = _HERE.parent
sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv

# Load env files if present. Inside Docker, env vars are injected by
# docker-compose so these files may not exist — skip gracefully.
_local_env = _API_ROOT / ".env"
if _local_env.exists():
    load_dotenv(_local_env, override=True)

try:
    _root_env = _API_ROOT.parents[1] / ".env"
    if _root_env.exists():
        load_dotenv(_root_env, override=False)
except IndexError:
    pass

from app.db.session import engine  # noqa: E402
from app.services.rag_recipe_service import RecipeSearchFilters, retrieve_recipes  # noqa: E402

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

GOLDEN_QA_PATH = _API_ROOT / "data" / "rag_golden_qa.json"


@dataclass
class QueryResult:
    query_id: str
    description: str
    query: str
    expected: list[str]
    retrieved: list[str]
    k: int

    keywords: list[str] = field(default_factory=list)

    def _is_relevant(self, name: str) -> bool:
        name_lower = name.lower()
        if name_lower in {e.lower() for e in self.expected}:
            return True
        return any(kw.lower() in name_lower for kw in self.keywords)

    @property
    def relevant_retrieved(self) -> list[str]:
        return [r for r in self.retrieved if self._is_relevant(r)]

    @property
    def precision_at_k(self) -> float:
        if not self.retrieved:
            return 0.0
        return len(self.relevant_retrieved) / len(self.retrieved)

    @property
    def recall_at_k(self) -> float:
        if not self.expected:
            return 1.0
        return min(len(self.relevant_retrieved) / len(self.expected), 1.0)

    @property
    def reciprocal_rank(self) -> float:
        for rank, name in enumerate(self.retrieved, start=1):
            if self._is_relevant(name):
                return 1.0 / rank
        return 0.0


@dataclass
class EvalReport:
    k: int
    results: list[QueryResult] = field(default_factory=list)

    @property
    def mean_precision(self) -> float:
        return sum(r.precision_at_k for r in self.results) / max(len(self.results), 1)

    @property
    def mean_recall(self) -> float:
        return sum(r.recall_at_k for r in self.results) / max(len(self.results), 1)

    @property
    def mrr(self) -> float:
        return sum(r.reciprocal_rank for r in self.results) / max(len(self.results), 1)


# ---------------------------------------------------------------------------
# Core evaluation logic
# ---------------------------------------------------------------------------

async def _run_single_query(
    qid: str,
    description: str,
    query: str,
    expected: list[str],
    keywords: list[str],
    filters_raw: dict,
    k: int,
) -> QueryResult:
    filters = RecipeSearchFilters(
        dietary_restrictions=filters_raw.get("dietary_restrictions", []),
        excluded_ingredients=filters_raw.get("excluded_ingredients", []),
        cuisine_preferences=filters_raw.get("cuisine_preferences", []),
        available_ingredients=filters_raw.get("available_ingredients", []),
        max_cooking_time_minutes=filters_raw.get("max_cooking_time_minutes"),
        meal_type=filters_raw.get("meal_type"),
    )
    try:
        hits = await retrieve_recipes(query, filters, limit=k)
        retrieved = [h.name for h in hits]
    except Exception as exc:
        print(f"  [ERROR] {qid}: {exc}", file=sys.stderr)
        retrieved = []

    return QueryResult(
        query_id=qid,
        description=description,
        query=query,
        expected=expected,
        keywords=keywords,
        retrieved=retrieved,
        k=k,
    )


async def evaluate(golden_path: Path, k: int) -> EvalReport:
    golden = json.loads(golden_path.read_text())
    queries = golden["queries"]

    print(f"\nRunning RAG evaluation — K={k}, {len(queries)} queries\n")

    report = EvalReport(k=k)
    for entry in queries:
        print(f"  [{entry['id']}] {entry['description'][:55]:<56}", end="", flush=True)
        result = await _run_single_query(
            qid=entry["id"],
            description=entry["description"],
            query=entry["query"],
            expected=entry["expected_recipes"],
            keywords=entry.get("relevant_keywords", []),
            filters_raw=entry.get("filters", {}),
            k=k,
        )
        report.results.append(result)
        hit = "✓" if result.reciprocal_rank > 0 else "✗"
        print(
            f"  P@{k}={result.precision_at_k:.2f}  "
            f"R@{k}={result.recall_at_k:.2f}  "
            f"RR={result.reciprocal_rank:.2f}  {hit}"
        )

    return report


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _print_report(report: EvalReport, thresholds: dict) -> None:
    sep = "─" * 72
    k = report.k

    print(f"\n{sep}")
    print(f"{'RAG RETRIEVAL EVALUATION SUMMARY':^72}")
    print(sep)
    print(f"  Queries evaluated : {len(report.results)}")
    print(f"  K                 : {k}")
    print(sep)

    p_ok  = report.mean_precision >= thresholds.get("precision_at_k", 0)
    r_ok  = report.mean_recall   >= thresholds.get("recall_at_k", 0)
    m_ok  = report.mrr           >= thresholds.get("mrr", 0)

    def _flag(ok: bool) -> str:
        return "✓ PASS" if ok else "✗ FAIL"

    print(f"  Mean Precision@{k}  : {report.mean_precision:.3f}   threshold={thresholds.get('precision_at_k', 0):.2f}  {_flag(p_ok)}")
    print(f"  Mean Recall@{k}    : {report.mean_recall:.3f}   threshold={thresholds.get('recall_at_k', 0):.2f}  {_flag(r_ok)}")
    print(f"  MRR               : {report.mrr:.3f}   threshold={thresholds.get('mrr', 0):.2f}  {_flag(m_ok)}")
    print(sep)

    # Per-query breakdown for failures
    failures = [r for r in report.results if r.reciprocal_rank == 0]
    if failures:
        print(f"\n  Queries with zero recall (first relevant not found):")
        for r in failures:
            print(f"    [{r.query_id}] {r.description}")
            print(f"          Expected : {r.expected}")
            print(f"          Got      : {r.retrieved}")
    print()


def _to_json(report: EvalReport, thresholds: dict) -> dict:
    return {
        "k": report.k,
        "mean_precision_at_k": round(report.mean_precision, 4),
        "mean_recall_at_k": round(report.mean_recall, 4),
        "mrr": round(report.mrr, 4),
        "thresholds": thresholds,
        "pass": (
            report.mean_precision >= thresholds.get("precision_at_k", 0)
            and report.mean_recall >= thresholds.get("recall_at_k", 0)
            and report.mrr >= thresholds.get("mrr", 0)
        ),
        "per_query": [
            {
                "id": r.query_id,
                "description": r.description,
                "query": r.query,
                "expected": r.expected,
                "retrieved": r.retrieved,
                "precision_at_k": round(r.precision_at_k, 4),
                "recall_at_k": round(r.recall_at_k, 4),
                "reciprocal_rank": round(r.reciprocal_rank, 4),
            }
            for r in report.results
        ],
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate RAG retrieval quality.")
    parser.add_argument("--k", type=int, default=5, help="Number of results to retrieve per query (default: 5)")
    parser.add_argument("--golden", type=Path, default=GOLDEN_QA_PATH, help="Path to golden QA JSON file")
    parser.add_argument("--output", type=Path, default=None, help="Write JSON results to this file")
    parser.add_argument("--fail-below-threshold", action="store_true", help="Exit with code 1 if any metric is below its threshold")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    golden = json.loads(args.golden.read_text())
    thresholds = golden.get("thresholds", {})

    report = await evaluate(args.golden, k=args.k)
    _print_report(report, thresholds)

    result_json = _to_json(report, thresholds)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result_json, indent=2))
        print(f"Results written to {args.output}")

    # Clean up DB connections
    await engine.dispose()

    if args.fail_below_threshold and not result_json["pass"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
