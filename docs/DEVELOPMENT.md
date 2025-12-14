# 开发指南 (Development Guide)

本文档描述 3579 Trading System 的开发环境搭建、质量门使用、以及常见问题排查。

---

## 目录

1. [环境要求](#环境要求)
2. [快速开始](#快速开始)
3. [任务运行器](#任务运行器)
4. [Python 路径配置](#python-路径配置)
5. [质量门 (Quality Gates)](#质量门-quality-gates)
6. [上下文导出 (Context Export)](#上下文导出-context-export)
7. [构建可执行文件](#构建可执行文件)
8. [常见问题](#常见问题)

---

## 环境要求

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 推荐 3.11 或 3.12 |
| Git | 2.x | 版本控制 |
| Make | (可选) | Linux/Mac 用户 |
| PowerShell | 5.1+ | Windows 用户 |

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/linxiaotutututu1123/3579.git
cd 3579
git checkout feat/mode2-trading-pipeline
```

### 2. 创建虚拟环境

```bash
# 创建 venv
python -m venv .venv

# 激活 venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Windows CMD:
.\.venv\Scripts\activate.bat

# Linux/Mac:
source .venv/bin/activate
```

### 3. 安装依赖

```bash
# 基础依赖
pip install -r requirements.txt

# 开发依赖（包含 ruff, mypy, pytest 等）
pip install -r requirements-dev.txt
```

### 4. 验证安装

```bash
# Windows
.\scripts\make.ps1 check

# Linux/Mac
make check
```

如果看到 `243 passed` 和 `93%+ coverage`，环境搭建成功。

---

## 任务运行器

项目提供两种等效的任务运行方式，行为完全一致：

| 平台 | 命令 | 示例 |
|------|------|------|
| Linux/Mac | `make <target>` | `make ci` |
| Windows | `.\scripts\make.ps1 <target>` | `.\scripts\make.ps1 ci` |

### 查看所有可用目标

```bash
# Windows
.\scripts\make.ps1 help

# Linux/Mac
make help
```

### 常用目标

| 目标 | 说明 |
|------|------|
| `ci` | 完整 CI 流程（format-check + lint + type + test） |
| `check` | 同 ci，用于本地验证 |
| `format` | 格式化代码（会修改文件） |
| `lint` | 代码检查 |
| `type` | 类型检查 (mypy) |
| `test` | 运行测试（85% 覆盖率门槛） |
| `test-fast` | 快速测试（无覆盖率） |
| `context` | 导出 lite 上下文 |
| `clean` | 清理构建产物 |

---

## Python 路径配置

### 默认行为

任务运行器默认使用项目根目录下的 `.venv` 虚拟环境：

| 平台 | 默认 Python 路径 |
|------|------------------|
| Windows | `.venv/Scripts/python.exe` |
| Linux/Mac | `.venv/bin/python` |

### 覆盖行为

如需使用其他 Python 解释器（如系统 Python 或 conda 环境）：

**Makefile (Linux/Mac):**

```bash
# 使用系统 Python
make ci PY=python

# 使用指定路径
make ci PY=/usr/local/bin/python3.11

# 使用 conda 环境
make ci PY=~/miniconda3/envs/myenv/bin/python
```

**PowerShell (Windows):**

```powershell
# 使用系统 Python
$env:PY='python'; .\scripts\make.ps1 ci

# 使用指定路径
$env:PY='C:\Python311\python.exe'; .\scripts\make.ps1 ci

# 单行形式
$env:PY='python'; .\scripts\make.ps1 ci; Remove-Item Env:PY
```

### 错误提示

如果 venv 不存在，会看到友好错误提示：

```
ERROR: Python not found at .venv/Scripts/python.exe
Run: python -m venv .venv
Or override: $env:PY='python' .\scripts\make.ps1 ci
```

---

## 质量门 (Quality Gates)

所有代码必须通过以下检查才能合并：

| 检查 | 工具 | 退出码 | 说明 |
|------|------|--------|------|
| Format | ruff format | 2 | 代码格式化 |
| Lint | ruff check | 2 | 代码规范检查 |
| Type | mypy | 3 | 静态类型检查 |
| Test | pytest | 4 | 单元测试 + 覆盖率 ≥ 85% |

### 退出码约定

| 退出码 | 含义 |
|--------|------|
| 0 | 通过 |
| 2 | Format/Lint 失败 |
| 3 | Type 检查失败 |
| 4 | Test 失败 |
| 5 | Coverage 不足 |
| 6 | Risk 违规 |
| 7 | Broker 错误 |

详见 [EXIT_CODES.md](./EXIT_CODES.md)

### 推荐工作流

```bash
# 1. 开发前拉取最新代码
git pull origin feat/mode2-trading-pipeline

# 2. 开发过程中随时格式化
.\scripts\make.ps1 format

# 3. 提交前完整检查
.\scripts\make.ps1 check

# 4. 确认通过后提交
git add -A
git commit -m "feat(xxx): your message"
git push
```

---

## 上下文导出 (Context Export)

为 AI 助手（如 Claude、Copilot）准备项目上下文：

| 级别 | 命令 | 包含内容 |
|------|------|----------|
| lite | `make context` | README + tree + pyproject + 关键 spec |
| dev | `make context-dev` | + interfaces/types/runner/orchestrator |
| debug | `make context-debug` | + 最近失败测试/audit 摘要 |

```bash
# 导出 lite 级别上下文
.\scripts\make.ps1 context

# 输出位置
# artifacts/context/context.md
```

### 安全过滤

上下文导出自动过滤敏感文件：
- `.env` / `.env.*`
- `**/secrets/**`
- `**/credentials/**`
- CTP 账户配置文件

---

## 构建可执行文件

```bash
# 构建模拟盘
.\scripts\make.ps1 build-paper

# 构建实盘
.\scripts\make.ps1 build-live

# 构建全部
.\scripts\make.ps1 build
```

输出位置：`dist/3579-paper.exe` 和 `dist/3579-live.exe`

---

## 常见问题

### Q1: `ruff: command not found`

**原因**：未安装开发依赖

**解决**：
```bash
pip install -r requirements-dev.txt
```

### Q2: mypy 报错 `Duplicate module named "torch"`

**原因**：mypy 扫描到了 `dist/` 目录下的打包产物

**解决**：已在 `pyproject.toml` 中配置排除，如仍报错：
```bash
.\scripts\make.ps1 clean
.\scripts\make.ps1 check
```

### Q3: 测试覆盖率不足 85%

**原因**：新代码缺少测试

**解决**：
1. 运行 `pytest --cov=src --cov-report=html` 生成覆盖率报告
2. 打开 `htmlcov/index.html` 查看未覆盖行
3. 补充测试用例

### Q4: Windows 上 `make` 命令不可用

**原因**：Windows 默认不带 GNU Make

**解决**：使用 PowerShell 脚本替代
```powershell
.\scripts\make.ps1 ci
```

或安装 Make：
```powershell
# 使用 Chocolatey
choco install make

# 使用 Scoop
scoop install make
```

### Q5: venv 激活后仍找不到 Python

**原因**：PATH 未正确设置

**解决**：
```powershell
# 检查当前 Python
Get-Command python

# 应显示 .venv\Scripts\python.exe
# 如果不是，手动激活：
.\.venv\Scripts\Activate.ps1
```

---

## CI/CD

GitHub Actions 自动运行：

| 平台 | 检查项 | 说明 |
|------|--------|------|
| Ubuntu | format + lint + type + test | 主要验证 |
| Windows | sanity check + test | Windows 兼容性验证 |

CI 配置：`.github/workflows/ci.yml`

### 本地模拟 CI

```bash
# 完全模拟 CI 行为
.\scripts\make.ps1 ci

# 通过则可放心推送
```

---

## 贡献代码

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feat/your-feature`
3. 开发并通过所有检查：`.\scripts\make.ps1 check`
4. 提交：使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式
5. 推送并创建 PR

提交格式示例：
```
feat(strategy): add momentum factor
fix(broker): handle timeout error
refactor(risk): simplify margin calculation
test(execution): add flatten executor tests
docs(readme): update installation guide
```

---

## 文件结构

```
3579/
├── .github/workflows/    # CI 配置
├── artifacts/            # 构建产物和上下文
│   ├── check/           # CI 检查报告
│   └── context/         # 上下文导出
├── docs/                 # 文档
│   ├── DEVELOPMENT.md   # 本文档
│   ├── EXIT_CODES.md    # 退出码约定
│   └── SPEC_*.md        # 规格文档
├── scripts/              # 脚本
│   ├── make.ps1         # PowerShell 任务运行器
│   └── export_context.py # 上下文导出工具
├── src/                  # 源代码
├── tests/                # 测试
├── Makefile              # Make 任务运行器
├── pyproject.toml        # Python 项目配置
├── requirements.txt      # 生产依赖
└── requirements-dev.txt  # 开发依赖
```

---

## 联系

如有问题，请在 GitHub Issues 中提出。
