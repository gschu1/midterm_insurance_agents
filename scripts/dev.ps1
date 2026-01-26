<#
dev.ps1 — deterministic dev runner for this repo (Windows PowerShell)

Key rule:
- Canonical virtual environment is `.venv/`
- This script does NOT rely on activation; it always calls `.venv\Scripts\python.exe`

Usage:
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task setup
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task doctor
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task streamlit
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task judge
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_code
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_model
  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_hitl
#>

[CmdletBinding()]
param(
    [string]$Task
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$PY = Join-Path $RepoRoot ".venv\Scripts\python.exe"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message"
}

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task setup"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task doctor"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task streamlit"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task judge"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_code"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_model"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_hitl"
}

function Ensure-Venv {
    if (Test-Path $PY) {
        return
    }

    Write-Step "Creating .venv (py -3 -m venv .venv; fallback: python -m venv .venv)"
    $hasPyLauncher = $null -ne (Get-Command py -ErrorAction SilentlyContinue)
    if ($hasPyLauncher) {
        & py -3 -m venv .venv
    } else {
        & python -m venv .venv
    }

    if (!(Test-Path $PY)) {
        throw "Failed to create .venv; expected interpreter not found: $PY"
    }
}

function Setup-Env {
    Ensure-Venv

    Write-Step "Upgrading pip"
    & $PY -m pip install -U pip

    Write-Step "Installing dependencies (requirements.txt, then requirements-ui.txt if present)"
    if (Test-Path (Join-Path $RepoRoot "requirements.txt")) {
        & $PY -m pip install -r requirements.txt
    } else {
        throw "requirements.txt not found in repo root."
    }

    if (Test-Path (Join-Path $RepoRoot "requirements-ui.txt")) {
        & $PY -m pip install -r requirements-ui.txt
    }

    Write-Step "Interpreter + pip"
    & $PY -c "import sys; print(sys.executable)"
    & $PY -m pip --version
}

function Doctor {
    Ensure-Venv

    Write-Step "Doctor"
    Write-Host ("Repo root: " + $RepoRoot)
    Write-Host (".venv exists: " + (Test-Path (Join-Path $RepoRoot ".venv")))
    Write-Host ("Python: " + $PY)

    $imports = @("llama_index", "eval_harness", "streamlit")
    foreach ($m in $imports) {
        Write-Host ""
        Write-Host ("Checking import: " + $m)
        & $PY -c ("import " + $m + "; print('import OK: " + $m + "')")
        if ($LASTEXITCODE -ne 0) {
            throw ("Import failed: " + $m + ". Run setup again: -Task setup")
        }
    }
}

if ([string]::IsNullOrWhiteSpace($Task)) {
    Show-Usage
    exit 2
}

switch ($Task) {
    "setup" {
        Setup-Env
    }
    "doctor" {
        Doctor
    }
    "streamlit" {
        Ensure-Venv
        Write-Step "Starting Streamlit (canonical interpreter, no activation)"
        & $PY -m streamlit run streamlit_app.py
    }
    "judge" {
        Ensure-Venv
        Write-Step "Running midterm judge"
        & $PY .\src\eval\judge.py
    }
    "eval_code" {
        Ensure-Venv
        Write-Step "Running eval harness (code suite, k=1)"
        & $PY -m eval_harness.run --suite code --k 1
    }
    "eval_model" {
        Ensure-Venv
        Write-Step "Running eval harness (model suite, k=1)"
        & $PY -m eval_harness.run --suite model --k 1
    }
    "eval_hitl" {
        Ensure-Venv
        Write-Step "Running eval harness (HITL suite, k=1)"
        & $PY -m eval_harness.run --suite hitl --k 1
    }
    default {
        Write-Host ("Unknown task: " + $Task)
        Show-Usage
        exit 2
    }
}

