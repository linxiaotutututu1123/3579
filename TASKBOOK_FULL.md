# 如何使用 Claude Code 执行任务书

1) 在仓库根目录打开终端，确保已切到目标分支：`feat/mode2-trading-pipeline`。
2) 严格按任务书 Feature 顺序实现（F1→F21），**不要跳步**。
3) 每完成一个 Feature（或一次完美化迭代）都必须运行并通过：
   `powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 check`
4) Gate 全绿后再提交并 push；commit message 使用 Conventional Commits。
5) 任何时候都**不得修改** `src/orchestrator.py::handle_risk_update()` 的既有行为；只能新增并行入口。

---

# Claude 一次性任务书（究极完整版｜多策略｜Torch 深度学习｜CTP 全自动下单｜强风控闭环｜CI Gate）

> 适用仓库：`linxiaotutututu1123/3579`（main）  
> 目标：实现“方式2：策略/AI输出目标净仓位（TargetPortfolio），规则引擎约束与下单”的**完整闭环**，并扩展到**多策略（含 Torch DL）**、**PAPER/LIVE 全自动**、**CTP 实盘下单**。  
> 验收：GitHub Actions / `scripts/dev.ps1 check` 全绿（ruff format check + ruff lint + mypy + pytest）。  
> 重要：**不得破坏** `src/orchestrator.py::handle_risk_update()` 的现有行为（HG5/HG6/correlation 审计依赖）。

---

## 目录

