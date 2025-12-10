# Security Configuration

This document outlines the comprehensive security measures implemented in the video analytics EKS deployment, following Defense-in-Depth principles.

## 1. Image and Supply Chain Security

### Base Images
- **Trusted base images**: All services use trusted base images:
  - Python services: `python:3.11-slim` (Debian-based, minimal)
  - Frontend: `nginxinc/nginx-unprivileged:1.27-alpine` (unprivileged nginx)
- **Multi-stage builds**: All Dockerfiles use multi-stage builds to minimize image size and attack surface
- **Minimal dependencies**: Processor installs `ffmpeg` with `--no-install-recommends` to reduce surface area

### Image Scanning
- **Trivy scanning**: Automated vulnerability scanning in CI/CD pipeline
  - Filesystem scan: Scans repository code for vulnerabilities
  - Image scan: Scans built Docker images before push
  - Fails on `HIGH`/`CRITICAL` vulnerabilities
  - Results uploaded to GitHub Security tab
- **Local scanning**: Run `pwsh ./video-analytics/scripts/trivy_scan.ps1` for local scans
- **ECR scanning**: AWS ECR provides additional vulnerability scanning

### Image Signing and Immutability
- **Cosign signing**: Images are signed with Cosign (optional, configured in CI/CD)
- **SHA-based tags**: CI/CD automatically tags images with commit SHA (e.g., `auth-service:abc1234`)
- **Immutable tags**: Production deployments should use SHA-based tags instead of `latest`

## 2. Cluster and Node Security

### EKS Cluster Configuration
- **Private API endpoint**: EKS API endpoint is private-only (`endpoint_private_access = true`)
- **Public access disabled**: No public access to EKS API endpoint
- **VPC**: Deployed in private subnets across 3 AZs; public subnets only for Load Balancers and NAT Gateways

### Node Security
- **SSH access disabled**: Worker nodes have no SSH keys configured (`remote_access.ec2_ssh_key = null`)
- **EBS encryption**: All EBS volumes encrypted at rest
- **Security Groups**: Applied to restrict inbound/outbound traffic
- **Managed node groups**: Using EKS managed node groups with AL2023 AMI

### Access Control
- **IRSA (IAM Roles for Service Accounts)**: All pods use IRSA for AWS API access with least-privilege permissions
- **RBAC**: Kubernetes RBAC restricts access based on roles (dev, gitops, admin)
- **EKS Access Entries**: Cluster access managed through EKS access entries with appropriate policies

## 3. Pod and Workload Security

### Pod Security Standards
- **Namespace-level enforcement**: Pod Security Standards applied via namespace labels
  - `prod` namespace: `restricted` (most secure)
  - `dev`/`staging` namespaces: `baseline` (moderate security)
- **Policy file**: `video-analytics/k8s/prod/pod-security-policy.yaml`

### Security Contexts
All pods include comprehensive security contexts:
- **runAsNonRoot**: `true` - All containers run as non-root users
  - Backend services: UID 1000 (`appuser`)
  - Frontend: UID 101 (nginx unprivileged user)
- **readOnlyRootFilesystem**: `true` - Root filesystem is read-only
- **allowPrivilegeEscalation**: `false` - Prevents privilege escalation
- **capabilities.drop**: `["ALL"]` - All Linux capabilities dropped
- **seccompProfile**: `RuntimeDefault` - Default seccomp profile applied

### Resource Limits
All containers have defined resource limits:
- **Gateway/Auth/Analytics**: 128Mi-512Mi memory, 100m-500m CPU
- **Uploader**: 256Mi-1Gi memory, 200m-1000m CPU
- **Processor**: 512Mi-2Gi memory, 500m-2000m CPU (higher for video processing)
- **Frontend**: 64Mi-128Mi memory, 50m-200m CPU

### Policy Enforcement
- **Kyverno policies**: Installed and enforced for:
  - Non-root containers
  - Read-only root filesystems
  - Resource limits
  - No privileged containers
  - No deployments to default namespace
- **Installation**: See `video-analytics/k8s/policies/install-kyverno.sh`

## 4. Network & Data Security

### Network Policies
- **Default deny-all**: Kubernetes NetworkPolicies deny all traffic by default
- **Explicit allow rules**: Only necessary communication allowed:
  - Frontend → Gateway
  - Gateway → Backend services (Uploader, Analytics, Auth)
  - DNS resolution allowed for all pods
- **Policy file**: `video-analytics/k8s/networkpolicies/policies.yaml`

