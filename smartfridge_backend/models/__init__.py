"""SQLAlchemy models for SmartFridge."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class that configures UUID primary keys by default."""

    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
    }


class TimestampMixin:
    """Mixin that provides automatic creation timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    """A SmartFridge user that owns fridge snapshots."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))

    snapshots: Mapped[list["FridgeSnapshot"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Product(Base):
    """Normalized product catalog entries."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(120))
    unit: Mapped[Optional[str]] = mapped_column(String(32))
    aliases: Mapped[list[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False
    )
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )

    snapshot_items: Mapped[list["SnapshotItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class FridgeSnapshot(TimestampMixin, Base):
    """A single inference result captured for a user."""

    __tablename__ = "fridge_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    captured_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(64), default="llm", server_default=text("'llm'::text"), nullable=False
    )
    raw_response: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    user: Mapped[User] = relationship(back_populates="snapshots")
    items: Mapped[list["SnapshotItem"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class SnapshotItem(Base):
    """Normalized inventory record derived from a snapshot."""

    __tablename__ = "snapshot_items"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id", "product_id", "notes", name="uq_snapshot_item_product"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fridge_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("1.0")
    )
    unit: Mapped[Optional[str]] = mapped_column(String(32))
    confidence: Mapped[Optional[Float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    snapshot: Mapped[FridgeSnapshot] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="snapshot_items")


def get_database_url() -> str:
    """Return the configured DATABASE_URL."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    return database_url
