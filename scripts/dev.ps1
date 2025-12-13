Param(
  [Parameter(Position=0)]
  [ValidateSet("init","check","fix","test","type","lint","fmt","context","clean")]
  [string]$Command = "check"
)

$ErrorActionPreference = "Stop"

$VenvDir = ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"
$Pip = Join-Path $VenvDir "Scripts\pip.exe"

function Ensure-Venv {
  if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
  }
}

function Install-Deps {
  & $Python -m pip install -U pip
  & $Pip install -r requirements.txt -r requirements-dev.txt
}

function Ensure-Artifacts {
  New-Item -ItemType Directory -Force -Path "artifacts\context" | Out-Null
}

switch ($Command) {
  "init" {
    Ensure-Venv
    Install-Deps
  }
  "fmt" {
    Ensure-Venv
    & $Python -m ruff format .
  }
  "lint" {
    Ensure-Venv
    & $Python -m ruff check .
  }
  "type" {
    Ensure-Venv
    & $Python -m mypy .
  }
  "test" {
    Ensure-Venv
    & $Python -m pytest -q
  }
  "fix" {
    Ensure-Venv
    & $Python -m ruff format .
    & $Python -m ruff check . --fix
  }
  "context" {
    Ensure-Venv
    Ensure-Artifacts
    try { tree /F > artifacts\context\tree.txt } catch {}
    try {
      git rev-parse HEAD > artifacts\context\git_commit.txt
      git status --porcelain=v1 > artifacts\context\git_status.txt
    } catch {}
    & $Python scripts\export_context.py --out artifacts\context\context.md
  }
  "check" {
    Ensure-Venv
    powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 context
    & $Python -m ruff format --check .
    & $Python -m ruff check .
    & $Python -m mypy .
    & $Python -m pytest -q
  }
  "clean" {
    Remove-Item -Recurse -Force artifacts -ErrorAction SilentlyContinue
  }
}
