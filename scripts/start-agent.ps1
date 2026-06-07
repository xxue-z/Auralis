# Auralis Agent Startup Script
param([switch]$Background)

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentDir = Join-Path $rootDir "agent"
$venvPython = Join-Path $agentDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Python venv not found" -ForegroundColor Red
    Write-Host "  Run: cd agent; python -m venv .venv" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Auralis Agent (ws://127.0.0.1:9527)..." -ForegroundColor Cyan

if ($Background) {
    Start-Process -FilePath $venvPython -ArgumentList "server.py" -WorkingDirectory $agentDir -WindowStyle Hidden
    Write-Host "Agent started in background." -ForegroundColor Green
} else {
    Push-Location $agentDir
    & $venvPython server.py
    Pop-Location
}
