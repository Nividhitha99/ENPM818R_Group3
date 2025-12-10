# Video Analytics Platform

Cloud-native video analytics platform for uploading, processing, and analyzing videos. Built with microservices architecture on AWS EKS.

## Summary

Microservices platform that enables video uploads, asynchronous processing (transcoding, thumbnails), and real-time analytics dashboards. Deployed on Kubernetes with auto-scaling, IRSA security, and comprehensive monitoring.

## Microservices

- **Frontend** - React 18 + Tailwind CSS + Nginx
- **Gateway** - FastAPI API gateway with request routing
- **Uploader** - FastAPI service for S3 uploads and SQS queuing
- **Processor** - FastAPI + FFmpeg for video transcoding
- **Analytics** - FastAPI service for metadata and statistics (uses RDS PostgreSQL)


## Tech Stack Installation

### Prerequisites
```bash
# Terraform
terraform --version  # >= 1.3

# AWS CLI
aws --version
aws configure

# kubectl
kubectl version --client

# Helm
helm version

# Docker (for local dev)
docker --version
docker-compose --version
```

### Local Development
```bash
# Frontend
cd video-analytics/frontend
npm install
npm start

# Backend (Python services)
cd video-analytics/backend/<service>
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

# Docker Compose (all services)
cd video-analytics
docker-compose up --build
```

## AWS Resources

- **EKS** - Kubernetes cluster (g3-eks-cluster, v1.33)
- **VPC** - 10.0.0.0/16 with public/private subnets (3 AZs)
- **EC2** - Managed node groups (t3.medium/large, auto-scaling 3-5 nodes)
- **S3** - video-analytics-uploads bucket (SSE-S3 encryption)
- **SQS** - video-processing-jobs queue
- **RDS** - PostgreSQL database for analytics data storage
- **EBS** - Persistent volumes for PVC mounting (gp3, encrypted)
- **ECR** - Container registry
- **ALB** - Application Load Balancer (via AWS Load Balancer Controller)
- **CloudWatch** - Logs, metrics, alarms
- **IAM/IRSA** - Service account roles for secure AWS access
- **NAT Gateway** - One per AZ (3 total)
- **ACM** - SSL/TLS certificates

## Terraform Setup

```bash
cd IaC

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy infrastructure
terraform apply

# Configure kubectl
aws eks update-kubeconfig --name g3-eks-cluster --region us-east-1
```

**Terraform Backend**: S3 bucket `grp-3-terraform-state-bucket` with DynamoDB locking

## Deployment

### 1. Infrastructure (Terraform)
```bash
cd IaC
terraform init && terraform apply
```

### 2. Configure kubectl
```bash
aws eks update-kubeconfig --name g3-eks-cluster --region us-east-1
```

### 3. Deploy Storage (EBS StorageClass and PVC)
```bash
# Deploy EBS StorageClass and PersistentVolumeClaim
kubectl apply -f video-analytics/k8s/storage/

# Verify PVC
kubectl get pvc -n prod
```

### 4. Deploy Applications
```bash
# Deploy all services
kubectl apply -f video-analytics/k8s/prod/

# Verify
kubectl get pods -n prod
kubectl get ingress -n prod
```

### 5. Access Application
```bash
# Get ALB URL
kubectl get ingress -n prod -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}'
```

## Quick Commands

```bash
# Check cluster status
kubectl get nodes
kubectl get pods -n prod

# View logs
kubectl logs -n prod <pod-name>

# Port forward (local access)
kubectl port-forward -n prod svc/frontend 3000:8080
```

## Documentation

- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md) - Detailed architecture
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [EXECUTIVE_SUMMARY.md](./EXECUTIVE_SUMMARY.md) - Project overview
