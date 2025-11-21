output "ingest_bucket" { value = aws_s3_bucket.ingest.bucket }
output "out_bucket"    { value = aws_s3_bucket.out.bucket }
output "vault_bucket"  { value = aws_s3_bucket.vault.bucket }
output "logs_bucket"   { value = aws_s3_bucket.logs.bucket }

output "iam_access_key_id" {
  value     = aws_iam_access_key.api.id
  sensitive = true
}
output "iam_secret_access_key" {
  value     = aws_iam_access_key.api.secret
  sensitive = true
}
output "kms_key_arn" { value = aws_kms_key.qd.arn }
