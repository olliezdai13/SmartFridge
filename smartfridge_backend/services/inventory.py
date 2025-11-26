"""Helpers for working with fridge inventory records."""

from __future__ import annotations

import uuid
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload, sessionmaker

from smartfridge_backend.models import FridgeSnapshot, SnapshotItem


class InventoryItem(TypedDict):
    """Latest normalized inventory entry for a user."""

    name: str
    quantity: int


def fetch_latest_items_for_user(
    session_factory: sessionmaker, *, user_id: uuid.UUID
) -> list[InventoryItem]:
    """Return the most recent snapshot items for the given user.

    Items are returned as JSON-safe dicts with ``name`` and ``quantity`` keys.
    When the user has never taken a snapshot, an empty list is returned.
    """

    session: Session = session_factory()
    try:
        snapshot = (
            session.execute(
                select(FridgeSnapshot)
                .options(
                    selectinload(FridgeSnapshot.items).selectinload(
                        SnapshotItem.product
                    )
                )
                .where(
                    FridgeSnapshot.user_id == user_id,
                    FridgeSnapshot.status == "complete",
                )
                # Order by creation time so we pick the newest snapshot even if an older
                # one finished processing later and has a later updated_at timestamp.
                .order_by(FridgeSnapshot.created_at.desc())
            )
            .scalars()
            .first()
        )

        if snapshot is None:
            return []

        items: list[InventoryItem] = []
        for item in snapshot.items:
            product = item.product
            if product is None or not product.name:
                continue
            items.append(
                {
                    "name": product.name,
                    # Snapshot quantities are persisted as whole numbers.
                    "quantity": max(int(item.quantity), 1),
                }
            )
        return items
    finally:
        session.close()
