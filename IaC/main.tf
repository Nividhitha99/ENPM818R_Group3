
// Fetch all the AZs in the region
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

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
  # endpoint_public_access = true
  endpoint_private_access = true
  # endpoint_public_access_cidrs = ["0.0.0.0/0"]

  access_entries = merge(
  {
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
  },

  # Dynamic users from variable
  {
    for name, user in var.eks_users : name => {
      principal_arn = user.arn
      type          = "STANDARD"

      policy_associations = {
        main = {
          policy_arn = user.policy == "ADMIN" ? "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy" : "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterReadOnlyPolicy"
          access_scope = {
            type = "cluster"
            namespaces = []
          }
        }
      }
    }
  }
  )



  # Create two managed node groups across at least 2 AZs.
  eks_managed_node_groups = {
    general-1 = {
      name = "general-1"
      instance_types = ["t3.medium", "t3.large", "t3a.medium"]
      ami_type = "AL2023_x86_64_STANDARD"
      desired_size = 4
      min_size = 3
      max_size = 5
    }

    general-2 = {
      name = "general-2"
      instance_types = ["t3.medium", "t3.large", "t3a.medium"]
      ami_type = "AL2023_x86_64_STANDARD"
      desired_size = 4
      min_size = 3
      max_size = 5
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

  enable_irsa = true

  tags = {
    Project     = "ENPM818R_Group3"
  }
}

# Data: cluster oidc provider from module output
data "aws_iam_openid_connect_provider" "oidc" {
  url = module.eks.cluster_oidc_issuer_url # module output when enable_irsa = true
}

# IAM role assume policy for IRSA
data "aws_iam_policy_document" "alb_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.oidc.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:aws-load-balancer-controller"]
    }
  }
}

resource "aws_iam_role" "alb_irsa_role" {
  name               = "${module.eks.cluster_name}-alb-irsa"
  assume_role_policy = data.aws_iam_policy_document.alb_assume_role.json
}

resource "aws_iam_role_policy_attachment" "alb_policy_attach" {
  role       = aws_iam_role.alb_irsa_role.name
  policy_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:policy/AWSLoadBalancerControllerIAMPolicy"
}


resource "kubernetes_service_account" "alb" {
  metadata {
    name      = "aws-load-balancer-controller"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.alb_irsa_role.arn
    }
  }
}

resource "helm_release" "aws_lb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"

  values = [<<EOF
clusterName: ${module.eks.cluster_name}
serviceAccount:
  create: false
  name: ${kubernetes_service_account.alb.metadata[0].name}
region: ${var.region}
vpcId: ${module.vpc.vpc_id}
EOF
  ]
  depends_on = [aws_iam_role_policy_attachment.alb_policy_attach]
}


# C. Create IAM role + install Cluster Autoscaler (IRSA)

# Assume role policy document for autoscaler
data "aws_iam_policy_document" "autoscaler_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.oidc.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:sub"
      values   = ["system:serviceaccount:kube-system:cluster-autoscaler-aws-cluster-autoscaler"]
    }
    condition {
      test     = "StringEquals"
      variable = "${replace(module.eks.cluster_oidc_issuer_url, "https://", "")}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster_autoscaler_irsa_role" {
  name               = "${module.eks.cluster_name}-cluster-autoscaler-irsa"
  assume_role_policy = data.aws_iam_policy_document.autoscaler_assume.json
}

resource "aws_iam_policy" "cluster_autoscaler_policy" {
  name   = "${module.eks.cluster_name}-autoscaler-policy"
  policy = file("${path.module}/policies/cluster-autoscaler-policy.json")
}

resource "aws_iam_role_policy_attachment" "attach_autoscaler_policy" {
  role       = aws_iam_role.cluster_autoscaler_irsa_role.name
  policy_arn = aws_iam_policy.cluster_autoscaler_policy.arn
}

resource "kubernetes_service_account" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscaler-aws-cluster-autoscaler"
    namespace = "kube-system"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.cluster_autoscaler_irsa_role.arn
    }
  }
}

# Helm install cluster-autoscaler
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  namespace  = "kube-system"
  values = [<<EOF
    autoDiscovery:
      clusterName: ${module.eks.cluster_name}
    awsRegion: ${var.region}
    serviceAccount:
      create: false
      name: ${kubernetes_service_account.cluster_autoscaler.metadata[0].name}
    extraArgs:
      skip-nodes-with-local-storage: false
      expander: least-waste
    EOF
  ]
  depends_on = [aws_iam_role_policy_attachment.attach_autoscaler_policy]
}


# ========== ENVIRONMENTS ==========
locals {
  environments = ["dev", "staging", "prod"]
}

# ========== NAMESPACE CREATION ==========
resource "kubernetes_namespace" "env" {
  for_each = toset(local.environments)

  metadata {
    name = each.key
  }
}

# ========== SERVICE ACCOUNTS ==========
resource "kubernetes_service_account" "ci" {
  for_each = kubernetes_namespace.env

  metadata {
    name      = "ci"
    namespace = each.key
  }
}

# ========== READ-ONLY ROLES ==========
resource "kubernetes_role" "ci_readonly" {
  for_each = kubernetes_namespace.env

  metadata {
    name      = "ci-readonly"
    namespace = each.key
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "pods/log", "services"]
    verbs      = ["get", "list", "watch"]
  }
}

# ========== ROLE BINDINGS ==========
resource "kubernetes_role_binding" "ci_readonly_binding" {
  for_each = kubernetes_namespace.env

  metadata {
    name      = "ci-readonly-binding"
    namespace = each.key
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role.ci_readonly[each.key].metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.ci[each.key].metadata[0].name
    namespace = each.key
  }
}
