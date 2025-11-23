"""Endpoint that handles fridge snapshots end-to-end."""

from __future__ import annotations

import mimetypes
import uuid
from typing import Any

from httpx import RequestError, TimeoutException
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from smartfridge_backend.api.deps import get_db_session
from smartfridge_backend.models import (
    FridgeSnapshot,
    Product,
    SnapshotItem,
    User,
)
from smartfridge_backend.services.llm import VisionLLMClient
from smartfridge_backend.services.normalization import normalize_product_name
from smartfridge_backend.services.storage import (
    S3SnapshotStorage,
    SnapshotStorageError,
)
from smartfridge_backend.services.uploads import StoredImage, save_image_upload
from smartfridge_backend.services.users import (
    DEFAULT_USER_ID,
    get_or_create_default_user,
)

bp = Blueprint("snapshot", __name__, url_prefix="/api")

_MAX_RAW_LLM_OUTPUT_BYTES = 16_000
_TRUNCATION_SUFFIX = " [truncated]"


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


def _get_or_create_request_user(session: Session) -> User:
    """Return the active user (placeholder until auth lands)."""

    return get_or_create_default_user(session)


def _add_snapshot_metadata(
    *,
    session: Session,
    user: User,
    stored_image: StoredImage,
) -> FridgeSnapshot:
    """Add a snapshot row to the session and flush so it has an id."""

    snapshot = FridgeSnapshot(
        user_id=user.id,
        image_bucket=stored_image.bucket,
        image_key=stored_image.key,
        image_filename=stored_image.filename,
    )
    session.add(snapshot)
    session.flush()
    return snapshot


_DEFAULT_ITEM_QUANTITY = 1


def _parse_quantity(value: object) -> int:
    """Return a positive integer quantity derived from arbitrary input."""

    if value is None:
        return _DEFAULT_ITEM_QUANTITY
    quantity: int | None = None
    if isinstance(value, bool):
        quantity = int(value)
    elif isinstance(value, int):
        quantity = value
    elif isinstance(value, float):
        quantity = int(value)
    elif isinstance(value, str):
        candidate = value.strip()
        if candidate:
            try:
                quantity = int(candidate)
            except ValueError:
                try:
                    quantity = int(float(candidate))
                except ValueError:
                    quantity = None
    if quantity is None:
        return _DEFAULT_ITEM_QUANTITY
    return quantity if quantity > 0 else _DEFAULT_ITEM_QUANTITY


def _get_or_create_product(session: Session, name: str) -> Product:
    product = session.execute(
        select(Product).where(Product.name == name)
    ).scalar_one_or_none()
    if product is None:
        product = Product(name=name)
        session.add(product)
        session.flush()
    return product


def _add_snapshot_items(
    *,
    session: Session,
    snapshot: FridgeSnapshot,
    normalized_payload: dict[str, Any],
) -> None:
    if not normalized_payload:
        return
    for normalized_name, payload in normalized_payload.items():
        name = (normalized_name or "").strip()
        if not name:
            continue
        product = _get_or_create_product(session, name)
        if isinstance(payload, dict):
            quantity = _parse_quantity(payload.get("quantity"))
        else:
            quantity = _parse_quantity(payload)
        session.add(
            SnapshotItem(
                snapshot_id=snapshot.id,
                product_id=product.id,
                quantity=quantity,
                raw_payload=payload,
            )
        )


def _truncate_raw_llm_output(
    raw_text: str | None,
    *,
    limit_bytes: int = _MAX_RAW_LLM_OUTPUT_BYTES,
) -> str | None:
    if not raw_text:
        return None
    encoded = raw_text.encode("utf-8")
    if len(encoded) <= limit_bytes:
        return raw_text
    suffix_bytes = _TRUNCATION_SUFFIX.encode("utf-8")
    if len(suffix_bytes) >= limit_bytes:
        return _TRUNCATION_SUFFIX[:limit_bytes]
    truncated_bytes = encoded[: limit_bytes - len(suffix_bytes)]
    truncated_text = truncated_bytes.decode("utf-8", errors="ignore")
    return f"{truncated_text}{_TRUNCATION_SUFFIX}"


def _attach_raw_llm_output(
    *,
    session: Session,
    snapshot: FridgeSnapshot,
    raw_text: str | None,
) -> None:
    """Attach truncated LLM output to the snapshot in the current transaction."""
    truncated = _truncate_raw_llm_output(raw_text)
    if truncated is None:
        return
    snapshot.raw_llm_output = truncated


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
            user_id=str(DEFAULT_USER_ID),
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
    except TimeoutException:
        current_app.logger.exception("vision LLM request timed out")
        return jsonify(error="vision model timed out"), 504
    except RequestError:
        current_app.logger.exception("vision LLM network error")
        return jsonify(error="vision model network error"), 502
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:  # pragma: no cover - surface upstream errors
        current_app.logger.exception("vision LLM invocation failed")
        return jsonify(error="failed to query vision model"), 502

    raw_text = (llm_result.raw_text or "").strip()
    if not raw_text:
        current_app.logger.error("vision LLM returned empty output")
        return jsonify(error="vision model returned empty output"), 502
    parsed_json = llm_result.parsed_json
    if not isinstance(parsed_json, dict):
        current_app.logger.error("vision LLM did not return JSON object")
        return jsonify(error="vision model did not return JSON output"), 502

    normalized_payload = {
        normalize_product_name(key): value
        for key, value in parsed_json.items()
    }
    normalized_payload = {
        key: value for key, value in normalized_payload.items() if key
    }

    session: Session | None = None
    try:
        session = get_db_session()
        request_user = _get_or_create_request_user(session)
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503
    except SQLAlchemyError:
        if session is not None:
            session.rollback()
            session.close()
            session = None
        current_app.logger.exception("failed to load snapshot user")
        return jsonify(error="failed to prepare snapshot owner"), 500

    try:
        snapshot_record = _add_snapshot_metadata(
            session=session,
            user=request_user,
            stored_image=stored_image,
        )
        _attach_raw_llm_output(
            session=session,
            snapshot=snapshot_record,
            raw_text=raw_text,
        )
        _add_snapshot_items(
            session=session,
            snapshot=snapshot_record,
            normalized_payload=normalized_payload,
        )
        session.commit()
    except SQLAlchemyError:
        if session is not None:
            session.rollback()
            session.close()
            session = None
        current_app.logger.exception("failed to persist snapshot data")
        return jsonify(error="failed to persist snapshot data"), 500
    finally:
        if session is not None:
            session.close()

    return ("", 201)
