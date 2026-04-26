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

variable "tailscale_auth_key_ssm_parameter_name" {
  type        = string
  default     = ""
  description = "Optional SecureString SSM parameter name containing the Tailscale auth key. Preferred over tailscale_auth_key because the key is fetched by EC2 at first boot instead of embedded in Terraform state user_data."
}

variable "tailscale_hostname" {
  type    = string
  default = ""
}

variable "tailscale_proxy_subnet_id" {
  type        = string
  default     = ""
  description = "Optional explicit subnet for the Tailscale proxy. Defaults to the first public subnet."
}

variable "certificate_arn" {
  type    = string
  default = ""
}

variable "container_image" {
  type    = string
  default = "public.ecr.aws/docker/library/busybox:latest"
}

variable "db_username" {
  type    = string
  default = "superset"
}

variable "manage_db_master_password" {
  type        = bool
  default     = true
  description = "Use RDS-managed master password storage instead of putting the DB password in Terraform state."
}

variable "db_password" {
  type      = string
  sensitive = true
  default   = null
  nullable  = true
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
