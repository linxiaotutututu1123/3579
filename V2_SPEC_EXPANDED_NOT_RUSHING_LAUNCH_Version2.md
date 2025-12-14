# V2（不赶上线版）扩展规格与设计说明（Expanded）
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