output "public_alb_dns_name" {
  description = "Public ALB DNS name (point your domain's A/ALIAS record here)"
  value       = module.compute.public_alb_dns_name
}

output "internal_nlb_dns_name" {
  description = "Internal NLB DNS name (frontend instances call this to reach the backend)"
  value       = module.compute.internal_nlb_dns_name
}

output "bastion_public_ip" {
  description = "Bastion public IP (null unless create_bastion = true)"
  value       = module.compute.bastion_public_ip
}

output "frontend_codedeploy_app_name" {
  description = "CodeDeploy application name for frontend (null unless create_deploy = true)"
  value       = try(module.deploy[0].frontend_app_name, null)
}

output "frontend_codedeploy_deployment_group_name" {
  description = "CodeDeploy deployment group name for frontend (null unless create_deploy = true)"
  value       = try(module.deploy[0].frontend_deployment_group_name, null)
}

output "backend_codedeploy_app_name" {
  description = "CodeDeploy application name for backend (null unless create_deploy = true)"
  value       = try(module.deploy[0].backend_app_name, null)
}

output "backend_codedeploy_deployment_group_name" {
  description = "CodeDeploy deployment group name for backend (null unless create_deploy = true)"
  value       = try(module.deploy[0].backend_deployment_group_name, null)
}

output "github_actions_deploy_role_arn" {
  description = "Register this as the DEPLOY_ROLE_ARN GitHub repo variable (null unless create_deploy = true)"
  value       = try(module.deploy[0].github_actions_deploy_role_arn, null)
}

output "codedeploy_artifacts_bucket" {
  description = "Register this as the CODEDEPLOY_ARTIFACTS_BUCKET GitHub repo variable (null unless create_deploy = true)"
  value       = try(module.deploy[0].codedeploy_artifacts_bucket, null)
}
