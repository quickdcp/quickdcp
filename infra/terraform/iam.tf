locals { tags = { Project = var.project, Managed = "terraform" } }
resource "aws_iam_user" "api" { name = "${var.project}-api" tags = local.tags }
resource "aws_iam_access_key" "api" { user = aws_iam_user.api.name }

data "aws_iam_policy_document" "s3_access" {
  statement {
    actions = [
      "s3:GetObject","s3:PutObject","s3:HeadObject","s3:ListBucket",
      "s3:AbortMultipartUpload","s3:CreateMultipartUpload",
      "s3:ListBucketMultipartUploads","s3:ListMultipartUploadParts","s3:CompleteMultipartUpload"
    ]
    resources = [
      aws_s3_bucket.ingest.arn, "${aws_s3_bucket.ingest.arn}/*",
      aws_s3_bucket.out.arn,    "${aws_s3_bucket.out.arn}/*",
      aws_s3_bucket.vault.arn,  "${aws_s3_bucket.vault.arn}/*",
      aws_s3_bucket.logs.arn,   "${aws_s3_bucket.logs.arn}/*"
    ]
  }
}
resource "aws_iam_user_policy" "attach" {
  user   = aws_iam_user.api.name
  name   = "${var.project}-api-s3"
  policy = data.aws_iam_policy_document.s3_access.json
}
