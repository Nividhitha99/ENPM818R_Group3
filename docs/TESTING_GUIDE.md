# Video Analytics Platform - Testing Guide

This guide provides comprehensive testing procedures to verify all deployed components, IRSA functionality, observability stack, and platform health.

## Prerequisites

```powershell
# Ensure you have access to the EKS cluster
aws eks update-kubeconfig --name g3-eks-cluster --region us-east-1
kubectl cluster-info

# Verify cluster connectivity
kubectl get nodes
```

## 1. IRSA (IAM Roles for Service Accounts) Testing

### 1.1 Verify Service Accounts Created

```bash
# List all service accounts in prod namespace
kubectl get sa -n prod

# List all service accounts in monitoring namespace
kubectl get sa -n monitoring

# Expected output should show: auth-sa, analytics-sa, gateway-sa, processor-sa, uploader-sa, frontend-sa
```

### 1.2 Verify IRSA Annotations

```bash
# Check if service accounts have IRSA role annotations
kubectl get sa -n prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.annotations.eks\.amazonaws\.com/role-arn}{"\n"}{end}'

# Each service account should have: eks.amazonaws.com/role-arn: arn:aws:iam::385046010615:role/<service>-irsa-role
```

### 1.3 Verify AWS Credentials in Pods

```bash
# Test auth service
kubectl exec -n prod deployment/auth -- env | grep AWS_

# Test analytics service
kubectl exec -n prod deployment/analytics -- env | grep AWS_

# Test processor service
kubectl exec -n prod deployment/processor -- env | grep AWS_

# Test gateway service
kubectl exec -n prod deployment/gateway -- env | grep AWS_

# Test uploader service
kubectl exec -n prod deployment/uploader -- env | grep AWS_

# Test frontend service
kubectl exec -n prod deployment/frontend -- env | grep AWS_

# Expected output should show:
# AWS_ROLE_ARN=arn:aws:iam::385046010615:role/<service>-irsa-role
# AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token
```

### 1.4 Verify Token File Exists

```bash
# Check if token file is mounted in pods
kubectl exec -n prod deployment/auth -- ls -la /var/run/secrets/eks.amazonaws.com/serviceaccount/

# Expected output should show token file is present
```

### 1.5 Test AWS API Access from Pod

```bash
# Get a pod name
$POD = kubectl get pods -n prod -l app=processor -o jsonpath='{.items[0].metadata.name}'

# Test S3 access from processor pod (should fail if no S3 permissions, but credentials exist)
kubectl exec -n prod $POD -- aws s3 ls

# Test from uploader (should have S3 access)
$UPLOADER_POD = kubectl get pods -n prod -l app=uploader -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n prod $UPLOADER_POD -- aws s3 ls

# Test DynamoDB access from analytics pod
$ANALYTICS_POD = kubectl get pods -n prod -l app=analytics -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n prod $ANALYTICS_POD -- aws dynamodb list-tables --region us-east-1
```

## 2. Pod Deployment Testing

### 2.1 Verify All Pods Running

```bash
# Check pod status in prod namespace
kubectl get pods -n prod

# Expected: All pods should be in Running state (1/1 Ready)
# Note: uploader may be CrashLoopBackOff if app config issues exist
```

### 2.2 Check Pod Logs

```bash
# Check auth service logs
kubectl logs -n prod deployment/auth --tail=50

# Check analytics service logs
kubectl logs -n prod deployment/analytics --tail=50

# Check processor service logs
kubectl logs -n prod deployment/processor --tail=50

# Check gateway service logs
kubectl logs -n prod deployment/gateway --tail=50

# Check uploader service logs (if in error state)
kubectl logs -n prod deployment/uploader --tail=100

# Check frontend logs
kubectl logs -n prod deployment/frontend --tail=50
```

### 2.3 Describe Pods for Issues

```bash
# Get detailed info on a failing pod
$FAILED_POD = kubectl get pods -n prod -o jsonpath='{.items[?(@.status.phase!="Running")].metadata.name}' | Select-Object -First 1
kubectl describe pod -n prod $FAILED_POD
```

## 3. Service and Networking Testing

### 3.1 Verify Services

```bash
# List all services in prod namespace
kubectl get svc -n prod

# List all services in monitoring namespace
kubectl get svc -n monitoring

# Expected: Each service should be accessible (ClusterIP or LoadBalancer)
```

