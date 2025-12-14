# 合约化 + 跨期套利 + 无人值守 + 全自动下单 规格说明

> 版本：v1.0  
> 日期：2025-12-15  
> 状态：设计完成，待实现

---

## 0. 总原则（贯穿所有设计）

1. **不存在"最赚钱且不亏钱"**；顶级系统追求的是：**可控回撤、尾部风险可处理、长期期望为正**
2. "顶级"不是更复杂的模型，而是：**输入合约化、执行原子性/回滚、风控硬闸、可观测、可恢复、可回放审计**
3. 策略公式可以保持简单，真正决定生死的是：
   - **腿对一致性（套利）**
   - **断流/卡单/漂移** 的自动处理
   - **到期/换月/流动性 gate**

---

## 1. 问题诊断：为什么当前系统"跨期套利做不了"

### 1.1 现状

```python
# src/config.py
strategy_symbols: tuple[str, ...] = ("AO", "SA", "LC")  # 品种级
```

```python
# src/strategy/types.py
prices: Mapping[str, float]  # key = "AO", "SA", "LC"
```

### 1.2 问题

- 中国期货下单最终都是 **合约**（如 `AO2501`），跨期套利必须同时拿到 near/far 两个合约的价格与盘口
- 当前系统是 **品种级**（AO/SA/LC）价格输入，**无法构建 near-far spread**

### 1.3 结论

**必须先引入合约级行情与合约元数据。**

---

## 2. 合约化架构：三层设计

### 2.1 Level 1：Instrument Cache（必须）

**职责**：启动时拉取全量合约元数据

```python
# 启动时
instruments = ctp_api.ReqQryInstrument()

# 内存缓存
instrument_cache: dict[str, InstrumentInfo] = {}

# 落盘（原子写入：tmp → rename）
# artifacts/instruments/{exchange}_{trading_day}.json
```

**InstrumentInfo 字段**：

```python
@dataclass
class InstrumentInfo:
    symbol: str              # "AO2501"
    product: str             # "AO"
    exchange: str            # "CZCE"
    expire_date: str         # "20250115"
    tick_size: float         # 1.0
    multiplier: int          # 20
    long_margin_ratio: float
    short_margin_ratio: float
    is_trading: bool
```

**用途**：到期 gate、换月、主力/次主力候选池、合规限制、tick_size/multiplier 等

### 2.2 Level 2：Universe 选择（强烈建议）

**职责**：动态选择主力/次主力合约

```python
# 刷新频率：30~120 秒
# 规则：open_interest + volume + days_to_expiry gate + 流动性评分

# 输出
dominant: dict[str, str] = {"AO": "AO2505", "SA": "SA2509", ...}
subdominant: dict[str, str] = {"AO": "AO2509", "SA": "SA2601", ...}
subscribe_set: set[str] = {"AO2505", "AO2509", "SA2509", ...}
```

**要点**：
- 加 **hysteresis/cooldown** 避免主力频繁跳
- 每品种订阅 1~2 个合约（主力 + 次主力），最多 3 个

### 2.3 Level 3：行情订阅（按需）

**职责**：只订阅 `subscribe_set` 中的合约

```python
# 订阅
md_api.SubscribeMarketData(list(subscribe_set))

# roll 后
md_api.UnSubscribeMarketData(old_contracts)
md_api.SubscribeMarketData(new_contracts)
```

**L1 Cache**：

```python
@dataclass
class L1Quote:
    symbol: str
    bid: float
    ask: float
    bid_vol: int
    ask_vol: int
    last: float
    volume: int
    open_interest: int
    timestamp: float
    is_stale: bool = False  # 超时标记
```

---

## 3. 策略与执行的分层方案

### 3.1 方案 A（采用）：策略品种级，执行映射到合约级

```
策略层                     执行层
┌─────────────────┐       ┌─────────────────────────┐
│ TopTier/MoE/DL  │       │ Product→Contract 映射    │
│                 │       │                         │
│ 输出:           │  ──>  │ AO → dominant(AO)       │
│ {"AO": +1, ...} │       │     = AO2505            │
│                 │       │                         │
│ (不改)          │       │ 输出: {"AO2505": +1}    │
└─────────────────┘       └─────────────────────────┘
```

