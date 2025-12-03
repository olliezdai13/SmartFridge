"""JWT helpers for issuing and storing SmartFridge auth cookies."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from flask import Response, current_app

AccessTokenType = Literal["access"]
RefreshTokenType = Literal["refresh"]
TokenType = AccessTokenType | RefreshTokenType

# Defaults keep tokens short-lived and predictable.
DEFAULT_ACCESS_TOKEN_TTL = timedelta(minutes=15)
DEFAULT_REFRESH_TOKEN_TTL = timedelta(days=30)
DEFAULT_ACCESS_COOKIE_NAME = "sf_access"
DEFAULT_REFRESH_COOKIE_NAME = "sf_refresh"
DEFAULT_COOKIE_PATH = "/"
DEFAULT_COOKIE_SAMESITE: Literal["Lax", "Strict", "None"] = "Lax"
DEFAULT_JWT_ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AuthSettings:
    """Configuration for issuing and storing auth tokens."""

    secret: str
    access_token_ttl: timedelta = DEFAULT_ACCESS_TOKEN_TTL
    refresh_token_ttl: timedelta = DEFAULT_REFRESH_TOKEN_TTL
    access_cookie_name: str = DEFAULT_ACCESS_COOKIE_NAME
    refresh_cookie_name: str = DEFAULT_REFRESH_COOKIE_NAME
    cookie_path: str = DEFAULT_COOKIE_PATH
    cookie_samesite: Literal["Lax", "Strict", "None"] = DEFAULT_COOKIE_SAMESITE
    cookie_secure: bool = True
    cookie_httponly: bool = True
    algorithm: str = DEFAULT_JWT_ALGORITHM

    @classmethod
    def load(cls, app=None) -> "AuthSettings":
        """Build settings from Flask config or environment."""

        app = app or _try_get_current_app()
        secret = None
        if app:
            secret = app.config.get("AUTH_SECRET")

        if not secret:
            secret = os.environ.get("SMARTFRIDGE_AUTH_SECRET")

        if not secret:
            raise RuntimeError("SMARTFRIDGE_AUTH_SECRET is not configured")

        return cls(secret=secret)


@dataclass(frozen=True)
class TokenPair:
    """Bundle of freshly issued access/refresh tokens and their expirations."""

    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    refresh_token_id: str


def issue_token_pair(
    user_id: uuid.UUID | str,
    settings: AuthSettings | None = None,
    refresh_token_id: str | None = None,
) -> TokenPair:
    """Create signed access/refresh JWTs for the given user."""

    settings = settings or AuthSettings.load()
    now = _now()
    refresh_id = refresh_token_id or uuid.uuid4().hex

    access_expires_at = now + settings.access_token_ttl
    refresh_expires_at = now + settings.refresh_token_ttl

    access_payload = _build_access_payload(
        user_id=user_id,
        refresh_token_id=refresh_id,
        expires_at=access_expires_at,
        issued_at=now,
    )
    refresh_payload = _build_refresh_payload(
        user_id=user_id,
        token_id=refresh_id,
        expires_at=refresh_expires_at,
        issued_at=now,
    )

    access_token = jwt.encode(
        access_payload, settings.secret, algorithm=settings.algorithm
    )
    refresh_token = jwt.encode(
        refresh_payload, settings.secret, algorithm=settings.algorithm
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
        refresh_token_id=refresh_id,
    )


def decode_token(
    token: str,
    settings: AuthSettings | None = None,
    expected_type: TokenType | None = None,
) -> dict[str, Any]:
    """Decode and validate a JWT, optionally enforcing its declared type."""

    settings = settings or AuthSettings.load()
    payload = jwt.decode(
        token,
        settings.secret,
        algorithms=[settings.algorithm],
    )
    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise ValueError(
            f"unexpected token type {token_type!r}; expected {expected_type!r}"
        )
    return payload


def apply_auth_cookies(
    response: Response, tokens: TokenPair, settings: AuthSettings | None = None
) -> None:
    """Attach HttpOnly, Secure auth cookies carrying the issued tokens."""

    settings = settings or AuthSettings.load()
    response.set_cookie(
        settings.access_cookie_name,
        tokens.access_token,
        max_age=int(settings.access_token_ttl.total_seconds()),
        expires=tokens.access_expires_at,
        path=settings.cookie_path,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
        samesite=settings.cookie_samesite,
    )
    response.set_cookie(
        settings.refresh_cookie_name,
        tokens.refresh_token,
        max_age=int(settings.refresh_token_ttl.total_seconds()),
        expires=tokens.refresh_expires_at,
        path=settings.cookie_path,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
        samesite=settings.cookie_samesite,
    )


def clear_auth_cookies(
    response: Response, settings: AuthSettings | None = None
) -> None:
    """Remove access and refresh cookies from the response."""

    settings = settings or AuthSettings.load()
    response.delete_cookie(
        settings.access_cookie_name,
        path=settings.cookie_path,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
    )
    response.delete_cookie(
        settings.refresh_cookie_name,
        path=settings.cookie_path,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        httponly=settings.cookie_httponly,
    )


def _build_access_payload(
    user_id: uuid.UUID | str,
    refresh_token_id: str,
    expires_at: datetime,
    issued_at: datetime,
) -> dict[str, Any]:
    return {
        "sub": str(user_id),
        "type": "access",
        "refresh": refresh_token_id,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }


def _build_refresh_payload(
    user_id: uuid.UUID | str,
    token_id: str,
    expires_at: datetime,
    issued_at: datetime,
) -> dict[str, Any]:
    return {
        "sub": str(user_id),
        "type": "refresh",
        "jti": token_id,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }


def _try_get_current_app():
    try:
        return current_app._get_current_object()
    except RuntimeError:
        return None
