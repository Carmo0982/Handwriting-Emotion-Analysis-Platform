output "repository_urls" {
  description = "Map of TDSE service name to ECR repository URL."
  value = {
    for service_name, repository in aws_ecr_repository.service :
    service_name => repository.repository_url
  }
}
