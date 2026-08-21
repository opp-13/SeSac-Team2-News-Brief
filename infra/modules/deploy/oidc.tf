# ---------------------------------------------------------------------------
# GitHub Actions OIDC federation for the app-deploy pipeline (build -> push
# to S3 -> trigger CodeDeploy). Distinct in purpose from the Terraform
# plan/apply OIDC setup referenced from terraform-example-structure/init/oidc
# -- that one is for infra CI, this one is scoped narrowly to deployment
# actions only.
#
# ---------------------------------------------------------------------------
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # thumbprint_list omitted -- computed automatically by the AWS provider (v6+).
}

# `sub` is wildcarded on both sides of org/repo because GitHub's "immutable
# subject claims" format (repo:org@<id>/repo@<id>:...) may or may not be
# active for this repo, and there's no way to know without decoding a real
# token. `*` matches zero characters too, so this pattern matches both the
# classic "repo:org/repo:..." format and the immutable-claims format.
#
# `:environment:*` (not `:ref:refs/heads/main`) because deploy.yml's jobs
# declare `environment: ${{ matrix.environment }}` -- once a job has an
# `environment:`, GitHub always shapes `sub` as
# `repo:org/repo:environment:<name>`, never the ref-based form, regardless of
# which branch triggered it. The `*` at the end covers every environment
# name (john, and whichever teammates get added to the matrix later) since
# they all deploy into this same AWS account/role.
data "aws_iam_policy_document" "github_actions_deploy_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_org}*/${var.github_repo}*:environment:*"]
    }
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = "${var.name_prefix}-gha-deploy-role"
  assume_role_policy = data.aws_iam_policy_document.github_actions_deploy_trust.json
}

data "aws_iam_policy_document" "github_actions_deploy_permissions" {
  statement {
    sid       = "ArtifactUpload"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.codedeploy_artifacts.arn}/*"]
  }

  statement {
    sid = "CodeDeployTrigger"
    actions = [
      "codedeploy:CreateDeployment",
      "codedeploy:GetDeployment",
      "codedeploy:GetDeploymentConfig",
      "codedeploy:GetApplicationRevision",
      "codedeploy:RegisterApplicationRevision",
    ]
    resources = [
      aws_codedeploy_app.frontend.arn,
      aws_codedeploy_app.backend.arn,
      aws_codedeploy_deployment_group.frontend.arn,
      aws_codedeploy_deployment_group.backend.arn,
      "arn:aws:codedeploy:*:*:deploymentconfig:*",
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "deploy-permissions"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_deploy_permissions.json
}
