output "frontend_instance_ids" {
  description = "Frontend EC2 instance IDs"
  value       = [for m in module.frontend : m.id]
}

output "frontend_private_ips" {
  description = "Frontend EC2 private IPs"
  value       = [for m in module.frontend : m.private_ip]
}

output "backend_instance_ids" {
  description = "Backend EC2 instance IDs"
  value       = [for m in module.backend : m.id]
}

output "backend_private_ips" {
  description = "Backend EC2 private IPs"
  value       = [for m in module.backend : m.private_ip]
}

output "db_instance_id" {
  description = "DB EC2 instance ID"
  value       = module.db.id
}

output "db_private_ip" {
  description = "DB EC2 private IP"
  value       = module.db.private_ip
}

output "redis_instance_id" {
  description = "Redis EC2 instance ID"
  value       = module.redis.id
}

output "redis_private_ip" {
  description = "Redis EC2 private IP"
  value       = module.redis.private_ip
}

output "bastion_public_ip" {
  description = "Bastion public IP (null unless create_bastion = true)"
  value       = try(module.bastion[0].public_ip, null)
}

output "public_alb_dns_name" {
  description = "Public ALB DNS name (point your domain's A/ALIAS record here)"
  value       = aws_lb.public.dns_name
}

output "internal_nlb_dns_name" {
  description = "Internal NLB DNS name (frontend instances call this to reach the backend)"
  value       = aws_lb.internal.dns_name
}

output "internal_nlb_zone_id" {
  description = "Internal NLB hosted zone ID (needed for a Route53 ALIAS record pointing at it)"
  value       = aws_lb.internal.zone_id
}
