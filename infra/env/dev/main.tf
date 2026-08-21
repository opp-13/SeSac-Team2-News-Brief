provider "aws" {
  region = var.region

  default_tags {
    tags = local.common_tags
  }
}

module "network" {
  source = "../../modules/network"

  name_prefix         = var.zone
  vpc_cidr            = var.vpc_cidr
  azs                 = var.azs
  public_subnet_cidrs = var.public_subnet_cidrs
  private_subnets     = var.private_subnets
  bastion_ssh_cidr    = var.bastion_ssh_cidr

  # team2.local private hosted zone -- these come from module.compute's
  # outputs, so this specific set of resources applies after compute (see
  # modules/network/dns.tf for why that's not a cycle).
  enable_private_dns    = var.enable_private_dns
  db_private_ip         = module.compute.db_private_ip
  redis_private_ip      = module.compute.redis_private_ip
  internal_nlb_dns_name = module.compute.internal_nlb_dns_name
  internal_nlb_zone_id  = module.compute.internal_nlb_zone_id
}

module "compute" {
  source = "../../modules/compute"

  name_prefix = var.zone
  vpc_id      = module.network.vpc_id

  public_subnet_ids = module.network.public_subnet_ids

  # var.private_subnets로 일괄 생성, 따라서 서버의 서브넷은 그곳에서 가져옴
  frontend_subnet_ids = slice(module.network.private_subnet_ids, 0, 2)
  backend_subnet_ids  = slice(module.network.private_subnet_ids, 2, 4)
  db_subnet_id        = module.network.private_subnet_ids[4]

  alb_security_group_id            = module.network.alb_security_group_id
  web_security_group_id            = module.network.web_security_group_id
  internal_api_security_group_id   = module.network.internal_api_security_group_id
  internal_mysql_security_group_id = module.network.internal_mysql_security_group_id
  internal_redis_security_group_id = module.network.internal_redis_security_group_id
  bastion_security_group_id        = module.network.bastion_security_group_id

  create_bastion = var.create_bastion
  create_deploy  = var.create_deploy
  key_pair_name  = var.key_pair_name

  enable_https           = var.enable_https
  acm_certificate_domain = var.acm_certificate_domain
}

module "deploy" {
  source = "../../modules/deploy"
  count  = var.create_deploy ? 1 : 0

  name_prefix = var.zone
  github_org  = "opp-13"
  github_repo = "SeSac-Team2-News-Brief"
}

