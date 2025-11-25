"""Endpoint that handles fridge snapshot uploads."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from smartfridge_backend.services.storage import (
    S3SnapshotStorage,
    SnapshotStorageError,
)
from smartfridge_backend.services.uploads import save_image_upload
from smartfridge_backend.services.users import DEFAULT_USER_ID

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
        stored_image, _ = save_image_upload(
            image_file,
            storage,
            user_id=str(DEFAULT_USER_ID),
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except SnapshotStorageError as exc:
        current_app.logger.exception("snapshot storage failure")
        return jsonify(error=str(exc)), 502

    return (
        jsonify(
            bucket=stored_image.bucket,
            key=stored_image.key,
            filename=stored_image.filename,
        ),
        201,
    )
