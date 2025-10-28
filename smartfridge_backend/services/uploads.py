"""Helpers for handling uploaded files."""

from datetime import datetime
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


def save_image_upload(image_file: FileStorage, upload_dir: Path) -> Path:
    """Persist an uploaded image to disk and return its destination path."""
    if image_file.filename == "":
        raise ValueError("empty filename")

    safe_name = secure_filename(image_file.filename) or "upload"
    stem = Path(safe_name).stem or "upload"
    suffix = Path(safe_name).suffix
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{stem}_{timestamp}{suffix}" if suffix else f"{stem}_{timestamp}"

    destination = upload_dir / filename
    image_file.save(destination)
    return destination
