# V3PRO＋ 验收矩阵 (Acceptance Matrix)

> **本文档是 V3PRO\_UPGRADE\_PLAN\_Version2.md 的可读验收总表**
> **所有场景必须通过，否则系统不可上线**

---

## 验收总览

| Phase | 名称 | 场景数 | 必须通过 | 状态 |
|-------|------|--------|---------|------|
| A | 接口冻结 + Replay-first | 8 | ✅ 全部 | 🔄 开发中 |
| B | 执行可靠性 | 15 | ✅ 全部 | 🔄 开发中 |
| C | 市场侧连续性 | 8 | ✅ 全部 | ⏳ 待开始 |
| D | 套利工程门槛 | 6 | ✅ 全部 | ⏳ 待开始 |
| E | Guardian 无人值守 | 8 | ✅ 全部 | ⏳ 待开始 |
| F | 审计与回放 | 6 | ✅ 全部 | ⏳ 待开始 |

---

## Phase A: 接口冻结 + Replay-first

### A.1 Instrument Cache

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `INST.CACHE.LOAD` | Instrument Cache 加载 | 能从 JSON 加载 InstrumentInfo，包含必填字段 | `test_instrument_cache*` |
| `INST.CACHE.PERSIST` | Instrument Cache 落盘 | 先写 tmp 再 rename，路径符合约定 | `test_instrument_*persist*` |

### A.2 Universe Selector

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `UNIV.DOMINANT.BASIC` | 主力选择 | 基于 OI + Volume 评分，返回 dominant_by_product | `test_universe_selector*dominant*` |
| `UNIV.SUBDOMINANT.PAIRING` | 次主力选择 | 返回 subdominant_by_product，次主力 ≠ 主力 | `test_universe_selector*subdominant*` |
| `UNIV.ROLL.COOLDOWN` | 切换冷却 | 切换后冷却期内不再切换，需超过 MIN_SWITCH_EDGE | `test_universe_*cooldown*` |
| `UNIV.EXPIRY.GATE` | 临期排除 | days_to_expiry < EXPIRY_BLOCK_DAYS 不成为主力 | `test_universe_*expiry*` |

---

## Phase B: 执行可靠性

### B.1 订单标识映射

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `EXEC.ID.MAPPING` | 标识映射完整 | local_id 唯一，order_ref 来自 ack，order_sys_id 来自 OnRtnOrder | `test_order_context*` |

### B.2 FSM 状态机

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `FSM.STRICT.TRANSITIONS` | 严格模式覆盖 | 所有 TRANSITIONS 被测试，非法转移 raise | `test_fsm*strict*` |
| `FSM.TOLERANT.IDEMPOTENT` | 容错模式幂等 | 重复事件 ignore，终态后事件 ignore | `test_fsm*tolerant*` |
| `FSM.CANCEL_WHILE_FILL` | 撤单途中成交 | CANCEL_SUBMITTING/PENDING + RTN_FILLED → FILLED | `test_fsm*cancel*fill*` |
| `FSM.STATUS_4_MAPPING` | OrderStatus='4' 映射 | 无成交→ERROR+reduce-only，有成交→PARTIAL_CANCELLED | `test_fsm*status_4*` |

### B.3 AutoOrderEngine

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `EXEC.ENGINE.PIPELINE` | 订单管线 | throttle→fat_finger→liquidity→broker.place_order | `test_auto_order*pipeline*` |
| `EXEC.TIMEOUT.ACK` | Ack 超时 | 超时后撤单，不可控则 ERROR + 降级 | `test_*timeout*ack*` |
| `EXEC.TIMEOUT.FILL` | Fill 超时 | 超时后撤单 + 追价，受 max_retry 限制 | `test_*timeout*fill*` |
| `EXEC.CANCEL_REPRICE.TIMEOUT` | 追价超时撤单 | 超时执行撤单，使用 REPRICE_MODE 配置 | `test_*reprice*timeout*` |
| `EXEC.PARTIAL.REPRICE` | 部分成交追价 | remaining_qty > 0 等待 fill_timeout 后追价 | `test_*partial*reprice*` |
| `EXEC.MAX_RETRY.LIMIT` | 最大重试 | max_retry 达到后 ERROR + 降级 | `test_*max_retry*` |

### B.4 Protection

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `PROT.LIQUIDITY.GATE` | 流动性门槛 | spread 超阈值 / volume 不足 → 拒单 | `test_*liquidity*gate*` |
| `PROT.FATFINGER.LIMIT` | 胖手指保护 | 手数/名义/价格偏离 → 拒单 | `test_*fatfinger*` |
| `PROT.THROTTLE.RATE` | 频率限制 | 超过 MAX_ORDERS_PER_MIN → 拒单 | `test_*throttle*` |

---

