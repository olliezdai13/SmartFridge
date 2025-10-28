"""Image upload endpoints."""

from flask import Blueprint, current_app, jsonify, request

from smartfridge_backend.services.uploads import save_image_upload

bp = Blueprint("images", __name__, url_prefix="/api")


@bp.post("/images")
def upload_image():
    """Receive an image upload from the Raspberry Pi client."""
    if "image" not in request.files:
        return jsonify(error="missing file part 'image'"), 400

    image_file = request.files["image"]

    try:
        destination = save_image_upload(
            image_file, current_app.config["UPLOAD_DIR"]
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    return (
        jsonify(filename=destination.name, upload_dir=str(destination.parent)),
        201,
    )
