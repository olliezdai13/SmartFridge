"""User helpers for authentication flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from smartfridge_backend.models import User


def normalize_email(email: str) -> str:
    """Normalize an email for lookups and storage."""

    return email.strip().lower()


def serialize_user(user: User) -> dict[str, Any]:
    """Return a JSON-friendly representation of the user."""

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "lastLoginAt": _serialize_datetime(user.last_login_at),
    }


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat()
