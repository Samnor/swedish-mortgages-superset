# Release Flow

This project uses a lightweight release flow:

1. Merge normal work into `develop`.
2. Let `develop` deploy to dev.
3. Check dev manually.
4. Open a release PR from `develop` to `main`.
5. Merge the release PR.
6. Approve the `prod` GitHub Environment deployment.
7. Check production health.

## Order

dbt must be released before Superset for the same environment. Superset imports
datasets that point at dbt-managed Athena Iceberg relations.

For production:

1. Release dbt to prod.
2. Confirm prod marts are available.
3. Release Superset to prod.
4. Check `https://superset.salaguno.com/health`.
5. Run one simple Superset/Athena query against a key dataset.

## Branches

- `develop` is the dev/integration branch.
- `main` is the production branch.

Production deployments run from `main` and require GitHub Environment approval.

## Rollback

For a Superset-only rollback, redeploy the previous ECS task definition revision.

Avoid destructive dbt changes in production unless they have an explicit rollback
or restore plan.
