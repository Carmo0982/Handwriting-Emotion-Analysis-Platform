variable "aws_region" {
  description = "AWS region where TDSE production infrastructure will be deployed."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for tags and resource names."
  type        = string
  default     = "tdse"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the TDSE VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets used by the public load balancer."
  type        = list(string)
  default     = ["10.0.0.0/24", "10.0.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets used by EKS pods, RDS, and MSK."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "eks_cluster_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.29"
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "tdse"
}

variable "db_username" {
  description = "PostgreSQL admin username."
  type        = string
  default     = "tdse_admin"
}

variable "db_password" {
  description = "PostgreSQL admin password. Do not commit real values."
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT signing secret. Do not commit real values."
  type        = string
  sensitive   = true
}

variable "s3_bucket_name" {
  description = "Globally unique S3 bucket name for handwritten image objects."
  type        = string
  default     = null
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for inference results."
  type        = string
  default     = "inference-results"
}

variable "kafka_version" {
  description = "MSK Kafka version."
  type        = string
  default     = "3.5.1"
}

variable "kafka_topics" {
  description = "Kafka topics used by the TDSE event pipeline."
  type        = list(string)
  default     = ["image-uploaded", "image-preprocessed", "inference-result"]
}

variable "create_kafka_topics" {
  description = "Whether Terraform should create MSK topics using kafka-topics.sh from a runner with VPC access."
  type        = bool
  default     = false
}
