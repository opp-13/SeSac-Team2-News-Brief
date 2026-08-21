output "bucket_name" {
  description = "S3 bucket name to use as the backend bucket in other Terraform configs"
  value       = aws_s3_bucket.tfstate.id
}

output "bucket_arn" {
  description = "S3 bucket ARN"
  value       = aws_s3_bucket.tfstate.arn
}
