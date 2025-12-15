# Project Context (for Claude/Copilot)

Generated: 2025-12-15T02:00:52.161226+00:00
Level: dev
Git: feat/mode2-trading-pipeline@d730f0e47abb

## Quality Gate

```
make ci   # Runs: format-check + lint + type + test (85% coverage)
```
- Exit codes: 0=pass, 2=format/lint, 3=type, 4=test, 5=coverage

## Directory Structure

```
(tree unavailable)
```

## Included Files (16 files)

### pyproject.toml

```toml
[project]
name = "cn-futures-auto-trader"
version = "0.1.0"
requires-python = ">=3.11"

# =============================================================================
# Ruff - 军规级静态分析配置
# =============================================================================
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
# 军规级规则集：严格覆盖主要错误类型
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear (严格)
    "UP",     # pyupgrade
    "SIM",    # flake8-simplify
    "C4",     # flake8-comprehensions (推荐列表推导式)
    "DTZ",    # flake8-datetimez (时区安全)
    "T10",    # flake8-debugger (禁止 debugger)
    "ICN",    # flake8-import-conventions
    "PIE",    # flake8-pie (杂项改进)
    "PT",     # flake8-pytest-style (测试规范)
    "RSE",    # flake8-raise (异常规范)
    "RET",    # flake8-return (返回值规范)
    "SLF",    # flake8-self (私有成员访问)
    "ARG",    # flake8-unused-arguments (未使用参数)
    "PGH",    # pygrep-hooks
    "PL",     # pylint 选择性规则
    "TRY",    # tryceratops (异常处理规范)
    "FLY",    # flynt (f-string 推荐)
    "PERF",   # perflint (性能)
    "RUF",    # ruff 专有规则
]

ignore = [
    # 允许的例外（必须有理由）
    "PLR0913",  # 允许函数参数超过 5 个（某些 API 需要）
    "PLR0911",  # 允许多个 return 语句（复杂逻辑需要）
    "PLR0912",  # 允许多个分支（复杂逻辑需要）
    "PLR2004",  # 允许魔法数字（配置常量）
    "TRY003",   # 允许长异常消息
    "TRY004",   # 允许 RuntimeError 代替 TypeError
    "TRY300",   # 允许 try 内 return
    "ARG001",   # 允许未使用参数（接口预留）
    "ARG002",   # 允许未使用的方法参数（接口兼容）
    "B008",     # 允许函数默认参数使用函数调用（FastAPI 依赖）
    "RUF002",   # 允许中文全角字符在 docstring 中
    "RUF003",   # 允许中文全角字符在注释中
    "RUF034",   # 允许冗余条件（可读性）
    "RUF046",   # 允许 int(round(...))（明确意图）
    "RET504",   # 允许 return 前赋值（调试友好）
    "PLW0603",  # 允许 global 语句（状态管理需要）
    "PLW1510",  # 允许 subprocess.run 不带 check
    "PLC0415",  # 允许函数内 import（延迟加载）
    "SIM102",   # 允许嵌套 if（可读性）
    "PERF401",  # 允许循环 append（可读性）
]

# 各模块单独配置
[tool.ruff.lint.per-file-ignores]
"tests/*" = [
    "S101",     # 测试允许 assert
    "SLF001",   # 测试允许访问私有成员
    "PT011",    # 测试允许宽泛的 pytest.raises
    "PT018",    # 测试允许复合断言
    "RUF043",   # 测试允许非原始正则
    "RUF059",   # 测试允许未使用的解包变量
    "PLR0124",  # 测试允许 NaN 检查 (qty == qty)
]
"scripts/*" = [
    "T201",     # 脚本允许 print
]

[tool.ruff.lint.isort]
known-first-party = ["src"]
force-single-line = false
lines-after-imports = 2

[tool.ruff.lint.flake8-bugbear]
extend-immutable-calls = ["fastapi.Depends", "fastapi.Query"]

# =============================================================================
# MyPy - 军规级类型检查配置
# =============================================================================
[tool.mypy]
python_version = "3.11"
pretty = true

# 严格模式基础配置
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
no_implicit_optional = true
strict_equality = true

# 军规级增强配置
warn_redundant_casts = true
warn_unused_ignores = true
warn_unreachable = true
disallow_any_generics = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_reexport = true
strict_concatenate = true

# 排除目录
exclude = [
    "^dist/",
    "^build/",
    "^\\.venv/",
    "^artifacts/",
    "^tests/",
]

# 核心模块使用最严格模式
[[tool.mypy.overrides]]
module = [
    "src.trading.*",
    "src.execution.*",
    "src.risk.*",
    "src.market.*",
]
strict = true
disallow_any_unimported = true

# 测试模块略微宽松
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_decorators = false
warn_unreachable = false
ignore_errors = true

# 外部依赖类型桩
[[tool.mypy.overrides]]
module = [
    "thostmduserapi.*",
    "thosttraderapi.*",
]
ignore_missing_imports = true

# =============================================================================
# Pytest 配置
# =============================================================================
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = [
    "-q",
    "--strict-markers",
    "--strict-config",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "replay: marks tests as replay/sim tests",
]

# =============================================================================
# Coverage 配置
# =============================================================================
[tool.coverage.run]
source = ["src"]
branch = true
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    # 入口脚本（CLI glue，非核心逻辑）
    "src/app/live_entry.py",
    "src/app/paper_entry.py",
]
# 军规级：核心域必须 100% 覆盖
# - src/trading/**（包括 ci_gate.py, sim_gate.py）
# - src/execution/**
# - src/risk/**
# - src/market/**
# 不允许排除核心模块！测试必须补齐

[tool.coverage.report]
# 核心域覆盖率阈值
fail_under = 85
show_missing = true
skip_covered = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
    "@abstractmethod",
]
```

