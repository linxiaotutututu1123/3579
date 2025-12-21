# V4PRO 审计模块 (audit/)

> **版本**: v4.0.0 军规级
> **军规覆盖**: M3, M7

---

## 模块职责

审计模块是V4PRO系统的**合规记录中心**，负责：
- JSONL格式审计日志写入
- fsync强制刷盘保证（M3核心）
- 决策/订单/盈亏全链路追踪
- 回放验证数据准备

---

## 文件清单

| 文件 | 功能 | 军规覆盖 |
|------|------|----------|
| `writer.py` | JSONL写入器，fsync保证 | M3 |
| `decision_log.py` | 决策日志记录 | M3 |
| `order_trail.py` | 订单轨迹追踪 | M3 |
| `guardian_log.py` | 守护日志记录 | M3,M6 |
| `pnl_attribution.py` | 盈亏归因 | M7 |
| `replay_verifier.py` | 回放验证器 | M7 |

---

## 核心概念

### JSONL + fsync (M3)
```python
from src.audit import AuditWriter

# 创建审计写入器
writer = AuditWriter(
    path="artifacts/audit.jsonl",
    fsync=True  # 必须启用！
)

# 写入决策事件
writer.write_decision({
    "run_id": "20240101_001",
    "exec_id": "E001",
    "timestamp": "2024-01-01T09:30:00",
    "action": "BUY",
    "symbol": "rb2405",
    "quantity": 10
})

# 写入后立即fsync
writer.flush()
```

### 审计事件类型
| 类型 | 说明 | 必需字段 |
|------|------|----------|
| DECISION | 策略决策 | run_id, exec_id, action |
| ORDER | 订单事件 | order_id, status |
| FILL | 成交事件 | fill_id, price, qty |
| PNL | 盈亏事件 | realized, unrealized |
| GUARDIAN | 守护事件 | trigger_type, action |

---

## 日志格式

```json
{"ts":"2024-01-01T09:30:00.123","type":"DECISION","run_id":"R001","exec_id":"E001","data":{...}}
{"ts":"2024-01-01T09:30:00.456","type":"ORDER","order_id":"O001","status":"SUBMITTED","data":{...}}
{"ts":"2024-01-01T09:30:01.789","type":"FILL","fill_id":"F001","price":3850.0,"qty":10,"data":{...}}
```

---

## 回放验证 (M7)

```python
from src.audit import ReplayVerifier

# 创建验证器
verifier = ReplayVerifier(audit_path="artifacts/audit.jsonl")

# 验证回放一致性
result = verifier.verify(replay_output)
if not result.consistent:
    print(f"不一致: {result.diff}")
```

---

## 使用示例

```python
from src.audit import (
    AuditWriter,
    DecisionLog,
    OrderTrail
)

# 1. 初始化
writer = AuditWriter("audit.jsonl", fsync=True)
decision_log = DecisionLog(writer)
order_trail = OrderTrail(writer)

# 2. 记录决策
decision_log.log_decision(
    strategy="calendar_arb",
    signal=signal,
    context=market_context
)

# 3. 追踪订单
order_trail.track_order(order)
order_trail.track_fill(fill)

# 4. 确保写入
writer.close()
```

---

## 依赖关系

```
audit/
    │
    ├──◀ trading/    (交易事件)
    ├──◀ strategy/   (决策事件)
    ├──◀ execution/  (订单事件)
    └──▶ replay/     (回放数据)
```

---

**军规级别国家伟大工程 - 审计模块规范**
