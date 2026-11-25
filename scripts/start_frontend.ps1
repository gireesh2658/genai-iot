<#
.SYNOPSIS
    Starts the IoTSynth AI Next.js frontend application (Signal Intelligence Studio).
.DESCRIPTION
    Resolves paths dynamically relative to the script location, checks for an existing listener
    on port 3000, builds production assets automatically if missing, and starts Next.js.
#>

param(
    [switch]$Dev
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendDir = Join-Path $ProjectRoot "frontend"
$FrontendHost = if ($env:FRONTEND_HOST) { $env:FRONTEND_HOST } else { "127.0.0.1" }
$FrontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 3000 }

if (-not (Test-Path (Join-Path $FrontendDir "package.json"))) {
    Write-Error "Frontend package.json not found under '$FrontendDir'."
    exit 1
}

Set-Location -Path $FrontendDir

if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    Write-Error "Frontend node_modules missing under '$FrontendDir'. Run: npm install"
    exit 1
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  IoTSynth AI - Next.js Frontend Launcher" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Frontend Dir : $FrontendDir"

$ExistingListener = Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue
if ($ExistingListener) {
    $OwnerPid = ($ExistingListener | Select-Object -First 1).OwningProcess
    Write-Host "[INFO] Port $FrontendPort is already listening (PID: $OwnerPid)." -ForegroundColor Yellow
    Write-Host "Home         : http://localhost:$FrontendPort/"
    Write-Host "Studio (V2)  : http://localhost:$FrontendPort/studio"
    Write-Host "Quality      : http://localhost:$FrontendPort/quality"
    Write-Host "Anomaly Lab  : http://localhost:$FrontendPort/anomaly"
    exit 0
}

if (-not $Dev) {
    $BuildManifest = Join-Path $FrontendDir ".next\BUILD_ID"
    if (-not (Test-Path $BuildManifest)) {
        Write-Host "[INFO] Production build not found. Running 'npm run build'..." -ForegroundColor Yellow
        npm run build
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Next.js production build failed."
            exit 1
        }
    }
}

Write-Host "Home         : http://localhost:$FrontendPort/"
Write-Host "Studio (V2)  : http://localhost:$FrontendPort/studio"
Write-Host "Quality      : http://localhost:$FrontendPort/quality"
Write-Host "Anomaly Lab  : http://localhost:$FrontendPort/anomaly"
Write-Host "Press Ctrl+C to stop the frontend server.`n"

if ($Dev) {
    npx next dev -H $FrontendHost -p $FrontendPort
} else {
    npm run start -- -H $FrontendHost -p $FrontendPort
}
exit $LASTEXITCODE
