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
  description = "Private subnet IDs for MSK brokers."
  type        = list(string)
}

variable "eks_cluster_security_group_id" {
  description = "EKS cluster security group allowed to connect to MSK."
  type        = string
}

variable "kafka_version" {
  description = "Kafka version for MSK."
  type        = string
}

variable "topics" {
  description = "Kafka topics used by TDSE."
  type        = list(string)
}

variable "create_topics" {
  description = "Create Kafka topics with kafka-topics.sh from the Terraform runner."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
}
