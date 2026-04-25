output "alb_dns_name" {
  value = aws_lb.superset.dns_name
}

output "ecr_repository" {
  value = aws_ecr_repository.superset.name
}

output "ecs_cluster" {
  value = aws_ecs_cluster.superset.name
}

output "ecs_service" {
  value = aws_ecs_service.superset.name
}

output "ecs_task_family" {
  value = aws_ecs_task_definition.superset.family
}

output "ecs_execution_role_arn" {
  value = aws_iam_role.execution.arn
}

output "ecs_task_role_arn" {
  value = aws_iam_role.task.arn
}

output "ecs_log_group" {
  value = aws_cloudwatch_log_group.superset.name
}

output "github_role_arn" {
  value = aws_iam_role.github_deploy.arn
}

output "superset_secret_key_secret_arn" {
  value = aws_secretsmanager_secret.secret_key.arn
}

output "superset_admin_password_secret_arn" {
  value = aws_secretsmanager_secret.admin_password.arn
}

output "superset_database_uri_secret_arn" {
  value = aws_secretsmanager_secret.database_uri.arn
}

output "tailscale_proxy_public_ip" {
  value = var.tailscale_proxy_enabled ? aws_instance.tailscale_proxy[0].public_ip : null
}

output "tailscale_hostname" {
  value = var.tailscale_proxy_enabled ? local.tailscale_hostname : null
}
