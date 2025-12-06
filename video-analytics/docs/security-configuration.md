# Security Configuration

## 1. Network Security
- **VPC**: Deployed in private subnets across 2 AZs. Public subnets only for Load Balancers and NAT Gateways.
- **Network Policies**: Kubernetes NetworkPolicies deny all traffic by default (`default-deny-all`), explicitly allowing only necessary communication (e.g., Frontend -> Uploader).
- **TLS**: All traffic encrypted in transit using AWS ACM certificates on ALB Ingress.

## 2. Container Security
- **Non-root runtime**: All services run as non-root; backend images use `appuser` (UID 1000) and the frontend uses the unprivileged nginx image listening on 8080.
- **Multi-stage, minimal bases**: Builder/runtime split for every image; Python uses `python:3.11-slim` with bytecode disabled and unbuffered logs; processor installs `ffmpeg` with `--no-install-recommends` to shrink surface area; frontend uses `npm ci` for reproducible installs.
- **Image scanning**: Run `scripts/trivy_scan.ps1` to build and scan all service images: `pwsh ./scripts/trivy_scan.ps1`. The script pulls the latest Trivy image and fails on `HIGH`/`CRITICAL` vulnerabilities (ignores unfixed by default).
- **Least-privilege mounts**: Runtime credentials are mounted read-only in `docker-compose` (e.g., `${USERPROFILE}/.aws:/root/.aws:ro`) to minimize write access from containers.

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