### 3.2 Test Service Connectivity (Internal)

```bash
# Get a pod to use for testing
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'

# Test connectivity to auth service
kubectl exec -n prod $TEST_POD -- curl -v http://auth.prod.svc.cluster.local:8000/health

# Test connectivity to analytics service
kubectl exec -n prod $TEST_POD -- curl -v http://analytics.prod.svc.cluster.local:8000/health

# Test connectivity to processor service
kubectl exec -n prod $TEST_POD -- curl -v http://processor.prod.svc.cluster.local:8000/health
```

### 3.3 Test LoadBalancer Services

```bash
# Get Grafana LoadBalancer URL
$GRAFANA_URL = kubectl get svc grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Grafana URL: http://$GRAFANA_URL:3000"

# Get Prometheus LoadBalancer URL
$PROMETHEUS_URL = kubectl get svc prometheus-lb -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Prometheus URL: http://$PROMETHEUS_URL:9090"

# Test connectivity (from your local machine)
curl "http://$PROMETHEUS_URL:9090/-/healthy"
curl "http://$GRAFANA_URL:3000/api/health"
```

## 4. Prometheus Testing

### 4.1 Verify Prometheus Deployment

```bash
# Check Prometheus pod
kubectl get pods -n monitoring -l app=prometheus

# Expected: 1/1 Running
```

### 4.2 Access Prometheus

```bash
# Method 1: LoadBalancer (external)
# Open browser to: http://k8s-monitori-promethe-c70c64809c-3207c6ab19cbd45a.elb.us-east-1.amazonaws.com:9090

# Method 2: Port forward
kubectl port-forward -n monitoring svc/prometheus 9090:9090

# Then access: http://localhost:9090

# Method 3: Internal (from pod)
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n prod $TEST_POD -- curl http://prometheus.monitoring.svc.cluster.local:9090/-/healthy
```

### 4.3 Verify Prometheus Targets

Navigate to Prometheus UI → Status → Targets

Check that the following targets are showing:

- Kubernetes API servers (should be `UP`)
- Kubernetes nodes (should be `UP`)
- Service pods (should show app endpoints)
- Prometheus itself (should be `UP`)

### 4.4 Test Prometheus Queries

In Prometheus UI, run these queries:

```promql
# Check node CPU usage
node_cpu_seconds_total

# Check pod memory usage
container_memory_usage_bytes

# Check API server request rate
apiserver_request_duration_seconds_bucket

# Check custom app metrics (if exposed on port 8000)
# Look for application-specific metrics
```

## 5. Grafana Testing

### 5.1 Access Grafana

```bash
# Get Grafana LoadBalancer URL
$GRAFANA_URL = kubectl get svc grafana -n monitoring -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
Write-Host "Grafana URL: http://$GRAFANA_URL:3000"

# Login credentials
# Username: admin
# Password: admin123
```

### 5.2 Verify Prometheus Datasource

In Grafana:
1. Navigate to Administration → Data Sources
2. Look for "Prometheus" datasource
3. Click "Test" button
4. Should show "Data source is working"

### 5.3 Verify Dashboards

In Grafana:
1. Navigate to Dashboards
2. Check if any dashboards are available
3. View cluster health and pod metrics

## 6. CloudWatch Testing

### 6.1 Verify Log Groups

```powershell
# List log groups
aws logs describe-log-groups --region us-east-1 --query 'logGroups[*].logGroupName'

# Expected log groups:
# /aws/eks/g3-eks-cluster/applications
# /aws/eks/g3-eks-cluster/cluster
```

### 6.2 Check Log Streams

```powershell
# Get log streams for applications
aws logs describe-log-streams --log-group-name "/aws/eks/g3-eks-cluster/applications" --max-items 10 --region us-east-1

# Get recent logs
aws logs tail "/aws/eks/g3-eks-cluster/applications" --follow --region us-east-1
```

### 6.3 Verify Alarms

```powershell
# List all CloudWatch alarms
aws cloudwatch describe-alarms --region us-east-1 --query 'MetricAlarms[*].[AlarmName,StateValue]' --output table

# Expected alarms:
# - eks-high-cpu-utilization
# - eks-high-memory-utilization

# Check alarm history
aws cloudwatch describe-alarm-history --alarm-name "eks-high-cpu-utilization" --region us-east-1 --max-records 5
```

