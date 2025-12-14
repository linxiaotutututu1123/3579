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
# 配置
# =============================================================================
$PYTHON = ".\.venv\Scripts\python.exe"
$PIP = ".\.venv\Scripts\pip.exe"
$COV_THRESHOLD = 85

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
}

function Invoke-Python {
    param([string[]]$Args)
    & $PYTHON @Args
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Install {
    & $PIP install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-InstallDev {
    Invoke-Install
    & $PIP install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Invoke-Format {
    Invoke-Python -m ruff format .
}

function Invoke-FormatCheck {
    Invoke-Python -m ruff format --check .
}

function Invoke-Lint {
    Invoke-Python -m ruff check .
}

function Invoke-LintFix {
    Invoke-Python -m ruff check --fix .
}

function Invoke-Type {
    Invoke-Python -m mypy .
}

function Invoke-Test {
    Invoke-Python -m pytest -q --cov=src --cov-report=term-missing:skip-covered --cov-fail-under=$COV_THRESHOLD
}

function Invoke-TestFast {
    Invoke-Python -m pytest -q -x
}

function Invoke-Check {
    Invoke-FormatCheck
    Invoke-Lint
    Invoke-Type
    Invoke-Test
}

function Invoke-CI {
    Invoke-Check
    Write-Host "=============================================="
    Write-Host "CI Gate PASSED"
    Write-Host "=============================================="
}

function Invoke-Context {
    param([string]$Level = "lite")
    New-Item -ItemType Directory -Force -Path artifacts\context | Out-Null
    Invoke-Python scripts/export_context.py --out artifacts/context/context.md --level $Level
}

function Invoke-BuildPaper {
    Invoke-Python -m PyInstaller 3579-paper.spec --noconfirm
}

function Invoke-BuildLive {
    Invoke-Python -m PyInstaller 3579-live.spec --noconfirm
}

function Invoke-Build {
    Invoke-BuildPaper
    Invoke-BuildLive
}

function Invoke-Clean {
    $dirs = @("build", "dist", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")
    foreach ($dir in $dirs) {
        if (Test-Path $dir) {
            Remove-Item -Recurse -Force $dir -ErrorAction SilentlyContinue
        }
    }
    if (Test-Path ".coverage") {
        Remove-Item -Force ".coverage" -ErrorAction SilentlyContinue
    }
}

# =============================================================================
# 主入口
# =============================================================================
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
