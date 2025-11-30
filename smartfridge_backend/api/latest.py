"""Lightweight endpoint for summarizing the latest fridge data."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from smartfridge_backend.api.deps import (
    get_current_user_id,
    get_sessionmaker,
)
from smartfridge_backend.models import FridgeSnapshot
from smartfridge_backend.services.inventory import (
    InventoryItem,
    fetch_latest_items_for_user,
)

bp = Blueprint("latest", __name__, url_prefix="/api")


def _serialize_snapshot(snapshot: FridgeSnapshot | None) -> dict | None:
    if snapshot is None:
        return None
    return {
        "id": str(snapshot.id),
        "status": snapshot.status,
        "createdAt": snapshot.created_at.isoformat()
        if snapshot.created_at
        else None,
        "updatedAt": snapshot.updated_at.isoformat()
        if snapshot.updated_at
        else None,
        "image": {
            "bucket": snapshot.image_bucket,
            "key": snapshot.image_key,
            "filename": snapshot.image_filename,
        },
    }


@bp.get("/latest")
def get_latest_snapshot():
    """Return the most recent snapshot summary and normalized items."""

    try:
        session_factory = get_sessionmaker()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user_id = get_current_user_id()
    session = session_factory()
    try:
        snapshot = (
            session.execute(
                select(FridgeSnapshot)
                .where(FridgeSnapshot.user_id == user_id)
                .order_by(FridgeSnapshot.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        items: list[InventoryItem] = fetch_latest_items_for_user(
            session_factory, user_id=user_id
        )
    except SQLAlchemyError:
        current_app.logger.exception("failed to load latest snapshot")
        return jsonify(error="failed to load latest snapshot"), 500
    finally:
        session.close()

    return jsonify(
        latest=_serialize_snapshot(snapshot),
        items=items,
        itemCount=len(items),
    )
