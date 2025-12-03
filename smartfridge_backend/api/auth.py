"""Authentication helpers for API request handling."""

from __future__ import annotations

import uuid

import jwt
from flask import current_app, g, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from smartfridge_backend.api.deps import get_sessionmaker
from smartfridge_backend.models import User
from smartfridge_backend.services.auth_tokens import AuthSettings, decode_token

_SKIP_PATH_PREFIXES = ("/api/auth",)
_SKIP_PATHS = {"/healthz", "/api/healthz"}


def attach_user_from_access_cookie():
    """Load the authenticated user from the access cookie and attach it to ``g``."""

    path = request.path or ""
    if not _should_enforce_auth(path):
        return None

    try:
        settings = AuthSettings.load()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    access_token = request.cookies.get(settings.access_cookie_name)
    if not access_token:
        return jsonify(error="unauthorized"), 401

    try:
        payload = decode_token(
            access_token, settings=settings, expected_type="access"
        )
    except jwt.ExpiredSignatureError:
        return jsonify(error="token expired"), 401
    except (jwt.InvalidTokenError, ValueError) as exc:
        current_app.logger.warning("invalid access token: %s", exc)
        return jsonify(error="unauthorized"), 401

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return jsonify(error="unauthorized"), 401

    try:
        session_factory = get_sessionmaker()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        with session_factory() as session:
            user = session.get(User, user_uuid)
    except SQLAlchemyError:
        current_app.logger.exception("failed to load user for request")
        return jsonify(error="failed to load user"), 500

    if user is None:
        return jsonify(error="unauthorized"), 401

    g.user = user
    g.user_id = user.id
    return None


def _should_enforce_auth(path: str) -> bool:
    if not path.startswith("/api"):
        return False
    if path in _SKIP_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in _SKIP_PATH_PREFIXES)
