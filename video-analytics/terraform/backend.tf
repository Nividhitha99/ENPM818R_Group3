terraform {
  backend "s3" {
    bucket         = "enpm818r-group3-tfstate"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