**优点**：
- 现有 5 个策略（SimpleAI/LinearAI/DlTorch/MoE/TopTier）不改
- 现有 CI / PAPER 风险最小
- 实盘真正下合约，符合中国期货交易现实

**注意**：
- roll 后 target 自动指向新主力
- 老合约若仍有仓位，由 rebalancer/close-then-open 渐进平掉

---

## 4. 跨期套利策略规格

### 4.1 策略名称

```python
STRATEGY_NAME = "cointegration_calendar_arb"  # 或 "spread_calendar_arb"
```

### 4.2 核心逻辑：自适应协整套利

```python
# 价格序列
p1 = log(mid_near)  # 近月
p2 = log(mid_far)   # 远月

# 滚动 OLS / Kalman 估计
# p1 ≈ α + β * p2
alpha, beta = rolling_ols(p1, p2, window=lookback)

# 残差
e = p1 - alpha - beta * p2

# z-score
z = (e - mean(e)) / std(e)
```

### 4.3 交易信号

| 条件 | 动作 |
|-----|------|
| `z > entry_z` (如 2.5) | 做空价差：卖近买远 |
| `z < -entry_z` | 做多价差：买近卖远 |
| `abs(z) < exit_z` (如 0.5) | 平仓 |
| `abs(z) > stop_z` (如 5~6) | 止损平仓 + 冷却 |

### 4.4 过滤条件

1. **半衰期过滤**：half-life 太长（如 > 20 天）= 不回归，不加仓
2. **到期 gate**：临近到期（如 < 5 天）→ reduce-only
3. **流动性 gate**：盘口 spread > 阈值 或 volume < 阈值 → reduce-only
4. **冷却期**：止损后 N 分钟内不开新仓

### 4.5 执行要求

- **PairExecutor**：腿对原子性
- **失败处理**：一腿成功另一腿失败 → 立即对冲/回滚
- **裸腿检测**：`leg_imbalance` → auto_hedge + 告警

---

## 5. 目录结构

```
src/
├── strategy/                  # 策略层（不改）
│   ├── simple_ai.py
│   ├── linear_ai.py
│   ├── dl_torch_policy.py
│   ├── ensemble_moe.py
│   ├── top_tier_trend_risk_parity.py
│   └── calendar_arb.py        # 新增：跨期套利策略
│
├── execution/
│   ├── broker.py              # Broker Protocol（已有）
│   ├── ctp_broker.py          # CTP Broker（已有）
│   ├── order_types.py         # Intent/Order 等（已有）
│   ├── order_tracker.py       # 订单追踪（建议与 FSM 融合）
│   ├── flatten_*.py           # FlattenExecutor 等（已有）
│   │
│   ├── auto/                  # 全自动下单（新增）
│   │   ├── __init__.py
│   │   ├── state_machine.py   # 严格 FSM（对齐 CTP）
│   │   ├── engine.py          # AutoOrderEngine
│   │   ├── recovery.py        # 自动恢复引擎
│   │   ├── timeout.py         # 超时策略
│   │   ├── retry.py           # 重试/追价
│   │   └── position_tracker.py# 本地+柜台同步
│   │
│   ├── protection/            # 执行保护（新增）
│   │   ├── __init__.py
│   │   ├── liquidity.py       # 流动性检查
│   │   ├── fat_finger.py      # 防乌龙指
│   │   └── throttle.py        # 频率限制
│   │
│   └── pair/                  # 套利执行器（新增）
│       ├── __init__.py
│       └── pair_executor.py   # 腿对原子执行
│
├── market/                    # 行情层（新增）
│   ├── __init__.py
│   ├── instrument_cache.py    # 合约元数据缓存
│   ├── universe.py            # 主力/次主力选择
│   ├── subscription.py        # 行情订阅管理
│   ├── l1_cache.py            # L1 行情缓存
│   └── product_mapper.py      # 品种→合约映射
│
├── guardian/                  # 无人值守守护（新增）
│   ├── __init__.py
│   ├── monitor.py             # 守护主循环
│   ├── quote_stale.py         # 行情超时检测
│   ├── order_stuck.py         # 卡单检测
│   ├── position_drift.py      # 仓位漂移检测
│   └── leg_imbalance.py       # 裸腿检测（套利）
│
├── audit/                     # 审计留痕（新增）
│   ├── __init__.py
│   ├── decision_log.py        # 策略决策日志
│   ├── order_trail.py         # 订单生命周期日志
│   └── replay_verifier.py     # 回放一致性校验
│
└── ...（其他已有模块）
```

