"""
Generate OpenAI embeddings for recipes and store them in Postgres.

Usage:
    python scripts/embed_recipes.py
    python scripts/embed_recipes.py --force
    python scripts/embed_recipes.py --batch-size 32
"""

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from the api directory before importing settings
load_dotenv(Path(__file__).parent.parent / ".env")

from app.core.config import settings  # noqa: E402
from app.db.session import AsyncSessionLocal  # noqa: E402
from app.models.recipe import Recipe  # noqa: E402
from app.observability.logging import get_logger  # noqa: E402
from app.services.recipe_text_service import build_searchable_text  # noqa: E402

logger = get_logger(__name__)


def _build_openai_client():
    if not settings.OPENAI_API_KEY:
        print(
            "ERROR: OPENAI_API_KEY is not set. "
            "Add it to apps/api/.env before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from openai import OpenAI
    except ImportError:
        print(
            "ERROR: 'openai' package is not installed. "
            "Run: pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    return OpenAI(api_key=settings.OPENAI_API_KEY)


async def embed_recipes(force: bool, batch_size: int) -> int:
    client = _build_openai_client()
    model = settings.EMBEDDING_MODEL

    async with AsyncSessionLocal() as session:
        stmt = select(Recipe).options(selectinload(Recipe.ingredients))
        if not force:
            stmt = stmt.where(Recipe.embedding.is_(None))

        result = await session.execute(stmt)
        recipes = result.scalars().all()

        total = len(recipes)
        if total == 0:
            logger.info("No recipes need embedding.")
            return 0

        logger.info(
            f"Embedding {total} recipe(s) with model '{model}' "
            f"(batch_size={batch_size}, force={force})"
        )

        embedded = 0
        for start in range(0, total, batch_size):
            batch = recipes[start : start + batch_size]
            texts = [build_searchable_text(r) for r in batch]

            response = client.embeddings.create(model=model, input=texts)

            for recipe, item in zip(batch, response.data):
                recipe.embedding = item.embedding
                embedded += 1

            await session.commit()
            logger.info(f"Embedded {embedded}/{total}")

        return embedded


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate recipe embeddings.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed all recipes, including those that already have embeddings.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of recipes per OpenAI embeddings API call (default: 64).",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    try:
        count = await embed_recipes(force=args.force, batch_size=args.batch_size)
    except KeyboardInterrupt:
        logger.info("Embedding interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise

    print(f"Embedded {count} recipe(s).")


if __name__ == "__main__":
    asyncio.run(main())