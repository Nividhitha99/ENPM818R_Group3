# CloudWatch Monitoring Configuration for EKS
# Creates log groups, alarms, and dashboards for cluster observability

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "eks_applications" {
  name              = "/aws/eks/${module.eks.cluster_name}/applications"
  retention_in_days = 30

  tags = {
    Name    = "EKS Application Logs"
    Project = "ENPM818R_Group3"
  }
}

resource "aws_cloudwatch_log_group" "eks_cluster" {
  name              = "/aws/eks/${module.eks.cluster_name}/cluster"
  retention_in_days = 90

  tags = {
    Name    = "EKS Cluster Logs"
    Project = "ENPM818R_Group3"
  }
}

# CloudWatch Alarms for CPU Utilization
resource "aws_cloudwatch_metric_alarm" "eks_high_cpu" {
  alarm_name          = "eks-high-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when EKS cluster CPU exceeds 80%"
  alarm_actions       = []

  tags = {
    Project = "ENPM818R_Group3"
  }
}

# CloudWatch Alarms for Memory Utilization
resource "aws_cloudwatch_metric_alarm" "eks_high_memory" {
  alarm_name          = "eks-high-memory-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Alert when EKS cluster memory exceeds 85%"
  alarm_actions       = []

  tags = {
    Project = "ENPM818R_Group3"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "eks_cluster" {
  dashboard_name = "eks-${module.eks.cluster_name}-overview"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EKS", "CPUUtilization", { stat = "Average" }],
            [".", "MemoryUtilization", { stat = "Average" }],
            [".", "NetworkIn", { stat = "Sum" }],
            [".", "NetworkOut", { stat = "Sum" }]
          ]
          period = 300
          stat   = "Average"
          region = data.aws_region.current.id
          title  = "EKS Cluster Metrics"
        }
      },
      {
        type = "log"
        properties = {
          query   = "fields @timestamp, @message | stats count() by bin(5m)"
          region = data.aws_region.current.id
          title   = "Application Log Volume"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", { stat = "Average" }],
            [".", "RequestCount", { stat = "Sum" }],
            [".", "HTTPCode_Target_2XX_Count", { stat = "Sum" }],
            [".", "HTTPCode_Target_4XX_Count", { stat = "Sum" }]
          ]
          period = 60
          stat   = "Average"
          region = data.aws_region.current.id
          title  = "Application Load Balancer Metrics"
        }
      }
    ]
  })
}

# Outputs
output "cloudwatch_log_groups" {
  description = "CloudWatch log group names"
  value = {
    applications = aws_cloudwatch_log_group.eks_applications.name
    cluster      = aws_cloudwatch_log_group.eks_cluster.name
  }
}

output "cloudwatch_alarms" {
  description = "CloudWatch alarm names"
  value = {
    high_cpu    = aws_cloudwatch_metric_alarm.eks_high_cpu.alarm_name
    high_memory = aws_cloudwatch_metric_alarm.eks_high_memory.alarm_name
  }
}

output "cloudwatch_dashboard" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.eks_cluster.dashboard_name
}
