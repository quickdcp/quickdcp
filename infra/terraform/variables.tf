variable "aws_region" {
  description = "AWS region for QuickDCP infra"
  type        = string
  default     = "eu-central-1"
}

variable "project" {
  description = "Project prefix for all resources"
  type        = string
  default     = "quickdcp"
}

variable "budget_usd" {
  description = "Monthly AWS cost guard"
  type        = number
  default     = 150
}
