# Secret Rotation Procedures

## Overview
This document outlines procedures for rotating secrets used in the video analytics application. Regular secret rotation is a critical security practice that limits the impact of potential credential compromise.

## Secrets Inventory

### 1. JWT Secret
- **Current Location**: Kubernetes Secret `video-analytics-secrets` in `prod` namespace
- **Key Name**: `JWT_SECRET`
- **Used By**: Auth service
- **Rotation Frequency**: Every 90 days or immediately after security incident
- **Impact**: All existing JWT tokens will be invalidated

### 2. AWS IAM Credentials
- **Location**: IRSA (IAM Roles for Service Accounts) - No rotation needed
- **Service Accounts**: 
  - `auth-sa` → `auth-irsa-role`
  - `uploader-sa` → `uploader-irsa-role`
  - `processor-sa` → `processor-irsa-role`
  - `analytics-sa` → `analytics-irsa-role`
- **Rotation**: IRSA uses temporary credentials, no manual rotation required

### 3. Database Credentials (if using RDS)
- **Location**: AWS Secrets Manager (recommended) or Kubernetes Secrets
- **Rotation Frequency**: Every 90 days
- **Procedure**: Use AWS RDS automatic password rotation if using Secrets Manager

### 4. GitHub Actions Secrets
- **Location**: GitHub Repository Secrets
- **Secrets**:
  - `COSIGN_PASSWORD` (for image signing)
  - Any other CI/CD secrets
- **Rotation Frequency**: Every 90 days or when team member leaves

## Rotation Procedures

### Procedure 1: Rotate JWT Secret

**Prerequisites:**
- Access to Kubernetes cluster
- `kubectl` configured with appropriate permissions

**Steps:**

1. **Generate New Secret:**
   ```bash
   # Generate a secure random secret
   NEW_JWT_SECRET=$(openssl rand -hex 32)
   echo "New JWT Secret: $NEW_JWT_SECRET"
   ```

2. **Update Kubernetes Secret:**
   ```bash
   # Update the secret
   kubectl create secret generic video-analytics-secrets \
     --from-literal=JWT_SECRET="$NEW_JWT_SECRET" \
     -n prod \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **Restart Auth Service:**
   ```bash
   # Force rolling restart to pick up new secret
   kubectl rollout restart deployment/auth -n prod
   
   # Wait for rollout to complete
   kubectl rollout status deployment/auth -n prod
   ```

4. **Verify Service Health:**
   ```bash
   # Check pod status
   kubectl get pods -n prod -l app=auth
   
   # Check logs for errors
   kubectl logs -n prod -l app=auth --tail=50
   
   # Test authentication endpoint
   curl -X POST http://<gateway-url>/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test"}'
   ```

5. **Update Documentation:**
   - Update secret backup location (if maintained)
   - Document rotation date in change log

**Rollback Procedure:**
If issues occur, revert to previous secret:
```bash
# Restore previous secret value
kubectl create secret generic video-analytics-secrets \
  --from-literal=JWT_SECRET="<previous-secret>" \
  -n prod \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/auth -n prod
