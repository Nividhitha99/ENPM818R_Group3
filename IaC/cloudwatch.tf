# CloudWatch Observability Configuration for EKS

# Create CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "eks_applications" {
  name              = "/aws/eks/g3-eks-cluster/applications"
  retention_in_days = 30

  tags = {
    Name        = "eks-applications-logs"
    Environment = "prod"
  }
}

# Create CloudWatch Log Group for EKS cluster logs
resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/g3-eks-cluster/cluster"
  retention_in_days = 90

  tags = {
    Name        = "eks-cluster-logs"
    Environment = "prod"
  }
}

# IAM Role for CloudWatch Agent
data "aws_iam_policy_document" "cloudwatch_agent_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:sub"
      values   = ["system:serviceaccount:amazon-cloudwatch:cloudwatch-sa"]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_url}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cloudwatch_agent" {
  name               = "eks-cloudwatch-agent-irsa-role"
  assume_role_policy = data.aws_iam_policy_document.cloudwatch_agent_trust.json

  tags = {
    Name        = "eks-cloudwatch-agent-irsa"
    Environment = "prod"
  }
}

# Attach CloudWatch Agent policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent_policy" {
  role       = aws_iam_role.cloudwatch_agent.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Allow writing to CloudWatch Logs
data "aws_iam_policy_document" "cloudwatch_logs_policy" {
  statement {
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:CreateLogGroup"
    ]
    resources = [
      aws_cloudwatch_log_group.eks_applications.arn,
      "${aws_cloudwatch_log_group.eks_applications.arn}:*",
      aws_cloudwatch_log_group.eks_cluster.arn,
      "${aws_cloudwatch_log_group.eks_cluster.arn}:*"
    ]
  }

  statement {
    actions = [
      "ec2:DescribeVolumes",
      "ec2:DescribeTags",
      "ec2:DescribeInstances",
      "ec2:DescribeInstanceAttribute"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "cloudwatch_logs" {
  name   = "cloudwatch-logs-policy"
  role   = aws_iam_role.cloudwatch_agent.id
  policy = data.aws_iam_policy_document.cloudwatch_logs_policy.json
}

# CloudWatch Dashboard for EKS monitoring
resource "aws_cloudwatch_dashboard" "eks_dashboard" {
  dashboard_name = "g3-eks-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EKS", "node_cpu_utilization", { stat = "Average" }],
            [".", "pod_cpu_utilization", { stat = "Average" }],
            [".", "node_memory_utilization", { stat = "Average" }],
            [".", "pod_memory_utilization", { stat = "Average" }],
            [".", "cluster_node_count", { stat = "Average" }]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "EKS Cluster Metrics"
        }
      },
      {
        type = "log"
        properties = {
          query   = "fields @timestamp, @message | stats count() by bin(5m)"
          region  = "us-east-1"
          title   = "Application Logs"
          logs_group_name = aws_cloudwatch_log_group.eks_applications.name
        }
      }
    ]
  })
}

# CloudWatch Alarms for EKS

# Alert on high CPU utilization
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "eks-high-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "pod_cpu_utilization"
  namespace           = "AWS/EKS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when EKS pod CPU utilization is high"
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "eks-high-cpu"
    Environment = "prod"
  }
}

# Alert on high memory utilization
resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "eks-high-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "pod_memory_utilization"
  namespace           = "AWS/EKS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Alert when EKS pod memory utilization is high"
  treat_missing_data  = "notBreaching"

  tags = {
    Name        = "eks-high-memory"
    Environment = "prod"
  }
}

# Outputs
output "cloudwatch_log_groups" {
  description = "CloudWatch Log Groups for EKS"
  value = {
    applications = aws_cloudwatch_log_group.eks_applications.name
    cluster      = aws_cloudwatch_log_group.eks_cluster.name
  }
}

output "cloudwatch_dashboard_url" {
  description = "URL to CloudWatch Dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=${aws_cloudwatch_dashboard.eks_dashboard.dashboard_name}"
}

output "cloudwatch_agent_role_arn" {
  description = "ARN of CloudWatch Agent IAM role"
  value       = aws_iam_role.cloudwatch_agent.arn
}
