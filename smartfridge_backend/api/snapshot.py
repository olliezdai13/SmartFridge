"""Endpoint that handles fridge snapshot uploads."""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from smartfridge_backend.api.deps import get_db_session
from smartfridge_backend.models import FridgeSnapshot, SnapshotItem
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


def _build_image_url(
    snapshot: FridgeSnapshot, storage: S3SnapshotStorage
) -> str:
    try:
        return storage.build_image_url(
            bucket=snapshot.image_bucket, key=snapshot.image_key
        )
    except SnapshotStorageError:
        current_app.logger.exception(
            "failed to generate snapshot URL",
            extra={"snapshot_id": str(snapshot.id)},
        )
        return f"s3://{snapshot.image_bucket}/{snapshot.image_key}"


def _serialize_snapshot(
    snapshot: FridgeSnapshot, storage: S3SnapshotStorage
) -> dict[str, object]:
    contents = []
    for item in snapshot.items:
        product = item.product
        if product is None or not product.name:
            continue
        contents.append(
            {
                "name": product.name,
                "quantity": max(int(item.quantity), 1),
            }
        )

    return {
        "id": str(snapshot.id),
        "timestamp": snapshot.created_at.isoformat(),
        "imageUrl": _build_image_url(snapshot, storage),
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
        snapshots = (
            session.execute(
                select(FridgeSnapshot)
                .options(
                    selectinload(FridgeSnapshot.items).selectinload(
                        SnapshotItem.product
                    )
                )
                .where(FridgeSnapshot.user_id == user_id)
                .order_by(FridgeSnapshot.created_at.desc())
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

    return jsonify(
        snapshots=[
            _serialize_snapshot(snapshot, storage) for snapshot in snapshots
        ]
    )