---

## 6. CTP 报单/撤单语义

### 6.1 报单流程

```
ReqOrderInsert
    │
    ├── OnRspOrderInsert(错误) ──> 拒绝
    │
    └── OnRtnOrder (多次推送)
            │
            ├── OrderStatus = 'a' (待报)
            ├── OrderStatus = '3' (未成交还在队列)
            ├── OrderStatus = '1' (部分成交还在队列)
            ├── OrderStatus = '0' (全部成交)
            ├── OrderStatus = '5' (已撤单)
            ├── OrderStatus = '2' (部分成交不在队列)
            └── OrderStatus = '4' (未成交不在队列)
```

### 6.2 OrderStatus 映射

| CTP 状态码 | 含义 | 映射事件 |
|-----------|------|---------|
| 'a' | 未知(待报) | `RTN_PENDING` |
| '3' | 未成交还在队列 | `RTN_ACCEPTED` |
| '1' | 部分成交还在队列 | `RTN_PARTIAL_FILLED` |
| '0' | 全部成交 | `RTN_FILLED` |
| '5' | 已撤单 | `RTN_CANCELLED` |
| '2' | 部分成交不在队列 | `RTN_PARTIAL_CANCELLED` |
| '4' | 未成交不在队列 | `RTN_NOT_IN_QUEUE`（需特殊处理）|
| 'b' | 尚未触发 | 条件单，暂不支持 |
| 'c' | 已触发 | 条件单，暂不支持 |

### 6.3 撤单流程

```
ReqOrderAction
    │
    ├── OnRspOrderAction(错误) ──> 撤单拒绝
    │
    └── OnRtnOrder(OrderStatus='5') ──> 撤单成功
```

---

## 7. 订单严格状态机

### 7.1 状态定义

```python
class OrderState(Enum):
    # 初始态
    CREATED = "created"
    
    # 提交中
    SUBMITTING = "submitting"
    
    # 活跃态
    PENDING = "pending"           # 已报，等待成交
    PARTIAL_FILLED = "partial"    # 部分成交
    
    # 撤单中
    CANCEL_SUBMITTING = "cancel_submitting"
    
    # 恢复态
    QUERYING = "querying"         # 查询中（超时后）
    RETRY_PENDING = "retry_pending"     # 等待重试
    CHASE_PENDING = "chase_pending"     # 等待追价
    
    # 终态
    FILLED = "filled"
    CANCELLED = "cancelled"
    PARTIAL_CANCELLED = "partial_cancelled"
    CANCEL_REJECTED = "cancel_rejected"
    REJECTED = "rejected"
    ERROR = "error"
```

### 7.2 事件定义

```python
class OrderEvent(Enum):
    # 用户动作
    SUBMIT = "submit"
    CANCEL = "cancel"
    
    # CTP 回报
    RTN_PENDING = "rtn_pending"         # 待报
    RTN_ACCEPTED = "rtn_accepted"       # 已报
    RTN_REJECTED = "rtn_rejected"       # 报单拒绝
    RTN_PARTIAL_FILLED = "rtn_partial"  # 部分成交
    RTN_FILLED = "rtn_filled"           # 全部成交
    RTN_CANCELLED = "rtn_cancelled"     # 已撤单
    RTN_PARTIAL_CANCELLED = "rtn_partial_cancelled"
    RTN_CANCEL_REJECTED = "rtn_cancel_rejected"
    RTN_NOT_IN_QUEUE = "rtn_not_in_queue"  # OrderStatus='4'
    
    # 内部事件
    TIMEOUT_ACK = "timeout_ack"         # 确认超时
    TIMEOUT_FILL = "timeout_fill"       # 成交超时
    TIMEOUT_CANCEL = "timeout_cancel"   # 撤单超时
    QUERY_OK = "query_ok"               # 查询成功
    QUERY_FAIL = "query_fail"           # 查询失败
    RETRY = "retry"                     # 重试
    GIVE_UP = "give_up"                 # 放弃
```

### 7.3 状态转移表

