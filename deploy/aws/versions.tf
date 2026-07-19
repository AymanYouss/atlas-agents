terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.40"
    }
  }

  # Configure a remote backend for real deployments.
  # backend "s3" {
  #   bucket         = "atlas-tfstate"
  #   key            = "atlas/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "atlas-tflock"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project     = "atlas"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
