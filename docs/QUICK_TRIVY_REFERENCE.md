# Quick Reference: Trivy Scans & ECR Configuration

## Prerequisites
```powershell
# 1. Start Docker Desktop (REQUIRED)
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Start-Sleep -Seconds 30

# 2. Verify Docker is running
docker ps
```

## Option 1: Run Original Trivy Scan Script
```powershell
cd C:\Users\jng05\OneDrive\Documents\repositories\enpm818R\video-analytics

# Scan all services
pwsh scripts/trivy_scan.ps1 -Services uploader,processor,analytics,auth,gateway,frontend

# Scan specific service
pwsh scripts/trivy_scan.ps1 -Services uploader
```

## Option 2: Generate Comprehensive Reports (RECOMMENDED)
```powershell
cd C:\Users\jng05\OneDrive\Documents\repositories\enpm818R\video-analytics

# Generate detailed reports with summary
pwsh scripts/generate_trivy_reports.ps1

# View summary
cat trivy-reports/SCAN_SUMMARY.md

# View individual service report
cat trivy-reports/uploader-report.txt
```

## Check ECR Scan Configuration
```powershell
cd C:\Users\jng05\OneDrive\Documents\repositories\enpm818R\video-analytics

# Check current scan settings
pwsh scripts/check_ecr_scans.ps1

# Enable scan-on-push for all repositories
pwsh scripts/check_ecr_scans.ps1 -EnableScanning
```

## Manual ECR Commands
```powershell
# List all ECR repositories
aws ecr describe-repositories --region us-east-1

# Check scan configuration for specific repo
aws ecr describe-repositories --repository-names uploader-service --region us-east-1 --query 'repositories[0].imageScanningConfiguration'

# Enable scan on push
aws ecr put-image-scanning-configuration --repository-name uploader-service --image-scanning-configuration scanOnPush=true --region us-east-1
```

## Expected Output Structure
```
video-analytics/
├── trivy-reports/
│   ├── SCAN_SUMMARY.md           # Overview of all scans
│   ├── uploader-report.txt       # Human-readable report
│   ├── uploader-report.json      # Machine-readable report
│   ├── processor-report.txt
│   ├── processor-report.json
│   ├── analytics-report.txt
│   ├── analytics-report.json
│   ├── auth-report.txt
│   ├── auth-report.json
│   ├── gateway-report.txt
│   ├── gateway-report.json
│   ├── frontend-report.txt
│   └── frontend-report.json
```

## Capture Evidence (Screenshots)
1. Terminal showing scan execution
2. Scan summary output
3. ECR Console - Repository list
4. ECR Console - Scan on push enabled
5. ECR Console - Scan results for images

## Troubleshooting
```powershell
# If Docker fails to connect
Get-Process "*docker*"
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# If AWS CLI not configured
aws configure

# If Trivy pull fails
docker pull aquasec/trivy:latest

# If scan fails due to missing image
cd video-analytics
docker compose build <service-name>
```