### SPEC_RISK.md

```markdown
﻿# RiskPolicy v1.1 (Final)

## Instruments
- AO (SHFE), SA (CZCE), LC (GFEX) + 2 auto-selected later

## Daily baseline
- E0 snapshot at **09:00:00** (day session)

## Kill switch (daily DD)
- Trigger: DD(t) <= -3% and kill_switch_fired_today == false
- Action: CancelAll -> ForceFlattenAll -> COOLDOWN(90min)
- After cooldown: RECOVERY
  - 
ecovery_risk_multiplier = 0.30
  - max_margin_recovery = 0.40
- Second time DD(t) <= -3% in same trading day: LOCKED (no opening until next day)

## Force flatten (execution policy)
- Order type: **LIMIT only** (no FAK/FOK)
- Prefer closing today positions first (**CloseToday**); if rejected, fallback to **Close**
- Stage1: 	1=5s near best (min impact)
- Stage2: dt=2s, 
=12 requotes, step=1 tick
- Stage3: aggressive but limited: cross <= 12 levels from best
- Alerts: DingTalk webhook
```

### docs/SPEC_CONTRACT_AUTOORDER.md

```markdown
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

... (truncated, 500 of 1020 lines)
```

### src/config.py

```python
from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class DingTalkSettings:
    webhook_url: str
    secret: str | None


@dataclass(frozen=True)
class AppSettings:
    baseline_time: str = "09:00:00"
    dingtalk: DingTalkSettings | None = None
    trade_mode: str = "PAPER"
    strategy_name: str = "top_tier"
    strategy_symbols: tuple[str, ...] = ("AO", "SA", "LC")


def load_settings() -> AppSettings:
    webhook = getenv("DINGTALK_WEBHOOK_URL", "").strip()
    secret = getenv("DINGTALK_SECRET", "").strip() or None
    baseline_time = getenv("BASELINE_TIME", "09:00:00").strip()
    trade_mode = getenv("TRADE_MODE", "PAPER").strip().upper()
    strategy_name = getenv("STRATEGY_NAME", "top_tier").strip()
    strategy_symbols_str = getenv("STRATEGY_SYMBOLS", "AO,SA,LC").strip()
    strategy_symbols = tuple(s.strip() for s in strategy_symbols_str.split(",") if s.strip())

    dingtalk = None
    if webhook:
        dingtalk = DingTalkSettings(webhook_url=webhook, secret=secret)

    return AppSettings(
        baseline_time=baseline_time,
        dingtalk=dingtalk,
        trade_mode=trade_mode,
        strategy_name=strategy_name,
        strategy_symbols=strategy_symbols,
    )
```

### src/runner.py