```python
TRANSITIONS: dict[OrderState, dict[OrderEvent, OrderState]] = {
    OrderState.CREATED: {
        OrderEvent.SUBMIT: OrderState.SUBMITTING,
    },
    
    OrderState.SUBMITTING: {
        OrderEvent.RTN_PENDING: OrderState.PENDING,
        OrderEvent.RTN_ACCEPTED: OrderState.PENDING,
        OrderEvent.RTN_REJECTED: OrderState.REJECTED,
        OrderEvent.RTN_FILLED: OrderState.FILLED,  # 极速成交
        OrderEvent.TIMEOUT_ACK: OrderState.QUERYING,
    },
    
    OrderState.PENDING: {
        OrderEvent.RTN_PARTIAL_FILLED: OrderState.PARTIAL_FILLED,
        OrderEvent.RTN_FILLED: OrderState.FILLED,
        OrderEvent.CANCEL: OrderState.CANCEL_SUBMITTING,
        OrderEvent.TIMEOUT_FILL: OrderState.CANCEL_SUBMITTING,  # 超时先撤
        OrderEvent.RTN_NOT_IN_QUEUE: OrderState.ERROR,  # 无成交被踢出
    },
    
    OrderState.PARTIAL_FILLED: {
        OrderEvent.RTN_PARTIAL_FILLED: OrderState.PARTIAL_FILLED,
        OrderEvent.RTN_FILLED: OrderState.FILLED,
        OrderEvent.CANCEL: OrderState.CANCEL_SUBMITTING,
        OrderEvent.TIMEOUT_FILL: OrderState.CANCEL_SUBMITTING,
        OrderEvent.RTN_NOT_IN_QUEUE: OrderState.PARTIAL_CANCELLED,
    },
    
    OrderState.CANCEL_SUBMITTING: {
        OrderEvent.RTN_CANCELLED: OrderState.CANCELLED,
        OrderEvent.RTN_PARTIAL_CANCELLED: OrderState.PARTIAL_CANCELLED,
        OrderEvent.RTN_CANCEL_REJECTED: OrderState.CANCEL_REJECTED,
        OrderEvent.RTN_FILLED: OrderState.FILLED,  # 撤单途中成交
        OrderEvent.TIMEOUT_CANCEL: OrderState.QUERYING,
    },
    
    OrderState.QUERYING: {
        OrderEvent.QUERY_OK: OrderState.RETRY_PENDING,  # 查到状态后决定
        OrderEvent.QUERY_FAIL: OrderState.ERROR,
        OrderEvent.RTN_FILLED: OrderState.FILLED,
        OrderEvent.RTN_CANCELLED: OrderState.CANCELLED,
    },
    
    OrderState.RETRY_PENDING: {
        OrderEvent.RETRY: OrderState.SUBMITTING,
        OrderEvent.GIVE_UP: OrderState.ERROR,
    },
    
    OrderState.CHASE_PENDING: {
        OrderEvent.SUBMIT: OrderState.SUBMITTING,  # 追价新单
        OrderEvent.GIVE_UP: OrderState.ERROR,
    },
    
    # 终态：不接受任何事件（幂等忽略）
    OrderState.FILLED: {},
    OrderState.CANCELLED: {},
    OrderState.PARTIAL_CANCELLED: {},
    OrderState.CANCEL_REJECTED: {},
    OrderState.REJECTED: {},
    OrderState.ERROR: {},
}
```

### 7.4 关键补丁

1. **撤单途中成交**：`CANCEL_SUBMITTING + RTN_FILLED → FILLED`
2. **OrderStatus='4' 处理**：无成交→ERROR，有成交→PARTIAL_CANCELLED
3. **幂等处理**：终态收到事件 → ignore + log（不抛异常）
4. **成交量累计**：用 TradeID 去重，累加 filled_qty

---

## 8. 成交量处理

### 8.1 Order 数据结构

