# Auralis 开发环境一键启动脚本
# 用法: .\scripts\dev.ps1
# 按 Ctrl+C 停止

$ErrorActionPreference = "Stop"
$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentDir = Join-Path $rootDir "agent"
$venvPython = Join-Path $agentDir ".venv\Scripts\python.exe"

# 检查环境
if (-not (Test-Path $venvPython)) {
    Write-Host "❌ Python 虚拟环境不存在" -ForegroundColor Red
    Write-Host "   请运行: cd agent && python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "node_modules")) {
    Write-Host "❌ node_modules 不存在" -ForegroundColor Red
    Write-Host "   请运行: npm install" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║       Auralis 开发环境               ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 1. 启动 Python Agent（后台进程）
Write-Host "🤖 启动 Agent (ws://127.0.0.1:9527)..." -ForegroundColor Cyan
$agentProcess = Start-Process -FilePath $venvPython -ArgumentList "server.py" `
    -WorkingDirectory $agentDir `
    -WindowStyle Hidden `
    -PassThru

Write-Host "   Agent PID: $($agentProcess.Id)" -ForegroundColor Gray

# 等待 Agent 启动
Start-Sleep -Seconds 2

# 2. 启动 Tauri（前台）
Write-Host "🧚 启动 Tauri..." -ForegroundColor Cyan
Write-Host "   按 Ctrl+C 停止所有服务" -ForegroundColor Yellow
Write-Host ""

try {
    Push-Location $rootDir
    npm run tauri dev
} finally {
    # 3. 清理：停止 Agent 进程
    Pop-Location
    if (-not $agentProcess.HasExited) {
        Write-Host ""
        Write-Host "🛑 停止 Agent..." -ForegroundColor Yellow
        Stop-Process -Id $agentProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "👋 开发环境已关闭" -ForegroundColor Green
}
