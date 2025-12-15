# V2 规格（不赶上线版）：合约化 + 跨期套利 + 无人值守 + 全自动下单 + CTP 订单状态机

> 目标：在“不急着上线实盘”的前提下，优先把系统做成 **可验证（Replay-first）**、**可恢复（Crash-safe）**、**可审计（Traceable）**、**可演进（Interface-frozen）** 的平台化架构。  
> 策略层（TopTier / MoE / DL Torch / LinearAI / SimpleAI）保持可选、不强制改公式；升级集中在 market/execution/guardian/audit 底座。

---

## 0. 总原则（贯穿所有设计）

1. **不承诺“最赚钱且不亏钱”**：只追求可控回撤、尾部风险可处理、长期期望为正。
2. **顶级 ≠ 模型复杂**：顶级 = 合约化输入 + 执行一致性/回滚 + 风控硬闸 + 可观测 + 可恢复 + 可回放审计。
3. 策略可简单，但系统必须硬：真正决定生死的是：
   - 套利腿对一致性（Pair atomicity）
   - 断流/卡单/漂移的自动处理
   - 到期/换月/流动性 gate
4. **单一真实来源（Single Source of Truth）**：
   - 订单状态：`OrderContext + FSM` 唯一维护
   - 持仓：`PositionTracker (trade-driven) + reconcile` 唯一维护
   禁止两个模块各自维护一套“真相”。
5. **Replay-first**：所有模块必须能在 `replay/sim` 下运行并有单测；CTP 只作为一个 feed/broker 实现。
6. **实盘容错，测试严格**：
   - `strict=True`（单测/回放）非法转移直接 raise
   - `strict=False`（实盘）重复/乱序事件幂等吸收，无法解释则降级/告警
7. **风险动作与策略解耦**：
   - 策略只产 `TargetPortfolio`（目标仓位）
   - 允许/禁止下单由 `execution + guardian` 决定
8. **所有自动动作必须可审计**：超时撤单、追价、降级、熔断、恢复都必须写入 audit JSONL，可回放复现。

---

## 1. 总体架构（收敛版：四大底座 + 策略层不改）

推荐目录落点（你已基本定稿）：

- `src/strategy/`：策略层（不改接口，继续可选 TopTier/MoE/DL/Linear/Simple）
- `src/market/`：合约化行情与连续主力聚合
- `src/execution/`：可靠执行（含 `auto/` 与 `protection/`）
- `src/guardian/`：无人值守守护（系统状态机与熔断/恢复）
- `src/audit/`：决策/订单/成交/守护事件留痕

> 提示：不要在 V2 引入 WAL/chaos/dashboard/多交易所网关等“V3+”设施，避免拖慢闭环。

---

## 2. 接口冻结（V2 最重要任务）

### 2.1 Market 侧核心协议
**QuoteProvider**（最小 L1）：
- `get_book_top(symbol) -> BookTop | None`  
  `BookTop={bid, ask, bid_vol, ask_vol, ts}`

**MarketFeed**：
- `start()`
- `poll() -> list[Tick]`（replay/sim/ctp 都实现）
- `subscribe(symbols: set[str])`
- `unsubscribe(symbols: set[str])`

### 2.2 Execution 侧核心协议
**Broker Protocol**（已有，需明确返回值与标识映射）：
- `place_order(intent) -> Ack`
- `cancel_order(cancel_key) -> None`
- 回调/事件：
  - `on_rtn_order(...)`
  - `on_rtn_trade(...)`
  - `on_rsp_order_insert_error(...)`
  - `on_rsp_order_action_error(...)`

### 2.3 事件结构（必须标准化）
- `OrderReport`（来自 OnRtnOrder）
- `TradeReport`（来自 OnRtnTrade）
- `BrokerError`（来自 OnRsp 失败、OnErr）
- `MarketTick` / `BookTop` / `Bar1m`
- `GuardianEvent`（降级/熔断/恢复）

> **要求**：事件结构必须是 dataclass/typed-dict，字段命名统一；audit 直接写这些结构化事件。

---

## 3. 合约化行情（Market）

### 3.1 为什么现在跨期套利做不了
当前只有品种级 AO/SA/LC 输入，无法同时获得 `AO2501` 与 `AO2505` 的 legs 价格与盘口。

