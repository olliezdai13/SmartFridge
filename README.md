# SmartFridge Backend

This repository hosts the backend for the SmartFridge project, a student-built platform that ingests camera snapshots from a Raspberry Pi-powered fridge, enriches them with AI, and exposes the results to companion apps. The backend is packaged for deployment on a small VPS via Docker.

## Stack Overview

- **Flask** – Lightweight Python framework handling HTTP endpoints for image uploads, inventory queries, and business logic orchestration.
- **Caddy** – Front-door web server and reverse proxy that terminates TLS, handles automatic Let’s Encrypt certificates, and forwards requests to the Flask app.
- **Docker** – Containerizes the entire stack so the Raspberry Pi client and server share reproducible environments, simplifying deployment to a small cloud VPS.

## Project Goals

1. Receive and store fridge images uploaded from the Raspberry Pi.
2. Run AI-backed analysis (LLM/computer vision) on the images to identify items and status.
3. Serve REST endpoints that the mobile or web SmartFridge app can call for real-time updates and notifications.
4. Stay lean enough for student infrastructure: one VPS, Docker Compose, and a straightforward deployment pipeline.

## Project Structure

- `smartfridge_backend/` – Flask application package with a lightweight health check route and space for future API modules.
- `wsgi.py` – Gunicorn entry point that exposes the Flask application.
- `requirements.txt` – Python dependencies installed into the Docker image.
- `Dockerfile` – Production-ready image using `gunicorn` and Python 3.12.
- `docker-compose.yml` – Local orchestration that mirrors the target VPS setup.

## Getting Started

### Run with Docker (recommended)

```bash
docker compose up --build
```

The service listens on port `8000`. In production, place Caddy or your preferred reverse proxy in front of the container to terminate TLS and forward traffic to `smartfridge-backend:8000`.

Verify the container is healthy:

```bash
./scripts/healthcheck.sh
```

### Manual setup (for quick iteration)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
FLASK_APP=smartfridge_backend flask run --host 0.0.0.0 --port 8000
```

With the server running locally, confirm the health endpoint:

```bash
./scripts/healthcheck.sh
```

## Status

The repository now contains the initial Flask scaffold and Docker tooling. Expand the `smartfridge_backend` package with modules for image ingestion, AI enrichment, persistence, and REST endpoints as features are designed.

## Maintenance

- Keep Docker and dependency definitions in sync with the evolving codebase.
- After every major structural change to the application, update all relevant sections of this README so installation, deployment, and architecture notes stay accurate.
