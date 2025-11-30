"""Shared API dependencies and helpers."""

from flask import current_app, g
from sqlalchemy.orm import Session, sessionmaker


def get_sessionmaker() -> sessionmaker:
    """Return the configured SQLAlchemy session factory."""

    session_factory: sessionmaker | None = current_app.extensions.get(
        "db_sessionmaker"
    )
    if session_factory is None:
        raise RuntimeError("database session factory is not configured")
    return session_factory


def get_db_session() -> Session:
    """Return a database session scoped to the current request context."""

    return get_sessionmaker()()


def get_current_user():
    """Return the authenticated user attached by the auth middleware."""

    user = getattr(g, "current_user", None)
    if user is None:
        raise RuntimeError("no authenticated user on request context")
    return user


def get_current_user_id():
    """Return the authenticated user's id attached by the auth middleware."""

    user_id = getattr(g, "current_user_id", None)
    if user_id is None:
        raise RuntimeError("no authenticated user on request context")
    return user_id
