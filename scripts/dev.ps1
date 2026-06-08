# Auralis Development Startup Script
# Usage: .\scripts\dev.ps1
# Press Ctrl+C to stop

$ErrorActionPreference = "Stop"
$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentDir = Join-Path $rootDir "agent"
$venvPython = Join-Path $agentDir ".venv\Scripts\python.exe"

# Check environment
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python venv not found" -ForegroundColor Red
    Write-Host "  Run: cd agent; python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path (Join-Path $rootDir "node_modules"))) {
    Write-Host "[ERROR] node_modules not found. Run: npm install" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Auralis Development ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Agent will be auto-started/stopped by Tauri" -ForegroundColor Gray
Write-Host ""

# Start Tauri (Agent will be auto-started by Tauri)
Write-Host "Starting Tauri..." -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

Push-Location $rootDir
try {
    npm run tauri dev
} finally {
    Pop-Location
    Write-Host ""
    Write-Host "Tauri stopped" -ForegroundColor Green
}
