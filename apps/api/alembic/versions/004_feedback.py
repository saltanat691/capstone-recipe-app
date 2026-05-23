"""Add feedback table for quality ratings

Revision ID: 004_feedback
Revises: 003_auth_and_retention
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_feedback"
down_revision: Union[str, None] = "003_auth_and_retention"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=200), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.String(length=200), nullable=True),
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
    op.create_index(op.f("ix_feedback_id"), "feedback", ["id"], unique=False)
    op.create_index(op.f("ix_feedback_trace_id"), "feedback", ["trace_id"], unique=False)
    op.create_index(op.f("ix_feedback_owner_id"), "feedback", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_owner_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_trace_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_id"), table_name="feedback")
    op.drop_table("feedback")
