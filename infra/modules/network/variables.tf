variable "name_prefix" {
  description = "Prefix used for resource names and Name tags (e.g. \"dmz-public-a\")"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "azs" {
  description = "Availability zones to spread subnets across"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets, one per AZ"
  type        = list(string)
}

variable "private_subnets" {
  description = "Private subnets to create, each with its own name and CIDR. AZ is assigned by position from var.azs (cycles if there are more subnets than AZs)."
  type = list(object({
    name = string
    cidr = string
  }))
}

variable "bastion_ssh_cidr" {
  description = "CIDR allowed to SSH into the bastion security group"
  type        = string
}

variable "enable_private_dns" {
  description = "Whether to create a team2.local Route53 private hosted zone (db/redis/api records). Optional -- off by default. When true, db_private_ip/redis_private_ip/internal_nlb_dns_name/internal_nlb_zone_id are required (they come from module.compute's outputs)."
  type        = bool
  default     = false
}

variable "db_private_ip" {
  description = "DB instance private IP, used for db.team2.local. Only used when enable_private_dns = true."
  type        = string
  default     = null
}

variable "redis_private_ip" {
  description = "Redis instance private IP, used for redis.team2.local. Only used when enable_private_dns = true."
  type        = string
  default     = null
}

variable "internal_nlb_dns_name" {
  description = "Internal NLB DNS name, aliased from api.team2.local. Only used when enable_private_dns = true."
  type        = string
  default     = null
}

variable "internal_nlb_zone_id" {
  description = "Internal NLB hosted zone ID, required for the api.team2.local ALIAS record. Only used when enable_private_dns = true."
  type        = string
  default     = null
}