```python
from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.config import AppSettings, load_settings
from src.execution.broker import Broker
from src.execution.broker_factory import broker_factory as default_broker_factory
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, PositionToClose
from src.orchestrator import handle_risk_update
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig
from src.trading.controls import TradeControls, TradeMode
from src.trading.orchestrator import handle_trading_tick


if TYPE_CHECKING:
    from src.strategy.base import Strategy
    from src.strategy.types import Bar1m


@dataclass(frozen=True)
class Components:
    settings: AppSettings
    risk: RiskManager
    flatten: FlattenExecutor


@dataclass(frozen=True)
class LiveTickData:
    snap: AccountSnapshot
    positions: Sequence[PositionToClose]
    books: Mapping[str, BookTop]
    bars_1m: Mapping[str, Sequence[Bar1m]]
    now_ts: float


def init_components(broker: Broker, risk_cfg: RiskConfig | None = None) -> Components:
    """
    App composition root.
    - Loads settings/env
    - Wires RiskManager + Executor
    - Returns components (no side effects like network calls)
    """
    settings = load_settings()

    cfg = risk_cfg or RiskConfig()

    # callbacks are stubs; later wire to Broker/OMS cancel/flatten
    def cancel_all() -> None:
        # placeholder: integrate with OMS later
        return

    def force_flatten_all() -> None:
        # placeholder: integrate with flatten runner later
        return

    risk = RiskManager(cfg, cancel_all_cb=cancel_all, force_flatten_all_cb=force_flatten_all)
    flatten = FlattenExecutor(broker)

    return Components(settings=settings, risk=risk, flatten=flatten)


def run_f21(
    *,
    broker_factory: Callable[[AppSettings], Broker] | None = None,
    strategy_factory: Callable[[AppSettings], Strategy],
    fetch_tick: Callable[[], LiveTickData],
    now_cb: Callable[[], float] = time.time,
    risk_cfg: RiskConfig | None = None,
    run_forever: bool = True,
) -> None:
    """
    Skeleton for live runner (F21).

    Intended flow (per taskbook F21):
    1) load settings/env (including TRADE_MODE, strategy selection)
    2) build broker/executor/strategy/risk (PAPER->Noop, LIVE->Ctp via broker_factory)
    3) per tick fetch AccountSnapshot/positions/books/bars_1m via fetch_tick()
    4) call handle_risk_update(...) then handle_trading_tick(...) in order
    5) log events (stdout or artifacts/log)

    This skeleton wires dependency acquisition and guards; the main loop
    and orchestration are left for F21 implementation. handle_risk_update
    行为必须保持不变（仅在 orchestrator 内部调用）。
    """

    settings = load_settings()

    # Use default broker_factory from F20 if not provided
    _broker_factory = broker_factory or default_broker_factory
    live_broker = _broker_factory(settings)
    components = init_components(broker=live_broker, risk_cfg=risk_cfg)
    strategy = strategy_factory(settings)

    def _run_once() -> None:
        tick = fetch_tick()

        # Day-start baseline: first tick (or when e0 missing) sets baseline.
        if components.risk.state.e0 is None:
            cid = uuid.uuid4().hex
            components.risk.on_day_start_0900(tick.snap, correlation_id=cid)

        risk_result = handle_risk_update(
            risk=components.risk,
            executor=components.flatten,
            snap=tick.snap,
            positions=tick.positions,
            books=tick.books,
            now_cb=lambda: tick.now_ts,
        )

        # Prepare trading inputs
        prices: dict[str, float] = {
            sym: (book.best_bid + book.best_ask) / 2.0 for sym, book in tick.books.items()
        }
        current_net_qty: dict[str, int] = {pos.symbol: pos.net_qty for pos in tick.positions}

        requested_mode = (
            settings.trade_mode.upper()
            if isinstance(settings.trade_mode, str)
            else str(settings.trade_mode)
        )
        effective_mode = (
            TradeMode.LIVE if requested_mode == TradeMode.LIVE.value else TradeMode.PAPER
        )
        controls = TradeControls(mode=effective_mode)

        handle_trading_tick(
            strategy=strategy,
            risk=components.risk,
            executor=components.flatten,
            controls=controls,
            snap=tick.snap,
            prices=prices,
            bars_1m=tick.bars_1m,
            current_net_qty=current_net_qty,
            correlation_id=risk_result.correlation_id,
            now_cb=lambda: tick.now_ts,
        )

    if run_forever:
        while True:
            _run_once()
    else:
        _run_once()
```

### src/orchestrator.py

```python
from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from src.execution.events import ExecutionEvent
from src.execution.flatten_executor import ExecutionRecord, FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose, build_flatten_intents
from src.risk.events import RiskEvent, RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot
from src.trading.utils import stable_json


NowCb = Callable[[], float]
Event = RiskEvent | ExecutionEvent


@dataclass(frozen=True)
class OrchestratorResult:
    correlation_id: str
    snapshot_hash: str
    events: list[Event]
    execution_records: list[ExecutionRecord]


def _hash_snapshot(
    *,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
) -> str:
    pos_data = [
        {
            "symbol": p.symbol,
            "net_qty": p.net_qty,
            "today_qty": p.today_qty,
            "yesterday_qty": p.yesterday_qty,
        }
        for p in sorted(positions, key=lambda x: x.symbol)
    ]
    book_data = {
        sym: {"best_bid": b.best_bid, "best_ask": b.best_ask, "tick": b.tick}
        for sym, b in sorted(books.items(), key=lambda kv: kv[0])
    }
    payload = {
        "snap": {"equity": snap.equity, "margin_used": snap.margin_used},
        "positions": pos_data,
        "books": book_data,
    }
    raw = stable_json(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def handle_risk_update(
    *,
    risk: RiskManager,
    executor: FlattenExecutor,
    snap: AccountSnapshot,
    positions: Sequence[PositionToClose],
    books: Mapping[str, BookTop],
    flatten_spec: FlattenSpec | None = None,
    now_cb: NowCb = time.time,
    max_rejections: int = 10,  # HG-5
) -> OrchestratorResult:
    correlation_id = uuid.uuid4().hex
    snapshot_hash = _hash_snapshot(snap=snap, positions=positions, books=books)

    risk.update(snap, correlation_id=correlation_id)
    base_risk_events = risk.pop_events()

    audit_event = RiskEvent(
        type=RiskEventType.AUDIT_SNAPSHOT,
        ts=now_cb(),
        correlation_id=correlation_id,
        data={"snapshot_hash": snapshot_hash},
    )

    exec_records: list[ExecutionRecord] = []
    exec_events: list[ExecutionEvent] = []

    kill_fired = any(e.type == RiskEventType.KILL_SWITCH_FIRED for e in base_risk_events)
    if kill_fired and risk.try_start_flatten(correlation_id=correlation_id):
        spec = flatten_spec or FlattenSpec()
        rejections = 0

        for pos in positions:
            book = books.get(pos.symbol)
            if book is None:
                risk.emit(
                    event_type=RiskEventType.DATA_QUALITY_MISSING_BOOK,
                    correlation_id=correlation_id,
                    data={"symbol": pos.symbol},
                )
                continue

            intents = build_flatten_intents(pos=pos, book=book, spec=spec)
            recs = executor.execute(intents, correlation_id=correlation_id)
            exec_records.extend(recs)

            rejections += sum(1 for r in recs if not r.ok)
            if rejections >= max_rejections:
                risk.emit(
                    event_type=RiskEventType.FLATTEN_ABORTED_TOO_MANY_REJECTIONS,
                    correlation_id=correlation_id,
                    data={"rejections": rejections, "max_rejections": max_rejections},
                )
                break

        exec_events = executor.drain_events()
        risk.mark_flatten_done(correlation_id=correlation_id)

    all_risk_events = risk.pop_events()
    events: list[Event] = [audit_event, *base_risk_events, *all_risk_events, *exec_events]

    return OrchestratorResult(
        correlation_id=correlation_id,
        snapshot_hash=snapshot_hash,
        events=events,
        execution_records=exec_records,
    )
```

