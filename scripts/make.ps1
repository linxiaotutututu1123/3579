<#
.SYNOPSIS
    3579 Trading System - PowerShell Task Runner
    Windows 上的 Makefile 等效脚本

.DESCRIPTION
    用法: .\scripts\make.ps1 <target>
    
    与 Makefile 完全一致，确保 CI 和本地行为相同

.EXAMPLE
    .\scripts\make.ps1 ci        # 运行完整 CI 检查
    .\scripts\make.ps1 format    # 格式化代码
    .\scripts\make.ps1 test      # 运行测试
#>

param(
    [Parameter(Position=0)]
    [ValidateSet(
        "help", "install", "install-dev",
        "format", "format-check", "lint", "lint-fix", "type", "test", "test-fast",
        "check", "ci",
        "context", "context-dev", "context-debug",
        "build", "build-paper", "build-live",
        "clean"
    )]
    [string]$Target = "help"
)

$ErrorActionPreference = "Stop"

# =============================================================================
# 配置：明确使用 venv 中的 Python，不依赖系统 PATH
# 支持环境变量覆盖：$env:PY=python .\scripts\make.ps1 ci
# =============================================================================
$_PY_DEFAULT = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$_PIP_DEFAULT = Join-Path $PSScriptRoot "..\.venv\Scripts\pip.exe"

# 支持外部覆盖（与 Makefile 的 PY ?= 对齐）
if ($env:PY) {
    $PYTHON = $env:PY
} else {
    $PYTHON = $_PY_DEFAULT
}

if ($env:PIP) {
    $PIP = $env:PIP
} else {
    $PIP = $_PIP_DEFAULT
}

$COV_THRESHOLD = 85

# 验证 Python 存在（友好错误提示）
function Assert-VenvExists {
    if (-not (Test-Path $PYTHON)) {
        Write-Host "ERROR: Python not found at $PYTHON" -ForegroundColor Red
        Write-Host "Run: python -m venv .venv" -ForegroundColor Yellow
        Write-Host "Or override: `$env:PY='python' .\scripts\make.ps1 ci" -ForegroundColor Yellow
        exit 1
    }
}

# =============================================================================
# 函数
# =============================================================================

function Show-Help {
    Write-Host "3579 Trading System - PowerShell Task Runner"
    Write-Host "============================================="
    Write-Host ""
    Write-Host "Usage: .\scripts\make.ps1 <target>"
    Write-Host ""
    Write-Host "Quality Gates:"
    Write-Host "  format       - Format code (ruff format)"
    Write-Host "  lint         - Lint code (ruff check)"
    Write-Host "  type         - Type check (mypy)"
    Write-Host "  test         - Run tests (pytest, 85% coverage gate)"
    Write-Host "  check        - Run all checks without modifying files"
    Write-Host "  ci           - Full CI pipeline"
    Write-Host ""
    Write-Host "Context Export:"
    Write-Host "  context      - Export lite context"
    Write-Host "  context-dev  - Export dev context"
    Write-Host "  context-debug- Export debug context"
    Write-Host ""
    Write-Host "Build:"
    Write-Host "  build-paper  - Build 3579-paper.exe"
    Write-Host "  build-live   - Build 3579-live.exe"
    Write-Host "  build        - Build both exe files"
    Write-Host ""
    Write-Host "Utility:"
    Write-Host "  install      - Install dependencies"
    Write-Host "  install-dev  - Install dev dependencies"
    Write-Host "  clean        - Clean build artifacts"
    Write-Host ""
    Write-Host "Python: $PYTHON"
}