```python
@dataclass
class Order:
    order_id: str
    symbol: str
    direction: Direction
    offset: Offset
    price: float
    qty: int
    
    # 成交跟踪
    filled_qty: int = 0              # 累计成交量
    filled_amount: float = 0.0       # 累计成交金额
    avg_price: float = 0.0           # 成交均价
    
    # 去重
    processed_trades: set[str] = field(default_factory=set)
    
    # 状态
    state: OrderState = OrderState.CREATED
    
    # 时间戳
    create_time: float = 0.0
    submit_time: float = 0.0
    last_update_time: float = 0.0
    
    @property
    def unfilled_qty(self) -> int:
        return self.qty - self.filled_qty
    
    @property
    def is_fully_filled(self) -> bool:
        return self.filled_qty >= self.qty
    
    def apply_trade(self, trade_id: str, volume: int, price: float) -> bool:
        """应用成交回报，返回是否为新成交"""
        if trade_id in self.processed_trades:
            return False  # 重复
        
        self.processed_trades.add(trade_id)
        self.filled_qty += volume
        self.filled_amount += price * volume
        self.avg_price = self.filled_amount / self.filled_qty
        return True
```

### 8.2 事件生成

```python
def generate_fill_event(order: Order) -> OrderEvent:
    """根据成交情况生成正确的事件"""
    if order.filled_qty >= order.qty:
        return OrderEvent.RTN_FILLED
    elif order.filled_qty > 0:
        return OrderEvent.RTN_PARTIAL_FILLED
    else:
        raise ValueError("No fill to report")
```

---

## 9. 自动恢复引擎

### 9.1 恢复动作

```python
class RecoveryAction(Enum):
    NONE = "none"           # 无需恢复
    QUERY = "query"         # 查询订单状态
    RETRY_SUBMIT = "retry"  # 重新提交
    RETRY_CANCEL = "retry_cancel"  # 重新撤单
    CHASE = "chase"         # 追价（撤旧发新）
    GIVE_UP = "give_up"     # 放弃，进入 ERROR
```

### 9.2 超时处理流程

```
报单超时（SUBMITTING）
    │
    └── QUERYING ──> 查询订单状态
            │
            ├── 订单存在 ──> 正常流程
            ├── 订单不存在 + retry < max ──> RETRY_PENDING ──> 重新提交
            └── retry >= max ──> ERROR

挂单超时（PENDING/PARTIAL_FILLED）
    │
    └── CANCEL_SUBMITTING ──> 先撤单
            │
            ├── 撤单成功 + chase < max ──> CHASE_PENDING ──> 追价新单
            └── chase >= max ──> ERROR（接受部分成交）

撤单超时（CANCEL_SUBMITTING）
    │
    └── QUERYING ──> 查询订单状态
            │
            ├── 已撤/已成 ──> 终态
            ├── 仍挂单 + retry < max ──> 重新撤单
            └── retry >= max ──> ERROR
```

### 9.3 配置参数

```python
@dataclass
class RecoveryConfig:
    max_retry_submit: int = 3       # 最大重试提交次数
    max_retry_cancel: int = 3       # 最大重试撤单次数
    max_query: int = 3              # 最大查询次数
    max_chase: int = 2              # 最大追价次数
    chase_tick_offset: int = 2      # 追价加减几个 tick
    query_interval_s: float = 1.0   # 查询间隔
```

---

## 10. AutoOrderEngine 规格

### 10.1 接口

```python
class AutoOrderEngine:
    def __init__(
        self,
        broker: Broker,
        position_tracker: PositionTracker,
        protection: ProtectionChain,
        config: AutoOrderConfig,
    ): ...
    
    # 提交订单
    def submit(self, intent: OrderIntent) -> Order: ...
    
    # 撤单
    def cancel(self, order_id: str) -> bool: ...
    
    # CTP 回报入口
    def on_rtn_order(self, rtn: OrderField) -> None: ...
    def on_rtn_trade(self, trade: TradeField) -> None: ...
    def on_rsp_order_insert(self, rsp: RspInfo) -> None: ...
    def on_rsp_order_action(self, rsp: RspInfo) -> None: ...
    
    # 定时检查
    def tick(self, now: float) -> None: ...
    
    # 模式切换
    def set_mode(self, mode: AutoOrderMode) -> None: ...
    
    # 状态查询
    def get_order(self, order_id: str) -> Order | None: ...
    def get_active_orders(self) -> list[Order]: ...
```

### 10.2 运行模式

```python
class AutoOrderMode(Enum):
    RUNNING = "running"       # 允许开仓
    REDUCE_ONLY = "reduce"    # 只允许减仓/平仓
    HALTED = "halted"         # 停止发新单 + 全撤
```

### 10.3 submit 前置检查