- [0. 冻结规则（风控最终规则，绝对不可改）](#0-冻结规则风控最终规则绝对不可改)
- [1. 代码结构总体设计（方式2总架构）](#1-代码结构总体设计方式2总架构)
- [2. 必须的改动与新增文件清单（按提交顺序）](#2-必须的改动与新增文件清单按提交顺序)
- [3. F1~F10（方式2闭环）详细实现要求](#3-f1f10方式2闭环详细实现要求)
- [4. F11~F16（多策略 + Torch DL + 模型管理）详细实现要求](#4-f11f16多策略--torch-dl--模型管理详细实现要求)
- [5. F17~F21（CTP Broker + 实盘 Runner + LIVE 自动下单）详细实现要求](#5-f17f21ctp-broker--实盘-runner--live-自动下单详细实现要求)
- [6. 事件与审计（correlation_id 贯穿、特征hash、可回放一致性）](#6-事件与审计correlation_id-贯穿特征hash可回放一致性)
- [7. 测试计划（必须新增的 tests 全量清单）](#7-测试计划必须新增的-tests-全量清单)
- [8. 配置与启动参数（PAPER/LIVE、策略选择、模型、CTP）](#8-配置与启动参数paperlive策略选择模型ctp)
- [9. 执行与运行手册（Replay / PAPER / LIVE）](#9-执行与运行手册replay--paper--live)
- [10. 交付与合并策略（小步提交 + CI Gate）](#10-交付与合并策略小步提交--ci-gate)

---

## 0. 冻结规则（风控最终规则，绝对不可改）

### 0.1 日亏损熔断状态机（必须与现有 RiskManager 状态机完全一致）
- 当日权益基准：**09:00**
  - 调用 `RiskManager.on_day_start_0900(AccountSnapshot, correlation_id=...)` 设置 `state.e0`
- 日亏损阈值：`dd_limit = -0.03`
- 首次触线（dd <= -0.03）：
  - 触发 `_fire_kill_switch()`（cancel all + force flatten）
  - `mode = COOLDOWN`
  - 冷却 `cooldown_seconds = 90*60`
  - `kill_switch_fired_today = True`
- 冷却到点：进入 `RECOVERY`
- `RECOVERY` 风险预算乘数：`recovery_risk_multiplier = 0.30`（用于缩放目标仓位）
- “当日不能出现两次触发流程”：
  - 若当天已触发过一次（`kill_switch_fired_today=True`），再次触线：
    - `mode = LOCKED`
    - **禁止开仓**
    - **不得再次调用** cancel/flatten
- 保证金占用硬闸：
  - `NORMAL`：`max_margin_normal = 0.70`
  - `RECOVERY`：`max_margin_recovery = 0.50`（从 0.40 改为 0.50）

### 0.2 Universe（策略默认交易品种）
- `AO / SA / LC`

---

## 1. 代码结构总体设计（方式2总架构）

### 1.1 总流水线（每个 tick）
1) 风控更新（不改变既有风控主流程）
   - `risk.update(snap, correlation_id=cid)`
   - 读取 `risk.pop_events()`
2) 策略（AI）输出目标净仓位
   - `TargetPortfolio(target_net_qty, model_version, features_hash)`
3) 规则引擎约束（Constraints）
   - mode gate（COOLDOWN/LOCKED -> 禁止交易）
   - RECOVERY 缩放 0.3
   - margin gate：允许减仓、禁止加仓
   - max_abs / max_turnover
4) Rebalancer（当前净仓位 -> 目标净仓位 -> OrderIntent[]）
   - 支持 cross-zero 分解成 **先平仓 CLOSE，再开仓 OPEN**
5) 串行执行（最高等级要求）
   - 先执行 close_batch
   - 若 close_batch 出现拒单（ExecutionEventType.ORDER_REJECTED）→ 跳过 open_batch
6) 事件化审计（TradingEvent + ExecutionEvent + RiskEvent）
7) PAPER/LIVE 控制
   - PAPER：不下单，只产出 intents/events
   - LIVE：真实下单（CTP broker）

### 1.2 关键兼容性约束
- **绝对不得修改** `src/orchestrator.py::handle_risk_update()` 的行为
- Trading 事件体系独立：`src/trading/events.py`
- correlation_id 贯穿 风控 / 交易 / 执行 全链路
- CI gate：`scripts/dev.ps1 check`

---

## 2. 必须的改动与新增文件清单（按提交顺序）

> 要求：严格小步提交。每步 `scripts/dev.ps1 check` 全绿后 commit + push。

### 2.1 修改文件（最少）
- `src/execution/order_types.py`（加 Offset.OPEN）
- `src/risk/state.py`（max_margin_recovery=0.50）
- `tests/test_risk_state_machine.py`（更新 0.40→0.50 的断言）

### 2.2 新增目录
- `src/strategy/`
- `src/portfolio/`
- `src/trading/`
- `src/brokers/ctp/`（如做 CTP）

### 2.3 新增文件（方式2闭环）
- `src/strategy/types.py`
- `src/strategy/base.py`
- `src/strategy/simple_ai.py`
- `src/strategy/top_tier_trend_risk_parity.py`
- `src/portfolio/constraints.py`
- `src/portfolio/rebalancer.py`
- `src/trading/events.py`
- `src/trading/controls.py`
- `src/trading/serial_exec.py`
- `src/trading/orchestrator.py`
- `src/strategy/factory.py`
- `src/trading/result.py`（建议：统一返回结构）
- `src/trading/utils.py`（建议：stable_json/uuid/ts）

### 2.4 新增文件（多策略 + Torch）
- `src/strategy/dl/features.py`
- `src/strategy/dl/model.py`
- `src/strategy/dl/policy.py`
- `src/strategy/dl/weights.py`（加载与hash）
- `src/strategy/dl_torch_policy.py`（Strategy 适配层）
- `src/strategy/ensemble_moe.py`（多专家 gating）
- `src/strategy/linear_ai.py`（无 torch 的线性AI）

### 2.5 新增文件（CTP）
- `src/brokers/ctp/config.py`
- `src/brokers/ctp/broker.py`
- `src/brokers/ctp/mapping.py`
- `src/brokers/ctp/errors.py`

### 2.6 新增测试（全量见第7节）

---

## 3. F1~F10（方式2闭环）详细实现要求

### F1：Offset.OPEN（必须）
**文件**：`src/execution/order_types.py`
- `Offset` Enum 增加：`OPEN="OPEN"`
- 不改 `OrderIntent` 结构

**测试**：`tests/test_order_types_offset_open.py`
- `assert Offset.OPEN.value == "OPEN"`

---

### F2：风控 max_margin_recovery=0.50 + lockout 测试（必须）
**文件**：`src/risk/state.py`
- `RiskConfig.max_margin_recovery = 0.50`

确保 RiskState 属性完整：
- `flatten_in_progress: bool`
- `flatten_completed_today: bool`
> 若仓库已有则不改；若缺失则补齐默认 False（保持语义）。

**修测试**：`tests/test_risk_state_machine.py`
- 将 recovery margin gate 测试对齐 0.50
- margin_used 用 550_000 (0.55) 触发 blocked
- 所有调用补 `correlation_id="cid"`

**新增测试**：`tests/test_risk_daily_loss_lockout.py`
- now_cb 可控（fake time）
- 首次 dd<=-0.03：mode=COOLDOWN、kill_switch_fired_today=True、cancel/flatten 计数=1
- 推进到 cooldown_end_ts：mode=RECOVERY
- 再触线 dd<=-0.03：mode=LOCKED 且 cancel/flatten 未再次触发（计数仍 1）

---

### F3：Strategy Types（必须含 bars_1m）
**文件**：`src/strategy/types.py`
- 定义 `Bar1m`（TypedDict 推荐）
  - ts/open/high/low/close/volume
- `MarketState(prices, equity, bars_1m)`
- `TargetPortfolio(target_net_qty, model_version, features_hash)`

**文件**：`src/strategy/base.py`
- `Strategy(ABC)` with `on_tick`

**文件**：`src/strategy/simple_ai.py`
- `SimpleAIStrategy(symbols)`：输出可跑通 pipeline 的最小目标
- `features_hash`：sha256(stable_json(features))

---

### F4：顶级策略 v1（非DL，量化可解释顶级路线）
**文件**：`src/strategy/top_tier_trend_risk_parity.py`
必须实现（numpy-only，deterministic）：
- 多周期动量 mom_15/60/240（log-return）
- EWMA vol（half-life=60）
- risk parity-ish sizing（risk_budget ∝ abs(signal)，pos ∝ risk_budget/vol）
- smoothing_alpha 降换手
- 输出 int qty，abs<=max_abs_qty_per_symbol
- 输出 `model_version="top-tier-trend-risk-parity-v1"`

**测试**：`tests/test_top_tier_strategy_smoke.py`（>=300 bars）

---

### F5：Constraints（必须）
**文件**：`src/portfolio/constraints.py`
函数：`clamp_target(risk, snap, current_net_qty, target) -> (TargetPortfolio, audit)`
规则：
1) COOLDOWN/LOCKED：clamp=current；audit.blocked_by_mode
2) RECOVERY：target*0.3 round；audit.recovery_scaled
3) margin gate：
   - 若 `risk.can_open(snap)==False`：禁止加仓，允许减仓到 0（reduce-only）
4) max_abs_qty_per_symbol=2
5) max_turnover_qty_per_tick=2
6) audit 记录触发原因与被 clamp 详情

