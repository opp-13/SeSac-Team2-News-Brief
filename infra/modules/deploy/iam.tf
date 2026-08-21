# ---------------------------------------------------------------------------
# CodeDeploy *service* role -- assumed by the CodeDeploy service itself to
# call EC2 APIs during a deployment. Distinct from modules/compute/iam.tf's
# *instance* role (assumed by ec2.amazonaws.com, used by the agent running on
# each instance to pull revisions from S3). One shared service role covers
# both the frontend and backend deployment groups.
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "codedeploy_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["codedeploy.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codedeploy_service" {
  name               = "${var.name_prefix}-codedeploy-service-role"
  assume_role_policy = data.aws_iam_policy_document.codedeploy_assume_role.json
}

resource "aws_iam_role_policy_attachment" "codedeploy_service" {
  role       = aws_iam_role.codedeploy_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole"
}
