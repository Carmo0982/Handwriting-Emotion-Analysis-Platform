variable "project_name" {
  description = "Project name used in resource names."
  type        = string
}

variable "environment" {
  description = "Environment name used in resource names."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for the DB subnet group."
  type        = list(string)
}

variable "eks_cluster_security_group_id" {
  description = "EKS cluster security group allowed to connect to PostgreSQL."
  type        = string
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
}

variable "db_username" {
  description = "PostgreSQL admin username."
  type        = string
}

variable "db_password" {
  description = "PostgreSQL admin password."
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
}