### 3.2 三层：全量合约信息 + 动态选择 + 按需订阅
#### Level 1：Instrument Cache（必须）
- 启动：`ReqQryInstrument` 拉全量元数据
- 内存：`dict[symbol, InstrumentInfo]`
- 落盘：`artifacts/instruments/{exchange}_{trading_day}.json`
- 写盘原子化：`tmp -> rename`
- 文件固定结构：
  - `schema_version`
  - `trading_day`
  - `generated_at`
  - `records: {symbol: InstrumentInfo}`

InstrumentInfo 最少字段：
- `symbol`, `product`, `exchange`
- `expire_date`
- `tick_size`, `multiplier`
- （可选）`max_order_volume`, `position_limit`

#### Level 2：Universe Selector（强烈建议）
- 刷新频率：30~120 秒
- 输入：instrument cache + 最新 tick stats（oi/vol/spread/liquidity）
- 输出：
  - `dominant_by_product: dict[product, contract_symbol]`
  - `subdominant_by_product: dict[product, contract_symbol]`
  - `subscribe_set: set[contract_symbol]`（每品种 1~2 个合约，最多 3 个）

规则：
- gate：`days_to_expiry >= EXPIRY_BLOCK_DAYS`
- score：`w1*rank(open_interest)+w2*rank(volume)+w3*liquidity_score`
- **切换门槛**：新主力比旧主力高 `min_switch_edge`（如10%）
- **切换冷却**：`ROLL_COOLDOWN_S` 内不切换

#### Level 3：Subscriber（按需订阅）
- 只订阅 `subscribe_set`
- roll 后自动退订旧合约、订阅新合约
- 维护 L1 cache：bid/ask/vol/mid/oi/vol/ts
- 断流检测：
  - `stale_ms`（用于策略输入健康）
  - `hard_stale_ms`（用于执行是否允许下单，更严格）
- stale → guardian/执行层进入 reduce-only

### 3.3 连续主力 bars（不改策略但提升一致性）
输出给策略的 `MarketState` 仍以品种为 key（AO/SA/LC），但 bars/price 来自主力合约聚合：
- `product_price[AO] = mid(dominant_contract(AO))`
- `product_bar_1m[AO] = bar_builder(dominant_contract(AO))`

拼接规则写入 audit（避免回放不一致）。

---

## 4. 方案A：策略仍品种级，执行映射到合约级

### 4.1 SymbolDomain（防止混用）
TargetPortfolio 强制带域：
- `symbol_domain = "product" | "contract"`

规则：
- product domain → `product_to_contract` 映射到 dominant 合约
- contract domain → 直接执行（套利 legs）
- 混用行为默认拒绝（除非显式允许）

### 4.2 Roll 处理
- roll 后，新的 target 自动指向新 dominant
- 旧 dominant 若仍有持仓：由 rebalancer/close-then-open 渐进平掉
- 临近到期：expiry gate 触发 reduce-only/禁开仓

---

## 5. 执行层（Execution）：全自动下单 V2

### 5.1 模块落点（你已定稿）
- `src/execution/auto/`：订单生命周期引擎（FSM/超时/追价/持仓跟踪）
- `src/execution/protection/`：下单前门卫（liquidity/fat_finger/throttle）

### 5.2 CTP 报单/撤单语义（纳入规格）
报单：
- `ReqOrderInsert`
  - `OnRspOrderInsert(错误)` 或
  - `OnRtnOrder` 多次推送状态变化：
    - '0' 全部成交
    - '1' 部分成交还在队列
    - '2' 部分成交不在队列（部分成交后结束/撤）
    - '3' 未成交还在队列
    - '4' 未成交不在队列（结束态/失败态，需谨慎）
    - '5' 撤单
    - 'a' 待报
    - 'b' 尚未触发
    - 'c' 已触发

撤单：
- `ReqOrderAction`
  - `OnRspOrderAction(错误)` 或
  - `OnRtnOrder(OrderStatus='5')`

### 5.3 订单标识映射（必须写死）
OrderContext 必须包含：
- `local_id`（uuid，系统内部主键）
- `order_ref`（CTP OrderRef，place_order 返回必须有）
- `order_sys_id`（交易所系统号，OnRtnOrder 补齐）
- 以及 `front_id/session_id/exchange_id`