### src/strategy/types.py

```python
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypedDict


class Bar1m(TypedDict):
    """1-minute OHLCV bar."""

    ts: float  # epoch seconds, minute-aligned
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketState:
    """Snapshot of market state for strategy consumption."""

    prices: Mapping[str, float]  # mid/last prices
    equity: float
    bars_1m: Mapping[str, Sequence[Bar1m]]  # oldest -> newest


@dataclass(frozen=True)
class TargetPortfolio:
    """Strategy output: target net positions."""

    target_net_qty: Mapping[str, int]
    model_version: str
    features_hash: str
```

### src/execution/broker.py

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.execution.order_types import OrderIntent


class OrderRejected(Exception):
    """Generic order rejection."""


class CloseTodayRejected(OrderRejected):
    """Raised when exchange rejects CloseToday offset for this position/order."""


@dataclass(frozen=True)
class OrderAck:
    order_id: str


class Broker(Protocol):
    def place_order(self, intent: OrderIntent) -> OrderAck:
        """Place an order described by intent. Raises OrderRejected subclasses on failure."""
        raise NotImplementedError


class NoopBroker(Broker):
    """Acknowledges orders without sending them (PAPER/testing)."""

    def __init__(self) -> None:
        self._counter = 0

    def place_order(self, intent: OrderIntent) -> OrderAck:  # pragma: no cover - trivial
        self._counter += 1
        return OrderAck(order_id=f"noop-{self._counter}")
```

### src/execution/order_types.py

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Offset(str, Enum):
    OPEN = "OPEN"
    CLOSETODAY = "CLOSETODAY"
    CLOSE = "CLOSE"


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: Side
    offset: Offset
    price: float
    qty: int
    reason: str = ""
```

### src/risk/manager.py

