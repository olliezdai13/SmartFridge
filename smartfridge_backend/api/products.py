"""Product maintenance endpoints."""

from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify
from sqlalchemy.exc import SQLAlchemyError

from smartfridge_backend.api.deps import get_db_session
from smartfridge_backend.services.llm import TextLLMClient
from smartfridge_backend.services.product_categorization import (
    CATEGORY_UPDATE_BATCH_LIMIT,
    ProductCategorizationError,
    apply_categories_to_products,
)

bp = Blueprint("products", __name__, url_prefix="/api")


def _get_text_llm_client() -> TextLLMClient:
    client: TextLLMClient | None = current_app.extensions.get(
        "text_llm_client"
    )
    if client is None:
        raise RuntimeError("text LLM client is not configured")
    return client


@bp.post("/update_categories")
def update_categories():
    """Assign categories to products that are currently uncategorized."""

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user_id = getattr(g, "user_id", None)
    if user_id is None:
        return jsonify(error="unauthorized"), 401

    try:
        llm_client = _get_text_llm_client()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        update_counts = apply_categories_to_products(
            session=session,
            llm_client=llm_client,
            limit=CATEGORY_UPDATE_BATCH_LIMIT,
        )
    except SQLAlchemyError:
        current_app.logger.exception("failed to load uncategorized products")
        session.close()
        return jsonify(error="failed to load products"), 500
    except ProductCategorizationError as exc:
        session.close()
        current_app.logger.warning("category LLM failure: %s", exc)
        return jsonify(error=str(exc)), 502

    updated_count, total_products = update_counts

    if total_products == 0:
        session.close()
        return jsonify(
            updated=0, message="no uncategorized products found"
        )

    if updated_count == 0:
        session.close()
        return (
            jsonify(error="LLM did not return categories for any products"),
            502,
        )

    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        current_app.logger.exception("failed to update product categories")
        return jsonify(error="failed to update product categories"), 500
    finally:
        session.close()

    return jsonify(updated=updated_count, total=total_products)
