variable "vpc_id" {
  description = "Existing VPC with at least one public subnet."
  type        = string

  validation {
    condition     = length(var.vpc_id) > 4 && substr(var.vpc_id, 0, 4) == "vpc-"
    error_message = "Must start with: \"vpc-\"."
  }
}
