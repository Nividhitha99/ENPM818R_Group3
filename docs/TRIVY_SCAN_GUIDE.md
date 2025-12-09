# Trivy Security Scan Report - Video Analytics Platform
**Date:** December 7, 2025  
**Scan Tool:** Trivy (Aqua Security)  
**Severity Levels:** HIGH, CRITICAL  
**Services Scanned:** uploader, processor, analytics, auth, gateway, frontend

---

## Prerequisites

### 1. Start Docker Desktop
Before running scans, ensure Docker Desktop is running:
```powershell
# Check Docker status
docker ps

# If not running, start Docker Desktop manually or via command:
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait for Docker to be ready (30-60 seconds)
Start-Sleep -Seconds 30
```

---

## Running Trivy Scans

### Execute Complete Scan
```powershell
# Navigate to video-analytics directory
cd C:\Users\jng05\OneDrive\Documents\repositories\enpm818R\video-analytics

# Run Trivy scans for all services
pwsh scripts/trivy_scan.ps1 -Services uploader,processor,analytics,auth,gateway,frontend

# Or scan individual services
pwsh scripts/trivy_scan.ps1 -Services uploader
pwsh scripts/trivy_scan.ps1 -Services processor
```

### Generate Detailed Reports (JSON format)
```powershell
# Create reports directory
New-Item -ItemType Directory -Force -Path "./trivy-reports"

# Scan each service and save JSON report
$services = @('uploader', 'processor', 'analytics', 'auth', 'gateway', 'frontend')

foreach ($svc in $services) {
    Write-Host "Scanning $svc..." -ForegroundColor Cyan
    
    # Build the image first
    docker compose build $svc
    
    # Run Trivy scan with JSON output
    docker run --rm `
        -v "/var/run/docker.sock:/var/run/docker.sock" `
        aquasec/trivy:latest image `
        --format json `
        --severity HIGH,CRITICAL `
        --output "/tmp/${svc}-trivy-report.json" `
        "video-analytics-${svc}:latest"
    
    # Copy report from container
    docker run --rm `
        -v "/var/run/docker.sock:/var/run/docker.sock" `
        -v "${PWD}/trivy-reports:/reports" `
        aquasec/trivy:latest image `
        --format json `
        --severity HIGH,CRITICAL `
        --ignore-unfixed `
        "video-analytics-${svc}:latest" > "trivy-reports/${svc}-report.json"
}
```

### Generate HTML Reports (for documentation)
```powershell
# Generate HTML reports for easier viewing
foreach ($svc in $services) {
    docker run --rm `
        -v "/var/run/docker.sock:/var/run/docker.sock" `
        -v "${PWD}/trivy-reports:/reports" `
        aquasec/trivy:latest image `
        --format template `
        --template "@contrib/html.tpl" `
        --severity HIGH,CRITICAL `
        --ignore-unfixed `
        "video-analytics-${svc}:latest" > "trivy-reports/${svc}-report.html"
}
```

---

## ECR Scan Settings Verification

### 1. Check ECR Scan Configuration (AWS CLI)
```powershell
# List all ECR repositories
aws ecr describe-repositories --region us-east-1

# Check scan configuration for each service
$ecrRepos = @(
    'uploader-service',
    'processor-service', 
    'analytics-service',
    'auth-service',
    'gateway-service',
    'frontend-service'
)

foreach ($repo in $ecrRepos) {
    Write-Host "`nChecking scan settings for $repo..." -ForegroundColor Green
    
    # Get repository scan configuration
    aws ecr get-repository-scanning-configuration `
        --repository-name $repo `
        --region us-east-1 2>$null
    
    # If above command fails, use describe-repositories
    aws ecr describe-repositories `
        --repository-names $repo `
        --region us-east-1 `
        --query 'repositories[0].imageScanningConfiguration' 2>$null
}
```

### 2. Enable Scan on Push (if not enabled)
```powershell
# Enable scan on push for all repositories
foreach ($repo in $ecrRepos) {
    Write-Host "Enabling scan on push for $repo..." -ForegroundColor Cyan
    
    aws ecr put-image-scanning-configuration `
        --repository-name $repo `
        --image-scanning-configuration scanOnPush=true `
        --region us-east-1
}

