"""add password hash and session version to users

Revision ID: 20241015_0006
Revises: 20241001_0005
Create Date: 2024-10-15 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

# revision identifiers, used by Alembic.
revision = "20241015_0006"
down_revision = "20241001_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "session_version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    bind = op.get_bind()
    default_hash = generate_password_hash("changeme")
    bind.execute(
        sa.text(
            "update users set password_hash = :password_hash where password_hash is null"
        ),
        {"password_hash": default_hash},
    )
    bind.execute(
        sa.text(
            "update users set session_version = 1 where session_version is null"
        )
    )

    op.alter_column("users", "password_hash", nullable=False)
    op.alter_column(
        "users",
        "session_version",
        nullable=False,
        server_default=sa.text("1"),
    )


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "session_version")
    op.drop_column("users", "password_hash")
