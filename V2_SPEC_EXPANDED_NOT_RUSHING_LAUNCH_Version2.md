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

# 扩展规格与设计说明
**主题**：合约化行情 + 主力/次主力选择 + 按需订阅 + 连续主力 bars + 全自动下单（CTP FSM）+ 执行保护 + 持仓对账 + 无人值守（Guardian）+ 审计回放  
**读者**：架构/执行/行情/策略/测试协作团队  
**目标**：先“设计正确、接口稳定、可回放可恢复可审计”，再逐步放开实盘自动开仓与顶级套利。

---

## 目录
- 0 总原则与非目标
- 1 术语与符号约定
- 2 总体架构与依赖边界（禁止反向依赖）
- 3 Replay-first 开发方式（为什么能减少返工）
- 4 合约化行情（Market）
  - 4.1 Level1 Instrument Cache
  - 4.2 Level2 Universe Selector（dominant/subdominant）
  - 4.3 Level3 Subscriber（按需订阅）
  - 4.4 连续主力聚合（产品级 MarketState）
  - 4.5 Roll/Expiry/Liquidity gate
  - 4.6 数据质量（stale / outlier / gap）最小实现
- 5 执行层（Execution）
  - 5.1 标识映射（local_id / order_ref / order_sys_id）
  - 5.2 CTP 报单/撤单语义与状态码映射
  - 5.3 订单状态机（FSM）strict/tolerant 双模式
  - 5.4 AutoOrderEngine 生命周期
  - 5.5 Partial fill / Retry / Reprice（追价）策略
  - 5.6 ExecutionPlan（close-then-open 保留）与 ExecContext（exec_id）
  - 5.7 执行保护 protection（liquidity / fat_finger / throttle）
  - 5.8 PositionTracker（trade-driven）与 reconcile
- 6 Guardian（无人值守）
  - 6.1 系统状态机（INIT/RUNNING/REDUCE_ONLY/HALTED/MANUAL）
  - 6.2 最小检测集（quote_stale/order_stuck/position_drift/leg_imbalance）
  - 6.3 统一动作接口（set_mode/cancel_all/flatten_all）
  - 6.4 重启恢复流程（cold start 演练）
- 7 Audit（审计与回放一致性）
  - 7.1 JSONL 事件流规范
  - 7.2 run_id / exec_id 关联规则
  - 7.3 回放一致性定义与 verifier
- 8 策略层兼容升级（TopTier/MoE/DL/Linear/Simple）
  - 8.1 全员共同升级（一次做全员受益）
  - 8.2 策略差异化增强建议
  - 8.3 降级策略与 fallback 机制
- 9 跨期套利（Arbitrage）
  - 9.1 V2 先完成工程门槛（PairExecutor）
  - 9.2 信号（zscore）与风险闸（stop_z/half-life/expiry）
- 10 配置规范（统一命名与默认值建议）
- 11 失败模式与应对表（FMEA 风格）
- 12 测试矩阵（单测/回放/故障注入/演练）
- 13 里程碑计划（不赶上线版）
- 14 接口锚点清单（实现前必须确认）

---

## 0. 总原则与非目标

### 0.1 总原则（强制）
1) **Replay-first**：所有模块必须在 replay/sim 环境下可运行并可单测。  
2) **接口冻结优先**：先定 types/protocols，再写实现。  
3) **单一真相**：  
   - 订单状态由 `OrderContext + FSM` 唯一维护  
   - 持仓由 `PositionTracker` 唯一维护  
4) **实盘容错，测试严格**：FSM strict 用于测试；实盘 tolerant 幂等吸收乱序/重复。  
5) **风险动作与策略解耦**：策略只产 Target；执行是否允许下单由 execution+guardian 决定。  
6) **一切自动动作可审计**：超时撤单、追价、降级、熔断、恢复都写 audit JSONL。  
7) **顶级 ≠ 目录多**：顶级 = 可控、可验证、可恢复、可复盘。  
8) **不要追求 100% 自动预测**：先把“出错时不炸”做对。

