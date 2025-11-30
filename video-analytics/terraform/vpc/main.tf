########################################
# VARIABLES (removed duplicates)
########################################

variable "vpc_name" {}
variable "project" {}
variable "cluster_name" {}
variable "vpc_cidr" {}
variable "availability_zones" {
  type = list(string)
}
variable "private_subnet_cidrs" {
  type = list(string)
}
variable "public_subnet_cidrs" {
  type = list(string)
}

########################################
# VPC
########################################

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name                                           = var.vpc_name
    Project                                        = var.project
    "kubernetes.io/cluster/${var.cluster_name}"    = "shared"
  }
}

########################################
# PUBLIC SUBNETS
########################################

resource "aws_subnet" "public" {
  count = length(var.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true  # Important for ALB & EKS nodegroups

  tags = {
    Name                                      = "${var.vpc_name}-public-${count.index}"
    "kubernetes.io/role/elb"                  = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    Project                                   = var.project
  }

  # Prevent accidental recreation
  lifecycle {
    ignore_changes = [
      cidr_block,
      map_public_ip_on_launch,
      tags,
    ]
  }
}

########################################
# PRIVATE SUBNETS
########################################

resource "aws_subnet" "private" {
  count = length(var.private_subnet_cidrs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = var.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name                                      = "${var.vpc_name}-private-${count.index}"
    "kubernetes.io/role/internal-elb"         = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
    Project                                   = var.project
  }

  lifecycle {
    ignore_changes = [
      cidr_block,
      tags,
    ]
  }
}

########################################
# INTERNET GATEWAY
########################################

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name    = "${var.vpc_name}-igw"
    Project = var.project
  }
}

########################################
# PUBLIC ROUTE TABLE
########################################

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name    = "${var.vpc_name}-public-rt"
    Project = var.project
  }
}

resource "aws_route" "public_route" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public_assoc" {
  count          = length(aws_subnet.public)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

########################################
# OUTPUTS (REMOVED FROM HERE)
########################################
# (outputs remain in outputs.tf)
