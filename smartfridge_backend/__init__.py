import os
from pathlib import Path

from flask import Flask, jsonify

from smartfridge_backend.api import init_app as init_api


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

    init_api(app)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
