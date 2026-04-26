## Release Checklist

Use this template for release PRs from `develop` to `main`.

- [ ] dbt dev deployment has completed successfully.
- [ ] Superset dev deployment has completed successfully.
- [ ] Dev Superset has been checked manually.
- [ ] Production impact is understood.
- [ ] Rollback path is known.
- [ ] Secrets, GitHub environment variables, and Terraform variables are unchanged or reviewed.

## Notes

Describe the user-visible or operational changes in this release.

## Rollback

Describe the quickest rollback path. For Superset-only changes, this is usually
redeploying the previous ECS task definition revision.
