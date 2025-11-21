# SmartFridge Backend

Backend services for the SmartFridge project. The app accepts camera snapshots from the Raspberry Pi fridge, stores them, and lets us poke a vision-capable LLM until the full ingestion pipeline is ready.

## Quick Start

### 1. Configure environment secrets

All runtime configuration lives in `.env.local`. Update the values in that file before starting services. If you need multiple variants (e.g., staging), create another file such as `.env.staging` and point Docker Compose at it via `SMARTFRIDGE_ENV_FILE` (details below).

Required variables (read at startup):

- `SMARTFRIDGE_LLM_API_KEY` – OpenAI key used by the vision client (`OPENAI_API_KEY` works as a fallback)
- `DATABASE_URL` – SQLAlchemy-style Postgres URL (use the psycopg dialect, e.g. `postgresql+psycopg://smartfridge:smartfridge@postgres:5432/smartfridge`)
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` – credentials injected into the bundled Postgres container (only needed if you override the defaults)
- `SMARTFRIDGE_S3_BUCKET`, `SMARTFRIDGE_S3_REGION`, `SMARTFRIDGE_S3_ENDPOINT_URL`, `SMARTFRIDGE_S3_BASE_PREFIX` – configure where snapshots are stored (point at LocalStack for development or an actual S3 endpoint in production)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` – credentials the storage client uses (LocalStack accepts any values; production requires real IAM secrets or roles)

Optional LLM tuning knobs:

- `SMARTFRIDGE_LLM_MODEL` – defaults to `gpt-4o-mini`
- `SMARTFRIDGE_LLM_SYSTEM_PROMPT` – system message injected ahead of user prompts (also used when requests omit a prompt)

Export them with your preferred shell tooling. One option for local work:

```bash
set -a
source .env.local
set +a
```

### 2. Run the server

**Docker (recommended)**

```bash
docker compose up --build
```

This brings up Postgres, LocalStack (for the S3-compatible bucket), and the Flask API in one shot. To target a different env file (e.g., staging vs. production) set `SMARTFRIDGE_ENV_FILE` when invoking Compose:

```bash
SMARTFRIDGE_ENV_FILE=.env.local docker compose up --build
SMARTFRIDGE_ENV_FILE=.env.staging docker compose up --build
```

By default the service loads variables from `.env.local` so the container has sane defaults even without overrides.

**Local virtualenv**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app smartfridge_backend run --host 0.0.0.0 --port 8000
```

`make install` bootstraps the virtualenv and dependencies if you prefer Make targets.

### 3. Apply database migrations

Alembic migrations live under `migrations/`. Run them whenever the schema changes:

```bash
# example: running locally against the Compose Postgres instance
DATABASE_URL=postgresql+psycopg://smartfridge:smartfridge@localhost:5432/smartfridge \
  alembic upgrade head

# or, inside the container where DATABASE_URL already points at postgres
docker compose exec smartfridge-backend alembic upgrade head
```

`alembic revision --autogenerate -m "..."` inspects the models in `smartfridge_backend/models/` and creates new migration files.

Verify the health check once the server is live:

```bash
./scripts/healthcheck.sh
```

## Snapshot Workflow

- The server wires up an OpenAI Responses client during startup when an API key is present.
- `/api/snapshot` accepts `multipart/form-data` with `image` (required) and `prompt` (optional) in a single request.
- The backend persists the photo into the configured S3 bucket (LocalStack in development), queries the vision model, and responds with the raw text plus best-effort JSON parsing.
- Errors surface as JSON with appropriate HTTP codes (`400` validation, `503` when the client is not configured, etc.).

Smoke-test the workflow end-to-end:

```bash
curl -X POST http://localhost:8000/api/snapshot \
  -F "image=@/path/to/fridge.jpg" \
  -F "prompt=List items and expiration dates"
```

## API Reference

### POST `/api/snapshot`

- Uploads a fridge snapshot via `multipart/form-data` using the `image` form field.
- Optional `prompt` overrides the configured system prompt for the LLM call.
- Returns the stored filename, S3 bucket/key, LLM output (`raw`, `json`, `result_json`). (`201 Created`).
- Storage is backed by S3-compatible object storage; in development, LocalStack provides the bucket defined in `SMARTFRIDGE_S3_BUCKET`.

## Local Object Storage (LocalStack)

- `docker compose up` now starts a `localstack` container alongside the backend and Postgres.
- The helper script in `scripts/localstack-init-s3.sh` automatically creates the `smartfridge-snapshots` bucket via `awslocal`.
- Default credentials/endpoint live in `.env.local` (the endpoint is `http://localstack:4566` so containers talk to the LocalStack service over Docker's network). When running the Flask app outside of Docker, export `SMARTFRIDGE_S3_ENDPOINT_URL=http://localhost:4566` so the client reaches LocalStack from the host machine.
- Objects are written under `snapshots/user-<id>/...`; for now the snapshot API stores uploads for `user-1` until multi-user plumbing is in place.
- Inspect stored snapshots via the LocalStack CLI:

  ```bash
  docker compose exec localstack awslocal s3 ls s3://smartfridge-snapshots --recursive
  ```

- Objects persist until you destroy the LocalStack container. Use `docker compose down -v` to wipe all mock S3 data (or remove individual keys with `awslocal s3 rm`).

## Project Structure

- `smartfridge_backend/` – Flask application package and app factory.
- `smartfridge_backend/api/` – Blueprint that owns the `/api/snapshot` endpoint.
- `smartfridge_backend/models/` – SQLAlchemy models and metadata used by Alembic.
- `smartfridge_backend/services/` – Upload helpers, the OpenAI client wrapper, and the S3 storage client.
- `Dockerfile`, `docker-compose.yml` – Deployment and local development scaffolding.
- `scripts/` – Handy utilities like the health check.

## Maintenance

- Keep Docker and dependency definitions aligned with code changes.
- Update this README whenever endpoint behavior or environment requirements shift.
- Store environment secrets outside of version control and create separate `.env.<stage>` files for each deployment target.
