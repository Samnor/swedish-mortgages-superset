variable "aws_region" {
  type    = string
  default = "eu-north-1"
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod."
  }
}

variable "name_prefix" {
  type    = string
  default = "swedish-mortgages"
}

variable "github_repo" {
  type    = string
  default = "Samnor/swedish-mortgages-superset"
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "assign_public_ip" {
  type    = bool
  default = true
}

variable "internal_alb" {
  type    = bool
  default = false
}

variable "allowed_ingress_cidrs" {
  type    = list(string)
  default = ["0.0.0.0/0"]
}

variable "tailscale_proxy_enabled" {
  type    = bool
  default = false
}

variable "tailscale_auth_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "tailscale_hostname" {
  type    = string
  default = ""
}

variable "certificate_arn" {
  type    = string
  default = ""
}

variable "container_image" {
  type    = string
  default = "public.ecr.aws/docker/library/busybox:latest"
}

variable "superset_secret_key" {
  type      = string
  sensitive = true
}

variable "superset_admin_password" {
  type      = string
  sensitive = true
}

variable "db_username" {
  type    = string
  default = "superset"
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_allocated_storage" {
  type    = number
  default = 20
}

variable "athena_schema" {
  type = string
}

variable "athena_s3_staging_dir" {
  type = string
}

variable "athena_results_bucket_arn" {
  type = string
}

variable "data_lake_bucket_arn" {
  type = string
}
