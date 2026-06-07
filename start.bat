@echo off
chcp 65001 >nul
title Auralis

echo.
echo ╔══════════════════════════════════════╗
echo ║       Auralis Development           ║
echo ╚══════════════════════════════════════╝
echo.

:: 检查 Python 虚拟环境
if not exist "agent\.venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found
    echo Run: cd agent ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: 检查 node_modules
if not exist "node_modules" (
    echo [ERROR] node_modules not found
    echo Run: npm install
    pause
    exit /b 1
)

:: 启动 Agent（后台）
echo [1/2] Starting Agent...
start /b "" "agent\.venv\Scripts\python.exe" "agent\server.py"

:: 等待 Agent 启动
timeout /t 2 /nobreak >nul

:: 启动 Tauri（前台）
echo [2/2] Starting Tauri...
echo.
npm run tauri dev

:: 停止 Agent
echo.
echo Stopping Agent...
taskkill /f /im python.exe /fi "WINDOWTITLE eq *server.py*" >nul 2>&1
echo Done.