```python
def submit(self, intent: OrderIntent) -> Order:
    # 1. 模式检查
    if self.mode == AutoOrderMode.HALTED:
        raise OrderRejected("Engine halted")
    
    if self.mode == AutoOrderMode.REDUCE_ONLY:
        if not self._is_reducing(intent):
            raise OrderRejected("Reduce only mode")
    
    # 2. 保护检查链
    self.protection.check(intent)  # 可能抛出 OrderRejected
    
    # 3. 创建订单并提交
    order = self._create_order(intent)
    self._do_submit(order)
    return order
```

---

## 11. PositionTracker 规格

### 11.1 双来源同步

```python
class PositionTracker:
    # 启动时
    def sync_from_broker(self) -> None:
        """从柜台查询真实仓位"""
        positions = self.broker.query_positions()
        self._positions = {p.symbol: p for p in positions}
    
    # 运行时
    def on_trade(self, trade: TradeField) -> None:
        """用成交回报增量更新"""
        symbol = trade.InstrumentID
        if symbol not in self._positions:
            self._positions[symbol] = Position(symbol=symbol)
        
        pos = self._positions[symbol]
        if trade.Direction == Direction.BUY:
            if trade.OffsetFlag == Offset.OPEN:
                pos.long_qty += trade.Volume
            else:
                pos.short_qty -= trade.Volume
        else:
            if trade.OffsetFlag == Offset.OPEN:
                pos.short_qty += trade.Volume
            else:
                pos.long_qty -= trade.Volume
    
    # 定期对账
    def reconcile(self) -> list[PositionDrift]:
        """对账，返回漂移列表"""
        broker_positions = self.broker.query_positions()
        drifts = []
        for bp in broker_positions:
            local = self._positions.get(bp.symbol)
            if local is None or local != bp:
                drifts.append(PositionDrift(
                    symbol=bp.symbol,
                    local=local,
                    broker=bp,
                ))
        return drifts
```

---

## 12. Guardian 无人值守

### 12.1 最小必做四件事

| 模块 | 触发条件 | 动作 |
|-----|---------|-----|
| `quote_stale` | 行情超时 > N 秒 | reduce-only / halt |
| `order_stuck` | 订单卡单 > N 秒 | cancel + degraded |
| `position_drift` | 本地≠柜台 | halt + reconcile + 告警 |
| `leg_imbalance` | 套利裸腿 | auto_hedge + 告警 + 冷却 |

### 12.2 守护状态机

```python
class GuardianState(Enum):
    RUNNING = "running"
    DEGRADED = "degraded"     # reduce-only
    HALTED = "halted"
    RECOVERING = "recovering"
```

### 12.3 状态转移

```
RUNNING ──(quote_stale)──> DEGRADED
RUNNING ──(order_stuck)──> DEGRADED
RUNNING ──(position_drift)──> HALTED
DEGRADED ──(持续异常)──> HALTED
DEGRADED ──(恢复正常)──> RUNNING
HALTED ──(手动确认)──> RECOVERING ──> RUNNING
```

---

## 13. Audit 审计

### 13.1 decision_log.py

```python
# 每次策略输出 target 时记录
{
    "timestamp": "2025-01-15T10:30:00.123456",
    "strategy": "top_tier_trend_risk_parity",
    "target": {"AO": 1, "SA": -1, "LC": 0},
    "features": {
        "momentum_score": {"AO": 0.8, "SA": -0.5, "LC": 0.1},
        "volatility": {"AO": 0.02, "SA": 0.03, "LC": 0.015},
    },
    "mode": "LIVE",
}
```

### 13.2 order_trail.py

```python
# 订单全生命周期
{
    "order_id": "ORD-20250115-001",
    "events": [
        {"time": "10:30:00.100", "event": "SUBMIT", "state": "SUBMITTING"},
        {"time": "10:30:00.150", "event": "RTN_ACCEPTED", "state": "PENDING"},
        {"time": "10:30:00.200", "event": "RTN_PARTIAL_FILLED", "state": "PARTIAL_FILLED", "filled": 5},
        {"time": "10:30:00.250", "event": "RTN_FILLED", "state": "FILLED", "filled": 10},
    ],
    "final_state": "FILLED",
    "total_filled": 10,
    "avg_price": 5678.0,
}
```

---

## 14. Protection 执行保护

### 14.1 liquidity.py

