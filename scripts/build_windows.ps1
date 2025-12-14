<#
Build Windows executables using PyInstaller.

Creates (or reuses) a virtual environment, installs PyInstaller, then builds two onedir executables:
- 3579-paper from src/app/paper_entry.py
- 3579-live  from src/app/live_entry.py

Outputs:
- dist/ (final artifacts)
- build/ (PyInstaller workpath)

Usage:
  powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1

Optional parameters:
  -VenvPath .venv
#>

[CmdletBinding()]
param(
  [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

function Get-VenvPython([string]$path) {
  return Join-Path $path "Scripts\\python.exe"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".."))
Set-Location $repoRoot

$venvPython = Get-VenvPython $VenvPath

if (-not (Test-Path $venvPython)) {
  Write-Host "Creating venv at $VenvPath..."
  python -m venv $VenvPath
}

$venvPython = Get-VenvPython $VenvPath

Write-Host "Using Python: $venvPython"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install --upgrade pyinstaller

# Ensure output directories exist
New-Item -ItemType Directory -Force -Path "dist" | Out-Null
New-Item -ItemType Directory -Force -Path "build" | Out-Null

# Build paper executable
& $venvPython -m PyInstaller `
  --noconfirm `
  --onedir `
  --name "3579-paper" `
  --distpath "dist" `
  --workpath "build" `
  "src/app/paper_entry.py"

# Build live executable
& $venvPython -m PyInstaller `
  --noconfirm `
  --onedir `
  --name "3579-live" `
  --distpath "dist" `
  --workpath "build" `
  "src/app/live_entry.py"

Write-Host "Build complete. See dist/ for artifacts."
