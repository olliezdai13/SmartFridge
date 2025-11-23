"""Recipe-related endpoints that prepare Spoonacular calls."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify
from sqlalchemy.exc import SQLAlchemyError

from smartfridge_backend.api.deps import get_sessionmaker
from smartfridge_backend.services.inventory import (
    InventoryItem,
    fetch_latest_items_for_user,
)
from smartfridge_backend.services.users import DEFAULT_USER_ID

bp = Blueprint("recipes", __name__, url_prefix="/api")

SPOONACULAR_FIND_BY_INGREDIENTS_URL = (
    "https://api.spoonacular.com/recipes/findByIngredients"
)
_DEFAULT_RECIPE_LIMIT = 5


def _prepare_spoonacular_query(
    items: list[InventoryItem]
) -> dict[str, object]:
    """Shape fridge items into the query params Spoonacular expects."""

    ingredient_tokens: list[str] = []
    for entry in items:
        name = entry["name"].strip()
        if not name:
            continue
        count = entry["quantity"]
        ingredient_tokens.extend([name] * max(count, 1))

    # Deduplicate while preserving order to keep the query readable.
    seen: set[str] = set()
    unique_ingredients = []
    for ingredient in ingredient_tokens:
        if ingredient not in seen:
            unique_ingredients.append(ingredient)
            seen.add(ingredient)

    return {
        "ingredients": ",".join(unique_ingredients),
        "number": _DEFAULT_RECIPE_LIMIT,
        "ranking": 1,
        "ignorePantry": True,
    }


@bp.get("/recipes")
def prepare_recipes_query():
    """Return the latest fridge items and a Spoonacular-ready query."""

    try:
        session_factory = get_sessionmaker()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        items = fetch_latest_items_for_user(
            session_factory, user_id=DEFAULT_USER_ID
        )
    except SQLAlchemyError:
        current_app.logger.exception("failed to load fridge inventory")
        return jsonify(error="failed to load fridge inventory"), 500

    if not items:
        return (
            jsonify(
                error="no fridge snapshots found for the active user",
                items=[],
            ),
            404,
        )

    spoonacular_query = _prepare_spoonacular_query(items)

    return jsonify(
        items=items,
        spoonacular_request={
            "endpoint": SPOONACULAR_FIND_BY_INGREDIENTS_URL,
            "query_params": spoonacular_query,
            "api_key_env": "SPOONACULAR_API_KEY",
            "note": (
                "The backend does not call Spoonacular yet; invoke this URL "
                "with your API key from the client or a future backend task."
            ),
        },
    )
