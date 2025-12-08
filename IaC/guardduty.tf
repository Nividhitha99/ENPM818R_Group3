# Amazon GuardDuty Configuration
# GuardDuty provides threat detection and continuous monitoring

# Enable GuardDuty for the current region
# resource "aws_guardduty_detector" "main" {
#   enable                       = true
#   finding_publishing_frequency = "FIFTEEN_MINUTES"
#   tags = {
#     Name    = "g3-guardduty-detector"
#     Project = "ENPM818R_Group3"
#   }
# }


# resource "aws_guardduty_detector_feature" "s3_protection" {
#   detector_id = aws_guardduty_detector.main.id
#   name        = "S3_DATA_EVENTS"
#   status      = "ENABLED"
# }

# resource "aws_guardduty_detector_feature" "eks_protection" {
#   detector_id = aws_guardduty_detector.main.id
#   name        = "EKS_AUDIT_LOGS"
#   status      = "ENABLED"
# }

# resource "aws_guardduty_detector_feature" "malware_protection" {
#   detector_id = aws_guardduty_detector.main.id
#   name        = "EBS_MALWARE_PROTECTION"
#   status      = "ENABLED"
# }

# resource "aws_iam_role" "guardduty_s3_malware_role" {
#   name = "guardduty-s3-malware-role"

#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Sid    = "AllowGuardDutyAssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "guardduty.amazonaws.com"
#         }
#         Action = "sts:AssumeRole"
#       }
#     ]
#   })

#   tags = {
#     Name    = "guardduty-s3-malware-role"
#     Project = "ENPM818R_Group3"
#   }
# }

# # Attach the custom policy to the existing role you created earlier.
# # If your role resource is named differently, change the role reference accordingly.
# resource "aws_iam_role_policy_attachment" "guardduty_malware_attach" {
#   role       = aws_iam_role.guardduty_s3_malware_role.name
#   policy_arn = aws_iam_policy.guardduty_malware_protection_policy.arn
# }



# # GuardDuty S3 Protection
# resource "aws_guardduty_malware_protection_plan" "main" {
#   # name = "g3-malware-protection"
#   role = aws_iam_role.guardduty_s3_malware_role.arn

#   protected_resource {
#     s3_bucket {
#       bucket_name     = "video-analytics-uploads"
#     }
#   }

#   actions {
#     tagging {
#       status = "ENABLED"
#     }
#   }

#   tags = {
#     Project = "ENPM818R_Group3"
#   }

#   depends_on = [aws_guardduty_detector.main]
# }


# CloudWatch Event Rule for GuardDuty findings
# resource "aws_cloudwatch_event_rule" "guardduty_findings" {
#   name        = "guardduty-findings-${module.eks.cluster_name}"
#   description = "Capture GuardDuty findings"

#   event_pattern = jsonencode({
#     source      = ["aws.guardduty"]
#     detail-type = ["GuardDuty Finding"]
#   })

#   tags = {
#     Project = "ENPM818R_Group3"
#   }
# }

# # SNS Topic for GuardDuty alerts
# resource "aws_sns_topic" "guardduty_alerts" {
#   name              = "guardduty-alerts-${module.eks.cluster_name}"
#   kms_master_key_id = "alias/aws/sns" # Use your KMS key if you have one

#   tags = {
#     Project = "ENPM818R_Group3"
#   }
# }

# # Subscribe CloudWatch Event Rule to SNS Topic
# resource "aws_cloudwatch_event_target" "guardduty_to_sns" {
#   rule      = aws_cloudwatch_event_rule.guardduty_findings.name
#   target_id = "SendToSNS"
#   arn       = aws_sns_topic.guardduty_alerts.arn
# }


# output "guardduty_sns_topic_arn" {
#   description = "SNS topic ARN for GuardDuty alerts"
#   value       = aws_sns_topic.guardduty_alerts.arn
# }



# NOTE:
# GuardDuty S3 malware protection requires an IAM role per AWS API.
# Terraform AWS provider does not fully support malware_protection_plan for S3.
# Feature enabled via AWS Console using role guardduty-s3-malware-role.
