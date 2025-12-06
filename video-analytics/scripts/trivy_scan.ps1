param(
    [string[]]$Services = @('uploader','processor','analytics','auth','gateway','frontend'),
    [string]$Severity = 'HIGH,CRITICAL'
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$composeDir = Resolve-Path (Join-Path $scriptDir '..')

Push-Location $composeDir

Write-Host "Building images for: $($Services -join ', ')" -ForegroundColor Cyan
# Builds only the requested services to ensure images exist for scanning
docker compose build $Services

# Expected tags from docker compose build for each service
$imageTags = @{
    uploader  = 'video-analytics-uploader:latest'
    processor = 'video-analytics-processor:latest'
    analytics = 'video-analytics-analytics:latest'
    auth      = 'video-analytics-auth:latest'
    gateway   = 'video-analytics-gateway:latest'
    frontend  = 'video-analytics-frontend:latest'
}

foreach ($svc in $Services) {
    $imageRef = $imageTags[$svc]
    if ([string]::IsNullOrWhiteSpace($imageRef)) {
        Write-Warning "Unknown service '$svc'; skipping."
        continue
    }

    Write-Host "Scanning $svc ($imageRef)..." -ForegroundColor Green
    docker run --rm --pull=always `
        -v "/var/run/docker.sock:/var/run/docker.sock" `
        -v "$HOME/.cache/trivy:/root/.cache/trivy" `
        aquasec/trivy:latest image `
        --quiet `
        --severity $Severity `
        --ignore-unfixed `
        --exit-code 1 `
        $imageRef
}

Pop-Location
