"""LLM-powered helpers for categorizing products."""

from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from smartfridge_backend.models import Product
from smartfridge_backend.models import ProductCategory
from smartfridge_backend.services.llm import TextLLMClient

logger = logging.getLogger(__name__)

CATEGORY_UPDATE_BATCH_LIMIT = 20


class ProductCategorizationError(RuntimeError):
    """Raised when the category LLM call fails or returns invalid data."""


def _build_prompt(product_names: Iterable[str]) -> str:
    category_entries = sorted(ProductCategory, key=lambda entry: entry.value)
    category_options = "\n".join(
        f"{entry.name}: {entry.value}" for entry in category_entries
    )
    example_category = category_entries[0].name
    formatted_names = "\n".join(f"- {name}" for name in product_names)
    prompt = (
        "Classify each grocery product into exactly one category.\n"
        f"Available categories:\n{category_options}\n"
        "Respond with a JSON object that maps the exact product name to a "
        "category enum. Do not add or omit products. Do not invent new categories. "
        f"Example: {{\"apple\": \"{example_category}\"}}.\n"
        "Products to categorize:\n"
        f"{formatted_names}\n"
        "Only output JSON."
    )
    return prompt


def _parse_llm_payload(
    payload: object, allowed_names: set[str]
) -> dict[str, str]:
    """Validate the LLM response matches expected shape and values."""
    if not isinstance(payload, dict):
        raise ValueError("LLM output must be a JSON object")

    updates: dict[str, str] = {}
    valid_categories = ProductCategory.keys()
    for raw_name, raw_category in payload.items():
        if raw_name not in allowed_names:
            raise ValueError(f"unknown product returned: {raw_name!r}")
        if not isinstance(raw_category, str):
            raise ValueError(
                f"category for {raw_name!r} must be a string"
            )

        normalized_category = raw_category.strip().upper()
        if normalized_category not in valid_categories:
            raise ValueError(
                f"invalid category {raw_category!r} for {raw_name!r}"
            )
        updates[raw_name] = normalized_category

    if not updates:
        raise ValueError("LLM output did not include any product categories")

    missing = allowed_names - set(updates)
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"missing categories for: {missing_str}")

    return updates


def categorize_products(
    llm_client: TextLLMClient, product_names: list[str]
) -> dict[str, str]:
    """Call the LLM to categorize the provided product names."""

    if not product_names:
        return {}

    prompt = _build_prompt(product_names)
    try:
        result = llm_client.run_prompt(prompt=prompt)
    except Exception as exc:  # pragma: no cover - surfacing dependency failures
        logger.exception("category LLM request failed")
        raise ProductCategorizationError("failed to invoke LLM") from exc

    if not result.raw_text:
        raise ProductCategorizationError("LLM returned empty output")
    if result.parsed_json is None:
        raise ProductCategorizationError("LLM did not return valid JSON")

    try:
        return _parse_llm_payload(result.parsed_json, set(product_names))
    except ValueError as exc:
        raise ProductCategorizationError(str(exc)) from exc


def apply_categories_to_products(
    *,
    session: Session,
    llm_client: TextLLMClient,
    limit: int = CATEGORY_UPDATE_BATCH_LIMIT,
) -> tuple[int, int]:
    """Assign categories to uncategorized products up to the provided limit."""

    uncategorized_products = (
        session.execute(
            select(Product)
            .where(or_(Product.category.is_(None), Product.category == ""))
            .order_by(Product.name)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    if not uncategorized_products:
        return 0, 0

    product_names = [product.name for product in uncategorized_products]
    updates = categorize_products(llm_client, product_names)

    updated_count = 0
    for product in uncategorized_products:
        category = updates.get(product.name)
        if not category:
            continue
        product.category = category
        updated_count += 1

    if updated_count == 0:
        raise ProductCategorizationError(
            "LLM did not return categories for any products"
        )

    return updated_count, len(product_names)
