locals {
  tags = {
    Project = var.project
    Managed = "terraform"
  }
}

# ingest (no object lock)
resource "aws_s3_bucket" "ingest" {
  bucket = "${var.project}-ingest"
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "ingest" {
  bucket = aws_s3_bucket.ingest.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ingest" {
  bucket = aws_s3_bucket.ingest.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ingest" {
  bucket = aws_s3_bucket.ingest.id

  rule {
    id     = "ingest-expire-7d"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 7
    }
  }
}

# out (Object Lock + KMS)
resource "aws_s3_bucket" "out" {
  bucket              = "${var.project}-out"
  object_lock_enabled = true
  tags                = local.tags
}

resource "aws_s3_bucket_versioning" "out" {
  bucket = aws_s3_bucket.out.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "out" {
  bucket = aws_s3_bucket.out.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 30
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "out" {
  bucket = aws_s3_bucket.out.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm   = "aws:kms"
      kms_master_key_id = aws_kms_key.qd.arn
    }
    bucket_key_enabled = true
  }
}

# vault (immutable proofs + sbom)
resource "aws_s3_bucket" "vault" {
  bucket              = "${var.project}-vault"
  object_lock_enabled = true
  tags                = local.tags
}

resource "aws_s3_bucket_versioning" "vault" {
  bucket = aws_s3_bucket.vault.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "vault" {
  bucket = aws_s3_bucket.vault.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 365
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "vault" {
  bucket = aws_s3_bucket.vault.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm   = "aws:kms"
      kms_master_key_id = aws_kms_key.qd.arn
    }
    bucket_key_enabled = true
  }
}

# logs (immutable)
resource "aws_s3_bucket" "logs" {
  bucket              = "${var.project}-logs"
  object_lock_enabled = true
  tags                = local.tags
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_object_lock_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    default_retention {
      mode = "COMPLIANCE"
      days = 365
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm   = "aws:kms"
      kms_master_key_id = aws_kms_key.qd.arn
    }
    bucket_key_enabled = true
  }
}

# TLS-only policies applied to all buckets
locals {
  tls_only = jsonencode({
    Version   = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecure"
      Effect    = "Deny"
      Principal = "*"
      Action    = ["s3:GetObject","s3:PutObject","s3:ListBucket"]
      Resource = [
        aws_s3_bucket.ingest.arn, "${aws_s3_bucket.ingest.arn}/*",
        aws_s3_bucket.out.arn,    "${aws_s3_bucket.out.arn}/*",
        aws_s3_bucket.vault.arn,  "${aws_s3_bucket.vault.arn}/*",
        aws_s3_bucket.logs.arn,   "${aws_s3_bucket.logs.arn}/*"
      ]
      Condition = {
        Bool = { "aws:SecureTransport" = "false" }
      }
    }]
  })
}

resource "aws_s3_bucket_policy" "ingest_tls" {
  bucket = aws_s3_bucket.ingest.id
  policy = local.tls_only
}

resource "aws_s3_bucket_policy" "out_tls" {
  bucket = aws_s3_bucket.out.id
  policy = local.tls_only
}

resource "aws_s3_bucket_policy" "vault_tls" {
  bucket = aws_s3_bucket.vault.id
  policy = local.tls_only
}

resource "aws_s3_bucket_policy" "logs_tls" {
  bucket = aws_s3_bucket.logs.id
  policy = local.tls_only
}
