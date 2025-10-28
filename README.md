# SmartFridge Backend

Backend services for the SmartFridge project. The app accepts camera snapshots from the Raspberry Pi fridge, stores them, and lets us poke a vision-capable LLM until the full ingestion pipeline is ready.

## Quick Start

### 1. Configure environment secrets

```bash
cp .env.example .env.local  # recommended: keep secrets out of version control
```

When using Docker Compose, point to the file with `SMARTFRIDGE_ENV_FILE=.env.local` (see below). For quick experimentation you can edit `.env.example` directly, but avoid committing real credentials to source control.

Required variables (read at startup):

- `SMARTFRIDGE_LLM_API_KEY` – OpenAI key used by the vision client (`OPENAI_API_KEY` works as a fallback)
- `SMARTFRIDGE_UPLOAD_DIR` – optional override for the image storage directory (`data/uploads` by default)

Optional LLM tuning knobs:

- `SMARTFRIDGE_LLM_MODEL` – defaults to `gpt-4o-mini`
- `SMARTFRIDGE_LLM_SYSTEM_PROMPT` – system message injected ahead of user prompts (also used when requests omit a prompt)

Export them with your preferred shell tooling. One option for local work:

```bash
set -a
source .env.local  # or .env.example if you are just experimenting
set +a
```

### 2. Run the server

**Docker (recommended)**

```bash
docker compose up --build
```

To target a different env file (e.g., staging vs. production) set `SMARTFRIDGE_ENV_FILE` when invoking Compose:

```bash
SMARTFRIDGE_ENV_FILE=.env.local docker compose up --build
SMARTFRIDGE_ENV_FILE=.env.staging docker compose up --build
```

By default the service loads variables from `.env.example` so the container has sane defaults even without overrides.

**Local virtualenv**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app smartfridge_backend run --host 0.0.0.0 --port 8000
```

`make install` bootstraps the virtualenv and dependencies if you prefer Make targets.

Verify the health check once the server is live:

```bash
./scripts/healthcheck.sh
```

## LLM Integration

- The server wires up an OpenAI Responses client during startup when an API key is present.
- `/api/llm` accepts an uploaded image filename (prompt optional) and returns the model's plain-text answer.
- Errors surface as JSON with appropriate HTTP codes (`400` validation, `404` missing image, `503` when the client is not configured).
- Future work: ingest responses into storage, enrich result payloads, and feed the data back into the inventory service.

Smoke-test the workflow end-to-end:

```bash
# Upload a photo
curl -X POST http://localhost:8000/api/images \
  -F "image=@/path/to/fridge.jpg"

# Pass it to the LLM
curl -X POST http://localhost:8000/api/llm \
  -H "Content-Type: application/json" \
  -d '{"image_name": "fridge_20240718T194501Z.jpg"}'
```

## API Reference

### POST `/api/images`

- Uploads a fridge snapshot via `multipart/form-data` using the `image` form field.
- Returns the stored filename and directory when successful (`201 Created`).
- Storage location defaults to `data/uploads/` unless `SMARTFRIDGE_UPLOAD_DIR` is set.

### POST `/api/llm`

- Accepts JSON with `image_name` (required) and `prompt` (optional override).
- Falls back to the configured system prompt when `prompt` is omitted.
- Returns `{ "result": "..." }` on success.
- Expects the referenced file to exist in the upload directory and an API key to be configured.

## Project Structure

- `smartfridge_backend/` – Flask application package and app factory.
- `smartfridge_backend/api/` – Blueprints for image and LLM endpoints.
- `smartfridge_backend/services/` – Upload helpers and the OpenAI client wrapper.
- `Dockerfile`, `docker-compose.yml` – Deployment and local development scaffolding.
- `scripts/` – Handy utilities like the health check.

## Maintenance

- Keep Docker and dependency definitions aligned with code changes.
- Update this README whenever endpoint behavior or environment requirements shift.
- Store environment secrets outside of version control and create separate `.env.<stage>` files for each deployment target.
