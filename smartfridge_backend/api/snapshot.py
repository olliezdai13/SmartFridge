"""Endpoint that handles fridge snapshots end-to-end."""

from __future__ import annotations

import json
import mimetypes

from flask import Blueprint, current_app, jsonify, request

from smartfridge_backend.services.llm import VisionLLMClient
from smartfridge_backend.services.storage import (
    S3SnapshotStorage,
    SnapshotStorageError,
)
from smartfridge_backend.services.uploads import save_image_upload

bp = Blueprint("snapshot", __name__, url_prefix="/api")


def _get_llm_client() -> VisionLLMClient:
    client: VisionLLMClient | None = current_app.extensions.get(
        "vision_llm_client"
    )
    if client is None:
        raise RuntimeError("vision LLM client is not configured")
    return client


def _get_snapshot_storage() -> S3SnapshotStorage:
    storage: S3SnapshotStorage | None = current_app.extensions.get(
        "snapshot_storage"
    )
    if storage is None:
        raise RuntimeError("snapshot storage client is not configured")
    return storage


def _extract_prompt() -> str | None:
    prompt = request.form.get("prompt")
    if not prompt:
        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt") if isinstance(payload, dict) else None
    if isinstance(prompt, str):
        prompt = prompt.strip() or None
    else:
        prompt = None
    return prompt


def _placeholder_pipeline_step(_: dict[str, object]) -> dict[str, str]:
    """Temporary stand-in for the forthcoming data-cleaning pipeline."""

    return {
        "status": "pending",
        "detail": "Data cleaning pipeline not implemented yet.",
    }


@bp.post("/snapshot")
def create_snapshot():
    """Accept a single request that uploads an image and runs the vision LLM."""

    if "image" not in request.files:
        return jsonify(error="missing file part 'image'"), 400

    image_file = request.files["image"]

    try:
        storage = _get_snapshot_storage()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        stored_image, image_bytes = save_image_upload(
            image_file,
            storage,
            user_id=1,
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except SnapshotStorageError as exc:
        current_app.logger.exception("snapshot storage failure")
        return jsonify(error=str(exc)), 502

    try:
        client = _get_llm_client()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    mime_type, _ = mimetypes.guess_type(stored_image.filename)

    prompt = _extract_prompt()

    try:
        llm_result = client.analyze_image(
            image_bytes=image_bytes,
            prompt=prompt,
            mime_type=mime_type,
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:  # pragma: no cover - surface upstream errors
        current_app.logger.exception("vision LLM invocation failed")
        return jsonify(error="failed to query vision model"), 502

    llm_payload: dict[str, object] = {
        "raw": llm_result.raw_text,
        "json": llm_result.parsed_json,
    }
    if llm_result.parsed_json is not None:
        llm_payload["result_json"] = llm_result.parsed_json

    pipeline_status = _placeholder_pipeline_step(llm_payload)

    response_payload = {
        "snapshot": {
            "filename": stored_image.filename,
            "bucket": stored_image.bucket,
            "key": stored_image.key,
        },
        "llm": llm_payload,
        "pipeline": pipeline_status,
    }

    return current_app.response_class(
        json.dumps(response_payload, indent=2) + "\n",
        status=201,
        mimetype="application/json",
    )