```python
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from src.risk.events import RiskEvent, RiskEventType
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState


@dataclass(frozen=True)
class Decision:
    allow_open: bool
    reason: str = ""


CancelAllCb = Callable[[], None]
ForceFlattenAllCb = Callable[[], None]


class NowCb(Protocol):
    def __call__(self) -> float: ...


class RiskManager:
    def __init__(
        self,
        cfg: RiskConfig,
        *,
        cancel_all_cb: CancelAllCb,
        force_flatten_all_cb: ForceFlattenAllCb,
        now_cb: NowCb = time.time,
    ) -> None:
        self.cfg = cfg
        self.state = RiskState()
        self._cancel_all = cancel_all_cb
        self._force_flatten_all = force_flatten_all_cb
        self._now = now_cb
        self._events: list[RiskEvent] = []

    def pop_events(self) -> list[RiskEvent]:
        ev = self._events[:]
        self._events.clear()
        return ev

    def emit(
        self,
        *,
        event_type: RiskEventType,
        correlation_id: str,
        data: dict[str, Any],
    ) -> None:
        self._events.append(
            RiskEvent(
                type=event_type,
                ts=self._now(),
                correlation_id=correlation_id,
                data=data,
            )
        )

    def on_day_start_0900(self, snap: AccountSnapshot, *, correlation_id: str) -> None:
        self.state.e0 = snap.equity
        self.state.mode = RiskMode.NORMAL
        self.state.kill_switch_fired_today = False
        self.state.cooldown_end_ts = None

        # reset highest-grade idempotency flags for the new day
        self.state.flatten_in_progress = False
        self.state.flatten_completed_today = False

        self._events.append(
            RiskEvent(
                type=RiskEventType.BASELINE_SET,
                ts=self._now(),
                correlation_id=correlation_id,
                data={"e0": snap.equity},
            )
        )

    def update(self, snap: AccountSnapshot, *, correlation_id: str) -> None:
        if self.state.e0 is None:
            return

        now_ts = self._now()

        if self.state.mode == RiskMode.COOLDOWN:
            if self.state.cooldown_end_ts is not None and now_ts >= self.state.cooldown_end_ts:
                self.state.mode = RiskMode.RECOVERY
                self._events.append(
                    RiskEvent(
                        type=RiskEventType.ENTER_RECOVERY,
                        ts=now_ts,
                        correlation_id=correlation_id,
                        data={"cooldown_end_ts": self.state.cooldown_end_ts},
                    )
                )
            return

        dd = self.state.dd(snap.equity)

        if dd <= self.cfg.dd_limit:
            if not self.state.kill_switch_fired_today:
                self._fire_kill_switch(correlation_id=correlation_id)
            else:
                self.state.mode = RiskMode.LOCKED
                self._events.append(
                    RiskEvent(
                        type=RiskEventType.LOCKED_FOR_DAY,
                        ts=now_ts,
                        correlation_id=correlation_id,
                        data={"dd": dd},
                    )
                )

    def _fire_kill_switch(self, *, correlation_id: str) -> None:
        now_ts = self._now()
        self.state.kill_switch_fired_today = True
        self.state.mode = RiskMode.COOLDOWN
        self.state.cooldown_end_ts = now_ts + self.cfg.cooldown_seconds

        self._cancel_all()
        self._force_flatten_all()

        self._events.append(
            RiskEvent(
                type=RiskEventType.KILL_SWITCH_FIRED,
                ts=now_ts,
                correlation_id=correlation_id,
                data={"cooldown_end_ts": self.state.cooldown_end_ts},
            )
        )

    # ---------- Highest-grade flatten idempotency ----------
    def try_start_flatten(self, *, correlation_id: str) -> bool:
        """
        Returns True exactly once per day (first successful start).
        Subsequent attempts are skipped (either in-progress or already completed today).
        """
        now_ts = self._now()

        if self.state.flatten_in_progress:
            self._events.append(
                RiskEvent(
                    type=RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS,
                    ts=now_ts,
                    correlation_id=correlation_id,
                    data={},
                )
            )
            return False

        if self.state.flatten_completed_today:
            # Reuse the same event type to keep it minimal; data indicates why.
            self._events.append(
                RiskEvent(
                    type=RiskEventType.FLATTEN_SKIPPED_ALREADY_IN_PROGRESS,
                    ts=now_ts,
                    correlation_id=correlation_id,
                    data={"reason": "already_completed_today"},
                )
            )
            return False

        self.state.flatten_in_progress = True
        self._events.append(
            RiskEvent(
                type=RiskEventType.FLATTEN_STARTED,
                ts=now_ts,
                correlation_id=correlation_id,
                data={},
            )
        )
        return True

    def mark_flatten_done(self, *, correlation_id: str) -> None:
        now_ts = self._now()
        self.state.flatten_in_progress = False
        self.state.flatten_completed_today = True
        self._events.append(
            RiskEvent(
                type=RiskEventType.FLATTEN_COMPLETED,
                ts=now_ts,
                correlation_id=correlation_id,
                data={},
            )
        )

    def can_open(self, snap: AccountSnapshot) -> Decision:
        if self.state.e0 is None:
            return Decision(False, "blocked_by_init:no_baseline")

        if self.state.mode in (RiskMode.COOLDOWN, RiskMode.LOCKED):
            return Decision(False, f"blocked_by_mode:{self.state.mode.value}")

        max_margin = (
            self.cfg.max_margin_normal
            if self.state.mode == RiskMode.NORMAL
            else self.cfg.max_margin_recovery
        )
        if snap.margin_ratio > max_margin:
            return Decision(False, "blocked_by_margin_ratio")

        return Decision(True, "ok")
```

### src/risk/state.py

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskMode(str, Enum):
    INIT = "INIT"
    NORMAL = "NORMAL"
    COOLDOWN = "COOLDOWN"
    RECOVERY = "RECOVERY"
    LOCKED = "LOCKED"


@dataclass
class RiskConfig:
    dd_limit: float = -0.03
    cooldown_seconds: int = 600
    max_margin_normal: float = 0.70
    max_margin_recovery: float = 0.50
    recovery_risk_multiplier: float = 0.30


@dataclass
class AccountSnapshot:
    equity: float
    margin_used: float

    @property
    def margin_ratio(self) -> float:
        if self.equity <= 0:
            return 1.0
        return self.margin_used / self.equity


@dataclass
class RiskState:
    e0: float | None = None
    mode: RiskMode = RiskMode.INIT
    kill_switch_fired_today: bool = False
    cooldown_end_ts: float | None = None

    # Highest-grade idempotency/anti-reentry for flatten
    flatten_in_progress: bool = False
    flatten_completed_today: bool = False

    def dd(self, equity: float) -> float:
        if self.e0 is None or self.e0 == 0:
            return 0.0
        return equity / self.e0 - 1.0
