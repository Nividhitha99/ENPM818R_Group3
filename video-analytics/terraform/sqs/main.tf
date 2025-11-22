resource "aws_sqs_queue" "jobs" {
  name                      = var.queue_name
  message_retention_seconds = 86400
  visibility_timeout_seconds = 60 # > processing time

  sqs_managed_sse_enabled = true
}

variable "queue_name" {}

output "queue_arn" {
  value = aws_sqs_queue.jobs.arn
}
output "queue_url" {
  value = aws_sqs_queue.jobs.id
}

