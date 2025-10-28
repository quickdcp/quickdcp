# AWS S3 buckets for QuickDCP (fixed)
# Creates four buckets: ingest, out, vault, logs
# - Object Lock + versioning for out/vault/logs
# - KMS encryption (CMK) for out/vault/logs; SSE-S3 for ingest
# - Server access logging into logs bucket
# - Enforce TLS-only access via bucket policy

variable "project" {
  type        = string
  default     = "quickdcp"
  description = "Project name used for bucket names and tags"
}

variable "kms_key_arn" {
  type        = string
  description = "KMS CMK ARN for out/vault/logs encryption"
}

locals {
  tags = { Project = var.project, Managed = "terraform" }

  # Simple names; adjust if you need unique per-account naming
  ingest_name = "${var.project}-ingest"
  out_name    = "${var.project}-out"
  vault_name  = "${var.project}-vault"
  logs_name   = "${var.project}-logs"
}

# ---------------------------------------------------------------------------
# Logs bucket (destination for access logs)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "logs" {
  bucket        = local.logs_name
  force_destroy = false
  tags          = local.tags
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  rule { default_retention { mode = "GOVERNANCE" days = 30 } }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket                  = aws_s3_bucket.logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "logs_tls" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.tls_enforce[0].json
}

# ---------------------------------------------------------------------------
# Ingest bucket (upload target)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "ingest" {
  bucket        = local.ingest_name
  force_destroy = false
  tags          = local.tags
}

resource "aws_s3_bucket_versioning" "ingest" {
  bucket = aws_s3_bucket.ingest.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ingest" {
  bucket = aws_s3_bucket.ingest.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # SSE-S3 acceptable for transient ingest
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ingest" {
  bucket = aws_s3_bucket.ingest.id
  rule {
    id     = "abort-multipart"
    status = "Enabled"
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

resource "aws_s3_bucket_logging" "ingest" {
  bucket        = aws_s3_bucket.ingest.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "ingest/"
}

resource "aws_s3_bucket_public_access_block" "ingest" {
  bucket                  = aws_s3_bucket.ingest.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "ingest_tls" {
  bucket = aws_s3_bucket.ingest.id
  policy = data.aws_iam_policy_document.tls_enforce[0].json
}

# ---------------------------------------------------------------------------
# Out bucket (final mastered DCPs)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "out" {
  bucket              = local.out_name
  force_destroy       = false
  tags                = local.tags
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "out" {
  bucket = aws_s3_bucket.out.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "out" {
  bucket = aws_s3_bucket.out.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "out" {
  bucket = aws_s3_bucket.out.id
  rule { default_retention { mode = "GOVERNANCE" days = 365 } }
}

resource "aws_s3_bucket_logging" "out" {
  bucket        = aws_s3_bucket.out.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "out/"
}

resource "aws_s3_bucket_public_access_block" "out" {
  bucket                  = aws_s3_bucket.out.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "out_tls" {
  bucket = aws_s3_bucket.out.id
  policy = data.aws_iam_policy_document.tls_enforce[0].json
}

# ---------------------------------------------------------------------------
# Vault bucket (manifests, proofs, KDMs)
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "vault" {
  bucket              = local.vault_name
  force_destroy       = false
  tags                = local.tags
  object_lock_enabled = true
}

resource "aws_s3_bucket_versioning" "vault" {
  bucket = aws_s3_bucket.vault.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "vault" {
  bucket = aws_s3_bucket.vault.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_object_lock_configuration" "vault" {
  bucket = aws_s3_bucket.vault.id
  rule { default_retention { mode = "GOVERNANCE" days = 365 } }
}

resource "aws_s3_bucket_logging" "vault" {
  bucket        = aws_s3_bucket.vault.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "vault/"
}

resource "aws_s3_bucket_public_access_block" "vault" {
  bucket                  = aws_s3_bucket.vault.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "vault_tls" {
  bucket = aws_s3_bucket.vault.id
  policy = data.aws_iam_policy_document.tls_enforce[0].json
}

# ---------------------------------------------------------------------------
# TLS enforcement policy (reused)
# ---------------------------------------------------------------------------

data "aws_iam_policy_document" "tls_enforce" {
  count = 1
  statement {
    sid     = "EnforceTLS"
    effect  = "Deny"
    actions = ["s3:*"]
    principals { type = "*" identifiers = ["*"] }
    resources = [
      aws_s3_bucket.ingest.arn, "${aws_s3_bucket.ingest.arn}/*",
      aws_s3_bucket.out.arn,    "${aws_s3_bucket.out.arn}/*",
      aws_s3_bucket.vault.arn,  "${aws_s3_bucket.vault.arn}/*",
      aws_s3_bucket.logs.arn,   "${aws_s3_bucket.logs.arn}/*",
    ]
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}
