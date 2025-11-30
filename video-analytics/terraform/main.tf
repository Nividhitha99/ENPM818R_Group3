# ===============================
# Providers
# ===============================
provider "aws" {
  region = var.aws_region
}

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

# ===============================
# VPC MODULE
# ===============================
module "vpc" {
  source = "./vpc"

  vpc_name     = "video-analytics-vpc"
  project      = "video-analytics"
  cluster_name = var.cluster_name

  vpc_cidr = var.vpc_cidr

  availability_zones = [
    "${var.aws_region}a",
    "${var.aws_region}b"
  ]

  private_subnet_cidrs = [
    "10.0.1.0/24",
    "10.0.2.0/24"
  ]

  public_subnet_cidrs = [
    "10.0.11.0/24",
    "10.0.12.0/24"
  ]
}

# ===============================
# EKS MODULE
# ===============================
module "eks" {
  source = "./eks"

  cluster_name = var.cluster_name
  aws_region   = var.aws_region

  vpc_id     = module.vpc.vpc_id
  subnet_ids = [
    "subnet-04c3880aed46b0d01",
    "subnet-0cbe408b4e5ee1029"
  ]

}

# ===============================
# STORAGE MODULES
# ===============================
module "s3" {
  source      = "./s3"
  bucket_name = var.upload_bucket_name
}

module "sqs" {
  source     = "./sqs"
  queue_name = var.job_queue_name
}

module "dynamodb" {
  source     = "./dynamodb"
  table_name = var.metadata_table_name
}

# ===============================
# IAM / IRSA MODULE
# ===============================
module "iam" {
  source = "./iam"

  cluster_oidc_issuer_url = module.eks.cluster_oidc_issuer_url

  upload_bucket_arn  = module.s3.bucket_arn
  job_queue_arn      = module.sqs.queue_arn
  metadata_table_arn = module.dynamodb.table_arn
}



# ===============================
# Outputs
# ===============================
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_id
}

output "s3_bucket_arn" {
  value = module.s3.bucket_arn
}

output "sqs_queue_url" {
  value = module.sqs.queue_url
}
