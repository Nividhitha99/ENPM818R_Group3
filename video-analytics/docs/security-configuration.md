# Security Configuration

## 1. Network Security
- **VPC**: Deployed in private subnets across 2 AZs. Public subnets only for Load Balancers and NAT Gateways.
- **Network Policies**: Kubernetes NetworkPolicies deny all traffic by default (`default-deny-all`), explicitly allowing only necessary communication (e.g., Frontend -> Uploader).
- **TLS**: All traffic encrypted in transit using AWS ACM certificates on ALB Ingress.

## 2. Container Security
- **Non-Root Users**: All Dockerfiles utilize `appuser` (UID 1000) instead of root.
- **Read-Only Filesystems**: `readOnlyRootFilesystem: true` configured in Kubernetes deployments where possible.
- **Capabilities**: `ALL` capabilities dropped.
- **Scanning**: Trivy/Grype integrated into CI/CD pipeline to block critical vulnerabilities.

## 3. IAM & Access Control
- **IRSA (IAM Roles for Service Accounts)**: Pods use minimal IAM permissions (e.g., Uploader only puts to S3, doesn't delete).
- **RBAC**: Kubernetes RBAC restricts access to resources based on roles (dev, gitops, admin).

## 4. Data Protection
- **Encryption at Rest**:
  - S3 Buckets: SSE-S3 (AES-256).
  - DynamoDB: Server-side encryption enabled.
  - EBS/EFS: Encrypted with KMS.
- **Secrets Management**: Kubernetes Secrets used for non-sensitive config; AWS Secrets Manager recommended for high-value creds.

## 5. Monitoring & Auditing
- **GuardDuty**: Enabled on AWS account.
- **Audit Logs**: EKS Control Plane logs enabled (Authenticator, ControllerManager, Scheduler).
- **Falco**: (Recommended) Runtime security monitoring.

