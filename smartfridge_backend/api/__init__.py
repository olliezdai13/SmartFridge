"""API package wiring for SmartFridge backend."""

from flask import Flask

from .images import bp as images_bp


def init_app(app: Flask) -> None:
    """Register all API blueprints on the given application."""
    app.register_blueprint(images_bp)
