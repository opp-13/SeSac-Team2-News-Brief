# ---------------------------------------------------------------------------
# team2.local private hosted zone -- resolves only inside this VPC. Points at
# compute module resources, so its inputs (db_private_ip, redis_private_ip,
# internal_nlb_dns_name/zone_id) come from module.compute's outputs, wired in
# env/dev/main.tf. That makes this specific set of resources depend on
# module.compute, even though module.compute itself depends on this module's
# vpc/subnet outputs -- fine in Terraform since the dependency graph is
# per-resource, not per-module (VPC/subnets -> EC2 instances -> these DNS
# records is a straight line, not a cycle).
# ---------------------------------------------------------------------------
resource "aws_route53_zone" "private" {
  count = var.enable_private_dns ? 1 : 0

  name = "team2.local"

  vpc {
    vpc_id = module.vpc.vpc_id
  }
}

resource "aws_route53_record" "db" {
  count = var.enable_private_dns ? 1 : 0

  zone_id = aws_route53_zone.private[0].zone_id
  name    = "db.team2.local"
  type    = "A"
  ttl     = 300
  records = [var.db_private_ip]
}

resource "aws_route53_record" "redis" {
  count = var.enable_private_dns ? 1 : 0

  zone_id = aws_route53_zone.private[0].zone_id
  name    = "redis.team2.local"
  type    = "A"
  ttl     = 300
  records = [var.redis_private_ip]
}

resource "aws_route53_record" "api" {
  count = var.enable_private_dns ? 1 : 0

  zone_id = aws_route53_zone.private[0].zone_id
  name    = "api.team2.local"
  type    = "A"

  alias {
    name                   = var.internal_nlb_dns_name
    zone_id                = var.internal_nlb_zone_id
    evaluate_target_health = false
  }
}
