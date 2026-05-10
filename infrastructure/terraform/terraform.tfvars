aws_region   = "us-east-1"
project_name = "tdse"
environment  = "production"

db_name     = "tdse"
db_username = "tdse_admin"
db_password = "REPLACE_WITH_VALUE_FROM_AWS_SECRETS_MANAGER"

jwt_secret_key = "REPLACE_WITH_STRONG_JWT_SECRET_FROM_AWS_SECRETS_MANAGER"

s3_bucket_name      = "tdse-production-handwriting-images-example"
dynamodb_table_name = "inference-results"
kafka_version       = "3.5.1"
create_kafka_topics = false
