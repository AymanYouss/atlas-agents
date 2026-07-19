resource "random_password" "db" {
  length  = 24
  special = false
}

module "db_security_group" {
  source  = "terraform-aws-modules/security-group/aws"
  version = "~> 5.2"

  name        = "${local.name}-rds"
  description = "Allow Postgres from the EKS node security group only."
  vpc_id      = module.vpc.vpc_id

  ingress_with_source_security_group_id = [
    {
      from_port                = 5432
      to_port                  = 5432
      protocol                 = "tcp"
      description              = "Postgres from EKS nodes"
      source_security_group_id = module.eks.node_security_group_id
    }
  ]

  tags = local.tags
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.9"

  identifier = "${local.name}-postgres"

  engine               = "postgres"
  engine_version       = "16"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_allocated_storage * 4
  storage_encrypted     = true

  db_name                     = local.db_name
  username                    = local.db_user
  password                    = random_password.db.result
  port                        = 5432
  manage_master_user_password = false

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group_name
  vpc_security_group_ids = [module.db_security_group.security_group_id]

  backup_retention_period      = 14
  deletion_protection          = true
  skip_final_snapshot          = false
  performance_insights_enabled = true

  tags = local.tags
}
