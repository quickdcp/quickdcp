# Terraform outputs for QuickDCP (fixed)

# Buckets
output "ingest_bucket" {
  description = "Name of ingest bucket"
  value       = aws_s3_bucket.ingest.bucket
}

output "out_bucket" {
  description = "Name of out bucket"
  value       = aws_s3_bucket.out.bucket
}

output "vault_bucket" {
  description = "Name of vault bucket"
  value       = aws_s3_bucket.vault.bucket
}

output "logs_bucket" {
  description = "Name of logs bucket"
  value       = aws_s3_bucket.logs.bucket
}

# KMS
output "kms_key_arn" {
  description = "ARN of the QuickDCP CMK"
  value       = aws_kms_key.qd.arn
}

output "kms_alias" {
  description = "Alias of the QuickDCP CMK"
  value       = aws_kms_alias.qd.name
}

# IAM credentials (sensitive!)
output "iam_access_key_id" {
  description = "Access key ID for API user"
  value       = aws_iam_access_key.api.id
  sensitive   = true
}

output "iam_secret_access_key" {
  description = "Secret access key for API user"
  value       = aws_iam_access_key.api.secret
  sensitive   = true
}
