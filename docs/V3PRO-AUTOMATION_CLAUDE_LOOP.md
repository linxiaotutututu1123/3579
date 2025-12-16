# Claude 自动闭环契约（军规级 v3.0）

> **本文档是 Claude Agent 的强制执行协议**
> **违反任何条款将触发 POLICY_VIOLATION（exit 12）**

---

## 核心原则（令行禁止）

```text
╔════════════════════════════════════════════════════════════════════════════╗
║  军规级自动闭环 = 白名单命令 + Schema 校验 + 审计日志 + 违规即停           ║
╚════════════════════════════════════════════════════════════════════════════╝
```

### 🚫 绝对禁止（自动检测 + 立即 FAIL）

| 违规行为 | 违规代码 | 后果 |
|---------|---------|------|
| 直接运行 `pytest`/`ruff`/`mypy` | `POLICY.COMMAND_BLACKLISTED` | exit 12 |
| 修改 `.github/workflows/*.yml` | `POLICY.PROTECTED_FILE` | exit 12 |
| 修改 `coverage_exceptions.yml` 未说明理由 | `POLICY.EXCEPTION_UNEXPLAINED` | exit 12 |
| 未在每轮循环前更新 context | `POLICY.CONTEXT_STALE` | exit 12 |
| report.json 缺失必填字段 | `SCHEMA.MISSING_FIELDS` | exit 12 |
| replay/sim 未启用 CHECK_MODE | `POLICY.CHECK_MODE_DISABLED` | exit 12 |
| schema_version < 3 | `SCHEMA.VERSION_OUTDATED` | exit 12 |
| Failure 缺少 rule_id/component/evidence | `SCHEMA.FAILURE_INCOMPLETE` | exit 12 |

### ✅ 必须遵守

- ✅ **只使用 `make.ps1` 入口** - 所有检查必须通过 make.ps1 targets
- ✅ **每轮刷新 context** - `make.ps1 context-dev` 在修改代码前执行
- ✅ **解析 JSON 报告** - 不依赖终端输出，只信任 `report.json`
- ✅ **按 rule_id 定位问题** - 使用 `V2_REQUIRED_SCENARIOS.yml` 中的 rule_id
- ✅ **提供 evidence** - 失败报告必须包含状态快照

---

## 退出码约定

| 退出码 | 名称 | 含义 | Claude 应对 |
|-------|------|------|-------------|
| 0 | SUCCESS | 全部通过 | 完成任务 |
| 1 | GENERAL_ERROR | 未知错误 | 检查日志，报告问题 |
| 2 | FORMAT_LINT_FAIL | 格式/lint 失败 | 运行 `make.ps1 format` |
| 3 | TYPE_CHECK_FAIL | 类型检查失败 | 根据 mypy 错误修改类型 |
| 4 | TEST_FAIL | 测试失败 | 根据 failures 数组修改代码 |
| 5 | COVERAGE_FAIL | 覆盖率不足 | 添加测试 |
| 6 | RISK_CONFIG_FAIL | 风险配置缺失 | 检查配置文件 |
| 7 | BROKER_CREDS_FAIL | Broker 凭据无效 | 检查凭据 |
| 8 | REPLAY_FAIL | Replay 失败 | 根据 rule_id 修改代码 |
| 9 | SIM_FAIL | Sim 失败 | 根据 rule_id 修改代码 |
| **12** | **POLICY_VIOLATION** | **军法处置** | **停止操作，检查违规报告** |

---

## A. 自动编码闘环（Code Fix Loop）

### 流程图（军规级）

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Claude 自动编码闭环（军规级 v3.0）                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│   │ 1. 刷新上下文 │───▶│ 2. 读 context │───▶│ 3. 修改代码  │                  │
│   │ context-dev  │    │ + V2_SPEC    │    │ 精确编辑     │                  │
│   └──────────────┘    └──────────────┘    └──────────────┘                  │
│          ▲                                       │                          │
│          │                                       ▼                          │
│   ┌──────┴──────┐                        ┌──────────────┐                   │
│   │ 6. 失败?    │◀───────────────────────│ 4. CI + 校验  │                   │
│   │ 解析 JSON   │                        │ ci-json      │                   │
│   │ 检查 schema │                        │ schema v3    │                   │
│   └─────────────┘                        └──────────────┘                   │
│          │                                       │                          │
│          │ schema 不符合                         │                          │
│          ▼                                       │                          │
│   ┌──────────────┐                               │                          │
│   │ POLICY_VIOLATION │◀──────────────────────────┘                          │
│   │ exit 12      │   schema_version < 3 / 缺失字段                          │
│   └──────────────┘                                                          │
│          │                                                                  │
│          ▼ 全部通过                                                          │
│   ┌──────────────┐                                                          │
│   │ 7. 进入 Replay │                                                         │
│   └──────────────┘                                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 执行命令（白名单）

