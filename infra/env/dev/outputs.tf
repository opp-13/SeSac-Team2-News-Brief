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
