# =============================================================================
# 3579 Trading System - Makefile
# 单一入口，强一致性，CI 与本地完全对齐
# 跨平台：Linux/Mac 用 make，Windows 用 make（需安装）或 .\scripts\make.ps1
#
# 用法:
#   make ci                    # 使用默认 venv Python
#   make ci PY=python          # 使用系统 Python
#   make ci PY=.venv/bin/python  # 指定 Python 路径
# =============================================================================

.PHONY: all format lint type test check ci ci-json replay replay-json sim sim-json clean build context help

# -----------------------------------------------------------------------------
# 默认目标
# -----------------------------------------------------------------------------
help:
	@echo "3579 Trading System - Available Targets"
	@echo "========================================"
	@echo ""
	@echo "Quality Gates:"
	@echo "  make format     - Format code (ruff format)"
	@echo "  make lint       - Lint code (ruff check)"
	@echo "  make type       - Type check (mypy)"
	@echo "  make test       - Run tests (pytest, 85% coverage gate)"
	@echo "  make check      - Run all checks without modifying files"
	@echo "  make ci         - Full CI pipeline (format-check + lint + type + test)"
	@echo "  make ci-json    - CI pipeline with JSON report (for Claude loop)"
	@echo ""
	@echo "Replay/Sim:"
	@echo "  make replay       - Run replay validation"
	@echo "  make replay-json  - Replay with JSON report (for Claude loop)"
	@echo "  make sim          - Run simulation"
	@echo "  make sim-json     - Simulation with JSON report (for Claude loop)"
	@echo ""
	@echo "Context Export:"
	@echo "  make context          - Export lite context"
	@echo "  make context-dev      - Export dev context"
	@echo "  make context-debug    - Export debug context"
	@echo ""
	@echo "Build:"
	@echo "  make build-paper      - Build 3579-paper.exe"
	@echo "  make build-live       - Build 3579-live.exe"
	@echo "  make build            - Build both exe files"
	@echo ""
	@echo "Utility:"
	@echo "  make clean            - Clean build artifacts"
	@echo "  make install          - Install dependencies"
	@echo "  make install-dev      - Install dev dependencies"

# -----------------------------------------------------------------------------
# 变量（跨平台，支持覆盖）
# -----------------------------------------------------------------------------
COV_THRESHOLD := 85

# Python 路径覆盖：make ci PY=/custom/python
# 如果用户在命令行传入 PY=xxx，则使用用户指定的
# 否则使用下面按平台写死的 venv 路径
#
# 注意：ifeq 块顶格，避免 tab/space 混用问题
ifeq ($(OS),Windows_NT)
# Windows: 写死 venv 路径（用 / 避免反斜杠在命令拼接时出问题）
_PY_DEFAULT := .venv/Scripts/python.exe
_PIP_DEFAULT := .venv/Scripts/pip.exe
_VENV_CHECK := if not exist ".venv\Scripts\python.exe" (echo ERROR: venv not found. Run: python -m venv .venv && exit /b 1)
RM := del /Q /F 2>nul || true
RMDIR := rmdir /S /Q 2>nul || true
MKDIR := mkdir
else
# Linux/Mac: 写死 venv 路径
_PY_DEFAULT := .venv/bin/python
_PIP_DEFAULT := .venv/bin/pip
_VENV_CHECK := test -x .venv/bin/python || { echo "ERROR: venv not found. Run: python -m venv .venv"; exit 1; }
RM := rm -f
RMDIR := rm -rf
MKDIR := mkdir -p
endif

# 外部可覆盖，默认用平台写死值
PY ?= $(_PY_DEFAULT)
PIP ?= $(_PIP_DEFAULT)

# 向后兼容：PYTHON 作为 PY 的别名
PYTHON := $(PY)

# -----------------------------------------------------------------------------
# venv 检查（友好错误提示）
# -----------------------------------------------------------------------------
venv-check:
	@$(_VENV_CHECK)

# -----------------------------------------------------------------------------
# 安装
# -----------------------------------------------------------------------------
install: venv-check
	$(PIP) install -r requirements.txt

install-dev: install
	$(PIP) install -r requirements-dev.txt

# -----------------------------------------------------------------------------
# 质量门（与 CI 完全一致）
# -----------------------------------------------------------------------------

# 格式化（会修改文件）
format: venv-check
	$(PYTHON) -m ruff format .

# 格式检查（不修改，只检查）
format-check:
	$(PYTHON) -m ruff format --check .

# Lint
lint:
	$(PYTHON) -m ruff check .

# Lint + 自动修复
lint-fix:
	$(PYTHON) -m ruff check --fix .

# 类型检查
type:
	$(PYTHON) -m mypy .

# 测试（带覆盖率门槛）
test:
	$(PYTHON) -m pytest -q --cov=src --cov-report=term-missing:skip-covered --cov-fail-under=$(COV_THRESHOLD)

# 快速测试（无覆盖率）
test-fast:
	$(PYTHON) -m pytest -q -x

# 所有检查（不修改文件）- 用于 pre-commit 或手动验证
check: venv-check format-check lint type test

# CI 完整流程（与 .github/workflows/ci.yml 完全一致）
ci: venv-check format-check lint type test
	@echo "=============================================="
	@echo "CI Gate PASSED"
	@echo "=============================================="

# -----------------------------------------------------------------------------
# 上下文导出（分层）
# -----------------------------------------------------------------------------

# Lite: 最小上下文（README + tree + pyproject + 关键 spec）
context:
	$(PYTHON) scripts/export_context.py --out artifacts/context/context.md --level lite

# Dev: 开发上下文（+ interfaces/types/runner/orchestrator）
context-dev:
	$(PYTHON) scripts/export_context.py --out artifacts/context/context.md --level dev

# Debug: 调试上下文（+ 最近失败测试/audit 摘要）
context-debug:
	$(PYTHON) scripts/export_context.py --out artifacts/context/context.md --level debug

# -----------------------------------------------------------------------------
# 构建（仅 Windows）
# -----------------------------------------------------------------------------
build-paper:
	$(PYTHON) -m PyInstaller 3579-paper.spec --noconfirm

build-live:
	$(PYTHON) -m PyInstaller 3579-live.spec --noconfirm

build: build-paper build-live

# -----------------------------------------------------------------------------
# 清理
# -----------------------------------------------------------------------------
clean:
ifeq ($(OS),Windows_NT)
	-$(RMDIR) build
	-$(RMDIR) dist
	-$(RMDIR) __pycache__
	-$(RMDIR) .pytest_cache
	-$(RMDIR) .mypy_cache
	-$(RMDIR) .ruff_cache
	-$(RM) .coverage
else
	$(RMDIR) build dist __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage
endif
