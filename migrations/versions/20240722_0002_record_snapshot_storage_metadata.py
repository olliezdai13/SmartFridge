"""record snapshot storage metadata

Revision ID: 20240722_0002
Revises: 20240718_0001
Create Date: 2024-07-22 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240722_0002"
down_revision = "20240718_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fridge_snapshots",
        sa.Column("image_bucket", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "fridge_snapshots",
        sa.Column("image_key", sa.String(length=512), nullable=False),
    )
    op.add_column(
        "fridge_snapshots",
        sa.Column("image_filename", sa.String(length=255), nullable=False),
    )
    op.drop_column("fridge_snapshots", "captured_at")
    op.drop_column("fridge_snapshots", "source")
    op.drop_column("fridge_snapshots", "raw_response")

    op.add_column(
        "snapshot_items",
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("snapshot_items", "raw_payload")

    op.add_column(
        "fridge_snapshots",
        sa.Column(
            "raw_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "fridge_snapshots",
        sa.Column(
            "source",
            sa.String(length=64),
            server_default=sa.text("'llm'::text"),
            nullable=False,
        ),
    )
    op.add_column(
        "fridge_snapshots",
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.drop_column("fridge_snapshots", "image_filename")
    op.drop_column("fridge_snapshots", "image_key")
    op.drop_column("fridge_snapshots", "image_bucket")