**测试**：`tests/test_constraints_recovery_and_margin.py`

---

### F6：Rebalancer（必须）
**文件**：`src/portfolio/rebalancer.py`
- 输入：current_net_qty/target_net_qty/mid_prices
- 输出：`list[OrderIntent]`
- cross-zero 必须拆：先 CLOSE 再 OPEN
- 同向增仓：OPEN，同向减仓：CLOSE
- price 用 mid

**测试**：`tests/test_rebalancer_cross_zero_split.py`

---

### F7：Trading Events + Controls（必须）
**文件**：`src/trading/events.py`
- TradingEventType enum：
  - SIGNAL_GENERATED, TARGET_PORTFOLIO_SET, TARGET_PORTFOLIO_CLAMPED
  - ORDERS_INTENDED, ORDERS_SENT
  - EXEC_BATCH_STARTED, EXEC_BATCH_FINISHED
  - OPEN_SKIPPED_DUE_TO_CLOSE_FAILURE
- `TradingEvent(type, ts, correlation_id, data)`

**文件**：`src/trading/controls.py`
- `TradeMode(PAPER/LIVE)`
- `TradeControls(mode=PAPER)`

---

### F8：串行执行（先平后开）
**文件**：`src/trading/serial_exec.py`
- 依据 Offset 拆 close/open batch
- 执行 close_batch：
  - `executor.execute(close_batch, correlation_id=cid)`
  - `close_events = executor.drain_events()`
- 若 close_events 含 `ExecutionEventType.ORDER_REJECTED`：
  - skip open_batch
  - emit `OPEN_SKIPPED_DUE_TO_CLOSE_FAILURE`
- 否则执行 open_batch

**测试**：`tests/test_serial_close_then_open_ordering.py`
- RecordingBroker：断言 CLOSE 在 OPEN 前
- RejectCloseBroker：close reject 时 open 不发送

