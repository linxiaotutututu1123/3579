# Development Guide

This document describes the development environment setup, quality gates, and troubleshooting for 3579 Trading System.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Quick Start](#quick-start)
3. [Task Runner](#task-runner)
4. [Python Path Configuration](#python-path-configuration)
5. [Quality Gates](#quality-gates)
6. [Context Export](#context-export)
7. [Build Executables](#build-executables)
8. [FAQ](#faq)

---

## Requirements

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Recommended 3.11 or 3.12 |
| Git | 2.x | Version control |
| Make | (optional) | Linux/Mac users |
| PowerShell | 5.1+ | Windows users |

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/linxiaotutututu1123/3579.git
cd 3579
git checkout feat/mode2-trading-pipeline
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv .venv

# Activate venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows CMD:
.\.venv\Scripts\activate.bat

# Linux/Mac:
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Base dependencies
pip install -r requirements.txt

# Dev dependencies (includes ruff, mypy, pytest, etc.)
pip install -r requirements-dev.txt
```

### 4. Verify Installation

```bash
# Windows
.\scripts\make.ps1 check

# Linux/Mac
make check
```

If you see `243 passed` and `93%+ coverage`, the environment is ready.

---

## Task Runner

The project provides two equivalent task runners with identical behavior:

| Platform | Command | Example |
|----------|---------|---------|
| Linux/Mac | `make <target>` | `make ci` |
| Windows | `.\scripts\make.ps1 <target>` | `.\scripts\make.ps1 ci` |

### Show All Available Targets

```bash
# Windows
.\scripts\make.ps1 help

# Linux/Mac
make help
```

### Common Targets

| Target | Description |
|--------|-------------|
| `ci` | Full CI pipeline (format-check + lint + type + test) |
| `check` | Same as ci, for local verification |
| `format` | Format code (modifies files) |
| `lint` | Code linting |
| `type` | Type checking (mypy) |
| `test` | Run tests (85% coverage threshold) |
| `test-fast` | Quick tests (no coverage) |
| `context` | Export lite context |
| `clean` | Clean build artifacts |

---

## Python Path Configuration

### Default Behavior

Task runners use `.venv` in project root by default:

| Platform | Default Python Path |
|----------|---------------------|
| Windows | `.venv/Scripts/python.exe` |
| Linux/Mac | `.venv/bin/python` |

### Override Behavior

To use a different Python interpreter (e.g., system Python or conda):

**Makefile (Linux/Mac):**

```bash
# Use system Python
make ci PY=python

# Use specific path
make ci PY=/usr/local/bin/python3.11

# Use conda environment
make ci PY=~/miniconda3/envs/myenv/bin/python
```

**PowerShell (Windows):**

```powershell
# Use system Python
$env:PY='python'; .\scripts\make.ps1 ci

# Use specific path
$env:PY='C:\Python311\python.exe'; .\scripts\make.ps1 ci

# One-liner form
$env:PY='python'; .\scripts\make.ps1 ci; Remove-Item Env:PY
```

### Error Messages

If venv doesn't exist, you'll see a friendly error:

```
ERROR: Python not found at .venv/Scripts/python.exe
Run: python -m venv .venv
Or override: $env:PY='python' .\scripts\make.ps1 ci
```

---

## Quality Gates

All code must pass these checks before merging:

| Check | Tool | Exit Code | Description |
|-------|------|-----------|-------------|
| Format | ruff format | 2 | Code formatting |
| Lint | ruff check | 2 | Code style checks |
| Type | mypy | 3 | Static type checking |
| Test | pytest | 4 | Unit tests + coverage >= 85% |

### Exit Code Convention

| Exit Code | Meaning |
|-----------|---------|
| 0 | Pass |
| 2 | Format/Lint failure |
| 3 | Type check failure |
| 4 | Test failure |
| 5 | Coverage insufficient |
| 6 | Risk violation |
| 7 | Broker error |

See [EXIT_CODES.md](./EXIT_CODES.md) for details.

### Recommended Workflow

```bash
# 1. Pull latest code before development
git pull origin feat/mode2-trading-pipeline

# 2. Format during development
.\scripts\make.ps1 format

# 3. Full check before commit
.\scripts\make.ps1 check

# 4. Commit after passing
git add -A
git commit -m "feat(xxx): your message"
git push
```

---

## Context Export

Prepare project context for AI assistants (Claude, Copilot, etc.):

| Level | Command | Contents |
|-------|---------|----------|
| lite | `make context` | README + tree + pyproject + key specs |
| dev | `make context-dev` | + interfaces/types/runner/orchestrator |
| debug | `make context-debug` | + recent test failures/audit summary |

```bash
# Export lite level context
.\scripts\make.ps1 context

# Output location
# artifacts/context/context.md
```

### Security Filtering

Context export automatically filters sensitive files:
- `.env` / `.env.*`
- `**/secrets/**`
- `**/credentials/**`
- CTP account configuration files

---

## Build Executables

```bash
# Build paper trading
.\scripts\make.ps1 build-paper

# Build live trading
.\scripts\make.ps1 build-live

# Build both
.\scripts\make.ps1 build
```

Output: `dist/3579-paper.exe` and `dist/3579-live.exe`

---

## FAQ

### Q1: `ruff: command not found`

**Cause**: Dev dependencies not installed

**Solution**:
```bash
pip install -r requirements-dev.txt
```

### Q2: mypy reports `Duplicate module named "torch"`

**Cause**: mypy scanning packaged files in `dist/`

**Solution**: Already configured in `pyproject.toml`. If still occurs:
```bash
.\scripts\make.ps1 clean
.\scripts\make.ps1 check
```

### Q3: Test coverage below 85%

**Cause**: New code lacks tests

**Solution**:
1. Run `pytest --cov=src --cov-report=html` to generate coverage report
2. Open `htmlcov/index.html` to see uncovered lines
3. Add test cases

### Q4: `make` command not available on Windows

**Cause**: Windows doesn't include GNU Make by default

**Solution**: Use PowerShell script instead
```powershell
.\scripts\make.ps1 ci
```

Or install Make:
```powershell
# Using Chocolatey
choco install make

# Using Scoop
scoop install make
```

### Q5: Python not found after activating venv

**Cause**: PATH not set correctly

**Solution**:
```powershell
# Check current Python
Get-Command python

# Should show .venv\Scripts\python.exe
# If not, manually activate:
.\.venv\Scripts\Activate.ps1
```

---

## CI/CD

GitHub Actions runs automatically:

| Platform | Checks | Notes |
|----------|--------|-------|
| Ubuntu | format + lint + type + test | Primary validation |
| Windows | sanity check + test | Windows compatibility |

CI config: `.github/workflows/ci.yml`

### Simulate CI Locally

```bash
# Fully simulate CI behavior
.\scripts\make.ps1 ci

# If passes, safe to push
```

---

## Contributing

1. Fork this repository
2. Create feature branch: `git checkout -b feat/your-feature`
3. Develop and pass all checks: `.\scripts\make.ps1 check`
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/)
5. Push and create PR

Commit format examples:
```
feat(strategy): add momentum factor
fix(broker): handle timeout error
refactor(risk): simplify margin calculation
test(execution): add flatten executor tests
docs(readme): update installation guide
```

---

## Directory Structure

```
3579/
├── .github/workflows/    # CI configuration
├── artifacts/            # Build artifacts and context
│   ├── check/           # CI check reports
│   └── context/         # Context exports
├── docs/                 # Documentation
│   ├── DEVELOPMENT.md   # This document
│   ├── EXIT_CODES.md    # Exit code convention
│   └── SPEC_*.md        # Specification documents
├── scripts/              # Scripts
│   ├── make.ps1         # PowerShell task runner
│   └── export_context.py # Context export tool
├── src/                  # Source code
├── tests/                # Tests
├── Makefile              # Make task runner
├── pyproject.toml        # Python project config
├── requirements.txt      # Production dependencies
└── requirements-dev.txt  # Development dependencies
```

---

## Contact

For questions, please open a GitHub Issue.