### 6.4 Check CloudWatch Metrics

```powershell
# List available metrics
aws cloudwatch list-metrics --namespace "AWS/EKS" --region us-east-1

# Get specific metric data (CPU)
aws cloudwatch get-metric-statistics `
  --namespace "AWS/EKS" `
  --metric-name "CPUUtilization" `
  --dimensions Name=ClusterName,Value=g3-eks-cluster `
  --start-time (Get-Date).AddHours(-1).ToUniversalTime().ToString('o') `
  --end-time (Get-Date).ToUniversalTime().ToString('o') `
  --period 300 `
  --statistics Average `
  --region us-east-1
```

## 7. Infrastructure Testing

### 7.1 Verify Terraform State

```bash
cd IaC

# Check Terraform state
terraform show

# List resources
terraform state list

# Expected resources:
# - aws_iam_role (auth-irsa-role, analytics-irsa-role, etc.)
# - aws_iam_role_policy (IRSA policies)
# - aws_cloudwatch_log_group
# - aws_cloudwatch_metric_alarm
# - aws_cloudwatch_dashboard
```

### 7.2 Verify IAM Roles

```powershell
# List all IRSA roles
aws iam list-roles --query "Roles[?contains(RoleName, 'irsa')].RoleName" --region us-east-1

# Check role policies
aws iam list-attached-role-policies --role-name "auth-irsa-role" --region us-east-1

# Get trust relationship for IRSA role
aws iam get-role --role-name "auth-irsa-role" --query 'Role.AssumeRolePolicyDocument' --region us-east-1
```

## 8. EKS Microservices Testing

### 8.1 Auth Service

#### Deployment Info

```bash
# Check deployment status
kubectl get deployment auth -n prod -o wide
kubectl get pods -n prod -l app=auth -o wide
kubectl get svc auth -n prod -o wide

# Expected: 1/1 Running, ClusterIP service on port 8000
```

#### Service URLs

```bash
# Internal URL (from within cluster)
http://auth.prod.svc.cluster.local:8000

# Via Port-Forward
kubectl port-forward -n prod svc/auth 8000:8000 &
# Then: http://localhost:8000
```

#### Test Commands

```bash
# Health check
kubectl exec -n prod deployment/auth -- curl -s http://localhost:8000/health

# Port-forward health check
curl http://localhost:8000/health

# Verify pod has AWS credentials (IRSA)
kubectl exec -n prod deployment/auth -- env | grep -E "AWS_ROLE_ARN|AWS_WEB_IDENTITY_TOKEN_FILE"

# Check pod logs
kubectl logs -n prod deployment/auth --tail=50
```

---

### 8.2 Analytics Service

#### Deployment Info

```bash
# Check deployment status
kubectl get deployment analytics -n prod -o wide
kubectl get pods -n prod -l app=analytics -o wide
kubectl get svc analytics -n prod -o wide

# Expected: 1/1 Running, ClusterIP service on port 8000
```

#### Service URLs

```bash
# Internal URL (from within cluster)
http://analytics.prod.svc.cluster.local:8000

# Via Port-Forward
kubectl port-forward -n prod svc/analytics 8000:8000 &
# Then: http://localhost:8000
```

#### Test Commands

```bash
# Health check
kubectl exec -n prod deployment/analytics -- curl -s http://localhost:8000/health

# Port-forward and test metrics endpoint
curl http://localhost:8000/metrics

# Get analytics data
curl http://localhost:8000/analytics

# Test with video ID
curl http://localhost:8000/analytics?video_id=test-123

# Verify DynamoDB access (IRSA)
kubectl exec -n prod deployment/analytics -- aws dynamodb list-tables --region us-east-1

# Check pod logs
kubectl logs -n prod deployment/analytics --tail=50
```

---

### 8.3 Gateway Service

#### Deployment Info

```bash
# Check deployment status
kubectl get deployment gateway -n prod -o wide
kubectl get pods -n prod -l app=gateway -o wide
kubectl get svc gateway -n prod -o wide

# Expected: 1/1 Running, ClusterIP service on port 8000
```

#### Service URLs

```bash
# Internal URL (from within cluster)
http://gateway.prod.svc.cluster.local:8000

# Via Port-Forward
kubectl port-forward -n prod svc/gateway 8000:8000 &
# Then: http://localhost:8000
```