---

### F9：Trading Orchestrator（方式2 tick 主入口）
**文件**：`src/trading/orchestrator.py`
函数：`handle_trading_tick(...) -> TradingTickResult`
建议新增返回结构：
- `TradingTickResult(correlation_id, trading_events, risk_events, execution_events, intents, target, clamped_target, audit)`

行为：
1) cid=uuid（允许外部传）
2) `risk.update(snap, correlation_id=cid)` + `risk.pop_events()`
3) `strategy.on_tick(MarketState(prices,equity,bars_1m))`
4) 发 SIGNAL/TARGET 事件
5) clamp_target：变更发 CLAMPED
6) rebalancer：发 ORDERS_INTENDED（含订单明细）
7) PAPER：不下单
8) LIVE：
   - 发 ORDERS_SENT
   - serial_exec 执行 close then open
   - 合并 execution events

**测试**：`tests/test_trading_tick_pipeline_paper.py`

---

### F10：配置驱动（PAPER/LIVE + 策略选择 + replay mode2 入口）
**文件**：`src/config.py`（或你现有 settings 系统）
新增配置项（必须 env 可驱动）：
- `TRADE_MODE`：PAPER/LIVE（默认 PAPER）
- `STRATEGY_NAME`：simple_ai/top_tier/linear_ai/moe/dl_torch（默认 top_tier）
- `STRATEGY_SYMBOLS`：默认 AO,SA,LC
- `DL_MODEL_PATH` / `DL_DEVICE=cpu` / `DL_WINDOW=240` 等

**文件**：`src/strategy/factory.py`
- `build_strategy(settings) -> Strategy`（多策略注册）

**Replay 接入（必须，不破坏旧入口）**
- **禁止修改**现有 `run_replay_tick()`（你贴的那个）
- 新增 `run_replay_tick_mode2()`（放在 replay 目录合适位置）
  - 先 `handle_risk_update(...)`（保持一致）
  - 再 `handle_trading_tick(...)`（用 settings.trade_mode）
  - prices 从 books 算 mid
  - current_net_qty 从 positions 提取
  - bars_1m 由 replay 数据源注入（若缺失则在函数签名显式要求）

---

## 4. F11~F16（多策略 + Torch DL + 模型管理）详细实现要求

> 目标：达到“多策略多AI”的顶级形态：  
> - DL Torch 策略（推理）  
> - 无 torch 的线性AI策略（可审计）  
> - 多专家（MoE）集成策略（AI风格）  
> - 策略统一输出 TargetPortfolio，方式2闭环统一接管下单

### F11：线性AI策略（无需torch，强可控）
**文件**：`src/strategy/linear_ai.py`
- 特征：mom/vol/volume shock/range 等（固定窗口）
- score = w·x（权重来自配置）
- score -> int qty（tanh/clip）
- model_version="linear-ai-v1"
- features_hash 包含 w 与 x

**测试**：`tests/test_linear_ai_smoke.py`

---

### F12：多专家 MoE（顶级“AI融合”）
**文件**：`src/strategy/ensemble_moe.py`
- 专家1：趋势（top-tier 信号）
- 专家2：均值回复（例如 zscore 反向）
- 专家3：突破（range breakout）
- gating：基于 regime 特征（趋势强度/波动/噪音比）分配权重
- 输出融合 target

**测试**：`tests/test_moe_strategy_smoke.py`

---

### F13：Torch 推理策略（DL）
#### 设计原则（必须）
- **仅 inference，不训练**
- deterministic：固定线程/算法
- `features_hash` 包含：特征 + 模型hash + 推理配置
- 模型文件版本化：hash -> model_version

#### 文件结构（建议）
- `src/strategy/dl/features.py`：numpy 特征工程（窗口化，归一化）
- `src/strategy/dl/model.py`：PyTorch 模型结构定义
- `src/strategy/dl/weights.py`：权重加载、hash、缓存
- `src/strategy/dl/policy.py`：inference pipeline（symbol batch -> scores）
- `src/strategy/dl_torch_policy.py`：Strategy 适配（on_tick -> TargetPortfolio）

