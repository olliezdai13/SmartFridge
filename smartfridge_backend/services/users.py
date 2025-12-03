"""User helpers and placeholder defaults until authentication lands."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from smartfridge_backend.models import User

DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_EMAIL = "demo@smartfridge.local"
DEFAULT_USER_NAME = "Demo User"
DEFAULT_USER_PASSWORD_HASH = (
    "scrypt:32768:8:1$9UhdfW9nDT12TkmN$"
    "5e3c5a26098d0c9e4abc97bfe0caee5d9835699b7fba7892286f8bc99"
    "c7c03db1fe4f264481811c4dea47a546b832f3363c3fb44abd383ca4b"
    "f8787c5674dc1c"
)


def get_or_create_default_user(session: Session) -> User:
    """Return the placeholder user record, creating it if missing."""

    user = session.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(
            id=DEFAULT_USER_ID,
            email=DEFAULT_USER_EMAIL.lower(),
            name=DEFAULT_USER_NAME,
            password_hash=DEFAULT_USER_PASSWORD_HASH,
        )
        session.add(user)
    return user
