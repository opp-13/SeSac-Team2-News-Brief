# ---------------------------------------------------------------------------
# Instance role for the CodeDeploy agent -- attached to frontend/backend only
# (the instances that actually receive app deployments). Grants the S3 read
# access the agent needs to pull deployment revisions (and its own installer).
# ---------------------------------------------------------------------------
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "codedeploy_instance" {
  count = var.create_deploy ? 1 : 0

  name               = "${var.name_prefix}-codedeploy-instance-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "codedeploy_instance" {
  count = var.create_deploy ? 1 : 0

  role       = aws_iam_role.codedeploy_instance[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2RoleforAWSCodeDeploy"
}

resource "aws_iam_instance_profile" "codedeploy_instance" {
  count = var.create_deploy ? 1 : 0

  name = "${var.name_prefix}-codedeploy-instance-profile"
  role = aws_iam_role.codedeploy_instance[0].name
}
