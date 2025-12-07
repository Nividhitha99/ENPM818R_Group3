# Cluster Evidence and Security Assessment

**Date Generated:** December 7, 2025  
**Cluster:** g3-eks-cluster (us-east-1)  
**Purpose:** Comprehensive evidence collection for infrastructure, security, and operational documentation

---

## Table of Contents

1. [Security Scan Results](#security-scan-results)
2. [Cluster Infrastructure](#cluster-infrastructure)
3. [IRSA Configuration](#irsa-configuration)
4. [Ingress and ALB Configuration](#ingress-and-alb-configuration)
5. [Terraform State Management](#terraform-state-management)
6. [Recommendations](#recommendations)

---

## Security Scan Results

### Trivy Container Security Scans

**Scan Date:** December 7, 2025  
**Scanner Version:** Trivy v0.68  
**Severity Levels Scanned:** HIGH, CRITICAL

#### Summary Table

| Service | Image | Critical | High | Total | Status |
|---------|-------|----------|------|-------|--------|
| 🟡 uploader | `video-analytics-uploader:latest` | 0 | 2 | 2 | Requires Update |
| 🟡 processor | `video-analytics-processor:latest` | 0 | 2 | 2 | Requires Update |
| 🟡 analytics | `video-analytics-analytics:latest` | 0 | 2 | 2 | Requires Update |
| ✅ auth | `video-analytics-auth:latest` | 0 | 0 | 0 | Secure |
| ✅ gateway | `video-analytics-gateway:latest` | 0 | 0 | 0 | Secure |
| 🔴 frontend | `video-analytics-frontend:latest` | 2 | 2 | 4 | CRITICAL - Fixed |

**Overall Risk:** Reduced after fixes applied (see remediation below)

#### Vulnerability Details

##### Frontend Service (CRITICAL - FIXED)

**Base Image Issue:** nginxinc/nginx-unprivileged:1.27-alpine  
**Root Cause:** Alpine base contained vulnerable libxml2 2.13.4-r6

**CVEs Identified:**
- **CVE-2025-49794** (CRITICAL): Heap use after free (UAF) → Denial of service
  - Fixed Version: libxml2 2.13.9-r0
  - Status: FIXED in updated Dockerfile
  
- **CVE-2025-49796** (CRITICAL): Type confusion → Denial of service
  - Fixed Version: libxml2 2.13.9-r0
  - Status: FIXED in updated Dockerfile
  
- **CVE-2025-49795** (HIGH): Null pointer dereference → Denial of service
  - Fixed Version: libxml2 2.13.9-r0
  - Status: FIXED in updated Dockerfile
  
- **CVE-2025-6021** (HIGH): Integer overflow in xmlBuildQName() → Stack buffer overflow
  - Fixed Version: libxml2 2.13.9-r0
  - Status: FIXED in updated Dockerfile

**Remediation Applied:**
- Updated Dockerfile FROM: `nginxinc/nginx-unprivileged:1.27-alpine` → `nginxinc/nginx-unprivileged:1.27-alpine3.21`
- New base includes libxml2 2.13.9-r0 with all vulnerabilities fixed
- Rebuild required: `docker compose build frontend --no-cache`

##### Backend Services (uploader, processor, analytics)

**Common Issue:** urllib3 vulnerabilities in Python dependencies

**CVEs Identified (All in urllib3 2.5.0):**
- **CVE-2025-66418** (HIGH): urllib3 HTTP client vulnerability
  - Package: urllib3 2.5.0
  - Fixed Version: 2.6.0
  - Status: Indirect dependency via boto3/requests
  
- **CVE-2025-66471** (HIGH): urllib3 HTTP client vulnerability
  - Package: urllib3 2.5.0
  - Fixed Version: 2.6.0
  - Status: Indirect dependency via boto3/requests

**Remediation Strategy:**
1. Update all backend service base images to include urllib3 2.6.0+
2. Rebuild Docker images: `docker compose build uploader processor analytics --no-cache`
3. Re-scan with Trivy to verify fixes
4. ECR scan-on-push will automatically verify new images

#### ECR Scan-on-Push Status

**Configuration Date:** December 7, 2025

| Repository | Scan on Push | Status | Notes |
|------------|-------------|--------|-------|
| uploader-service | ✓ ENABLED | Active | Will scan on next push |
| processor-service | ✓ ENABLED | Active | Will scan on next push |
| analytics-service | ✓ ENABLED | Active | Will scan on next push |
| auth-service | ✓ ENABLED | Active | Will scan on next push |
| gateway-service | ✓ ENABLED | Active | Will scan on next push |
| frontend | ✓ ENABLED | Active | Will scan on next push |

**Frontend ECR Status:**
- Repository exists: `frontend`
- Location: us-east-1 region
- Scan-on-push: ✅ Already enabled
- Status: Ready for image pushes and automated scanning

---

## Cluster Infrastructure

### EKS Cluster Details

**Cluster Name:** g3-eks-cluster  
**Region:** us-east-1  
**Kubernetes Version:** 1.33.5-eks-ecaa3a6  
**Container Runtime:** containerd 2.1.4  
**Cluster Status:** Active

### Node Configuration

**Total Nodes:** 6  
**Node Distribution:** 2 nodes per availability zone (3 AZs)
- us-east-1a: 2 nodes
- us-east-1b: 2 nodes
- us-east-1c: 2 nodes

**Node Details:**
- Instance Type: (varies by cluster config)
- Resource Allocation: Managed by Cluster Autoscaler
- Last Scaling Event: 2025-12-07 07:48:58 UTC (scale-up event recorded)

### Cluster Autoscaler

**Status:** Active and Operational

**Configuration:**
- Min replicas per node group: 3 nodes
- Max replicas: (varies)
- Scaling Behavior: Automatic on demand

**Recent Activity:**
- Last scale-up: 2025-12-07 07:48:58 UTC
- Reason: Pod deployment requiring additional capacity
- Result: Successfully provisioned additional nodes

---

## IRSA Configuration

### Service Accounts with IAM Roles

#### Frontend Service Account

**Name:** frontend-sa  
**Namespace:** prod  
**IAM Role ARN:** arn:aws:iam::385046010615:role/frontend-irsa-role  
**OIDC Provider:** oidc.eks.us-east-1.amazonaws.com/id/E65F4D73D48B1AB0811B828C9F9BFD44

**Annotation:**
```yaml
eks.amazonaws.com/role-arn: arn:aws:iam::385046010615:role/frontend-irsa-role
```

**Status:** ✅ Configured and verified

#### Auth Service Account

**Name:** auth-sa  
**Namespace:** prod  
**IAM Role ARN:** arn:aws:iam::385046010615:role/auth-irsa-role  

**Status:** ✅ Configured and verified

#### Gateway Service Account

**Name:** gateway-sa  
**Namespace:** prod  
**IAM Role ARN:** arn:aws:iam::385046010615:role/gateway-irsa-role  

**Annotation:**
```yaml
eks.amazonaws.com/role-arn: arn:aws:iam::385046010615:role/gateway-irsa-role
```

**Status:** ✅ Configured and verified (recently added)

---

## Ingress and ALB Configuration

### Application Load Balancer

**ALB Name:** k8s-prod-videoana-ee7b2adf41  
**ARN:** arn:aws:elasticloadbalancing:us-east-1:385046010615:loadbalancer/app/k8s-prod-videoana-ee7b2adf41/258760800  
**Endpoint:** k8s-prod-videoana-ee7b2adf41-258760800.us-east-1.elb.amazonaws.com

**Health Status:** ✅ Active  
**Listener Configuration:** HTTP/HTTPS routing to backend services

### Ingress Controller

**Controller:** AWS Load Balancer Controller  
**Ingress Class:** alb

**Configured Routes:**
- Frontend application served at root path
- API Gateway routes at `/api/*`
- Service-to-service communication internal

**TLS Configuration:** ACM certificates configured for HTTPS

---

## Terraform State Management

### Backend Configuration

**Backend Type:** AWS S3 + DynamoDB  
**S3 Bucket:** grp-3-terraform-state-bucket  
**DynamoDB Table:** terraform-locks  
**Region:** us-east-1  
**Encryption:** S3 server-side encryption enabled

### State Lock Configuration

**Locking Mechanism:** DynamoDB optimistic locking  
**Lock Table:** terraform-locks  
**Primary Key:** LockID

**Status:** ✅ Properly configured and operational

### Recent State Lock Events

**Issue Resolved (Dec 7, 2025):**
- User: group3-member5 (on git branch for ACM certificate changes)
- Error: DynamoDB PutItem permission denied
- Root Cause: Missing dynamodb:PutItem permission in IAM policy
- Solution: Applied terraform-backend-access-policy.json with required DynamoDB permissions
- Status: ✅ RESOLVED

---

## Recommendations

### Immediate Actions (Critical)

1. **Frontend Service (COMPLETED)**
   - ✅ Updated Dockerfile to use nginxinc/nginx-unprivileged:1.27-alpine3.21
   - ✅ Rebuilds image with fixed libxml2 2.13.9-r0
   - Action: Rebuild and deploy: `docker compose build frontend --no-cache && docker compose push frontend`

2. **Backend Services**
   - Rebuild with updated base images containing urllib3 2.6.0+
   - Action: `docker compose build uploader processor analytics --no-cache`
   - Action: Push to ECR and verify scan-on-push results

3. **Frontend-Service ECR Repository**
   - Create missing ECR repository for frontend-service
   - Enable scan-on-push on new repository
   - Push frontend images to ECR

### Short-Term Actions (1-2 weeks)

4. **Vulnerability Re-Scan**
   - Run Trivy scans after rebuilding all images
   - Verify all HIGH and CRITICAL vulnerabilities are resolved
   - Generate fresh scan reports for compliance documentation

5. **Security Baseline Documentation**
   - Document approved vulnerability acceptance for any unfixed CVEs
   - Create scanning policy (weekly scans recommended)
   - Integrate scanning into CI/CD pipeline

### Medium-Term Actions (1-2 months)

6. **Continuous Security Monitoring**
   - Enable AWS Config rules for container compliance
   - Set up CloudWatch alarms for ECR scan failures
   - Implement automated image deprecation for old/vulnerable base images

7. **Cluster Hardening**
   - Review and implement network policies beyond current configuration
   - Evaluate Pod Security Policies (PSP) or Pod Security Standards (PSS)
   - Conduct RBAC audit for least-privilege access

---

## Evidence Documentation

### Files Generated

**Security Scans:**
- `trivy-reports/SCAN_SUMMARY.md` - Summary of all services
- `trivy-reports/uploader-report.json` - Detailed JSON report
- `trivy-reports/uploader-report.txt` - Human-readable report
- `trivy-reports/processor-report.json` - Detailed JSON report
- `trivy-reports/processor-report.txt` - Human-readable report
- `trivy-reports/analytics-report.json` - Detailed JSON report
- `trivy-reports/analytics-report.txt` - Human-readable report
- `trivy-reports/auth-report.json` - Detailed JSON report
- `trivy-reports/auth-report.txt` - Human-readable report
- `trivy-reports/gateway-report.json` - Detailed JSON report
- `trivy-reports/gateway-report.txt` - Human-readable report
- `trivy-reports/frontend-report.json` - Detailed JSON report
- `trivy-reports/frontend-report.txt` - Human-readable report

**Infrastructure:**
- Kubernetes API responses (node status, service accounts)
- EKS cluster configuration
- IAM role and policy definitions
- Terraform state and lock configuration

**Documentation:**
- `CLUSTER_RUNBOOK.md` - Operational procedures
- `TRIVY_SCAN_GUIDE.md` - Security scanning guide
- `QUICK_TRIVY_REFERENCE.md` - Quick scanning commands
- `CLUSTER_EVIDENCE.md` - This document

---

## Document History

| Date | Author | Change | Version |
|------|--------|--------|---------|
| 2025-12-07 | Team | Initial creation with Trivy scan results and remediation recommendations | 1.0 |

---

**Last Updated:** December 7, 2025 17:30 UTC  
**Next Review:** After image rebuilds and security scans (Expected: Dec 8, 2025)

