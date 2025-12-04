# output "eks_client_public_ip" {
#   description = "Public IP of the EC2 instance used for both EKS management and Docker app."
#   value       = aws_instance.eks_client.public_ip
# }

# output "eks_cluster_name" {
#   description = "EKS Cluster Name"
#   value       = module.eks.cluster_name
# }

# output "eks_cluster_endpoint" {
#   description = "EKS Cluster Endpoint"
#   value       = module.eks.cluster_endpoint
# }

# output "eks_cluster_certificate_authority_data" {
#   description = "EKS Cluster Certificate Authority Data"
#   value       = module.eks.cluster_certificate_authority_data
# }

# output "docker_app_url" {
#   description = "URL to access the Docker-based application (adjust port if needed)"
#   value       = "http://${aws_instance.eks_client.public_ip}:8080"
# }

output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}
output "private_subnets" {
  description = "List of private subnets"
  value       = module.vpc.private_subnets
}
output "public_subnets" {
  description = "List of public subnets"
  value       = module.vpc.public_subnets
}

output "eks_cluster_endpoint" {
  description = "EKS Cluster Endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_id" {
  description = "EKS Cluster Endpoint"
  value       = module.eks.cluster_id
}

# output "kubeconfig" {
#   value = module.eks.kubeconfig
#   sensitive = true
# }
