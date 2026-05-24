"""
Generate OpenAI embeddings for recipes and store them in Postgres.

Usage:
    python scripts/embed_recipes.py
    python scripts/embed_recipes.py --force
    python scripts/embed_recipes.py --batch-size 32
    python scripts/embed_recipes.py --batch-size 16 --sleep 2.0

Changes from v1:
  - Uses AsyncOpenAI (non-blocking; doesn't stall the event loop).
  - Retries each batch up to 5 times with exponential back-off on rate-limit
    (429) and transient server errors (5xx / timeout).
  - Optional --sleep between batches to stay within free-tier TPM limits.
  - Clearer progress output with percentage and per-batch timing.
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path / env bootstrap (must happen before any app import)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # noqa: E402

_api_root = Path(__file__).parent.parent
load_dotenv(_api_root / ".env", override=True)
try:
    _root_env = _api_root.parents[1] / ".env"
    if _root_env.exists():
        load_dotenv(_root_env, override=False)
except IndexError:
    pass

from app.core.config import settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.recipe import Recipe  # noqa: E402
from app.observability.logging import get_logger  # noqa: E402
from app.services.recipe_text_service import build_searchable_text  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------

_RETRY_EXCEPTIONS = ("RateLimitError", "APITimeoutError", "APIConnectionError",
                     "InternalServerError")
_MAX_RETRIES = 5
_BASE_BACKOFF = 2.0  # seconds


async def _embed_with_retry(client, model: str, texts: list[str]) -> list:
    """Call embeddings.create with exponential back-off on transient errors."""
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = await client.embeddings.create(model=model, input=texts)
            return resp.data
        except Exception as exc:
            exc_type = type(exc).__name__
            is_retryable = any(name in exc_type for name in _RETRY_EXCEPTIONS)
            if not is_retryable or attempt == _MAX_RETRIES:
                raise
            wait = _BASE_BACKOFF * (2 ** (attempt - 1))
            print(
                f"\n  [{exc_type}] Attempt {attempt}/{_MAX_RETRIES} failed — "
                f"retrying in {wait:.0f}s…",
                flush=True,
            )
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")  # pragma: no cover


# ---------------------------------------------------------------------------
# Main embedding logic
# ---------------------------------------------------------------------------

async def embed_recipes(force: bool, batch_size: int, sleep_between: float) -> int:
    if not settings.OPENAI_API_KEY:
        print(
            "ERROR: OPENAI_API_KEY is not set. "
            "Add it to apps/api/.env before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("ERROR: 'openai' package is not installed.", file=sys.stderr)
        sys.exit(1)

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=60.0,
    )
    model = settings.EMBEDDING_MODEL

    async with AsyncSessionLocal() as session:
        stmt = select(Recipe).options(selectinload(Recipe.ingredients))
        if not force:
            stmt = stmt.where(Recipe.embedding.is_(None))

        result = await session.execute(stmt)
        recipes = result.scalars().all()

        total = len(recipes)
        if total == 0:
            print("All recipes already have embeddings. Use --force to re-embed.")
            return 0

        num_batches = (total + batch_size - 1) // batch_size
        print(
            f"Embedding {total} recipe(s) — "
            f"model={model}, batch_size={batch_size}, batches={num_batches}"
        )
        if sleep_between:
            print(f"Sleeping {sleep_between}s between batches (rate-limit guard).")
        print()

        embedded = 0
        for batch_num, start in enumerate(range(0, total, batch_size), start=1):
            batch = recipes[start : start + batch_size]
            texts = [build_searchable_text(r) for r in batch]

            t0 = time.monotonic()
            print(
                f"  Batch {batch_num}/{num_batches} "
                f"({len(batch)} recipes, {embedded}/{total} done)…",
                end=" ",
                flush=True,
            )

            data = await _embed_with_retry(client, model, texts)

            for recipe, item in zip(batch, data):
                recipe.embedding = item.embedding
                embedded += 1

            await session.commit()
            elapsed = time.monotonic() - t0
            pct = 100 * embedded / total
            print(f"done in {elapsed:.1f}s  [{pct:.0f}%]")

            if sleep_between and batch_num < num_batches:
                await asyncio.sleep(sleep_between)

    print(f"\nFinished. {embedded}/{total} recipe(s) embedded.")
    return embedded


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate recipe embeddings.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed all recipes, including those that already have embeddings.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Recipes per API call (default: 32). Reduce if hitting token limits.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        dest="sleep_between",
        metavar="SECONDS",
        help="Sleep between batches to avoid rate limits (default: 0.5s).",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    try:
        await embed_recipes(
            force=args.force,
            batch_size=args.batch_size,
            sleep_between=args.sleep_between,
        )
    except KeyboardInterrupt:
        print("\nInterrupted. Progress up to the last committed batch is saved.")
        sys.exit(130)
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    asyncio.run(main())
