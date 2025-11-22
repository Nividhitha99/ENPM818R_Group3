resource "aws_s3_bucket" "uploads" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_ownership_controls" "uploads" {
  bucket = aws_s3_bucket.uploads.id
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

resource "aws_s3_bucket_acl" "uploads" {
  depends_on = [aws_s3_bucket_ownership_controls.uploads]
  bucket = aws_s3_bucket.uploads.id
  acl    = "private"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

variable "bucket_name" {}

output "bucket_arn" {
  value = aws_s3_bucket.uploads.arn
}
output "bucket_id" {
  value = aws_s3_bucket.uploads.id
}

