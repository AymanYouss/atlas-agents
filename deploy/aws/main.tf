data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs     = slice(data.aws_availability_zones.available.names, 0, 3)
  tags    = { Project = "atlas", Environment = var.environment }
  name    = var.cluster_name
  db_name = "atlas"
  db_user = "atlas"
}

# ------------------------------------------------------------------------- VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.13"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  private_subnets  = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i)]
  public_subnets   = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i + 8)]
  database_subnets = [for i in range(3) : cidrsubnet(var.vpc_cidr, 4, i + 12)]

  enable_nat_gateway           = true
  single_nat_gateway           = true
  enable_dns_hostnames         = true
  create_database_subnet_group = true

  # Tags required by the AWS Load Balancer Controller for subnet discovery.
  public_subnet_tags  = { "kubernetes.io/role/elb" = "1" }
  private_subnet_tags = { "kubernetes.io/role/internal-elb" = "1" }

  tags = local.tags
}

# ------------------------------------------------------------------------- EKS
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.24"

  cluster_name    = local.name
  cluster_version = var.cluster_version

  cluster_endpoint_public_access = true
  enable_irsa                    = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    default = {
      instance_types = var.node_instance_types
      desired_size   = var.node_desired_size
      min_size       = var.node_min_size
      max_size       = var.node_max_size
      capacity_type  = "ON_DEMAND"
      labels         = { workload = "atlas" }
    }
  }

  # Add-ons kept current for networking, DNS and storage.
  cluster_addons = {
    coredns            = { most_recent = true }
    kube-proxy         = { most_recent = true }
    vpc-cni            = { most_recent = true }
    aws-ebs-csi-driver = { most_recent = true }
  }

  tags = local.tags
}

# IRSA role for the AWS Load Balancer Controller (installed via Helm out of band).
module "lb_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.44"

  role_name                              = "${local.name}-alb-controller"
  attach_load_balancer_controller_policy = true

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = local.tags
}
