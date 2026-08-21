module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.0"

  name = var.name_prefix
  cidr = var.vpc_cidr
  azs  = var.azs

  public_subnets = var.public_subnet_cidrs

    public_subnet_names = [
    for i, cidr in var.public_subnet_cidrs : "${var.name_prefix}-public-${substr(element(var.azs, i), -1, 1)}"
    ]

  private_subnets      = [for s in var.private_subnets : s.cidr]
  private_subnet_names = [for s in var.private_subnets : "${var.name_prefix}-${s.name}"]

  enable_dns_hostnames = true
  enable_dns_support   = true

  # nat gw는 vpc에 한개만 사용
  # one_nat_gateway_per_az = true
  enable_nat_gateway = true
  single_nat_gateway = true

}


# Bastion Security Group (public) - SSH from anywhere
module "bastion_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.name_prefix}-bastion-sg"
  description = "Bastion host - SSH from internet"
  vpc_id      = module.vpc.vpc_id

  ingress_rules = {
    ssh = {
      from_port   = 22
      to_port     = 22
      ip_protocol = "tcp"
      cidr_ipv4   = var.bastion_ssh_cidr
      description = "SSH from anywhere"
    }
  }

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound"
    }
  }
}


module "alb_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.name_prefix}-alb-sg"
  description = "Internet-facing ALB - HTTP/HTTPS from anywhere"
  vpc_id      = module.vpc.vpc_id

  ingress_rules = {
    http = {
      from_port   = 80
      to_port     = 80
      ip_protocol = "tcp"
      cidr_ipv4   = "0.0.0.0/0"
      description = "HTTP from anywhere"
    }
    https = {
      from_port   = 443
      to_port     = 443
      ip_protocol = "tcp"
      cidr_ipv4   = "0.0.0.0/0"
      description = "HTTPS from anywhere"
    }
  }

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound"
    }
  }
}


module "web_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.name_prefix}-web-sg"
  description = "Bastion host - SSH from internet"
  vpc_id      = module.vpc.vpc_id

  ingress_rules = {
    ssh = {
      from_port                    = 22
      to_port                      = 22
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.bastion_sg.id
      description                  = "SSH from bastion"
    }
    http = {
      from_port                    = 80
      to_port                      = 80
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.alb_sg.id
      description                  = "HTTP from ALB"
    }
    https = {
      from_port                    = 443
      to_port                      = 443
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.alb_sg.id
      description                  = "HTTPS from ALB"
    }
  }

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound"
    }
  }
}


module "internal_mysql_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.name_prefix}-internal-mysql-sg"
  description = "Private resources - SSH and MySQL from within the VPC"
  vpc_id      = module.vpc.vpc_id

  ingress_rules = {
    ssh = {
      from_port                    = 22
      to_port                      = 22
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.bastion_sg.id
      description                  = "SSH from bastion"
    }
    mysql = {
      from_port   = 3306
      to_port     = 3306
      ip_protocol = "tcp"
      cidr_ipv4   = var.vpc_cidr
      description = "MySQL from within the VPC"
    }
  }

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound"
    }
  }
}


module "internal_redis_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.name_prefix}-internal-redis-sg"
  description = "Private resources - SSH and REDIS from within the VPC"
  vpc_id      = module.vpc.vpc_id

  ingress_rules = {
    ssh = {
      from_port                    = 22
      to_port                      = 22
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.bastion_sg.id
      description                  = "SSH from bastion"
    }
    redis = {
      from_port   = 6379
      to_port     = 6379
      ip_protocol = "tcp"
      cidr_ipv4   = var.vpc_cidr
      description = "Redis from within the VPC"
    }
  }

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound"
    }
  }
}


module "internal_api_sg" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 6.0"

  name        = "${var.name_prefix}-internal-api-sg"
  description = "Private resources - SSH and API from within the VPC"
  vpc_id      = module.vpc.vpc_id

  ingress_rules = {
    ssh = {
      from_port                    = 22
      to_port                      = 22
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.bastion_sg.id
      description                  = "SSH from bastion"
    }
    api = {
      from_port                    = 8000
      to_port                      = 8000
      ip_protocol                  = "tcp"
      referenced_security_group_id = module.web_sg.id
      description                  = "API from web server"
    }
    # The internal NLB's health-check probes come from its own ENIs in the
    # backend subnets, not from web_sg -- the SG-scoped `api` rule above
    # doesn't cover them, which left every target permanently "unhealthy"
    # even with a working app. Same VPC-CIDR pattern as internal_mysql_sg /
    # internal_redis_sg below.
    api_healthcheck = {
      from_port   = 8000
      to_port     = 8000
      ip_protocol = "tcp"
      cidr_ipv4   = var.vpc_cidr
      description = "API from within the VPC (covers NLB health checks)"
    }
  }

  egress_rules = {
    all = {
      ip_protocol = "-1"
      cidr_ipv4   = "0.0.0.0/0"
      description = "Allow all outbound"
    }
  }
}