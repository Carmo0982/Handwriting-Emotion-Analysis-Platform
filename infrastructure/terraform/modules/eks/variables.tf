variable "project_name" {
  description = "Project name used in resource names."
  type        = string
}

variable "environment" {
  description = "Environment name used in resource names."
  type        = string
}

variable "cluster_version" {
  description = "EKS Kubernetes version."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for EKS control plane and node groups."
  type        = list(string)
}

variable "s3_bucket_arn" {
  description = "S3 bucket ARN accessed by TDSE pods."
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB table ARN accessed by TDSE pods."
  type        = string
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
}
