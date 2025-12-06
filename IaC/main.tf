
// Fetch all the AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Reference existing VPC
data "aws_vpc" "existing" {
  id = "vpc-0482006eacc05081c"
}

# Reference existing private subnets
data "aws_subnets" "private" {
  filter {
    name   = "subnet-id"
    values = ["subnet-0e1c23f5bef0a0523", "subnet-04796fca1c11de44c", "subnet-0477efaa4cf9565fc"]
  }
}

# Reference existing EKS cluster (data source only, no module)
data "aws_eks_cluster" "existing" {
  name = "g3-eks-cluster"
}

data "aws_eks_cluster_auth" "existing" {
  name = "g3-eks-cluster"
}

