# CI Gate 退出码约定 (军规级 v4.0)

> **文档版本**: v4.0 军规级别标准
> **更新日期**: 2025-12-17
> **适用范围**: 3579 中国期货量化交易系统

本文档定义 3579 系统 CI/CD 的标准退出码，确保本地与 CI 行为一致。
**军规级要求**: 所有退出码必须严格遵守，违规将导致系统拒绝部署。

---

## 退出码总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    军规级退出码体系 (Exit Code System)                     │
├─────────────────────────────────────────────────────────────────────────┤
│  0     SUCCESS              全部通过                                     │
│  1     GENERAL_ERROR        一般错误（未预期异常）                         │
│  2     FORMAT_LINT_FAIL     格式/Lint 失败                               │
│  3     TYPE_CHECK_FAIL      类型检查失败                                  │
│  4     TEST_FAIL            测试失败                                     │
│  5     COVERAGE_FAIL        覆盖率不足 (<85%)                            │
│  6     RISK_CONFIG_FAIL     风控配置缺失                                  │
│  7     BROKER_CREDS_FAIL    Broker 凭证无效                              │
│  8     REPLAY_FAIL          Replay 验证失败                              │
│  9     SIM_FAIL             Sim 验证失败                                 │
│  10    MODEL_WEIGHTS_FAIL   模型权重缺失/无效                             │
│  11    SCENARIO_MISSING     必需场景缺失                                  │
│  12    POLICY_VIOLATION     军法处置（最高严重级别）                        │
│  13    CAPABILITY_MISSING   平台能力缺失                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 退出码详细表

### 基础 CI 检查退出码 (0-5)

| 退出码 | 名称 | 含义 | 触发条件 | 军规覆盖 |
|:------:|------|------|---------|----------|
| `0` | SUCCESS | 全部通过 | 所有检查通过 | - |
| `1` | GENERAL_ERROR | 一般错误 | 未预期的异常 | M9 |
| `2` | FORMAT_LINT_FAIL | 格式/Lint 失败 | `ruff format --check` 或 `ruff check` 失败 | - |
| `3` | TYPE_CHECK_FAIL | 类型检查失败 | `mypy` 失败 | - |
| `4` | TEST_FAIL | 测试失败 | `pytest` 有失败用例 | - |
| `5` | COVERAGE_FAIL | 覆盖率不足 | 覆盖率 < 85% | - |

### LIVE 模式部署检查退出码 (6-7)

| 退出码 | 名称 | 含义 | 触发条件 | 军规覆盖 |
|:------:|------|------|---------|----------|
| `6` | RISK_CONFIG_FAIL | 风控配置缺失 | LIVE 模式缺少风控配置 | M6, M16 |
| `7` | BROKER_CREDS_FAIL | Broker 凭证无效 | LIVE 模式凭证验证失败 | M8 |

### Replay/Sim 验证退出码 (8-9)

| 退出码 | 名称 | 含义 | 触发条件 | 军规覆盖 |
|:------:|------|------|---------|----------|
| `8` | REPLAY_FAIL | Replay 失败 | 回放测试有场景失败 | M7 |
| `9` | SIM_FAIL | Sim 失败 | 模拟测试有场景失败 | M7 |

### 高级验证退出码 (10-11)

| 退出码 | 名称 | 含义 | 触发条件 | 军规覆盖 |
|:------:|------|------|---------|----------|
| `10` | MODEL_WEIGHTS_FAIL | 模型权重失败 | DL/RL 模型权重缺失或加载失败 | M18 |
| `11` | SCENARIO_MISSING | 场景缺失 | v3pro_required_scenarios.yml 中的必需场景未执行 | M7 |

### 军规级强制退出码 (12-13)

| 退出码 | 名称 | 含义 | 触发条件 | 军规覆盖 |
|:------:|------|------|---------|----------|
| `12` | POLICY_VIOLATION | 军法处置 | Schema不符/绕开入口/CHECK_MODE未启用 | 全部 |
| `13` | CAPABILITY_MISSING | 能力缺失 | 平台必需能力未实现 | M4, M5 |

---

## POLICY_VIOLATION (Exit 12) 详解

**Exit 12 是军规级最高强制退出码**，表示严重违反系统纪律条款。

### 触发条件

