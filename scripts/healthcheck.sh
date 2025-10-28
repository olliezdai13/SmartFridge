#!/usr/bin/env bash
set -euo pipefail

HEALTH_URL="${HEALTH_URL:-http://localhost:8000/healthz}"

echo "Checking SmartFridge backend health at ${HEALTH_URL} ..."
response="$(curl --fail --silent --show-error "${HEALTH_URL}")"

if command -v jq >/dev/null 2>&1; then
    echo "${response}" | jq '.'
else
    echo "${response}" | python3 -m json.tool 2>/dev/null || echo "${response}"
fi

echo "Health check succeeded."
