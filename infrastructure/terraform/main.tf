terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "tdse-terraform-state-prod"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "tdse-terraform-locks"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
  }

  service_names = [
    "auth-service",
    "upload-service",
    "preprocessing-service",
    "inference-service",
    "results-service",
    "tenant-service",
  ]
}

module "vpc" {
  source = "./modules/vpc"

  project_name         = var.project_name
  environment          = var.environment
  vpc_cidr             = var.vpc_cidr
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  tags                 = local.common_tags
}

module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
  bucket_name  = var.s3_bucket_name
  tags         = local.common_tags
}

module "dynamodb" {
  source = "./modules/dynamodb"

  table_name = var.dynamodb_table_name
  tags       = local.common_tags
}

module "ecr" {
  source = "./modules/ecr"

  service_names = local.service_names
  tags          = local.common_tags
}

module "eks" {
  source = "./modules/eks"

  project_name       = var.project_name
  environment        = var.environment
  cluster_version    = var.eks_cluster_version
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  s3_bucket_arn      = module.s3.bucket_arn
  dynamodb_table_arn = module.dynamodb.table_arn
  tags               = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  project_name                  = var.project_name
  environment                   = var.environment
  vpc_id                        = module.vpc.vpc_id
  private_subnet_ids            = module.vpc.private_subnet_ids
  eks_cluster_security_group_id = module.eks.cluster_security_group_id
  db_name                       = var.db_name
  db_username                   = var.db_username
  db_password                   = var.db_password
  tags                          = local.common_tags
}

module "msk" {
  source = "./modules/msk"

  project_name                  = var.project_name
  environment                   = var.environment
  vpc_id                        = module.vpc.vpc_id
  private_subnet_ids            = module.vpc.private_subnet_ids
  eks_cluster_security_group_id = module.eks.cluster_security_group_id
  kafka_version                 = var.kafka_version
  topics                        = var.kafka_topics
  create_topics                 = var.create_kafka_topics
  tags                          = local.common_tags
}

resource "aws_secretsmanager_secret" "database_url" {
  name        = "/${var.project_name}/${var.environment}/database-url"
  description = "Async SQLAlchemy PostgreSQL URL for TDSE services."
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = format(
    "postgresql+asyncpg://%s:%s@%s:%s/%s",
    var.db_username,
    var.db_password,
    module.rds.endpoint,
    module.rds.port,
    var.db_name,
  )
}

resource "aws_secretsmanager_secret" "jwt_secret_key" {
  name        = "/${var.project_name}/${var.environment}/jwt-secret-key"
  description = "JWT signing secret shared by TDSE auth-aware services."
}

resource "aws_secretsmanager_secret_version" "jwt_secret_key" {
  secret_id     = aws_secretsmanager_secret.jwt_secret_key.id
  secret_string = var.jwt_secret_key
}