| 违规类型 | 代码 | 描述 | 检测位置 |
|---------|------|------|---------|
| **Schema 版本错误** | `SCHEMA.VERSION_OUTDATED` | `schema_version < 3` | `validate_policy.py` |
| **必填字段缺失** | `SCHEMA.MISSING_FIELDS` | 缺少 `type`, `overall`, `exit_code`, `check_mode` | `validate_report_schema()` |
| **无效 JSON** | `SCHEMA.INVALID_JSON` | JSON 解析失败 | `validate_policy.py` |
| **文件缺失** | `SCHEMA.FILE_MISSING` | 报告文件不存在 | `validate_policy.py` |
| **CHECK_MODE 未启用** | `POLICY.CHECK_MODE_DISABLED` | Replay/Sim 报告中 `check_mode=false` | `sim_gate.py` |
| **绕开统一入口** | `POLICY.COMMAND_BLACKLISTED` | 直接执行 `pytest`/`ruff`/`mypy` 而非通过 `make.ps1` | `check_command_whitelist()` |
| **失败结构不完整** | `POLICY.FAILURE_INCOMPLETE` | 失败缺少 `rule_id`, `component`, `evidence` | `validate_failure_structure()` |
| **工件路径错误** | `POLICY.ARTIFACT_PATH_INVALID` | 输出到非 D.1 约定路径 | `validate_artifact_path()` |

### 违规报告结构

触发 POLICY_VIOLATION 时，系统输出到 `artifacts/claude/policy_violation.json`:

```json
{
  "timestamp": "2025-12-17T10:30:00Z",
  "exit_code": 12,
  "violation_count": 1,
  "violations": [
    {
      "code": "SCHEMA.VERSION_OUTDATED",
      "message": "Report schema version 2 is below minimum required version 3",
      "file": "artifacts/check/report.json",
      "evidence": {
        "expected": "schema_version >= 3",
        "actual": "schema_version: 2"
      }
    }
  ]
}
```

### 修复指南

| 违规代码 | 修复方法 |
|---------|---------|
| `SCHEMA.VERSION_OUTDATED` | 更新代码使用 `CIJsonReportV3` 或 `SimReport` |
| `SCHEMA.MISSING_FIELDS` | 确保报告包含所有必填字段 |
| `POLICY.CHECK_MODE_DISABLED` | 使用 `make.ps1 replay-json` 而非直接调用 |
| `POLICY.COMMAND_BLACKLISTED` | 只使用 `make.ps1` 入口命令 |
| `POLICY.FAILURE_INCOMPLETE` | 调用 `add_failure()` 时传入 `rule_id`, `component`, `evidence` |

---

## CAPABILITY_MISSING (Exit 13) 详解

**Exit 13** 表示平台必需能力未实现，通常在策略降级时触发。

### 触发条件

```
platform_required.capability 中定义的能力未通过验证:
- COST.* 成本模型缺失
- PROT.* 执行保护层缺失
- PAIR.* PairExecutor 能力缺失
- AUDIT.* 审计层能力缺失
```

---

## 门禁检查顺序

按照军规级要求，门禁必须严格按以下顺序执行：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        门禁检查顺序 (Gate Check Order)                    │
├─────────────────────────────────────────────────────────────────────────┤
│  Step 1: Ruff Format Check (格式检查)          → Exit 2 on failure      │
│  Step 2: Ruff Lint Check   (代码风格)          → Exit 2 on failure      │
│  Step 3: Mypy Type Check   (类型检查)          → Exit 3 on failure      │
│  Step 4: Pytest Tests      (单元测试)          → Exit 4 on failure      │
│  Step 5: Coverage Check    (覆盖率 ≥85%)       → Exit 5 on failure      │
│  Step 6: Policy Validation (策略验证)          → Exit 12 on failure     │
│  Step 7: Scenario Check    (场景验证)          → Exit 11 on failure     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 使用方式

### 统一入口命令 (推荐)

```powershell
# CI 检查（输出 JSON 到 artifacts/check/report.json）
.\scripts\make.ps1 ci-json

# Replay 检查（自动启用 CHECK_MODE，输出到 artifacts/replay/report.json）
.\scripts\make.ps1 replay-json

# Sim 检查（自动启用 CHECK_MODE，输出到 artifacts/sim/report.json）
.\scripts\make.ps1 sim-json

# 全量门禁检查
.\scripts\make.ps1 gate-all
```

### 本地快速检查