```

### src/trading/live_guard.py

```python
"""LIVE mode guard and safety checks.

Provides safeguards for transitioning to LIVE trading mode.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class TradeMode(str, Enum):
    """Trading mode enumeration."""

    PAPER = "PAPER"
    LIVE = "LIVE"
    BACKTEST = "BACKTEST"


@dataclass(frozen=True)
class LiveModeCheck:
    """Result of a LIVE mode pre-flight check."""

    check_name: str
    passed: bool
    message: str


class LiveModeGuard:
    """
    Guard for LIVE mode trading.

    Performs safety checks before allowing LIVE trading.
    """

    def __init__(self, mode: str) -> None:
        """
        Initialize the guard.

        Args:
            mode: Trading mode string (PAPER, LIVE, BACKTEST)
        """
        self._mode = TradeMode(mode.upper())
        self._checks: list[LiveModeCheck] = []

    @property
    def mode(self) -> TradeMode:
        """Current trading mode."""
        return self._mode

    @property
    def is_live(self) -> bool:
        """Check if in LIVE mode."""
        return self._mode == TradeMode.LIVE

    @property
    def is_paper(self) -> bool:
        """Check if in PAPER mode."""
        return self._mode == TradeMode.PAPER

    def add_check(self, name: str, passed: bool, message: str = "") -> None:
        """Add a pre-flight check result."""
        check = LiveModeCheck(check_name=name, passed=passed, message=message)
        self._checks.append(check)

    def run_preflight_checks(
        self,
        *,
        broker_connected: bool = False,
        risk_limits_set: bool = False,
        strategy_validated: bool = False,
    ) -> list[LiveModeCheck]:
        """
        Run pre-flight checks for LIVE mode.

        Args:
            broker_connected: Whether broker is connected
            risk_limits_set: Whether risk limits are configured
            strategy_validated: Whether strategy has been validated

        Returns:
            List of check results
        """
        self._checks = []

        # Check 1: Broker connection
        self.add_check(
            "broker_connected",
            broker_connected,
            "Broker must be connected for LIVE trading",
        )

        # Check 2: Risk limits
        self.add_check(
            "risk_limits_set",
            risk_limits_set,
            "Risk limits must be configured for LIVE trading",
        )

        # Check 3: Strategy validation
        self.add_check(
            "strategy_validated",
            strategy_validated,
            "Strategy must be validated before LIVE trading",
        )

        return self._checks

    def all_checks_passed(self) -> bool:
        """Check if all pre-flight checks passed."""
        if not self._checks:
            return False
        return all(c.passed for c in self._checks)

    def can_trade_live(self) -> bool:
        """
        Check if LIVE trading is allowed.

        Returns:
            True only if in LIVE mode AND all checks passed
        """
        if not self.is_live:
            return False
        return self.all_checks_passed()

    def get_failed_checks(self) -> list[LiveModeCheck]:
        """Get list of failed checks."""
        return [c for c in self._checks if not c.passed]

    def log_status(self) -> None:
        """Log current guard status."""
        logger.info("Trade mode: %s", self._mode.value)
        if self._checks:
            passed = sum(1 for c in self._checks if c.passed)
            logger.info("Pre-flight checks: %d/%d passed", passed, len(self._checks))
            for check in self._checks:
                status = "PASS" if check.passed else "FAIL"
                logger.info("  [%s] %s: %s", status, check.check_name, check.message)
```

### src/trading/ci_gate.py

```python
"""CI gate checks for LIVE mode deployment.

Provides pre-deployment checks that must pass before LIVE trading.
Also provides machine-readable JSON report generation for Claude automated loop.

Military-Grade v3.0:
- Strict JSON schema validation
- run_id / exec_id for traceability
- context_manifest_sha for audit
- POLICY_VIOLATION (exit 12) enforcement
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# =============================================================================
# 固定路径约定 (D.1)
# =============================================================================
FIXED_PATHS = {
    "ci_report": Path("artifacts/check/report.json"),
    "sim_report": Path("artifacts/sim/report.json"),
    "events_jsonl": Path("artifacts/sim/events.jsonl"),
    "context": Path("artifacts/context/context.md"),
    "commands_log": Path("artifacts/claude/commands.log"),
    "round_summary": Path("artifacts/claude/round_summary.json"),
    "policy_violation": Path("artifacts/claude/policy_violation.json"),
}


