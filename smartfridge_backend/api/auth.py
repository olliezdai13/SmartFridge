"""Authentication helpers and endpoints for API request handling."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

import jwt
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from smartfridge_backend.api.deps import get_sessionmaker
from smartfridge_backend.models import User
from smartfridge_backend.services.auth_tokens import (
    AuthSettings,
    apply_auth_cookies,
    clear_auth_cookies,
    decode_token,
    issue_token_pair,
)

_SKIP_PATH_PREFIXES = ("/api/auth",)
_SKIP_PATHS = {"/healthz", "/api/healthz"}
bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def attach_user_from_access_cookie():
    """Load the authenticated user from the access cookie and attach it to ``g``."""

    path = request.path or ""
    if not _should_enforce_auth(path):
        return None

    auth_ctx = _get_auth_context()
    if auth_ctx.error_response:
        return auth_ctx.error_response

    user, error = _load_user_from_access_cookie(auth_ctx, require_cookie=True)
    if error:
        return error

    g.user = user
    g.user_id = user.id
    return None


def _should_enforce_auth(path: str) -> bool:
    if not path.startswith("/api"):
        return False
    if path in _SKIP_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in _SKIP_PATH_PREFIXES)


@bp.post("/signup")
def signup():
    """Create a new user and issue auth cookies."""

    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    password = payload.get("password")
    name = payload.get("name")

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    auth_ctx = _get_auth_context()
    if auth_ctx.error_response:
        return auth_ctx.error_response

    password_hash = generate_password_hash(password)

    try:
        with auth_ctx.session_factory() as session:
            existing = session.scalar(
                select(User).where(func.lower(User.email) == email)
            )
            if existing:
                return jsonify(error="user already exists"), 409

            user = User(email=email, password_hash=password_hash, name=name)
            session.add(user)
            session.commit()
            session.refresh(user)
    except SQLAlchemyError:
        current_app.logger.exception("failed to create user")
        return jsonify(error="database failure while creating user"), 500

    tokens = issue_token_pair(user.id, settings=auth_ctx.settings)
    response = jsonify(user=_serialize_user(user))
    apply_auth_cookies(response, tokens, settings=auth_ctx.settings)
    return response, 201


@bp.post("/login")
def login():
    """Authenticate a user, rotate tokens, and record the login timestamp."""

    payload = request.get_json(silent=True) or {}
    email = _normalize_email(payload.get("email"))
    password = payload.get("password")

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    auth_ctx = _get_auth_context()
    if auth_ctx.error_response:
        return auth_ctx.error_response

    now = datetime.now(timezone.utc)

    try:
        with auth_ctx.session_factory() as session:
            user = session.scalar(
                select(User).where(func.lower(User.email) == email)
            )
            if not user or not check_password_hash(
                user.password_hash, password
            ):
                return jsonify(error="invalid credentials"), 401

            user.last_login_at = now
            session.commit()
    except SQLAlchemyError:
        current_app.logger.exception("failed to authenticate user")
        return jsonify(error="database failure during login"), 500

    tokens = issue_token_pair(user.id, settings=auth_ctx.settings)
    response = jsonify(user=_serialize_user(user))
    apply_auth_cookies(response, tokens, settings=auth_ctx.settings)
    return response


@bp.post("/refresh")
def refresh_tokens():
    """Validate the refresh cookie and issue a fresh token pair."""

    auth_ctx = _get_auth_context()
    if auth_ctx.error_response:
        return auth_ctx.error_response

    user, error = _load_user_from_refresh_cookie(auth_ctx)
    if error:
        return error

    tokens = issue_token_pair(user.id, settings=auth_ctx.settings)
    response = jsonify(user=_serialize_user(user))
    apply_auth_cookies(response, tokens, settings=auth_ctx.settings)
    return response


@bp.post("/logout")
def logout():
    """Clear auth cookies for the caller."""

    auth_ctx = _get_auth_context()
    if auth_ctx.error_response:
        return auth_ctx.error_response

    response = jsonify(status="ok")
    clear_auth_cookies(response, settings=auth_ctx.settings)
    return response


@bp.get("/me")
def get_me():
    """Return the currently authenticated user's profile."""

    auth_ctx = _get_auth_context()
    if auth_ctx.error_response:
        return auth_ctx.error_response

    user, error = _load_user_from_access_cookie(auth_ctx, require_cookie=True)
    if error:
        return error

    return jsonify(user=_serialize_user(user))


def _normalize_email(value) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    return value or None


class _AuthContext:
    def __init__(
        self,
        settings: AuthSettings | None,
        session_factory,
        error_response,
    ):
        self.settings = settings
        self.session_factory = session_factory
        self.error_response = error_response


def _get_auth_context() -> _AuthContext:
    try:
        settings = AuthSettings.load()
    except RuntimeError as exc:
        return _AuthContext(None, None, (jsonify(error=str(exc)), 503))

    try:
        session_factory = get_sessionmaker()
    except RuntimeError as exc:
        return _AuthContext(settings, None, (jsonify(error=str(exc)), 503))

    return _AuthContext(settings, session_factory, None)


def _load_user_from_access_cookie(
    auth_ctx: _AuthContext, require_cookie: bool
) -> tuple[User | None, tuple | None]:
    access_token = request.cookies.get(auth_ctx.settings.access_cookie_name)
    if not access_token:
        if require_cookie:
            return None, (jsonify(error="unauthorized"), 401)
        return None, None

    try:
        payload = decode_token(
            access_token,
            settings=auth_ctx.settings,
            expected_type="access",
        )
    except jwt.ExpiredSignatureError:
        return None, (jsonify(error="token expired"), 401)
    except (jwt.InvalidTokenError, ValueError) as exc:
        current_app.logger.warning("invalid access token: %s", exc)
        return None, (jsonify(error="unauthorized"), 401)

    return _load_user_from_payload(auth_ctx, payload)


def _load_user_from_refresh_cookie(
    auth_ctx: _AuthContext,
) -> tuple[User | None, tuple | None]:
    refresh_token = request.cookies.get(auth_ctx.settings.refresh_cookie_name)
    if not refresh_token:
        return None, (jsonify(error="unauthorized"), 401)

    try:
        payload = decode_token(
            refresh_token,
            settings=auth_ctx.settings,
            expected_type="refresh",
        )
    except jwt.ExpiredSignatureError:
        return None, (jsonify(error="token expired"), 401)
    except (jwt.InvalidTokenError, ValueError) as exc:
        current_app.logger.warning("invalid refresh token: %s", exc)
        return None, (jsonify(error="unauthorized"), 401)

    return _load_user_from_payload(auth_ctx, payload)


def _load_user_from_payload(
    auth_ctx: _AuthContext, payload: dict[str, str]
) -> tuple[User | None, tuple | None]:
    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(str(user_id))
    except (TypeError, ValueError):
        return None, (jsonify(error="unauthorized"), 401)

    try:
        with auth_ctx.session_factory() as session:
            user = session.get(User, user_uuid)
    except SQLAlchemyError:
        current_app.logger.exception("failed to load user for request")
        return None, (jsonify(error="failed to load user"), 500)

    if user is None:
        return None, (jsonify(error="unauthorized"), 401)

    return user, None


def _serialize_user(user: User) -> dict[str, str | None]:
    last_login = (
        user.last_login_at.isoformat() if user.last_login_at else None
    )
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "last_login_at": last_login,
    }
