"""add auth columns and email normalization to users

Revision ID: 20240915_0004
Revises: 20241001_0005
Create Date: 2024-09-15 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240915_0004"
down_revision = "20241001_0005"
branch_labels = None
depends_on = None

DEMO_USER_PASSWORD_HASH = (
    "scrypt:32768:8:1$9UhdfW9nDT12TkmN$"
    "5e3c5a26098d0c9e4abc97bfe0caee5d9835699b7fba7892286f8bc99"
    "c7c03db1fe4f264481811c4dea47a546b832f3363c3fb44abd383ca4b"
    "f8787c5674dc1c"
)


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )

    op.execute(sa.text("UPDATE users SET email = LOWER(email)"))

    op.execute(
        sa.text(
            """
            UPDATE users
            SET password_hash = :password_hash
            WHERE password_hash IS NULL
            """
        ).bindparams(password_hash=DEMO_USER_PASSWORD_HASH)
    )

    op.drop_constraint("users_email_key", "users", type_="unique")
    op.create_index(
        "uq_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.drop_index("uq_users_email_lower", table_name="users")
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.drop_column("users", "updated_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "password_hash")
