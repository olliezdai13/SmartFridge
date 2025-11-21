import os

from flask import Flask, jsonify

from smartfridge_backend.api import init_app as init_api
from smartfridge_backend.services.llm import (
    VisionLLMSettings,
    init_vision_llm_client,
)
from smartfridge_backend.services.storage import (
    SnapshotStorageSettings,
    init_snapshot_storage,
)


def create_app() -> Flask:
    """Application factory for the SmartFridge backend."""
    app = Flask(__name__)

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

    llm_api_key = os.environ.get("SMARTFRIDGE_LLM_API_KEY") or os.environ.get(
        "OPENAI_API_KEY"
    )
    llm_model = os.environ.get("SMARTFRIDGE_LLM_MODEL", "gpt-4o-mini")
    llm_system_prompt = os.environ.get("SMARTFRIDGE_LLM_SYSTEM_PROMPT")

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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
