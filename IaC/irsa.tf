# IRSA (IAM Roles for Service Accounts) Configuration
# Enables Kubernetes service accounts to assume IAM roles for AWS API access

# Get the OIDC provider endpoint from the EKS cluster
data "aws_eks_cluster" "cluster" {
  name = module.eks.cluster_name
}

# Create OIDC Provider for IRSA
resource "aws_iam_openid_connect_provider" "eks" {
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.eks.certificates[0].sha1_fingerprint]
  url             = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer

  tags = {
    Name    = "${module.eks.cluster_name}-irsa"
    Project = "ENPM818R_Group3"
  }
}

# Get the TLS certificate from the OIDC provider
data "tls_certificate" "eks" {
  url = data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer
}

# Helper local for creating trust policies
locals {
  oidc_provider_arn = aws_iam_openid_connect_provider.eks.arn
  oidc_url          = replace(aws_iam_openid_connect_provider.eks.url, "https://", "")
}

# Auth Service IRSA Role
resource "aws_iam_role" "auth_irsa" {
  name = "auth-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:prod:auth-sa"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "auth"
    Project = "ENPM818R_Group3"
  }
}

# Auth Secrets Manager Policy (for JWT secret)
resource "aws_iam_role_policy" "auth_secrets" {
  name = "auth-secrets-policy"
  role = aws_iam_role.auth_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.jwt_secret.arn
        ]
      }
    ]
  })
}

# Analytics Service IRSA Role
resource "aws_iam_role" "analytics_irsa" {
  name = "analytics-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:prod:analytics-sa"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "analytics"
    Project = "ENPM818R_Group3"
  }
}

# Analytics S3 Policy (for listing and reading video metadata)
resource "aws_iam_role_policy" "analytics_s3" {
  name = "analytics-s3-policy"
  role = aws_iam_role.analytics_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::video-analytics-uploads",
          "arn:aws:s3:::video-analytics-uploads/*"
        ]
      }
    ]
  })
}

# Analytics Secrets Manager Policy (for RDS credentials)
resource "aws_iam_role_policy" "analytics_secrets" {
  name = "analytics-secrets-policy"
  role = aws_iam_role.analytics_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          "arn:aws:secretsmanager:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:secret:video-analytics/*"
        ]
      }
    ]
  })
}

# Processor Service IRSA Role
resource "aws_iam_role" "processor_irsa" {
  name = "processor-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:prod:processor-sa"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "processor"
    Project = "ENPM818R_Group3"
  }
}

# Processor SQS Access Policy
resource "aws_iam_role_policy" "processor_sqs" {
  name = "processor-sqs-policy"
  role = aws_iam_role.processor_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = "arn:aws:sqs:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:*"
      }
    ]
  })
}

# Processor S3 Access Policy
resource "aws_iam_role_policy" "processor_s3" {
  name = "processor-s3-policy"
  role = aws_iam_role.processor_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:HeadObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::video-analytics-uploads",
          "arn:aws:s3:::video-analytics-uploads/*"
        ]
      }
    ]
  })
}

# Processor Secrets Manager Access Policy
resource "aws_iam_role_policy" "processor_secrets" {
  name = "processor-secrets-policy"
  role = aws_iam_role.processor_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = "arn:aws:secretsmanager:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:secret:video-analytics/*"
      }
    ]
  })
}

# Uploader Service IRSA Role
resource "aws_iam_role" "uploader_irsa" {
  name = "uploader-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:prod:uploader-sa"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "uploader"
    Project = "ENPM818R_Group3"
  }
}

# Uploader S3 Policy
resource "aws_iam_role_policy" "uploader_s3" {
  name = "uploader-s3-policy"
  role = aws_iam_role.uploader_irsa.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::video-analytics-uploads",
          "arn:aws:s3:::video-analytics-uploads/*"
        ]
      }
    ]
  })
}

# Gateway Service IRSA Role
resource "aws_iam_role" "gateway_irsa" {
  name = "gateway-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:prod:gateway-sa"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "gateway"
    Project = "ENPM818R_Group3"
  }
}

# Frontend Service IRSA Role
resource "aws_iam_role" "frontend_irsa" {
  name = "frontend-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:prod:frontend-sa"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "frontend"
    Project = "ENPM818R_Group3"
  }
}

# CloudWatch Agent IRSA Role (for monitoring)
resource "aws_iam_role" "cloudwatch_agent_irsa" {
  name = "eks-cloudwatch-agent-irsa-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${local.oidc_url}:sub" = "system:serviceaccount:amazon-cloudwatch:cloudwatch-agent"
            "${local.oidc_url}:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = {
    Service = "cloudwatch-agent"
    Project = "ENPM818R_Group3"
  }
}

# CloudWatch Agent Policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_policy" {
  role       = aws_iam_role.cloudwatch_agent_irsa.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Outputs for IRSA roles
output "irsa_roles" {
  description = "IRSA role information"
  value = {
    oidc_provider_arn = local.oidc_provider_arn
    auth_role_arn     = aws_iam_role.auth_irsa.arn
    analytics_role_arn = aws_iam_role.analytics_irsa.arn
    processor_role_arn = aws_iam_role.processor_irsa.arn
    uploader_role_arn  = aws_iam_role.uploader_irsa.arn
    gateway_role_arn   = aws_iam_role.gateway_irsa.arn
    frontend_role_arn  = aws_iam_role.frontend_irsa.arn
  }
}
