# V2 SPEC 差距分析报告 (Gap Analysis)

> **生成日期**：2025-12-15  
> **对照规格**：V2_SPEC_EXPANDED_NOT_RUSHING_LAUNCH_Version2.md  
> **目标**：识别当前代码与 V2 SPEC 的差距，指导下一步开发

---

## 差距总览

| 模块 | V2 SPEC 要求 | 当前状态 | 差距等级 |
|------|-------------|---------|---------|
| `src/market/` | 合约化行情三层架构 | ❌ 模块不存在 | 🔴 严重缺失 |
| `src/guardian/` | 无人值守四件必做事 | ❌ 模块不存在 | 🔴 严重缺失 |
| `src/audit/` | 结构化 JSONL 审计事件流 | ❌ 模块不存在 | 🔴 严重缺失 |
| `src/execution/auto/` | 全自动下单引擎 | ❌ 子模块不存在 | 🔴 严重缺失 |
| `src/execution/protection/` | 执行保护（三件套） | ❌ 子模块不存在 | 🔴 严重缺失 |
| `src/execution/pair/` | 套利双腿原子执行 | ❌ 子模块不存在 | 🟡 Phase D |
| FSM 状态机 | 严格 CTP 状态机 | 🟡 简单版 `order_tracker.py` | 🟠 需升级 |
| 订单标识映射 | local_id/order_ref/order_sys_id | 🟡 部分实现 | 🟠 需补全 |
| PositionTracker | 双源同步+reconcile | ❌ 不存在 | 🔴 严重缺失 |

---

## 详细差距分析

### 1. 🔴 src/market/ （合约化行情）

**V2 SPEC 要求**（Phase A + C）：

| 文件 | 职责 | 状态 |
|-----|------|------|
| `instrument_cache.py` | 全量合约元数据缓存 | ❌ 缺失 |
| `universe.py` | 主力/次主力动态选择 | ❌ 缺失 |
| `subscription.py` | 行情按需订阅管理 | ❌ 缺失 |
| `l1_cache.py` | L1 行情缓存 + stale 检测 | ❌ 缺失 |
| `product_mapper.py` | 品种→合约映射 | ❌ 缺失 |

**当前实现**：
- 无 `src/market/` 目录
- 策略层直接使用品种级 MarketState（AO/SA/LC）
- 无合约级行情支持，无法做跨期套利

**差距影响**：
- ❌ 无法获取合约级行情（AO2501 vs AO2505）
- ❌ 无法做跨期套利
- ❌ 无主力切换逻辑
- ❌ 无行情 stale 检测

---

### 2. 🔴 src/guardian/ （无人值守守护）

**V2 SPEC 要求**（Phase E）：

| 文件 | 职责 | 状态 |
|-----|------|------|
| `monitor.py` | 守护主循环 + 系统状态机 | ❌ 缺失 |
| `quote_stale.py` | 行情超时检测 → reduce-only/halt | ❌ 缺失 |
| `order_stuck.py` | 卡单检测 → cancel + degraded | ❌ 缺失 |
| `position_drift.py` | 仓位漂移检测 → halt + reconcile | ❌ 缺失 |
| `leg_imbalance.py` | 套利裸腿检测 → auto_hedge | ❌ 缺失 |

**当前实现**：
- 有 `src/trading/live_guard.py`（需检查是否符合 V2）

**差距影响**：
- ❌ 无系统级状态机（RUNNING/REDUCE_ONLY/HALTED）
- ❌ 无四件必做事的自动化守护

---

### 3. 🔴 src/audit/ （审计事件流）

**V2 SPEC 要求**（Phase F）：

| 事件类型 | 必备字段 | 状态 |
|---------|---------|------|
| `DecisionEvent` | ts, run_id, target, model_version | ❌ 缺失 |
| `ExecEvent` | ts, exec_id, plan | ❌ 缺失 |
| `OrderStateEvent` | order_id, state_from, state_to, event | ❌ 缺失 |
| `TradeEvent` | trade_id, price, volume | ❌ 缺失 |
| `GuardianEvent` | state_from, state_to, trigger | ❌ 缺失 |

**当前实现**：
- `sim_gate.py` 有 events.jsonl 输出
- 无统一的 Audit 模块

**差距影响**：
- ❌ 无法完整回放审计
- ❌ 无法追踪订单全生命周期

---

### 4. 🟠 src/execution/ FSM 状态机

**V2 SPEC 要求**：

```python
class OrderState(Enum):
    CREATED = "created"
    WAITING = "waiting"           # 等待 CTP Ack
    PENDING = "pending"           # 已挂单
    PARTIAL_FILLED = "partial"
    FILLED = "filled"
    CANCEL_SUBMITTING = "cancel_submitting"
    CANCEL_PENDING = "cancel_pending"
    CANCELLED = "cancelled"
    PARTIAL_CANCELLED = "partial_cancelled"
    ERROR = "error"
```

**当前实现**（`order_tracker.py`）：

```python
class OrderState(str, Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
```

**差距**：
- ❌ 缺少 `CANCEL_SUBMITTING`、`CANCEL_PENDING` 状态
- ❌ 缺少 `WAITING`（等待 CTP Ack）
- ❌ 缺少 `ERROR` 状态
- ❌ 缺少 `PARTIAL_CANCELLED`（部分成交后撤单）
- ❌ 无状态转移表 `TRANSITIONS`
- ❌ 无 strict/tolerant 模式支持

---

