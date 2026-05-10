output "bucket_name" {
  description = "S3 bucket name."
  value       = aws_s3_bucket.images.bucket
}

output "bucket_arn" {
  description = "S3 bucket ARN."
  value       = aws_s3_bucket.images.arn
}

output "tenant_scoped_policy_arn" {
  description = "IAM policy ARN for tenant-prefixed S3 access."
  value       = aws_iam_policy.tenant_scoped_s3_access.arn
}
