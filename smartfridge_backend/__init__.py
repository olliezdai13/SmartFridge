from flask import Flask, jsonify


def create_app() -> Flask:
    """Application factory for the SmartFridge backend."""
    app = Flask(__name__)

    @app.get("/healthz")
    def healthcheck():
        return jsonify(status="ok")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
