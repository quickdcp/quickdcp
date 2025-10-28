# Central variables file for QuickDCP Terraform (fixed)
# NOTE: Core variables are already defined in the individual component files
# (providers.tf, s3.tf, kms.tf, iam.tf, budget.tf) to keep each unit portable.
# To avoid duplicate-definition errors, this file only includes optional/global
# variables that are safe to declare here.

variable "name_prefix" {
  description = "Human-friendly name prefix for resources (not required)."
  type        = string
  default     = "quickdcp"
}

variable "tags_extra" {
  description = "Optional extra tags applied by modules that support it."
  type        = map(string)
  default     = {}
}

variable "enable_budget" {
  description = "Toggle creation of AWS Budgets (used if wired in root module)."
  type        = bool
  default     = true
}
