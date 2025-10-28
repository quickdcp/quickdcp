# AWS KMS for QuickDCP (fixed)
# Creates a CMK used to encrypt out/vault/logs buckets.

variable "project" {
  type        = string
  default     = "quickdcp"
  description = "Project name for tagging/alias"
}

variable "kms_key_admin_arns" {
  type        = list(string)
  default     = []
  description = "Additional IAM principals (ARNs) to grant full admin on the CMK"
}

locals {
  tags = { Project = var.project, Managed = "terraform" }
}

# The default key policy grants account root admin; additional admins may be added.
# AWS best practice is to keep a minimal policy and rely on IAM for usage.
resource "aws_kms_key" "qd" {
  description             = "${var.project} CMK for out/vault/logs"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = local.tags

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EnableRootPermissions"
        Effect   = "Allow"
        Principal = { AWS = "*" }
        Action   = "kms:*"
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      # Optional explicit admins (if provided)
      for admin in var.kms_key_admin_arns : {
        Sid      = "GrantAdmin-${replace(admin, ":", "-")}"
        Effect   = "Allow"
        Principal = { AWS = admin }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })
}

data "aws_caller_identity" "current" {}

resource "aws_kms_alias" "qd" {
  name          = "alias/${var.project}-cmk"
  target_key_id = aws_kms_key.qd.key_id
}
