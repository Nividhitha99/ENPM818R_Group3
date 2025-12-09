terraform {
  required_version = ">= 1.3"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = ">= 2.0"
    }
  }
  backend "s3" {
    bucket  = "grp-3-terraform-state-bucket"    # your S3 bucket
    key     = "gp3-tf-state/terraform.tfstate"  # path inside bucket
    region  = "us-east-1"                       # your region
    encrypt = true                              # encrypt state at rest
  }
}
