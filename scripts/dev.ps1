# Auralis 开发环境一键启动脚本
$ErrorActionPreference = "Stop"
$rootDir = Join-Path $PSScriptRoot ".."

Write-Host "🚀 启动 Auralis 开发环境..." -ForegroundColor Cyan

# 启动 Python Agent（后台）
$agentJob = Start-Job -ScriptBlock {
    Set-Location $using:rootDir
    & ".\agent\.venv\Scripts\Activate.ps1"
    Set-Location ".\agent"
    python server.py
}

Write-Host "✅ Agent 已在后台启动 (Job ID: $($agentJob.Id))" -ForegroundColor Green

# 启动 Tauri
Write-Host "🔧 启动 Tauri..." -ForegroundColor Cyan
Set-Location $rootDir
npm run tauri dev

Stop-Job -Id $agentJob.Id -ErrorAction SilentlyContinue
Remove-Job -Id $agentJob.Id -ErrorAction SilentlyContinue
Write-Host "👋 开发环境已关闭" -ForegroundColor Yellow
