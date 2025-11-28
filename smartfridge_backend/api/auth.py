"""Lightweight shared-secret guard for API endpoints."""

from __future__ import annotations

from flask import current_app, jsonify, request


def require_shared_secret():
    """Enforce the presence of the configured shared secret on incoming requests."""

    shared_secret = current_app.config.get("API_SHARED_SECRET")
    if not shared_secret:
        return jsonify(error="API shared secret is not configured"), 503

    token = _extract_token()
    if not token or token != shared_secret:
        return jsonify(error="unauthorized"), 401

    return None


def _extract_token() -> str | None:
    """Pull a bearer token or fallback header from the request."""

    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    return request.headers.get("X-API-Token")
