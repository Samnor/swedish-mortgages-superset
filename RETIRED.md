# Retired

This Superset app was retired on 2026-04-26.

The replacement public dashboard is:

```text
https://salaguno.com/mortgages/
```

## Do Not Redeploy

Do not run:

```bash
terraform apply
```

or the `Deploy Superset` GitHub Actions workflow from this repo.

The AWS resources managed by this repo were intentionally removed directly to
stop recurring costs:

- ECS services and clusters
- Application Load Balancers and target groups
- RDS Superset metadata databases
- Dev Tailscale proxy EC2 instance
- ECR repositories
- Secrets Manager Superset secrets
- CloudWatch Superset log groups

The Terraform state is historical and no longer represents live AWS resources.
