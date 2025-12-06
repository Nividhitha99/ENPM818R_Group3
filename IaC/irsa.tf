# IRSA (IAM Roles for Service Accounts) Configuration

# Get OIDC Provider thumbprint
data "tls_certificate" "cluster" {
  url = data.aws_eks_cluster.existing.identity[0].oidc[0].issuer
}

# Reference existing OIDC Provider or create if doesn't exist
data "aws_iam_openid_connect_provider" "eks" {
  arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${replace(data.aws_eks_cluster.existing.identity[0].oidc[0].issuer, "https://", "")}"
}

# Helper function to create IRSA role trust policy
locals {
  namespace = "prod"
  oidc_provider_arn = data.aws_iam_openid_connect_provider.eks.arn
  oidc_provider_url = replace(data.aws_eks_cluster.existing.identity[0].oidc[0].issuer, "https://", "")
  
  services = {
    auth = {
      namespace = "prod"
    }
    analytics = {
      namespace = "prod"
    }
    gateway = {
      namespace = "prod"
    }
    processor = {
      namespace = "prod"
    }
    uploader = {
      namespace = "prod"
    }
    frontend = {
      namespace = "prod"
    }
  }
}

# Create trust policy for IRSA roles
data "aws_iam_policy_document" "irsa_trust_policy" {
  for_each = local.services

  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:${each.value.namespace}:${each.key}-sa"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

# Import existing auth-irsa-role
resource "aws_iam_role" "auth" {
  name               = "auth-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust_policy["auth"].json

  tags = {
    Name        = "auth-irsa-role"
    Service     = "auth"
    Environment = "prod"
  }

  lifecycle {
    ignore_changes = [assume_role_policy]
  }
}

# Create analytics-irsa-role
resource "aws_iam_role" "analytics" {
  name               = "analytics-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust_policy["analytics"].json

  tags = {
    Name        = "analytics-irsa-role"
    Service     = "analytics"
    Environment = "prod"
  }
}

# Create gateway-irsa-role
resource "aws_iam_role" "gateway" {
  name               = "gateway-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust_policy["gateway"].json

  tags = {
    Name        = "gateway-irsa-role"
    Service     = "gateway"
    Environment = "prod"
  }
}

# Create processor-irsa-role
resource "aws_iam_role" "processor" {
  name               = "processor-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust_policy["processor"].json

  tags = {
    Name        = "processor-irsa-role"
    Service     = "processor"
    Environment = "prod"
  }
}

# Create uploader-irsa-role
resource "aws_iam_role" "uploader" {
  name               = "uploader-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust_policy["uploader"].json

  tags = {
    Name        = "uploader-irsa-role"
    Service     = "uploader"
    Environment = "prod"
  }
}

# Create frontend-irsa-role
resource "aws_iam_role" "frontend" {
  name               = "frontend-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.irsa_trust_policy["frontend"].json

  tags = {
    Name        = "frontend-irsa-role"
    Service     = "frontend"
    Environment = "prod"
  }
}

# Example: S3 policy for uploader service (adjust based on your needs)
data "aws_iam_policy_document" "uploader_policy" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket"
    ]
    resources = ["arn:aws:s3:::video-analytics-bucket/*", "arn:aws:s3:::video-analytics-bucket"]
  }
}

resource "aws_iam_role_policy" "uploader" {
  name   = "uploader-s3-policy"
  role   = aws_iam_role.uploader.id
  policy = data.aws_iam_policy_document.uploader_policy.json
}

# Example: DynamoDB policy for analytics service (adjust based on your needs)
data "aws_iam_policy_document" "analytics_policy" {
  statement {
    actions = [
      "dynamodb:GetItem",
      "dynamodb:Query",
      "dynamodb:Scan"
    ]
    resources = ["arn:aws:dynamodb:us-east-1:385046010615:table/analytics-*"]
  }
}

resource "aws_iam_role_policy" "analytics" {
  name   = "analytics-dynamodb-policy"
  role   = aws_iam_role.analytics.id
  policy = data.aws_iam_policy_document.analytics_policy.json
}

# Output IRSA role ARNs
output "irsa_role_arns" {
  description = "ARNs of all IRSA roles"
  value = {
    auth      = aws_iam_role.auth.arn
    analytics = aws_iam_role.analytics.arn
    gateway   = aws_iam_role.gateway.arn
    processor = aws_iam_role.processor.arn
    uploader  = aws_iam_role.uploader.arn
    frontend  = aws_iam_role.frontend.arn
  }
}

output "oidc_provider_arn" {
  description = "ARN of the OIDC provider"
  value       = local.oidc_provider_arn
}
