"""Add api_keys table and expires_at retention columns

Revision ID: 003_auth_and_retention
Revises: 002_recipe_embedding_hnsw_index
Create Date: 2026-05-23

Changes:
  - New table: api_keys (hashed keys, owner, consent flag, expiry)
  - agent_runs.expires_at       — nullable timestamp for retention cleanup
  - user_preferences.expires_at — nullable timestamp for retention cleanup
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_auth_and_retention"
down_revision: Union[str, None] = "002_recipe_embedding_hnsw_index"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- api_keys ----------------------------------------------------------
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("tracing_consent", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_keys_id"), "api_keys", ["id"], unique=False)
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_owner_id"), "api_keys", ["owner_id"], unique=False)
    op.create_index(op.f("ix_api_keys_is_active"), "api_keys", ["is_active"], unique=False)

    # ---- retention columns -------------------------------------------------
    op.add_column(
        "agent_runs",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_agent_runs_expires_at", "agent_runs", ["expires_at"], unique=False
    )

    op.add_column(
        "user_preferences",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_user_preferences_expires_at",
        "user_preferences",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_preferences_expires_at", table_name="user_preferences")
    op.drop_column("user_preferences", "expires_at")

    op.drop_index("ix_agent_runs_expires_at", table_name="agent_runs")
    op.drop_column("agent_runs", "expires_at")

    op.drop_index(op.f("ix_api_keys_is_active"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_owner_id"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_key_hash"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_id"), table_name="api_keys")
    op.drop_table("api_keys")
