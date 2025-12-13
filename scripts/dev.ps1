Param(
  [Parameter(Position=0)]
  [ValidateSet("init","check","fix","test","type","lint","fmt","context","clean")]
  [string]$Task = "check"
)

$ErrorActionPreference = "Stop"

$VenvPath = ".venv"
$Py = Join-Path $VenvPath "Scripts\python.exe"
$Pip = Join-Path $VenvPath "Scripts\pip.exe"

function Ensure-Venv {
  if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
  }
}

function Install-Deps {
  & $Py -m pip install -U pip
  & $Pip install -r requirements.txt -r requirements-dev.txt
}

function Ensure-Artifacts {
  New-Item -ItemType Directory -Force -Path "artifacts\context" | Out-Null
}

switch ($Task) {
  "init" {
    Ensure-Venv
    Install-Deps
  }
  "fmt" {
    Ensure-Venv
    & $Py -m ruff format .
  }
  "lint" {
    Ensure-Venv
    & $Py -m ruff check .
  }
  "type" {
    Ensure-Venv
    & $Py -m mypy .
  }
  "test" {
    Ensure-Venv
    & $Py -m pytest -q
  }
  "fix" {
    Ensure-Venv
    & $Py -m ruff format .
    & $Py -m ruff check . --fix
  }
  "context" {
    Ensure-Venv
    Ensure-Artifacts
    try { tree /F > artifacts\context\tree.txt } catch {}
    try {
      git rev-parse HEAD > artifacts\context\git_commit.txt
      git status --porcelain=v1 > artifacts\context\git_status.txt
    } catch {}
    & $Py scripts\export_context.py --out artifacts\context\context.md
  }
  "check" {
    Ensure-Venv
    powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 context
    & $Py -m ruff format --check .
    & $Py -m ruff check .
    & $Py -m mypy .
    & $Py -m pytest -q
  }
  "clean" {
    Remove-Item -Recurse -Force artifacts -ErrorAction SilentlyContinue
  }
}