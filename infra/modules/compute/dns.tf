# ---------------------------------------------------------------------------
# team2.local private hosted zone -- resolves only inside this VPC. Lives in
# this module (not modules/network) on purpose: db/redis private IPs and the
# internal NLB's dns_name/zone_id are all created right here, so this avoids
# passing them back out to network and back in again (a backwards, confusing
# cross-module dependency that also complicated destroy ordering).
# ---------------------------------------------------------------------------
resource "aws_route53_zone" "private" {
  count = var.enable_private_dns ? 1 : 0

  name = "team2.local"

  vpc {
    vpc_id = var.vpc_id
  }
}

resource "aws_route53_record" "db" {
  count = var.enable_private_dns ? 1 : 0

  zone_id = aws_route53_zone.private[0].zone_id
  name    = "db.team2.local"
  type    = "A"
  ttl     = 300
  records = [module.db.private_ip]
}

resource "aws_route53_record" "redis" {
  count = var.enable_private_dns ? 1 : 0

  zone_id = aws_route53_zone.private[0].zone_id
  name    = "redis.team2.local"
  type    = "A"
  ttl     = 300
  records = [module.redis.private_ip]
}

resource "aws_route53_record" "api" {
  count = var.enable_private_dns ? 1 : 0

  zone_id = aws_route53_zone.private[0].zone_id
  name    = "api.team2.local"
  type    = "A"

  alias {
    name                   = aws_lb.internal.dns_name
    zone_id                = aws_lb.internal.zone_id
    evaluate_target_health = false
  }
}
