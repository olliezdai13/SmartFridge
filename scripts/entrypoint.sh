#!/usr/bin/env bash
set -euo pipefail

log() {
  echo "[$(date -Iseconds)] $*"
}

run_migrations() {
  # Skip when DATABASE_URL is not available (e.g., healthcheck builds)
  if [[ -z "${DATABASE_URL:-}" ]]; then
    log "DATABASE_URL not set; skipping alembic upgrade"
    return 0
  fi

  local attempts=2
  local delay=3

  for attempt in $(seq 1 "${attempts}"); do
    if alembic upgrade head; then
      log "alembic upgrade head succeeded"
      return 0
    fi

    if [[ "${attempt}" -eq "${attempts}" ]]; then
      log "alembic upgrade head failed after ${attempts} attempts"
      return 1
    fi

    log "alembic upgrade head failed (attempt ${attempt}/${attempts}); retrying in ${delay}s"
    sleep "${delay}"
  done
}

log "starting SmartFridge backend entrypoint"
run_migrations

exec "$@"
