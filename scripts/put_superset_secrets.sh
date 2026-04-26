#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-eu-north-1}"
NAME_PREFIX="${NAME_PREFIX:-swedish-mortgages}"
TF_DIR="${TF_DIR:-infra/terraform}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

require_env SUPERSET_SECRET_KEY
require_env SUPERSET_ADMIN_PASSWORD

tf_output() {
  terraform -chdir="${TF_DIR}" output -raw "$1" 2>/dev/null || true
}

DB_INSTANCE_ID="${DB_INSTANCE_ID:-${NAME_PREFIX}-${ENVIRONMENT}-superset}"
DB_HOST="${DB_HOST:-$(tf_output db_address)}"
DB_NAME="${DB_NAME:-$(tf_output db_name)}"
DB_USERNAME="${DB_USERNAME:-$(tf_output db_username)}"
DB_MASTER_SECRET_ARN="${DB_MASTER_SECRET_ARN:-$(tf_output db_master_user_secret_arn)}"

if [[ -z "${DB_HOST}" || -z "${DB_NAME}" || -z "${DB_USERNAME}" || -z "${DB_MASTER_SECRET_ARN}" ]]; then
  DB_DESCRIPTION="$(aws rds describe-db-instances \
    --region "${AWS_REGION}" \
    --db-instance-identifier "${DB_INSTANCE_ID}" \
    --query 'DBInstances[0].[Endpoint.Address,DBName,MasterUsername,MasterUserSecret.SecretArn]' \
    --output text)"

  read -r DB_HOST DB_NAME DB_USERNAME DB_MASTER_SECRET_ARN <<<"${DB_DESCRIPTION}"
fi

if [[ -z "${DB_PASSWORD:-}" && -n "${DB_MASTER_SECRET_ARN}" && "${DB_MASTER_SECRET_ARN}" != "None" ]]; then
  DB_SECRET_JSON="$(aws secretsmanager get-secret-value \
    --region "${AWS_REGION}" \
    --secret-id "${DB_MASTER_SECRET_ARN}" \
    --query SecretString \
    --output text)"
  DB_PASSWORD="$(DB_SECRET_JSON="${DB_SECRET_JSON}" python3 - <<'PY'
import json
import os

print(json.loads(os.environ["DB_SECRET_JSON"])["password"])
PY
)"
fi

require_env DB_PASSWORD

put_secret() {
  local name="$1"
  local value="$2"

  aws secretsmanager put-secret-value \
    --region "${AWS_REGION}" \
    --secret-id "${name}" \
    --secret-string "${value}" >/dev/null
}

DATABASE_URI="postgresql+psycopg2://${DB_USERNAME}:${DB_PASSWORD}@${DB_HOST}:5432/${DB_NAME}"

put_secret "/${NAME_PREFIX}/${ENVIRONMENT}/superset/secret-key" "${SUPERSET_SECRET_KEY}"
put_secret "/${NAME_PREFIX}/${ENVIRONMENT}/superset/admin-password" "${SUPERSET_ADMIN_PASSWORD}"
put_secret "/${NAME_PREFIX}/${ENVIRONMENT}/superset/database-uri" "${DATABASE_URI}"

echo "Updated Superset secrets for ${ENVIRONMENT} in ${AWS_REGION}."
