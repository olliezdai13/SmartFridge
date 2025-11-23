"""add raw llm output to snapshots

Revision ID: 20240910_0004
Revises: 20240908_0003
Create Date: 2024-09-10 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240910_0004"
down_revision = "20240908_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "snapshots",
        sa.Column("raw_llm_output", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("snapshots", "raw_llm_output")