function Invoke-Install {
    Write-Host "Installing base dependencies..." -ForegroundColor Cyan
    & $PIP install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-InstallDev {
    Invoke-Install
    Write-Host "Installing dev dependencies..." -ForegroundColor Cyan
    & $PIP install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Format {
    Write-Host "Formatting code..." -ForegroundColor Cyan
    & $PYTHON -m ruff format .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-FormatCheck {
    Write-Host "Checking format..." -ForegroundColor Cyan
    & $PYTHON -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { exit 2 }
}

function Invoke-Lint {
    Write-Host "Linting..." -ForegroundColor Cyan
    & $PYTHON -m ruff check .
    if ($LASTEXITCODE -ne 0) { exit 2 }
}

function Invoke-LintFix {
    Write-Host "Linting with auto-fix..." -ForegroundColor Cyan
    & $PYTHON -m ruff check --fix .
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Type {
    Write-Host "Type checking..." -ForegroundColor Cyan
    & $PYTHON -m mypy .
    if ($LASTEXITCODE -ne 0) { exit 3 }
}

function Invoke-Test {
    Write-Host "Running tests (coverage threshold: $COV_THRESHOLD%)..." -ForegroundColor Cyan
    & $PYTHON -m pytest -q --cov=src --cov-report=term-missing:skip-covered --cov-fail-under=$COV_THRESHOLD
    if ($LASTEXITCODE -ne 0) { exit 4 }
}

function Invoke-TestFast {
    Write-Host "Running tests (fast, no coverage)..." -ForegroundColor Cyan
    & $PYTHON -m pytest -q -x
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Check {
    Invoke-FormatCheck
    Invoke-Lint
    Invoke-Type
    Invoke-Test
}

function Invoke-CI {
    Write-Host "=============================================="
    Write-Host "Running CI Gate..."
    Write-Host "Python: $PYTHON"
    Write-Host "=============================================="
    Invoke-Check
    Write-Host ""
    Write-Host "=============================================="
    Write-Host "CI Gate PASSED" -ForegroundColor Green
    Write-Host "=============================================="
}

function Invoke-Context {
    param([string]$Level = "lite")
    Write-Host "Exporting context (level: $Level)..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Force -Path artifacts\context | Out-Null
    & $PYTHON scripts/export_context.py --out artifacts/context/context.md --level $Level
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-BuildPaper {
    Write-Host "Building 3579-paper.exe..." -ForegroundColor Cyan
    & $PYTHON -m PyInstaller 3579-paper.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-BuildLive {
    Write-Host "Building 3579-live.exe..." -ForegroundColor Cyan
    & $PYTHON -m PyInstaller 3579-live.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Build {
    Invoke-BuildPaper
    Invoke-BuildLive
}

function Invoke-Clean {
    Write-Host "Cleaning build artifacts..." -ForegroundColor Cyan
    $dirs = @("build", "dist", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
            Write-Host "  Removed: $dir"
        }
    }
    if (Test-Path ".coverage") {
        Remove-Item -Force ".coverage" -ErrorAction SilentlyContinue
        Write-Host "  Removed: .coverage"
    }
}

# =============================================================================
# 主入口
# =============================================================================

# 切换到项目根目录（脚本所在目录的父目录）
Push-Location (Join-Path $PSScriptRoot "..")

try {
    switch ($Target) {
        "help"          { Show-Help }
        "install"       { Invoke-Install }
        "install-dev"   { Invoke-InstallDev }
        "format"        { Invoke-Format }
        "format-check"  { Invoke-FormatCheck }
        "lint"          { Invoke-Lint }
        "lint-fix"      { Invoke-LintFix }
        "type"          { Invoke-Type }
        "test"          { Invoke-Test }
        "test-fast"     { Invoke-TestFast }
        "check"         { Invoke-Check }
        "ci"            { Invoke-CI }
        "context"       { Invoke-Context -Level "lite" }
        "context-dev"   { Invoke-Context -Level "dev" }
        "context-debug" { Invoke-Context -Level "debug" }
        "build"         { Invoke-Build }
        "build-paper"   { Invoke-BuildPaper }
        "build-live"    { Invoke-BuildLive }
        "clean"         { Invoke-Clean }
        default         { Show-Help }
    }
} finally {
    Pop-Location
}
