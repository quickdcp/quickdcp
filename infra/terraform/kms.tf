locals { tags = { Project = var.project, Managed = "terraform" } }
resource "aws_kms_key" "qd" {
  description         = "QuickDCP CMK for out/vault/logs"
  enable_key_rotation = true
  tags                = local.tags
}
resource "aws_kms_alias" "qd" {
  name          = "alias/${var.project}-cmk"
  target_key_id = aws_kms_key.qd.key_id
}