### 0.2 非目标（V2 不做 / 不强制）
- WAL / chaos / disaster drill 全套平台（可 V3）  
- dashboard/websocket/Prometheus exporter（可 V3）  
- 多交易所、多券商网关抽象（可 V3）  
- 在 V2 直接上 cointegration/ECM/Kalman 全家桶模型（先做执行门槛）

---

## 1. 术语与符号约定

- **Product（品种）**：AO / SA / LC  
- **Contract（合约）**：AO2501 / AO2505 等  
- **Dominant（主力）**：当前最优流动性合约  
- **Subdominant（次主力）**：第二流动性合约，常用于跨期套利  
- **Leg（腿）**：套利中的一个合约方向与仓位  
- **ExecContext / exec_id**：一次调仓意图（可能产生多笔订单用于追价/补单）  
- **OrderContext / local_id**：单笔订单在系统内的唯一标识  
- **order_ref**：CTP 报单引用（撤单常用）  
- **order_sys_id**：交易所系统号（最终确认、撤单/查询可能用）  
- **Reduce-only**：只允许减仓/平仓，不允许开仓  
- **Stale**：行情过期；分软 stale（策略信任）与 hard stale（执行允许下单）

---

## 2. 总体架构与依赖边界（禁止反向依赖）

### 2.1 模块划分
- `market/`：InstrumentCache + UniverseSelector + Subscriber + BarBuilder + Aggregator  
- `execution/`：Broker + FSM + AutoOrderEngine + Protection + PositionTracker + FlattenExecutor  
- `guardian/`：系统状态机 + 异常检测 + 指令输出  
- `audit/`：事件流（decision/order/trade/guardian）记录与回放校验  
- `strategy/`：策略集合（不改接口）  
- `trading/`：Orchestrator（把各模块串起来）

### 2.2 依赖方向（必须遵守）
- strategy → MarketState（只读）
- execution → market（只用于 book_top/quote、合约信息）
- guardian → market + execution（读取健康状态、订单/持仓）
- audit ← 全部模块（只订阅写日志，不反向依赖）
- trading/orchestrator → 调用各模块（唯一组装点）

---

## 3. Replay-first 开发方式（为什么能减少返工）

### 3.1 Replay-first 的定义
- 任意一天的 tick 数据回放，系统执行路径与 live 逻辑一致：  
  - 同样的订单FSM状态演进  
  - 同样的 guardian 降级/恢复  
  - 同样的 decision/audit 事件流结构  
- 差异允许：时间戳、撮合结果（sim vs real），但**决策输入输出结构一致**。

### 3.2 强制要求
- `market/feed/replay.py` 必须实现 MarketFeed Protocol  
- `execution/broker/sim_broker.py`（或 mock）必须能驱动 OnRtnOrder/OnRtnTrade 事件序列  
- 每次重大改动必须附带 replay test case

---

## 4. 合约化行情（Market）

### 4.0 背景：为什么“全部合约行情订阅”不可取
- 全市场合约 tick 推送会导致：带宽/CPU/SDK 限制/推送洪水/系统不稳定  
- 顶级做法：**全量 instrument 信息 + 按需订阅行情**（动态更新订阅集合）

---

### 4.1 Level 1：Instrument Cache（必须）

#### 4.1.1 输入与来源
- live：CTP `ReqQryInstrument`  
- replay/sim：从落盘 JSON 加载

#### 4.1.2 数据结构（最小字段）
InstrumentInfo（建议最小）：
- symbol（合约名）
- product（品种）
- exchange
- expire_date
- tick_size
- multiplier

可选字段（后续增强）：
- max_order_volume
- position_limit
- margin_ratio（若可得）

#### 4.1.3 落盘规范
路径：
- `artifacts/instruments/{exchange}_{trading_day}.json`

文件结构（固定）：
- schema_version
- trading_day
- generated_at
- records: {symbol: InstrumentInfo}

写盘原子化：
- 先写 tmp，再 rename

---

### 4.2 Level 2：Universe Selector（主力/次主力）

#### 4.2.1 输入
- InstrumentCache
- tick stats（open_interest, volume, spread, top depth）
- expiry gate 参数（EXPIRY_BLOCK_DAYS）

#### 4.2.2 输出
UniverseSnapshot：
- dominant_by_product
- subdominant_by_product
- subscribe_set
- generated_at

