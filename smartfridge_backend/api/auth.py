"""Authentication endpoints and middleware for SmartFridge."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from flask import Blueprint, current_app, g, jsonify, make_response, request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

from smartfridge_backend.api.deps import get_db_session
from smartfridge_backend.models import User
from smartfridge_backend.services.users import normalize_email, serialize_user

ACCESS_COOKIE_NAME = "sf_access_token"
REFRESH_COOKIE_NAME = "sf_refresh_token"
_DEFAULT_ACCESS_MINUTES = 15
_DEFAULT_REFRESH_DAYS = 7

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ---- Helpers -----------------------------------------------------------------


def _auth_secret() -> str:
    secret = os.environ.get("SMARTFRIDGE_AUTH_SECRET") or current_app.config.get(
        "SECRET_KEY"
    )
    if not secret:
        raise RuntimeError(
            "SMARTFRIDGE_AUTH_SECRET or SECRET_KEY must be configured for auth"
        )
    return secret


def _access_token_ttl() -> timedelta:
    minutes = os.environ.get("SMARTFRIDGE_ACCESS_TOKEN_MINUTES")
    if minutes:
        try:
            return timedelta(minutes=int(minutes))
        except ValueError:
            current_app.logger.warning(
                "invalid SMARTFRIDGE_ACCESS_TOKEN_MINUTES=%s, falling back to %s",
                minutes,
                _DEFAULT_ACCESS_MINUTES,
            )
    return timedelta(minutes=_DEFAULT_ACCESS_MINUTES)


def _refresh_token_ttl() -> timedelta:
    days = os.environ.get("SMARTFRIDGE_REFRESH_TOKEN_DAYS")
    if days:
        try:
            return timedelta(days=int(days))
        except ValueError:
            current_app.logger.warning(
                "invalid SMARTFRIDGE_REFRESH_TOKEN_DAYS=%s, falling back to %s",
                days,
                _DEFAULT_REFRESH_DAYS,
            )
    return timedelta(days=_DEFAULT_REFRESH_DAYS)


def _cookie_params(max_age: int | None) -> dict[str, Any]:
    secure = (
        os.environ.get("SMARTFRIDGE_COOKIE_SECURE", "false").lower() == "true"
    )
    domain = os.environ.get("SMARTFRIDGE_COOKIE_DOMAIN") or None
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "Lax",
        "path": "/",
        "max_age": max_age,
        "domain": domain,
    }


def _encode_token(claims: dict[str, Any]) -> str:
    return jwt.encode(claims, _auth_secret(), algorithm="HS256")


def _decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    payload = jwt.decode(token, _auth_secret(), algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("unexpected token type")
    return payload


def _token_claims(user: User, *, token_type: str, expires_in: timedelta) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "sub": str(user.id),
        "type": token_type,
        "ver": user.session_version,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
    }


def _issue_tokens(user: User) -> tuple[str, str]:
    access_claims = _token_claims(
        user, token_type="access", expires_in=_access_token_ttl()
    )
    refresh_claims = _token_claims(
        user, token_type="refresh", expires_in=_refresh_token_ttl()
    )
    return _encode_token(access_claims), _encode_token(refresh_claims)


def _set_auth_cookies(response, *, access_token: str, refresh_token: str):
    access_age = int(_access_token_ttl().total_seconds())
    refresh_age = int(_refresh_token_ttl().total_seconds())
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        **_cookie_params(access_age),
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        **_cookie_params(refresh_age),
    )
    return response


def _clear_auth_cookies(response):
    params = _cookie_params(0)
    response.set_cookie(ACCESS_COOKIE_NAME, "", expires=0, **params)
    response.set_cookie(REFRESH_COOKIE_NAME, "", expires=0, **params)
    return response


def _load_user(session, user_id: str) -> User | None:
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return None
    return session.get(User, uid)


def _user_from_refresh(session) -> tuple[User | None, dict[str, Any] | None]:
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        return None, None
    try:
        claims = _decode_token(token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        return None, None
    except jwt.InvalidTokenError:
        current_app.logger.info("invalid refresh token")
        return None, None

    user = _load_user(session, claims.get("sub"))
    if not user or user.session_version != claims.get("ver"):
        return None, None
    return user, claims


def authenticate_request():
    """Middleware used by protected blueprints to require a valid access token."""

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    token = request.cookies.get(ACCESS_COOKIE_NAME)
    if not token:
        return jsonify(error="unauthorized"), 401

    try:
        claims = _decode_token(token, expected_type="access")
        user = _load_user(session, claims.get("sub"))
        if not user or user.session_version != claims.get("ver"):
            return jsonify(error="unauthorized"), 401
        g.current_user = user
        g.current_user_id = user.id
    except jwt.ExpiredSignatureError:
        return jsonify(error="session expired"), 401
    except jwt.InvalidTokenError:
        return jsonify(error="unauthorized"), 401
    except SQLAlchemyError:
        current_app.logger.exception("failed to load user during auth check")
        return jsonify(error="failed to load user"), 500
    finally:
        session.close()

    return None


def _login_response(
    session,
    user: User,
    *,
    status_code: int = 200,
) -> tuple[Any, int]:
    user.last_login_at = datetime.now(timezone.utc)
    session.commit()
    access_token, refresh_token = _issue_tokens(user)
    response = make_response(jsonify(user=serialize_user(user)), status_code)
    return _set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=refresh_token,
    ), status_code


# ---- Routes ------------------------------------------------------------------


@bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = normalize_email(str(data.get("email", "")))
    password = str(data.get("password", ""))
    name = (data.get("name") or "").strip() or None

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    user_id: uuid.UUID | None = None
    try:
        existing = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing:
            return jsonify(error="email already registered"), 409

        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password),
            session_version=1,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        user_id = user.id
    except SQLAlchemyError:
        session.rollback()
        current_app.logger.exception("failed to create user")
        return jsonify(error="failed to create user"), 500
    finally:
        session.close()

    # Reload in a new session to avoid detached issues when setting cookies.
    if user_id is None:
        return jsonify(error="user creation failed"), 500
    session = get_db_session()
    try:
        user = session.get(User, user_id)
        if user is None:
            return jsonify(error="user creation failed"), 500
        return _login_response(session, user, status_code=201)
    finally:
        session.close()


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = normalize_email(str(data.get("email", "")))
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify(error="email and password are required"), 400

    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        user = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify(error="invalid credentials"), 401
        return _login_response(session, user)
    except SQLAlchemyError:
        session.rollback()
        current_app.logger.exception("failed to query user")
        return jsonify(error="failed to log in"), 500
    finally:
        session.close()


@bp.post("/refresh")
def refresh():
    try:
        session = get_db_session()
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503

    try:
        user, claims = _user_from_refresh(session)
        if not user or not claims:
            return jsonify(error="unauthorized"), 401
        access_token, refresh_token = _issue_tokens(user)
        response = make_response(jsonify(user=serialize_user(user)), 200)
        return _set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token,
        )
    except SQLAlchemyError:
        current_app.logger.exception("failed to refresh session")
        return jsonify(error="failed to refresh session"), 500
    finally:
        session.close()


@bp.get("/me")
def me():
    auth_error = authenticate_request()
    if auth_error:
        return auth_error

    user: User = g.current_user
    return jsonify(user=serialize_user(user))


@bp.post("/logout")
def logout():
    try:
        session = get_db_session()
    except RuntimeError as exc:
        resp = jsonify(error=str(exc))
        return _clear_auth_cookies(resp), 503

    try:
        user, _ = _user_from_refresh(session)
        if not user:
            # Fallback to access token if refresh is missing/expired.
            token = request.cookies.get(ACCESS_COOKIE_NAME)
            if token:
                try:
                    claims = _decode_token(token, expected_type="access")
                    user = _load_user(session, claims.get("sub"))
                except jwt.InvalidTokenError:
                    user = None

        if user:
            user.session_version += 1
            session.commit()
    except SQLAlchemyError:
        session.rollback()
        current_app.logger.exception("failed to logout user")
        return _clear_auth_cookies(jsonify(error="failed to logout")), 500
    finally:
        session.close()

    return _clear_auth_cookies(jsonify(success=True))
