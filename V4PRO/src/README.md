# V4PRO 源代码目录 (src/)

> **版本**: v4.3.0 军规级
> **军规覆盖**: M1-M20

---

## 架构概览 (10分钟理解)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        V4PRO 中国期货量化交易系统                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   market/   │───▶│  strategy/  │───▶│  execution/ │───▶│   broker/   │  │
│  │   行情层    │    │   策略层    │    │   执行层    │    │  Broker层   │  │
│  │   (M3)     │    │  (M4,M9)   │    │   (M1)     │    │   (M8)     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                 │                  │                  │          │
│         ▼                 ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         audit/ 审计层 (M3,M7)                        │   │
│  │                    JSONL + fsync + run_id/exec_id                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│         │                 │                  │                  │          │
│         ▼                 ▼                  ▼                  ▼          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         risk/ 风控层 (M6,M16)                        │   │
│  │                    VaR + 熔断 + 保证金监控                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  guardian/  │    │ compliance/ │    │  trading/   │    │  replay/    │  │
│  │   守护层    │    │   合规层    │    │   CI门禁    │    │   回放层    │  │
│  │ (M6,M13)   │    │   (M17)    │    │  (M1-M9)   │    │   (M7)     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 模块清单

| 目录 | 功能 | 军规覆盖 | 文件数 |
|------|------|----------|--------|
| `trading/` | CI门禁、退出码、CHECK_MODE | M1-M9 | 11 |
| `strategy/` | 策略框架、降级管理、套利策略 | M4,M9,M18 | 20+ |
| `audit/` | 审计日志、JSONL写入 | M3,M7 | 7 |
| `market/` | 行情订阅、交易所配置、夜盘日历 | M3,M15,M20 | 11 |
| `cost/` | 成本估计、手续费计算 | M4,M5,M14 | 3 |
| `risk/` | VaR计算、压力测试、风险归因、置信度评估 | M3,M6,M16,M19,M31 | 9 |
| `replay/` | 回放验证、SHA256哈希 | M7 | 3 |
| `guardian/` | 守护监控、中国触发器 | M6,M13,M15,M16 | 7 |
| `compliance/` | 程序化合规、报撤单节流 | M12,M17 | 3 |
| `execution/` | 订单执行、保护层 | M1,M4 | 20+ |
| `portfolio/` | 组合管理、持仓聚合 | M6 | 5 |
| `monitoring/` | 健康检查、指标收集 | M9 | 3 |

---

## 数据流向

```
行情数据 ──▶ market/ ──▶ strategy/ ──▶ execution/ ──▶ broker/
                │            │              │            │
                ▼            ▼              ▼            ▼
            audit/ ◀──────────────────────────────────────
                │
                ▼
            replay/ (回放验证M7)
```

---

## 快速开始

```python
# 1. 导入核心模块
from src.trading import ExitCode, enable_check_mode
from src.strategy import Strategy, FallbackManager
from src.audit import AuditWriter

# 2. 启用CHECK_MODE (CI/仿真必须)
enable_check_mode()

# 3. 创建策略
from src.strategy.calendar_arb import CalendarArbStrategy
strategy = CalendarArbStrategy(config)

# 4. 审计日志
writer = AuditWriter("audit.jsonl")
writer.write_decision(decision_event)
```

---

## 军规速查

| 军规 | 核心文件 | 说明 |
|------|----------|------|
| M1 | `trading/ci_gate.py` | CHECK_MODE阻止实盘 |
| M3 | `audit/writer.py` | JSONL+fsync审计 |
| M6 | `guardian/triggers.py` | 熔断保护 |
| M7 | `replay/verifier.py` | 回放一致性 |
| M13 | `execution/protection/limit_price.py` | 涨跌停感知 |
| M15 | `market/trading_calendar.py` | 夜盘日历 |
| M17 | `compliance/programmatic_trading.py` | 报撤单合规 |
| M31 | `risk/confidence.py` | 置信度检查 (v4.3) |

---

**军规级别国家伟大工程 - 源代码规范**
