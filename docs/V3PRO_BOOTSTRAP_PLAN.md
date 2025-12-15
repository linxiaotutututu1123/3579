# V3PRO+ 军规级目录结构创建计划

> **原则**: V3PRO+ = V3PRO+ 策略层 (B-Models) + V2 其他层升级 (A-Platform)
>
> **策略层保持不动**，仅升级平台基础设施层

---

## 〇、架构总览

```text
V3PRO+ 完整架构
┌─────────────────────────────────────────────────────────────────┐
│  A-Platform（V2 升级到 V3PRO+ 标准）                            │
│  ├─ src/market/         ← V2 Phase A+C 市场数据层               │
│  ├─ src/execution/auto/ ← V2 Phase B 执行可靠性                 │
│  ├─ src/execution/protection/ ← V2 Phase B 保护层              │
│  ├─ src/execution/pair/ ← V2 Phase D 套利工程门槛               │
│  ├─ src/guardian/       ← V2 Guardian 无人值守                  │
│  ├─ src/audit/          ← V2 Audit 审计与回放                   │
│  ├─ src/cost/           ← V3PRO+ 新增 成本模型统一库            │
│  └─ src/replay/verifier.py ← V2 Audit 回放验证                  │
├─────────────────────────────────────────────────────────────────┤
│  B-Models（保持不动）                                           │
│  └─ src/strategy/*      ← 现有策略代码不动                      │
│      ├─ fallback.py     ← 需创建（A-Platform 框架）             │
│      └─ calendar_arb/   ← 需创建（B-Models 新策略）             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 一、Phase 1: 市场数据层 `src/market/` (V2 Phase A+C)

### 1.1 文件清单

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `instrument_cache.py` | INST.CACHE.LOAD, INST.CACHE.PERSIST | market.instrument_cache | 合约信息缓存 |
| 3 | `universe_selector.py` | UNIV.DOMINANT.*, UNIV.SUBDOMINANT.*, UNIV.ROLL.*, UNIV.EXPIRY.* | market.universe_selector | 主力/次主力选择 |
| 4 | `quote_cache.py` | MKT.STALE.SOFT, MKT.STALE.HARD | market.quote_cache | 行情缓存+stale检测 |
| 5 | `subscriber.py` | MKT.SUBSCRIBER.DIFF_UPDATE | market.subscriber | 订阅集差分更新 |
| 6 | `bar_builder.py` | MKT.CONTINUITY.BARS, MKT.CONTINUITY.INTRADAY_STABLE | market.bar_builder | 连续主力bars |
| 7 | `liquidity_gate.py` | MKT.GATE.LIQUIDITY | market.liquidity_gate | 流动性门控 |
| 8 | `quality.py` | MKT.QUALITY.OUTLIER, MKT.QUALITY.GAP, MKT.QUALITY.DISORDER | market.quality | 数据质量检测 |

### 1.2 V2 场景覆盖

| V2 rule_id | 描述 | 优先级 |
|------------|------|--------|
| INST.CACHE.LOAD | 合约信息加载 | P0 |
| INST.CACHE.PERSIST | 合约信息原子落盘 | P0 |
| UNIV.DOMINANT.BASIC | 主力合约选择 | P0 |
| UNIV.SUBDOMINANT.PAIRING | 次主力配对 | P0 |
| UNIV.ROLL.COOLDOWN | 主力切换冷却 | P1 |
| UNIV.EXPIRY.GATE | 临期合约排除 | P1 |
| MKT.SUBSCRIBER.DIFF_UPDATE | 订阅差分更新 | P0 |
| MKT.STALE.SOFT | 软stale检测 | P0 |
| MKT.STALE.HARD | 硬stale检测 | P0 |
| MKT.CONTINUITY.BARS | 连续主力bars | P1 |
| MKT.CONTINUITY.INTRADAY_STABLE | 日内主力稳定 | P1 |
| MKT.CONTINUITY.ROLLOVER_NO_FLAP | 换月不抖动 | P1 |
| MKT.GATE.LIQUIDITY | 流动性门控 | P0 |
| MKT.QUALITY.OUTLIER | 异常值检测 | P1 |
| MKT.QUALITY.GAP | 行情间隙检测 | P1 |
| MKT.QUALITY.DISORDER | 时间乱序检测 | P1 |

**共 8 个文件，覆盖 16 个 V2 场景**

---

## 二、Phase 2: 执行层 `src/execution/` (V2 Phase B+D)

### 2.1 `src/execution/auto/` (新目录 - Phase B 核心)

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `order_context.py` | EXEC.ID.MAPPING | execution.order_context | 订单标识映射 (local_id, order_ref, order_sys_id) |
| 3 | `exec_context.py` | EXEC.CONTEXT.TRACKING | execution.exec_context | 调仓上下文 (exec_id) |
| 4 | `fsm.py` | FSM.STRICT.*, FSM.TOLERANT.*, FSM.CANCEL_WHILE_FILL, FSM.STATUS_4_MAPPING | execution.fsm | 订单状态机 |
| 5 | `auto_order_engine.py` | EXEC.ENGINE.PIPELINE, EXEC.TIMEOUT.*, EXEC.CANCEL_REPRICE.*, EXEC.PARTIAL.*, EXEC.RETRY.* | execution.auto_order_engine | 自动订单引擎 |
| 6 | `position_tracker.py` | POS.TRACKER.*, POS.RECONCILE.* | execution.position_tracker | 持仓追踪+对账 |

### 2.2 V2 Phase B 场景覆盖

| V2 rule_id | 描述 | 优先级 |
|------------|------|--------|
| EXEC.ID.MAPPING | 订单标识映射完整 | P0 |
| FSM.STRICT.TRANSITIONS | 严格模式FSM覆盖所有转移 | P0 |
| FSM.TOLERANT.IDEMPOTENT | 容错模式FSM幂等处理 | P0 |
| FSM.CANCEL_WHILE_FILL | 撤单途中成交处理 | P0 |
| FSM.STATUS_4_MAPPING | OrderStatus='4'正确映射 | P0 |
| EXEC.ENGINE.PIPELINE | 订单提交管线完整 | P0 |
| EXEC.TIMEOUT.ACK | Ack超时处理 | P0 |
| EXEC.TIMEOUT.FILL | Fill超时处理 | P0 |
| EXEC.CANCEL_REPRICE.TIMEOUT | 追价超时撤单 | P1 |
| EXEC.PARTIAL.REPRICE | 部分成交追价补单 | P1 |
| EXEC.RETRY.BACKOFF | 重试指数退避 | P1 |
| EXEC.CONTEXT.TRACKING | ExecContext追踪调仓意图 | P0 |
| POS.TRACKER.TRADE_DRIVEN | 按trade更新持仓 | P0 |
| POS.RECONCILE.PERIODIC | 定期对账 | P0 |
| POS.RECONCILE.AFTER_DISCONNECT | 断连后对账 | P0 |
| POS.RECONCILE.FAIL_ACTION | 对账失败动作 | P0 |

**共 6 个文件，覆盖 16 个 V2 场景**

---

### 2.3 `src/execution/protection/` (新目录 - Phase B 保护层)

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `liquidity.py` | EXEC.PROTECTION.LIQUIDITY | execution.protection | 流动性保护 (盘口/spread) |
| 3 | `fat_finger.py` | EXEC.PROTECTION.FATFINGER | execution.protection | 乌龙指保护 (手数/名义/价格) |
| 4 | `throttle.py` | EXEC.PROTECTION.THROTTLE | execution.protection | 频率限制 |
| 5 | `audit.py` | EXEC.PROTECTION.AUDIT | execution.protection | 保护层审计事件 |

### 2.4 V2 Protection 场景覆盖

| V2 rule_id | 描述 | 优先级 |
|------------|------|--------|
| EXEC.PROTECTION.LIQUIDITY | 流动性保护生效 | P0 |
| EXEC.PROTECTION.FATFINGER | 胖手指保护生效 | P0 |
| EXEC.PROTECTION.THROTTLE | 节流保护生效 | P0 |
| EXEC.PROTECTION.AUDIT | 保护拒单有审计事件 | P0 |

**共 5 个文件，覆盖 4 个 V2 场景**

---

### 2.5 `src/execution/pair/` (新目录 - Phase D 套利门槛)

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `pair_executor.py` | PAIR.EXECUTOR.ATOMIC, PAIR.ROLLBACK.*, PAIR.AUTOHEDGE.* | execution.pair_executor | 双腿执行器 |
| 3 | `imbalance_detector.py` | PAIR.IMBALANCE.DETECT | execution.pair_executor | 腿不平衡检测 |

### 2.6 V2 Phase D 场景覆盖

| V2 rule_id | 描述 | 优先级 |
|------------|------|--------|
| PAIR.EXECUTOR.ATOMIC | 双腿原子性提交 | P0 |
| PAIR.ROLLBACK.ON_LEG_FAIL | 单腿失败回滚 | P0 |
| PAIR.AUTOHEDGE.DELTA_NEUTRAL | 自动对冲保持delta neutral | P0 |
| PAIR.IMBALANCE.DETECT | 腿不平衡检测 | P0 |
| PAIR.BREAKER.STOP_Z | 止损熔断 | P1 |

**共 3 个文件，覆盖 5 个 V2 场景**

---

## 三、Phase 3: Guardian 层 `src/guardian/` (V2 Guardian)

### 3.1 文件清单

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `state_machine.py` | GUARD.FSM.TRANSITIONS | guardian.state_machine | 状态机 |
| 3 | `detector.py` | GUARD.DETECT.* | guardian.detector | 异常检测器 |
| 4 | `actions.py` | GUARD.ACTION.* | guardian.actions | 动作执行 |
| 5 | `recovery.py` | GUARD.RECOVERY.COLD_START | guardian.recovery | 冷启动恢复 |
| 6 | `monitor.py` | - | guardian.monitor | 主监控器（整合） |

### 3.2 状态机定义 (V2 对齐)

```python
class GuardianState(Enum):
    INIT = "init"
    RUNNING = "running"
    REDUCE_ONLY = "reduce_only"
    HALTED = "halted"
    MANUAL = "manual"
    COOLDOWN = "cooldown"  # V3PRO+ 新增