## Phase C: 市场侧连续性

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `MKT.BARS.CONTINUOUS` | 连续主力 bars | roll 时 bars 正确拼接 | `test_*continuous_bars*` |
| `MKT.ROLL.AUDIT` | Roll 审计 | 切换点写入 audit 事件 | `test_*roll*audit*` |
| `MKT.QUOTE.STALE` | 行情过期 | 软/硬 stale 正确检测 | `test_*quote*stale*` |
| `MKT.QUALITY.OUTLIER` | 异常价格 | 多倍 tick_size 跳变标记异常 | `test_*outlier*` |

---

## Phase D: 套利工程门槛

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `PAIR.EXECUTOR.ATOMIC` | 双腿原子性 | 两腿同时提交或回滚 | `test_pair_executor*` |
| `PAIR.ROLLBACK.HEDGE` | 回滚对冲 | 单腿成交后另腿失败 → 自动对冲 | `test_*rollback*hedge*` |
| `PAIR.LEG_IMBALANCE` | 单腿敞口检测 | 敞口超阈值 → 降级 | `test_*leg_imbalance*` |
| `PAIR.STOP_Z.BREAKER` | 止损熔断 | zscore 超 stop_z → 平仓 | `test_*stop_z*` |

---

## Phase E: Guardian 无人值守

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `GUARD.STATE.MACHINE` | 状态机转移 | INIT→RUNNING↔REDUCE_ONLY→HALTED→MANUAL | `test_guardian*state*` |
| `GUARD.QUOTE_STALE` | 行情断流检测 | 硬 stale 触发 REDUCE_ONLY | `test_*quote_stale*` |
| `GUARD.ORDER_STUCK` | 卡单检测 | FSM 长时间不推进 → cancel_all | `test_*order_stuck*` |
| `GUARD.POSITION_DRIFT` | 持仓漂移 | reconcile 不一致 → HALTED | `test_*position_drift*` |
| `GUARD.COLD_START` | 冷启动恢复 | cancel_all → query → REDUCE_ONLY → 冷却 → RUNNING | `test_*cold_start*` |

---

## Phase F: 审计与回放

| Rule ID | 场景 | 验收标准 | 对应测试 |
|---------|------|---------|---------|
| `AUDIT.EVENT.COMPLETE` | 事件完整性 | 包含 run_id, exec_id, event_id, ts, component | `test_audit*complete*` |
| `AUDIT.JSONL.FORMAT` | JSONL 格式 | 每行可独立解析 | `test_*jsonl*` |
| `REPLAY.DETERMINISTIC` | 回放确定性 | 同 inputs 产生相同 DecisionEvent 序列 | `test_*replay*deterministic*` |
| `REPLAY.FSM.CONSISTENT` | FSM 一致性 | 回放与 live 相同状态转移 | `test_*replay*fsm*` |

---

## 验收流程

### 1. 运行验收测试

```powershell
# 完整验收（CI + Replay + Sim）
.\scripts\claude_loop.ps1 -Mode full -Strict

# 或分步验收
.\scripts\make.ps1 ci-json
.\scripts\make.ps1 replay-json
```

### 2. 检查报告

```powershell
# 查看 CI 报告
Get-Content artifacts\check\report.json | ConvertFrom-Json

# 查看 Sim 报告
Get-Content artifacts\sim\report.json | ConvertFrom-Json
```

### 3. 验证 Policy

```powershell
# 运行策略验证
.\scripts\validate_policy.ps1 -Check all -Strict
```

---

## Rule ID 命名规范

```text
{DOMAIN}.{CATEGORY}.{NAME}

DOMAIN:
- INST: Instrument 合约
- UNIV: Universe 主力选择
- EXEC: Execution 执行
- FSM: 状态机
- PROT: Protection 保护
- MKT: Market 行情
- PAIR: Pair 套利
- GUARD: Guardian 守护
- AUDIT: 审计
- REPLAY: 回放

示例:
- UNIV.DOMINANT.BASIC = Universe.主力选择.基础场景
- FSM.CANCEL_WHILE_FILL = FSM.撤单途中成交
- GUARD.QUOTE_STALE = Guardian.行情断流
```

---

## 失败处理对照表

| Rule ID 前缀 | 失败时应修改的模块 |
|-------------|-------------------|
| `INST.*` | `src/market/instrument_cache.py` |
| `UNIV.*` | `src/market/universe_selector.py` |
| `EXEC.*` | `src/execution/auto_order_engine.py` |
| `FSM.*` | `src/execution/fsm.py` |
| `PROT.*` | `src/execution/protection.py` |
| `MKT.*` | `src/market/` |
| `PAIR.*` | `src/execution/pair_executor.py` |
| `GUARD.*` | `src/guardian/` |
| `AUDIT.*` | `src/audit/` |
| `REPLAY.*` | `src/replay/` |

---

## 版本历史

| 版本 | 日期 | 变更 |
|-----|------|------|
| 1.0 | 2025-01-15 | 初始版本，基于 V2_SPEC 生成 |
