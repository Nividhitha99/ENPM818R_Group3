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

module "vpc" {
  source = "./vpc"
  
  vpc_cidr = var.vpc_cidr
  cluster_name = var.cluster_name
  aws_region = var.aws_region
}

module "eks" {
  source = "./eks"

  cluster_name = var.cluster_name
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  aws_region = var.aws_region
}

module "s3" {
  source = "./s3"
  bucket_name = var.upload_bucket_name
}

module "sqs" {
  source = "./sqs"
  queue_name = var.job_queue_name
}

module "dynamodb" {
  source = "./dynamodb"
  table_name = var.metadata_table_name
}

# IAM for Service Accounts (IRSA) setup is typically done alongside EKS or apps
module "iam" {
  source = "./iam"
  
  cluster_oidc_issuer_url = module.eks.cluster_oidc_issuer_url
  upload_bucket_arn = module.s3.bucket_arn
  job_queue_arn = module.sqs.queue_arn
  metadata_table_arn = module.dynamodb.table_arn
}

