# Security Implementation Guide

This document provides guidance on implementing and maintaining security best practices for the video analytics EKS deployment.

## Table of Contents
1. [Branch Protection](#branch-protection)
2. [Signed Commits](#signed-commits)
3. [CI/CD Security](#cicd-security)
4. [Image Security](#image-security)
5. [Kubernetes Security](#kubernetes-security)
6. [Network Security](#network-security)
7. [Monitoring and Auditing](#monitoring-and-auditing)

## Branch Protection

### GitHub Branch Protection Rules

To enable branch protection for the `main` branch:

1. Navigate to: **Settings** → **Branches** → **Add rule**
2. Configure the following rules:
   - **Branch name pattern**: `main`
   - **Require a pull request before merging**:
     - ✅ Require approvals: **2**
     - ✅ Dismiss stale pull request approvals when new commits are pushed
     - ✅ Require review from Code Owners
   - **Require status checks to pass before merging**:
     - ✅ Require branches to be up to date before merging
     - ✅ Required status checks:
       - `security-scan` (Trivy filesystem scan)
       - `build-and-push` (Image build and scan)
   - **Require signed commits**: ✅ Enabled
   - **Do not allow bypassing the above settings**: ✅ Enabled
   - **Restrict who can push to matching branches**: ✅ Enabled (only admins)

### Code Owners

The `CODEOWNERS` file in `video-analytics/` ensures that security-sensitive changes require review from designated team members.

## Signed Commits

### Setting Up GPG Key for Signed Commits

1. **Generate a GPG key** (if you don't have one):
   ```bash
   gpg --full-generate-key
   # Choose RSA and RSA, 4096 bits
   # Set expiration (recommended: 1 year)
   ```

2. **List your GPG keys**:
   ```bash
   gpg --list-secret-keys --keyid-format=long
   ```

3. **Copy your GPG key ID** (the long form after `sec`):
   ```bash
   gpg --armor --export YOUR_KEY_ID
   ```

4. **Add GPG key to GitHub**:
   - Go to: **Settings** → **SSH and GPG keys** → **New GPG key**
   - Paste your public key

5. **Configure Git to use your GPG key**:
   ```bash
   git config --global user.signingkey YOUR_KEY_ID
   git config --global commit.gpgsign true
   ```

6. **Verify signed commits**:
   ```bash
   git commit -S -m "Your commit message"
   git log --show-signature
   ```

### Alternative: S/MIME Signing

For organizations using S/MIME:
1. Obtain an S/MIME certificate from your organization
2. Configure Git:
   ```bash
   git config --global user.signingkey YOUR_SMIME_CERT
   git config --global gpg.format x509
   git config --global gpg.x509.program smimesign
   ```

## CI/CD Security

### GitHub Actions Secrets

Store sensitive values in GitHub Secrets:
- **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Required secrets:
- `COSIGN_PASSWORD`: Password for Cosign key pair (for image signing)
- `AWS_ACCOUNT_ID`: AWS account ID (if not in workflow)
- Any other service-specific secrets

### Automated Security Scanning

The CI/CD pipeline includes:
1. **Trivy Filesystem Scan**: Scans repository for vulnerabilities
2. **Trivy Image Scan**: Scans built Docker images
3. **Image Signing**: Signs images with Cosign (optional but recommended)

### Manual Security Checks

Before merging PRs, verify:
- [ ] All security scans pass
- [ ] No HIGH or CRITICAL vulnerabilities
- [ ] Images are signed (if signing is enabled)
- [ ] Kubernetes manifests follow security best practices

## Image Security

### Image Scanning

Run Trivy scans locally:
```powershell
# Windows PowerShell
pwsh ./video-analytics/scripts/trivy_scan.ps1
```

Or scan individual images:
```bash
trivy image 385046010615.dkr.ecr.us-east-1.amazonaws.com/gateway-service:latest
```

### Image Signing with Cosign

1. **Generate a key pair**:
   ```bash
   cosign generate-key-pair
   ```

2. **Sign an image**:
   ```bash
   cosign sign --key cosign.key <IMAGE_URL>
   ```

3. **Verify an image**:
   ```bash
   cosign verify --key cosign.pub <IMAGE_URL>
   ```

### Using SHA-Based Tags

The CI/CD pipeline automatically tags images with SHA-based tags:
- `auth-service:abc1234` (first 7 characters of commit SHA)
- `auth-service:latest` (also pushed for convenience)

**Recommendation**: In production, prefer SHA-based tags over `latest` for immutability.

## Kubernetes Security

### Pod Security Standards

Pod Security Standards are enforced at the namespace level:
- **prod**: `restricted` (most secure)
- **dev/staging**: `baseline` (moderate security)

To apply:
```bash
kubectl apply -f video-analytics/k8s/prod/pod-security-policy.yaml
```

### Kyverno Policies

Install and apply Kyverno policies:
```bash
cd video-analytics/k8s/policies
chmod +x install-kyverno.sh
./install-kyverno.sh
```

Policies enforce:
- Non-root containers
- Read-only root filesystems
- Resource limits
- No privileged containers
- No deployments to default namespace

### Security Contexts

All deployments include security contexts:
- `runAsNonRoot: true`
- `readOnlyRootFilesystem: true`
- `allowPrivilegeEscalation: false`
- `capabilities.drop: ["ALL"]`

## Network Security

### TLS/HTTPS Configuration

1. **Create ACM Certificate**:
   - Request certificate in AWS Certificate Manager
   - Validate domain ownership
   - Note the certificate ARN

2. **Update Ingress**:
   - Edit `video-analytics/k8s/prod/ingress.yaml`
   - Replace `REPLACE_WITH_YOUR_CERT_ARN` with your ACM certificate ARN

3. **Apply Ingress**:
   ```bash
   kubectl apply -f video-analytics/k8s/prod/ingress.yaml
   ```

### Network Policies

Network policies are defined in `video-analytics/k8s/networkpolicies/policies.yaml`:
- Default deny-all policy
- Explicit allow rules for required communication

Apply:
```bash
kubectl apply -f video-analytics/k8s/networkpolicies/policies.yaml
```

## Monitoring and Auditing

### EKS Control Plane Logging

Control plane logs are enabled for:
- API server
- Audit logs
- Authenticator
- Controller Manager
- Scheduler

Logs are sent to CloudWatch Log Groups:
- `/aws/eks/g3-eks-cluster/cluster`

### GuardDuty

GuardDuty is enabled via Terraform (`IaC/guardduty.tf`):
- Monitors EKS audit logs
- Scans S3 buckets for malware
- Detects threats and anomalies

View findings:
```bash
aws guardduty list-findings --detector-id <DETECTOR_ID>
```

### CloudWatch Alarms

Alarms are configured for:
- High CPU utilization (>80%)
- High memory utilization (>85%)

View alarms:
```bash
aws cloudwatch describe-alarms --alarm-names eks-high-cpu-utilization eks-high-memory-utilization
```

## Security Checklist

Before deploying to production:

- [ ] Branch protection rules enabled
- [ ] All commits are signed
- [ ] CI/CD security scans pass
- [ ] Images are scanned and signed
- [ ] Pod Security Standards applied
- [ ] Kyverno policies installed
- [ ] Security contexts added to all pods
- [ ] Resource limits defined
- [ ] Network policies applied
- [ ] TLS/HTTPS configured on Ingress
- [ ] EKS Control Plane Logging enabled
- [ ] GuardDuty enabled
- [ ] Secrets stored in AWS Secrets Manager (not Kubernetes Secrets)
- [ ] IRSA configured for all service accounts
- [ ] SSH access disabled on worker nodes

## Incident Response

If a security issue is detected:

1. **Immediate Actions**:
   - Review GuardDuty findings
   - Check CloudWatch logs
   - Review recent deployments

2. **Containment**:
   - Isolate affected pods/services
   - Revoke compromised credentials
   - Update security groups/network policies

3. **Remediation**:
   - Patch vulnerabilities
   - Rotate secrets
   - Update security policies

4. **Documentation**:
   - Document the incident
   - Update security procedures
   - Conduct post-mortem

## Additional Resources

- [AWS EKS Security Best Practices](https://aws.github.io/aws-eks-best-practices/security/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
- [Kyverno Documentation](https://kyverno.io/docs/)
- [Cosign Documentation](https://docs.sigstore.dev/cosign/overview/)

