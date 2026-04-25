#!/usr/bin/env bash
set -euo pipefail

: "${SUPERSET_SECRET_KEY:?SUPERSET_SECRET_KEY is required}"
: "${SUPERSET_ADMIN_USERNAME:?SUPERSET_ADMIN_USERNAME is required}"
: "${SUPERSET_ADMIN_PASSWORD:?SUPERSET_ADMIN_PASSWORD is required}"
: "${ATHENA_S3_STAGING_DIR:?ATHENA_S3_STAGING_DIR is required}"

CODEX_ASSETS_DIR=/app/codex_assets python /app/codex_scripts/render_datasources.py

superset db upgrade
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME}" \
  --firstname "${SUPERSET_ADMIN_FIRSTNAME:-Superset}" \
  --lastname "${SUPERSET_ADMIN_LASTNAME:-Admin}" \
  --email "${SUPERSET_ADMIN_EMAIL:-admin@example.com}" \
  --password "${SUPERSET_ADMIN_PASSWORD}" 2>/dev/null || true
superset init
superset import_datasources -p /app/codex_assets/datasources/swedish_mortgages.yaml -u "${SUPERSET_ADMIN_USERNAME}" || true
python /app/codex_assets/custom/create_mortgage_dashboard.py || true

exec superset run -h 0.0.0.0 -p "${SUPERSET_PORT:-8088}" --with-threads
