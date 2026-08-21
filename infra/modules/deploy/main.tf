# ---------------------------------------------------------------------------
# Frontend: CodeDeploy application + deployment group. Targets instances via
# the Role=frontend tag set in modules/compute/main.tf -- no direct reference
# to module.compute on purpose (this module is decoupled; tag matching
# happens at deploy time, not apply time, so there's no ordering dependency).
# ---------------------------------------------------------------------------
resource "aws_codedeploy_app" "frontend" {
  name             = "${var.name_prefix}-frontend-app"
  compute_platform = "Server"
}

resource "aws_codedeploy_deployment_group" "frontend" {
  app_name               = aws_codedeploy_app.frontend.name
  deployment_group_name  = "${var.name_prefix}-frontend-dg"
  service_role_arn       = aws_iam_role.codedeploy_service.arn
  deployment_config_name = "CodeDeployDefault.OneAtATime"

  ec2_tag_filter {
    key   = "Role"
    type  = "KEY_AND_VALUE"
    value = var.frontend_role_tag_value
  }

  deployment_style {
    deployment_type   = "IN_PLACE"
    deployment_option = "WITHOUT_TRAFFIC_CONTROL"
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }
}

# ---------------------------------------------------------------------------
# Backend: same pattern, targets Role=backend.
# ---------------------------------------------------------------------------
resource "aws_codedeploy_app" "backend" {
  name             = "${var.name_prefix}-backend-app"
  compute_platform = "Server"
}

resource "aws_codedeploy_deployment_group" "backend" {
  app_name               = aws_codedeploy_app.backend.name
  deployment_group_name  = "${var.name_prefix}-backend-dg"
  service_role_arn       = aws_iam_role.codedeploy_service.arn
  deployment_config_name = "CodeDeployDefault.OneAtATime"

  ec2_tag_filter {
    key   = "Role"
    type  = "KEY_AND_VALUE"
    value = var.backend_role_tag_value
  }

  deployment_style {
    deployment_type   = "IN_PLACE"
    deployment_option = "WITHOUT_TRAFFIC_CONTROL"
  }

  auto_rollback_configuration {
    enabled = true
    events  = ["DEPLOYMENT_FAILURE"]
  }
}
