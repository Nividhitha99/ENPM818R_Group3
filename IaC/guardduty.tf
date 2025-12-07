# Amazon GuardDuty Configuration
# GuardDuty provides threat detection and continuous monitoring

# Enable GuardDuty for the current region
resource "aws_guardduty_detector" "main" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }

  tags = {
    Name    = "g3-guardduty-detector"
    Project = "ENPM818R_Group3"
  }
}

# GuardDuty S3 Protection
resource "aws_guardduty_malware_protection_plan" "main" {
  name = "g3-malware-protection"

  protected_resource {
    s3_bucket {
      bucket_name = "video-analytics-uploads" # Replace with your actual bucket name
    }
  }

  actions {
    tag {
      key   = "malware-scan-status"
      value  = "scanned"
    }
  }

  tags = {
    Project = "ENPM818R_Group3"
  }

  depends_on = [aws_guardduty_detector.main]
}

# CloudWatch Event Rule for GuardDuty findings
resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "guardduty-findings-${module.eks.cluster_name}"
  description = "Capture GuardDuty findings"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
  })

  tags = {
    Project = "ENPM818R_Group3"
  }
}

# SNS Topic for GuardDuty alerts
resource "aws_sns_topic" "guardduty_alerts" {
  name              = "guardduty-alerts-${module.eks.cluster_name}"
  kms_master_key_id = "alias/aws/sns" # Use your KMS key if you have one

  tags = {
    Project = "ENPM818R_Group3"
  }
}

# Subscribe CloudWatch Event Rule to SNS Topic
resource "aws_cloudwatch_event_target" "guardduty_to_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "SendToSNS"
  arn       = aws_sns_topic.guardduty_alerts.arn
}

# Outputs
output "guardduty_detector_id" {
  description = "GuardDuty detector ID"
  value       = aws_guardduty_detector.main.id
}

output "guardduty_sns_topic_arn" {
  description = "SNS topic ARN for GuardDuty alerts"
  value       = aws_sns_topic.guardduty_alerts.arn
}