# Verify the change
foreach ($repo in $ecrRepos) {
    aws ecr describe-repositories `
        --repository-names $repo `
        --region us-east-1 `
        --query 'repositories[0].imageScanningConfiguration.scanOnPush'
}
```

### 3. Verify in AWS Console
**Manual Steps:**
1. Navigate to **AWS Console** → **ECR** → **Repositories**
2. For each repository (uploader-service, processor-service, etc.):
   - Click on the repository name
   - Check **"Scan on push"** setting in repository details
   - Should show: `Scan on push: Enabled`
3. Click **"Images"** tab to view scan results for pushed images
4. Look for **"Scan status"** column showing scan results

### Screenshot Checklist for Evidence:
- [ ] ECR Repositories list showing all 6 services
- [ ] Individual repository showing "Scan on push: Enabled"
- [ ] Image scan results page (vulnerabilities summary)
- [ ] Scan findings details (HIGH/CRITICAL vulnerabilities)

---

## Expected Scan Results

### Base Image Vulnerabilities
All services use `python:3.11-slim` or `node:18-alpine` as base images.

**Common findings:**
- **Python 3.11-slim**: May have LOW/MEDIUM severity issues in system packages
- **Node 18-alpine**: Generally fewer vulnerabilities due to minimal Alpine base
- **Nginx unprivileged**: Very minimal attack surface

### Service-Specific Considerations

#### 1. Uploader Service
**Potential Issues:**
- `boto3` (AWS SDK) - Keep updated
- File upload libraries

**Mitigation:**
- Regular dependency updates in `requirements.txt`
- S3 bucket policies restrict access

#### 2. Processor Service
**Potential Issues:**
- `ffmpeg` - Check CVEs in system package
- Video processing libraries

**Mitigation:**
- FFmpeg installed from official repos
- Isolated processing environment
- Non-root user execution

#### 3. Analytics Service
**Potential Issues:**
- `boto3` for DynamoDB
- Data processing libraries

**Mitigation:**
- IAM roles limit DynamoDB access (IRSA)
- Read-only operations

#### 4. Auth Service
**Potential Issues:**
- JWT libraries (PyJWT)
- Cryptography packages

**Mitigation:**
- Up-to-date cryptography libraries
- Secure JWT secret management (K8s secrets)

#### 5. Gateway Service
**Potential Issues:**
- FastAPI and dependencies
- HTTP client libraries

**Mitigation:**
- Regular security updates
- Network policies restrict access

#### 6. Frontend
**Potential Issues:**
- Node.js build dependencies
- React and ecosystem packages

**Mitigation:**
- Multi-stage build removes dev dependencies
- Only static assets in final image
- Unprivileged Nginx

---

## Sample Scan Output

### Successful Scan (No Critical Issues)
```
Scanning uploader (video-analytics-uploader:latest)...
2025-12-07T10:30:00.000Z	INFO	Vulnerability scanning is enabled
2025-12-07T10:30:05.000Z	INFO	Detected OS: debian
2025-12-07T10:30:05.000Z	INFO	Detecting Debian vulnerabilities...
2025-12-07T10:30:08.000Z	INFO	Number of language-specific files: 1
2025-12-07T10:30:08.000Z	INFO	Detecting python-pkg vulnerabilities...

Total: 0 (HIGH: 0, CRITICAL: 0)
```

### Scan with Vulnerabilities Found
```
Scanning processor (video-analytics-processor:latest)...
Total: 2 (HIGH: 1, CRITICAL: 1)

┌──────────────┬────────────────┬──────────┬────────┬───────────────────┬───────────────┬─────────────────────┐
│   Library    │ Vulnerability  │ Severity │ Status │ Installed Version │ Fixed Version │        Title        │
├──────────────┼────────────────┼──────────┼────────┼───────────────────┼───────────────┼─────────────────────┤
│ libssl1.1    │ CVE-2023-12345 │ HIGH     │ fixed  │ 1.1.1n-0+deb11u3  │ 1.1.1n-0+...  │ OpenSSL: Buffer...  │
│ python3      │ CVE-2023-67890 │ CRITICAL │ fixed  │ 3.11.2-1          │ 3.11.4-1      │ Python: Code exec.. │
└──────────────┴────────────────┴──────────┴────────┴───────────────────┴───────────────┴─────────────────────┘
```

---

## Remediation Strategies

### 1. Update Base Images
```dockerfile
# Update to latest patch version
FROM python:3.11.7-slim  # Instead of python:3.11-slim

# Or use specific digest for reproducibility
FROM python:3.11-slim@sha256:abc123...
```

### 2. Update Python Dependencies
```bash
# Check for outdated packages
pip list --outdated

# Update requirements.txt
pip install --upgrade boto3 fastapi uvicorn
pip freeze > requirements.txt
```

### 3. Accept Unfixed Vulnerabilities (if necessary)
Create `.trivyignore` file:
```
# Ignore unfixed vulnerabilities in base OS
CVE-2023-12345
CVE-2023-67890

# Reason: No fix available, compensating controls in place
```

### 4. Rebuild and Rescan
```powershell
# Rebuild images with updates
docker compose build --no-cache uploader

# Rescan to verify fixes
pwsh scripts/trivy_scan.ps1 -Services uploader
```

---

## Continuous Scanning Setup

### 1. GitHub Actions Integration (Optional)
Create `.github/workflows/trivy-scan.yml`:
```yaml
name: Trivy Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly scan

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build images
        run: docker compose build
      
      - name: Run Trivy scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'video-analytics-uploader:latest'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### 2. ECR Scan on Push (Automated)
When enabled in ECR:
- **Automatic**: Scans run on every `docker push`
- **Results**: Available in AWS Console within minutes
- **Notifications**: Can set up EventBridge rules for alerts

### 3. Local Pre-commit Hook (Optional)
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "Running Trivy scan on changed services..."
# Scan only changed Dockerfiles
# Fail commit if CRITICAL vulnerabilities found
```

---

## Evidence Collection Checklist

### ✅ Trivy Scan Evidence
- [ ] Terminal output showing scan execution
- [ ] JSON reports saved in `trivy-reports/` directory
- [ ] HTML reports for each service
- [ ] Summary of vulnerabilities (counts by severity)
- [ ] Remediation actions taken (if any)

### ✅ ECR Scan Evidence
- [ ] AWS CLI output showing scan-on-push enabled
- [ ] ECR Console screenshots:
  - Repository list
  - Scan configuration for each repo
  - Recent scan results
  - Vulnerability findings details

### ✅ Documentation
- [ ] List of base images and versions
- [ ] Known vulnerabilities and risk acceptance
- [ ] Update schedule for dependencies
- [ ] Incident response plan for critical CVEs

---

## Quick Commands Reference

```powershell
# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Navigate to project
cd C:\Users\jng05\OneDrive\Documents\repositories\enpm818R\video-analytics

# Run all scans
pwsh scripts/trivy_scan.ps1 -Services uploader,processor,analytics,auth,gateway,frontend

# Check ECR scan settings
aws ecr describe-repositories --region us-east-1 --query 'repositories[*].[repositoryName,imageScanningConfiguration.scanOnPush]' --output table

# Enable ECR scanning for all repos
$repos = @('uploader-service','processor-service','analytics-service','auth-service','gateway-service','frontend-service')
$repos | ForEach-Object { aws ecr put-image-scanning-configuration --repository-name $_ --image-scanning-configuration scanOnPush=true --region us-east-1 }

# Generate scan reports
New-Item -ItemType Directory -Force -Path "./trivy-reports"
```

---

**Next Steps:**
1. Start Docker Desktop
2. Run Trivy scans using the commands above
3. Capture terminal output
4. Check ECR scan configuration
5. Take screenshots of AWS Console
6. Document findings in this report
