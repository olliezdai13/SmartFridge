"""cleanup schema naming and product/item columns

Revision ID: 20240908_0003
Revises: 20240722_0002
Create Date: 2024-09-08 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240908_0003"
down_revision = "20240722_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("fridge_snapshots", "snapshots")
    op.rename_table("snapshot_items", "items")

    op.drop_constraint("uq_snapshot_item_product", "items", type_="unique")
    op.drop_column("items", "unit")
    op.drop_column("items", "confidence")
    op.drop_column("items", "notes")
    op.create_unique_constraint(
        "uq_item_product", "items", ["snapshot_id", "product_id"]
    )

    op.drop_constraint("products_slug_key", "products", type_="unique")
    op.drop_column("products", "slug")
    op.drop_column("products", "aliases")
    op.drop_column("products", "extra_metadata")
    op.create_unique_constraint("uq_product_name", "products", ["name"])


def downgrade() -> None:
    op.drop_constraint("uq_product_name", "products", type_="unique")
    op.add_column(
        "products",
        sa.Column(
            "extra_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("slug", sa.String(length=150), nullable=True),
    )
    op.create_unique_constraint("products_slug_key", "products", ["slug"])

    op.drop_constraint("uq_item_product", "items", type_="unique")
    op.add_column(
        "items",
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("unit", sa.String(length=32), nullable=True),
    )
    op.create_unique_constraint(
        "uq_snapshot_item_product",
        "items",
        ["snapshot_id", "product_id", "notes"],
    )

    op.rename_table("items", "snapshot_items")
    op.rename_table("snapshots", "fridge_snapshots")