#### Test Commands

```bash
# Health check
kubectl exec -n prod deployment/gateway -- curl -s http://localhost:8000/health

# Port-forward and test gateway endpoints
curl http://localhost:8000/health

# Test routing to backend services
curl http://localhost:8000/api/auth/status

# Verify IRSA credentials present
kubectl exec -n prod deployment/gateway -- env | grep AWS_ROLE_ARN

# Check pod logs
kubectl logs -n prod deployment/gateway --tail=50
```

---

### 8.4 Processor Service

#### Deployment Info

```bash
# Check deployment status
kubectl get deployment processor -n prod -o wide
kubectl get pods -n prod -l app=processor -o wide
kubectl get svc processor -n prod -o wide

# Expected: 1/1 Running, ClusterIP service on port 8000
```

#### Service URLs

```bash
# Internal URL (from within cluster)
http://processor.prod.svc.cluster.local:8000

# Via Port-Forward
kubectl port-forward -n prod svc/processor 8000:8000 &
# Then: http://localhost:8000
```

#### Test Commands

```bash
# Health check
kubectl exec -n prod deployment/processor -- curl -s http://localhost:8000/health

# Port-forward and check processor status
curl http://localhost:8000/health

# Get processing jobs
curl http://localhost:8000/jobs

# Submit a processing job
curl -X POST http://localhost:8000/process -d '{"video_id":"test-123"}'

# Verify IRSA credentials
kubectl exec -n prod deployment/processor -- env | grep AWS_

# Check pod logs
kubectl logs -n prod deployment/processor --tail=50
```

---

### 8.5 Uploader Service

#### Deployment Info

```bash
# Check deployment status
kubectl get deployment uploader -n prod -o wide
kubectl get pods -n prod -l app=uploader -o wide
kubectl get svc uploader -n prod -o wide

# Expected: 0/1 or 1/1 Running (may be CrashLoopBackOff with app config issues), ClusterIP service on port 8000
```

#### Service URLs

```bash
# Internal URL (from within cluster)
http://uploader.prod.svc.cluster.local:8000

# Via Port-Forward (if pod is running)
kubectl port-forward -n prod svc/uploader 8000:8000 &
# Then: http://localhost:8000
```

#### Test Commands

```bash
# Check if pod is running
kubectl get pods -n prod -l app=uploader

# Health check (if running)
kubectl exec -n prod deployment/uploader -- curl -s http://localhost:8000/health

# Port-forward health check
curl http://localhost:8000/health

# Get available storage
curl http://localhost:8000/storage/info

# Check upload status
curl http://localhost:8000/uploads

# Verify S3 access (IRSA with S3 permissions)
kubectl exec -n prod deployment/uploader -- aws s3 ls

# Verify DynamoDB access for upload tracking
kubectl exec -n prod deployment/uploader -- aws dynamodb describe-table --table-name uploads --region us-east-1

# Check pod logs for errors
kubectl logs -n prod deployment/uploader --tail=100

# If CrashLoopBackOff, check events
kubectl describe pod -n prod $(kubectl get pods -n prod -l app=uploader -o jsonpath='{.items[0].metadata.name}')
```

---

### 8.6 Frontend Service

#### Deployment Info

```bash
# Check deployment status
kubectl get deployment frontend -n prod -o wide
kubectl get pods -n prod -l app=frontend -o wide
kubectl get svc frontend -n prod -o wide

# Expected: 1/1 Running, ClusterIP service on port 80
```

#### Service URLs

```bash
# Internal URL (from within cluster)
http://frontend.prod.svc.cluster.local:80

# Via Port-Forward
kubectl port-forward -n prod svc/frontend 3000:80 &
# Then: http://localhost:3000
```

#### Test Commands

```bash
# Health check
kubectl exec -n prod deployment/frontend -- curl -s http://localhost:80/health

# Port-forward and check if frontend loads
curl http://localhost:3000

# Get frontend assets
curl http://localhost:3000/index.html

# Check API connectivity from frontend
curl http://localhost:3000/api/config

# Verify IRSA credentials present
kubectl exec -n prod deployment/frontend -- env | grep AWS_ROLE_ARN

# Check nginx config
kubectl exec -n prod deployment/frontend -- cat /etc/nginx/nginx.conf

# Check pod logs
kubectl logs -n prod deployment/frontend --tail=50
```

