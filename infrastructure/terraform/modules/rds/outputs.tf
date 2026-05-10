output "endpoint" {
  description = "RDS PostgreSQL endpoint."
  value       = aws_db_instance.postgres.address
}

output "port" {
  description = "RDS PostgreSQL port."
  value       = aws_db_instance.postgres.port
}

output "security_group_id" {
  description = "RDS security group ID."
  value       = aws_security_group.rds.id
}