#### 4.2.3 评分与稳定性
评分示例：
- score = 0.7 * rank(open_interest) + 0.3 * rank(volume) + w * liquidity_score

稳定性规则：
- `min_switch_edge`：新主力比旧主力高 >= 10% 才切换
- `ROLL_COOLDOWN_S`：切换后冷却期不再切换
- 禁用列表：可把异常合约加入 denylist

---

### 4.3 Level 3：Subscriber（按需订阅）

#### 4.3.1 订阅管理
- subscribe_set 差分更新：
  - add = new - old
  - remove = old - new

#### 4.3.2 行情缓存
维护：
- quote_cache[symbol] = BookTop + derived mid + last_ts + oi/vol

stale 规则：
- soft stale：`QUOTE_STALE_MS`
- hard stale：`QUOTE_HARD_STALE_MS`（执行 gate 用）

硬 stale 触发：
- execution 禁止开仓（reduce-only）
- guardian 可进一步 HALTED（视策略）

---

### 4.4 连续主力聚合（策略兼容关键）

#### 4.4.1 方案A（策略仍品种级）
MarketService 应输出：
- prices_product[product]（从 dominant 合约 mid 聚合）
- bars_1m_product[product]（从 dominant 合约 tick→bar 聚合）

#### 4.4.2 拼接规则（必须审计）
roll 发生时 bars 如何处理必须固定并审计：
- 方案1：直接切换（会有跳变）
- 方案2：基于价差做 back-adjust（更一致但复杂）
V2 建议：先固定“直接切换”方案，同时审计切换点，后续可升级 back-adjust。

---

### 4.5 Roll/Expiry/Liquidity gate（必须）
- expiry gate：days_to_expiry < EXPIRY_BLOCK_DAYS → 永不成为 dominant/subdominant
- liquidity gate：盘口消失/spread超阈值 → reduce-only
- roll gate：切换期间进入 reduce-only 冷却（可选）

---

### 4.6 数据质量最小实现（V2 建议做）
- outlier：价格跳变（多倍 tick_size）→ 标记异常 + 可拒绝进入策略
- gap：长时间无 tick → stale
- time disorder：时间倒退 → drop 并记审计

> 不做“大而全 quality/”，先做最小门卫即可。

---

## 5. 执行层（Execution）

### 5.1 标识映射（local_id / order_ref / order_sys_id）

#### 5.1.1 为什么必须三者都存在
- local_id：系统内部串联 exec_id/audit/回放  
- order_ref：CTP 下单引用（撤单/回报关联常用）  
- order_sys_id：交易所系统号（最终确认/撤单/查询常用）  

#### 5.1.2 规则（写死）
- place_order ack 必须包含 `order_ref`（否则无法稳定撤单）
- OnRtnOrder 到来后补齐 `order_sys_id`
- cancel 优先 order_sys_id，其次 order_ref

---

### 5.2 CTP 报单/撤单语义与状态码映射（纳入规格）

CTP 报单：
- ReqOrderInsert → OnRspOrderInsert(错误) 或 OnRtnOrder(状态更新)

OrderStatus 关键值：
- '0' 全部成交
- '1' 部分成交还在队列
- '2' 部分成交不在队列（部分成交后结束/撤）
- '3' 未成交还在队列
- '4' 未成交不在队列（结束态/失败态：需结合其它字段判断）
- '5' 撤单
- 'a' 待报
- 'b' 尚未触发
- 'c' 已触发

撤单：
- ReqOrderAction → OnRspOrderAction(错误) 或 OnRtnOrder(OrderStatus='5')

---

### 5.3 FSM：strict/tolerant 双模式（你现在的严格FSM基础上升级）

#### 5.3.1 strict=True（测试/回放）
- 非法转移直接 raise
- 用于发现漏掉的边界与 bug

#### 5.3.2 strict=False（实盘/长期运行）
- 重复事件：ignore + debug log
- 终态后事件：ignore + debug log
- 乱序但可解释：缓存/补全
- 无法解释：进入 ERROR + guardian 降级

#### 5.3.3 必须补齐的边界（你已确认）
- 撤单途中成交：
  - CANCEL_SUBMITTING + RTN_FILLED → FILLED
  - CANCEL_PENDING + RTN_FILLED → FILLED
