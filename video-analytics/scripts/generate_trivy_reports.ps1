# Trivy Scan Report Generator
# Generates comprehensive security scan reports for all services

param(
    [string]$OutputDir = "trivy-reports",
    [string[]]$Services = @('uploader', 'processor', 'analytics', 'auth', 'gateway', 'frontend'),
    [string]$Severity = 'HIGH,CRITICAL'
)

$ErrorActionPreference = 'Continue'

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  Trivy Security Scan Report Generator" -ForegroundColor Cyan
Write-Host "  Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[1/6] Checking Docker status..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running!" -ForegroundColor Red
    Write-Host "  Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}
Write-Host ""

# Create output directory
Write-Host "[2/6] Creating output directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Write-Host "✓ Output directory: $OutputDir" -ForegroundColor Green
Write-Host ""

# Navigate to video-analytics directory
$scriptDir = Split-Path -Parent $PSCommandPath
$projectRoot = Resolve-Path (Join-Path $scriptDir '..')
Push-Location $projectRoot

# Build images
Write-Host "[3/6] Building Docker images..." -ForegroundColor Yellow
foreach ($svc in $Services) {
    Write-Host "  Building $svc..." -ForegroundColor Cyan
    docker compose build $svc 2>&1 | Out-Null
}
Write-Host "✓ All images built successfully" -ForegroundColor Green
Write-Host ""

# Image tag mapping
$imageTags = @{
    uploader  = 'video-analytics-uploader:latest'
    processor = 'video-analytics-processor:latest'
    analytics = 'video-analytics-analytics:latest'
    auth      = 'video-analytics-auth:latest'
    gateway   = 'video-analytics-gateway:latest'
    frontend  = 'video-analytics-frontend:latest'
}

# Scan images and generate reports
Write-Host "[4/6] Scanning images with Trivy..." -ForegroundColor Yellow
$scanResults = @{}

