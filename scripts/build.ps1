# Auralis Local Build Script
# Usage: .\scripts\build.ps1
# Builds Tauri installer with bundled Python Agent

param(
    [switch]$SkipAgentBuild,
    [string]$Version
)

$ErrorActionPreference = "Stop"
$rootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$agentDir = Join-Path $rootDir "agent"
$tauriDir = Join-Path $rootDir "src-tauri"
$agentDist = Join-Path $agentDir "dist"
$agentExe = Join-Path $agentDist "auralis-agent.exe"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Auralis Local Build" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# -- 1. Check prerequisites ---------------------------
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

$hasErrors = $false

$npmPath = (Get-Command npm -ErrorAction SilentlyContinue).Source
if (-not $npmPath) {
    Write-Host "  [X] npm not found" -ForegroundColor Red
    $hasErrors = $true
} else {
    Write-Host "  [v] npm: $npmPath" -ForegroundColor Green
}

$cargoPath = (Get-Command cargo -ErrorAction SilentlyContinue).Source
if (-not $cargoPath) {
    Write-Host "  [X] cargo not found" -ForegroundColor Red
    $hasErrors = $true
} else {
    Write-Host "  [v] cargo: $cargoPath" -ForegroundColor Green
}

$venvPython = Join-Path $agentDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  [X] Python venv not found: $venvPython" -ForegroundColor Red
    Write-Host "       Run: cd agent; python -m venv .venv" -ForegroundColor Yellow
    $hasErrors = $true
} else {
    Write-Host "  [v] Python venv: $venvPython" -ForegroundColor Green
}

if (-not (Test-Path (Join-Path $rootDir "node_modules"))) {
    Write-Host "  [X] node_modules missing, running npm ci..." -ForegroundColor Yellow
    Push-Location $rootDir
    try {
        npm ci
    } finally {
        Pop-Location
    }
    Write-Host "  [v] node_modules installed" -ForegroundColor Green
} else {
    Write-Host "  [v] node_modules" -ForegroundColor Green
}

if ($hasErrors) { exit 1 }

# -- 2. Build Python agent with PyInstaller -----------
if (-not $SkipAgentBuild) {
    Write-Host ""
    Write-Host "[2/5] Building Python agent (PyInstaller)..." -ForegroundColor Yellow

    Push-Location $agentDir
    try {
        Write-Host "  Installing Python deps..." -ForegroundColor Gray
        & $venvPython -m pip install -r requirements.txt --quiet
        if ($LASTEXITCODE -ne 0) { throw "pip install failed" }

        & $venvPython -m pip install pyinstaller --quiet
        if ($LASTEXITCODE -ne 0) { throw "pyinstaller install failed" }

        if (-not (Test-Path "dist")) {
            New-Item -ItemType Directory -Path "dist" -Force | Out-Null
        }

        Write-Host "  Running PyInstaller..." -ForegroundColor Gray
        & $venvPython -m PyInstaller --onefile --name auralis-agent --distpath dist server.py
        if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

        if (-not (Test-Path $agentExe)) {
            throw "Agent exe not found: $agentExe"
        }
        Write-Host "  [v] Agent exe: $agentExe" -ForegroundColor Green
    } catch {
        Write-Host "  [X] $_" -ForegroundColor Red
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "[2/5] Skipping agent build (-SkipAgentBuild)" -ForegroundColor Yellow
    if (-not (Test-Path $agentExe)) {
        Write-Host "  [X] Agent exe not found: $agentExe" -ForegroundColor Red
        exit 1
    }
}

# -- 3. Build frontend --------------------------------
Write-Host ""
Write-Host "[3/5] Building frontend..." -ForegroundColor Yellow

Push-Location $rootDir
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
    Write-Host "  [v] Frontend built" -ForegroundColor Green
} catch {
    Write-Host "  [X] $_" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# -- 4. Build Tauri installer with bundled agent -------
Write-Host ""
Write-Host "[4/5] Building Tauri installer..." -ForegroundColor Yellow

Push-Location $rootDir
try {
    $tauriConfig = Join-Path $tauriDir "tauri.conf.json"
    $cargoConfig = Join-Path $tauriDir "Cargo.toml"
    $configBackup = Join-Path $tauriDir "tauri.conf.json.bak"
    Copy-Item $tauriConfig $configBackup -Force

    # inject version
    if ($Version) {
        Write-Host "  Setting version: $Version" -ForegroundColor Gray
        & node (Join-Path $PSScriptRoot "inject-version.js") $Version
        if ($LASTEXITCODE -ne 0) { throw "Version injection failed" }
    }

    # inject agent resource
    $configData = Get-Content $tauriConfig -Raw | ConvertFrom-Json
    $configData.bundle.resources = @{
        "../agent/dist/auralis-agent.exe" = "agent/auralis-agent.exe"
    }
    $configData | ConvertTo-Json -Depth 10 | Set-Content $tauriConfig -Encoding UTF8

    npm run tauri build
    if ($LASTEXITCODE -ne 0) { throw "Tauri build failed" }
    Write-Host "  [v] Tauri build complete" -ForegroundColor Green
} catch {
    Write-Host "  [X] $_" -ForegroundColor Red
    exit 1
} finally {
    if (Test-Path $configBackup) { Copy-Item $configBackup $tauriConfig -Force; Remove-Item $configBackup -Force }
    Pop-Location
}

# -- 5. Show build artifacts --------------------------
Write-Host ""
Write-Host "[5/5] Build artifacts..." -ForegroundColor Yellow

$msiFiles = Get-ChildItem -Path (Join-Path $tauriDir "target\release\bundle\msi\*.msi") -ErrorAction SilentlyContinue
$nsisFiles = Get-ChildItem -Path (Join-Path $tauriDir "target\release\bundle\nsis\*.exe") -ErrorAction SilentlyContinue

if ($msiFiles) {
    foreach ($f in $msiFiles) {
        Write-Host "  [MSI] $($f.FullName)" -ForegroundColor Green
    }
}
if ($nsisFiles) {
    foreach ($f in $nsisFiles) {
        Write-Host "  [NSIS] $($f.FullName)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Build complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
