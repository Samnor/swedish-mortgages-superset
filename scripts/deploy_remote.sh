#!/usr/bin/env bash
set -euo pipefail

: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${SUPERSET_SECRET_KEY:?SUPERSET_SECRET_KEY is required}"
: "${SUPERSET_ADMIN_USERNAME:?SUPERSET_ADMIN_USERNAME is required}"
: "${SUPERSET_ADMIN_PASSWORD:?SUPERSET_ADMIN_PASSWORD is required}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is required}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is required}"
: "${ATHENA_S3_STAGING_DIR:?ATHENA_S3_STAGING_DIR is required}"

cd "$DEPLOY_PATH"

git fetch --prune origin
git checkout "${DEPLOY_BRANCH:-main}"
git pull --ff-only origin "${DEPLOY_BRANCH:-main}"

cat > .env <<ENV
SUPERSET_PORT=${SUPERSET_PORT:-8088}
SUPERSET_SECRET_KEY=${SUPERSET_SECRET_KEY}
SUPERSET_ADMIN_USERNAME=${SUPERSET_ADMIN_USERNAME}
SUPERSET_ADMIN_FIRSTNAME=${SUPERSET_ADMIN_FIRSTNAME:-Superset}
SUPERSET_ADMIN_LASTNAME=${SUPERSET_ADMIN_LASTNAME:-Admin}
SUPERSET_ADMIN_EMAIL=${SUPERSET_ADMIN_EMAIL:-admin@example.com}
SUPERSET_ADMIN_PASSWORD=${SUPERSET_ADMIN_PASSWORD}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}
AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-eu-north-1}
ATHENA_REGION=${ATHENA_REGION:-eu-north-1}
ATHENA_DATABASE=${ATHENA_DATABASE:-awsdatacatalog}
ATHENA_SCHEMA=${ATHENA_SCHEMA:-swedish_mortgages_dev_marts}
ATHENA_WORK_GROUP=${ATHENA_WORK_GROUP:-primary}
ATHENA_S3_STAGING_DIR=${ATHENA_S3_STAGING_DIR}
SUPERSET_DATABASE_NAME=${SUPERSET_DATABASE_NAME:-Athena Swedish Mortgages}
TAILSCALE_BASE_URL=${TAILSCALE_BASE_URL:-}
ENV

python3 scripts/render_datasources.py
docker compose up -d --build
docker compose exec -T superset superset import_datasources -p /app/codex_assets/datasources/swedish_mortgages.yaml -u "${SUPERSET_ADMIN_USERNAME}"
docker compose exec -T superset python /app/codex_assets/custom/create_mortgage_dashboard.py
