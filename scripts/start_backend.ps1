<#
.SYNOPSIS
    Starts the IoTSynth AI FastAPI backend server using the CPU inference environment (.venv).
.DESCRIPTION
    Resolves paths dynamically relative to the script location, checks for an existing listener
    on port 8000, validates required model checkpoints and datasets, and launches uvicorn cleanly.
#>

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BackendPort = if ($env:BACKEND_PORT) { [int]$env:BACKEND_PORT } else { 8000 }
$BackendHost = if ($env:BACKEND_HOST) { $env:BACKEND_HOST } else { "127.0.0.1" }

Set-Location -Path $ProjectRoot

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  IoTSynth AI - FastAPI Backend Launcher" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Project Root : $ProjectRoot"

if (-not (Test-Path $VenvPython)) {
    Write-Error "CPU serving virtual environment not found at '$VenvPython'. Create it with: python -m venv .venv && .\.venv\Scripts\pip.exe install -r requirements.txt"
    exit 1
}

$RequiredFiles = @(
    "backend\main.py",
    "models\ctgan\v2\ctgan_device_aware_v2.pkl",
    "models\ctgan\v1\ctgan_full_v1.pkl",
    "datasets\processed\ciciot2023_preprocessed_sample.parquet"
)

foreach ($rel in $RequiredFiles) {
    $full = Join-Path $ProjectRoot $rel
    if (-not (Test-Path $full)) {
        Write-Error "Missing required runtime file: $full"
        exit 1
    }
}

$ExistingListener = Get-NetTCPConnection -LocalPort $BackendPort -State Listen -ErrorAction SilentlyContinue
if ($ExistingListener) {
    $OwnerPid = ($ExistingListener | Select-Object -First 1).OwningProcess
    Write-Host "[INFO] Port $BackendPort is already listening (PID: $OwnerPid)." -ForegroundColor Yellow
    Write-Host "Backend API  : http://localhost:$BackendPort"
    Write-Host "Swagger Docs : http://localhost:$BackendPort/docs"
    Write-Host "OpenAPI Spec : http://localhost:$BackendPort/openapi.json"
    exit 0
}

Write-Host "Python Env   : $VenvPython (CPU inference runtime)"
Write-Host "Primary Model: ctgan_device_aware_v2 (Baseline: ctgan_full_v1)"
Write-Host "Backend URL  : http://localhost:$BackendPort"
Write-Host "Swagger Docs : http://localhost:$BackendPort/docs"
Write-Host "OpenAPI JSON : http://localhost:$BackendPort/openapi.json"
Write-Host "Press Ctrl+C to stop the backend server.`n"

& $VenvPython -B -m uvicorn backend.main:app --host $BackendHost --port $BackendPort
exit $LASTEXITCODE