#### 必须功能
- `DL_WINDOW` 默认 240 或 480
- 输入：bars_1m closes + volume + range
- 输出：每个 symbol 一个 score（回归或分类-logit 都可）
- score -> qty：
  - `qty = round(tanh(score) * max_abs_qty_per_symbol)`
  - 后续仍会经过 constraints 再 clamp（双保险）
- `DL_DEVICE` 默认 cpu（CI 必须可跑）

#### 权重文件管理（必须选一种并写清楚）
- A：小模型权重（state_dict.pt）直接提交仓库（推荐用于CI）
- B：Git LFS
- C：CI 下载 release asset（需要公开URL或token）

**测试**：`tests/test_dl_torch_policy_smoke.py`
- 使用内置小权重或固定seed权重
- 300 bars 输入，输出合法 qty，hash/version 非空

---

### F14：策略注册与选择（必须）
`src/strategy/factory.py`
- 支持：simple_ai/top_tier/linear_ai/moe/dl_torch
- 每个策略都接 `symbols`，并在 features_hash 中包含 symbols

---

### F15：策略一致性与审计（必须）
- 所有策略必须：
  - 输出覆盖 universe 的每个 symbol（缺数据则输出 0）
  - features_hash：sha256(stable_json(features))
  - model_version：固定字符串 +（可选）模型hash截断
- 添加 `tests/test_strategy_contract.py`：
  - 对所有策略跑相同的 contract 检查（类型、hash、输出 keys）

---

### F16：风险预算与仓位解释层（可选但推荐）
新增 `src/strategy/explain.py`
- 把策略输出转成审计可读字段（signal/vol/weights/score）
- 由 orchestrator 在 TradingEvent.data 中携带精简版 explain（避免事件太大）

---

## 5. F17~F21（CTP Broker + 实盘 Runner + LIVE 自动下单）详细实现要求

> 注意：如果你没有可 pip 安装的 CTP Python SDK，CI 会很难绿。  
> 要求：至少保证 PAPER 能全绿；LIVE 在本地装好 CTP 依赖后可运行。

### F17：CTP 配置（必须）
`src/brokers/ctp/config.py`
- 读取 env：
  - `CTP_FRONT_ADDR`
  - `CTP_BROKER_ID`
  - `CTP_USER_ID`
  - `CTP_PASSWORD`
  - `CTP_APP_ID`（可选）
  - `CTP_AUTH_CODE`（可选）
- validate：`TRADE_MODE=LIVE` 时缺任何关键项 -> raise

---

### F18：CTP order 映射（必须）
`src/brokers/ctp/mapping.py`
- Side/Offset -> CTP Direction/OffsetFlag
- OPEN/CLOSE/CLOSETODAY 映射明确写死
- symbol 合约映射策略（如果你的 symbol 本身就含交易所合约代码，则直接透传）

---

### F19：CTP Broker 实现（必须）
`src/brokers/ctp/broker.py`
- `class CtpBroker(Broker)` 实现 `place_order`
- 下单失败抛 `OrderRejected`
- place_order 返回 `OrderAck(order_id=...)`
- 最小可用：同步返回本地order_id（真实回报事件后续再接入）

---

### F20：Broker 选择（PAPER/LIVE）
新增 `src/execution/broker_factory.py`
- PAPER：NoopBroker（仅 ack，不发真实单）
- LIVE：CtpBroker（必须配置齐全）

---

### F21：实盘 Runner 接入（必须，且不动 handle_risk_update 行为）
> 不要求改 `src/main.py`，但必须提供一个可运行入口，比如：
- `src/live/runner.py`（新建）
- 或在 `src/runner.py` 中新增新函数，但保持旧行为

Runner 需要做：
1) 加载 Settings（含 trade_mode/strategy）
2) build broker/executor/strategy/risk
3) 每 tick 拉取：
   - AccountSnapshot（equity/margin_used）
   - current positions（net_qty per symbol）
   - booktop(mid) or prices
   - bars_1m（最近N根）
4) 09:00 调 `on_day_start_0900`
5) tick 内按顺序：
   - `handle_risk_update(...)`（kill-switch flatten，不可改其逻辑）
   - `handle_trading_tick(...)`（方式2正常交易）
6) 记录事件日志（至少写到 artifacts/log 或 stdout）

---

## 6. 事件与审计（correlation_id 贯穿、特征hash、可回放一致性）

