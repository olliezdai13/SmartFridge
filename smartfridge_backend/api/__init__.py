"""API package wiring for SmartFridge backend."""

from flask import Flask

from .auth import authenticate_request, bp as auth_bp
from .latest import bp as latest_bp
from .recipes import bp as recipes_bp
from .snapshot import bp as snapshot_bp


def init_app(app: Flask) -> None:
    """Register all API blueprints on the given application."""

    app.register_blueprint(auth_bp)

    _protect_blueprint(recipes_bp)
    _protect_blueprint(snapshot_bp)
    _protect_blueprint(latest_bp)

    app.register_blueprint(recipes_bp)
    app.register_blueprint(snapshot_bp)
    app.register_blueprint(latest_bp)


def _protect_blueprint(bp):
    @bp.before_request
    def _require_auth():
        return authenticate_request()
