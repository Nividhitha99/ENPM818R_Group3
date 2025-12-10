# Security Configuration

## Overview
This document details the security implementation and recent remediations for the Video Analytics platform deployed on AWS EKS. All security measures follow AWS Well-Architected Framework Security Pillar principles.

---

## 1. Network Security

### Infrastructure
- **VPC**: Deployed in private subnets across 3 AZs (10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24). Public subnets (10.0.101.0/24, 10.0.102.0/24, 10.0.103.0/24) only for Load Balancers and NAT Gateways.
- **EKS API Endpoint**: Private access enabled, public access disabled to restrict cluster access to VPC.
- **Node SSH Access**: Disabled (`ec2_ssh_key = null`) to prevent unauthorized direct access to worker nodes.

### NetworkPolicies
Kubernetes NetworkPolicies enforce zero-trust networking:
- **Default-deny-all**: Blocks all ingress/egress traffic by default in `prod` namespace
- **Allow-internal-dns**: Permits DNS queries to kube-system (UDP 53)
- **Allow-alb-to-frontend**: Allows ALB Ingress Controller to reach frontend pods on ports 80/8080
- **Allow-alb-to-gateway**: Allows external traffic to API gateway on port 8000
- **Allow-frontend-to-backend**: Permits frontend → gateway communication
- **Allow-gateway-to-services**: Permits gateway → uploader/analytics/auth on port 8000
- **Allow-aws-egress-for-irsa-services**: Permits IRSA-enabled pods (uploader, processor, analytics, auth, gateway) to reach AWS APIs over HTTPS (port 443)
- **Allow-imds-egress-for-irsa-services**: Permits all services to reach AWS IMDS (169.254.169.254:80) for IAM credential retrieval

### TLS/Encryption in Transit
- **ALB Ingress**: Configured with TLS 1.3 policy (`ELBSecurityPolicy-TLS13-1-2-2021-06`)
- **ACM Certificate**: `arn:aws:acm:us-east-1:385046010615:certificate/ae4330a4-d1c0-4a72-a4dc-43ab0a7bfe57`
- **SSL Redirect**: All HTTP (port 80) traffic redirected to HTTPS (port 443)
- **Security Headers**: HTTP/2 enabled, idle timeout 60s, deletion protection enabled

---

## 2. Container Security

### Runtime Security
- **Non-root runtime**: All services run as non-root users:
  - Backend services: `appuser` (UID 1000)
  - Frontend: nginxinc/nginx-unprivileged (UID 101)
- **Read-only root filesystem**: Enabled on all pods except where tmpfs volumes are mounted
- **No privileged containers**: `privileged: false` enforced on all pods
- **Drop all capabilities**: `capabilities.drop: [ALL]` applied to all containers
- **Seccomp**: `RuntimeDefault` seccomp profile enforced

### Image Security
- **Multi-stage builds**: Separate builder and runtime stages for all services
- **Minimal base images**:
  - Python services: `python:3.11-slim` (Debian)
  - Frontend: `nginxinc/nginx-unprivileged:1.27-alpine` with explicit libxml2 upgrade
- **PYTHONDONTWRITEBYTECODE=1**: Prevents `.pyc` file generation
- **HEALTHCHECK directives**: All Dockerfiles include health checks

### Vulnerability Scanning & Image Signing
- **Trivy Scanning**: Integrated in CI/CD pipeline (`.github/workflows/build-and-push.yml`)
  - Filesystem scan before build
  - Image scan after build, fails on HIGH/CRITICAL vulnerabilities
  - Results uploaded to GitHub Security tab
- **ECR Scan-on-Push**: Enabled for all 6 ECR repositories (auth-service, gateway-service, uploader-service, processor-service, analytics-service, frontend)
- **Image Signing**: AWS Signer (Notation) integrated in CI/CD
  - Signer Profile: `EcrSignerProfile` (Notation-OCI-SHA384-ECDSA)
  - All images signed post-push with `notation verify` validation

### Recent Remediations (2025-12-10)
- **Frontend**: Updated Dockerfile to use `nginxinc/nginx-unprivileged:1.27-alpine` with `apk upgrade libxml2` to fix CVE-2025-49794, CVE-2025-49796 (CRITICAL) and CVE-2025-49795, CVE-2025-6021 (HIGH)
- **Backend Services**: All services already specify `urllib3>=2.6.0` in requirements.txt to address CVE-2025-66418, CVE-2025-66471 (HIGH)

---

## 3. IAM & Access Control

### IRSA (IAM Roles for Service Accounts)
Fine-grained IAM permissions via OIDC federation:
- **Auth Service** (`auth-irsa-role`):
  - Secrets Manager: GetSecretValue for `video-analytics/jwt-secret`
- **Analytics Service** (`analytics-irsa-role`):
  - S3: ListBucket, GetObject, PutObject on `video-analytics-uploads`
  - Secrets Manager: GetSecretValue for RDS credentials
- **Processor Service** (`processor-irsa-role`):
  - SQS: ReceiveMessage, DeleteMessage, GetQueueAttributes, ChangeMessageVisibility
  - S3: GetObject, PutObject, HeadObject, ListBucket on `video-analytics-uploads`
  - Secrets Manager: GetSecretValue
- **Uploader Service** (`uploader-irsa-role`):
  - S3: PutObject, GetObject, ListBucket on `video-analytics-uploads`
  - SQS: SendMessage
- **Gateway Service** (`gateway-irsa-role`):
  - S3: ListBucket, GetObject on `video-analytics-uploads`
- **CloudWatch Agent** (`cloudwatch-agent-irsa-role`):
  - Logs: CreateLogGroup, CreateLogStream, PutLogEvents, DescribeLogStreams