---

## 8.7 Backend Architecture Testing

### 8.7.1 Verify Backend Components

```bash
# Check all backend services are deployed
kubectl get all -n prod -o wide

# Get backend services list
kubectl get svc -n prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.type}{"\n"}{end}'

# Expected services: auth, analytics, gateway, processor, uploader, frontend (all ClusterIP)
```

### 8.7.2 Test Backend Service Ports

```bash
# Verify all backend services expose port 8000
kubectl get svc -n prod -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.ports[0].port}{"\n"}{end}'

# Expected: All services on port 8000 (except frontend on 80)
```

### 8.7.3 Backend Communication Chain

```bash
# Get a pod for testing
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'

# Test complete backend chain
Write-Host "1. Auth Service"
kubectl exec -n prod $TEST_POD -- curl -s http://auth.prod.svc.cluster.local:8000/health | jq .

Write-Host "2. Analytics Service"
kubectl exec -n prod $TEST_POD -- curl -s http://analytics.prod.svc.cluster.local:8000/health | jq .

Write-Host "3. Processor Service"
kubectl exec -n prod $TEST_POD -- curl -s http://processor.prod.svc.cluster.local:8000/health | jq .

Write-Host "4. Uploader Service"
kubectl exec -n prod $TEST_POD -- curl -s http://uploader.prod.svc.cluster.local:8000/health | jq .

Write-Host "5. Gateway Service"
kubectl exec -n prod $TEST_POD -- curl -s http://localhost:8000/health | jq .
```

### 8.7.4 Backend Resource Monitoring

```bash
# Monitor backend services resource usage
kubectl top pods -n prod --containers

# Check backend services' memory usage
kubectl get pods -n prod -o custom-columns=NAME:.metadata.name,MEMORY:.status.containerStatuses[0].lastState.running.startedAt

# Get CPU and memory requests/limits
kubectl get pods -n prod -o custom-columns=NAME:.metadata.name,CPU_REQ:.spec.containers[0].resources.requests.cpu,MEM_REQ:.spec.containers[0].resources.requests.memory,CPU_LIM:.spec.containers[0].resources.limits.cpu,MEM_LIM:.spec.containers[0].resources.limits.memory
```

---

## 8.8 API Gateway Testing

The Gateway service acts as the main API router for all backend requests.

### 8.8.1 Gateway Deployment Verification

```bash
# Verify gateway is running and healthy
kubectl get deployment gateway -n prod -o wide
kubectl get pods -n prod -l app=gateway -o wide
kubectl get svc gateway -n prod -o wide

# Check gateway pod resources
kubectl describe pod -n prod $(kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}')
```

### 8.8.2 Gateway Health Endpoints

```bash
# Basic health check
kubectl exec -n prod deployment/gateway -- curl -s http://localhost:8000/health

# Port-forward to test from local machine
kubectl port-forward -n prod svc/gateway 8000:8000 &

# Local health check
curl http://localhost:8000/health

# Verbose health check
curl -v http://localhost:8000/health
```

### 8.8.3 Gateway Routing Tests

```bash
# Test routing to each backend service

# Route to auth service
curl -X GET http://localhost:8000/api/auth/health

# Route to analytics service
curl -X GET http://localhost:8000/api/analytics/health

# Route to processor service
curl -X GET http://localhost:8000/api/processor/health

# Route to uploader service
curl -X GET http://localhost:8000/api/uploader/health

# Get gateway version/info
curl http://localhost:8000/info

# List available routes
curl http://localhost:8000/routes
```

### 8.8.4 Gateway Authentication Tests

```bash
# Test unauthenticated request (should fail for protected routes)
curl http://localhost:8000/api/analytics/data

# Generate auth token
$TOKEN = $(curl -X POST http://localhost:8000/api/auth/token -d '{"username":"test","password":"test"}' | jq -r '.token')

# Test authenticated request
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/analytics/data

# Test token validation
curl -X POST http://localhost:8000/api/auth/validate -H "Authorization: Bearer $TOKEN"

# Test token refresh
curl -X POST http://localhost:8000/api/auth/refresh -H "Authorization: Bearer $TOKEN"
```

### 8.8.5 Gateway Load Balancing

