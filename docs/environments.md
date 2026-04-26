# Environments

## Design

The Superset app follows the same environment split as the dbt project:

- `dev` reads `swedish_mortgages_dev_marts`
- `prod` reads `swedish_mortgages_prod_marts`

The dbt deployment must run before Superset deployment for the same environment,
because Superset imports datasets that point at dbt-managed Athena Iceberg
relations.

## Runtime Architecture

Superset runs on ECS Fargate behind an Application Load Balancer.

Each environment has separate:

- ECS cluster, service, and task definition
- ALB target group and security groups
- CloudWatch log group
- RDS Postgres metadata database
- Secrets Manager secrets
- ECS task role
- GitHub Actions OIDC deploy role

Production additionally uses an HTTPS listener with an ACM certificate and a
Route53 alias record for `superset.salaguno.com`. Development remains behind an
internal ALB and Tailscale access.

The ECR repository is shared and images are tagged with:

```text
dev-<git-sha>
prod-<git-sha>
```

## Secrets

Runtime secrets live in AWS Secrets Manager:

- `/swedish-mortgages/<env>/superset/secret-key`
- `/swedish-mortgages/<env>/superset/admin-password`
- `/swedish-mortgages/<env>/superset/database-uri`

GitHub should not store Superset admin passwords, database URLs, or AWS access
keys. GitHub Actions assumes an AWS role through OIDC.

## GitHub Environment Variables

Set these variables on both GitHub Environments, using the matching Terraform
outputs for `dev` and `prod`:

- `AWS_REGION`
- `AWS_ROLE_ARN`
- `ECR_REPOSITORY`
- `ECS_CLUSTER`
- `ECS_SERVICE`
- `ECS_TASK_FAMILY`
- `ECS_EXECUTION_ROLE_ARN`
- `ECS_TASK_ROLE_ARN`
- `ECS_LOG_GROUP`
- `SUPERSET_PORT`
- `SUPERSET_DATABASE_NAME`
- `SUPERSET_ADMIN_USERNAME`
- `SUPERSET_ADMIN_FIRSTNAME`
- `SUPERSET_ADMIN_LASTNAME`
- `SUPERSET_ADMIN_EMAIL`
- `ATHENA_REGION`
- `ATHENA_DATABASE`
- `ATHENA_SCHEMA`
- `ATHENA_WORK_GROUP`
- `ATHENA_S3_STAGING_DIR`
- `SUPERSET_SECRET_KEY_SECRET_ARN`
- `SUPERSET_ADMIN_PASSWORD_SECRET_ARN`
- `SUPERSET_DATABASE_URI_SECRET_ARN`

## Terraform

Infrastructure lives in `infra/terraform`.

Example:

```bash
cd infra/terraform
terraform init
terraform plan -var-file=dev.tfvars
terraform apply -var-file=dev.tfvars
```

Do not commit real `*.tfvars` files. Use the `.example` files as templates.
