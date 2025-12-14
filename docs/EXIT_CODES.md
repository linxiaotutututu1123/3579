# CI Gate 退出码约定

本文档定义 3579 系统 CI/CD 的标准退出码，确保本地与 CI 行为一致。

## 退出码表

### CI 检查退出码

| 退出码 | 名称 | 含义 | 触发条件 |
|:------:|------|------|---------|
| `0` | SUCCESS | 全部通过 | 所有检查通过 |
| `1` | GENERAL_ERROR | 一般错误 | 未预期的异常 |
| `2` | FORMAT_LINT_FAIL | 格式/Lint 失败 | `ruff format --check` 或 `ruff check` 失败 |
| `3` | TYPE_CHECK_FAIL | 类型检查失败 | `mypy` 失败 |
| `4` | TEST_FAIL | 测试失败 | `pytest` 有失败用例 |
| `5` | COVERAGE_FAIL | 覆盖率不足 | 覆盖率 < 85% |
| `6` | RISK_CONFIG_FAIL | 风控配置缺失 | LIVE 模式缺少风控配置 |
| `7` | BROKER_CREDS_FAIL | Broker 凭证无效 | LIVE 模式凭证验证失败 |

### Replay/Sim 退出码

| 退出码 | 名称 | 含义 | 触发条件 |
|:------:|------|------|---------|
| `0` | SUCCESS | 全部通过 | 所有场景通过 |
| `8` | REPLAY_FAIL | Replay 失败 | replay 测试有失败 |
| `9` | SIM_FAIL | Sim 失败 | sim 测试有失败 |

## 使用方式

### 统一入口命令

```powershell
# CI 检查（输出 JSON 到 artifacts/check/report.json）
.\scripts\make.ps1 ci-json

# Replay 检查（自动启用 CHECK_MODE，输出到 artifacts/sim/report.json）
.\scripts\make.ps1 replay-json

# Sim 检查（自动启用 CHECK_MODE，输出到 artifacts/sim/report.json）
.\scripts\make.ps1 sim-json
```

### 直接调用模块入口

```bash
# Replay（自动启用 CHECK_MODE）
python -m src.trading.replay --output artifacts/sim/report.json

# Sim（自动启用 CHECK_MODE）
python -m src.trading.sim --output artifacts/sim/report.json
```

### Makefile

```bash
# 运行 CI 检查
make ci

# 生成 JSON 报告
make ci-json
# 输出: artifacts/check/report.json

# Replay/Sim（自动启用 CHECK_MODE）
make replay-json
make sim-json
```

### Python

```python
from src.trading.ci_gate import CIGate, get_exit_code, ExitCode

gate = CIGate(target_mode="LIVE")
report = gate.run_all_checks(
    tests_passed=True,
    lint_passed=True,
    type_check_passed=True,
    risk_limits_configured=True,
    broker_credentials_valid=True,
    model_weights_exist=True,
)

exit_code = get_exit_code(report)
sys.exit(exit_code)
```

### GitHub Actions

CI workflow 中每个 step 返回对应退出码：

```yaml
- name: Format check
  run: |
    python -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { exit 2 }

- name: Type check
  run: |
    python -m mypy .
    if ($LASTEXITCODE -ne 0) { exit 3 }
```

## CHECK 模式

当 `CHECK_MODE=1` 时，系统进入检查模式：

- **禁止所有 broker 操作**（place_order 会抛出 RuntimeError）
- 用于 CI/CD 验证，不会产生真实交易

```python
from src.trading.ci_gate import enable_check_mode, assert_not_check_mode

# 启用 CHECK 模式
enable_check_mode()

# 在 broker 中使用
def place_order(self, intent):
    assert_not_check_mode("place_order")  # 会抛出 RuntimeError
    # ...
```

## 报告格式

`artifacts/check/report.json`:

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "commit": "abc123...",
  "branch": "feat/xxx",
  "checks": [
    {"name": "format", "status": "PASS"},
    {"name": "lint", "status": "PASS"},
    {"name": "type", "status": "PASS"},
    {"name": "test", "status": "PASS"}
  ],
  "all_passed": true
}
```

## 与其他工具集成

### Pre-commit Hook

```bash
#!/bin/bash
make check || exit $?
```

### IDE (VS Code)

在 `.vscode/tasks.json` 中配置：

```json
{
  "label": "CI Check",
  "type": "shell",
  "command": "make ci",
  "problemMatcher": []
}
```
