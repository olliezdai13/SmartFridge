"""Shared API dependencies and helpers."""

from flask import current_app
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
