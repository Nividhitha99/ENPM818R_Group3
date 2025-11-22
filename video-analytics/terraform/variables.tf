variable "aws_region" {
  description = "AWS Region"
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  default     = "10.0.0.0/16"
}

variable "cluster_name" {
  description = "EKS Cluster Name"
  default     = "video-analytics-cluster"
}

variable "upload_bucket_name" {
  default = "video-analytics-uploads-prod-123" # Must be globally unique
}

variable "job_queue_name" {
  default = "video-processing-jobs"
}

variable "metadata_table_name" {
  default = "video-metadata"
}

