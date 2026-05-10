variable "service_names" {
  description = "TDSE service names that need ECR repositories."
  type        = list(string)
}

variable "tags" {
  description = "Tags applied to all resources."
  type        = map(string)
}
