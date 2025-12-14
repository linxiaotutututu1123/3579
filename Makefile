# =============================================================================
# 3579 Trading System - Makefile
# 单一入口，强一致性，CI 与本地完全对齐
# =============================================================================

.PHONY: all format lint type test check ci clean build context help

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
# 变量
# -----------------------------------------------------------------------------
PYTHON := .venv/Scripts/python.exe
PIP := .venv/Scripts/pip.exe
COV_THRESHOLD := 85

# Windows 兼容
ifeq ($(OS),Windows_NT)
    PYTHON := .venv\Scripts\python.exe
    PIP := .venv\Scripts\pip.exe
    RM := del /Q /F
    RMDIR := rmdir /S /Q
else
    RM := rm -f
    RMDIR := rm -rf
endif

# -----------------------------------------------------------------------------
# 安装
# -----------------------------------------------------------------------------
install:
	$(PIP) install -r requirements.txt

install-dev: install
	$(PIP) install -r requirements-dev.txt

# -----------------------------------------------------------------------------
# 质量门（与 CI 完全一致）
# -----------------------------------------------------------------------------

# 格式化（会修改文件）
format:
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
check: format-check lint type test

# CI 完整流程（与 .github/workflows/ci.yml 完全一致）
ci: format-check lint type test
	@echo "=============================================="
	@echo "CI Gate PASSED"
	@echo "=============================================="

# -----------------------------------------------------------------------------
# CHECK 模式（生成报告 + 退出码约定）
# -----------------------------------------------------------------------------
# 退出码约定:
#   0 = 全部通过
#   2 = 格式/Lint 失败
#   3 = 类型检查失败
#   4 = 测试失败
#   5 = 覆盖率不足

check-report:
	@mkdir -p artifacts/check
	@echo '{"timestamp":"$(shell date -u +%Y-%m-%dT%H:%M:%SZ)","checks":[' > artifacts/check/report.json
	@$(PYTHON) -m ruff format --check . && echo '{"name":"format","status":"PASS"},' >> artifacts/check/report.json || (echo '{"name":"format","status":"FAIL"},' >> artifacts/check/report.json && exit 2)
	@$(PYTHON) -m ruff check . && echo '{"name":"lint","status":"PASS"},' >> artifacts/check/report.json || (echo '{"name":"lint","status":"FAIL"},' >> artifacts/check/report.json && exit 2)
	@$(PYTHON) -m mypy . && echo '{"name":"type","status":"PASS"},' >> artifacts/check/report.json || (echo '{"name":"type","status":"FAIL"},' >> artifacts/check/report.json && exit 3)
	@$(PYTHON) -m pytest -q --cov=src --cov-fail-under=$(COV_THRESHOLD) && echo '{"name":"test","status":"PASS"}' >> artifacts/check/report.json || (echo '{"name":"test","status":"FAIL"}' >> artifacts/check/report.json && exit 4)
	@echo ']}' >> artifacts/check/report.json
	@echo "Report: artifacts/check/report.json"

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
# 构建
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
	$(RMDIR) build dist __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage 2>nul || true
	$(RMDIR) artifacts/check 2>nul || true