- OrderStatus='4'：
  - 无成交：ERROR（保守）+ 进入 reduce-only
  - 有成交：PARTIAL_CANCELLED

---

### 5.4 AutoOrderEngine 生命周期（行为规范）

#### 5.4.1 submit(intent) 的固定管线
1) throttle.check(intent)  
2) fat_finger.check(intent, limits, positions)  
3) liquidity.check(symbol, book_top)  
4) broker.place_order(intent) → 返回 ack(order_ref)  
5) 创建 OrderContext(local_id+order_ref，挂到 exec_id)  
6) FSM 推进到 waiting 状态

#### 5.4.2 回报入口
- on_rtn_order(report)：刷新 order_sys_id / order_status，推进 FSM  
- on_rtn_trade(trade)：TradeID 去重，更新 filled_qty_total，更新 PositionTracker

#### 5.4.3 tick(now)：超时推进
- ack_timeout：未进入可解释状态 → 尝试撤单/查询 → 不可控则 ERROR + 降级  
- fill_timeout：撤单→追价补单（剩余量）或进入 ERROR  
- cancel_timeout：撤单无响应 → ERROR + HALTED（强制人工）

#### 5.4.4 mode（由 guardian 驱动）
- RUNNING：允许开仓+平仓  
- REDUCE_ONLY：禁止开仓，仅平仓/减仓  
- HALTED：停止发新单 + cancel_all（可选 flatten_all）

---

### 5.5 Partial fill / Retry / Reprice（追价）策略规范

#### 5.5.1 Partial fill 的默认策略（V2）
- 若 remaining_qty > 0：
  - 等待 fill_timeout
  - 超时则撤单 → 追价补单（剩余量）
- Partial fill 不允许无限补单：受 max_retry 限制

#### 5.5.2 Retry（指数退避）
- retry_count 随 exec_id 记录（不是仅 per-order）
- backoff：min( base * 2^k , max_backoff )
- max_retry：到达后进入 ERROR + 降级

#### 5.5.3 Reprice 模式（可配置）
- to_best：对手价（买→ask，卖→bid）
- to_best_plus_tick：对手价±1 tick
- to_cross：允许穿透（成本高，成交快）
V2 仅推荐默认 `to_best` 或 `to_best_plus_tick`。

---

### 5.6 ExecutionPlan（close-then-open 保留）与 ExecContext（exec_id）

#### 5.6.1 close-then-open 仍保留
- 它负责把目标仓位变化拆成有序 intents：
  - 先平风险，再开新仓（降低保证金/方向暴露）

#### 5.6.2 ExecContext 必须引入（V2）
- 每次调仓产生一个 exec_id
- exec_id 下可包含多个订单（追价/补单/重试）
- exec_id 写入 audit，并用于恢复/调试

---

### 5.7 执行保护 protection（必须）
- liquidity：盘口存在 + spread + volume + hard-stale
- fat_finger：手数/名义/价格偏离/涨跌停禁开仓
- throttle：频率/全局订单上限/最小调仓间隔

保护拒单必须产生审计事件（原因+阈值+采样book_top）。

---

### 5.8 PositionTracker（trade-driven）与 reconcile

#### 5.8.1 双来源策略
- 启动 query：同步真实仓位
- 运行 trade-driven：按 TradeReport 更新本地账本
- 周期 reconcile：每 30~60s（可配）

#### 5.8.2 对账失败动作（不赶上线更保守）
- 立即 set_mode(REDUCE_ONLY)
- cancel_all
- 若仍不一致：HALTED 等待人工
（是否 auto_flatten 作为可配置项，不建议默认）

---

## 6. Guardian（无人值守）

### 6.1 状态机
- INIT → RUNNING ↔ REDUCE_ONLY → HALTED → MANUAL

### 6.2 最小检测集（必须）
- quote_stale：硬 stale（QUOTE_HARD_STALE_MS）
- order_stuck：订单长时间不推进（基于 FSM + timeout 指标）
- position_drift：reconcile 不一致
- leg_imbalance（套利专用）：单腿敞口超阈值或未对冲成交

