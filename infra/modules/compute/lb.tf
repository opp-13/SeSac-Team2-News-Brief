# ---------------------------------------------------------------------------
# ACM certificate for the public ALB's HTTPS listener. Optional (var.enable_https).
# Looked up by domain, not created/validated here -- Route53 DNS validation for
# it is assumed to already be in place (issued via another Terraform config or
# manually).
# ---------------------------------------------------------------------------
data "aws_acm_certificate" "public" {
  count = var.enable_https ? 1 : 0

  domain      = var.acm_certificate_domain
  statuses    = ["ISSUED"]
  most_recent = true
}

# ---------------------------------------------------------------------------
# Public ALB: internet -> frontend instances
# ---------------------------------------------------------------------------
resource "aws_lb" "public" {
  name               = "${var.name_prefix}-public-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids
}

resource "aws_lb_target_group" "frontend" {
  name     = "${var.name_prefix}-frontend-tg"
  port     = var.frontend_port
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
  }
}

resource "aws_lb_target_group_attachment" "frontend" {
  count = length(module.frontend)

  target_group_arn = aws_lb_target_group.frontend.arn
  target_id        = module.frontend[count.index].id
  port             = var.frontend_port
}

# enable_https = false (기본값): 그냥 HTTP forward.
# enable_https = true: HTTPS(443)로 리다이렉트하고, 실제 forward는 아래 public_https가 담당.
resource "aws_lb_listener" "public_http" {
  load_balancer_arn = aws_lb.public.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = var.enable_https ? "redirect" : "forward"
    target_group_arn = var.enable_https ? null : aws_lb_target_group.frontend.arn

    dynamic "redirect" {
      for_each = var.enable_https ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}

resource "aws_lb_listener" "public_https" {
  count = var.enable_https ? 1 : 0

  load_balancer_arn = aws_lb.public.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = data.aws_acm_certificate.public[0].arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# ---------------------------------------------------------------------------
# Private NLB: frontend -> backend instances (internal only, not internet
# facing). No security_groups attached here on purpose -- the backend
# instances' own internal_api_security_group_id already restricts inbound
# traffic on backend_port to callers carrying the frontend's security group,
# which NLB preserves as the original client for same-VPC traffic.
# ---------------------------------------------------------------------------
resource "aws_lb" "internal" {
  name               = "${var.name_prefix}-internal-nlb"
  internal           = true
  load_balancer_type = "network"
  subnets            = var.backend_subnet_ids
}

resource "aws_lb_target_group" "backend" {
  name     = "${var.name_prefix}-backend-tg"
  port     = var.backend_port
  protocol = "TCP"
  vpc_id   = var.vpc_id

  health_check {
    protocol            = "TCP"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 10
  }
}

resource "aws_lb_target_group_attachment" "backend" {
  count = length(module.backend)

  target_group_arn = aws_lb_target_group.backend.arn
  target_id        = module.backend[count.index].id
  port             = var.backend_port
}

resource "aws_lb_listener" "internal_tcp" {
  load_balancer_arn = aws_lb.internal.arn
  port              = var.backend_port
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
