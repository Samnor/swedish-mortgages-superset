data "aws_caller_identity" "current" {}

locals {
  name               = "${var.name_prefix}-${var.environment}-superset"
  db_name            = "superset_${var.environment}"
  tailscale_hostname = var.tailscale_hostname == "" ? local.name : var.tailscale_hostname
  common_tags = {
    Project     = "swedish-mortgages"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_ecr_repository" "superset" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "superset" {
  name              = "/ecs/${local.name}"
  retention_in_days = var.environment == "prod" ? 30 : 7
  tags              = local.common_tags
}

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb"
  description = "Superset ALB ingress"
  vpc_id      = var.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  for_each = toset(var.allowed_ingress_cidrs)

  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = each.value
  from_port         = var.certificate_arn == "" ? 80 : 443
  ip_protocol       = "tcp"
  to_port           = var.certificate_arn == "" ? 80 : 443
}

resource "aws_vpc_security_group_egress_rule" "alb_all" {
  security_group_id = aws_security_group.alb.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "ecs" {
  name        = "${local.name}-ecs"
  description = "Superset ECS tasks"
  vpc_id      = var.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  from_port                    = 8088
  ip_protocol                  = "tcp"
  to_port                      = 8088
}

resource "aws_vpc_security_group_egress_rule" "ecs_all" {
  security_group_id = aws_security_group.ecs.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_security_group" "db" {
  name        = "${local.name}-db"
  description = "Superset metadata Postgres"
  vpc_id      = var.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_ingress_rule" "db_from_ecs" {
  security_group_id            = aws_security_group.db.id
  referenced_security_group_id = aws_security_group.ecs.id
  from_port                    = 5432
  ip_protocol                  = "tcp"
  to_port                      = 5432
}

resource "aws_vpc_security_group_egress_rule" "db_all" {
  security_group_id = aws_security_group.db.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_db_subnet_group" "superset" {
  name       = local.name
  subnet_ids = var.private_subnet_ids
  tags       = local.common_tags
}

resource "aws_db_instance" "superset" {
  identifier             = local.name
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  db_name                = local.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.superset.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  skip_final_snapshot    = var.environment == "dev"
  deletion_protection    = var.environment == "prod"
  storage_encrypted      = true
  tags                   = local.common_tags
}

resource "aws_secretsmanager_secret" "secret_key" {
  name = "/swedish-mortgages/${var.environment}/superset/secret-key"
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id     = aws_secretsmanager_secret.secret_key.id
  secret_string = var.superset_secret_key
}

resource "aws_secretsmanager_secret" "admin_password" {
  name = "/swedish-mortgages/${var.environment}/superset/admin-password"
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "admin_password" {
  secret_id     = aws_secretsmanager_secret.admin_password.id
  secret_string = var.superset_admin_password
}

resource "aws_secretsmanager_secret" "database_uri" {
  name = "/swedish-mortgages/${var.environment}/superset/database-uri"
  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "database_uri" {
  secret_id = aws_secretsmanager_secret.database_uri.id
  secret_string = format(
    "postgresql+psycopg2://%s:%s@%s:5432/%s",
    var.db_username,
    var.db_password,
    aws_db_instance.superset.address,
    local.db_name
  )
}

resource "aws_lb" "superset" {
  name               = substr(replace(local.name, "-", ""), 0, 32)
  internal           = var.internal_alb
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids
  tags               = local.common_tags
}

resource "aws_lb_target_group" "superset" {
  name        = substr(replace("${local.name}-tg", "-", ""), 0, 32)
  port        = 8088
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/health"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 5
  }

  tags = local.common_tags
}

resource "aws_lb_listener" "superset" {
  load_balancer_arn = aws_lb.superset.arn
  port              = var.certificate_arn == "" ? 80 : 443
  protocol          = var.certificate_arn == "" ? "HTTP" : "HTTPS"
  certificate_arn   = var.certificate_arn == "" ? null : var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.superset.arn
  }
}

resource "aws_ecs_cluster" "superset" {
  name = "${local.name}-cluster"
  tags = local.common_tags
}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${local.name}-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.secret_key.arn,
        aws_secretsmanager_secret.admin_password.arn,
        aws_secretsmanager_secret.database_uri.arn
      ]
    }]
  })
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "task_athena" {
  name = "${local.name}-athena"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup",
          "athena:StopQueryExecution",
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          var.data_lake_bucket_arn,
          "${var.data_lake_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:AbortMultipartUpload"]
        Resource = [
          var.athena_results_bucket_arn,
          "${var.athena_results_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_ecs_task_definition" "superset" {
  family                   = local.name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "superset"
    image     = var.container_image
    essential = true
    portMappings = [{
      containerPort = 8088
      hostPort      = 8088
      protocol      = "tcp"
    }]
    environment = [
      { name = "SUPERSET_CONFIG_PATH", value = "/app/pythonpath/superset_config.py" },
      { name = "SUPERSET_PORT", value = "8088" },
      { name = "SUPERSET_DATABASE_NAME", value = "Athena Swedish Mortgages" },
      { name = "SUPERSET_ADMIN_USERNAME", value = "admin" },
      { name = "SUPERSET_ADMIN_FIRSTNAME", value = "Superset" },
      { name = "SUPERSET_ADMIN_LASTNAME", value = "Admin" },
      { name = "SUPERSET_ADMIN_EMAIL", value = "admin@example.com" },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      { name = "ATHENA_REGION", value = var.aws_region },
      { name = "ATHENA_DATABASE", value = "awsdatacatalog" },
      { name = "ATHENA_SCHEMA", value = var.athena_schema },
      { name = "ATHENA_WORK_GROUP", value = "primary" },
      { name = "ATHENA_S3_STAGING_DIR", value = var.athena_s3_staging_dir },
      { name = "TAILSCALE_BASE_URL", value = "" }
    ]
    secrets = [
      { name = "SUPERSET_SECRET_KEY", valueFrom = aws_secretsmanager_secret.secret_key.arn },
      { name = "SUPERSET_ADMIN_PASSWORD", valueFrom = aws_secretsmanager_secret.admin_password.arn },
      { name = "SUPERSET_DATABASE_URI", valueFrom = aws_secretsmanager_secret.database_uri.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-region        = var.aws_region
        awslogs-group         = aws_cloudwatch_log_group.superset.name
        awslogs-stream-prefix = "superset"
      }
    }
  }])

  tags = local.common_tags
}

