# SmartFridge Backend

Backend for accepting fridge camera snapshots, storing them, and running a vision-capable LLM pipeline.

## Prerequisites

- Docker + Docker Compose (recommended flow)
- Python 3.11+ if running without Docker
- `make` is optional; most commands below use plain shell

## Configure Environment

Create `.env.local` (or `.env.<stage>`) with the variables the app reads at startup:

- `SMARTFRIDGE_LLM_API_KEY` (or `OPENAI_API_KEY`) for the vision client
- `DATABASE_URL` (e.g. `postgresql+psycopg://smartfridge:smartfridge@postgres:5432/smartfridge`)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` for the bundled Postgres container
- `SMARTFRIDGE_S3_BUCKET`, `SMARTFRIDGE_S3_REGION`, `SMARTFRIDGE_S3_ENDPOINT_URL`, `SMARTFRIDGE_S3_BASE_PREFIX` for object storage (LocalStack in dev, S3 in prod)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` for the storage client
- `SMARTFRIDGE_API_SHARED_SECRET` token required on all API calls
- `SPOONACULAR_API_KEY` to enable `/api/recipes`
- `WORKER_CONCURRENCY` number of threads the background job consumer will use per process

Switch env files with `SMARTFRIDGE_ENV_FILE=.env.staging docker compose up ...` when you need a different config. To export variables locally:

```bash
set -a && source .env.local && set +a
```

## Run with Docker (recommended)

```bash
docker compose up --build -d
```

This starts the Flask API, Postgres, and LocalStack. Health check once it is up:

```bash
./scripts/healthcheck.sh
```

The backend entrypoint automatically runs `alembic upgrade head` (with retries) on startup so the database schema stays current.

Reload after changing code or dependencies: `docker compose up --build -d` (or `docker compose restart smartfridge-backend` for config-only changes). Inspect logs with `docker compose logs -f smartfridge-backend`.

## Run without Docker

Ensure Postgres and LocalStack are running (you can reuse the Compose services: `docker compose up postgres localstack`). Then:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app smartfridge_backend run --host 0.0.0.0 --port 8000
```

`make install` sets up the venv and dependencies if you prefer Make.

## Database Migrations

Apply migrations:

```bash
docker compose exec smartfridge-backend alembic upgrade head
```

The container runs this automatically on startup; use the command above if you need to re-run manually.

Generate a migration from model changes:

```bash
docker compose exec smartfridge-backend alembic revision --autogenerate -m "describe change"
```

Running outside Docker? Set `DATABASE_URL` and run the same Alembic commands locally.

## Snapshot Workflow

- `/api/snapshot` saves the uploaded image to S3/LocalStack, records a `snapshots` row, and enqueues a `process_snapshot` job.
- A worker downloads the image, runs vision parsing (LLM for now), and writes structured items back to `snapshots` + `items`.
- Status transitions: `pending -> processing -> complete` (or `failed` after retries).

Smoke test:

```bash
curl -X POST http://localhost:8000/api/snapshot \
  -F "image=@/path/to/fridge.jpg" \
  -F "prompt=List items and expiration dates"
```

## API Quick Reference

- Authentication: include the shared secret on every call, either `Authorization: Bearer <token>` or `X-API-Token: <token>`.
- `POST /api/snapshot` — multipart upload with `image` (and optional `prompt`); returns `202` with `snapshot_id`, bucket/key, and initial status. Poll the `snapshots` row to track progress. Example:
  ```bash
  curl -H "Authorization: Bearer $SMARTFRIDGE_API_SHARED_SECRET" \
    -X POST http://localhost:8000/api/snapshot \
    -F "image=@/path/to/fridge.jpg" \
    -F "prompt=List items and expiration dates"
  ```
- `GET /api/recipes` — requires `SPOONACULAR_API_KEY`; returns latest fridge inventory plus the Spoonacular request/response. Example:
  ```bash
  curl -H "Authorization: Bearer $SMARTFRIDGE_API_SHARED_SECRET" \
    http://localhost:8000/api/recipes
  ```

## Local Object Storage

LocalStack runs with Compose and seeds the `smartfridge-snapshots` bucket via `scripts/localstack-init-s3.sh`. When running the app outside Docker, point the client at `http://localhost:4566` via `SMARTFRIDGE_S3_ENDPOINT_URL`. Inspect stored objects:

```bash
docker compose exec localstack awslocal s3 ls s3://smartfridge-snapshots --recursive
```