### TLS/HTTPS
- **Ingress TLS**: ALB Ingress configured with AWS Certificate Manager (ACM) certificates
- **SSL policy**: `ELBSecurityPolicy-TLS13-1-2-2021-06` (TLS 1.2+)
- **HTTP to HTTPS redirect**: Enabled
- **HTTP/2**: Enabled on ALB
- **Certificate ARN**: Configure in `video-analytics/k8s/prod/ingress.yaml`

### Inter-Service Communication
- **Cluster-internal**: Services communicate via ClusterIP services within the cluster
- **mTLS**: Optional - Can be enabled with service mesh (AWS App Mesh or Istio)

### Data Encryption
- **At Rest**:
  - S3 Buckets: SSE-S3 (AES-256)
  - DynamoDB: Server-side encryption enabled
  - EBS Volumes: Encrypted with KMS
- **In Transit**: All traffic encrypted via TLS/HTTPS

### Secrets Management
- **Kubernetes Secrets**: Used for non-sensitive configuration
- **AWS Secrets Manager**: Recommended for high-value credentials (JWT secrets, API keys)
- **IRSA Integration**: Secrets Manager accessed via IRSA (no hardcoded credentials)

## 5. CI/CD and Access Security

### GitHub Actions Security
- **OIDC authentication**: Uses AWS IAM roles via OIDC (no long-lived credentials)
- **Automated security scanning**: 
  - Trivy filesystem scan on every push
  - Trivy image scan after build
  - Results uploaded to GitHub Security tab
- **Image signing**: Cosign signing configured (optional)
- **SHA-based tags**: Automatic tagging with commit SHA

### Branch Protection
- **Required**: Pull request reviews (2 approvals)
- **Required**: Status checks must pass (security scans)
- **Required**: Signed commits
- **Required**: Code owner reviews
- **Restricted**: Direct pushes to main branch disabled

### Signed Commits
- **GPG signing**: All commits should be signed with GPG keys
- **S/MIME**: Alternative signing method supported
- **Verification**: GitHub verifies commit signatures
- **Setup guide**: See `video-analytics/docs/security-implementation-guide.md`

### Manifest Validation
- **Kyverno**: Validates Kubernetes manifests before deployment
- **Policy enforcement**: Blocks non-compliant deployments
- **Audit mode**: Some policies run in audit mode for visibility

## 6. Monitoring & Auditing

### EKS Control Plane Logging
- **Enabled log types**:
  - API server logs
  - Audit logs
  - Authenticator logs
  - Controller Manager logs
  - Scheduler logs
- **CloudWatch Log Groups**: 
  - `/aws/eks/g3-eks-cluster/cluster`
  - `/aws/eks/g3-eks-cluster/applications`
- **Retention**: 90 days for cluster logs, 30 days for application logs

### GuardDuty
- **Enabled**: Threat detection and continuous monitoring
- **Features**:
  - EKS audit log protection
  - S3 malware protection
  - EC2 instance protection
  - Finding publishing frequency: 15 minutes
- **Alerts**: SNS topic configured for GuardDuty findings
- **Configuration**: `IaC/guardduty.tf`

### CloudWatch Monitoring
- **Alarms**: 
  - High CPU utilization (>80%)
  - High memory utilization (>85%)
- **Dashboards**: EKS cluster metrics dashboard
- **Log aggregation**: Centralized logging for all services

### Additional Recommendations
- **Falco**: Runtime security monitoring (recommended for production)
- **Prometheus/Grafana**: Application metrics and monitoring
- **AWS Security Hub**: Centralized security findings aggregation

## Security Checklist

Before deploying to production, ensure:

- [x] Pod Security Standards applied
- [x] Security contexts added to all pods
- [x] Resource limits defined
- [x] Network policies configured
- [x] TLS/HTTPS enabled on Ingress
- [x] EKS Control Plane Logging enabled
- [x] GuardDuty enabled
- [x] CI/CD security scanning configured
- [x] Image signing configured (optional)
- [x] Branch protection rules enabled
- [x] Signed commits required
- [x] Kyverno policies installed
- [x] SSH access disabled on worker nodes
- [x] EBS volumes encrypted
- [ ] Secrets migrated to AWS Secrets Manager (recommended)
- [ ] Service mesh for mTLS (optional)

## Additional Resources

- **Security Implementation Guide**: `video-analytics/docs/security-implementation-guide.md`
- **AWS EKS Security Best Practices**: https://aws.github.io/aws-eks-best-practices/security/
- **Kubernetes Security**: https://kubernetes.io/docs/concepts/security/
- **Trivy Documentation**: https://aquasecurity.github.io/trivy/
- **Kyverno Documentation**: https://kyverno.io/docs/

