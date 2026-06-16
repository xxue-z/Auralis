@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   Auralis Local Build
echo ========================================
echo.

PowerShell -ExecutionPolicy RemoteSigned -NoProfile -File "%~dp0build.ps1" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Build failed
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Build complete!
pause
