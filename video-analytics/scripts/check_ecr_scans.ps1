# ECR Scan Settings Verification Script
# Checks and enables scan-on-push for all ECR repositories

param(
    [string]$Region = "us-east-1",
    [switch]$EnableScanning = $false
)

$ErrorActionPreference = 'Continue'

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  ECR Scan Settings Verification" -ForegroundColor Cyan
Write-Host "  Region: $Region" -ForegroundColor Cyan
Write-Host "  Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# ECR repository names
$ecrRepos = @(
    'uploader-service',
    'processor-service',
    'analytics-service',
    'auth-service',
    'gateway-service',
    'frontend'
)

Write-Host "[1/3] Checking AWS CLI configuration..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
    Write-Host "✓ AWS Account: $($identity.Account)" -ForegroundColor Green
    Write-Host "✓ User/Role: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI not configured or credentials invalid!" -ForegroundColor Red
    Write-Host "  Run 'aws configure' to set up credentials" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

Write-Host "[2/3] Checking ECR scan configuration..." -ForegroundColor Yellow
Write-Host ""

$scanStatus = @{}

foreach ($repo in $ecrRepos) {
    Write-Host "  Checking $repo..." -ForegroundColor Cyan
    
    try {
        # Get repository details
        $repoInfo = aws ecr describe-repositories `
            --repository-names $repo `
            --region $Region 2>&1 | ConvertFrom-Json
        
        if ($repoInfo.repositories) {
            $scanOnPush = $repoInfo.repositories[0].imageScanningConfiguration.scanOnPush
            $scanStatus[$repo] = $scanOnPush
            
            if ($scanOnPush) {
                Write-Host "    ✓ Scan on push: ENABLED" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Scan on push: DISABLED" -ForegroundColor Red
            }
        }
    } catch {
        Write-Host "    ⚠ Repository not found or access denied" -ForegroundColor Yellow
        $scanStatus[$repo] = $null
    }
}
Write-Host ""

# Enable scanning if requested
if ($EnableScanning) {
    Write-Host "[3/3] Enabling scan-on-push for all repositories..." -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($repo in $ecrRepos) {
        if ($scanStatus[$repo] -eq $false -or $scanStatus[$repo] -eq $null) {
            Write-Host "  Enabling scan for $repo..." -ForegroundColor Cyan
            
            try {
                aws ecr put-image-scanning-configuration `
                    --repository-name $repo `
                    --image-scanning-configuration scanOnPush=true `
                    --region $Region 2>&1 | Out-Null
                
                Write-Host "    ✓ Enabled successfully" -ForegroundColor Green
                $scanStatus[$repo] = $true
            } catch {
                Write-Host "    ✗ Failed to enable: $_" -ForegroundColor Red
            }
        } else {
            Write-Host "  $repo - Already enabled" -ForegroundColor Gray
        }
    }
    Write-Host ""
} else {
    Write-Host "[3/3] Scan status check complete (use -EnableScanning to enable)" -ForegroundColor Yellow
    Write-Host ""
}

# Generate summary
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                    SUMMARY" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$enabledCount = ($scanStatus.Values | Where-Object { $_ -eq $true }).Count
$disabledCount = ($scanStatus.Values | Where-Object { $_ -eq $false }).Count
$unknownCount = ($scanStatus.Values | Where-Object { $_ -eq $null }).Count

Write-Host "Repositories checked: $($ecrRepos.Count)" -ForegroundColor White
Write-Host "  ✓ Scan enabled:  $enabledCount" -ForegroundColor Green
Write-Host "  ✗ Scan disabled: $disabledCount" -ForegroundColor $(if($disabledCount -gt 0){"Red"}else{"Gray"})
Write-Host "  ? Unknown:       $unknownCount" -ForegroundColor $(if($unknownCount -gt 0){"Yellow"}else{"Gray"})
Write-Host ""

# Detailed table
Write-Host "Detailed Status:" -ForegroundColor White
Write-Host "┌─────────────────────────┬───────────────────┐" -ForegroundColor Gray
Write-Host "│ Repository              │ Scan on Push      │" -ForegroundColor Gray
Write-Host "├─────────────────────────┼───────────────────┤" -ForegroundColor Gray

foreach ($repo in $ecrRepos) {
    $status = $scanStatus[$repo]
    $statusText = switch ($status) {
        $true { "✓ ENABLED " }
        $false { "✗ DISABLED" }
        $null { "? UNKNOWN " }
    }
    $color = switch ($status) {
        $true { "Green" }
        $false { "Red" }
        $null { "Yellow" }
    }
    
    Write-Host "│ " -NoNewline -ForegroundColor Gray
    Write-Host "$($repo.PadRight(23))" -NoNewline -ForegroundColor White
    Write-Host " │ " -NoNewline -ForegroundColor Gray
    Write-Host "$statusText" -NoNewline -ForegroundColor $color
    Write-Host "         │" -ForegroundColor Gray
}

Write-Host "└─────────────────────────┴───────────────────┘" -ForegroundColor Gray
Write-Host ""

# Recommendations
if ($disabledCount -gt 0) {
    Write-Host "⚠️  RECOMMENDATION:" -ForegroundColor Yellow
    Write-Host "   Run this script with -EnableScanning flag to enable scan-on-push" -ForegroundColor Yellow
    Write-Host "   Command: pwsh check_ecr_scans.ps1 -EnableScanning" -ForegroundColor Cyan
    Write-Host ""
}

if ($enabledCount -eq $ecrRepos.Count) {
    Write-Host "✅ All repositories have scan-on-push enabled!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor White
    Write-Host "  1. Push an image to trigger automatic scan" -ForegroundColor Gray
    Write-Host "  2. Check scan results in AWS Console: ECR → Repository → Images" -ForegroundColor Gray
    Write-Host "  3. Review vulnerabilities and remediate as needed" -ForegroundColor Gray
    Write-Host ""
}

# Output AWS Console URLs for convenience
Write-Host "AWS Console Links:" -ForegroundColor White
Write-Host "  ECR Repositories: https://console.aws.amazon.com/ecr/repositories?region=$Region" -ForegroundColor Cyan

foreach ($repo in $ecrRepos) {
    Write-Host "  $repo`: https://console.aws.amazon.com/ecr/repositories/private/385046010615/$repo/?region=$Region" -ForegroundColor Gray
}
Write-Host ""

# Exit code
if ($disabledCount -gt 0 -and -not $EnableScanning) {
    exit 1
} else {
    exit 0
}