class GateCheckStatus(str, Enum):
    """Gate check status."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class GateCheck:
    """Single gate check result."""

    name: str
    status: GateCheckStatus
    message: str = ""
    required: bool = True

    @property
    def passed(self) -> bool:
        """Check if this gate passed or was skipped."""
        return self.status in (GateCheckStatus.PASS, GateCheckStatus.SKIP)

    @property
    def blocking(self) -> bool:
        """Check if this failure blocks deployment."""
        return self.required and self.status == GateCheckStatus.FAIL


@dataclass(frozen=True)
class GateReport:
    """Full CI gate report."""

    checks: tuple[GateCheck, ...]
    target_mode: str

    @property
    def all_passed(self) -> bool:
        """Check if all required checks passed."""
        return not any(c.blocking for c in self.checks)

    @property
    def blocking_failures(self) -> list[GateCheck]:
        """Get list of blocking failures."""
        return [c for c in self.checks if c.blocking]

    @property
    def pass_count(self) -> int:
        """Number of passed checks."""
        return sum(1 for c in self.checks if c.passed)

    def summary(self) -> str:
        """Generate summary string."""
        status = "PASS" if self.all_passed else "FAIL"
        return (
            f"CI Gate [{self.target_mode}]: {status} ({self.pass_count}/{len(self.checks)} passed)"
        )


class CIGate:
    """
    CI gate for LIVE mode deployment.

    Runs a series of checks before allowing LIVE deployment.
    """

    def __init__(self, target_mode: str = "LIVE") -> None:
        """
        Initialize CI gate.

        Args:
            target_mode: Target deployment mode
        """
        self._target_mode = target_mode.upper()
        self._checks: list[GateCheck] = []

    def add_check(
        self,
        name: str,
        status: GateCheckStatus,
        message: str = "",
        *,
        required: bool = True,
    ) -> None:
        """Add a gate check."""
        self._checks.append(GateCheck(name=name, status=status, message=message, required=required))

    def check_tests_pass(self, test_passed: bool) -> None:
        """Check if all tests passed."""
        self.add_check(
            "tests_pass",
            GateCheckStatus.PASS if test_passed else GateCheckStatus.FAIL,
            "All tests must pass",
        )

    def check_lint_pass(self, lint_passed: bool) -> None:
        """Check if linting passed."""
        self.add_check(
            "lint_pass",
            GateCheckStatus.PASS if lint_passed else GateCheckStatus.FAIL,
            "Code must pass linting",
        )

    def check_type_check_pass(self, type_check_passed: bool) -> None:
        """Check if type checking passed."""
        self.add_check(
            "type_check_pass",
            GateCheckStatus.PASS if type_check_passed else GateCheckStatus.FAIL,
            "Code must pass type checking",
        )

    def check_risk_limits_configured(self, configured: bool) -> None:
        """Check if risk limits are configured."""
        self.add_check(
            "risk_limits_configured",
            GateCheckStatus.PASS if configured else GateCheckStatus.FAIL,
            "Risk limits must be configured for LIVE",
        )

    def check_broker_credentials(self, credentials_valid: bool) -> None:
        """Check if broker credentials are valid."""
        self.add_check(
            "broker_credentials",
            GateCheckStatus.PASS if credentials_valid else GateCheckStatus.FAIL,
            "Broker credentials must be valid",
        )

    def check_model_weights_exist(self, weights_exist: bool) -> None:
        """Check if model weights exist in repo."""
        self.add_check(
            "model_weights_exist",
            GateCheckStatus.PASS if weights_exist else GateCheckStatus.FAIL,
            "Model weights must be in repository",
        )

    def generate_report(self) -> GateReport:
        """Generate gate report."""
        return GateReport(
            checks=tuple(self._checks),
            target_mode=self._target_mode,
        )

    def run_all_checks(
        self,
        *,
        tests_passed: bool = False,
        lint_passed: bool = False,
        type_check_passed: bool = False,
        risk_limits_configured: bool = False,
        broker_credentials_valid: bool = False,
        model_weights_exist: bool = False,
    ) -> GateReport:
        """
        Run all standard CI gate checks.

        Args:
            tests_passed: Whether tests passed
            lint_passed: Whether linting passed
            type_check_passed: Whether type checking passed
            risk_limits_configured: Whether risk limits are set
            broker_credentials_valid: Whether broker creds are valid
            model_weights_exist: Whether model weights exist

        Returns:
            GateReport with all check results
        """
        self._checks = []  # Reset checks
        self.check_tests_pass(tests_passed)
        self.check_lint_pass(lint_passed)
        self.check_type_check_pass(type_check_passed)
        self.check_risk_limits_configured(risk_limits_configured)
        self.check_broker_credentials(broker_credentials_valid)
        self.check_model_weights_exist(model_weights_exist)
        return self.generate_report()


def log_gate_report(report: GateReport) -> None:
    """Log gate report."""
    logger.info(report.summary())
    for check in report.checks:
        status_str = check.status.value
        req_str = "[REQ]" if check.required else "[OPT]"
        logger.info("  %s %s %s: %s", req_str, status_str, check.name, check.message)
    if report.blocking_failures:
        logger.error("Blocking failures: %d", len(report.blocking_failures))


# =============================================================================
# 退出码约定（军规级）
# =============================================================================
class ExitCode:
    """Standard exit codes for CI gate.

    Exit codes:
        0 = All checks passed
        1 = General error (unexpected)
        2 = Format or Lint check failed
        3 = Type check failed
        4 = Test failed
        5 = Coverage threshold not met
        6 = Risk limits not configured
        7 = Broker credentials invalid
        8 = Replay failed (reserved for sim_gate)
        9 = Sim failed (reserved for sim_gate)
        12 = Policy violation (military-grade enforcement)
    """

    SUCCESS = 0
    GENERAL_ERROR = 1
    FORMAT_LINT_FAIL = 2
    TYPE_CHECK_FAIL = 3
    TEST_FAIL = 4
    COVERAGE_FAIL = 5
    RISK_CONFIG_FAIL = 6
    BROKER_CREDS_FAIL = 7
    REPLAY_FAIL = 8
    SIM_FAIL = 9
    POLICY_VIOLATION = 12


def get_exit_code(report: GateReport) -> int:
    """Determine exit code based on gate report.

    Returns appropriate exit code based on first blocking failure.
    """
    if report.all_passed:
        return ExitCode.SUCCESS

    # Check failures in order of priority
    for check in report.blocking_failures:
        if check.name in ("format_pass", "lint_pass"):
            return ExitCode.FORMAT_LINT_FAIL
        if check.name == "type_check_pass":
            return ExitCode.TYPE_CHECK_FAIL
        if check.name == "tests_pass":
            return ExitCode.TEST_FAIL
        if check.name == "coverage_pass":
            return ExitCode.COVERAGE_FAIL
        if check.name == "risk_limits_configured":
            return ExitCode.RISK_CONFIG_FAIL
        if check.name == "broker_credentials":
            return ExitCode.BROKER_CREDS_FAIL

    return ExitCode.GENERAL_ERROR


# =============================================================================
# CHECK 模式硬禁令
# =============================================================================
_CHECK_MODE_ENABLED: bool = False


def enable_check_mode() -> None:
    """Enable CHECK mode - blocks all broker operations."""
    global _CHECK_MODE_ENABLED
    _CHECK_MODE_ENABLED = True
    logger.warning("CHECK_MODE enabled - broker.place_order will be blocked")


def disable_check_mode() -> None:
    """Disable CHECK mode."""
    global _CHECK_MODE_ENABLED
    _CHECK_MODE_ENABLED = False


def is_check_mode() -> bool:
    """Check if CHECK mode is active."""
    return _CHECK_MODE_ENABLED


def assert_not_check_mode(operation: str = "place_order") -> None:
    """Assert that we are NOT in CHECK mode.

    Raises:
        RuntimeError: If CHECK mode is enabled and broker operation is attempted.

    Usage:
        # In broker.place_order():
        assert_not_check_mode("place_order")
    """
    if _CHECK_MODE_ENABLED:
        msg = f"BLOCKED: {operation} is forbidden in CHECK_MODE=1"
        logger.error(msg)
        raise RuntimeError(msg)


# =============================================================================
# CI JSON 报告生成（供 Claude 自动闭环使用）
# =============================================================================


class CIStepStatus(str, Enum):
    """CI step status."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CIStepFailure:
    """Single failure detail within a CI step."""

    file: str
    line: int
    rule: str
    message: str