```powershell
# 【唯一允许的命令入口】

# Step 1: 生成开发上下文（每轮必须）
.\scripts\make.ps1 context-dev

# Step 2: 读取上下文 + V2_REQUIRED_SCENARIOS
Get-Content artifacts\context\context.md
Get-Content V2_REQUIRED_SCENARIOS.yml

# Step 3: 修改代码（使用编辑器工具）

# Step 4: 运行 CI 并获取 JSON 结果
.\scripts\make.ps1 ci-json

# Step 5: 解析 JSON 报告（严格 schema 校验）
Get-Content artifacts\check\report.json | ConvertFrom-Json

# Step 6: 如果 CI 通过，运行 Replay
.\scripts\make.ps1 replay-json

# Step 7: 解析 Replay 报告
Get-Content artifacts\sim\report.json | ConvertFrom-Json
```

---

## B. JSON 报告格式（v3.0 军规级 Schema）

### CI 报告 (`artifacts/check/report.json`)

```json
{
  "schema_version": 3,
  "type": "ci",
  "timestamp": "2025-01-15T10:30:00Z",
  "check_mode": false,
  "all_passed": false,
  "failed_step": "lint",
  "overall": "FAIL",
  "exit_code": 2,
  "steps": [
    {
      "name": "format-check",
      "status": "PASS",
      "exit_code": 0,
      "duration_ms": 1234
    },
    {
      "name": "lint",
      "status": "FAIL",
      "exit_code": 2,
      "duration_ms": 2345,
      "summary": "src/foo.py:42:1: E501 line too long...",
      "failures": [
        {
          "file": "src/foo.py",
          "line": 42,
          "rule": "E501",
          "message": "line too long (120 > 100)"
        }
      ],
      "hints": [
        "Line too long - break into multiple lines or use parentheses",
        "Run: make lint-fix to auto-fix some issues"
      ]
    }
  ]
}
```

### Replay/Sim 报告 (`artifacts/sim/report.json`)

```json
{
  "schema_version": 3,
  "type": "replay",
  "timestamp": "2025-01-15T10:35:00Z",
  "check_mode": true,
  "overall": "FAIL",
  "exit_code": 8,
  "scenarios_total": 55,
  "scenarios_passed": 52,
  "scenarios_failed": 3,
  "failures": [
    {
      "scenario": "universe_selector_roll_rules",
      "rule_id": "UNIV.DOMINANT.ROLL.COOLDOWN",
      "component": "market.universe_selector",
      "tick": 42,
      "expected": {"dominant": "rb2501"},
      "actual": {"dominant": "rb2410"},
      "error": "dominant contract violates cooldown rule",
      "evidence": {
        "volumes": {"rb2501": 12345, "rb2410": 23456},
        "open_interest": {"rb2501": 888, "rb2410": 999},
        "last_roll_tick": 10,
        "cooldown_seconds": 300
      }
    }
  ],
  "metrics": {
    "total_ticks": 1000,
    "avg_tick_duration_ms": 1.5,
    "max_drawdown_pct": 2.3,
    "orders_placed": 50,
    "orders_rejected": 2,
    "orders_filled": 48,
    "pnl_total": 1234.56
  }
}
```

---

## C. 必填字段校验表

### CI Report 必填字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `schema_version` | int | 必须 >= 3 |
| `type` | string | "ci" |
| `overall` | string | "PASS" / "FAIL" |
| `exit_code` | int | 退出码 |
| `check_mode` | bool | CI 报告可为 false |

### Sim/Replay Report 必填字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `schema_version` | int | 必须 >= 3 |
| `type` | string | "replay" / "sim" |
| `overall` | string | "PASS" / "FAIL" |
| `exit_code` | int | 退出码 |
| `check_mode` | bool | **必须为 true** |
| `scenarios_total` | int | 场景总数 |
| `scenarios_passed` | int | 通过数 |
| `scenarios_failed` | int | 失败数 |

### Failure 必填字段

| 字段 | 类型 | 说明 |
|-----|------|------|
| `rule_id` | string | 场景标识（如 UNIV.DOMINANT.BASIC） |
| `component` | string | 模块名（如 market.universe_selector） |
| `tick` | int | 失败发生的 tick |
| `expected` | object | 期望值 |
| `actual` | object | 实际值 |
| `error` | string | 错误描述 |
| `evidence` | object | 状态快照（可选但强烈建议） |

---

## D. 审计日志与产物路径

### D.1 固定产物路径（绝对不变）

```text
artifacts/
├── check/
│   └── report.json          # CI 报告
├── sim/
│   └── report.json          # Replay/Sim 报告
├── context/
│   └── context.md           # 开发上下文
└── claude/
    ├── commands.log         # 命令审计日志
    ├── round_summary.json   # 每轮结果摘要
    └── policy_violation.json # 违规报告
```

### D.2 命令审计日志格式

```text
========== Session Start: 2025-01-15 10:30:00 ==========
Mode: full, MaxRounds: 5, Strict: True
[2025-01-15 10:30:01] CMD: make.ps1 context-dev | EXIT: 0 | RESULT: 
[2025-01-15 10:30:02] CMD: make.ps1 ci-json | EXIT: 0 | RESULT: 
[2025-01-15 10:30:05] CMD: make.ps1 replay-json | EXIT: 8 | RESULT: 
```

### D.3 违规报告格式

