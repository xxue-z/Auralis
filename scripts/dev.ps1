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

# 1. Start Python Agent (background process)
Write-Host "[1/2] Starting Agent (ws://127.0.0.1:9527)..." -ForegroundColor Cyan
$agentProcess = Start-Process -FilePath $venvPython -ArgumentList "server.py" `
    -WorkingDirectory $agentDir `
    -WindowStyle Hidden `
    -PassThru

Write-Host "  Agent PID: $($agentProcess.Id)" -ForegroundColor Gray

# Wait for Agent to start
Start-Sleep -Seconds 2

# 2. Start Tauri (foreground)
Write-Host "[2/2] Starting Tauri..." -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

try {
    Push-Location $rootDir
    npm run tauri dev
} finally {
    # 3. Cleanup: stop Agent process
    Pop-Location
    if (-not $agentProcess.HasExited) {
        Write-Host ""
        Write-Host "Stopping Agent..." -ForegroundColor Yellow
        Stop-Process -Id $agentProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Done." -ForegroundColor Green
}
