output "bootstrap_servers" {
  description = "MSK TLS bootstrap brokers."
  value       = aws_msk_cluster.this.bootstrap_brokers_tls
}

output "bootstrap_servers_tls" {
  description = "MSK TLS bootstrap brokers."
  value       = aws_msk_cluster.this.bootstrap_brokers_tls
}

output "security_group_id" {
  description = "MSK security group ID."
  value       = aws_security_group.msk.id
}