```json
{
  "timestamp": "2025-01-15T10:35:00Z",
  "has_violations": true,
  "violation_count": 1,
  "violations": [
    {
      "code": "POLICY.CHECK_MODE_DISABLED",
      "message": "CHECK_MODE must be enabled for replay",
      "evidence": {
        "check_mode": false
      }
    }
  ]
}
```

---

## E. V2 Required Scenarios 集成

### E.1 场景来源

所有必须通过的场景定义在 `V2_REQUIRED_SCENARIOS.yml`：

```yaml
phases:
  A:
    name: "接口冻结 + Replay-first"
    scenarios:
      - rule_id: "UNIV.DOMINANT.BASIC"
        component: "market.universe_selector"
        required: true
        test_pattern: "test_universe_selector*dominant*"
  B:
    name: "执行可靠性"
    scenarios:
      - rule_id: "FSM.STRICT.TRANSITIONS"
        component: "execution.fsm"
        required: true
```

### E.2 失败处理策略

| 失败类型 | rule_id 前缀 | 应修改的模块 |
|---------|-------------|-------------|
| 主力选择 | `UNIV.*` | `src/market/universe_selector.py` |
| FSM 状态机 | `FSM.*` | `src/execution/fsm.py` |
| 执行引擎 | `EXEC.*` | `src/execution/auto_order_engine.py` |
| 持仓对账 | `POS.*` | `src/execution/position_tracker.py` |
| 市场连续性 | `MKT.*` | `src/market/` |
| 套利执行 | `PAIR.*` | `src/execution/pair_executor.py` |
| Guardian | `GUARD.*` | `src/guardian/` |
| 审计 | `AUDIT.*` | `src/audit/` |
| 回放 | `REPLAY.*` | `src/replay/` |

---

## F. 军规级闭环驱动器使用

### F.1 完整闭环（推荐）

```powershell
# 严格模式：任何违规立即 exit 12
.\scripts\claude_loop.ps1 -Mode full -Strict

# 非严格模式：允许 schema 校验警告
.\scripts\claude_loop.ps1 -Mode full
```

### F.2 单独模式

```powershell
# 只运行 CI
.\scripts\claude_loop.ps1 -Mode ci -Strict

# 只运行 Replay（假设 CI 已通过）
.\scripts\claude_loop.ps1 -Mode replay -SkipContext

# 只运行 Sim
.\scripts\claude_loop.ps1 -Mode sim
```

### F.3 自动化环境

```powershell
# CI 环境自动继续下一轮
$env:CLAUDE_AUTOMATED = "1"
.\scripts\claude_loop.ps1 -Mode full -MaxRounds 10
```

---

## G. 违规检测清单

### G.1 自动检测的违规

| 检测点 | 违规代码 | 检测方式 |
|-------|---------|---------|
| report.json 不存在 | `SCHEMA.FILE_MISSING` | 文件系统检查 |
| JSON 解析失败 | `SCHEMA.INVALID_JSON` | JSON.parse |
| schema_version < 3 | `SCHEMA.VERSION_OUTDATED` | 字段比较 |
| 缺少必填字段 | `SCHEMA.MISSING_FIELDS` | 字段集合差 |
| CHECK_MODE=false (replay/sim) | `POLICY.CHECK_MODE_DISABLED` | 字段检查 |
| Failure 缺少 rule_id | `SCHEMA.FAILURE_INCOMPLETE` | 字段检查 |
| 直接运行 pytest/ruff/mypy | `POLICY.COMMAND_BLACKLISTED` | 命令日志 |

### G.2 需要人工审查的违规

| 场景 | 建议 |
|-----|------|
| 修改 coverage_exceptions.yml | 必须在 PR 中说明理由 |
| 修改 V2_REQUIRED_SCENARIOS.yml | 必须说明为何调整验收标准 |
| 跳过必须场景 | 必须说明临时豁免原因 |

---

## H. 故障排除

### H.1 常见 POLICY_VIOLATION

**问题**: `SCHEMA.VERSION_OUTDATED`
**原因**: 旧版代码生成的报告
**解决**: 更新 `ci_gate.py` / `sim_gate.py` 使用 v3 schema

**问题**: `POLICY.CHECK_MODE_DISABLED`
**原因**: replay/sim 未启用 CHECK_MODE
**解决**: 使用 `python -m src.trading.replay` 入口（自动启用）

**问题**: `SCHEMA.FAILURE_INCOMPLETE`
**原因**: 失败报告缺少 rule_id/component
**解决**: 更新 `add_failure()` 调用，提供完整参数

### H.2 调试命令

```powershell
# 查看违规报告
Get-Content artifacts\claude\policy_violation.json | ConvertFrom-Json

# 查看命令日志
Get-Content artifacts\claude\commands.log -Tail 20

# 查看轮次摘要
Get-Content artifacts\claude\round_summary.json | ConvertFrom-Json
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 1.0 | 2025-01-14 | 初始版本 |
| 2.0 | 2025-01-14 | 添加 hints、50 行 summary |
| **3.0** | **2025-01-15** | **军规级升级：schema v3、POLICY_VIOLATION、审计日志** |
