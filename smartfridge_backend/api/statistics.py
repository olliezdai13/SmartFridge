"""Analytics endpoints for historical fridge data."""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from smartfridge_backend.api.deps import get_db_session
from smartfridge_backend.models import (
    FridgeSnapshot,
    ProductCategory,
    SnapshotItem,
)

bp = Blueprint("statistics", __name__, url_prefix="/api/statistics")


def _normalize_category_key(raw_category: str | None) -> str:
    normalized = (raw_category or "").strip().upper()
    if normalized in ProductCategory.keys():
        return normalized
    return "OTHER"


@bp.get("/ingredient_composition")
def ingredient_composition():
    """Return per-snapshot counts of items grouped by category."""

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user_id = getattr(g, "user_id", None)
    if user_id is None:
        return jsonify(error="unauthorized"), 401

    try:
        snapshots = (
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
                .order_by(
                    FridgeSnapshot.created_at.asc(), FridgeSnapshot.id.asc()
                )
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception(
            "failed to load snapshots for ingredient composition statistics",
            extra={"user_id": str(user_id)},
        )
        return jsonify(error="failed to load snapshot history"), 500
    finally:
        session.close()

    category_labels = ProductCategory.key_value_map()
    category_keys = list(category_labels.keys())

    payload_snapshots = []
    for snapshot in snapshots:
        category_counts = {key: 0 for key in category_keys}

        for item in snapshot.items:
            product = item.product
            if product is None:
                continue

            category_key = _normalize_category_key(product.category)
            quantity = max(int(item.quantity), 1)
            category_counts[category_key] = (
                category_counts.get(category_key, 0) + quantity
            )

        payload_snapshots.append(
            {
                "snapshotId": str(snapshot.id),
                "timestamp": snapshot.created_at.isoformat(),
                "categoryCounts": [
                    {
                        "category": key,
                        "label": category_labels.get(key),
                        "count": category_counts.get(key, 0),
                    }
                    for key in category_keys
                ],
                "totalItems": sum(category_counts.values()),
            }
        )

    return jsonify(
        categoryLabels=category_labels,
        snapshots=payload_snapshots,
    )
