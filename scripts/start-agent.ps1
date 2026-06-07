# Auralis Agent 启动脚本
$ErrorActionPreference = "Stop"
$agentDir = Join-Path $PSScriptRoot "..\agent"
$venvActivate = Join-Path $agentDir ".venv\Scripts\Activate.ps1"

Write-Host "🚀 启动 Auralis Agent..." -ForegroundColor Cyan

if (-not (Test-Path $venvActivate)) {
    Write-Host "❌ 虚拟环境不存在，请先运行: python -m venv agent\.venv" -ForegroundColor Red
    exit 1
}

& $venvActivate
Set-Location $agentDir
python server.py
