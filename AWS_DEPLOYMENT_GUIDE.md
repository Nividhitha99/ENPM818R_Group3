# AWS Deployment & Testing Guide

This guide walks you through deploying the Processor & Analytics services from local development to a live AWS EKS cluster with full testing.

## Table of Contents

1. [Quick Start Summary](#quick-start-summary)
2. [AWS Prerequisites](#aws-prerequisites)
3. [Step 1: Build & Push Docker Images](#step-1-build--push-docker-images)
4. [Step 2: Deploy Infrastructure with Terraform](#step-2-deploy-infrastructure-with-terraform)
5. [Step 3: Deploy Services with Helm](#step-3-deploy-services-with-helm)
6. [Step 4: Configure AWS Credentials in Cluster](#step-4-configure-aws-credentials-in-cluster)
7. [Step 5: Testing & Validation](#step-5-testing--validation)
8. [Monitoring & Logging](#monitoring--logging)
9. [Troubleshooting](#troubleshooting)
10. [Cleanup](#cleanup)

---

## Quick Start Summary

```bash
# 1. Build and push images to ECR
docker-compose build processor analytics
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag video-analytics-processor:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/video-analytics:processor-latest
docker tag video-analytics-analytics:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/video-analytics:analytics-latest
docker push "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/video-analytics:processor-latest"
docker push "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/video-analytics:analytics-latest"

# 2. Deploy infrastructure with Terraform
cd IaC
terraform init
terraform plan
terraform apply

# 3. Connect to cluster
aws eks update-kubeconfig --region us-east-1 --name g3-eks-cluster
kubectl create namespace video-analytics

# 4. Create IAM roles for pod-level access
# (See Step 4 section below)

# 5. Deploy with Helm
helm install processor ./helm/processor -n video-analytics
helm install analytics ./helm/analytics -n video-analytics

# 6. Test services
kubectl port-forward svc/analytics 8002:8000 -n video-analytics
curl http://localhost:8002/videos
```

---

## AWS Prerequisites

### 1. AWS Account & CLI Setup

```bash
# Check AWS CLI version (must be 2.x or later)
aws --version

# Configure credentials
aws configure
# Provide:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Default output format: json

# Verify authentication
aws sts get-caller-identity
# Output should show your account ID
```

### 2. Required Tools

```bash
# Kubernetes CLI
kubectl version --client

# Helm 3
helm version

# Docker
docker --version

# Terraform (for infrastructure)
terraform --version

# jq (for JSON parsing - optional but helpful)
jq --version
```

### 3. Environment Variables

```bash
# Set these for easy copy-paste of commands
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO=video-analytics
export EKS_CLUSTER=g3-eks-cluster
export NAMESPACE=video-analytics

# Verify
echo "Account ID: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
```

### 4. IAM Permissions Required

Your AWS user needs these permissions:
- EKS: Create/manage clusters, node groups
- EC2: Create/manage VPCs, security groups, instances
- IAM: Create roles, policies, IRSA setup
- ECR: Create repositories, push images
- S3: Read/write video buckets
- SQS: Create queues for processor
- CloudFormation: Deploy stacks (via Terraform)

---

## Step 1: Build & Push Docker Images

### 1.1 Build Docker Images

```bash
cd video-analytics

# Build individual images
docker-compose build processor analytics

# OR build all services
docker-compose build

# Verify build
docker images | grep video-analytics
```

### 1.2 Create ECR Repository

```bash
# Create repository (one-time)
aws ecr create-repository \
  --repository-name $ECR_REPO \
  --region $AWS_REGION

# Output includes repository URI
# Example: 385046010615.dkr.ecr.us-east-1.amazonaws.com/video-analytics
```

### 1.3 Push Images to ECR

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag images
docker tag video-analytics-processor:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:processor-latest

docker tag video-analytics-analytics:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:analytics-latest

# Push to ECR
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:processor-latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:analytics-latest"

# Verify push
aws ecr describe-images \
  --repository-name $ECR_REPO \
  --region $AWS_REGION \
  --query 'imageDetails[*].{Tag:imageTags,Pushed:imagePushedAt}' \
  --output table
```

**Expected output:**
```
|              Tag              |           Pushed           |
|-------------------------------|-----------------------------|
| processor-latest              | 2025-12-04 15:35:21.123000 |
| analytics-latest              | 2025-12-04 15:35:42.456000 |
```

---

## Step 2: Deploy Infrastructure with Terraform

### 2.1 Initialize Terraform

```bash
cd IaC

# Initialize Terraform (downloads modules)
terraform init

# Verify state (should be empty)
terraform state list
```

### 2.2 Review Infrastructure Plan

```bash
# See what will be created
terraform plan

# Key resources:
# - VPC (10.0.0.0/16, 3 AZs)
# - EKS Cluster (v1.33, 2 node groups, t3.medium-t3.large instances)
# - Security groups, IAM roles, subnets
# - Cost estimate shown at end
```

### 2.3 Deploy Infrastructure

```bash
# Create AWS resources
terraform apply

# Review and type "yes" when prompted
# Deployment takes 10-20 minutes

# Outputs will show:
# - EKS cluster endpoint
# - VPC ID
# - Subnets
```

### 2.4 Verify Cluster

```bash
# Get cluster status
aws eks describe-cluster \
  --name $EKS_CLUSTER \
  --region $AWS_REGION \
  --query 'cluster.{Name:name,Status:status,Endpoint:endpoint}' \
  --output table

# Expected Status: ACTIVE
```

---

## Step 3: Deploy Services with Helm

### 3.1 Connect kubectl to Cluster

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region $AWS_REGION \
  --name $EKS_CLUSTER

# Verify connection
kubectl cluster-info
kubectl get nodes

# Expected: 4 nodes (2 node groups × 2 nodes)
```

### 3.2 Create Namespace & ConfigMap

```bash
# Create namespace
kubectl create namespace $NAMESPACE

# Verify
kubectl get namespaces
```

### 3.3 Create S3 Buckets (if not existing)

```bash
# Videos bucket
aws s3 mb s3://video-analytics-uploads-$(date +%s) \
  --region $AWS_REGION

# Metadata bucket (optional, can use same bucket)
aws s3 mb s3://video-analytics-metadata-$(date +%s) \
  --region $AWS_REGION

# Note bucket names for Step 4
export VIDEOS_BUCKET=video-analytics-uploads-XXXX
export METADATA_BUCKET=video-analytics-metadata-XXXX
```

### 3.4 Deploy Processor Service

```bash
# Update Helm values with your ECR image URI
# Edit: helm/processor/values.yaml
# Change: image.repository = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO"
# Change: image.tag = "processor-latest"

# Deploy
helm install processor \
  ./video-analytics/helm/processor \
  --namespace $NAMESPACE \
  --set image.repository=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO \
  --set image.tag=processor-latest \
  --set env.AWS_REGION=$AWS_REGION \
  --set env.SQS_QUEUE_URL="https://sqs.$AWS_REGION.amazonaws.com/$AWS_ACCOUNT_ID/video-processing-queue"

# Verify deployment
kubectl get deployments -n $NAMESPACE
kubectl get pods -n $NAMESPACE
```

### 3.5 Deploy Analytics Service

```bash
# Deploy
helm install analytics \
  ./video-analytics/helm/analytics \
  --namespace $NAMESPACE \
  --set image.repository=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO \
  --set image.tag=analytics-latest \
  --set env.AWS_REGION=$AWS_REGION \
  --set env.S3_BUCKET=$VIDEOS_BUCKET

# Verify deployment
kubectl get deployments -n $NAMESPACE
kubectl get svc -n $NAMESPACE
```

### 3.6 Verify Helm Releases

```bash
# List deployed releases
helm list -n $NAMESPACE

# Check release status
helm status processor -n $NAMESPACE
helm status analytics -n $NAMESPACE
```

---

## Step 4: Configure AWS Credentials in Cluster

### 4.1 Enable IRSA (IAM Roles for Service Accounts)

```bash
# Get OIDC provider ID
OIDC_ID=$(aws eks describe-cluster \
  --name $EKS_CLUSTER \
  --region $AWS_REGION \
  --query 'cluster.identity.oidc.issuer' \
  --output text | cut -d '/' -f 5)

echo "OIDC ID: $OIDC_ID"
```

### 4.2 Create Processor IAM Role

```bash
# Create trust policy
cat > /tmp/processor-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/oidc.eks.$AWS_REGION.amazonaws.com/id/$OIDC_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.$AWS_REGION.amazonaws.com/id/$OIDC_ID:sub": "system:serviceaccount:$NAMESPACE:processor-sa"
        }
      }
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name processor-eks-role \
  --assume-role-policy-document file:///tmp/processor-trust-policy.json

# Attach permissions policy (from iam/processor-iam-policy.json)
aws iam put-role-policy \
  --role-name processor-eks-role \
  --policy-name processor-policy \
  --policy-document file://iam/processor-iam-policy.json
```

### 4.3 Create Analytics IAM Role

```bash
# Create trust policy
cat > /tmp/analytics-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::$AWS_ACCOUNT_ID:oidc-provider/oidc.eks.$AWS_REGION.amazonaws.com/id/$OIDC_ID"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.$AWS_REGION.amazonaws.com/id/$OIDC_ID:sub": "system:serviceaccount:$NAMESPACE:analytics-sa"
        }
      }
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name analytics-eks-role \
  --assume-role-policy-document file:///tmp/analytics-trust-policy.json

# Attach permissions policy
aws iam put-role-policy \
  --role-name analytics-eks-role \
  --policy-name analytics-policy \
  --policy-document file://iam/analytics-iam-policy.json
```

### 4.4 Create Kubernetes Service Accounts

```bash
# Processor service account with IAM role annotation
kubectl create serviceaccount processor-sa -n $NAMESPACE
kubectl annotate serviceaccount processor-sa -n $NAMESPACE \
  eks.amazonaws.com/role-arn=arn:aws:iam::$AWS_ACCOUNT_ID:role/processor-eks-role

# Analytics service account
kubectl create serviceaccount analytics-sa -n $NAMESPACE
kubectl annotate serviceaccount analytics-sa -n $NAMESPACE \
  eks.amazonaws.com/role-arn=arn:aws:iam::$AWS_ACCOUNT_ID:role/analytics-eks-role

# Verify
kubectl get serviceaccounts -n $NAMESPACE
```

### 4.5 Update Helm Deployments with Service Accounts

```bash
# Upgrade processor with service account
helm upgrade processor \
  ./video-analytics/helm/processor \
  --namespace $NAMESPACE \
  --set serviceAccount.name=processor-sa

# Upgrade analytics with service account
helm upgrade analytics \
  ./video-analytics/helm/analytics \
  --namespace $NAMESPACE \
  --set serviceAccount.name=analytics-sa

# Verify pods restarted with new service account
kubectl get pods -n $NAMESPACE
kubectl describe pod -l app=processor -n $NAMESPACE | grep -A 2 "Service Account"
```

---

## Step 5: Testing & Validation

### 5.1 Verify Pods are Running

```bash
# Check pod status
kubectl get pods -n $NAMESPACE

# Expected output:
# NAME                           READY   STATUS    RESTARTS   AGE
# processor-74f44bff4f-xxx       1/1     Running   0          2m
# analytics-5c5d58d7fc-yyy       1/1     Running   0          2m

# Check pod logs
kubectl logs -f deployment/analytics -n $NAMESPACE
kubectl logs -f deployment/processor -n $NAMESPACE
```

### 5.2 Port Forward Services

```bash
# Analytics service (terminal 1)
kubectl port-forward svc/analytics 8002:8000 -n $NAMESPACE

# Processor service (terminal 2)
kubectl port-forward svc/processor 8001:8000 -n $NAMESPACE
```

### 5.3 Test Analytics Endpoints

```bash
# Health check
curl http://localhost:8002/health

# Expected: aws_available should be true now
# {
#   "status": "healthy",
#   "service": "analytics",
#   "aws_available": true
# }

# Get videos
curl http://localhost:8002/videos

# Get specific video
curl http://localhost:8002/video/video-001

# Get stats
curl http://localhost:8002/stats

# Record view
curl -X POST http://localhost:8002/view/video-001

# Record like
curl -X POST http://localhost:8002/like/video-001
```

### 5.4 Test Processor Service

```bash
# Health check
curl http://localhost:8001/health

# Expected: aws_available should be true
# {
#   "status": "healthy",
#   "service": "processor",
#   "aws_available": true
# }

# Metrics
curl http://localhost:8001/metrics | grep processor_jobs
```

### 5.5 End-to-End Testing

```bash
# 1. Upload video to SQS queue
aws sqs send-message \
  --queue-url https://sqs.$AWS_REGION.amazonaws.com/$AWS_ACCOUNT_ID/video-processing-queue \
  --message-body '{
    "video_id": "test-video-001",
    "s3_key": "videos/test-video.mp4",
    "timestamps": [0, 30, 60]
  }'

# 2. Monitor processor logs
kubectl logs -f deployment/processor -n $NAMESPACE

# 3. Verify S3 upload
aws s3 ls s3://$VIDEOS_BUCKET/metadata/

# 4. Query analytics for new video
curl http://localhost:8002/video/test-video-001
```

---

## Monitoring & Logging

### 6.1 CloudWatch Integration

```bash
# Check logs in CloudWatch
aws logs describe-log-groups \
  --query 'logGroups[?contains(logGroupName, `eks`) || contains(logGroupName, `video-analytics`)]' \
  --region $AWS_REGION

# View logs
aws logs tail /eks/video-analytics --follow --region $AWS_REGION
```

### 6.2 Prometheus Metrics

```bash
# Port forward Prometheus (if deployed)
kubectl port-forward svc/prometheus 9090:9090 -n $NAMESPACE

# Access metrics dashboard
# http://localhost:9090

# Query metrics
curl http://localhost:8002/metrics | grep processor_jobs_total
curl http://localhost:8001/metrics | grep videos_retrieved_total
```

### 6.3 Pod Resource Usage

```bash
# Check resource utilization
kubectl top nodes
kubectl top pods -n $NAMESPACE

# Check pod events
kubectl describe pod -l app=analytics -n $NAMESPACE
```

---

## Troubleshooting

### Problem: Pod stuck in "Pending"

```bash
# Describe pod to see events
kubectl describe pod <pod-name> -n $NAMESPACE

# Check node capacity
kubectl top nodes
kubectl describe nodes

# Possible causes:
# - Insufficient resources: Scale up node group
# - Image pull errors: Check ECR permissions, image URI
# - PVC issues: Check persistent volumes
```

### Problem: AWS credentials not working

```bash
# Check service account annotations
kubectl get sa processor-sa -n $NAMESPACE -o yaml | grep role-arn

# Check IAM role
aws iam get-role --role-name processor-eks-role

# Check policy attachment
aws iam list-role-policies --role-name processor-eks-role

# Test assume role manually
aws sts assume-role-with-web-identity \
  --role-arn arn:aws:iam::$AWS_ACCOUNT_ID:role/processor-eks-role \
  --role-session-name test-session \
  --web-identity-token $(kubectl create token processor-sa -n $NAMESPACE)
```

### Problem: Services returning "aws_available": false

```bash
# Check pod logs for credential errors
kubectl logs deployment/analytics -n $NAMESPACE | grep AWS

# Verify environment variables
kubectl set env pod/<pod-name> -n $NAMESPACE --list

# Check AWS_REGION is set correctly
kubectl describe deployment analytics -n $NAMESPACE | grep -A 5 "Environment"
```

### Problem: Connection refused when port-forwarding

```bash
# Verify service exists
kubectl get svc -n $NAMESPACE

# Check service endpoints
kubectl get endpoints -n $NAMESPACE

# Verify pod is ready
kubectl get pods -n $NAMESPACE -o wide

# Kill and restart port-forward
# Ctrl+C to stop
# Then re-run port-forward command
```

### Problem: Slow or timeout errors

```bash
# Check pod logs
kubectl logs deployment/processor -n $NAMESPACE

# Monitor resource usage
kubectl top pod -n $NAMESPACE

# Check network policies
kubectl get networkpolicies -n $NAMESPACE

# Increase timeout in Helm values
helm upgrade analytics \
  ./video-analytics/helm/analytics \
  --namespace $NAMESPACE \
  --set service.timeout=60
```

---

## Cleanup

### Remove Services from Cluster

```bash
# Delete Helm releases
helm uninstall processor -n $NAMESPACE
helm uninstall analytics -n $NAMESPACE

# Delete namespace
kubectl delete namespace $NAMESPACE

# Verify deletion
kubectl get namespaces
```

### Destroy AWS Infrastructure

```bash
cd IaC

# Preview what will be deleted
terraform plan -destroy

# Delete all AWS resources (10+ minutes)
terraform destroy

# Type "yes" when prompted
```

### Clean Up IAM Roles

```bash
# Delete IAM roles (if not using Terraform)
aws iam delete-role-policy --role-name processor-eks-role --policy-name processor-policy
aws iam delete-role-policy --role-name analytics-eks-role --policy-name analytics-policy

aws iam delete-role --role-name processor-eks-role
aws iam delete-role --role-name analytics-eks-role
```

### Delete ECR Images

```bash
# Delete repository (careful: will delete all images)
aws ecr delete-repository \
  --repository-name $ECR_REPO \
  --force \
  --region $AWS_REGION
```

---

## Next Steps After Deployment

1. **Configure DNS:** Use Route 53 for ingress endpoints
2. **Set up auto-scaling:** Configure HPA based on metrics
3. **Enable logging:** CloudWatch, ELK, or Datadog integration
4. **Implement CI/CD:** GitHub Actions to auto-deploy on code push
5. **Add monitoring:** Prometheus + Grafana for real-time metrics
6. **Security hardening:** Pod security policies, network policies, secrets management
7. **Backup strategy:** Automated EBS snapshots for data persistence

---

## Support & References

- **Local Testing:** See `LOCAL_TESTING.md`
- **Architecture:** See `MEMBER4-ARCHITECTURE.md`
- **API Documentation:** See `api-reference.md`
- **Helm Charts:** See `helm/processor/` and `helm/analytics/`
- **Infrastructure Code:** See `IaC/` directory

For additional details on specific components, refer to the referenced documentation files.
