"""Image ingestion pipeline for fridge snapshots."""

from __future__ import annotations

import mimetypes
from typing import Any

from httpx import RequestError, TimeoutException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from smartfridge_backend.models import (
    FridgeSnapshot,
    Product,
    SnapshotItem,
    User,
)
from smartfridge_backend.services.llm import VisionLLMClient
from smartfridge_backend.services.normalization import normalize_product_name
from smartfridge_backend.services.uploads import StoredImage

MAX_RAW_LLM_OUTPUT_BYTES = 16_000
TRUNCATION_SUFFIX = " [truncated]"
DEFAULT_ITEM_QUANTITY = 1


class IngestionError(RuntimeError):
    """Raised when the ingestion pipeline fails."""


class IngestionPersistenceError(IngestionError):
    """Raised when the ingestion pipeline cannot write to the database."""


class IngestionLLMError(IngestionError):
    """Raised when the ingestion pipeline encounters an LLM failure."""


def truncate_raw_llm_output(
    raw_text: str | None,
    *,
    limit_bytes: int = MAX_RAW_LLM_OUTPUT_BYTES,
) -> str | None:
    """Trim oversized LLM responses for storage."""
    if not raw_text:
        return None
    encoded = raw_text.encode("utf-8")
    if len(encoded) <= limit_bytes:
        return raw_text
    suffix_bytes = TRUNCATION_SUFFIX.encode("utf-8")
    if len(suffix_bytes) >= limit_bytes:
        return TRUNCATION_SUFFIX[:limit_bytes]
    truncated_bytes = encoded[: limit_bytes - len(suffix_bytes)]
    truncated_text = truncated_bytes.decode("utf-8", errors="ignore")
    return f"{truncated_text}{TRUNCATION_SUFFIX}"


def _parse_quantity(value: object) -> int:
    """Return a positive integer quantity derived from arbitrary input."""

    if value is None:
        return DEFAULT_ITEM_QUANTITY
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
        return DEFAULT_ITEM_QUANTITY
    return quantity if quantity > 0 else DEFAULT_ITEM_QUANTITY


def _get_or_create_product(session: Session, name: str) -> Product:
    product = session.execute(
        select(Product).where(Product.name == name)
    ).scalar_one_or_none()
    if product is None:
        product = Product(name=name)
        session.add(product)
        session.flush()
    return product


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


def _attach_raw_llm_output(
    *,
    session: Session,
    snapshot: FridgeSnapshot,
    raw_text: str | None,
) -> None:
    """Attach truncated LLM output to the snapshot in the current transaction."""
    truncated = truncate_raw_llm_output(raw_text)
    if truncated is None:
        return
    snapshot.raw_llm_output = truncated


def ingest_snapshot_image(
    *,
    session: Session,
    user: User,
    stored_image: StoredImage,
    image_bytes: bytes,
    llm_client: VisionLLMClient,
    prompt: str | None = None,
) -> FridgeSnapshot:
    """Run the image through the vision pipeline and persist results."""

    mime_type, _ = mimetypes.guess_type(stored_image.filename)

    try:
        llm_result = llm_client.analyze_image(
            image_bytes=image_bytes,
            prompt=prompt,
            mime_type=mime_type,
        )
    except (TimeoutException, RequestError, ValueError) as exc:
        raise IngestionLLMError("vision model request failed") from exc
    except Exception as exc:  # pragma: no cover - surface upstream errors
        raise IngestionLLMError("vision model invocation failed") from exc

    raw_text = (llm_result.raw_text or "").strip()
    if not raw_text:
        raise IngestionLLMError("vision model returned empty output")
    parsed_json = llm_result.parsed_json
    if not isinstance(parsed_json, dict):
        raise IngestionLLMError("vision model did not return JSON output")

    normalized_payload = {
        normalize_product_name(key): value
        for key, value in parsed_json.items()
    }
    normalized_payload = {
        key: value for key, value in normalized_payload.items() if key
    }

    try:
        snapshot_record = _add_snapshot_metadata(
            session=session,
            user=user,
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
    except SQLAlchemyError as exc:
        session.rollback()
        raise IngestionPersistenceError(
            "failed to persist snapshot data"
        ) from exc

    return snapshot_record
