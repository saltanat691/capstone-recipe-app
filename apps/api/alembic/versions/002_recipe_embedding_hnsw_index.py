"""Add HNSW index on recipes.embedding for cosine similarity

Revision ID: 002_recipe_embedding_hnsw_index
Revises: 001_initial
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "002_recipe_embedding_hnsw_index"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_recipes_embedding_hnsw "
        "ON recipes USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_recipes_embedding_hnsw")