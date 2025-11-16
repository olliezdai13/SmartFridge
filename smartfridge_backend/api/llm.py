"""Endpoints for interacting with the vision LLM."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from smartfridge_backend.services.llm import VisionLLMClient

bp = Blueprint("llm", __name__, url_prefix="/api")


def _resolve_image_path(image_name: str) -> Path:
    upload_dir: Path = current_app.config["UPLOAD_DIR"]
    candidate = (upload_dir / image_name).resolve()

    if not str(candidate).startswith(str(upload_dir.resolve())):
        raise ValueError("image_name must refer to a file inside the upload directory")

    return candidate


def _get_llm_client() -> VisionLLMClient:
    client: VisionLLMClient | None = current_app.extensions.get("vision_llm_client")
    if client is None:
        raise RuntimeError("vision LLM client is not configured")
    return client


@bp.post("/llm")
def invoke_llm():
    """Pass a stored image and prompt to the configured vision LLM."""
    payload = request.get_json(silent=True) or {}
    image_name = payload.get("image_name")
    prompt = payload.get("prompt")
    if isinstance(prompt, str):
        prompt = prompt.strip() or None

    if not image_name:
        return jsonify(error="image_name is required"), 400

    try:
        image_path = _resolve_image_path(image_name)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    if not image_path.exists() or not image_path.is_file():
        return jsonify(error=f"image '{image_name}' not found"), 404

    try:
        client = _get_llm_client()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    with image_path.open("rb") as fp:
        image_bytes = fp.read()

    mime_type, _ = mimetypes.guess_type(image_path.name)

    try:
        llm_result = client.analyze_image(
            image_bytes=image_bytes,
            prompt=prompt,
            mime_type=mime_type,
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:  # pragma: no cover - surface upstream errors
        current_app.logger.exception("vision LLM invocation failed")
        return jsonify(error="failed to query vision model"), 502

    response_payload: dict[str, object] = {"raw": llm_result.raw_text, "json": llm_result.parsed_json}
    if llm_result.parsed_json is not None:
        response_payload["result_json"] = llm_result.parsed_json

    return jsonify(response_payload)