撤单优先级：
1. 若有 `order_sys_id` → 用它撤
2. 否则用 `order_ref`（按 broker 实现）

### 5.4 严格 FSM（测试 strict，实盘 tolerant）
- 测试/回放：`strict=True`，非法转移 raise
- 实盘：`strict=False`，幂等吸收：
  - 终态后事件：ignore + log
  - 重复事件：ignore + log
  - 乱序可解释：缓存/补全
  - 真不可解释：`ERROR` + guardian 降级

**必须补的边界：**
- **撤单途中成交**：`CANCEL_SUBMITTING/CANCEL_PENDING + RTN_FILLED -> FILLED`
- **OrderStatus='4'**：映射逻辑：
  - 无成交：建议 `ERROR`（告警+降级）
  - 有成交：`PARTIAL_CANCELLED`

### 5.5 AutoOrderEngine 行为规范
submit(intent)：
1) `protection.throttle.check`
2) `protection.fat_finger.check`
3) `protection.liquidity.check`（通过 QuoteProvider）
4) `broker.place_order` → 记录 `order_ref` → FSM 进入 waiting

回报处理：
- `on_rtn_order(report)` → 推进 FSM（accepted/cancelled/…）
- `on_rtn_trade(trade)`：
  - TradeID 去重
  - 更新 `filled_qty_total`
  - 更新 PositionTracker
  - 必要时触发 FSM 进入 PARTIAL/FILLED

tick(now)：
- ack_timeout / fill_timeout / cancel_timeout
- timeout 动作：
  - 优先撤单
  - cancel 成功后可按策略追价补单（剩余量）
  - 超过 max_retry → ERROR + guardian 降级

engine mode（由 guardian 驱动）：
- `RUNNING`：允许开仓
- `REDUCE_ONLY`：禁止开仓，只允许减仓/平仓
- `HALTED`：停止发新单 + 全撤（可选 flatten）

### 5.6 ExecContext（执行组）（V2 必须纳入）
一次调仓意图形成一个 `exec_id`，允许包含多个订单（追价/补单/重试）。  
audit 必须以 exec_id 串起全链路。

---

## 6. PositionTracker（持仓跟踪）V2 规范
双来源：
- 启动：柜台 query 同步真实仓位
- 运行：trade-driven ledger 增量更新
- 周期 reconcile：每 `reconcile_interval_s` 对账

对账失败（默认更保守）：
- 立即 `REDUCE_ONLY`
- `cancel_all`
- 若仍不一致：`HALT` 等待人工（可配置为 auto_flatten，但 V2 建议默认不自动 flatten）

---

## 7. 执行保护（protection）V2 规范
所有策略共享：

1) `liquidity.py`
- 盘口存在
- spread_ticks ≤ `LIQ_MAX_SPREAD_TICKS`
- bid/ask vol ≥ `LIQ_MIN_BIDASK_VOL`
- quote 不 stale（hard_stale）

2) `fat_finger.py`
- 单笔最大手数/最大名义
- 价格偏离上限（相对 mid 偏差）
- 禁止在涨跌停/无对手价时开仓

3) `throttle.py`
- 每 symbol 每分钟最大订单数
- 全局每分钟最大订单数
- 最小调仓间隔（防抖）

---

## 8. Guardian（无人值守守护）V2 规范

### 8.1 最小必做四件事（你已同意）
1) quote_stale：行情超时 → reduce-only / halt  
2) order_stuck：卡单 → cancel + degraded  
3) position_drift：仓位漂移 → halt + reconcile  
4) leg_imbalance（套利专用）：裸腿 → auto_hedge + 告警 + 冷却

### 8.2 Guardian 输出动作必须收敛
guardian 只输出三类硬指令：
- `set_mode(RUNNING|REDUCE_ONLY|HALTED)`
- `cancel_all()`
- `flatten_all()`（极少触发）

并要求：
- 所有触发阈值与冷却时间写入 config
- 每次状态变迁写入 audit（GuardianEvent）

---

## 9. Audit（审计）V2 规范：结构化 JSONL 事件流

