output "eks_cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint."
  value       = module.rds.endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for handwritten images."
  value       = module.s3.bucket_name
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for inference results."
  value       = module.dynamodb.table_name
}

output "msk_bootstrap_servers_tls" {
  description = "MSK TLS bootstrap broker string."
  value       = module.msk.bootstrap_servers_tls
}

output "ecr_urls" {
  description = "Map of service name to ECR repository URL."
  value       = module.ecr.repository_urls
}
