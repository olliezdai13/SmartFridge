"""Endpoint that handles fridge snapshots end-to-end."""

from __future__ import annotations

import mimetypes
import uuid
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

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

bp = Blueprint("snapshot", __name__, url_prefix="/api")

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_EMAIL = "demo@smartfridge.local"
DEFAULT_USER_NAME = "Demo User"


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


def _get_sessionmaker() -> sessionmaker:
    session_factory: sessionmaker | None = current_app.extensions.get(
        "db_sessionmaker"
    )
    if session_factory is None:
        raise RuntimeError("database session factory is not configured")
    return session_factory


def _get_db_session() -> Session:
    return _get_sessionmaker()()


def _get_or_create_request_user(session: Session) -> User:
    """Return the active user (placeholder until auth lands)."""

    user = session.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(
            id=DEFAULT_USER_ID,
            email=DEFAULT_USER_EMAIL,
            name=DEFAULT_USER_NAME,
        )
        session.add(user)
    return user


def _persist_snapshot_metadata(
    *,
    session: Session,
    user: User,
    stored_image: StoredImage,
) -> FridgeSnapshot:
    """Create a fridge_snapshots row tied to the stored object."""

    snapshot = FridgeSnapshot(
        user_id=user.id,
        image_bucket=stored_image.bucket,
        image_key=stored_image.key,
        image_filename=stored_image.filename,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


_DEFAULT_ITEM_QUANTITY = 1


def _clean_string(value: object) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        try:
            return float(candidate)
        except ValueError:
            return None
    return None


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


def _extract_snapshot_item_fields(
    payload: object,
) -> tuple[int, str | None, float | None, str | None]:
    quantity = _DEFAULT_ITEM_QUANTITY
    unit = None
    confidence = None
    notes = None

    if isinstance(payload, dict):
        quantity = _parse_quantity(payload.get("quantity"))
        unit = _clean_string(payload.get("unit") or payload.get("units"))
        confidence = _coerce_float(payload.get("confidence"))
        notes = _clean_string(payload.get("notes"))
    else:
        if isinstance(payload, (int, float, str)):
            quantity = _parse_quantity(payload)
        if isinstance(payload, str):
            notes = _clean_string(payload)

    return quantity, unit, confidence, notes


def _get_or_create_product(session: Session, slug: str) -> Product:
    product = session.execute(
        select(Product).where(Product.slug == slug)
    ).scalar_one_or_none()
    if product is None:
        product = Product(slug=slug, name=slug)
        session.add(product)
        session.flush()
    return product


def _persist_snapshot_items(
    *,
    snapshot: FridgeSnapshot,
    normalized_payload: dict[str, Any],
) -> None:
    if not normalized_payload:
        return
    session = _get_db_session()
    try:
        for normalized_name, payload in normalized_payload.items():
            slug = (normalized_name or "").strip()
            if not slug:
                continue
            product = _get_or_create_product(session, slug)
            quantity, unit, confidence, notes = _extract_snapshot_item_fields(
                payload
            )
            session.add(
                SnapshotItem(
                    snapshot_id=snapshot.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit=unit,
                    confidence=confidence,
                    notes=notes,
                    raw_payload=payload,
                )
            )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


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

    session: Session | None = None
    snapshot_record: FridgeSnapshot | None = None
    try:
        session = _get_db_session()
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
        stored_image, image_bytes = save_image_upload(
            image_file,
            storage,
            user_id=str(request_user.id),
        )
    except ValueError as exc:
        if session is not None:
            session.rollback()
            session.close()
            session = None
        return jsonify(error=str(exc)), 400
    except SnapshotStorageError as exc:
        if session is not None:
            session.rollback()
            session.close()
            session = None
        current_app.logger.exception("snapshot storage failure")
        return jsonify(error=str(exc)), 502

    try:
        snapshot_record = _persist_snapshot_metadata(
            session=session,
            user=request_user,
            stored_image=stored_image,
        )
    except SQLAlchemyError:
        if session is not None:
            session.rollback()
            session.close()
            session = None
        current_app.logger.exception("failed to persist snapshot metadata")
        return jsonify(error="failed to persist snapshot metadata"), 500
    finally:
        if session is not None:
            session.close()
            session = None

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

    assert snapshot_record is not None
    try:
        _persist_snapshot_items(
            snapshot=snapshot_record,
            normalized_payload=normalized_payload,
        )
    except SQLAlchemyError:
        current_app.logger.exception("failed to persist snapshot items")
        return jsonify(error="failed to persist snapshot items"), 500

    return ("", 201)
