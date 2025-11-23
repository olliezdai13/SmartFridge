"""User helpers and placeholder defaults until authentication lands."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from smartfridge_backend.models import User

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_EMAIL = "demo@smartfridge.local"
DEFAULT_USER_NAME = "Demo User"


def get_or_create_default_user(session: Session) -> User:
    """Return the placeholder user record, creating it if missing."""

    user = session.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(
            id=DEFAULT_USER_ID,
            email=DEFAULT_USER_EMAIL,
            name=DEFAULT_USER_NAME,
        )
        session.add(user)
    return user
