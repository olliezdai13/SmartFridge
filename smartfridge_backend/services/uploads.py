"""Helpers for handling uploaded files."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .storage import S3SnapshotStorage


@dataclass(slots=True)
class StoredImage:
    """Metadata describing where the snapshot lives in object storage."""

    filename: str
    bucket: str
    key: str


def _build_unique_filename(original_name: str | None) -> str:
    safe_name = secure_filename(original_name or "snapshot") or "snapshot"
    suffix = Path(safe_name).suffix
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}{suffix}" if suffix else timestamp


def save_image_upload(
    image_file: FileStorage,
    storage: S3SnapshotStorage,
    *,
    user_id: str | int,
) -> Tuple[StoredImage, bytes]:
    """Persist an uploaded image to S3 and return metadata plus the raw bytes."""

    if image_file.filename == "":
        raise ValueError("empty filename")

    image_bytes = image_file.read()
    if not image_bytes:
        raise ValueError("uploaded file was empty")

    filename = _build_unique_filename(image_file.filename)

    key = storage.store_image_bytes(
        user_id=str(user_id),
        filename=filename,
        image_bytes=image_bytes,
        content_type=image_file.mimetype,
    )

    stored_image = StoredImage(
        filename=filename,
        bucket=storage.bucket,
        key=key,
    )
    return stored_image, image_bytes