```bash
# Send multiple requests to test load balancing
for i in {1..10}; do 
  echo "Request $i"
  curl http://localhost:8000/health
done

# Monitor which backend pod handles requests
kubectl logs -n prod deployment/gateway --tail=20 -f

# Test with concurrent requests
$jobs = @()
for ($i = 0; $i -lt 10; $i++) {
  $jobs += (curl http://localhost:8000/health -AsJob)
}
$jobs | Wait-Job | Receive-Job
```

### 8.8.6 Gateway Logging and Tracing

```bash
# Get gateway logs
kubectl logs -n prod deployment/gateway --tail=100

# Stream gateway logs in real-time
kubectl logs -n prod deployment/gateway -f

# Get gateway logs with timestamps
kubectl logs -n prod deployment/gateway --tail=50 --timestamps=true

# Filter gateway logs for errors
kubectl logs -n prod deployment/gateway | grep -i error

# Filter gateway logs for request paths
kubectl logs -n prod deployment/gateway | grep -i "GET\|POST\|PUT\|DELETE"
```

### 8.8.7 Gateway Network Policies

```bash
# Verify gateway service network connectivity
kubectl get networkpolicies -n prod

# Test gateway DNS resolution
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n prod $TEST_POD -- nslookup auth.prod.svc.cluster.local
kubectl exec -n prod $TEST_POD -- nslookup analytics.prod.svc.cluster.local

# Verify gateway IRSA access
kubectl exec -n prod deployment/gateway -- env | grep AWS_
```

---

## 8.9 Frontend Testing

### 8.9.1 Frontend Deployment Verification

```bash
# Verify frontend is running
kubectl get deployment frontend -n prod -o wide
kubectl get pods -n prod -l app=frontend -o wide
kubectl get svc frontend -n prod -o wide

# Check frontend pod details
kubectl describe pod -n prod $(kubectl get pods -n prod -l app=frontend -o jsonpath='{.items[0].metadata.name}')
```

### 8.9.2 Frontend Nginx Configuration

```bash
# Verify Nginx is serving content
kubectl exec -n prod deployment/frontend -- curl -s http://localhost:80 | head -20

# Check Nginx configuration
kubectl exec -n prod deployment/frontend -- cat /etc/nginx/nginx.conf

# Check Nginx status
kubectl exec -n prod deployment/frontend -- nginx -t

# Verify serving static assets
kubectl exec -n prod deployment/frontend -- curl -s http://localhost:80/index.html | head -10
```

### 8.9.3 Frontend Port-Forward Access

```bash
# Port-forward to frontend
kubectl port-forward -n prod svc/frontend 3000:80 &

# Access frontend locally
curl http://localhost:3000

# Test specific pages
curl http://localhost:3000/index.html
curl http://localhost:3000/

# Test assets
curl http://localhost:3000/main.jsx
curl http://localhost:3000/index.css

# Get frontend response headers
curl -v http://localhost:3000/
```

### 8.9.4 Frontend API Configuration

```bash
# Check frontend config endpoint
curl http://localhost:3000/config

# Verify API gateway URL configured
curl http://localhost:3000/api/config

# Get frontend environment
curl http://localhost:3000/env
```

### 8.9.5 Frontend Component Testing

```bash
# Test dashboard page
curl http://localhost:3000/dashboard

# Test analytics page
curl http://localhost:3000/analytics

# Test uploads page
curl http://localhost:3000/uploads

# Test navbar component
curl http://localhost:3000/components/navbar

# Get component health
curl http://localhost:3000/health
```

### 8.9.6 Frontend Build Verification

```bash
# Check if frontend is built
kubectl exec -n prod deployment/frontend -- ls -la /usr/share/nginx/html/

# Verify build artifacts exist
kubectl exec -n prod deployment/frontend -- ls -la /usr/share/nginx/html/public/

# Check for common frontend files
kubectl exec -n prod deployment/frontend -- test -f /usr/share/nginx/html/index.html && echo "index.html exists"
kubectl exec -n prod deployment/frontend -- test -f /usr/share/nginx/html/main.jsx && echo "main.jsx exists"
```

### 8.9.7 Frontend Logs

```bash
# Get frontend (Nginx) logs
kubectl logs -n prod deployment/frontend --tail=50

# Stream Nginx logs
kubectl logs -n prod deployment/frontend -f

# Get Nginx access logs
kubectl exec -n prod deployment/frontend -- tail -f /var/log/nginx/access.log

# Get Nginx error logs
kubectl exec -n prod deployment/frontend -- tail -f /var/log/nginx/error.log
```

