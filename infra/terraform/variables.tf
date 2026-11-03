variable "aws_region" {
  description = "AWS region for every resource, for example ap-south-1."
  type        = string
}

variable "project_name" {
  description = "Used in resource names and tags."
  type        = string
  default     = "costpilot"
}

variable "instance_type" {
  description = "Server size. Keycloak needs about 1 GB, so t3.micro is too small."
  type        = string
  default     = "t3.small"
}

variable "root_volume_gb" {
  description = "Disk size. The AWS free plan covers up to 30 GB."
  type        = number
  default     = 20
}

variable "swap_gb" {
  description = "Swap file size on the server, a safety buffer for memory."
  type        = number
  default     = 2
}

variable "bucket_name" {
  description = "Private S3 bucket for bills, backups and deploy bundles. Must be unique across all of AWS."
  type        = string
}

variable "backup_keep_days" {
  description = "Days to keep nightly database backups."
  type        = number
  default     = 14
}

variable "deploy_bundle_keep_days" {
  description = "Days to keep old deploy bundles."
  type        = number
  default     = 30
}

variable "old_version_keep_days" {
  description = "Days to keep overwritten or deleted files, so a mistake can be undone."
  type        = number
  default     = 7
}

variable "parameter_path" {
  description = "Parameter Store folder that holds the production settings."
  type        = string
  default     = "/costpilot/prod"
}

variable "github_repository" {
  description = "GitHub repository allowed to deploy, as owner/name."
  type        = string
}

variable "github_owner_id" {
  description = "Stable numeric ID of the GitHub repository owner, used in OIDC tokens."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_owner_id))
    error_message = "github_owner_id must contain only digits."
  }
}

variable "github_repository_id" {
  description = "Stable numeric ID of the GitHub repository, used in OIDC tokens."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must contain only digits."
  }
}

variable "github_environment" {
  description = "GitHub environment the deploy job runs in. Only that job can deploy."
  type        = string
  default     = "production"
}

variable "create_github_oidc_provider" {
  description = "Set to false if your AWS account already trusts GitHub Actions."
  type        = bool
  default     = true
}

variable "alert_email" {
  description = "Email address for budget alerts."
  type        = string
}

variable "create_budget" {
  description = "Set to false if your AWS user may not create budgets. Then add the alert in the Billing console."
  type        = bool
  default     = true
}

variable "monthly_budget_usd" {
  description = "Alert when real charges, after free credits, pass this amount in a month."
  type        = number
  default     = 1
}
