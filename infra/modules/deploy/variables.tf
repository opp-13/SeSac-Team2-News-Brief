variable "name_prefix" {
  description = "Prefix used for resource names (e.g. \"dmz\")"
  type        = string
}

variable "frontend_role_tag_value" {
  description = "Value of the Role tag on frontend instances (must match modules/compute's frontend `tags = { Role = ... }`)"
  type        = string
  default     = "frontend"
}

variable "backend_role_tag_value" {
  description = "Value of the Role tag on backend instances (must match modules/compute's backend `tags = { Role = ... }`)"
  type        = string
  default     = "backend"
}

variable "github_org" {
  description = "GitHub org/user that owns the deploy workflow's repo, for OIDC trust policy scoping"
  type        = string
  default     = "opp-13"
}

variable "github_repo" {
  description = "GitHub repo name containing the deploy workflow, for OIDC trust policy scoping"
  type        = string
  default     = "SeSac-Team2-News-Brief"
}
