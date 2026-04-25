#!/usr/bin/env bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-eu-north-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
STATE_BUCKET="${STATE_BUCKET:-swedish-mortgages-terraform-state-${AWS_ACCOUNT_ID}}"
LOCK_TABLE="${LOCK_TABLE:-swedish-mortgages-terraform-locks}"

if ! aws s3api head-bucket --bucket "$STATE_BUCKET" >/dev/null 2>&1; then
  aws s3api create-bucket \
    --bucket "$STATE_BUCKET" \
    --region "$AWS_REGION" \
    --create-bucket-configuration "LocationConstraint=$AWS_REGION"
fi

aws s3api put-bucket-versioning \
  --bucket "$STATE_BUCKET" \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket "$STATE_BUCKET" \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

aws s3api put-public-access-block \
  --bucket "$STATE_BUCKET" \
  --public-access-block-configuration '{
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }'

if ! aws dynamodb describe-table --region "$AWS_REGION" --table-name "$LOCK_TABLE" >/dev/null 2>&1; then
  aws dynamodb create-table \
    --region "$AWS_REGION" \
    --table-name "$LOCK_TABLE" \
    --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH >/dev/null
  aws dynamodb wait table-exists --region "$AWS_REGION" --table-name "$LOCK_TABLE"
fi

cat <<EOF
STATE_BUCKET=$STATE_BUCKET
LOCK_TABLE=$LOCK_TABLE
EOF
