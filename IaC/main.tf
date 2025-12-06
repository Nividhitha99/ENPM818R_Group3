
// Fetch all the AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = ">= 4.0"

  name = "eks-g3-vpc"
  cidr = "10.0.0.0/16"

  azs             = slice(data.aws_availability_zones.available.names, 0, 3) # pick 3 AZs
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = false
  enable_dns_hostnames = true
  enable_dns_support = true
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "21.10.1"
  kubernetes_version = "1.33"
  name    = "g3-eks-cluster"
  subnet_ids = module.vpc.private_subnets
  vpc_id = module.vpc.vpc_id
  
  access_entries = {
    cluster_admin = {
      principal_arn = data.aws_caller_identity.current.arn

      type = "STANDARD"

      policy_associations = {
        admin = {
          policy_arn = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = {
            type       = "cluster"
            namespaces = []
          }
        }
      }
    }
  }


  # Control plane logging if desired
  # enable_irsa = true
  
  # Create two managed node groups across at least 2 AZs.
  eks_managed_node_groups = {
    general-1 = {
      name = "general-1"
      instance_types = ["t3.medium", "t3.large", "t3a.medium"]
      ami_type = "AL2023_x86_64_STANDARD"
      desired_capacity = 2
      min_size = 1
      max_size = 3
    }

    general-2 = {
      name = "general-2"
      instance_types = ["t3.medium", "t3.large", "t3a.medium"]
      ami_type = "AL2023_x86_64_STANDARD"
      desired_capacity = 2
      min_size = 1
      max_size = 3
    }
  }

  addons = {
    coredns = {}
    eks-pod-identity-agent = {
      before_compute = true
    }
    kube-proxy = {}
    vpc-cni = {
      before_compute = true
    }
  }
}