```powershell
# Windows PowerShell 本地快速门禁检查
$python = ".venv/Scripts/python.exe"

# Step 1-2: 格式和Lint
& $python -m ruff format --check . || exit 2
& $python -m ruff check . || exit 2

# Step 3: 类型检查
& $python -m mypy . --ignore-missing-imports || exit 3

# Step 4-5: 测试和覆盖率
& $python -m pytest -q --cov=src --cov-fail-under=85 || exit 4

# Step 6: 策略验证
& $python scripts/validate_policy.py --all || exit 12
```

### Python 编程接口

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
if exit_code != ExitCode.SUCCESS:
    print(f"门禁失败: {exit_code}")
    sys.exit(exit_code)
```

---

## CHECK 模式

当 `CHECK_MODE=True` 时，系统进入检查模式：

- **禁止所有 broker 操作**（`place_order` 抛出 `RuntimeError`）
- 用于 CI/CD 验证，不会产生真实交易
- Replay/Sim 报告**必须**启用 CHECK_MODE

```python
from src.trading.ci_gate import enable_check_mode, assert_not_check_mode, is_check_mode

# 启用 CHECK 模式
enable_check_mode()
assert is_check_mode()  # True

# 在 broker 中使用
def place_order(self, intent):
    assert_not_check_mode("place_order")  # CHECK_MODE 下抛出 RuntimeError
    # ... 实际下单逻辑
```

---

## 报告格式 (Schema v3)

### CI 报告 (`artifacts/check/report.json`)

```json
{
  "schema_version": 3,
  "type": "ci",
  "overall": "PASS",
  "exit_code": 0,
  "check_mode": true,
  "timestamp": "2025-12-17T10:30:00Z",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "exec_id": "abc123_20251217103000",
  "artifacts": {
    "report_path": "artifacts/check/report.json"
  },
  "steps": [
    {"name": "format-check", "status": "PASS", "exit_code": 0, "duration_ms": 1234},
    {"name": "lint", "status": "PASS", "exit_code": 0, "duration_ms": 2345},
    {"name": "type-check", "status": "PASS", "exit_code": 0, "duration_ms": 3456},
    {"name": "test", "status": "PASS", "exit_code": 0, "duration_ms": 45678}
  ]
}
```

### Replay/Sim 报告 (`artifacts/replay/report.json`)

```json
{
  "schema_version": 3,
  "type": "replay",
  "overall": "PASS",
  "exit_code": 0,
  "check_mode": true,
  "timestamp": "2025-12-17T10:30:00Z",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "exec_id": "abc123_20251217103000",
  "artifacts": {
    "report_path": "artifacts/replay/report.json",
    "events_jsonl_path": "artifacts/replay/events.jsonl"
  },
  "scenarios": {
    "total": 165,
    "passed": 165,
    "failed": 0,
    "skipped": 0
  },
  "failures": [],
  "metrics": {
    "total_ticks": 10000,
    "avg_tick_duration_ms": 1.5,
    "pnl_total": 5000.0
  }
}
```

---

## 与其他工具集成

### GitHub Actions

```yaml
- name: Gate Check
  run: |
    python -m ruff format --check . || exit 2
    python -m ruff check . || exit 2
    python -m mypy . || exit 3
    python -m pytest -q --cov=src --cov-fail-under=85 || exit 4
    python scripts/validate_policy.py --all || exit 12
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
python -m ruff format --check . || exit 2
python -m ruff check . || exit 2
python -m mypy . || exit 3
```

### VS Code Task

```json
{
  "label": "军规级门禁检查",
  "type": "shell",
  "command": ".venv/Scripts/python.exe",
  "args": ["scripts/validate_policy.py", "--all"],
  "problemMatcher": []
}
```

---

## 军规关联

| 退出码 | 关联军规 | 说明 |
|--------|----------|------|
| Exit 4 | M7 回放一致 | 测试确保决策可重现 |
| Exit 5 | M3 完整审计 | 覆盖率确保审计完整 |
| Exit 6 | M6, M16 | 风控配置确保熔断保护 |
| Exit 8 | M7 回放一致 | 回放验证确保一致性 |
| Exit 10 | M18 实验性门禁 | 模型权重验证 |
| Exit 11 | M7, M18 | 场景完整性验证 |
| Exit 12 | M1-M20 全部 | 最高级别军法执行 |
| Exit 13 | M4, M5 | 平台能力验证 |

---

**军规级别国家伟大工程 - 退出码规范文档**
**版本 v4.0 | 严格执行 | 违规必究**
