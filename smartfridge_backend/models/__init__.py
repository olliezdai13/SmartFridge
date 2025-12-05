"""SQLAlchemy models for SmartFridge."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
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
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )

    snapshots: Mapped[list["FridgeSnapshot"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Product(Base):
    """Normalized product catalog entries."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(120))
    unit: Mapped[Optional[str]] = mapped_column(String(32))

    snapshot_items: Mapped[list["SnapshotItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )


class ProductCategory(str, Enum):
    """Supported food group buckets for products."""

    FRUITS_VEGETABLES = "Vegetables, salad and fruit"
    GRAINS_STARCH = "Wholemeal cereals and breads, potatoes, pasta and rice"
    DAIRY = "Milk, yogurt and cheese"
    PROTEIN_FOODS = "Meat, poultry, fish, eggs, beans and nuts"
    FATS_OILS = "Fats, spreads and oils"
    PROCESSED_FOODS = "Processed foods, drinks"
    OTHER = "Other"

    @classmethod
    def values(cls) -> set[str]:
        return {entry.value for entry in cls}

    @classmethod
    def key_value_map(cls) -> dict[str, str]:
        """Return a mapping of enum member names to their display values."""
        return {entry.name: entry.value for entry in cls}

    @classmethod
    def keys(cls) -> set[str]:
        return {entry.name for entry in cls}


class FridgeSnapshot(TimestampMixin, Base):
    """A single inference result captured for a user."""

    __tablename__ = "snapshots"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending','processing','complete','failed')",
            name="ck_snapshots_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    image_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    image_key: Mapped[str] = mapped_column(String(512), nullable=False)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_llm_output: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[Literal["pending", "processing", "complete", "failed"]] = (
        mapped_column(String(32), nullable=False, default="pending")
    )
    error: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="snapshots")
    items: Mapped[list["SnapshotItem"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


class SnapshotItem(Base):
    """Normalized inventory record derived from a snapshot."""

    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id", "product_id", name="uq_item_product"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("1.0")
    )
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)

    snapshot: Mapped[FridgeSnapshot] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="snapshot_items")


class Job(Base):
    """Lightweight job row for async snapshot processing."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "job_type",
            "snapshot_id",
            name="uq_jobs_snapshot_job_type",
        ),
        CheckConstraint(
            "status in ('queued','running','done','failed')",
            name="ck_jobs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("snapshots.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[Literal["queued", "running", "done", "failed"]] = (
        mapped_column(String(32), nullable=False, default="queued")
    )
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    run_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_by: Mapped[Optional[str]] = mapped_column(String(64))
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    snapshot: Mapped[FridgeSnapshot] = relationship()


def get_database_url() -> str:
    """Return the configured DATABASE_URL."""

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    # Normalize common Postgres URL forms to the installed psycopg v3 driver.
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://") :]
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://") :]
    if database_url.startswith("postgresql+psycopg2://"):
        return (
            "postgresql+psycopg://"
            + database_url[len("postgresql+psycopg2://") :]
        )

    return database_url
