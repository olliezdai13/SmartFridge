"""API package wiring for SmartFridge backend."""

from flask import Flask

from .auth import attach_user_from_access_cookie, bp as auth_bp
from .recipes import bp as recipes_bp
from .snapshot import bp as snapshot_bp


def init_app(app: Flask) -> None:
    """Register all API blueprints on the given application."""

    app.before_request(attach_user_from_access_cookie)

    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp)
    app.register_blueprint(snapshot_bp)
