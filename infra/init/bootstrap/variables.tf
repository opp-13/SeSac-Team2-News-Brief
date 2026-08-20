variable "bucket_name" {
  description = "Name of the S3 bucket that will hold Terraform remote state for this project"
  type        = string
  default     = "terraform-s3-sesac-team2"
}

variable "aws_profile" {
  description = "Named AWS CLI profile to use. Leave null to fall back to the default AWS credential chain."
  type        = string
  default     = null
}
