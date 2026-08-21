# ---------------------------------------------------------------------------
# Revision bucket the GitHub Actions deploy workflow pushes app bundles into
# (via `aws deploy push`), and instances read from via their own instance
# role (modules/compute/iam.tf's AmazonEC2RoleforAWSCodeDeploy, already
# Resource: "*" -- no extra grant needed on that side).
# ---------------------------------------------------------------------------
resource "aws_s3_bucket" "codedeploy_artifacts" {
  bucket = "${var.name_prefix}-codedeploy-artifacts"
}

resource "aws_s3_bucket_public_access_block" "codedeploy_artifacts" {
  bucket = aws_s3_bucket.codedeploy_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
