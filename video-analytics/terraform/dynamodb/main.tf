resource "aws_dynamodb_table" "metadata" {
  name           = var.table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "video_id"

  attribute {
    name = "video_id"
    type = "S"
  }

  server_side_encryption {
    enabled = true
  }
}

variable "table_name" {}

output "table_arn" {
  value = aws_dynamodb_table.metadata.arn
}