### 6.1 correlation_id 贯穿
- RiskManager.update(..., correlation_id=cid)
- on_day_start_0900(..., correlation_id=cid)
- executor.execute(..., correlation_id=cid)
- TradingEvent 必须带 cid
- ExecutionEvent/RiskEvent 你仓库已有 cid 字段就沿用

### 6.2 features_hash
- 对策略特征与关键参数 stable_json + sha256
- DL 策略另加 model_hash（权重hash）进入 features_hash

### 6.3 可回放一致性
- replay tick 输入相同 -> 输出事件序列一致（除 correlation_id/ts 允许不同）
- 建议：replay 提供 deterministic now_ts

---

## 7. 测试计划（必须新增的 tests 全量清单）

> 这些 tests 必须全部新增并通过（与任务书 F1~F21 对齐）。

### 7.1 必须新增
- `tests/test_order_types_offset_open.py`
- `tests/test_risk_daily_loss_lockout.py`
- `tests/test_constraints_recovery_and_margin.py`
- `tests/test_rebalancer_cross_zero_split.py`
- `tests/test_serial_close_then_open_ordering.py`
- `tests/test_trading_tick_pipeline_paper.py`
- `tests/test_top_tier_strategy_smoke.py`

### 7.2 多策略新增
- `tests/test_linear_ai_smoke.py`
- `tests/test_moe_strategy_smoke.py`
- `tests/test_dl_torch_policy_smoke.py`
- `tests/test_strategy_contract.py`

### 7.3 必须修改
- `tests/test_risk_state_machine.py`（0.40→0.50 对齐）

---

## 8. 配置与启动参数（PAPER/LIVE、策略选择、模型、CTP）

### 8.1 env keys（必须支持）
- `TRADE_MODE=PAPER|LIVE`
- `STRATEGY_NAME=top_tier|dl_torch|moe|linear_ai|simple_ai`
- `STRATEGY_SYMBOLS=AO,SA,LC`

DL：
- `DL_MODEL_PATH=...`
- `DL_DEVICE=cpu`
- `DL_WINDOW=240`
- `DL_MAX_ABS_QTY=2`

CTP（LIVE 必填）：
- `CTP_FRONT_ADDR=...`
- `CTP_BROKER_ID=...`
- `CTP_USER_ID=...`
- `CTP_PASSWORD=...`
- `CTP_APP_ID`（可选）
- `CTP_AUTH_CODE`（可选）

---

## 9. 执行与运行手册（Replay / PAPER / LIVE）

### 9.1 开发检查（等价 CI）
- `./scripts/dev.ps1 init`
- `./scripts/dev.ps1 check`

### 9.2 Replay
- 使用 `run_replay_tick()` 仅风控强平（保持不动）
- 使用 `run_replay_tick_mode2()` 同时跑方式2 trading（PAPER 默认）

### 9.3 PAPER
- `TRADE_MODE=PAPER`
- broker=NoopBroker
- 产生 TradingEvent/Intents 但不发真实单

### 9.4 LIVE（CTP）
- `TRADE_MODE=LIVE`
- broker=CtpBroker
- 确保 CTP 配置齐全
- 强风控：任何拒单/异常保证先平后开与熔断规则生效

---

## 10. 交付与合并策略（小步提交 + CI Gate）

### 10.1 强制小步提交
每个 Feature（F1..F21）必须：
1) 修改最少文件
2) `scripts/dev.ps1 check` 全绿
3) commit + push
4) GitHub Actions 绿后再继续下一 Feature

### 10.2 建议分支
- `feat/mode2-trading-pipeline`
- `feat/multi-strategy-ai`
- `feat/ctp-live-broker`

---

## 最终说明（给 Claude 的硬性执行要求）

- 你必须按 F1→F21 的顺序实现，不允许跳跃。
- 每一步都要保证 `scripts/dev.ps1 check` 全绿后再提交。
- 不允许改 `src/orchestrator.py::handle_risk_update()` 的行为（只可新增并行入口）。
- Torch/CTP 导入必须确保 CI 可运行：
  - 若 CTP 包无法 pip 安装，请将 CTP broker 实现做成可选导入（LIVE 时才 import），CI 仍可绿。
  - Torch 若 CI 安装困难，至少保证 DL 策略在 CI 下可以 import（可用轻量模型），不要跳过 tests。
