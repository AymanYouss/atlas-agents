# Application secrets live in Secrets Manager and are projected into the cluster
# by the External Secrets Operator (installed via Helm). The database URL is
# assembled from the RDS module outputs so it always matches the provisioned DB.
resource "aws_secretsmanager_secret" "atlas" {
  name        = "${local.name}/app"
  description = "Atlas application secrets (LLM keys, database URL)."
  tags        = local.tags
}

resource "aws_secretsmanager_secret_version" "atlas" {
  secret_id = aws_secretsmanager_secret.atlas.id
  secret_string = jsonencode({
    ANTHROPIC_API_KEY = var.anthropic_api_key
    TAVILY_API_KEY    = var.tavily_api_key
    ATLAS_DATABASE_URL = format(
      "postgresql+asyncpg://%s:%s@%s/%s",
      local.db_user,
      random_password.db.result,
      module.rds.db_instance_endpoint,
      local.db_name,
    )
  })
}

# IRSA role that lets the External Secrets Operator read this secret.
data "aws_iam_policy_document" "external_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
    resources = [aws_secretsmanager_secret.atlas.arn]
  }
}

resource "aws_iam_policy" "external_secrets" {
  name   = "${local.name}-external-secrets"
  policy = data.aws_iam_policy_document.external_secrets.json
}

module "external_secrets_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.44"

  role_name = "${local.name}-external-secrets"
  role_policy_arns = {
    read = aws_iam_policy.external_secrets.arn
  }

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["atlas:atlas-external-secrets"]
    }
  }

  tags = local.tags
}
