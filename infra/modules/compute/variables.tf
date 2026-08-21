variable "name_prefix" {
  description = "Prefix used for resource names and Name tags (e.g. \"dmz\")"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID the ALB/NLB target groups are created in"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for the internet-facing ALB"
  type        = list(string)
}

variable "frontend_subnet_ids" {
  description = "Private frontend subnet IDs. One instance is created per subnet."
  type        = list(string)
}

variable "backend_subnet_ids" {
  description = "Private backend subnet IDs. One instance is created per subnet."
  type        = list(string)
}

variable "db_subnet_id" {
  description = "Private subnet ID for the single DB instance"
  type        = string
}

variable "alb_security_group_id" {
  description = "Security group ID for the internet-facing ALB (pass network module's alb_security_group_id)"
  type        = string
}

variable "web_security_group_id" {
  description = "Security group ID for frontend instances (pass network module's web_security_group_id)"
  type        = string
}

variable "internal_api_security_group_id" {
  description = "Security group ID for backend instances (pass network module's internal_api_security_group_id)"
  type        = string
}

variable "internal_mysql_security_group_id" {
  description = "Security group ID for the DB instance (pass network module's internal_mysql_security_group_id)"
  type        = string
}

variable "internal_redis_security_group_id" {
  description = "Security group ID for the Redis instance (pass network module's internal_redis_security_group_id)"
  type        = string
}

variable "bastion_security_group_id" {
  description = "Security group ID for the bastion host (pass network module's bastion_security_group_id). Only used when create_bastion = true."
  type        = string
}

variable "create_bastion" {
  description = "Whether to create a bastion host in the first public subnet. Optional -- off by default."
  type        = bool
  default     = false
}

variable "create_deploy" {
  description = "Whether modules/deploy (CodeDeploy pipeline) exists -- gates whether frontend/backend instances get the CodeDeploy agent's IAM instance profile and Role tag. Should match env/dev's var.create_deploy passed into both modules; pointless to attach these without the deployment groups they're meant to serve."
  type        = bool
  default     = true
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair (created in the AWS console) to use for SSH access to the instances"
  type        = string
}

variable "ami" {
  description = "AMI ID to use for all instances. Defaults to the latest Amazon Linux 2023 AMI if not set."
  type        = string
  default     = null
}

variable "instance_type" {
  description = "EC2 instance type for all instances"
  type        = string
  default     = "t3.micro"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB. Must be >= the AMI's root snapshot size (current AL2023 AMI needs >= 30GB)."
  type        = number
  default     = 30
}

variable "frontend_port" {
  description = "Port frontend instances listen on. Also the ALB target group's forwarding port."
  type        = number
  default     = 80
}

variable "backend_port" {
  description = "Port backend instances listen on. Also the NLB target group's forwarding port."
  type        = number
  default     = 8000
}

variable "enable_https" {
  description = "Whether to add an HTTPS listener (ACM cert) to the public ALB and redirect HTTP to it. Optional -- off by default (ALB stays plain HTTP)."
  type        = bool
  default     = false
}

variable "enable_private_dns" {
  description = "Whether to create the team2.local Route53 private hosted zone (db/redis/api records pointing at this module's own db/redis instances and internal NLB). Optional -- off by default."
  type        = bool
  default     = false
}

variable "acm_certificate_domain" {
  description = <<-EOT
    Domain name exactly as registered on an existing, already-ISSUED ACM
    certificate in this account/region (looked up via data source -- the
    certificate itself is not created here). Required only when
    enable_https = true.

    This is NOT necessarily the Route53 zone's apex domain. If the
    certificate was issued for a wildcard (e.g. the zone is "example.com"
    but the cert covers "*.example.com"), this must be the literal
    "*.example.com" string -- the apex domain alone won't match and the
    data source will fail to find the certificate.
  EOT
  type        = string
  default     = null
}
