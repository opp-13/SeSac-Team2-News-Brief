output "frontend_app_name" {
  description = "CodeDeploy application name for frontend"
  value       = aws_codedeploy_app.frontend.name
}

output "frontend_deployment_group_name" {
  description = "CodeDeploy deployment group name for frontend"
  value       = aws_codedeploy_deployment_group.frontend.deployment_group_name
}

output "backend_app_name" {
  description = "CodeDeploy application name for backend"
  value       = aws_codedeploy_app.backend.name
}

output "backend_deployment_group_name" {
  description = "CodeDeploy deployment group name for backend"
  value       = aws_codedeploy_deployment_group.backend.deployment_group_name
}

output "codedeploy_service_role_arn" {
  description = "IAM role ARN CodeDeploy assumes to run deployments (needed by CI/CD if it creates deployments directly)"
  value       = aws_iam_role.codedeploy_service.arn
}

output "github_actions_deploy_role_arn" {
  description = "IAM role ARN the GitHub Actions deploy workflow assumes via OIDC -- register as the DEPLOY_ROLE_ARN repo variable"
  value       = aws_iam_role.github_actions_deploy.arn
}

output "codedeploy_artifacts_bucket" {
  description = "S3 bucket the deploy workflow pushes revisions into -- register as the CODEDEPLOY_ARTIFACTS_BUCKET repo variable"
  value       = aws_s3_bucket.codedeploy_artifacts.bucket
}