```

### 3.3 状态转移图

```text
INIT → RUNNING ↔ REDUCE_ONLY → HALTED → MANUAL
         ↑                        ↓
         └──── COOLDOWN ──────────┘
```

### 3.4 V2 Guardian 场景覆盖

| V2 rule_id | 描述 | 优先级 |
|------------|------|--------|
| GUARD.FSM.TRANSITIONS | Guardian状态机转移 | P0 |
| GUARD.DETECT.QUOTE_STALE | 行情stale检测 | P0 |
| GUARD.DETECT.ORDER_STUCK | 订单卡住检测 | P0 |
| GUARD.DETECT.POSITION_DRIFT | 持仓漂移检测 | P0 |
| GUARD.DETECT.LEG_IMBALANCE | 腿不平衡检测 | P0 |
| GUARD.ACTION.SET_MODE | set_mode动作 | P0 |
| GUARD.ACTION.CANCEL_ALL | cancel_all动作 | P0 |
| GUARD.ACTION.FLATTEN_ALL | flatten_all动作 | P1 |
| GUARD.RECOVERY.COLD_START | 冷启动恢复流程 | P0 |

**共 6 个文件，覆盖 9 个 V2 场景**

---

## 四、Phase 4: 审计层 `src/audit/` (V2 Audit)

### 4.1 文件清单

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `event.py` | AUDIT.EVENT.STRUCTURE | audit.event | 事件结构定义 |
| 3 | `writer.py` | AUDIT.JSONL.FORMAT | audit.writer | JSONL写入 |
| 4 | `correlation.py` | AUDIT.CORRELATION.RUN_EXEC | audit.correlation | run_id/exec_id关联 |
| 5 | `decision_log.py` | - | audit.decision_log | DecisionEvent (V3PRO+新增) |
| 6 | `guardian_log.py` | - | audit.guardian_log | GuardianEvent |
| 7 | `pnl_attribution.py` | - | audit.pnl_attribution | PnL归因 (V3PRO+新增) |

### 4.2 V2 Audit 场景覆盖

| V2 rule_id | 描述 | 优先级 |
|------------|------|--------|
| AUDIT.EVENT.STRUCTURE | 审计事件结构完整 | P0 |
| AUDIT.JSONL.FORMAT | JSONL格式正确 | P0 |
| AUDIT.CORRELATION.RUN_EXEC | run_id/exec_id关联正确 | P0 |
| REPLAY.DETERMINISTIC.DECISION | 回放决策确定性 | P0 |
| REPLAY.DETERMINISTIC.GUARDIAN | 回放Guardian确定性 | P0 |

**共 7 个文件，覆盖 5 个 V2 场景**

---

## 五、Phase 5: 回放验证 `src/replay/verifier.py`

### 5.1 文件

| # | 文件 | V2 rule_id | component | 说明 |
|---|------|------------|-----------|------|
| 1 | `verifier.py` | REPLAY.DETERMINISTIC.* | replay.verifier | 回放验证器 |

### 5.2 功能要求

- 同 inputs 产生同 DecisionEvent 序列
- protection 拒单原因一致
- guardian 状态迁移一致

**共 1 个文件**

---

## 六、Phase 6: 成本模型 `src/cost/` (V3PRO+ 新增)

### 6.1 文件清单

| # | 文件 | V3PRO+ rule_id | component | 说明 |
|---|------|----------------|-----------|------|
| 1 | `__init__.py` | - | - | 导出 |
| 2 | `estimator.py` | COST.FEE.ESTIMATE, COST.SLIPPAGE.ESTIMATE, COST.IMPACT.ESTIMATE, COST.EDGE.GATE | cost.estimator | 成本估计器 |

### 6.2 V3PRO+ 成本场景

| V3PRO+ rule_id | 描述 | 优先级 |
|----------------|------|--------|
| COST.FEE.ESTIMATE | 手续费正确估计 | P0 |
| COST.SLIPPAGE.ESTIMATE | 滑点正确估计 | P0 |
| COST.IMPACT.ESTIMATE | 市场冲击正确估计 | P1 |
| COST.EDGE.GATE | 统一edge gate检查 | P0 |

**共 2 个文件，覆盖 4 个 V3PRO+ 新增场景**

---

## 七、策略层补全 `src/strategy/` (B-Models 桥接)

### 7.1 需创建的文件

| # | 文件 | 说明 | 归属 |
|---|------|------|------|
| 1 | `fallback.py` | 降级框架 | A-Platform (框架) |
| 2 | `calendar_arb/__init__.py` | 套利策略导出 | B-Models (新策略) |
| 3 | `calendar_arb/strategy.py` | 套利策略主体 | B-Models |
| 4 | `calendar_arb/kalman_beta.py` | Kalman滤波 | B-Models |

### 7.2 已存在的文件 (不动)

```text
src/strategy/
├── base.py            ✅ 已存在
├── factory.py         ✅ 已存在
├── simple_ai.py       ✅ 已存在
├── linear_ai.py       ✅ 已存在
├── ensemble_moe.py    ✅ 已存在
├── dl_torch_policy.py ✅ 已存在
├── top_tier_trend_risk_parity.py ✅ 已存在
├── types.py           ✅ 已存在
├── explain.py         ✅ 已存在
└── dl/                ✅ 已存在
```

**共 4 个文件需创建**

---

## 八、完整统计

| Phase | 目录 | 文件数 | V2 场景 | V3PRO+ 新增 |
|-------|------|--------|---------|-------------|
| 1 | src/market/ | 8 | 16 | - |
| 2.1 | src/execution/auto/ | 6 | 16 | - |
| 2.2 | src/execution/protection/ | 5 | 4 | - |
| 2.3 | src/execution/pair/ | 3 | 5 | - |
| 3 | src/guardian/ | 6 | 9 | 1 (COOLDOWN) |
| 4 | src/audit/ | 7 | 5 | 2 (decision_log, pnl) |
| 5 | src/replay/ | 1 | 2 | - |
| 6 | src/cost/ | 2 | - | 4 |
| 7 | src/strategy/ | 4 | - | 1 (fallback) |
| **总计** | **9 个目录** | **42 个文件** | **57** | **8** |

---

## 九、执行顺序

```text
Phase 1: src/market/         (依赖: 无)
    ↓
