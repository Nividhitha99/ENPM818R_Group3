# Video Analytics Platform - EKS Deployment Documentation

## Overview

This document describes the complete deployment of the Video Analytics Platform on AWS EKS with enterprise-grade security, observability, and infrastructure-as-code practices.

## IRSA (IAM Roles for Service Accounts)

All microservices use IRSA for secure AWS API access without requiring long-lived credentials.

### Service Accounts
- auth-sa → auth-irsa-role
- analytics-sa → analytics-irsa-role
- gateway-sa → gateway-irsa-role
- processor-sa → processor-irsa-role
- uploader-sa → uploader-irsa-role (S3 access)
- frontend-sa → frontend-irsa-role

### Verification
kubectl exec -n prod <POD> -- env | grep AWS_ROLE_ARN

## CloudWatch Observability

### Log Groups
- /aws/eks/g3-eks-cluster/applications (30 days)
- /aws/eks/g3-eks-cluster/cluster (90 days)

### Alarms
- eks-high-cpu-utilization (threshold: 80%)
- eks-high-memory-utilization (threshold: 85%)

## Prometheus & Grafana

### Access
- **Prometheus (LoadBalancer)**: http://k8s-monitori-promethe-c70c64809c-3207c6ab19cbd45a.elb.us-east-1.amazonaws.com:9090 ✅ (Fully operational)
- **Prometheus (Internal)**: http://prometheus.monitoring.svc.cluster.local:9090 (within cluster only)
- **Prometheus (Port Forward)**: `kubectl port-forward -n monitoring svc/prometheus 9090:9090`
- **Grafana**: http://k8s-monitori-grafana-7448b91123-4076a7b0845bbf44.elb.us-east-1.amazonaws.com:3000 ✅ (Fully operational)
- **Credentials**: admin / admin123 (⚠️ Change in production!)

### Scraping
Prometheus scrapes:
1. Kubernetes API servers
2. Kubernetes nodes
3. Kubernetes pods (with prometheus annotation)
4. Video Analytics services on port 8000

## Deployment Commands

\\\ash
# Terraform
cd IaC
terraform init
terraform plan
terraform apply -auto-approve

# Kubernetes
kubectl apply -f video-analytics/k8s/prod/
kubectl apply -f video-analytics/k8s/monitoring/
\\\

## Status

✅ IRSA configured for all 6 microservices
✅ CloudWatch monitoring enabled
✅ Prometheus + Grafana fully deployed and accessible
✅ LoadBalancer targets healthy (8/8)
✅ 5/6 services running (uploader has app config issue)
✅ All infrastructure as code