---

## 10. Service Connectivity Testing

### 10.1 Test All Services Internal Communication

```bash
# Get a running pod to use as test client
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'

# Test connectivity to all services
Write-Host "Testing Auth Service..."
kubectl exec -n prod $TEST_POD -- curl -v http://auth.prod.svc.cluster.local:8000/health

Write-Host "Testing Analytics Service..."
kubectl exec -n prod $TEST_POD -- curl -v http://analytics.prod.svc.cluster.local:8000/health

Write-Host "Testing Processor Service..."
kubectl exec -n prod $TEST_POD -- curl -v http://processor.prod.svc.cluster.local:8000/health

Write-Host "Testing Uploader Service..."
kubectl exec -n prod $TEST_POD -- curl -v http://uploader.prod.svc.cluster.local:8000/health

Write-Host "Testing Frontend Service..."
kubectl exec -n prod $TEST_POD -- curl -v http://frontend.prod.svc.cluster.local:80/health
```

### 10.2 Test DNS Resolution

```bash
# Test DNS resolution from a pod
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'

# Resolve auth service
kubectl exec -n prod $TEST_POD -- nslookup auth.prod.svc.cluster.local

# Resolve analytics service
kubectl exec -n prod $TEST_POD -- nslookup analytics.prod.svc.cluster.local

# Resolve services by short name
kubectl exec -n prod $TEST_POD -- nslookup auth
```

---

## 11. End-to-End Workflow Testing

### 11.1 Full Service Chain Test

```bash
# 1. Authenticate with Auth service
$AUTH_TOKEN = curl -X POST http://localhost:8000/token -d '{"user":"test"}' | jq -r '.token'

# 2. Upload video via Uploader service (if running)
curl -X POST -H "Authorization: Bearer $AUTH_TOKEN" -F "file=@test-video.mp4" http://localhost:8000/upload

# 3. Get upload status from Analytics
curl -H "Authorization: Bearer $AUTH_TOKEN" http://localhost:8000/analytics/uploads

# 4. Check processing status from Processor
curl -H "Authorization: Bearer $AUTH_TOKEN" http://localhost:8000/process/status

# 5. View frontend dashboard
curl http://localhost:3000
```

### 11.2 Load Testing All Services

```bash
# Test Auth service throughput
for i in {1..10}; do curl http://localhost:8000/health & done

# Test Analytics queries
for i in {1..10}; do curl "http://localhost:8000/analytics?video_id=test-$i" & done

# Test Gateway routing
for i in {1..10}; do curl http://localhost:8000/api/health & done

# Wait for all background jobs
wait
```

### 11.3 Verify Service Discovery

```bash
# Check all service endpoints
kubectl get endpoints -n prod

# Verify service selectors are working
kubectl get pods -n prod --show-labels

# Test Kubernetes DNS from pod
$TEST_POD = kubectl get pods -n prod -l app=gateway -o jsonpath='{.items[0].metadata.name}'
kubectl exec -n prod $TEST_POD -- curl -s http://auth.prod:8000/health
```

---

## 12. Health Checks

## 9. Health Checks

### 12.1 Cluster Health

```bash
# Get cluster nodes health
kubectl get nodes -o wide

# Get cluster events
kubectl get events --all-namespaces --sort-by='.lastTimestamp' | tail -20

# Check API server health
kubectl get componentstatuses
```

### 12.2 Pod Health

```bash
# Check for unhealthy pods
kubectl get pods --all-namespaces --field-selector=status.phase!=Running

# Check for pods with warnings
kubectl get events --all-namespaces --field-selector type=Warning

# Get pod resource usage
kubectl top pods -n prod
kubectl top nodes
```

### 12.3 Service Health

```bash
# Check service endpoints
kubectl get endpoints -n prod

# Expected: Each service should have endpoints listed

# Check for services without endpoints
kubectl get svc -n prod -o wide | grep '<none>'
```

## 13. Troubleshooting Commands

### 13.1 Debug Pod Issues

```bash
# Get detailed pod information
kubectl describe pod -n prod <POD_NAME>

# Check pod events
kubectl get events -n prod --sort-by='.lastTimestamp'

# Stream logs
kubectl logs -n prod -f deployment/<SERVICE>

# Execute into pod for debugging
kubectl exec -it -n prod <POD_NAME> -- /bin/sh
```

