"""Endpoint that handles fridge snapshot uploads."""

from __future__ import annotations

from io import BytesIO
import mimetypes
import uuid

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    request,
    send_file,
    url_for,
)
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from smartfridge_backend.api.deps import get_db_session
from smartfridge_backend.models import (
    FridgeSnapshot,
    ProductCategory,
    SnapshotItem,
)
from smartfridge_backend.services.ingestion import create_snapshot_request
from smartfridge_backend.services.storage import (
    S3SnapshotStorage,
    SnapshotStorageError,
)
from smartfridge_backend.services.uploads import save_image_upload

bp = Blueprint("snapshot", __name__, url_prefix="/api")


def _get_snapshot_storage() -> S3SnapshotStorage:
    storage: S3SnapshotStorage | None = current_app.extensions.get(
        "snapshot_storage"
    )
    if storage is None:
        raise RuntimeError("snapshot storage client is not configured")
    return storage


def _serialize_snapshot(snapshot: FridgeSnapshot) -> dict[str, object]:
    contents = []
    for item in snapshot.items:
        product = item.product
        if product is None or not product.name:
            continue
        raw_category = (product.category or "").strip()
        normalized_category = raw_category.upper() if raw_category else None
        contents.append(
            {
                "name": product.name,
                "quantity": max(int(item.quantity), 1),
                "category": normalized_category,
                "categoryLabel": (
                    ProductCategory.key_value_map().get(normalized_category)
                    if normalized_category
                    else None
                ),
            }
        )

    return {
        "id": str(snapshot.id),
        "timestamp": snapshot.created_at.isoformat(),
        "imageUrl": url_for(
            "snapshot.get_snapshot_image",
            snapshot_id=str(snapshot.id),
            _external=True,
        ),
        "contents": contents,
    }


@bp.post("/snapshot")
def create_snapshot():
    """Accept a snapshot upload and store it in object storage."""

    if "image" not in request.files:
        return jsonify(error="missing file part 'image'"), 400

    image_file = request.files["image"]

    try:
        storage = _get_snapshot_storage()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user = getattr(g, "user", None)
    if user is None:
        return jsonify(error="unauthorized"), 401

    try:
        stored_image, _ = save_image_upload(
            image_file,
            storage,
            user_id=str(user.id),
        )
        snapshot = create_snapshot_request(
            session=session,
            user=user,
            stored_image=stored_image,
        )
        session.commit()
    except ValueError as exc:
        session.rollback()
        return jsonify(error=str(exc)), 400
    except SnapshotStorageError as exc:
        session.rollback()
        current_app.logger.exception("snapshot storage failure")
        return jsonify(error=str(exc)), 502
    except SQLAlchemyError:
        session.rollback()
        current_app.logger.exception("failed to enqueue snapshot")
        return jsonify(error="database failure while creating snapshot"), 500
    finally:
        session.close()

    return (
        jsonify(
            snapshot_id=str(snapshot.id),
            status=snapshot.status,
            bucket=stored_image.bucket,
            key=stored_image.key,
            filename=stored_image.filename,
        ),
        202,
    )


@bp.get("/snapshots")
def list_snapshots():
    """Return all snapshots for the authenticated user."""

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user_id = getattr(g, "user_id", None)
    if user_id is None:
        return jsonify(error="unauthorized"), 401

    raw_limit = request.args.get("limit", default=None, type=int)
    raw_offset = request.args.get("offset", default=None, type=int)
    limit = 5 if raw_limit is None else max(min(raw_limit, 50), 1)
    offset = 0 if raw_offset is None else max(raw_offset, 0)

    try:
        snapshot_rows = (
            session.execute(
                select(FridgeSnapshot)
                .options(
                    selectinload(FridgeSnapshot.items).selectinload(
                        SnapshotItem.product
                    )
                )
                .where(FridgeSnapshot.user_id == user_id)
                .order_by(
                    FridgeSnapshot.created_at.desc(), FridgeSnapshot.id.desc()
                )
                .offset(offset)
                .limit(limit + 1)
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError:
        current_app.logger.exception(
            "failed to load snapshots for user", extra={"user_id": str(user_id)}
        )
        return jsonify(error="failed to load snapshots"), 500
    finally:
        session.close()

    more_available = len(snapshot_rows) > limit
    limited_snapshots = snapshot_rows[:limit]
    next_offset = offset + len(limited_snapshots)

    return jsonify(
        snapshots=[
            _serialize_snapshot(snapshot) for snapshot in limited_snapshots
        ],
        hasMore=more_available,
        nextOffset=next_offset,
    )


@bp.get("/snapshots/<uuid:snapshot_id>/image")
def get_snapshot_image(snapshot_id: uuid.UUID):
    """Return the raw image bytes for a snapshot owned by the active user."""

    try:
        storage = _get_snapshot_storage()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user_id = getattr(g, "user_id", None)
    if user_id is None:
        return jsonify(error="unauthorized"), 401

    try:
        snapshot = (
            session.execute(
                select(FridgeSnapshot)
                .where(
                    FridgeSnapshot.id == snapshot_id,
                    FridgeSnapshot.user_id == user_id,
                )
                .limit(1)
            )
            .scalars()
            .first()
        )
    except SQLAlchemyError:
        current_app.logger.exception(
            "failed to load snapshot for image fetch",
            extra={"snapshot_id": str(snapshot_id), "user_id": str(user_id)},
        )
        return jsonify(error="failed to load snapshot"), 500
    finally:
        session.close()

    if snapshot is None:
        return jsonify(error="snapshot not found"), 404

    try:
        image_bytes = storage.fetch_image_bytes(
            bucket=snapshot.image_bucket,
            key=snapshot.image_key,
        )
    except SnapshotStorageError as exc:
        current_app.logger.exception(
            "failed to download snapshot image",
            extra={"snapshot_id": str(snapshot_id)},
        )
        return jsonify(error=str(exc)), 502

    mime_type, _ = mimetypes.guess_type(snapshot.image_filename)
    response = send_file(
        BytesIO(image_bytes),
        mimetype=mime_type or "application/octet-stream",
        download_name=snapshot.image_filename,
    )
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response
