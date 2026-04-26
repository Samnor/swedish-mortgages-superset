# Swedish Mortgages Superset

This repo runs a local Superset app for the Swedish mortgage marts built by
[`Samnor/swedish-mortgages-dbt`](https://github.com/Samnor/swedish-mortgages-dbt).
It is intentionally separate from the dbt repo so the BI app, container
runtime, and network exposure can evolve independently.

## What this app reads

The app is designed around these dbt tables:

- `rates_daily`
- `bank_margin_analysis`
- `bank_vs_market_analysis`

The datasource import file is rendered from `.env`. Use
`ATHENA_SCHEMA=swedish_mortgages_dev_marts` for dev and
`ATHENA_SCHEMA=swedish_mortgages_prod_marts` for prod.

## Repo layout

- `docker-compose.yml`: local Superset runtime exposed on `0.0.0.0`
- `Dockerfile`: installs the Athena SQLAlchemy driver
- `custom_pythonpath/superset_config.py`: small local config overrides
- `assets/datasources/swedish_mortgages.template.yaml`: datasource template
- `scripts/render_datasources.py`: renders importable datasource metadata

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- Athena-access AWS credentials
- The dbt mortgage marts already built in Athena

## Quick start

1. Copy `.env.example` to `.env`.
2. Fill in the admin credentials, Superset secret, and AWS credentials.
3. Start the app:

```bash
cd /Volumes/ExternalSSD/dataengineering/swedish-mortgages-superset
docker compose up -d --build
```

4. Open Superset:

```text
http://<your-lan-ip>:8088
```

If Tailscale runs on the host machine, the same port is reachable at:

```text
http://<your-tailscale-ip>:8088
```

## Create the Athena database connection in Superset

After the container is up, sign in and add a database with the name:

```text
Athena Swedish Mortgages
```

Use this SQLAlchemy URI pattern so PyAthena picks up the container's AWS
environment credentials:

```text
awsathena+rest://@athena.eu-north-1.amazonaws.com/awsdatacatalog?work_group=primary&s3_staging_dir=s3%3A%2F%2FYOUR-ATHENA-QUERY-RESULTS%2Fdbt-results%2F
```

Adjust the region, catalog, workgroup, or staging dir if your `.env` differs.

## Import the mortgage datasets

Once the database exists in Superset, import the datasource metadata:

```bash
cd /Volumes/ExternalSSD/dataengineering/swedish-mortgages-superset
docker compose exec superset superset import_datasources -p /app/codex_assets/datasources/swedish_mortgages.yaml -u admin
```

`make import-datasources` renders the datasource YAML from `.env` before
running the import.

## Network notes

- The container binds to `0.0.0.0:${SUPERSET_PORT}` so it is visible on local
  Wi-Fi and to Tailscale traffic reaching the host.
- This repo is for LAN or Tailscale access, not public internet exposure.
- If you later put it behind a reverse proxy, `superset_config.py` already
  enables proxy header handling.

## Dev Tailscale proxy auth key

For AWS dev, store the temporary Tailscale auth key in SSM Parameter Store
instead of putting it directly in Terraform variables:

```bash
aws ssm put-parameter \
  --region eu-north-1 \
  --name /swedish-mortgages/dev/tailscale/auth-key \
  --type SecureString \
  --value '<temporary-tskey-auth-value>' \
  --overwrite
```

Set `tailscale_auth_key_ssm_parameter_name` in `dev.tfvars`. The EC2 proxy
reads the key once at first boot, and Terraform ignores later `user_data`
changes so revoking or rotating the key does not replace the proxy.

## AWS Superset secrets

Terraform creates the Secrets Manager containers, but live Superset values are
written outside Terraform state:

```bash
export ENVIRONMENT=dev
export AWS_REGION=eu-north-1
export SUPERSET_SECRET_KEY='<random-secret-key>'
export SUPERSET_ADMIN_PASSWORD='<admin-password>'

scripts/put_superset_secrets.sh
```

The script reads the RDS host/name/username from Terraform outputs and, when
`manage_db_master_password=true`, reads the RDS-managed password from AWS
Secrets Manager. If you disable RDS-managed passwords, set `DB_PASSWORD`
explicitly before running it. It writes:

- `/swedish-mortgages/dev/superset/secret-key`
- `/swedish-mortgages/dev/superset/admin-password`
- `/swedish-mortgages/dev/superset/database-uri`

## Next steps

- Add richer charts beyond the starter dashboard for rate history, bank
  margins, and bank-vs-market comparisons.
- Point the app at `swedish_mortgages_prod_marts` for production.
- Add a dbt exposure in the dbt repo with the final Superset dashboard URL.

## Dev and Prod Deployment

See `docs/environments.md`. GitHub Actions deploys through protected GitHub
Environments. The `dev` environment should read `swedish_mortgages_dev_marts`;
`prod` should read `swedish_mortgages_prod_marts`.
