import logging
import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from smartfridge_backend.api import init_app as init_api
from smartfridge_backend.config import (
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_SYSTEM_PROMPT,
)
from smartfridge_backend.models import get_database_url
from smartfridge_backend.services.llm import (
    VisionLLMSettings,
    init_vision_llm_client,
)
from smartfridge_backend.services.worker import SnapshotJobWorker, WorkerSettings
from smartfridge_backend.services.storage import (
    SnapshotStorageSettings,
    init_snapshot_storage,
)

FRONTEND_DIST_DIR = (
    Path(__file__).resolve().parent.parent / "smartfridge_frontend" / "dist"
)


def create_app() -> Flask:
    """Application factory for the SmartFridge backend."""
    app = Flask(__name__)

    app.config["API_SHARED_SECRET"] = os.environ.get(
        "SMARTFRIDGE_API_SHARED_SECRET"
    )

    _configure_logging(app)
    _init_database(app)

    storage_bucket = os.environ.get("SMARTFRIDGE_S3_BUCKET")
    if storage_bucket:
        storage_settings = SnapshotStorageSettings(
            bucket=storage_bucket,
            region_name=os.environ.get("SMARTFRIDGE_S3_REGION"),
            endpoint_url=os.environ.get("SMARTFRIDGE_S3_ENDPOINT_URL"),
            base_prefix=os.environ.get("SMARTFRIDGE_S3_BASE_PREFIX", "snapshots"),
            access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        app.extensions["snapshot_storage"] = init_snapshot_storage(
            storage_settings
        )
    else:
        app.logger.warning(
            "SMARTFRIDGE_S3_BUCKET not set; snapshot storage disabled"
        )

    @app.get("/healthz")
    def healthcheck():
        return jsonify(status="ok")

    @app.get("/api/healthz")
    def api_healthcheck():
        return jsonify(status="ok")

    llm_api_key = os.environ.get("SMARTFRIDGE_LLM_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    llm_model = os.environ.get("SMARTFRIDGE_LLM_MODEL", DEFAULT_LLM_MODEL)
    llm_system_prompt = os.environ.get(
        "SMARTFRIDGE_LLM_SYSTEM_PROMPT", DEFAULT_LLM_SYSTEM_PROMPT
    )

    if llm_api_key:
        app.extensions["vision_llm_client"] = init_vision_llm_client(
            VisionLLMSettings(
                api_key=llm_api_key,
                model=llm_model,
                system_prompt=llm_system_prompt or None,
            )
        )
    else:
        app.logger.warning(
            "SMARTFRIDGE_LLM_API_KEY/OPENAI_API_KEY not set; vision LLM endpoint disabled"
        )

    init_api(app)
    _maybe_start_worker(app)
    _register_frontend(app)

    return app


def _configure_logging(app: Flask) -> None:
    """Ensure application and root loggers emit INFO-level logs."""

    logging.basicConfig(level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)


def _init_database(app: Flask) -> None:
    """Configure the SQLAlchemy session factory for request handlers."""

    try:
        database_url = get_database_url()
    except RuntimeError:
        app.logger.warning(
            "DATABASE_URL not set; database-backed features disabled"
        )
        return

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    app.extensions["db_engine"] = engine
    app.extensions["db_sessionmaker"] = SessionLocal


def _maybe_start_worker(app: Flask) -> None:
    """Start the background snapshot worker when dependencies are available."""

    concurrency_env = os.environ.get("WORKER_CONCURRENCY", "1")
    try:
        concurrency = int(concurrency_env)
    except ValueError:
        app.logger.warning(
            "snapshot worker disabled: invalid WORKER_CONCURRENCY=%s",
            concurrency_env,
        )
        return

    if concurrency <= 0:
        app.logger.info("snapshot worker disabled (concurrency=%s)", concurrency)
        return

    sessionmaker = app.extensions.get("db_sessionmaker")
    storage = app.extensions.get("snapshot_storage")
    llm_client = app.extensions.get("vision_llm_client")

    if not sessionmaker or not storage or not llm_client:
        app.logger.info(
            "snapshot worker not started; missing dependencies",
            extra={
                "sessionmaker": bool(sessionmaker),
                "storage": bool(storage),
                "llm_client": bool(llm_client),
            },
        )
        return

    worker = SnapshotJobWorker(
        session_factory=sessionmaker,
        storage=storage,
        llm_client=llm_client,
        settings=WorkerSettings(),
    )
    app.logger.info(
        "starting snapshot worker", extra={"concurrency": concurrency}
    )
    worker.start(concurrency=concurrency)
    app.extensions["snapshot_worker"] = worker


def _register_frontend(app: Flask) -> None:
    """Serve the built frontend bundle when available."""

    if not FRONTEND_DIST_DIR.exists():
        app.logger.warning(
            "frontend bundle missing; UI routes will return 404",
            extra={"path": str(FRONTEND_DIST_DIR)},
        )
        return

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def _serve_frontend(path: str):
        asset_path = FRONTEND_DIST_DIR / path
        if path and asset_path.exists():
            return send_from_directory(FRONTEND_DIST_DIR, path)

        return send_from_directory(FRONTEND_DIST_DIR, "index.html")


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