resource "aws_ecs_service" "superset" {
  name            = local.name
  cluster         = aws_ecs_cluster.superset.id
  task_definition = aws_ecs_task_definition.superset.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.superset.arn
    container_name   = "superset"
    container_port   = 8088
  }

  depends_on = [aws_lb_listener.superset]
  tags       = local.common_tags

  lifecycle {
    ignore_changes = [task_definition]
  }
}

resource "aws_security_group" "tailscale_proxy" {
  count       = var.tailscale_proxy_enabled ? 1 : 0
  name        = "${local.name}-tailscale-proxy"
  description = "Tailscale proxy for private Superset dev access"
  vpc_id      = var.vpc_id
  tags        = local.common_tags
}

resource "aws_vpc_security_group_egress_rule" "tailscale_proxy_all" {
  count             = var.tailscale_proxy_enabled ? 1 : 0
  security_group_id = aws_security_group.tailscale_proxy[0].id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

resource "aws_vpc_security_group_ingress_rule" "alb_from_tailscale_proxy" {
  count                        = var.tailscale_proxy_enabled ? 1 : 0
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.tailscale_proxy[0].id
  from_port                    = var.certificate_arn == "" ? 80 : 443
  ip_protocol                  = "tcp"
  to_port                      = var.certificate_arn == "" ? 80 : 443
}

resource "aws_iam_role" "tailscale_proxy" {
  count = var.tailscale_proxy_enabled ? 1 : 0
  name  = "${local.name}-tailscale-proxy"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRole"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
  tags = local.common_tags
}

resource "aws_iam_instance_profile" "tailscale_proxy" {
  count = var.tailscale_proxy_enabled ? 1 : 0
  name  = "${local.name}-tailscale-proxy"
  role  = aws_iam_role.tailscale_proxy[0].name
}

resource "aws_iam_role_policy" "tailscale_proxy_ssm" {
  count = var.tailscale_proxy_enabled && var.tailscale_auth_key_ssm_parameter_name != "" ? 1 : 0
  name  = "${local.name}-tailscale-proxy-ssm"
  role  = aws_iam_role.tailscale_proxy[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssm:GetParameter"
      ]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.tailscale_auth_key_ssm_parameter_name}"
    }]
  })
}

data "aws_ami" "amazon_linux" {
  count       = var.tailscale_proxy_enabled ? 1 : 0
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "architecture"
    values = ["arm64"]
  }
}

resource "aws_instance" "tailscale_proxy" {
  count                       = var.tailscale_proxy_enabled ? 1 : 0
  ami                         = data.aws_ami.amazon_linux[0].id
  instance_type               = "t4g.nano"
  subnet_id                   = var.public_subnet_ids[0]
  vpc_security_group_ids      = [aws_security_group.tailscale_proxy[0].id]
  associate_public_ip_address = true
  iam_instance_profile        = aws_iam_instance_profile.tailscale_proxy[0].name

  user_data = templatefile("${path.module}/tailscale-proxy-user-data.sh.tftpl", {
    tailscale_auth_key                    = var.tailscale_auth_key
    tailscale_auth_key_ssm_parameter_name = var.tailscale_auth_key_ssm_parameter_name
    tailscale_hostname                    = local.tailscale_hostname
    alb_dns_name                          = aws_lb.superset.dns_name
    listener_port                         = var.certificate_arn == "" ? 80 : 443
  })

  metadata_options {
    http_tokens = "required"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name}-tailscale-proxy"
  })

  lifecycle {
    ignore_changes = [user_data]
  }
}

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:environment:${var.environment}"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "GitHubActionsSwedishMortgagesSuperset${title(var.environment)}"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "${local.name}-deploy"
  role = aws_iam_role.github_deploy.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart"
        ]
        Resource = aws_ecr_repository.superset.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.execution.arn,
          aws_iam_role.task.arn
        ]
      }
    ]
  })
}
