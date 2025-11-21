"""API package wiring for SmartFridge backend."""

from flask import Flask

from .snapshot import bp as snapshot_bp


def init_app(app: Flask) -> None:
    """Register all API blueprints on the given application."""
    app.register_blueprint(snapshot_bp)