```python
def check_liquidity(intent: OrderIntent, quote: L1Quote) -> None:
    # 盘口存在
    if quote.bid <= 0 or quote.ask <= 0:
        raise OrderRejected("No bid/ask")
    
    # 盘口超时
    if quote.is_stale:
        raise OrderRejected("Quote stale")
    
    # spread 检查
    spread_ticks = (quote.ask - quote.bid) / tick_size
    if spread_ticks > MAX_SPREAD_TICKS:
        raise OrderRejected(f"Spread too wide: {spread_ticks}")
    
    # 量检查
    if intent.direction == Direction.BUY:
        if quote.ask_vol < MIN_ASKBID_VOL:
            raise OrderRejected("Ask volume too thin")
    else:
        if quote.bid_vol < MIN_ASKBID_VOL:
            raise OrderRejected("Bid volume too thin")
```

### 14.2 fat_finger.py

```python
def check_fat_finger(intent: OrderIntent) -> None:
    # 手数限制
    if intent.qty > MAX_ORDER_QTY:
        raise OrderRejected(f"Qty {intent.qty} > max {MAX_ORDER_QTY}")
    
    # 价格偏离
    mid = (quote.bid + quote.ask) / 2
    deviation = abs(intent.price - mid) / mid
    if deviation > MAX_PRICE_DEVIATION:
        raise OrderRejected(f"Price deviation {deviation:.2%} > max")
```

### 14.3 throttle.py

```python
def check_throttle() -> None:
    now = time.time()
    # 清理过期记录
    self._order_times = [t for t in self._order_times if now - t < 60]
    
    if len(self._order_times) >= MAX_ORDERS_PER_MINUTE:
        raise OrderRejected("Order rate limit exceeded")
    
    self._order_times.append(now)
```

---

## 15. 配置参数汇总

```python
# src/config.py 新增

# === 自动下单 ===
AUTO_MODE: str = "OFF"  # OFF | ASSISTED | LIVE | DEGRADED
AUTO_ORDER_TIMEOUT_ACK_S: float = 3.0
AUTO_ORDER_TIMEOUT_FILL_S: float = 30.0
AUTO_ORDER_TIMEOUT_CANCEL_S: float = 5.0
AUTO_ORDER_MAX_RETRY: int = 3
AUTO_ORDER_MAX_CHASE: int = 2
AUTO_CHASE_TICK_OFFSET: int = 2

# === 流动性保护 ===
LIQ_MAX_SPREAD_TICKS: int = 10
LIQ_MIN_BIDASK_VOL: int = 5
LIQ_QUOTE_STALE_S: float = 5.0

# === 其他保护 ===
FAT_FINGER_MAX_QTY: int = 100
FAT_FINGER_MAX_DEVIATION: float = 0.05  # 5%
THROTTLE_MAX_ORDERS_PER_MIN: int = 60

# === 换月/到期 ===
EXPIRY_BLOCK_DAYS: int = 5
ROLL_COOLDOWN_S: float = 300.0  # 5 分钟

# === 守护 ===
GUARDIAN_CHECK_INTERVAL_S: float = 1.0
REDUCE_ONLY_COOLDOWN_S: float = 300.0

# === 持仓对账 ===
POSITION_RECONCILE_INTERVAL_S: float = 60.0
POSITION_DRIFT_THRESHOLD: int = 1  # 允许偏差手数
```

---

## 16. CTP 接口锚点

### 16.1 place_order 返回值

```python
def place_order(self, intent: OrderIntent) -> OrderRef:
    """
    返回 OrderRef（本地报单引用）
    后续用 OrderRef 追踪此订单
    CTP 回报中 OrderRef 与此匹配
    """
    order_ref = self._next_order_ref()
    # ... 发送 ReqOrderInsert
    return order_ref
```

### 16.2 回报字段

