# EKS Cluster Operations Runbook

## Table of Contents
- [Kubeconfig Setup](#kubeconfig-setup)
- [Cluster Bootstrap](#cluster-bootstrap)
- [Maintenance Procedures](#maintenance-procedures)
- [Troubleshooting](#troubleshooting)

## Kubeconfig Setup

### Initial Configuration

1. **Install AWS CLI and kubectl**
   ```powershell
   # Verify installations
   aws --version
   kubectl version --client
   ```

2. **Configure AWS Credentials**
   ```powershell
   aws configure
   # Enter your Access Key ID, Secret Access Key, and region (us-east-1)
   ```

3. **Update Kubeconfig**
   ```powershell
   aws eks update-kubeconfig --name enpm818r-cluster --region us-east-1
   ```

4. **Verify Access**
   ```powershell
   kubectl get nodes
   kubectl get namespaces
   ```

### Multiple Users Setup

For team members who need access:

1. **Admin creates IAM role binding** (one-time setup)
   ```powershell
   kubectl create clusterrolebinding team-member-binding `
     --clusterrole=edit `
     --user=arn:aws:iam::385046010615:user/<username>
   ```

2. **Team member updates kubeconfig**
   ```powershell
   aws eks update-kubeconfig --name enpm818r-cluster --region us-east-1
   ```

## Cluster Bootstrap

### Prerequisites
- Terraform installed (v1.0+)
- AWS CLI configured
- kubectl installed
- Helm installed (optional, for add-ons)

### Infrastructure Deployment

1. **Navigate to IaC directory**
   ```powershell
   cd IaC
   ```

2. **Initialize Terraform**
   ```powershell
   terraform init
   ```

3. **Review planned changes**
   ```powershell
   terraform plan
   ```

4. **Apply infrastructure**
   ```powershell
   terraform apply
   ```
   This creates:
   - EKS cluster with managed node groups
   - VPC and networking
   - IRSA roles for service accounts
   - CloudWatch logging

5. **Update kubeconfig**
   ```powershell
   aws eks update-kubeconfig --name enpm818r-cluster --region us-east-1
   ```

### Application Bootstrap

1. **Create namespaces**
   ```powershell
   kubectl create namespace prod
   ```

2. **Apply secrets and ConfigMaps**
   ```powershell
   cd ..\video-analytics\k8s\prod
   kubectl apply -f config-secrets.yaml
   ```

3. **Deploy services in order**
   ```powershell
   # Auth service first
   kubectl apply -f auth.yaml
   kubectl wait --for=condition=available --timeout=120s deployment/auth -n prod
   
   # Backend services
   kubectl apply -f uploader.yaml
   kubectl apply -f processor.yaml
   kubectl apply -f analytics.yaml
   
   # Gateway
   kubectl apply -f gateway.yaml
   
   # Frontend
   kubectl apply -f frontend.yaml
   ```

4. **Apply ingress**
   ```powershell
   kubectl apply -f ingress.yaml
   ```

5. **Verify deployments**
   ```powershell
   kubectl get pods -n prod
   kubectl get svc -n prod
   kubectl get ingress -n prod
   ```

### IRSA Verification

Verify that service accounts have proper IAM role annotations:

```powershell
kubectl get sa -n prod
kubectl describe sa gateway-sa -n prod | Select-String "role-arn"
kubectl describe sa uploader-sa -n prod | Select-String "role-arn"
kubectl describe sa processor-sa -n prod | Select-String "role-arn"
kubectl describe sa analytics-sa -n prod | Select-String "role-arn"
kubectl describe sa auth-sa -n prod | Select-String "role-arn"
```

Expected annotation:
```
eks.amazonaws.com/role-arn: arn:aws:iam::385046010615:role/<service>-irsa-role
```

## Maintenance Procedures

### Routine Health Checks

**Daily Checks** (automated via CloudWatch)
```powershell
# Check node health
kubectl get nodes

# Check pod status
kubectl get pods -n prod

# Check resource usage
kubectl top nodes
kubectl top pods -n prod
```

**Weekly Checks**
```powershell
# Review logs for errors
kubectl logs -n prod -l app=gateway --tail=100 | Select-String "ERROR"
kubectl logs -n prod -l app=processor --tail=100 | Select-String "ERROR"

# Check persistent volume claims
kubectl get pvc -n prod

# Review ingress status
kubectl get ingress -n prod
```

### Scaling Operations

**Manual Scaling**
```powershell
# Scale a deployment
kubectl scale deployment/<service-name> --replicas=<count> -n prod

# Example: Scale gateway to 3 replicas
kubectl scale deployment/gateway --replicas=3 -n prod
```

**Cluster Autoscaler** (automated)
- Configured in Terraform (`cluster-autoscaler-policy.json`)
- Automatically scales nodes based on pod resource requests
- Min nodes: 2, Max nodes: 10

### Rolling Updates

**Update container image**
```powershell
# Set new image
kubectl set image deployment/<service-name> <container-name>=<new-image> -n prod

# Example: Update gateway
kubectl set image deployment/gateway gateway=385046010615.dkr.ecr.us-east-1.amazonaws.com/gateway-service:v2.0 -n prod

# Monitor rollout
kubectl rollout status deployment/<service-name> -n prod
```

**Rollback if needed**
```powershell
kubectl rollout undo deployment/<service-name> -n prod
```

### Secret Rotation

```powershell
# Update secret
kubectl delete secret <secret-name> -n prod
kubectl create secret generic <secret-name> --from-literal=key=value -n prod

# Restart deployment to pick up new secret
kubectl rollout restart deployment/<service-name> -n prod
```

### Certificate Management

**Check ALB ingress certificate expiration**
```powershell
aws acm describe-certificate --certificate-arn <cert-arn> --region us-east-1
```

**Renew certificates** (automated via ACM)
- ACM automatically renews certificates
- Monitor expiration dates via CloudWatch alarms

### Backup Procedures

**DynamoDB** (automated)
- Point-in-time recovery enabled in Terraform
- Retention: 7 days

**S3 Buckets** (automated)
- Versioning enabled
- Lifecycle policies configured

**Kubernetes Configuration Backup**
```powershell
# Export all resources in prod namespace
kubectl get all -n prod -o yaml > backup-prod-$(Get-Date -Format 'yyyyMMdd').yaml

# Export secrets (encrypted)
kubectl get secrets -n prod -o yaml > backup-secrets-$(Get-Date -Format 'yyyyMMdd').yaml
```

### Log Management

**View logs**
```powershell
# Recent logs
kubectl logs -n prod <pod-name> --tail=100

# Follow logs
kubectl logs -n prod <pod-name> -f

# Previous container logs (if crashed)
kubectl logs -n prod <pod-name> --previous
```

**CloudWatch Logs**
```powershell
# View via AWS CLI
aws logs tail /aws/eks/enpm818r-cluster/cluster --follow --region us-east-1
```

## Troubleshooting

### Pod Issues

**Pod not starting**
```powershell
# Describe pod for events
kubectl describe pod <pod-name> -n prod

# Common issues:
# - ImagePullBackOff: Check ECR permissions
# - CrashLoopBackOff: Check application logs
# - Pending: Check resource requests vs available capacity
```

**Pod evicted or terminated**
```powershell
# Check node pressure
kubectl describe node <node-name> | Select-String "Pressure"

# Check resource quotas
kubectl describe resourcequota -n prod
```

### Service Discovery Issues

**Service not reachable**
```powershell
# Verify service endpoints
kubectl get endpoints <service-name> -n prod

# Test internal DNS
kubectl run test-pod --image=busybox --rm -it -- nslookup <service-name>.prod.svc.cluster.local

# Check network policies
kubectl get networkpolicies -n prod
```

### IRSA/Permission Issues

**Pods can't access AWS resources**
```powershell
# Verify service account annotation
kubectl describe sa <sa-name> -n prod

# Check pod environment
kubectl exec -n prod <pod-name> -- env | Select-String "AWS"

# Verify IAM role trust policy
aws iam get-role --role-name <role-name> --region us-east-1
```

### Ingress Issues

**ALB not created**
```powershell
# Check ingress controller logs
kubectl logs -n kube-system -l app.kubernetes.io/name=aws-load-balancer-controller

# Verify ingress resource
kubectl describe ingress <ingress-name> -n prod

# Check AWS ALB
aws elbv2 describe-load-balancers --region us-east-1
```

### Node Issues

**Node not ready**
```powershell
# Check node status
kubectl describe node <node-name>

# Check node logs (via AWS Systems Manager)
aws ssm start-session --target <instance-id> --region us-east-1
```

**Node resource exhaustion**
```powershell
# Check resource usage
kubectl top nodes
kubectl describe node <node-name> | Select-String "Allocated resources"

# Force pod eviction if needed
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

### Emergency Procedures

**Complete service outage**
1. Check AWS Service Health Dashboard
2. Verify EKS cluster status: `aws eks describe-cluster --name enpm818r-cluster --region us-east-1`
3. Check node status: `kubectl get nodes`
4. Review recent deployments: `kubectl rollout history deployment/<service> -n prod`
5. Rollback if needed: `kubectl rollout undo deployment/<service> -n prod`

**Database connectivity issues**
1. Check DynamoDB service status
2. Verify IAM permissions on analytics service
3. Check network policies
4. Review application logs for connection errors

**Security incident**
1. Isolate affected pods: `kubectl scale deployment/<service> --replicas=0 -n prod`
2. Capture logs: `kubectl logs <pod-name> -n prod > incident-logs.txt`
3. Review CloudWatch Logs for suspicious activity
4. Rotate secrets: `kubectl delete secret <secret> -n prod`
5. Update IAM policies if compromised

## Additional Resources

- [AWS EKS Documentation](https://docs.aws.amazon.com/eks/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Project Security Configuration](../video-analytics/docs/security-configuration.md)
- [Project Observability Runbook](../video-analytics/docs/observability-runbook.md)
- [Deployment Guide](../DEPLOYMENT.md)
- [Testing Guide](../TESTING_GUIDE.md)

## Contact

For urgent issues:
- Team Lead: [Team contact info]
- AWS Support: [Support plan details]
- On-call rotation: [Link to schedule]