### 13.2 Debug Service Issues

```bash
# Check service selector matching
kubectl get pods -n prod -L app

# Verify service endpoints
kubectl get endpoints -n prod <SERVICE_NAME>

# Test DNS resolution
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup <SERVICE_NAME>.prod.svc.cluster.local
```

### 13.3 Debug IRSA Issues

```bash
# Check OIDC provider configuration
aws iam list-open-id-connect-providers

# Verify IRSA role trust policy
aws iam get-role --role-name <IRSA_ROLE_NAME> --query 'Role.AssumeRolePolicyDocument'

# Check service account annotation
kubectl get sa -n prod <SERVICE_ACCOUNT> -o yaml | grep role-arn
```

### 13.4 Debug LoadBalancer Issues

```powershell
# Get LoadBalancer details
$LB_NAME = kubectl get svc prometheus-lb -n monitoring -o jsonpath='{.metadata.annotations.service\.beta\.kubernetes\.io/aws-load-balancer-name}'
aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(LoadBalancerName, '$LB_NAME')]"

# Check target health
$LB_ARN = (aws elbv2 describe-load-balancers --query "LoadBalancers[?contains(DNSName, 'k8s-monitori-promethe')].LoadBalancerArn" --output text)
$TG_ARN = (aws elbv2 describe-target-groups --load-balancer-arn $LB_ARN --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 describe-target-health --target-group-arn $TG_ARN --output table
```

## 14. Performance Testing

### 14.1 Load Generation

```bash
# Port-forward to a service
kubectl port-forward -n prod svc/gateway 8000:8000 &

# Use Apache Bench (if installed)
ab -n 1000 -c 10 http://localhost:8000/health

# Alternative: Use curl in a loop
for i in {1..100}; do curl http://localhost:8000/health & done
```

### 14.2 Resource Monitoring

```bash
# Watch pod resource usage in real-time
kubectl top pods -n prod --containers

# Watch node resource usage
kubectl top nodes --containers

# Get resource requests and limits
kubectl get pods -n prod -o custom-columns=NAME:.metadata.name,CPU_REQ:.spec.containers[0].resources.requests.cpu,CPU_LIMIT:.spec.containers[0].resources.limits.cpu
```

## Checklist

### IRSA & Security
- [ ] All IRSA service accounts have correct annotations
- [ ] All pods have AWS credentials via environment variables
- [ ] IRSA roles have appropriate permissions
- [ ] S3 access working for uploader service
- [ ] Secrets Manager access working for analytics/auth services

### Microservices Health
- [ ] Auth service: 1/1 Running, health check responds
- [ ] Analytics service: 1/1 Running, health check responds, RDS connected
- [ ] Gateway service: 1/1 Running, health check responds, can route to other services
- [ ] Processor service: 1/1 Running, health check responds
- [ ] Uploader service: Running or known config issue, S3 access verified
- [ ] Frontend service: 1/1 Running, nginx serving content

### Service Connectivity
- [ ] All services can communicate internally (DNS resolution working)
- [ ] All services respond to health checks
- [ ] Service-to-service calls work (e.g., gateway to auth)
- [ ] Port-forward to individual services works

### Observability
- [ ] Prometheus is scraping targets (at least 80% UP)
- [ ] Prometheus LoadBalancer has healthy targets (8/8)
- [ ] Prometheus accessible via LoadBalancer URL
- [ ] Grafana can connect to Prometheus datasource
- [ ] Grafana accessible via LoadBalancer URL
- [ ] CloudWatch log groups are receiving logs
- [ ] CloudWatch alarms are in OK state

### Infrastructure
- [ ] LoadBalancers have healthy targets
- [ ] External access to Prometheus and Grafana working
- [ ] IRSA role trust policies correct
- [ ] Terraform state valid and all resources deployed
- [ ] No unresolved events or warnings

## Next Steps

Once all tests pass:
1. Verify application-specific metrics are being collected in Prometheus
2. Configure additional Grafana dashboards for microservices
3. Set up alert notifications for CloudWatch alarms
4. Document runbooks for common issues
5. Schedule regular chaos engineering tests
6. Test uploader service once app config is fixed
7. Configure ingress/API gateway for external access
8. Set up CI/CD pipeline for service deployments
