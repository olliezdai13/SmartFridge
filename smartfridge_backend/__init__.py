import os
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename


def create_app() -> Flask:
    """Application factory for the SmartFridge backend."""
    app = Flask(__name__)

    upload_dir = Path(
        os.environ.get("SMARTFRIDGE_UPLOAD_DIR", "data/uploads")
    ).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_DIR"] = upload_dir

    @app.get("/healthz")
    def healthcheck():
        return jsonify(status="ok")

    @app.post("/api/images")
    def upload_image():
        """Receive an image upload from the Raspberry Pi client."""
        if "image" not in request.files:
            return jsonify(error="missing file part 'image'"), 400

        image_file = request.files["image"]
        if image_file.filename == "":
            return jsonify(error="empty filename"), 400

        safe_name = secure_filename(image_file.filename) or "upload"
        stem = Path(safe_name).stem or "upload"
        suffix = Path(safe_name).suffix
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        filename = f"{stem}_{timestamp}{suffix}" if suffix else f"{stem}_{timestamp}"

        destination = app.config["UPLOAD_DIR"] / filename
        image_file.save(destination)

        return (
            jsonify(filename=filename, upload_dir=str(app.config["UPLOAD_DIR"])),
            201,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
