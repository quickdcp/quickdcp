resource "aws_kms_key" "qd" {
  description         = "QuickDCP CMK for out/vault/logs"
  enable_key_rotation = true
}