### Kubernetes RBAC
- **Cluster Admin**: Full cluster access for deployment management
- **CI/CD ReadOnly**: Limited read-only access for GitHub Actions
- **Namespace Isolation**: dev/staging/prod namespaces with separate resource quotas

---

## 4. Data Protection

### Encryption at Rest
- **S3 Buckets**: SSE-S3 (AES-256) encryption for `video-analytics-uploads`
- **RDS PostgreSQL**: Encryption at rest enabled with AWS-managed KMS keys
- **EBS Volumes**: All node volumes encrypted with KMS
- **EFS (if used)**: Encryption at rest with KMS

### Secrets Management
**Migration Completed (2025-12-10):**
- **Before**: JWT_SECRET stored in Kubernetes Secret (`config-secrets.yaml`) as plaintext Base64
- **After**: JWT_SECRET migrated to AWS Secrets Manager
  - Secret ARN: `arn:aws:secretsmanager:us-east-1:385046010615:secret:video-analytics/jwt-secret-XUwon6`
  - Auth service updated to fetch secret via boto3 using IRSA credentials
  - Environment variables:
    - `USE_SECRETS_MANAGER=true`
    - `JWT_SECRET_ARN=<arn>`
    - `AWS_REGION=us-east-1`
- **Benefits**: Automatic rotation support, centralized secret management, audit logging

---

## 5. Monitoring & Threat Detection

### GuardDuty
- **Status**: ENABLED (Detector ID: `18cd7dceac14e8b0db927e01eef18c0d`)
- **Features Enabled**:
  - CloudTrail monitoring
  - DNS logs analysis
  - VPC Flow Logs analysis
  - S3 Data Events
  - **EKS Audit Logs** (malicious API calls, credential access)
  - **EKS Runtime Monitoring** (ENABLED 2025-12-10): Process activity, file access, network connections
  - EBS Malware Protection

### EKS Control Plane Logging
All log types enabled:
- `api`: API server audit logs
- `audit`: Kubernetes audit events
- `authenticator`: IAM/OIDC authentication
- `controllerManager`: Controller lifecycle events
- `scheduler`: Pod scheduling decisions

**CloudWatch Log Groups**:
- `/aws/eks/g3-eks-cluster/cluster`: 90-day retention
- `/aws/eks/g3-eks-cluster/applications`: 30-day retention

### Observability
- **Prometheus**: Metrics collection with ServiceMonitor definitions
- **Grafana**: Dashboards for cluster/application metrics
- **CloudWatch Alarms**: CPU/memory thresholds, pod restart alerts

---

## 6. CI/CD Security

### GitHub Actions
- **Authentication**: OIDC federation with AWS (no long-lived credentials)
  - Role: `github-actions-ecr-role`
  - Permissions: `id-token: write`, `contents: read`
- **Workflow Permissions**: Least-privilege scoped to ECR push operations
- **Branch Protection** (Recommended): Enforce code review before merging to main

### Pipeline Security Controls
1. **Pre-build**: Trivy filesystem scan (`security-scan` job)
2. **Build**: Multi-stage Docker builds with pinned base images
3. **Post-build**: Trivy image scan (fails on HIGH/CRITICAL)
4. **Push**: Images tagged with Git SHA (7-char) + `latest`
5. **Sign**: AWS Signer with Notation CLI
6. **Verify**: Signature verification before deployment

---

## 7. Security Audit Trail (2025-12-10)

### Remediations Completed
1. ✅ **ACM Certificate**: Replaced placeholder with real certificate ARN in ingress.yaml
2. ✅ **JWT Secrets Management**: Migrated from K8s Secret to AWS Secrets Manager
3. ✅ **NetworkPolicies**: Added IMDS egress and AWS API egress policies for IRSA services
4. ✅ **Frontend Vulnerabilities**: Updated Dockerfile to fix libxml2 CVEs (2 CRITICAL, 2 HIGH)
5. ✅ **Backend Vulnerabilities**: urllib3>=2.6.0 already specified in requirements.txt
6. ✅ **ECR Scan-on-Push**: Enabled for all 6 repositories
7. ✅ **GuardDuty EKS Runtime**: Enabled for advanced threat detection
8. ✅ **Image Signing**: AWS Signer (Notation) verified in CI/CD pipeline

### Pending Actions
- **Frontend Image Rebuild**: Rebuild and push frontend:latest with libxml2 fix (requires Docker Desktop running)
- **ACM Certificate Validation**: Complete DNS validation for certificate if not already issued
- **Falco Deployment** (Optional): Runtime security monitoring for anomaly detection
- **Policy as Code** (Optional): Integrate OPA Gatekeeper for admission control

---

## 8. Compliance & Best Practices

### AWS Well-Architected
- ✅ Defense-in-depth: Multiple layers of security (network, container, IAM)
- ✅ Least-privilege: IRSA roles scoped to specific resources
- ✅ Encryption: At-rest and in-transit encryption enforced
- ✅ Monitoring: GuardDuty, CloudWatch, control plane logs enabled
- ✅ Incident response: Audit logs and GuardDuty findings for forensics

### CIS Kubernetes Benchmark
- ✅ Non-root containers (4.1.1)
- ✅ Read-only root filesystem (4.1.2)
- ✅ Seccomp profiles (4.1.3)
- ✅ Network policies (4.2.1)
- ✅ Pod Security Standards enforced

---

## References
- [AWS EKS Security Best Practices](https://docs.aws.amazon.com/eks/latest/userguide/best-practices-security.html)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [IRSA Documentation](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [AWS Signer (Notation)](https://docs.aws.amazon.com/signer/latest/developerguide/Welcome.html)

---

**Last Updated**: 2025-12-10  
**Security Contact**: ENPM818R_Group3  
**Next Review**: 2026-01-10

