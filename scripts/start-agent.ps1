# Auralis Agent 启动脚本
param([switch]$Background)

$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentDir = Join-Path $rootDir "agent"
$venvPython = Join-Path $agentDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "❌ Python 虚拟环境不存在" -ForegroundColor Red
    Write-Host "   请运行: cd agent && python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

Write-Host "🚀 启动 Auralis Agent (ws://127.0.0.1:9527)..." -ForegroundColor Cyan

if ($Background) {
    # 后台启动（dev.ps1 用）
    Start-Process -FilePath $venvPython -ArgumentList "server.py" -WorkingDirectory $agentDir -WindowStyle Hidden
    Write-Host "✅ Agent 已后台启动" -ForegroundColor Green
} else {
    # 前台启动（单独调试用）
    Push-Location $agentDir
    & $venvPython server.py
    Pop-Location
}
