"""API package wiring for SmartFridge backend."""

from flask import Flask

from .auth import require_shared_secret
from .recipes import bp as recipes_bp
from .snapshot import bp as snapshot_bp


def init_app(app: Flask) -> None:
    """Register all API blueprints on the given application."""

    _protect_blueprint(recipes_bp)
    _protect_blueprint(snapshot_bp)

    app.register_blueprint(recipes_bp)
    app.register_blueprint(snapshot_bp)


def _protect_blueprint(bp):
    @bp.before_request
    def _require_secret():
        return require_shared_secret()
