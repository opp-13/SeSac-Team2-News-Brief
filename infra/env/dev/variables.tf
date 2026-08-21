variable "project" {
  description = "Project name"
  type        = string
}

variable "owner" {
  description = "Owner of the resources"
  type        = string
}

variable "zone" {
  description = "Zone tag, also used as the network module's name_prefix"
  type        = string
}

variable "environment" {
  description = "Deployment environment (e.g. dev/poc/prod)"
  type        = string
}

variable "mangedby" {
  description = "Resource manager"
  type        = string
  default     = "terraform"
}

variable "aws_profile" {
  description = "Named AWS CLI profile to use. Leave null to fall back to the default AWS credential chain."
  type        = string
  default     = null
}

variable "oidc_role_arn" {
  description = "IAM role ARN to assume via GitHub OIDC web-identity federation for this environment's actual resource deployment (CI only, from init/oidc's apply_role_arn/plan_role_arn output). Leave null for local applies, which use var.aws_profile instead."
  type        = string
  default     = null
}

variable "web_identity_token_file" {
  description = "Path to a file containing the GitHub Actions OIDC ID token (CI only, paired with var.oidc_role_arn). Leave null for local applies."
  type        = string
  default     = null
}

variable "region" {
  description = "AWS region"
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
  description = "Private subnets to create, each with its own name and CIDR"
  type = list(object({
    name = string
    cidr = string
  }))
}

variable "bastion_ssh_cidr" {
  description = "CIDR allowed to SSH into the bastion security group"
  type        = string
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair (created in the AWS console) for SSH access to the compute instances"
  type        = string
}

variable "create_bastion" {
  description = "Whether to create a bastion host in the first public subnet. Optional."
  type        = bool
  default     = false
}

variable "enable_https" {
  description = "Whether to add an HTTPS listener (ACM cert) to the public ALB and redirect HTTP to it. Optional -- off by default."
  type        = bool
  default     = false
}

variable "create_deploy" {
  description = "Whether to create the CodeDeploy pipeline (module.deploy: OIDC provider/role, S3 artifacts bucket, CodeDeploy apps/deployment groups). Optional -- on by default."
  type        = bool
  default     = true
}

variable "acm_certificate_domain" {
  description = <<-EOT
    Domain name exactly as registered on an existing, already-ISSUED ACM
    certificate (Route53 DNS-validated) in this account/region. Required
    only when enable_https = true.

    NOT necessarily the Route53 zone's apex domain -- if the cert is a
    wildcard (zone "s6john.cloud" but cert covers "*.s6john.cloud"), use
    the literal "*.s6john.cloud" string, not the apex alone.
  EOT
  type        = string
  default     = null
}

