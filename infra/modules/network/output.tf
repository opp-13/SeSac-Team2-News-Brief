output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public Subnet IDs"
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "Private Subnet IDs"
  value       = module.vpc.private_subnets
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = module.vpc.igw_id
}

output "public_route_table_ids" {
  description = "Public Route Table IDs"
  value       = module.vpc.public_route_table_ids
}

output "private_route_table_ids" {
  description = "Private Route Table IDs"
  value       = module.vpc.private_route_table_ids
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs"
  value       = module.vpc.nat_ids
}

output "nat_gateway_public_ips" {
  description = "NAT Gateway public IPs"
  value       = module.vpc.nat_public_ips
}

output "bastion_security_group_id" {
  description = "Bastion Security Group ID (SSH from anywhere)"
  value       = module.bastion_sg.id
}

output "alb_security_group_id" {
  description = "ALB Security Group ID (HTTP/HTTPS from anywhere)"
  value       = module.alb_sg.id
}

output "web_security_group_id" {
  description = "Web Security Group ID (SSH from bastion, HTTP/HTTPS from ALB)"
  value       = module.web_sg.id
}

output "internal_mysql_security_group_id" {
  description = "Internal MySQL Security Group ID (SSH from bastion, MySQL from within the VPC)"
  value       = module.internal_mysql_sg.id
}

output "internal_redis_security_group_id" {
  description = "Internal Redis Security Group ID (SSH from bastion, Redis from within the VPC)"
  value       = module.internal_redis_sg.id
}

output "internal_api_security_group_id" {
  description = "Internal API Security Group ID (SSH from bastion, API from web server)"
  value       = module.internal_api_sg.id
}
