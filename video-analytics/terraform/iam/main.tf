variable "cluster_oidc_issuer_url" {}
variable "upload_bucket_arn" {}
variable "job_queue_arn" {}
variable "metadata_table_arn" {}

# IAM Policy for Uploader Service
resource "aws_iam_policy" "uploader_policy" {
  name        = "UploaderServicePolicy"
  description = "Policy for Uploader Service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = "${var.upload_bucket_arn}/*"
      },
      {
        Action = [
          "sqs:SendMessage"
        ]
        Effect   = "Allow"
        Resource = var.job_queue_arn
      }
    ]
  })
}

# IAM Policy for Processor Service
resource "aws_iam_policy" "processor_policy" {
  name        = "ProcessorServicePolicy"
  description = "Policy for Processor Service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Effect   = "Allow"
        Resource = var.job_queue_arn
      },
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Effect   = "Allow"
        Resource = var.metadata_table_arn
      }
    ]
  })
}

# IAM Policy for Analytics Service
resource "aws_iam_policy" "analytics_policy" {
  name        = "AnalyticsServicePolicy"
  description = "Policy for Analytics Service"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query",
          "dynamodb:UpdateItem"
        ]
        Effect   = "Allow"
        Resource = var.metadata_table_arn
      }
    ]
  })
}

module "uploader_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "uploader-role"

  oidc_providers = {
    main = {
      provider_arn               = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${replace(var.cluster_oidc_issuer_url, "https://", "")}"
      namespace_service_accounts = ["prod:uploader-sa"]
    }
  }

  role_policy_arns = {
    policy = aws_iam_policy.uploader_policy.arn
  }
}

# Assume similar blocks for Processor and Analytics
# ...
data "aws_caller_identity" "current" {}

