output "cluster_name" {
  value       = module.eks.cluster_name
  description = "EKS cluster name (use with: aws eks update-kubeconfig)."
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "region" {
  value = var.region
}

output "ecr_repository_urls" {
  value = { for k, r in aws_ecr_repository.atlas : k => r.repository_url }
}

output "rds_endpoint" {
  value     = module.rds.db_instance_endpoint
  sensitive = true
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.atlas.arn
}

output "kubeconfig_command" {
  value = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}
