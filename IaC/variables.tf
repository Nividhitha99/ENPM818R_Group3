variable "region" {
  default = "us-east-1"
}

variable "ami_id" {
  default = "ami-0f00d706c4a80fd93" # Amazon Linux 2
  type = string
  description = "The AMI ID to use for the instance"
}

variable "eks_users" {
  type = map(object({
    arn    = string
    policy = string
  }))

  default = {}

}