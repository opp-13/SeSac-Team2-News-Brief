locals {
  common_tags = {
    Owner       = var.owner
    Zone        = var.zone
    Project     = var.project
    Environment = var.environment
    ManagedBy   = var.mangedby
  }
}