Phase 2.1: src/execution/auto/  (依赖: 无)
    ↓
Phase 2.2: src/execution/protection/ (依赖: 无)
    ↓
Phase 2.3: src/execution/pair/ (依赖: 无)
    ↓
Phase 3: src/guardian/       (依赖: execution.fsm)
    ↓
Phase 4: src/audit/          (依赖: 无)
    ↓
Phase 5: src/replay/verifier.py (依赖: audit)
    ↓
Phase 6: src/cost/           (依赖: 无)
    ↓
Phase 7: src/strategy/fallback.py + calendar_arb/ (依赖: 全部)
```

---

## 十、验收检查点

| 检查点 | 命令 | 预期结果 |
|--------|------|----------|
| ① 语法检查 | `ruff check src/` | All checks passed |
| ② 导入测试 | `python -c "from src.market import InstrumentCache"` | 无报错 |
| ③ 导入测试 | `python -c "from src.execution.auto import AutoOrderEngine"` | 无报错 |
| ④ 导入测试 | `python -c "from src.execution.protection import LiquidityGate"` | 无报错 |
| ⑤ 导入测试 | `python -c "from src.execution.pair import PairExecutor"` | 无报错 |
| ⑥ 导入测试 | `python -c "from src.guardian import GuardianMonitor"` | 无报错 |
| ⑦ 导入测试 | `python -c "from src.audit import AuditWriter"` | 无报错 |
| ⑧ 导入测试 | `python -c "from src.cost import CostEstimator"` | 无报错 |
| ⑨ 导入测试 | `python -c "from src.strategy.fallback import FallbackManager"` | 无报错 |
| ⑩ CI 通过 | `.\scripts\claude_loop.ps1 -Mode full` | Exit 0 |

---

## 十一、骨架代码模板

```python
"""
{module_name} - {description}

V3PRO+ Platform Component
V2 Scenarios: {v2_rule_ids}
V3PRO+ Scenarios: {v3pro_rule_ids}
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # 类型导入


class {ClassName}:
    """
    {description}
    
    军规级要求:
    - {requirement_1}
    - {requirement_2}
    """
    
    def __init__(self) -> None:
        raise NotImplementedError("TODO: implement")
```

---

## 十二、V2 → V3PRO+ rule_id 映射

| V2 rule_id | V3PRO+ rule_id | 归属 |
|------------|----------------|------|
| MKT.STALE.HARD | PROT.LIQUIDITY.HARD_STALE | A-Platform.capability |
| EXEC.PROTECTION.LIQUIDITY | PROT.LIQUIDITY.DEPTH_GATE | A-Platform.capability |
| EXEC.PROTECTION.FATFINGER | PROT.FATFINGER.MAX_QTY | A-Platform.capability |
| EXEC.PROTECTION.THROTTLE | PROT.THROTTLE.RATE_LIMIT | A-Platform.capability |
| FSM.STRICT.TRANSITIONS | EXEC.FSM.STRICT_TRANSITIONS | A-Platform.capability |
| GUARD.FSM.TRANSITIONS | GUARD.STATE_MACHINE.TRANSITIONS | A-Platform.capability |
| GUARD.ACTION.SET_MODE | GUARD.ACTION.SET_MODE | A-Platform.capability |
| GUARD.ACTION.CANCEL_ALL | GUARD.ACTION.CANCEL_ALL | A-Platform.capability |
| GUARD.ACTION.FLATTEN_ALL | GUARD.ACTION.FLATTEN_ALL | A-Platform.capability |
| AUDIT.JSONL.FORMAT | AUDIT.JSONL.FORMAT | A-Platform.capability |
| AUDIT.EVENT.STRUCTURE | AUDIT.EVENT.COMPLETE | A-Platform.capability |
| PAIR.EXECUTOR.ATOMIC | PAIR.EXEC.SERIAL | A-Platform.capability |
| PAIR.IMBALANCE.DETECT | PAIR.EXEC.LEG_MISMATCH | A-Platform.capability |

---

## 十三、下一步

确认本计划后，执行：

```powershell
# 按 Phase 顺序创建 42 个骨架文件
# 每个 Phase 完成后验证导入
# 最后运行 CI 验证
```

---

**文档版本**: v1.0
**创建时间**: 2025-12-15
**状态**: 待确认
