"""Endpoint that handles fridge snapshot uploads."""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from smartfridge_backend.api.deps import get_db_session
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
