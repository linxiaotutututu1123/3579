Param(
  [Parameter(Position=0)]
  [ValidateSet("init","check","fix","test","type","lint","fmt","context","clean")]
  [string]$Command = "check"
)

Stop = "Stop"

 = ".venv"
 = Join-Path  "Scripts\python.exe"
 = Join-Path  "Scripts\pip.exe"

function Ensure-Venv {
  if (-not (Test-Path )) {
    python -m venv 
  }
}

function Install-Deps {
  &  -m pip install -U pip
  &  install -r requirements.txt -r requirements-dev.txt
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
    &  -m ruff format .
  }
  "lint" {
    Ensure-Venv
    &  -m ruff check .
  }
  "type" {
    Ensure-Venv
    &  -m mypy .
  }
  "test" {
    Ensure-Venv
    &  -m pytest -q
  }
  "fix" {
    Ensure-Venv
    &  -m ruff format .
    &  -m ruff check . --fix
  }
  "context" {
    Ensure-Venv
    Ensure-Artifacts
    try { tree /F > artifacts\context\tree.txt } catch {}
    try {
      git rev-parse HEAD > artifacts\context\git_commit.txt
      git status --porcelain=v1 > artifacts\context\git_status.txt
    } catch {}
    &  scripts\export_context.py --out artifacts\context\context.md
  }
  "check" {
    Ensure-Venv
    powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 context
    &  -m ruff format --check .
    &  -m ruff check .
    &  -m mypy .
    &  -m pytest -q
  }
  "clean" {
    Remove-Item -Recurse -Force artifacts -ErrorAction SilentlyContinue
  }
}