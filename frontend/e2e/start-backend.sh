#!/usr/bin/env bash
# Start the API and ingestion worker for the end-to-end tests, on a freshly reset database.
# Playwright launches this (see playwright.config.ts) and supplies the environment.
set -euo pipefail
cd "$(dirname "$0")/../../backend"

rm -rf "${UPLOAD_DIR:?}"
mkdir -p "$UPLOAD_DIR"
uv run docqa reset-db --yes

uv run arq docqa.worker.settings.WorkerSettings &
worker=$!
uv run uvicorn docqa.main:create_app --factory --host 127.0.0.1 --port "$E2E_API_PORT" &
api=$!
trap 'kill "$worker" "$api" 2>/dev/null || true; wait' EXIT INT TERM
# Exit (and stop both) as soon as either process dies. (No `wait -n`: macOS ships bash 3.2.)
while kill -0 "$worker" 2>/dev/null && kill -0 "$api" 2>/dev/null; do
  sleep 1
done
exit 1
