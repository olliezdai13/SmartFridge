"""Recipe-related endpoints backed by the Spoonacular API."""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

from flask import Blueprint, current_app, jsonify
import requests
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
SPOONACULAR_API_KEY_ENV = "SPOONACULAR_API_KEY"
_DEFAULT_RECIPE_LIMIT = 10
_SPOONACULAR_TIMEOUT_SECONDS = 10
_ParamValue = str | bytes | int | float | bool | Sequence[str | bytes | int | float | bool]
_RequestParams = Mapping[str, _ParamValue]


def _summarize_recipe(recipe: Mapping[str, Any]) -> dict[str, Any]:
    """Return only the recipe fields we expose to the client."""

    used_ingredients = []
    for ingredient in recipe.get("usedIngredients") or []:
        name = ingredient.get("name") or ingredient.get("originalName")
        if not name:
            continue

        entry: dict[str, Any] = {
            "name": name,
            "amount": ingredient.get("amount"),
        }

        unit = ingredient.get("unit")
        if unit:
            entry["unit"] = unit

        used_ingredients.append(entry)

    return {
        "title": recipe.get("title"),
        "image": recipe.get("image"),
        "missedIngredientCount": recipe.get("missedIngredientCount", 0),
        "usedIngredientCount": recipe.get("usedIngredientCount", len(used_ingredients)),
        "usedIngredients": used_ingredients,
    }


def _prepare_spoonacular_query(
    items: list[InventoryItem]
) -> _RequestParams:
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
        "ranking": 2,
        "ignorePantry": True,
    }


def _get_spoonacular_api_key() -> str:
    api_key = os.environ.get(SPOONACULAR_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{SPOONACULAR_API_KEY_ENV} is not configured")
    return api_key


@bp.get("/recipes")
def prepare_recipes_query():
    """Return the latest fridge items and Spoonacular recipe matches."""

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

    try:
        api_key = _get_spoonacular_api_key()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    spoonacular_query = _prepare_spoonacular_query(items)
    try:
        api_response = requests.get(
            SPOONACULAR_FIND_BY_INGREDIENTS_URL,
            params={**spoonacular_query, "apiKey": api_key},
            timeout=_SPOONACULAR_TIMEOUT_SECONDS,
        )
    except requests.RequestException:
        current_app.logger.exception("failed to call Spoonacular API")
        return jsonify(error="failed to reach Spoonacular API"), 502

    if not api_response.ok:
        current_app.logger.warning(
            "Spoonacular API returned %s: %s",
            api_response.status_code,
            api_response.text[:512],
        )
        return jsonify(error="Spoonacular API request failed"), 502

    try:
        recipes = api_response.json()
    except ValueError:
        current_app.logger.exception("invalid Spoonacular API response")
        return jsonify(error="invalid Spoonacular API response"), 502

    # current_app.logger.info("Spoonacular recipes payload: %r", recipes)

    return jsonify(
        items=items,
        spoonacular_request={
            "endpoint": SPOONACULAR_FIND_BY_INGREDIENTS_URL,
            "query_params": spoonacular_query,
        },
        recipes=[_summarize_recipe(recipe) for recipe in recipes]
    )