```python
# OnRtnOrder
class OrderField:
    OrderRef: str           # 报单引用（本地）
    OrderSysID: str         # 系统编号（交易所）
    InstrumentID: str       # 合约代码
    Direction: str          # 买卖方向
    CombOffsetFlag: str     # 开平标志
    LimitPrice: float       # 价格
    VolumeTotalOriginal: int  # 原始数量
    VolumeTraded: int       # 已成交数量（累计）
    OrderStatus: str        # 状态码
    StatusMsg: str          # 状态信息

# OnRtnTrade
class TradeField:
    TradeID: str            # 成交编号（唯一）
    OrderRef: str           # 报单引用
    OrderSysID: str         # 系统编号
    InstrumentID: str       # 合约代码
    Direction: str          # 买卖方向
    OffsetFlag: str         # 开平标志
    Price: float            # 成交价格
    Volume: int             # 成交数量（本次）
    TradeDate: str          # 成交日期
    TradeTime: str          # 成交时间
```

### 16.3 cancel_order 参数

```python
def cancel_order(self, order_ref: str, order_sys_id: str = "") -> bool:
    """
    撤单
    - 优先用 OrderSysID（如果已知）
    - 否则用 OrderRef
    """
    # 构造 CThostFtdcInputOrderActionField
    # ...
```

---

## 17. 实现阶段规划

### Sprint 1：可自动跑（2-3 周）

**目标**：先不亏大钱，能自动运行

| 任务 | 优先级 | 依赖 |
|-----|-------|-----|
| InstrumentCache | P0 | - |
| Universe + 主力选择 | P0 | InstrumentCache |
| L1 行情缓存 | P0 | Universe |
| Product→Contract 映射 | P0 | Universe |
| protection.liquidity | P0 | L1 Cache |
| 严格 FSM | P0 | - |
| AutoOrderEngine（无重发） | P0 | FSM |
| PositionTracker | P1 | - |
| 订单审计日志 | P1 | FSM |

**验收标准**：
- [ ] 能获取主力/次主力合约
- [ ] 策略输出品种级 target，执行层映射到合约
- [ ] 流动性不足时拒绝下单
- [ ] 订单状态正确流转
- [ ] 成交后仓位正确更新

### Sprint 2：无人值守闭环（1-2 周）

**目标**：能过夜无人值守

| 任务 | 优先级 | 依赖 |
|-----|-------|-----|
| guardian.quote_stale | P0 | L1 Cache |
| guardian.order_stuck | P0 | FSM |
| guardian.position_drift | P0 | PositionTracker |
| 重启恢复逻辑 | P0 | - |
| 自动恢复引擎 | P1 | FSM |
| 钉钉/企微告警 | P1 | guardian |

**验收标准**：
- [ ] 行情断流 → reduce-only
- [ ] 卡单 → 自动撤单
- [ ] 仓位漂移 → 告警 + halt
- [ ] 重启后能恢复状态

### Sprint 3：顶级套利（2-3 周）

**目标**：跨期套利可实盘

| 任务 | 优先级 | 依赖 |
|-----|-------|-----|
| PairExecutor | P0 | AutoOrderEngine |
| leg_imbalance + auto_hedge | P0 | PairExecutor |
| 协整策略 | P1 | L1 Cache |
| expiry gate | P1 | InstrumentCache |
| 止损熔断 | P1 | - |

**验收标准**：
- [ ] 腿对原子执行
- [ ] 一腿失败自动对冲
- [ ] 临近到期自动 reduce-only
- [ ] 止损后冷却

---

## 18. 变更日志

| 日期 | 版本 | 变更内容 |
|-----|------|---------|
| 2025-12-15 | v1.0 | 初始版本 |

---

## 附录 A：术语表

| 术语 | 解释 |
|-----|------|
| 品种 (Product) | 如 AO、SA、LC |
| 合约 (Contract) | 如 AO2501、SA2509 |
| 主力合约 (Dominant) | 持仓量最大的合约 |
| 次主力 (Subdominant) | 持仓量第二的合约 |
| 跨期套利 (Calendar Spread) | 买近卖远或卖近买远 |
| 协整 (Cointegration) | 两个序列的线性组合平稳 |
| 裸腿 (Naked Leg) | 套利中只成交一腿 |
| 追价 (Chase) | 撤旧单，按更优价格发新单 |
| reduce-only | 只允许减仓/平仓 |
| halt | 停止交易 |

---

## 附录 B：相关文件

- [TASKBOOK_FULL.md](TASKBOOK_FULL.md) - F1-F21 实现记录
- [SPEC_RISK.md](SPEC_RISK.md) - 风控规格
- `src/execution/ctp_broker.py` - CTP Broker 实现
- `src/strategy/types.py` - 策略类型定义
