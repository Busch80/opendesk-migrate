#!/usr/bin/env bash
set -euo pipefail

cd /app

# Apply Alembic migrations only if AUTO_MIGRATE=true
if [[ "${AUTO_MIGRATE:-false}" == "true" ]]; then
  echo "[entrypoint] Running Alembic migrations..."
  alembic upgrade head
fi

# Boot uvicorn
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${WEB_CONCURRENCY:-2}" \
  --proxy-headers \
  --forwarded-allow-ips "*" \
  --log-level "${APP_LOG_LEVEL_UVICORN:-info}"
