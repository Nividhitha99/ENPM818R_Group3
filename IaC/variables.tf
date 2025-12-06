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

  default = {
  group3_project_user = {
    arn    = "arn:aws:iam::385046010615:user/group3-project-user"
    policy = "ADMIN"
  }
  group3_member2 = {
    arn    = "arn:aws:iam::385046010615:user/group3-member2"
    policy = "ADMIN"
  }
  group3_member3 = {
    arn    = "arn:aws:iam::385046010615:user/group3-member3"
    policy = "ADMIN"
  }
  group3_member4 = {
    arn    = "arn:aws:iam::385046010615:user/group3-member4"
    policy = "ADMIN"
  }
  group3_member5 = {
    arn    = "arn:aws:iam::385046010615:user/group3-member5"
    policy = "ADMIN"
  }
  group3_member6 = {
    arn    = "arn:aws:iam::385046010615:user/group3-member6"
    policy = "ADMIN"
  }
  group3_member7 = {
    arn    = "arn:aws:iam::385046010615:user/group3-member7"
    policy = "ADMIN"
  }
}

}