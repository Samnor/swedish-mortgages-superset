# Environments

## Design

The Superset app follows the same environment split as the dbt project:

- `dev` reads `swedish_mortgages_dev_marts`
- `prod` reads `swedish_mortgages_prod_marts`

The dbt deployment must run before Superset deployment for the same environment,
because Superset imports datasets that point at dbt-managed Athena relations.

## GitHub Environments

Create two GitHub Environments in this repo:

- `dev`: deploys from `develop` or manual dispatch
- `prod`: deploys from `main` and should require approval

Environment variables:

- `SUPERSET_DEPLOY_HOST`
- `SUPERSET_DEPLOY_PORT`
- `SUPERSET_DEPLOY_USER`
- `SUPERSET_DEPLOY_PATH`
- `SUPERSET_PORT`
- `SUPERSET_DATABASE_NAME`
- `SUPERSET_ADMIN_USERNAME`
- `SUPERSET_ADMIN_FIRSTNAME`
- `SUPERSET_ADMIN_LASTNAME`
- `SUPERSET_ADMIN_EMAIL`
- `AWS_DEFAULT_REGION`
- `ATHENA_REGION`
- `ATHENA_DATABASE`
- `ATHENA_SCHEMA`
- `ATHENA_WORK_GROUP`
- `ATHENA_S3_STAGING_DIR`
- `TAILSCALE_BASE_URL`

Environment secrets:

- `SUPERSET_DEPLOY_SSH_KEY`
- `SUPERSET_SECRET_KEY`
- `SUPERSET_ADMIN_PASSWORD`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` when temporary credentials are used

## Deployment Host

The remote host should have:

- Docker and Docker Compose
- this repository cloned at `SUPERSET_DEPLOY_PATH`
- SSH access for `SUPERSET_DEPLOY_USER`
- network access to Athena and to users through LAN, VPN, or Tailscale

The deploy workflow writes the environment-specific `.env`, renders datasource
metadata, starts Superset, imports datasets, and bootstraps the dashboard.
