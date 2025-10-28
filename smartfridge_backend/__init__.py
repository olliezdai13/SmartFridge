import os
from pathlib import Path

from flask import Flask, jsonify

from smartfridge_backend.api import init_app as init_api
from smartfridge_backend.services.llm import (
    VisionLLMSettings,
    init_vision_llm_client,
)


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
