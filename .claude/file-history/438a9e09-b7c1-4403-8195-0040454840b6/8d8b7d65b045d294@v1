# V4PRO 自动闭环系统报告 - 军规级自动化运维

> **文档版本**: v4.0 SUPREME AUTOMATION
> **生成日期**: 2025-12-16
> **文档等级**: 最高机密 - 军规级
> **Schema版本**: v4.0
> **退出码范围**: 0-20

---

## 目录

- [§1 系统概述](#1-系统概述)
- [§2 退出码标准](#2-退出码标准)
- [§3 Schema定义](#3-schema定义)
- [§4 CI报告规范](#4-ci报告规范)
- [§5 SIM报告规范](#5-sim报告规范)
- [§6 闭环流程](#6-闭环流程)
- [§7 命令日志规范](#7-命令日志规范)
- [§8 轮次摘要规范](#8-轮次摘要规范)
- [§9 策略违规检测](#9-策略违规检测)
- [§10 中国期货市场合规检查](#10-中国期货市场合规检查)
- [§11 实验性策略门禁检查](#11-实验性策略门禁检查)
- [§12 告警与通知](#12-告警与通知)
- [§13 自动恢复机制](#13-自动恢复机制)
- [§14 脚本实现](#14-脚本实现)
- [§15 验收标准](#15-验收标准)

---

## §1 系统概述

### 1.1 设计目标

```
V4PRO 自动闭环系统设计目标：
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 无人值守自动化运行                                                │
│ 2. 军规级错误检测与恢复                                              │
│ 3. 完整的审计追溯能力                                                │
│ 4. 中国期货市场合规保障                                              │
│ 5. 实验性策略安全门禁                                                │
│ 6. 多层次告警与通知                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     V4PRO 自动闭环系统架构                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │  CI 门禁    │───▶│  SIM 门禁   │───▶│  PROD 部署  │            │
│   │ (schema v4) │    │ (scenario)  │    │ (canary)    │            │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘            │
│          │                  │                  │                    │
│          ▼                  ▼                  ▼                    │
│   ┌─────────────────────────────────────────────────────┐          │
│   │              审计日志层 (JSONL)                      │          │
│   │     commands.log · round_summary · ci_report        │          │
│   └─────────────────────────────────────────────────────┘          │
│          │                  │                  │                    │
│          ▼                  ▼                  ▼                    │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │  策略违规   │    │  合规检查   │    │  门禁检查   │            │
│   │   检测器    │    │ (2025新规)  │    │ (实验性)    │            │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘            │
│          │                  │                  │                    │
│          └──────────────────┼──────────────────┘                    │
│                             ▼                                       │
│                      ┌─────────────┐                                │
│                      │  告警系统   │                                │
│                      │ (多渠道)    │                                │
│                      └─────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2025-12-14 | 初始版本，退出码0-6 |
| v2.0 | 2025-12-15 | 添加退出码7-12 |
| v3.0 | 2025-12-15 | Schema升级，添加场景验证 |
| **v4.0** | **2025-12-16** | **退出码13-20，中国期货市场合规** |

---

## §2 退出码标准

### 2.1 退出码总表

| 退出码 | 名称 | 描述 | 严重级别 | 自动恢复 |
|--------|------|------|----------|----------|
| 0 | SUCCESS | 全部通过 | INFO | - |
| 1 | GENERAL_ERROR | 通用错误 | ERROR | 否 |
| 2 | LINT_FAIL | Ruff检查失败 | ERROR | 是 |
| 3 | TYPE_FAIL | Mypy检查失败 | ERROR | 是 |
| 4 | TEST_FAIL | Pytest失败 | ERROR | 是 |
| 5 | COVERAGE_FAIL | 覆盖率不足 | WARNING | 是 |
| 6 | BUILD_FAIL | 构建失败 | ERROR | 否 |
| 7 | DEPENDENCY_FAIL | 依赖安装失败 | ERROR | 是 |
| 8 | CONFIG_FAIL | 配置错误 | ERROR | 否 |
| 9 | SIM_FAIL | 仿真门禁失败 | ERROR | 否 |
| 10 | SCENARIO_MISSING | 场景缺失 | ERROR | 是 |
| 11 | SCHEMA_INVALID | Schema无效 | ERROR | 否 |
| **12** | **POLICY_VIOLATION** | **策略违规** | **FATAL** | **否** |
| **13** | **COMPLIANCE_FAIL** | **合规检查失败** | **FATAL** | **否** |
| **14** | **ANCHOR_DRIFT** | **锚点漂移** | **WARNING** | **是** |
| **15** | **MARGIN_INSUFFICIENT** | **保证金不足** | **FATAL** | **否** |
| **16** | **LIMIT_PRICE_TRIGGER** | **涨跌停触发** | **WARNING** | **是** |
| **17** | **EXP_GATE_FAIL** | **实验性门禁失败** | **ERROR** | **否** |
| **18** | **MATURITY_INSUFFICIENT** | **成熟度不足** | **ERROR** | **否** |
| **19** | **NIGHT_SESSION_ERROR** | **夜盘跨日错误** | **ERROR** | **是** |
| **20** | **REPORT_CANCEL_EXCEED** | **报撤单频率超限** | **FATAL** | **否** |

### 2.2 退出码分类

```
退出码分类：
┌─────────────────────────────────────────────────────────────────────┐
│ 0:       成功                                                       │
│ 1-6:     CI基础检查 (lint/type/test/coverage/build)                 │
│ 7-8:     环境问题 (dependency/config)                               │
│ 9-11:    仿真门禁 (sim/scenario/schema)                             │
│ 12:      策略违规 (最严重，不可自动恢复)                             │
│ 13-20:   中国期货市场特化检查 (v4.0新增)                             │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 退出码详细说明

#### 退出码 12: POLICY_VIOLATION

```
触发条件：
- 违反军规 M1-M20 任一条
- 检测到禁止的命令或操作
- 上传了调试文件到生产环境
- JSON路径格式不符合规范
- 命令白名单之外的操作

处理措施：
- 立即停止所有操作
- 记录违规详情到审计日志
- 发送FATAL级别告警
- 需要人工介入处理
- 不允许自动恢复
```

#### 退出码 13: COMPLIANCE_FAIL

```
触发条件：
- 程序化交易备案检查失败
- 算法备案记录不完整
- 违反2025年新规要求
- 技术系统合规检查失败

处理措施：
- 暂停程序化交易
- 记录合规违规详情
- 通知合规部门
- 需要人工审核后恢复
```

#### 退出码 15: MARGIN_INSUFFICIENT

```
触发条件：
- 保证金使用率 ≥ 100%
- 追加保证金通知未响应
- 强平预警触发

处理措施：
- 立即停止开仓
- 按优先级平仓释放保证金
- 发送FATAL告警
- 记录保证金状态
- 需要资金补充后恢复
```

#### 退出码 20: REPORT_CANCEL_EXCEED

```
触发条件：
- 5秒内报撤单 ≥ 50笔
- 日内报撤单 ≥ 20000笔
- 被判定为高频交易

处理措施：
- 立即停止所有报撤单
- 记录违规时间和数量
- 通知合规部门
- 等待下一交易日自动恢复
- 或人工确认后恢复
```

---

## §3 Schema定义

### 3.1 CI报告Schema (v4.0)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CI Report Schema v4.0",
  "type": "object",
  "required": [
    "schema_version",
    "timestamp",
    "run_id",
    "exit_code",
    "checks"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "4.0"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "run_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
    },
    "exit_code": {
      "type": "integer",
      "minimum": 0,
      "maximum": 20
    },
    "checks": {
      "type": "object",
      "properties": {
        "lint": {
          "$ref": "#/definitions/check_result"
        },
        "type_check": {
          "$ref": "#/definitions/check_result"
        },
        "test": {
          "$ref": "#/definitions/check_result"
        },
        "coverage": {
          "$ref": "#/definitions/coverage_result"
        },
        "policy": {
          "$ref": "#/definitions/check_result"
        },
        "compliance": {
          "$ref": "#/definitions/compliance_result"
        },
        "maturity": {
          "$ref": "#/definitions/maturity_result"
        }
      },
      "required": ["lint", "type_check", "test", "coverage", "policy"]
    },
    "metadata": {
      "type": "object",
      "properties": {
        "branch": {"type": "string"},
        "commit": {"type": "string"},
        "author": {"type": "string"},
        "duration_ms": {"type": "integer"}
      }
    }
  },
  "definitions": {
    "check_result": {
      "type": "object",
      "required": ["passed", "message"],
      "properties": {
        "passed": {"type": "boolean"},
        "message": {"type": "string"},
        "details": {"type": "array", "items": {"type": "string"}}
      }
    },
    "coverage_result": {
      "type": "object",
      "required": ["passed", "percentage", "threshold"],
      "properties": {
        "passed": {"type": "boolean"},
        "percentage": {"type": "number", "minimum": 0, "maximum": 100},
        "threshold": {"type": "number", "minimum": 0, "maximum": 100},
        "uncovered_files": {"type": "array", "items": {"type": "string"}}
      }
    },
    "compliance_result": {
      "type": "object",
      "required": ["passed", "checks"],
      "properties": {
        "passed": {"type": "boolean"},
        "checks": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["rule_id", "passed"],
            "properties": {
              "rule_id": {"type": "string"},
              "passed": {"type": "boolean"},
              "message": {"type": "string"}
            }
          }
        }
      }
    },
    "maturity_result": {
      "type": "object",
      "required": ["passed", "strategies"],
      "properties": {
        "passed": {"type": "boolean"},
        "strategies": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["name", "maturity_score", "can_activate"],
            "properties": {
              "name": {"type": "string"},
              "maturity_score": {"type": "number", "minimum": 0, "maximum": 100},
              "can_activate": {"type": "boolean"},
              "training_days": {"type": "integer"}
            }
          }
        }
      }
    }
  }
}
```

### 3.2 SIM报告Schema (v4.0)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SIM Report Schema v4.0",
  "type": "object",
  "required": [
    "schema_version",
    "timestamp",
    "run_id",
    "exit_code",
    "scenarios",
    "summary"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "4.0"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "run_id": {
      "type": "string"
    },
    "exit_code": {
      "type": "integer",
      "minimum": 0,
      "maximum": 20
    },
    "scenarios": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/scenario_result"
      }
    },
    "summary": {
      "type": "object",
      "required": ["total", "passed", "failed", "skipped"],
      "properties": {
        "total": {"type": "integer"},
        "passed": {"type": "integer"},
        "failed": {"type": "integer"},
        "skipped": {"type": "integer"},
        "pass_rate": {"type": "number"}
      }
    },
    "china_futures": {
      "$ref": "#/definitions/china_futures_result"
    }
  },
  "definitions": {
    "scenario_result": {
      "type": "object",
      "required": ["rule_id", "component", "passed"],
      "properties": {
        "rule_id": {"type": "string"},
        "component": {"type": "string"},
        "passed": {"type": "boolean"},
        "evidence": {"type": "string"},
        "duration_ms": {"type": "integer"},
        "military_rule": {"type": "string"}
      }
    },
    "china_futures_result": {
      "type": "object",
      "properties": {
        "exchange_config": {"type": "boolean"},
        "limit_price_check": {"type": "boolean"},
        "margin_monitor": {"type": "boolean"},
        "night_session": {"type": "boolean"},
        "compliance_check": {"type": "boolean"},
        "report_cancel_rate": {
          "type": "object",
          "properties": {
            "5s_count": {"type": "integer"},
            "daily_count": {"type": "integer"},
            "within_limit": {"type": "boolean"}
          }
        }
      }
    }
  }
}
```

---

## §4 CI报告规范

### 4.1 报告文件路径

```
报告路径规范：
├── reports/
│   ├── ci/
│   │   ├── ci_report_{run_id}_{date}.json
│   │   └── ci_summary_{date}.json
│   ├── sim/
│   │   ├── sim_report_{run_id}_{date}.json
│   │   └── sim_summary_{date}.json
│   └── compliance/
│       ├── compliance_{run_id}_{date}.json
│       └── maturity_{run_id}_{date}.json
```

### 4.2 报告生成示例

```python
def generate_ci_report(
    run_id: str,
    checks: dict,
    exit_code: int,
) -> dict:
    """生成CI报告 (Schema v4.0)"""

    report = {
        "schema_version": "4.0",
        "timestamp": datetime.now().isoformat(),
        "run_id": run_id,
        "exit_code": exit_code,
        "checks": {
            "lint": {
                "passed": checks.get("lint_passed", False),
                "message": checks.get("lint_message", ""),
                "details": checks.get("lint_details", []),
            },
            "type_check": {
                "passed": checks.get("type_passed", False),
                "message": checks.get("type_message", ""),
            },
            "test": {
                "passed": checks.get("test_passed", False),
                "message": checks.get("test_message", ""),
                "details": checks.get("test_failures", []),
            },
            "coverage": {
                "passed": checks.get("coverage_passed", False),
                "percentage": checks.get("coverage_pct", 0),
                "threshold": 85.0,
            },
            "policy": {
                "passed": checks.get("policy_passed", False),
                "message": checks.get("policy_message", ""),
            },
        },
        "metadata": {
            "branch": checks.get("branch", "unknown"),
            "commit": checks.get("commit", "unknown"),
            "duration_ms": checks.get("duration_ms", 0),
        },
    }

    return report
```

### 4.3 CI门禁顺序

```
CI门禁执行顺序：
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: Ruff Check (lint)                                           │
│         └─ 失败: exit 2                                             │
│ Step 2: Ruff Format (format)                                        │
│         └─ 失败: exit 2                                             │
│ Step 3: Mypy (type)                                                 │
│         └─ 失败: exit 3                                             │
│ Step 4: Pytest (test)                                               │
│         └─ 失败: exit 4                                             │
│ Step 5: Coverage Check                                              │
│         └─ < 85%: exit 5                                            │
│ Step 6: Policy Check                                                │
│         └─ 违规: exit 12                                            │
│ Step 7: Compliance Check (v4.0新增)                                 │
│         └─ 失败: exit 13                                            │
│ Step 8: Maturity Check (v4.0新增)                                   │
│         └─ 失败: exit 17/18                                         │
│ Step 9: 生成报告                                                    │
│         └─ 成功: exit 0                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## §5 SIM报告规范

### 5.1 必过场景列表

```yaml
# scripts/v4_required_scenarios.yml

version: "4.0"
description: "V4PRO必过场景列表"

required_scenarios:
  # Phase A: 基础设施 (15)
  - INFRA.CI.GATE_PASS
  - INFRA.CI.LINT_PASS
  - INFRA.CI.TYPE_PASS
  - INFRA.CI.TEST_PASS
  - INFRA.CI.COVERAGE_MIN
  - INFRA.SIM.GATE_PASS
  - INFRA.SIM.SCENARIO_ALL
  - INFRA.CTP.CONNECT
  - INFRA.CTP.AUTH
  - INFRA.CTP.SUBSCRIBE
  - INFRA.CTP.RECONNECT
  - INFRA.CONFIG.LOAD
  - INFRA.CONFIG.VALIDATE
  - INFRA.CONFIG.ENV_ISOLATE
  - INFRA.LOG.FORMAT

  # Phase B: 行情层 (12)
  - MKT.SUBSCRIBER.DIFF_UPDATE
  - MKT.SUBSCRIBER.CALLBACK
  - MKT.SUBSCRIBER.CLEAR
  - MKT.CACHE.INSTRUMENT_INFO
  - MKT.CACHE.EXPIRE_CHECK
  - MKT.CACHE.UPDATE
  - MKT.TICK.BUFFER_OVERFLOW
  - MKT.TICK.TIMESTAMP_ORDER
  - MKT.KLINE.BUILD_CORRECT
  - MKT.KLINE.GAP_HANDLE
  - MKT.SNAPSHOT.CAPTURE
  - MKT.SNAPSHOT.RESTORE

  # Phase C: 审计层 (18)
  - AUDIT.EVENT.STRUCTURE
  - AUDIT.EVENT.JSONL_FORMAT
  - AUDIT.CORRELATION.RUN_EXEC
  - AUDIT.WRITER.PROPERTIES
  - AUDIT.WRITER.CLOSE_BEHAVIOR
  - AUDIT.WRITER.CONTEXT_MANAGER
  - AUDIT.VALIDATE.MISSING_TS
  - AUDIT.VALIDATE.MISSING_TYPE
  - AUDIT.VALIDATE.REQUIRED_FIELDS
  - AUDIT.DICT.WRITE
  - AUDIT.DICT.MISSING_REQUIRED
  - AUDIT.READ.EMPTY_FILE
  - AUDIT.READ.CORRUPTED
  - AUDIT.EXPORT.CSV
  - AUDIT.EXPORT.PARQUET
  - AUDIT.COMPRESS.GZIP
  - AUDIT.RETENTION.POLICY
  - AUDIT.SIGNAL_SOURCE.TRACK

  # Phase D: 策略降级 (12)
  - STRAT.FALLBACK.ON_EXCEPTION
  - STRAT.FALLBACK.ON_TIMEOUT
  - STRAT.FALLBACK.CHAIN_DEFINED
  - ARB.KALMAN.BETA_ESTIMATE
  - ARB.KALMAN.RESIDUAL_ZSCORE
  - ARB.KALMAN.BETA_BOUND
  - ARB.LEGS.FIXED_NEAR_FAR
  - ARB.SIGNAL.HALF_LIFE_GATE
  - ARB.SIGNAL.STOP_Z_BREAKER
  - ARB.SIGNAL.EXPIRY_GATE
  - ARB.SIGNAL.CORRELATION_BREAK
  - ARB.COST.ENTRY_GATE

  # Phase E: 回放验证 (2)
  - REPLAY.DETERMINISTIC.DECISION
  - REPLAY.DETERMINISTIC.GUARDIAN

  # Phase H: 实验性门禁 (8)
  - EXP.MATURITY.80_THRESHOLD
  - EXP.MATURITY.60_DIMENSION
  - EXP.MATURITY.90_DAYS
  - EXP.GATE.NO_BYPASS
  - EXP.GATE.MANUAL_APPROVAL
  - EXP.MONITOR.PROGRESS
  - EXP.MONITOR.ALERT
  - EXP.MONITOR.ETA

exemptions:
  # 非核心豁免列表 (必须带原因)
  - rule_id: "DL.LSTM.PREDICT"
    reason: "B类模型Phase 6待实现"
  - rule_id: "RL.PPO.ACTION"
    reason: "B类模型Phase 6待实现"
```

### 5.2 场景验证逻辑

```python
def validate_required_scenarios(
    report: dict,
    required: list[str],
) -> tuple[bool, list[str]]:
    """验证必过场景"""

    passed_scenarios = {
        s["rule_id"]
        for s in report["scenarios"]
        if s["passed"]
    }

    missing = [
        rule_id
        for rule_id in required
        if rule_id not in passed_scenarios
    ]

    return len(missing) == 0, missing
```

---

## §6 闭环流程

### 6.1 完整闭环流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                      V4PRO 自动闭环流程                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────┐                                                       │
│   │  开始   │                                                       │
│   └────┬────┘                                                       │
│        ▼                                                            │
│   ┌─────────┐    失败    ┌─────────┐                               │
│   │ CI门禁  │───────────▶│自动修复 │──┐                            │
│   └────┬────┘            └─────────┘  │                            │
│        │ 通过                         │ 重试                        │
│        ▼                              │                             │
│   ┌─────────┐    失败    ┌─────────┐  │                            │
│   │SIM门禁  │───────────▶│分析失败 │◀─┘                            │
│   └────┬────┘            └────┬────┘                               │
│        │ 通过                 │ 不可修复                            │
│        ▼                      ▼                                     │
│   ┌─────────┐            ┌─────────┐                               │
│   │合规检查 │            │人工介入 │                               │
│   └────┬────┘            └─────────┘                               │
│        │ 通过                                                       │
│        ▼                                                            │
│   ┌─────────┐    失败    ┌─────────┐                               │
│   │门禁检查 │───────────▶│策略隔离 │                               │
│   │(实验性) │            │(B轨)    │                               │
│   └────┬────┘            └─────────┘                               │
│        │ 通过                                                       │
│        ▼                                                            │
│   ┌─────────┐                                                       │
│   │生成报告 │                                                       │
│   └────┬────┘                                                       │
│        ▼                                                            │
│   ┌─────────┐                                                       │
│   │ 部署    │                                                       │
│   └────┬────┘                                                       │
│        ▼                                                            │
│   ┌─────────┐                                                       │
│   │  结束   │                                                       │
│   └─────────┘                                                       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 轮次执行逻辑

```python
class ClaudeLoop:
    """CLAUDE自动闭环执行器"""

    MAX_ROUNDS = 10
    MAX_RETRY_PER_CHECK = 3

    def __init__(self):
        self.round = 0
        self.commands_log: list[dict] = []
        self.violations: list[dict] = []

    def run(self) -> int:
        """执行闭环流程"""

        while self.round < self.MAX_ROUNDS:
            self.round += 1
            self._log_round_start()

            # Step 1: CI门禁
            ci_result = self._run_ci_gate()
            if not ci_result.passed:
                if ci_result.can_auto_fix:
                    self._auto_fix(ci_result)
                    continue
                else:
                    return ci_result.exit_code

            # Step 2: SIM门禁
            sim_result = self._run_sim_gate()
            if not sim_result.passed:
                if sim_result.missing_scenarios:
                    self._report_missing(sim_result)
                return sim_result.exit_code

            # Step 3: 合规检查
            compliance_result = self._run_compliance_check()
            if not compliance_result.passed:
                self._handle_compliance_violation(compliance_result)
                return 13

            # Step 4: 实验性门禁
            maturity_result = self._run_maturity_check()
            if not maturity_result.passed:
                self._isolate_immature_strategies(maturity_result)
                # 继续执行，只是隔离策略

            # Step 5: 生成报告
            self._generate_reports()

            # Step 6: 成功
            self._log_round_end(success=True)
            return 0

        # 超过最大轮次
        return 1

    def _log_round_start(self) -> None:
        """记录轮次开始"""
        self.commands_log.append({
            "event": "ROUND_START",
            "round": self.round,
            "timestamp": datetime.now().isoformat(),
        })

    def _log_round_end(self, success: bool) -> None:
        """记录轮次结束"""
        self.commands_log.append({
            "event": "ROUND_END",
            "round": self.round,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        })
```

---

## §7 命令日志规范

### 7.1 日志格式

```json
{
  "timestamp": "2025-12-16T10:30:00.000Z",
  "round": 1,
  "event": "COMMAND_EXECUTE",
  "command": "ruff check .",
  "exit_code": 0,
  "duration_ms": 1234,
  "stdout_lines": 10,
  "stderr_lines": 0
}
```

### 7.2 日志事件类型

| 事件类型 | 描述 |
|----------|------|
| `ROUND_START` | 轮次开始 |
| `ROUND_END` | 轮次结束 |
| `COMMAND_EXECUTE` | 命令执行 |
| `CHECK_PASS` | 检查通过 |
| `CHECK_FAIL` | 检查失败 |
| `AUTO_FIX` | 自动修复 |
| `VIOLATION_DETECT` | 违规检测 |
| `ALERT_SEND` | 告警发送 |
| `COMPLIANCE_CHECK` | 合规检查 |
| `MATURITY_CHECK` | 成熟度检查 |

### 7.3 命令白名单

```python
COMMAND_WHITELIST = [
    # Ruff
    r"^ruff check",
    r"^ruff format",

    # Mypy
    r"^mypy \.",
    r"^mypy src/",

    # Pytest
    r"^pytest",
    r"^python -m pytest",

    # 脚本
    r"^python scripts/validate_policy\.py",
    r"^python scripts/sim_gate\.py",
    r"^python scripts/coverage_gate\.py",

    # Git (只读)
    r"^git status",
    r"^git log",
    r"^git diff",

    # 其他
    r"^python -c",
    r"^pip install -r",
]

# 禁止的命令模式
COMMAND_BLACKLIST = [
    r"rm -rf",
    r"sudo",
    r"curl.*\|.*bash",
    r"wget.*\|.*sh",
    r"git push --force",
    r"git reset --hard",
]
```

---

## §8 轮次摘要规范

### 8.1 摘要格式

```json
{
  "round_summary": {
    "round": 1,
    "start_time": "2025-12-16T10:30:00.000Z",
    "end_time": "2025-12-16T10:35:00.000Z",
    "duration_ms": 300000,
    "exit_code": 0,
    "checks": {
      "lint": {"passed": true, "duration_ms": 5000},
      "type": {"passed": true, "duration_ms": 30000},
      "test": {"passed": true, "duration_ms": 180000, "test_count": 765},
      "coverage": {"passed": true, "percentage": 88.22},
      "policy": {"passed": true},
      "compliance": {"passed": true},
      "maturity": {"passed": true, "strategies_checked": 4}
    },
    "violations": [],
    "auto_fixes": []
  }
}
```

### 8.2 摘要生成

```python
def generate_round_summary(
    round_num: int,
    start_time: datetime,
    end_time: datetime,
    checks: dict,
    violations: list,
    auto_fixes: list,
) -> dict:
    """生成轮次摘要"""

    return {
        "round_summary": {
            "round": round_num,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            "exit_code": _calculate_exit_code(checks, violations),
            "checks": checks,
            "violations": violations,
            "auto_fixes": auto_fixes,
        }
    }
```

---

## §9 策略违规检测

### 9.1 违规类型

| 违规代码 | 描述 | 严重级别 |
|----------|------|----------|
| `POL001` | 禁止命令执行 | FATAL |
| `POL002` | 路径格式错误 | ERROR |
| `POL003` | 调试文件上传 | FATAL |
| `POL004` | Schema版本不匹配 | ERROR |
| `POL005` | 军规违反 | FATAL |
| `POL006` | 白名单外命令 | ERROR |
| `POL007` | 敏感信息泄露 | FATAL |

### 9.2 违规检测逻辑

```python
def detect_violations(
    commands: list[dict],
    files_modified: list[str],
) -> list[dict]:
    """检测策略违规"""

    violations = []

    for cmd in commands:
        # 检查禁止命令
        for pattern in COMMAND_BLACKLIST:
            if re.match(pattern, cmd["command"]):
                violations.append({
                    "code": "POL001",
                    "message": f"禁止命令: {cmd['command']}",
                    "severity": "FATAL",
                    "timestamp": cmd["timestamp"],
                })

        # 检查白名单外命令
        if not any(re.match(p, cmd["command"]) for p in COMMAND_WHITELIST):
            violations.append({
                "code": "POL006",
                "message": f"白名单外命令: {cmd['command']}",
                "severity": "ERROR",
                "timestamp": cmd["timestamp"],
            })

    for file_path in files_modified:
        # 检查路径格式
        if not file_path.replace("\\", "/").startswith(("src/", "tests/", "scripts/")):
            violations.append({
                "code": "POL002",
                "message": f"非法路径: {file_path}",
                "severity": "ERROR",
            })

        # 检查调试文件
        if any(pattern in file_path for pattern in [".debug", ".tmp", "__pycache__"]):
            violations.append({
                "code": "POL003",
                "message": f"调试文件: {file_path}",
                "severity": "FATAL",
            })

    return violations
```

---

## §10 中国期货市场合规检查

### 10.1 合规检查项

| 检查项 | 规则来源 | 检查方式 |
|--------|----------|----------|
| 程序化交易备案 | 2025年新规 | 配置验证 |
| 报撤单频率 | 5秒50笔 | 实时监控 |
| 高频交易判定 | 300笔/秒或2万笔/日 | 统计分析 |
| 大额订单复核 | 内部规定 | 流程检查 |
| 算法备案 | 交易所要求 | 配置验证 |

### 10.2 合规检查实现

```python
class ComplianceChecker:
    """中国期货市场合规检查器"""

    # 监管阈值
    REPORT_CANCEL_LIMIT_5S = 50
    HIGH_FREQ_LIMIT_PER_SEC = 300
    HIGH_FREQ_LIMIT_DAILY = 20000

    def check_all(self) -> ComplianceResult:
        """执行全部合规检查"""

        checks = []

        # 1. 程序化交易备案
        checks.append(self._check_registration())

        # 2. 报撤单频率
        checks.append(self._check_report_cancel_rate())

        # 3. 高频交易判定
        checks.append(self._check_high_freq())

        # 4. 算法备案
        checks.append(self._check_algo_registration())

        return ComplianceResult(
            passed=all(c["passed"] for c in checks),
            checks=checks,
        )

    def _check_report_cancel_rate(self) -> dict:
        """检查报撤单频率"""

        # 获取5秒窗口内的报撤单数
        count_5s = self._get_5s_count()

        return {
            "rule_id": "COMPLIANCE.REPORT_CANCEL",
            "passed": count_5s < self.REPORT_CANCEL_LIMIT_5S,
            "message": f"5秒报撤单: {count_5s}/{self.REPORT_CANCEL_LIMIT_5S}",
            "count": count_5s,
            "limit": self.REPORT_CANCEL_LIMIT_5S,
        }
```

### 10.3 合规告警等级

```python
class ComplianceLevel(Enum):
    """合规等级"""

    NORMAL = "正常"      # 正常交易
    WARNING = "预警"     # 接近阈值 (80%)
    CRITICAL = "临界"    # 接近上限 (95%)
    EXCEEDED = "超限"    # 已超限

def get_compliance_level(count: int, limit: int) -> ComplianceLevel:
    """获取合规等级"""

    ratio = count / limit
    if ratio < 0.8:
        return ComplianceLevel.NORMAL
    elif ratio < 0.95:
        return ComplianceLevel.WARNING
    elif ratio < 1.0:
        return ComplianceLevel.CRITICAL
    else:
        return ComplianceLevel.EXCEEDED
```

---

## §11 实验性策略门禁检查

### 11.1 门禁检查流程

```
实验性策略门禁检查流程：
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│   ┌─────────────┐                                                   │
│   │ 策略列表    │                                                   │
│   └──────┬──────┘                                                   │
│          ▼                                                          │
│   ┌─────────────┐     否     ┌─────────────┐                       │
│   │ 是实验性？  │───────────▶│ 跳过检查    │                       │
│   └──────┬──────┘            └─────────────┘                       │
│          │ 是                                                       │
│          ▼                                                          │
│   ┌─────────────┐     否     ┌─────────────┐                       │
│   │成熟度≥80%？ │───────────▶│ 隔离策略    │                       │
│   └──────┬──────┘            │ exit 18     │                       │
│          │ 是                └─────────────┘                       │
│          ▼                                                          │
│   ┌─────────────┐     否     ┌─────────────┐                       │
│   │维度≥60%？   │───────────▶│ 隔离策略    │                       │
│   └──────┬──────┘            │ exit 18     │                       │
│          │ 是                └─────────────┘                       │
│          ▼                                                          │
│   ┌─────────────┐     否     ┌─────────────┐                       │
│   │训练≥90天？  │───────────▶│ 隔离策略    │                       │
│   └──────┬──────┘            │ exit 18     │                       │
│          │ 是                └─────────────┘                       │
│          ▼                                                          │
│   ┌─────────────┐     否     ┌─────────────┐                       │
│   │人工审批？   │───────────▶│ 等待审批    │                       │
│   └──────┬──────┘            │ exit 17     │                       │
│          │ 是                └─────────────┘                       │
│          ▼                                                          │
│   ┌─────────────┐                                                   │
│   │ 允许启用    │                                                   │
│   └─────────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 门禁检查实现

```python
class MaturityChecker:
    """成熟度门禁检查器"""

    MATURITY_THRESHOLD = 0.80      # 总成熟度阈值
    DIMENSION_THRESHOLD = 0.60     # 维度阈值
    MIN_TRAINING_DAYS = 90         # 最低训练天数
    BYPASS_FORBIDDEN = True        # 禁止绕过

    def check_strategy(
        self,
        strategy_name: str,
        maturity_report: MaturityReport,
    ) -> MaturityCheckResult:
        """检查单个策略的成熟度"""

        reasons = []

        # 检查总成熟度
        if maturity_report.overall_score < self.MATURITY_THRESHOLD:
            reasons.append(
                f"总成熟度 {maturity_report.overall_score:.1%} < {self.MATURITY_THRESHOLD:.0%}"
            )

        # 检查各维度
        for dim_name, dim_score in maturity_report.dimension_scores.items():
            if dim_score < self.DIMENSION_THRESHOLD:
                reasons.append(
                    f"维度 {dim_name} {dim_score:.1%} < {self.DIMENSION_THRESHOLD:.0%}"
                )

        # 检查训练天数
        if maturity_report.training_days < self.MIN_TRAINING_DAYS:
            reasons.append(
                f"训练天数 {maturity_report.training_days} < {self.MIN_TRAINING_DAYS}"
            )

        # 检查人工审批
        if not maturity_report.manually_approved:
            reasons.append("未获得人工审批")

        return MaturityCheckResult(
            strategy_name=strategy_name,
            can_activate=len(reasons) == 0,
            maturity_score=maturity_report.overall_score,
            training_days=maturity_report.training_days,
            reasons=reasons,
        )
```

---

## §12 告警与通知

### 12.1 告警级别

| 级别 | 描述 | 通知方式 | 响应时间 |
|------|------|----------|----------|
| INFO | 信息通知 | 日志记录 | - |
| WARNING | 警告 | 邮件/钉钉 | 1小时 |
| ERROR | 错误 | 邮件/钉钉/短信 | 15分钟 |
| FATAL | 致命 | 电话/即时通讯 | 立即 |

### 12.2 告警规则

```python
ALERT_RULES = {
    # 退出码告警
    12: {"level": "FATAL", "message": "策略违规"},
    13: {"level": "FATAL", "message": "合规检查失败"},
    15: {"level": "FATAL", "message": "保证金不足"},
    20: {"level": "FATAL", "message": "报撤单频率超限"},

    # 阈值告警
    "coverage_drop": {"level": "WARNING", "threshold": 5.0},
    "test_fail_rate": {"level": "ERROR", "threshold": 0.01},
    "latency_high": {"level": "WARNING", "threshold": 100},
}
```

### 12.3 告警发送

```python
class AlertSender:
    """告警发送器"""

    def send(self, alert: Alert) -> None:
        """发送告警"""

        if alert.level == AlertLevel.INFO:
            self._log_only(alert)
        elif alert.level == AlertLevel.WARNING:
            self._send_email(alert)
            self._send_dingtalk(alert)
        elif alert.level == AlertLevel.ERROR:
            self._send_email(alert)
            self._send_dingtalk(alert)
            self._send_sms(alert)
        elif alert.level == AlertLevel.FATAL:
            self._send_all_channels(alert)
            self._trigger_oncall(alert)
```

---

## §13 自动恢复机制

### 13.1 可自动恢复的退出码

| 退出码 | 自动恢复方式 |
|--------|--------------|
| 2 | `ruff check --fix` |
| 3 | 分析错误，尝试类型注解 |
| 5 | 添加测试用例 |
| 7 | `pip install -r requirements.txt` |
| 10 | 生成缺失场景测试 |
| 14 | 更新锚点文档 |
| 16 | 撤销涨跌停订单 |
| 19 | 修正交易日归属 |

### 13.2 自动恢复逻辑

```python
AUTO_FIX_HANDLERS = {
    2: lambda: subprocess.run(["ruff", "check", ".", "--fix"]),
    5: lambda: generate_missing_tests(),
    7: lambda: subprocess.run(["pip", "install", "-r", "requirements.txt"]),
    14: lambda: update_anchor_document(),
    16: lambda: cancel_limit_orders(),
    19: lambda: fix_trading_day_assignment(),
}

def attempt_auto_fix(exit_code: int) -> bool:
    """尝试自动修复"""

    if exit_code not in AUTO_FIX_HANDLERS:
        return False

    try:
        handler = AUTO_FIX_HANDLERS[exit_code]
        handler()
        return True
    except Exception as e:
        log_error(f"自动修复失败: {e}")
        return False
```

---

## §14 脚本实现

### 14.1 主闭环脚本 (PowerShell)

```powershell
# scripts/claude_loop.ps1

param(
    [int]$MaxRounds = 10,
    [switch]$Strict,
    [switch]$NoAutoFix
)

$ErrorActionPreference = "Stop"

# 初始化
$RunId = [guid]::NewGuid().ToString()
$Round = 0
$CommandsLog = @()

function Write-CommandLog {
    param([string]$Event, [hashtable]$Data)

    $LogEntry = @{
        timestamp = (Get-Date -Format "o")
        round = $Round
        event = $Event
    } + $Data

    $script:CommandsLog += $LogEntry
}

function Run-CIGate {
    Write-CommandLog -Event "CHECK_START" -Data @{check = "ci"}

    # Ruff Check
    $result = & .venv/Scripts/python.exe -m ruff check .
    if ($LASTEXITCODE -ne 0) {
        if (-not $NoAutoFix) {
            & .venv/Scripts/python.exe -m ruff check . --fix
            if ($LASTEXITCODE -ne 0) { return 2 }
        } else {
            return 2
        }
    }

    # Ruff Format
    $result = & .venv/Scripts/python.exe -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { return 2 }

    # Mypy
    $result = & .venv/Scripts/python.exe -m mypy .
    if ($LASTEXITCODE -ne 0) { return 3 }

    # Pytest
    $result = & .venv/Scripts/python.exe -m pytest tests/ -q
    if ($LASTEXITCODE -ne 0) { return 4 }

    # Policy
    $result = & .venv/Scripts/python.exe scripts/validate_policy.py --all
    if ($LASTEXITCODE -ne 0) { return 12 }

    Write-CommandLog -Event "CHECK_PASS" -Data @{check = "ci"}
    return 0
}

function Run-ComplianceCheck {
    Write-CommandLog -Event "CHECK_START" -Data @{check = "compliance"}

    # 合规检查逻辑
    # ...

    Write-CommandLog -Event "CHECK_PASS" -Data @{check = "compliance"}
    return 0
}

# 主循环
while ($Round -lt $MaxRounds) {
    $Round++
    Write-CommandLog -Event "ROUND_START" -Data @{}

    # CI门禁
    $exitCode = Run-CIGate
    if ($exitCode -ne 0) {
        Write-CommandLog -Event "ROUND_END" -Data @{success = $false; exit_code = $exitCode}
        exit $exitCode
    }

    # 合规检查
    $exitCode = Run-ComplianceCheck
    if ($exitCode -ne 0) {
        Write-CommandLog -Event "ROUND_END" -Data @{success = $false; exit_code = $exitCode}
        exit $exitCode
    }

    # 成功
    Write-CommandLog -Event "ROUND_END" -Data @{success = $true; exit_code = 0}
    break
}

# 保存命令日志
$CommandsLog | ConvertTo-Json -Depth 10 | Out-File "reports/commands_$RunId.json"

exit 0
```

### 14.2 Python版闭环脚本

```python
#!/usr/bin/env python
"""claude_auto_loop.py - V4PRO自动闭环脚本"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def main() -> int:
    """主函数"""

    parser = argparse.ArgumentParser(description="V4PRO自动闭环")
    parser.add_argument("--max-rounds", type=int, default=10)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--no-auto-fix", action="store_true")
    args = parser.parse_args()

    run_id = str(uuid4())
    commands_log = []

    for round_num in range(1, args.max_rounds + 1):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "event": "ROUND_START",
        }
        commands_log.append(log_entry)

        # CI门禁
        exit_code = run_ci_gate(args.no_auto_fix)
        if exit_code != 0:
            save_log(commands_log, run_id)
            return exit_code

        # 合规检查
        exit_code = run_compliance_check()
        if exit_code != 0:
            save_log(commands_log, run_id)
            return exit_code

        # 成熟度检查
        exit_code = run_maturity_check()
        if exit_code != 0:
            save_log(commands_log, run_id)
            return exit_code

        # 成功
        commands_log.append({
            "timestamp": datetime.now().isoformat(),
            "round": round_num,
            "event": "ROUND_END",
            "success": True,
        })
        break

    save_log(commands_log, run_id)
    return 0


def run_ci_gate(no_auto_fix: bool) -> int:
    """运行CI门禁"""

    # Ruff Check
    result = subprocess.run(
        [".venv/Scripts/python.exe", "-m", "ruff", "check", "."],
        capture_output=True,
    )
    if result.returncode != 0:
        if not no_auto_fix:
            subprocess.run(
                [".venv/Scripts/python.exe", "-m", "ruff", "check", ".", "--fix"]
            )
            result = subprocess.run(
                [".venv/Scripts/python.exe", "-m", "ruff", "check", "."],
                capture_output=True,
            )
            if result.returncode != 0:
                return 2
        else:
            return 2

    # Mypy
    result = subprocess.run(
        [".venv/Scripts/python.exe", "-m", "mypy", "."],
        capture_output=True,
    )
    if result.returncode != 0:
        return 3

    # Pytest
    result = subprocess.run(
        [".venv/Scripts/python.exe", "-m", "pytest", "tests/", "-q"],
        capture_output=True,
    )
    if result.returncode != 0:
        return 4

    # Policy
    result = subprocess.run(
        [".venv/Scripts/python.exe", "scripts/validate_policy.py", "--all"],
        capture_output=True,
    )
    if result.returncode != 0:
        return 12

    return 0


def run_compliance_check() -> int:
    """运行合规检查"""
    # TODO: 实现合规检查
    return 0


def run_maturity_check() -> int:
    """运行成熟度检查"""
    # TODO: 实现成熟度检查
    return 0


def save_log(log: list, run_id: str) -> None:
    """保存命令日志"""
    path = Path(f"reports/commands_{run_id}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main())
```

---

## §15 验收标准

### 15.1 功能验收

- [ ] 退出码0-20全部定义正确
- [ ] CI报告Schema v4.0验证通过
- [ ] SIM报告Schema v4.0验证通过
- [ ] 命令日志格式正确
- [ ] 轮次摘要生成正确
- [ ] 策略违规检测生效
- [ ] 合规检查生效
- [ ] 成熟度检查生效
- [ ] 告警发送正确
- [ ] 自动恢复机制可用

### 15.2 性能验收

| 指标 | 要求 |
|------|------|
| CI门禁耗时 | < 5分钟 |
| SIM门禁耗时 | < 10分钟 |
| 合规检查耗时 | < 1秒 |
| 报告生成耗时 | < 5秒 |

### 15.3 安全验收

- [ ] 命令白名单生效
- [ ] 禁止命令拦截
- [ ] 敏感信息不泄露
- [ ] 审计日志完整

---

## 附录

### A. 退出码速查表

```
┌────────┬────────────────────┬──────────┐
│ 退出码 │ 名称               │ 严重级别 │
├────────┼────────────────────┼──────────┤
│ 0      │ SUCCESS            │ INFO     │
│ 1      │ GENERAL_ERROR      │ ERROR    │
│ 2      │ LINT_FAIL          │ ERROR    │
│ 3      │ TYPE_FAIL          │ ERROR    │
│ 4      │ TEST_FAIL          │ ERROR    │
│ 5      │ COVERAGE_FAIL      │ WARNING  │
│ 6      │ BUILD_FAIL         │ ERROR    │
│ 7      │ DEPENDENCY_FAIL    │ ERROR    │
│ 8      │ CONFIG_FAIL        │ ERROR    │
│ 9      │ SIM_FAIL           │ ERROR    │
│ 10     │ SCENARIO_MISSING   │ ERROR    │
│ 11     │ SCHEMA_INVALID     │ ERROR    │
│ 12     │ POLICY_VIOLATION   │ FATAL    │
│ 13     │ COMPLIANCE_FAIL    │ FATAL    │
│ 14     │ ANCHOR_DRIFT       │ WARNING  │
│ 15     │ MARGIN_INSUFFICIENT│ FATAL    │
│ 16     │ LIMIT_PRICE_TRIGGER│ WARNING  │
│ 17     │ EXP_GATE_FAIL      │ ERROR    │
│ 18     │ MATURITY_INSUFF    │ ERROR    │
│ 19     │ NIGHT_SESSION_ERROR│ ERROR    │
│ 20     │ REPORT_CANCEL_EXCEED│ FATAL   │
└────────┴────────────────────┴──────────┘
```

### B. Schema版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2025-12-14 | 初始版本 |
| v2.0 | 2025-12-15 | 添加scenario字段 |
| v3.0 | 2025-12-15 | 添加military_rule字段 |
| v4.0 | 2025-12-16 | 添加compliance/maturity |

---

**文档结束**

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│              V4PRO 自动闭环系统报告 - 军规级自动化                   │
│                                                                     │
│                    Schema v4.0 · 退出码 0-20                        │
│                                                                     │
│                    CLAUDE上校 2025-12-16                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
