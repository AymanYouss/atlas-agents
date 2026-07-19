variable "region" {
  type        = string
  default     = "eu-west-1"
  description = "AWS region."
}

variable "environment" {
  type        = string
  default     = "production"
  description = "Deployment environment name."
}

variable "cluster_name" {
  type        = string
  default     = "atlas"
  description = "EKS cluster name."
}

variable "cluster_version" {
  type        = string
  default     = "1.31"
  description = "EKS Kubernetes version."
}

variable "vpc_cidr" {
  type    = string
  default = "10.60.0.0/16"
}

variable "node_instance_types" {
  type        = list(string)
  default     = ["m6i.large"]
  description = "Managed node group instance types."
}

variable "node_desired_size" {
  type    = number
  default = 3
}

variable "node_min_size" {
  type    = number
  default = 3
}

variable "node_max_size" {
  type    = number
  default = 8
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_allocated_storage" {
  type    = number
  default = 50
}

variable "anthropic_api_key" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Stored in Secrets Manager; leave blank and set the secret out of band."
}

variable "tavily_api_key" {
  type      = string
  default   = ""
  sensitive = true
}