统一写入 JSONL（建议按日期分文件），至少包括事件类型：
- `DecisionEvent`（策略输出 target + 特征摘要/模型版本）
- `ExecEvent`（执行计划开始/结束、exec_id）
- `OrderStateEvent`（FSM 迁移）
- `OrderTimeoutEvent` / `OrderRetryEvent` / `CancelEvent`
- `TradeEvent`（成交）
- `PositionReconcileEvent`（对账）
- `GuardianEvent`（降级/熔断/恢复）

必备字段：
- `ts`, `run_id`, `exec_id`
- `symbol`
- `order_local_id`, `order_ref`, `order_sys_id`
- `state_from`, `state_to`, `event`
- `reason` / `error_code` / `error_msg`

> V2 强调“可查询”而不是“漂亮 UI”。dashboard 属于 V3+。

---

## 10. 跨期套利（Arbitrage）V2：先工程闭环，后模型升级

### 10.1 V2 策略最小实现
- `spread_calendar_arb`：z-score +（可选）half-life filter
- legs 由 `dominant/subdominant` 或显式配置决定

### 10.2 V2 必须先做的执行门槛
- `PairExecutor`（放 execution 或 arbitrage/execution）
  - 错单/拒单/超时 → rollback/auto-hedge
- `leg_imbalance` 检测优先级最高

### 10.3 V3 才做（模型增强）
- cointegration residual（OLS/Kalman）
- ECM 信号
- regime 识别
- 更复杂 sizing（risk parity/capacity）

---

## 11. 配置（V2 建议统一）
核心配置建议：

- `AUTO_MODE = OFF|ASSISTED|LIVE|DEGRADED`
- `AUTO_ORDER_TIMEOUT_ACK_S`
- `AUTO_ORDER_TIMEOUT_FILL_S`
- `AUTO_ORDER_TIMEOUT_CANCEL_S`
- `AUTO_ORDER_MAX_RETRY`
- `LIQ_MAX_SPREAD_TICKS`
- `LIQ_MIN_BIDASK_VOL`
- `QUOTE_STALE_MS`
- `QUOTE_HARD_STALE_MS`
- `EXPIRY_BLOCK_DAYS`
- `ROLL_COOLDOWN_S`
- `REDUCE_ONLY_COOLDOWN_S`
- `RECONCILE_INTERVAL_S`
- `MIN_SWITCH_EDGE`

---

## 12. 落地顺序（不赶上线版）
> 目标：先把“接口冻结 + 回放验证 + 状态恢复演练”做完，再考虑全自动开仓与套利开仓。

### Phase A：接口冻结 + Replay-first
- types/protocols 定稿
- replay_feed/sim_feed 驱动 market + execution(不真实下单)
- audit 事件全链路打通

### Phase B：执行可靠性
- FSM tolerant + 幂等乱序处理
- 超时撤单/追价流程
- PositionTracker reconcile 演练
- protection 三件套生效

### Phase C：合约化与 roll 连续性
- instrument cache 版本化落盘
- universe selector 稳定切换（门槛+冷却）
- 连续主力 bars 拼接规则固化并审计

### Phase D：套利工程门槛
- PairExecutor + rollback/auto-hedge
- leg_imbalance/breakers
- 再迭代到协整/ECM

---

## 13. 必须确认的接口锚点（执行前置条件）
1) `CtpBroker.place_order()` 返回的 ack/标识是什么？是否包含 `order_ref`？
2) OnRtnOrder/OnRtnTrade 在 Python 侧能拿到哪些字段？至少：
   - `OrderSysID`, `OrderStatus`, `OrderRef`, `ExchangeID`
   - `TradeID`, `Volume`, `Price`, `Direction`, `OffsetFlag`
3) `cancel_order()` 入参到底需要本地 id、order_ref 还是 order_sys_id？
4) trade 回报的成交量语义（本次 vs 累计）与去重依据（TradeID）是否可靠？
5) OrderStatus='4' 在你们柜台/交易所常见吗？对应字段组合是什么？（决定映射策略）
6) 追价策略允许穿透对手价吗？（影响成本与风控）

---

## 14. 对现有策略层的保证（兼容性声明）
- TopTier/MoE/DL Torch/LinearAI/SimpleAI 的接口不改；
- 继续基于品种级 MarketState 运行；
- 合约化、roll、执行保护、自动下单、守护、审计全部在底座完成；
- 策略可逐步升级（成本门槛、调仓频率、降级 fallback 等），但不作为 V2 上线前置条件。