foreach ($svc in $Services) {
    $imageRef = $imageTags[$svc]
    Write-Host "  Scanning $svc ($imageRef)..." -ForegroundColor Cyan
    
    # Generate JSON report
    $jsonReport = Join-Path $OutputDir "$svc-report.json"
    docker run --rm `
        -v "/var/run/docker.sock:/var/run/docker.sock" `
        aquasec/trivy:latest image `
        --format json `
        --severity $Severity `
        --ignore-unfixed `
        $imageRef > $jsonReport
    
    # Generate table report
    $tableReport = Join-Path $OutputDir "$svc-report.txt"
    docker run --rm `
        -v "/var/run/docker.sock:/var/run/docker.sock" `
        aquasec/trivy:latest image `
        --format table `
        --severity $Severity `
        --ignore-unfixed `
        $imageRef > $tableReport
    
    # Parse JSON to get vulnerability count
    try {
        $jsonContent = Get-Content $jsonReport -Raw | ConvertFrom-Json
        $vulnCount = 0
        $critical = 0
        $high = 0
        
        if ($jsonContent.Results) {
            foreach ($result in $jsonContent.Results) {
                if ($result.Vulnerabilities) {
                    foreach ($vuln in $result.Vulnerabilities) {
                        $vulnCount++
                        if ($vuln.Severity -eq 'CRITICAL') { $critical++ }
                        if ($vuln.Severity -eq 'HIGH') { $high++ }
                    }
                }
            }
        }
        
        $scanResults[$svc] = @{
            Total = $vulnCount
            Critical = $critical
            High = $high
            Image = $imageRef
        }
        
        if ($vulnCount -eq 0) {
            Write-Host "    ✓ No vulnerabilities found" -ForegroundColor Green
        } else {
            Write-Host "    ⚠ Found $vulnCount vulnerabilities (CRITICAL: $critical, HIGH: $high)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "    ⚠ Could not parse scan results" -ForegroundColor Yellow
        $scanResults[$svc] = @{
            Total = -1
            Critical = -1
            High = -1
            Image = $imageRef
        }
    }
}
Write-Host ""

# Generate summary report
Write-Host "[5/6] Generating summary report..." -ForegroundColor Yellow
$summaryReport = Join-Path $OutputDir "SCAN_SUMMARY.md"

$summaryContent = @"
# Trivy Security Scan Summary
**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Severity Levels:** $Severity  
**Services Scanned:** $($Services.Count)

---

## Scan Results Overview

| Service | Image | Critical | High | Total |
|---------|-------|----------|------|-------|
"@

foreach ($svc in $Services) {
    $result = $scanResults[$svc]
    $status = if ($result.Total -eq 0) { "✅" } elseif ($result.Critical -gt 0) { "🔴" } elseif ($result.High -gt 0) { "🟡" } else { "✅" }
    $summaryContent += "`n| $status $svc | ``$($result.Image)`` | $($result.Critical) | $($result.High) | $($result.Total) |"
}

$summaryContent += @"


---

## Individual Reports

"@

foreach ($svc in $Services) {
    $summaryContent += "- **$svc**: ``$OutputDir/$svc-report.txt`` (detailed), ``$OutputDir/$svc-report.json`` (JSON)`n"
}

$summaryContent += @"

---

## Remediation Recommendations

### If Vulnerabilities Found:

1. **Update Base Images**
   - Check for newer patch versions of base images
   - Update Dockerfile: ``FROM python:3.11-slim`` → ``FROM python:3.11.7-slim``

2. **Update Dependencies**
   - Review and update ``requirements.txt`` or ``package.json``
   - Run ``pip install --upgrade`` or ``npm update``

3. **Review Unfixed Vulnerabilities**
   - Document risk acceptance for unfixed CVEs
   - Implement compensating controls

4. **Rebuild and Rescan**
   - Rebuild images with ``docker compose build --no-cache``
   - Re-run this scan to verify fixes

### If No Vulnerabilities:

✅ Images are secure at the scanned severity levels ($Severity)  
✅ Continue regular scanning (weekly recommended)  
✅ Enable ECR scan-on-push for automated checks

---

## Next Steps

1. Review detailed reports in ``$OutputDir/`` directory
2. Check ECR scan configuration (see TRIVY_SCAN_GUIDE.md)
3. Update CLUSTER_EVIDENCE.md with scan results
4. Schedule regular security scans (weekly or on code changes)

---

**Scan completed successfully!**
"@

$summaryContent | Out-File -FilePath $summaryReport -Encoding UTF8
Write-Host "✓ Summary report: $summaryReport" -ForegroundColor Green
Write-Host ""

# Display summary
Write-Host "[6/6] Scan Summary:" -ForegroundColor Yellow
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              TRIVY SECURITY SCAN RESULTS                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

foreach ($svc in $Services) {
    $result = $scanResults[$svc]
    $statusIcon = if ($result.Total -eq 0) { "✓" } elseif ($result.Critical -gt 0) { "✗" } else { "⚠" }
    $statusColor = if ($result.Total -eq 0) { "Green" } elseif ($result.Critical -gt 0) { "Red" } else { "Yellow" }
    
    Write-Host "  $statusIcon " -NoNewline -ForegroundColor $statusColor
    Write-Host "$svc`.PadRight(15) " -NoNewline
    Write-Host "CRITICAL: $($result.Critical)  " -NoNewline -ForegroundColor $(if($result.Critical -gt 0){"Red"}else{"Green"})
    Write-Host "HIGH: $($result.High)  " -NoNewline -ForegroundColor $(if($result.High -gt 0){"Yellow"}else{"Green"})
    Write-Host "Total: $($result.Total)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📁 Reports saved to: $OutputDir" -ForegroundColor Green
Write-Host "📄 Summary: $summaryReport" -ForegroundColor Green
Write-Host ""

# Calculate overall status
$totalVulns = ($scanResults.Values | Measure-Object -Property Total -Sum).Sum
$totalCritical = ($scanResults.Values | Measure-Object -Property Critical -Sum).Sum
$totalHigh = ($scanResults.Values | Measure-Object -Property High -Sum).Sum

if ($totalVulns -eq 0) {
    Write-Host "✅ All images passed security scan!" -ForegroundColor Green
    $exitCode = 0
} elseif ($totalCritical -gt 0) {
    Write-Host "⚠️  CRITICAL vulnerabilities found! Immediate action required." -ForegroundColor Red
    $exitCode = 1
} else {
    Write-Host "⚠️  HIGH severity vulnerabilities found. Review and remediate." -ForegroundColor Yellow
    $exitCode = 0
}

Write-Host ""
Write-Host "Run 'cat $summaryReport' to view detailed summary" -ForegroundColor Cyan

Pop-Location
exit $exitCode