@dataclass
class CIStep:
    """Single CI step result."""

    name: str
    status: CIStepStatus
    exit_code: int | None = None
    duration_ms: int = 0
    summary: str = ""  # First 50 lines of output
    reason: str = ""  # For SKIP status
    failures: list[CIStepFailure] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)  # Common fix suggestions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result: dict[str, Any] = {
            "name": self.name,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }
        if self.status == CIStepStatus.SKIP:
            result["reason"] = self.reason
        elif self.status == CIStepStatus.FAIL:
            result["summary"] = self.summary
            if self.failures:
                result["failures"] = [asdict(f) for f in self.failures]
            if self.hints:
                result["hints"] = self.hints
        return result


def _generate_run_id() -> str:
    """Generate a unique run_id (UUID)."""
    return str(uuid.uuid4())


def _generate_exec_id() -> str:
    """Generate exec_id from git commit + timestamp."""
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        commit = result.stdout.strip()[:8] if result.returncode == 0 else "unknown"
    except Exception:
        commit = "unknown"
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return f"{commit}_{ts}"


def _compute_context_sha(context_path: Path) -> str:
    """Compute SHA256 of context.md for audit."""
    if not context_path.exists():
        return ""
    with open(context_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@dataclass
class CIJsonReport:
    """Machine-readable CI report for Claude automated loop (Military-Grade v3.0).

    Military-grade required fields:
    - schema_version: must be >= 3
    - type: "ci"
    - run_id: UUID for traceability
    - exec_id: commit_sha + timestamp
    - artifacts: paths to generated files
    - context_manifest_sha: SHA256 of context.md
    """

    steps: list[CIStep] = field(default_factory=list)
    schema_version: int = 3
    check_mode: bool = False
    timestamp: str = ""
    run_id: str = ""
    exec_id: str = ""
    context_manifest_sha: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()
        if not self.run_id:
            self.run_id = _generate_run_id()
        if not self.exec_id:
            self.exec_id = _generate_exec_id()
        # Compute context SHA if available
        context_path = FIXED_PATHS["context"]
        if not self.context_manifest_sha and context_path.exists():
            self.context_manifest_sha = _compute_context_sha(context_path)

    @property
    def all_passed(self) -> bool:
        """Check if all steps passed."""
        return not any(s.status == CIStepStatus.FAIL for s in self.steps)

    @property
    def failed_step(self) -> str | None:
        """Get first failed step name."""
        for step in self.steps:
            if step.status == CIStepStatus.FAIL:
                return step.name
        return None

    @property
    def overall(self) -> str:
        """Overall status string."""
        return "PASS" if self.all_passed else "FAIL"

    @property
    def exit_code(self) -> int:
        """Overall exit code (first failure)."""
        for step in self.steps:
            if step.status == CIStepStatus.FAIL and step.exit_code is not None:
                return step.exit_code
        return 0

    def add_step(self, step: CIStep) -> None:
        """Add a CI step result."""
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (Military-Grade v3.0 schema)."""
        return {
            # 强制顶层字段（缺一不可）
            "schema_version": self.schema_version,
            "type": "ci",
            "overall": self.overall,
            "exit_code": self.exit_code,
            "check_mode": self.check_mode,
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "exec_id": self.exec_id,
            "artifacts": {
                "report_path": str(FIXED_PATHS["ci_report"]),
                "context_path": str(FIXED_PATHS["context"]),
            },
            "context_manifest_sha": self.context_manifest_sha,
            # 兼容字段
            "all_passed": self.all_passed,
            "failed_step": self.failed_step,
            "steps": [s.to_dict() for s in self.steps],
        }

... (truncated, 500 of 1180 lines)
```

---
*Security: .env, secrets, credentials, CTP accounts are auto-filtered.*