### 6.3 输出动作收敛（只允许）
- set_mode(...)
- cancel_all()
- flatten_all()（极少触发）

所有 guardian 动作必须写入 audit（GuardianEvent）。

### 6.4 重启恢复流程（必须可演练）
冷启动建议：
1) cancel_all 未完成订单
2) query positions → PositionTracker 同步
3) set_mode(REDUCE_ONLY) 冷却（REDUCE_ONLY_COOLDOWN_S）
4) 订阅就绪且稳定 N 秒
5) 冷却结束后允许 RUNNING（如果健康检查通过）

---

## 7. Audit（审计与回放一致性）

### 7.1 JSONL 事件流规范
事件至少：
- DecisionEvent
- ExecEvent
- OrderStateEvent
- OrderTimeoutEvent / RetryEvent / CancelEvent
- TradeEvent
- PositionReconcileEvent
- GuardianEvent

必须字段：
- ts, run_id, exec_id
- symbol
- order_local_id, order_ref, order_sys_id
- state_from/state_to/event
- reason/error_code/error_msg（如有）

### 7.2 关联规则
- run_id：一次运行唯一
- exec_id：一次调仓/执行意图
- order_local_id：单笔订单主键
- trade_id：成交去重关键

### 7.3 回放一致性定义（V2）
同一 inputs（ticks+instruments+config）下：
- DecisionEvent 序列一致（允许 ts 有微差）
- ExecEvent 结构一致
- protection 拒单原因一致
- guardian 状态迁移一致

可选 verifier：
- replay_verifier 对事件序列做 hash/关键字段对比

---

## 8. 策略层兼容升级（你问的“那些策略共同升级/单独建议”）

### 8.1 所有策略共同吃到的升级（一次做，全员受益）
- 连续主力 bars（roll-aware）
- 执行保护（liquidity/fat_finger/throttle）
- 自动下单 FSM + 超时撤单/追价可控
- PositionTracker + reconcile（避免漂移）
- Guardian：quote_stale/order_stuck/position_drift
- Audit：decision_log + order_trail

### 8.2 单独建议（按策略差异）
- TopTier：成本门槛 + 调仓频率限制（避免震荡磨损）
- MoE：专家冲突抑制 + 输出平滑（EWMA / 限制变化幅度）
- DL Torch：推理失败 fallback（-> Linear/Simple 或 0）+ 模型版本写入审计
- LinearAI/SimpleAI：非常适合作为 guardian DEGRADED 时兜底（reduce-only兼容、稳定）

### 8.3 降级策略（推荐）
- guardian 进入 REDUCE_ONLY：
  - 系统禁止开仓
  - 复杂策略可被切换为 Linear/Simple 或直接输出 0（视你编排层实现）

---

## 9. 跨期套利（Arbitrage）V2：工程门槛优先

### 9.1 V2 先完成的工程门槛
- PairExecutor（两腿原子性 + rollback/auto-hedge）
- leg_imbalance 检测与应急
- expiry/liquidity gate + stop_z breaker

### 9.2 信号（V2 推荐先简单）
- spread = p_near - beta * p_far
- zscore entry/exit/stop（entry 2.5, exit 0.5, stop 5~6）
- half-life 过滤（可选）

---

## 10. 配置规范（统一命名建议）

- AUTO_MODE = OFF|ASSISTED|LIVE|DEGRADED
- QUOTE_STALE_MS
- QUOTE_HARD_STALE_MS
- AUTO_ORDER_TIMEOUT_ACK_S
- AUTO_ORDER_TIMEOUT_FILL_S
- AUTO_ORDER_TIMEOUT_CANCEL_S
- AUTO_ORDER_MAX_RETRY
- REPRICE_MODE = to_best|to_best_plus_tick|to_cross
- LIQ_MAX_SPREAD_TICKS
- LIQ_MIN_BIDASK_VOL
- FATFINGER_MAX_QTY
- FATFINGER_MAX_NOTIONAL
- THROTTLE_MAX_ORDERS_PER_MIN
- THROTTLE_MAX_ORDERS_PER_MIN_PER_SYMBOL
- EXPIRY_BLOCK_DAYS
- MIN_SWITCH_EDGE
- ROLL_COOLDOWN_S
- REDUCE_ONLY_COOLDOWN_S
- RECONCILE_INTERVAL_S