### 5. 🔴 src/execution/auto/ （全自动下单引擎）

**V2 SPEC 要求**：

| 文件 | 职责 | 状态 |
|-----|------|------|
| `state_machine.py` | 严格 FSM（对齐 CTP） | ❌ 缺失 |
| `engine.py` | AutoOrderEngine 主引擎 | ❌ 缺失 |
| `recovery.py` | 自动恢复引擎 | ❌ 缺失 |
| `timeout.py` | 超时策略（ack/fill/cancel） | ❌ 缺失 |
| `retry.py` | 重试/追价逻辑 | ❌ 缺失 |
| `position_tracker.py` | 本地+柜台同步 | ❌ 缺失 |

**当前实现**：
- `order_tracker.py` 仅提供基础跟踪
- 无超时/重试/追价逻辑
- 无 PositionTracker

---

### 6. 🔴 src/execution/protection/ （执行保护三件套）

**V2 SPEC 要求**：

| 文件 | 职责 | 检查项 | 状态 |
|-----|------|-------|------|
| `liquidity.py` | 流动性检查 | 盘口存在、spread、volume | ❌ 缺失 |
| `fat_finger.py` | 防乌龙指 | 手数、名义、价格偏离 | ❌ 缺失 |
| `throttle.py` | 频率限制 | 每分钟订单数、最小间隔 | ❌ 缺失 |

**当前实现**：
- `src/risk/` 目录下可能有部分实现
- 无统一的 protection 子模块

---

### 7. 🟡 订单标识映射

**V2 SPEC 要求**：

```python
@dataclass
class OrderContext:
    local_id: str           # UUID，系统内部主键
    order_ref: str          # CTP OrderRef，place_order 返回
    order_sys_id: str       # 交易所系统号，OnRtnOrder 补齐
    front_id: int
    session_id: int
    exchange_id: str
```

**当前实现**（`order_types.py`）：

```python
@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: Side
    offset: Offset
    price: float
    qty: int
    reason: str = ""
```

**差距**：
- ❌ 无 `local_id`
- ❌ 无 `order_ref`
- ❌ 无 `order_sys_id`
- ❌ 无 CTP 标识映射

---

## 已对齐的部分 ✅

| 模块 | V2 要求 | 当前状态 |
|------|--------|---------|
| 策略层 | 品种级 MarketState | ✅ 已实现 |
| 策略接口 | `on_tick(state) -> TargetPortfolio` | ✅ 已实现 |
| 五策略 | SimpleAI/LinearAI/DL/MoE/TopTier | ✅ 已实现 |
| Broker Protocol | `place_order`, `cancel_order` | ✅ 已实现 |
| Flatten Executor | 平仓执行器 | ✅ 已实现 |
| CI Gate | 军规级 CI 报告 | ✅ 已实现 |
| Sim Gate | Replay/Sim 报告 | ✅ 已实现 |
| events.jsonl | 事件输出路径分离 | ✅ 已实现 |

---

## 优先级排序（Phase 顺序）

### Phase A（接口冻结 + Replay-first）⏳ 部分完成

| 任务 | 优先级 | 状态 |
|-----|--------|------|
| types/protocols 定稿 | P0 | 🟡 部分 |
| Instrument Cache | P1 | ❌ 缺失 |
| Universe Selector | P1 | ❌ 缺失 |
| 订单标识映射补全 | P0 | ❌ 缺失 |

### Phase B（执行可靠性）❌ 未开始

| 任务 | 优先级 | 状态 |
|-----|--------|------|
| FSM 升级（V2 状态） | P0 | ❌ 缺失 |
| AutoOrderEngine | P0 | ❌ 缺失 |
| Protection 三件套 | P1 | ❌ 缺失 |
| PositionTracker | P1 | ❌ 缺失 |

### Phase C（市场侧连续性）❌ 未开始

依赖 Phase A 的 market 模块

### Phase D（套利工程门槛）❌ 未开始

依赖 Phase B 的执行层

### Phase E（Guardian 无人值守）❌ 未开始

| 任务 | 优先级 | 状态 |
|-----|--------|------|
| 系统状态机 | P0 | ❌ 缺失 |
| 四件必做事 | P0 | ❌ 缺失 |

### Phase F（审计与回放）❌ 未开始

| 任务 | 优先级 | 状态 |
|-----|--------|------|
| Audit 模块 | P1 | ❌ 缺失 |
| 回放一致性校验 | P1 | ❌ 缺失 |

---

## 下一步建议

### 立即行动（本周）

1. **创建 `src/market/` 骨架**
   - `__init__.py`
   - `instrument_cache.py`（InstrumentInfo dataclass）
   - `types.py`（L1Quote, BookTop）

2. **创建 `src/execution/auto/` 骨架**
   - `state_machine.py`（V2 状态 + TRANSITIONS）
   - `types.py`（OrderContext）

3. **创建 `src/guardian/` 骨架**
   - `types.py`（GuardianState enum）
   - `monitor.py`（状态机框架）

4. **创建 `src/audit/` 骨架**
   - `types.py`（事件 dataclass）
   - `writer.py`（JSONL writer）

### 短期目标（两周）

1. FSM 升级到 V2 状态定义
2. Protection 三件套实现
3. Instrument Cache + Universe Selector 基础实现

### 中期目标（一个月）

1. Guardian 四件必做事
2. PositionTracker + reconcile
3. Audit 完整事件流

---

## 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 1.0 | 2025-12-15 | 初始 Gap Analysis |