```

### Procedure 2: Rotate GitHub Actions Secrets

**Steps:**

1. **Generate New Secret Value:**
   - For `COSIGN_PASSWORD`: Generate new password for Cosign key pair
   - For other secrets: Generate new values as appropriate

2. **Update in GitHub:**
   - Go to: Repository → Settings → Secrets and variables → Actions
   - Select secret to update
   - Click "Update"
   - Enter new value
   - Save

3. **Verify CI/CD Pipeline:**
   - Trigger a test build
   - Verify pipeline completes successfully
   - Check that image signing works (if using Cosign)

4. **Update Local Key (if Cosign):**
   ```bash
   # If Cosign key was stored locally, update it
   # Generate new key pair if needed
   cosign generate-key-pair
   # Update COSIGN_PASSWORD secret in GitHub
   ```

### Procedure 3: Rotate AWS Secrets Manager Secrets (if used)

**Steps:**

1. **Update Secret in AWS Secrets Manager:**
   ```bash
   aws secretsmanager update-secret \
     --secret-id video-analytics/jwt-secret \
     --secret-string '{"JWT_SECRET":"<new-secret>"}' \
     --region us-east-1
   ```

2. **Restart Services:**
   ```bash
   kubectl rollout restart deployment/auth -n prod
   ```

3. **Verify:**
   - Check service logs
   - Test authentication

## Rotation Schedule

### Standard Rotation
- **Frequency**: Every 90 days
- **Schedule**: 
  - Q1: January 1
  - Q2: April 1
  - Q3: July 1
  - Q4: October 1

### Emergency Rotation
Rotate immediately if:
- Security incident detected
- Credential compromise suspected
- Team member with access leaves organization
- Compliance requirement mandates rotation

### On-Demand Rotation
- When requested by security team
- After security audit findings
- When migrating to new secret management system

## Verification Checklist

After each rotation:

- [ ] New secret value generated and stored securely
- [ ] Kubernetes Secret updated (if applicable)
- [ ] Services restarted successfully
- [ ] Service health checks passing
- [ ] Application logs show no errors
- [ ] Authentication flows working correctly
- [ ] No user-facing errors reported
- [ ] CloudWatch metrics normal
- [ ] Documentation updated
- [ ] Old secret securely archived (if required by policy)

## Best Practices

1. **Use AWS Secrets Manager**: For production, migrate from Kubernetes Secrets to AWS Secrets Manager with automatic rotation
2. **Automate Rotation**: Use AWS Secrets Manager automatic rotation where possible
3. **Test First**: Test rotation procedure in dev/staging before production
4. **Document Changes**: Maintain rotation log with dates and responsible parties
5. **Backup Secrets**: Securely backup old secrets for rollback (encrypted, access-controlled)
6. **Notify Team**: Inform team of rotation schedule to minimize disruption
7. **Monitor After Rotation**: Closely monitor services for 24 hours after rotation
8. **Use IRSA**: Prefer IRSA over static credentials for AWS access

## Migration to AWS Secrets Manager

**Recommended Approach:**

1. **Create Secret in AWS Secrets Manager:**
   ```bash
   aws secretsmanager create-secret \
     --name video-analytics/jwt-secret \
     --secret-string '{"JWT_SECRET":"<current-secret>"}' \
     --region us-east-1
   ```

2. **Update IRSA Policy:**
   - Add Secrets Manager read permissions to auth IRSA role

3. **Update Deployment:**
   - Modify `auth.yaml` to use External Secrets Operator or AWS SDK to fetch from Secrets Manager
   - Remove Kubernetes Secret reference

4. **Enable Automatic Rotation:**
   ```bash
   aws secretsmanager enable-rotation \
     --secret-id video-analytics/jwt-secret \
     --rotation-lambda-arn <lambda-arn> \
     --region us-east-1
   ```

## Incident Response

If secret compromise is suspected:

1. **Immediate Actions:**
   - Rotate secret immediately (don't wait for scheduled rotation)
   - Revoke all existing tokens/sessions
   - Review access logs
   - Notify security team

2. **Investigation:**
   - Review GuardDuty findings
   - Check CloudTrail logs
   - Review application logs
   - Identify scope of compromise

3. **Remediation:**
   - Rotate all related secrets
   - Update security policies
   - Conduct security review

## Contact Information

- **Security Team**: [Contact Info]
- **On-Call Engineer**: [Contact Info]
- **Rotation Coordinator**: [Contact Info]

## Change Log

| Date | Secret | Rotated By | Notes |
|------|--------|------------|-------|
| [Date] | JWT_SECRET | [Name] | Initial rotation |
| | | | |

---

**Last Updated**: [Current Date]
**Next Scheduled Rotation**: [Date]

