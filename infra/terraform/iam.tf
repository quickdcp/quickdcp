# AWS IAM for QuickDCP API (fixed)
# Creates a dedicated IAM user with scoped S3 + KMS permissions
# Buckets and KMS key can be created in other TF files; pass their names/ARN here.

variable "project" { type = string, default = "quickdcp" }

variable "bucket_ingest" { type = string, description = "Name of ingest bucket" }
variable "bucket_out"    { type = string, description = "Name of out bucket" }
variable "bucket_vault"  { type = string, description = "Name of vault bucket" }
variable "bucket_logs"   { type = string, description = "Name of logs bucket" }

variable "kms_key_arn" {
  type        = string
  description = "KMS CMK ARN used for out/vault/logs buckets"
}

locals {
  tags = { Project = var.project, Managed = "terraform" }

  s3_arns = [
    "arn:aws:s3:::${var.bucket_ingest}",
    "arn:aws:s3:::${var.bucket_ingest}/*",
    "arn:aws:s3:::${var.bucket_out}",
    "arn:aws:s3:::${var.bucket_out}/*",
    "arn:aws:s3:::${var.bucket_vault}",
    "arn:aws:s3:::${var.bucket_vault}/*",
    "arn:aws:s3:::${var.bucket_logs}",
    "arn:aws:s3:::${var.bucket_logs}/*",
  ]
}

resource "aws_iam_user" "api" {
  name = "${var.project}-api"
  tags = local.tags
}

resource "aws_iam_access_key" "api" {
  user = aws_iam_user.api.name
}

# Policy: S3 multipart + head/list/get/put; KMS encrypt/decrypt for the CMK
data "aws_iam_policy_document" "api" {
  statement {
    sid     = "S3Access"
    actions = [
      "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
      "s3:HeadObject", "s3:ListBucket",
      "s3:AbortMultipartUpload", "s3:CreateMultipartUpload",
      "s3:ListBucketMultipartUploads", "s3:ListMultipartUploadParts", "s3:CompleteMultipartUpload"
    ]
    resources = local.s3_arns
  }

  statement {
    sid     = "KMSAccess"
    actions = [
      "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"
    ]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_user_policy" "attach" {
  user   = aws_iam_user.api.name
  name   = "${var.project}-api-s3kms"
  policy = data.aws_iam_policy_document.api.json
}
