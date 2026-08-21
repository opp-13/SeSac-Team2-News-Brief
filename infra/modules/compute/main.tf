locals {
  ami = coalesce(var.ami, data.aws_ami.al2023.id)
  # null when create_deploy = false -- no CodeDeploy pipeline exists to serve, so
  # nothing should attach the agent's instance profile either.
  codedeploy_instance_profile_name = var.create_deploy ? aws_iam_instance_profile.codedeploy_instance[0].name : null
}

# ---------------------------------------------------------------------------
# Frontend instances -- one per frontend subnet, private, sit behind the ALB
# (defined in lb.tf). web_security_group_id already allows the frontend port
# from the ALB's security group only.
# ---------------------------------------------------------------------------
module "frontend" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "~> 6.0"
  count   = length(var.frontend_subnet_ids)

  name = "${var.name_prefix}-frontend-${count.index}"

  ami                         = local.ami
  instance_type               = var.instance_type
  subnet_id                   = var.frontend_subnet_ids[count.index]
  vpc_security_group_ids      = [var.web_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = false
  iam_instance_profile        = local.codedeploy_instance_profile_name
  user_data                   = file("${path.module}/scripts/install_web.sh")
  user_data_replace_on_change = true
  # Role tag consumed by modules/deploy's ec2_tag_filter (frontend_role_tag_value) -- keep in sync.
  tags = var.create_deploy ? { Role = "frontend" } : {}

  root_block_device = {
    size = var.root_volume_size
    type = "gp3"
  }
}

# ---------------------------------------------------------------------------
# Backend instances -- one per backend subnet, private, sit behind the
# internal NLB (defined in lb.tf). internal_api_security_group_id already
# allows the backend port from the frontend's security group only.
# ---------------------------------------------------------------------------
module "backend" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "~> 6.0"
  count   = length(var.backend_subnet_ids)

  name = "${var.name_prefix}-backend-${count.index}"

  ami                         = local.ami
  instance_type               = var.instance_type
  subnet_id                   = var.backend_subnet_ids[count.index]
  vpc_security_group_ids      = [var.internal_api_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = false
  iam_instance_profile        = local.codedeploy_instance_profile_name
  user_data                   = file("${path.module}/scripts/install_was.sh")
  user_data_replace_on_change = true
  # Role tag consumed by modules/deploy's ec2_tag_filter (backend_role_tag_value) -- keep in sync.
  tags = var.create_deploy ? { Role = "backend" } : {}

  root_block_device = {
    size = var.root_volume_size
    type = "gp3"
  }
}

# ---------------------------------------------------------------------------
# DB instance -- exactly one, private, no load balancer in front of it.
# Backend instances reach it directly on 3306 (internal_mysql_security_group_id
# allows that from within the VPC CIDR).
# ---------------------------------------------------------------------------
module "db" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "~> 6.0"

  name = "${var.name_prefix}-db"

  ami                         = local.ami
  instance_type               = var.instance_type
  subnet_id                   = var.db_subnet_id
  vpc_security_group_ids      = [var.internal_mysql_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = false
  user_data                   = file("${path.module}/scripts/install_mysql.sh")
  user_data_replace_on_change = true

  root_block_device = {
    size = var.root_volume_size
    type = "gp3"
  }
}

# ---------------------------------------------------------------------------
# Redis instance -- exactly one, WAS(backend) subnet alongside the backend
# instances, no load balancer in front of it. internal_redis_security_group_id
# already allows 6379 from within the VPC CIDR.
# ---------------------------------------------------------------------------
module "redis" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "~> 6.0"

  name = "${var.name_prefix}-redis"

  ami                         = local.ami
  instance_type               = var.instance_type
  subnet_id                   = var.backend_subnet_ids[0]
  vpc_security_group_ids      = [var.internal_redis_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = false
  user_data                   = file("${path.module}/scripts/install_redis.sh")
  user_data_replace_on_change = true

  root_block_device = {
    size = var.root_volume_size
    type = "gp3"
  }
}

# ---------------------------------------------------------------------------
# Bastion host -- optional (var.create_bastion), single instance in the first
# public subnet. bastion_security_group_id already only allows SSH from
# var.bastion_ssh_cidr (set on the network module).
# ---------------------------------------------------------------------------
module "bastion" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "~> 6.0"
  count   = var.create_bastion ? 1 : 0

  name = "${var.name_prefix}-bastion"

  ami                         = local.ami
  instance_type               = var.instance_type
  subnet_id                   = var.public_subnet_ids[0]
  vpc_security_group_ids      = [var.bastion_security_group_id]
  key_name                    = var.key_pair_name
  associate_public_ip_address = true
  user_data                   = file("${path.module}/scripts/install_bastion.sh")
  user_data_replace_on_change = true

  root_block_device = {
    size = var.root_volume_size
    type = "gp3"
  }
}
