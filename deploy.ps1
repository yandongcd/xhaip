# xhaip v1.0 — 一键部署 (Windows PowerShell)
# Usage: .\deploy.ps1
#   -Start     启动服务 (默认)
#   -Stop      停止服务
#   -Restart   重启服务
#   -Status    查看状态
#   -Port 8769 指定端口

param(
    [switch]$Start,
    [switch]$Stop,
    [switch]$Restart,
    [switch]$Status,
    [int]$Port = 8769,
    [string]$HostAddr = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$PyModule = "haip.web_server:app"
$Url = "http://127.0.0.1:${Port}"

function Get-ServerPid {
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        return $conn.OwningProcess
    } catch { return $null }
}

function Stop-Server {
    $svr_pid = Get-ServerPid
    if ($svr_pid -and $svr_pid -ne 0) {
        Write-Host "Stopping xhaip (PID: $svr_pid)..." -ForegroundColor Yellow
        Stop-Process -Id $svr_pid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "Stopped." -ForegroundColor Green
    } else {
        Write-Host "xhaip not running on port $Port" -ForegroundColor Gray
    }
}

function Start-Server {
    $svr_pid = Get-ServerPid
    if ($svr_pid -and $svr_pid -ne 0) {
        Write-Host "xhaip already running on port $Port (PID: $svr_pid)" -ForegroundColor Yellow
        return
    }

    Write-Host "=== xhaip v1.0 — Hospital AI Platform ===" -ForegroundColor Cyan
    Write-Host "Starting server..." -ForegroundColor Cyan

    # Startup validation
    Write-Host "  [1/3] Validating Python environment..."
    $pyVer = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Python not found" -ForegroundColor Red
        exit 1
    }
    Write-Host "         $pyVer"

    Write-Host "  [2/3] Checking dependencies..."
    $deps = python -c "import fastapi,uvicorn,yaml; print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Missing dependencies. Run: pip install fastapi uvicorn pyyaml" -ForegroundColor Red
        exit 1
    }
    Write-Host "         Dependencies OK"

    Write-Host "  [3/3] Loading agents + TOGAF validation..."
    $check = python -c @"
import sys; sys.path.insert(0, 'packages/haip-core'); sys.path.insert(0, 'packages/haip-hospital')
from haip.agent import load_from_dir, list_all
load_from_dir('packages/haip-hospital/agents/definitions')
agents = list_all()
from haip.togaf.validator import validate_all
reports = validate_all()
passed = sum(1 for r in reports if r.passed)
print(f'{len(agents)}/{passed}')
"@ 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Validation failed, continuing anyway" -ForegroundColor Yellow
        Write-Host $check
    } else {
        Write-Host "         Agents: $check (loaded/passed)" -ForegroundColor Green
    }

    # Launch
    Write-Host ""
    Write-Host "Launching on ${HostAddr}:${Port}..." -ForegroundColor Cyan
    $proc = Start-Process -WindowStyle Minimized -FilePath python `
        -ArgumentList "-m", "uvicorn", $PyModule, "--host", $HostAddr, "--port", $Port `
        -WorkingDirectory $Root -PassThru

    # Health check
    Write-Host "Waiting for server..." -NoNewline
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 2
            Write-Host ""
            Write-Host ""
            Write-Host "============================================" -ForegroundColor Green
            Write-Host "  xhaip v1.0 RUNNING" -ForegroundColor Green
            Write-Host "  Dashboard: $Url/dashboard" -ForegroundColor Cyan
            Write-Host "  Process:   $Url/process/<agent-name>" -ForegroundColor Cyan
            Write-Host "  Agent:     $Url/agent/<agent-name>" -ForegroundColor Cyan
            Write-Host "  API:       $Url/api/health" -ForegroundColor Gray
            Write-Host "============================================" -ForegroundColor Green
            return
        } catch {
            Write-Host "." -NoNewline
        }
    }
    Write-Host ""
    Write-Host "WARNING: Server started but health check timed out" -ForegroundColor Yellow
}

function Show-Status {
    $svr_pid = Get-ServerPid
    if ($svr_pid -and $svr_pid -ne 0) {
        Write-Host "xhaip RUNNING on port $Port (PID: $svr_pid)" -ForegroundColor Green
        try {
            $r = Invoke-WebRequest -Uri "$Url/api/health" -UseBasicParsing -TimeoutSec 2
            $data = $r.Content | ConvertFrom-Json
            Write-Host "  Agents loaded: $($data.agents_loaded)"
            Write-Host "  Version: $($data.version)"
            Write-Host "  Dashboard: $Url/dashboard"
        } catch {
            Write-Host "  Health check failed" -ForegroundColor Red
        }
    } else {
        Write-Host "xhaip NOT running on port $Port" -ForegroundColor Gray
    }
}

# ── Main ──

if ($Stop) { Stop-Server; return }
if ($Status) { Show-Status; return }
if ($Restart) { Stop-Server; Start-Sleep -Seconds 2; Start-Server; return }
# Default: start
Start-Server