---

## 11. 失败模式与应对表（FMEA 风格）

| 失败模式 | 典型症状 | 危害 | 检测 | 默认动作（V2） | 审计 |
|---|---|---|---|---|---|
| 行情断流 | book_top ts 过期 | 误下单/滑点爆炸 | quote_stale | REDUCE_ONLY 或 HALTED | GuardianEvent |
| 卡单 | FSM 长时间不推进 | 风险敞口失控 | order_stuck | cancel_all + REDUCE_ONLY | OrderTimeoutEvent |
| 撤单无响应 | cancel_pending 超时 | 不可控 | cancel_timeout | HALTED 等待人工 | OrderTimeoutEvent |
| 持仓漂移 | reconcile 不一致 | 风险未知 | position_drift | HALTED + 对账 | PositionReconcileEvent |
| 部分成交卡住 | partial 长时间不变 | 裸露风险 | fill_timeout | cancel + reprice（限重试） | RetryEvent |
| 主力频繁切换 | dominant 抖动 | 特征/执行抖动 | cooldown/edge | 冷却/门槛抑制 | UniverseSnapshot |
| 临期未处理 | 近到期仍持仓 | 被动强平 | expiry_gate | 禁开仓/减仓 | GuardianEvent |

---

## 12. 测试矩阵（必须配套）

### 12.1 单元测试（strict FSM）
- 订单状态机所有 TRANSITIONS 覆盖
- 撤单途中成交路径
- OrderStatus='4' 映射逻辑
- 幂等：重复事件/终态事件

### 12.2 回放测试（Replay-first）
- 同 ticks 回放 → DecisionEvent/GuardianEvent 可复现
- roll 切换点与 bars 拼接一致
- protection 拒单一致

### 12.3 故障注入（最少做）
- 人为断开行情输入 → quote_stale → REDUCE_ONLY
- 模拟 OnRtnOrder 丢失/乱序 → tolerant 吸收/降级
- 模拟 reconcile 漂移 → HALTED

### 12.4 演练（不赶上线反而要做）
- kill -9 重启流程演练（撤单→同步→冷却→恢复）
- 部分成交+第二腿失败（套利）→ rollback/auto-hedge

---

## 13. 里程碑计划（不赶上线版）

### Phase A：接口冻结 + Replay-first
- 冻结 types/protocols
- replay_feed/sim_broker 打通 market→strategy→execution（可不真实下单）
- audit 事件流全链路

### Phase B：执行可靠性
- FSM tolerant 幂等乱序
- 超时撤单/追价（可配置）
- PositionTracker reconcile
- protection 生效

### Phase C：市场侧连续性
- instrument cache 版本化落盘
- universe selector 稳定切换（门槛+冷却）
- 连续主力 bars 拼接规则与审计

### Phase D：套利工程门槛
- PairExecutor + rollback/auto-hedge
- leg_imbalance/breakers
- 之后再做协整/ECM/Kalman

---

## 14. 接口锚点（实现前必须确认）

1) `CtpBroker.place_order()` 返回是否包含 `order_ref`？是否能同步拿到 front_id/session_id？  
2) Python 侧 OnRtnOrder/OnRtnTrade 的字段集（OrderSysID/OrderStatus/TradeID/Volume/Price/OffsetFlag 等）具体长什么样？  
3) `cancel_order()` 需要 ref 还是 sys_id？能否查询当前订单状态（可选）？  
4) Trade 回报 volume 是本次还是累计？TradeID 是否可靠可去重？  
5) OrderStatus='4' 在你们柜台实测含义（组合字段）是什么？  
6) 追价策略是否允许穿透对手价（to_cross）？默认用哪种？  

--- 

## 附录：你目前已有组件如何被这套吸收（不推翻）
- `CtpBroker`：仍负责发送/撤单 + 回报适配为 OrderReport/TradeReport
- `OrderTracker`：建议融合进 FSM/OrderContext，避免双真相
- `close-then-open`：保留，作为 ExecutionPlanBuilder 生成 intents
- `FlattenExecutor`：保留，作为 guardian 最终动作（极少触发）