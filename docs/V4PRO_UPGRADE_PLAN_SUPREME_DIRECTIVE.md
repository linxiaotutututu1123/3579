# V4PRO 中国期货交易系统升级计划

> **文档版本**: v4.0 SUPREME DIRECTIVE
> **生成日期**: 2025-12-16
> **适用市场**: 中华人民共和国期货市场
> **语言要求**: 全程中文（代码注释、文档、日志）

---

## 目录

- [§1 执行原则与军规 M1-M20](#1-执行原则与军规-m1-m20)
- [§2 当前状态与锚点](#2-当前状态与锚点)
- [§3 升级架构总览](#3-升级架构总览)
- [§4 Phase依赖关系图](#4-phase依赖关系图)
- [§5 Phase 0: 基础设施](#5-phase-0-基础设施)
- [§6 Phase 1: 行情层](#6-phase-1-行情层)
- [§7 Phase 2: 审计层](#7-phase-2-审计层)
- [§8 Phase 3: 策略降级与套利](#8-phase-3-策略降级与套利)
- [§9 Phase 4: 回放验证](#9-phase-4-回放验证)
- [§10 Phase 5: 成本层](#10-phase-5-成本层)
- [§11 Phase 6: B类模型](#11-phase-6-b类模型)
- [§12 Phase 7: 中国期货市场特化](#12-phase-7-中国期货市场特化)
- [§13 Phase 8: 智能策略升级](#13-phase-8-智能策略升级)
- [§14 Phase 9: 合规与监控](#14-phase-9-合规与监控)
- [§15 Phase 10: 组合与风控增强](#15-phase-10-组合与风控增强)
- [§16 六大交易所配置](#16-六大交易所配置)
- [§17 交易时段与夜盘规则](#17-交易时段与夜盘规则)
- [§18 涨跌停板规则](#18-涨跌停板规则)
- [§19 保证金制度](#19-保证金制度)
- [§20 手续费结构](#20-手续费结构)
- [§21 程序化交易合规](#21-程序化交易合规)
- [§22 VaR风控增强](#22-var风控增强)
- [§23 压力测试场景](#23-压力测试场景)
- [§24 实验性策略门禁](#24-实验性策略门禁)
- [§25 审计日志规范](#25-审计日志规范)
- [§26 配置管理](#26-配置管理)
- [§27 FMEA故障模式分析](#27-fmea故障模式分析)
- [§28 回滚策略](#28-回滚策略)
- [§29 测试规范](#29-测试规范)
- [§30 CI/CD集成](#30-cicd集成)
- [§31 场景矩阵总表](#31-场景矩阵总表)
- [§32 文件清单](#32-文件清单)
- [§33 工时估算](#33-工时估算)
- [§34 验收标准](#34-验收标准)
- [§35 附录](#35-附录)

---

## §1 执行原则与军规 M1-M20

### 1.1 最高军令

```
┌─────────────────────────────────────────────────────────────────────────┐
│  务必切记本最高军令：                                                    │
│  1. 专注于中国期货市场                                                   │
│  2. 全程使用中文（代码注释、文档、日志、错误信息）                        │
│  3. 严格遵守军规 M1-M20，无一例外                                        │
│  4. 保证风险控制的前提下最大化收益                                        │
│  5. 所有模块必须通过门禁检查方可合并                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 军规总表 M1-M20

| 编号 | 军规名称 | 原则描述 | 违规后果 | 检查方式 |
|------|----------|----------|----------|----------|
| **M1** | 单一信号源 | 一个交易信号只能来自一个策略实例 | 订单冲突、重复下单 | 代码审查 + 单测 |
| **M2** | 幂等执行 | 相同信号重复执行结果一致 | 重复下单、资金损失 | 回放测试 |
| **M3** | 完整审计 | 所有决策必须有审计日志 | 无法追溯、监管风险 | 日志检查 |
| **M4** | 降级兜底 | 策略异常必须有降级路径 | 系统瘫痪、无法交易 | 异常注入测试 |
| **M5** | 成本先行 | 信号边际收益必须大于成本 | 亏损交易、无效下单 | 成本门禁 |
| **M6** | 熔断保护 | 触发风控阈值必须立即停止 | 巨额亏损、穿仓 | 风控测试 |
| **M7** | 回放一致 | 相同输入必须产生相同输出 | 无法验证、策略失效 | 回放测试 |
| **M8** | 配置隔离 | 不同环境配置严格隔离 | 误操作、资金损失 | 配置审查 |
| **M9** | 错误上报 | 所有异常必须上报监控系统 | 故障隐藏、延误处理 | 告警测试 |
| **M10** | 资源限制 | CPU/内存/网络必须有上限 | 系统崩溃、影响其他服务 | 压测 |
| **M11** | 版本兼容 | 新版本必须兼容旧数据格式 | 数据丢失、回滚困难 | 兼容性测试 |
| **M12** | 双重确认 | 大额订单需人工或二次确认 | 误操作、巨额损失 | 流程审查 |
| **M13** | 涨跌停感知 | 订单价格必须检查涨跌停板 | 废单、无效挂单 | 行情检查 |
| **M14** | 平今平昨分离 | 平仓时必须区分平今/平昨 | 手续费计算错误 | 持仓检查 |
| **M15** | 夜盘跨日处理 | 夜盘交易日归属必须正确 | 结算错误、持仓混乱 | 日历检查 |
| **M16** | 保证金实时监控 | 保证金使用率必须实时计算 | 强平风险、穿仓 | 风控检查 |
| **M17** | 程序化合规 | 报撤单频率必须在监管阈值内 | 监管处罚、限制交易 | 合规检查 |
| **M18** | 实验性门禁 | 未成熟策略禁止实盘启用 | 策略失效、资金损失 | 成熟度检查 |
| **M19** | 风险归因 | 每笔亏损必须有归因分析 | 无法改进、重复犯错 | 归因报告 |
| **M20** | 跨所一致 | 不同交易所逻辑必须一致 | 套利失败、对冲失效 | 跨所测试 |

### 1.3 军规违规处理

```
违规等级定义：
┌────────┬────────────────┬─────────────────────────────────┐
│ 等级   │ 定义           │ 处理措施                        │
├────────┼────────────────┼─────────────────────────────────┤
│ FATAL  │ 资金损失风险   │ 立即停止交易 + 人工介入         │
│ SEVERE │ 合规违规风险   │ 暂停相关策略 + 告警通知         │
│ MAJOR  │ 功能异常       │ 记录日志 + 降级处理             │
│ MINOR  │ 性能问题       │ 记录日志 + 后续优化             │
└────────┴────────────────┴─────────────────────────────────┘
```

### 1.4 军规检查清单

每次代码提交前必须完成以下检查：

- [ ] M1: 信号来源唯一性验证
- [ ] M3: 审计日志完整性验证
- [ ] M5: 成本门禁通过
- [ ] M6: 风控阈值配置正确
- [ ] M13: 涨跌停检查逻辑存在
- [ ] M14: 平今平昨分离逻辑正确
- [ ] M17: 报撤单频率检查存在
- [ ] M18: 实验性策略门禁检查

---

## §2 当前状态与锚点

### 2.1 Phase完成状态

| Phase | 名称 | 文件数 | 场景数 | 状态 | 完成日期 |
|-------|------|--------|--------|------|----------|
| Phase 0 | 基础设施 | 8 | 15 | ✅ 完成 | 2025-12-14 |
| Phase 1 | 行情层 | 7 | 12 | ✅ 完成 | 2025-12-14 |
| Phase 2 | 审计层 | 7 | 18 | ✅ 完成 | 2025-12-15 |
| Phase 3 | 策略降级 | 4 | 12 | ✅ 完成 | 2025-12-15 |
| Phase 4 | 回放验证 | 2 | 2 | ✅ 完成 | 2025-12-15 |
| Phase 5 | 成本层 | 2 | 8 | ⏸ 待执行 | - |
| Phase 6 | B类模型 | 6 | 22 | ⏸ 待执行 | - |
| Phase 7 | 中国期货特化 | 10 | 35 | ⏸ 待执行 | - |
| Phase 8 | 智能策略 | 12 | 26 | ⏸ 待执行 | - |
| Phase 9 | 合规监控 | 6 | 16 | ⏸ 待执行 | - |
| Phase 10 | 组合风控 | 7 | 25 | ⏸ 待执行 | - |

### 2.2 代码库锚点

```
当前代码库状态 (2025-12-16):
├── src/
│   ├── market/           # 7 files ✅
│   ├── audit/            # 7 files ✅
│   ├── cost/             # 2 files ✅
│   ├── guardian/         # 6 files ✅
│   ├── execution/
│   │   ├── auto/         # 8 files ✅
│   │   ├── protection/   # 4 files ✅
│   │   └── pair/         # 3 files ✅
│   ├── strategy/
│   │   ├── calendar_arb/ # 4 files ✅
│   │   └── experimental/ # 4 files ✅ (成熟度评估系统)
│   ├── replay/           # 2 files ✅
│   ├── portfolio/        # 4 files ✅ (P2升级)
│   ├── monitoring/       # 3 files ✅ (P2升级)
│   ├── risk/             # 3 files ✅
│   └── trading/          # CI/SIM gates
├── tests/                # 765 tests ✅
├── docs/                 # 9 documents
└── scripts/              # 6 scripts
```

### 2.3 门禁状态锚点

| 门禁 | 状态 | 最后检查时间 |
|------|------|--------------|
| Ruff Check | ✅ PASS | 2025-12-16 |
| Ruff Format | ✅ PASS | 2025-12-16 |
| Mypy | ✅ PASS | 2025-12-16 |
| Pytest | ✅ PASS (765 tests) | 2025-12-16 |
| Coverage | 88.22% | 2025-12-16 |
| Policy | ✅ PASS | 2025-12-16 |

### 2.4 已实现模块摘要

| 模块 | 核心功能 | 军规覆盖 |
|------|----------|----------|
| `src/portfolio/` | 多策略持仓管理、风险分析、夏普比率 | M1, M3, M19 |
| `src/monitoring/` | 健康检查、Prometheus指标、告警 | M9, M10 |
| `src/risk/var_calculator.py` | 历史/参数/蒙特卡洛VaR | M6, M16 |
| `src/strategy/experimental/` | 成熟度评估、训练门禁、进度监控 | M18 |
| `src/strategy/calendar_arb/` | Kalman滤波、套利策略、降级链 | M4, M5, M7 |
| `src/replay/` | 决策回放、哈希验证 | M7 |

---

## §3 升级架构总览

### 3.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        V4PRO 军规级交易系统架构                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   行情层    │───▶│   策略层    │───▶│   执行层    │                 │
│  │  (Market)   │    │ (Strategy)  │    │ (Execution) │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────────────────────────────────────────────┐               │
│  │                    审计层 (Audit)                    │               │
│  │        JSONL格式 · 完整追溯 · 监管合规              │               │
│  └─────────────────────────────────────────────────────┘               │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   风控层    │    │   成本层    │    │   回放层    │                 │
│  │   (Risk)    │    │   (Cost)    │    │  (Replay)   │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────────────────────────────────────────────┐               │
│  │                  守护层 (Guardian)                   │               │
│  │    熔断保护 · 涨跌停检查 · 保证金监控 · 合规节流    │               │
│  └─────────────────────────────────────────────────────┘               │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │  组合管理   │    │  监控告警   │    │  实验门禁   │                 │
│  │ (Portfolio) │    │ (Monitor)   │    │(Experimental)│                 │
│  └─────────────┘    └─────────────┘    └─────────────┘                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流向

```
行情数据 ──▶ 合约缓存 ──▶ 策略引擎 ──▶ 信号生成 ──▶ 成本门禁 ──▶ 风控检查
                                                                    │
                                                                    ▼
CTP接口 ◀── 订单执行 ◀── 订单验证 ◀── 涨跌停检查 ◀── 保证金检查 ◀── 合规检查
                                                                    │
                                                                    ▼
                                                              审计日志记录
```

### 3.3 双轨架构

| 轨道 | 描述 | 适用场景 |
|------|------|----------|
| **A轨 (生产)** | 成熟策略，全自动执行 | 日常交易 |
| **B轨 (实验)** | 实验策略，门禁控制 | 策略研发 |

---

## §4 Phase依赖关系图

```
                           ┌─────────────┐
                           │  Phase 0    │
                           │  基础设施   │
                           └──────┬──────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
       │  Phase 1    │     │  Phase 2    │     │  Phase 5    │
       │   行情层    │     │   审计层    │     │   成本层    │
       └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
              │                   │                   │
              ▼                   ▼                   ▼
       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
       │  Phase 3    │     │  Phase 4    │     │  Phase 6    │
       │ 策略降级    │     │  回放验证   │     │  B类模型    │
       └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
              │                   │                   │
              └───────────────────┼───────────────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │  Phase 7    │
                           │中国期货特化 │
                           └──────┬──────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
       ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
       │  Phase 8    │     │  Phase 9    │     │  Phase 10   │
       │ 智能策略    │     │ 合规监控    │     │ 组合风控    │
       └─────────────┘     └─────────────┘     └─────────────┘
```

---

## §5 Phase 0: 基础设施

### 5.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/trading/ci_gate.py` | ~150 | CI门禁检查 | ✅ |
| `src/trading/sim_gate.py` | ~160 | 仿真门禁检查 | ✅ |
| `src/brokers/ctp/api.py` | ~200 | CTP接口封装 | ✅ |
| `src/brokers/ctp/config.py` | ~100 | CTP配置管理 | ✅ |
| `src/app/config.py` | ~150 | 应用配置 | ✅ |
| `src/app/logger.py` | ~100 | 日志配置 | ✅ |
| `scripts/validate_policy.py` | ~200 | 策略验证脚本 | ✅ |
| `scripts/sim_gate.py` | ~160 | 仿真门禁脚本 | ✅ |

### 5.2 场景覆盖

| Rule ID | 场景描述 | 测试文件 |
|---------|----------|----------|
| `INFRA.CI.GATE_PASS` | CI门禁全部通过 | test_ci_gate.py |
| `INFRA.CI.LINT_PASS` | Ruff检查通过 | test_ci_gate.py |
| `INFRA.CI.TYPE_PASS` | Mypy检查通过 | test_ci_gate.py |
| `INFRA.CI.TEST_PASS` | Pytest通过 | test_ci_gate.py |
| `INFRA.CI.COVERAGE_MIN` | 覆盖率≥80% | test_ci_gate.py |
| `INFRA.SIM.GATE_PASS` | 仿真门禁通过 | test_sim_gate.py |
| `INFRA.SIM.SCENARIO_ALL` | 所有场景覆盖 | test_sim_gate.py |
| `INFRA.CTP.CONNECT` | CTP连接成功 | test_ctp_api.py |
| `INFRA.CTP.AUTH` | CTP认证成功 | test_ctp_api.py |
| `INFRA.CTP.SUBSCRIBE` | 行情订阅成功 | test_ctp_api.py |
| `INFRA.CONFIG.LOAD` | 配置加载成功 | test_config.py |
| `INFRA.CONFIG.VALIDATE` | 配置验证通过 | test_config.py |
| `INFRA.CONFIG.ENV_ISOLATE` | 环境隔离正确 | test_config.py |
| `INFRA.LOG.FORMAT` | 日志格式正确 | test_logger.py |
| `INFRA.LOG.LEVEL` | 日志级别正确 | test_logger.py |

---

## §6 Phase 1: 行情层

### 6.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/market/subscriber.py` | ~250 | 行情订阅管理 | ✅ |
| `src/market/instrument_cache.py` | ~184 | 合约元数据缓存 | ✅ |
| `src/market/tick_buffer.py` | ~200 | Tick数据缓冲 | ✅ |
| `src/market/kline_builder.py` | ~180 | K线构建器 | ✅ |
| `src/market/snapshot.py` | ~150 | 行情快照 | ✅ |
| `src/market/exchange_config.py` | ~300 | 交易所配置 | ⏸ 待新增 |
| `src/market/trading_calendar.py` | ~250 | 夜盘交易日历 | ⏸ 待新增 |

### 6.2 InstrumentInfo 扩展字段

```python
@dataclass
class InstrumentInfo:
    """合约元数据 (中国期货市场扩展版)"""

    # 基础字段 (已有)
    symbol: str                    # 合约代码 如 "rb2501"
    product: str                   # 品种代码 如 "rb"
    exchange: str                  # 交易所代码 如 "SHFE"
    expire_date: str               # 到期日 如 "20250115"
    tick_size: float               # 最小变动价位
    multiplier: int                # 合约乘数
    max_order_volume: int          # 单笔最大下单量
    position_limit: int            # 持仓限额

    # 中国期货市场扩展字段 (待新增)
    price_limit_up: float          # 涨停价
    price_limit_down: float        # 跌停价
    price_limit_pct: float         # 涨跌停幅度 (%)
    margin_ratio_long: float       # 多头保证金率
    margin_ratio_short: float      # 空头保证金率
    fee_open_ratio: float          # 开仓手续费率 (按金额)
    fee_close_ratio: float         # 平仓手续费率 (按金额)
    fee_open_fixed: float          # 开仓手续费 (按手)
    fee_close_fixed: float         # 平仓手续费 (按手)
    fee_close_today_ratio: float   # 平今手续费率
    fee_type: str                  # 手续费类型: "ratio" | "fixed" | "mixed"
    trading_sessions: list[tuple]  # 交易时段列表
    has_night_session: bool        # 是否有夜盘
    is_main_contract: bool         # 是否主力合约
    delivery_month: int            # 交割月份
    last_trading_day: str          # 最后交易日
```

### 6.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `MKT.SUBSCRIBER.DIFF_UPDATE` | 差量更新订阅列表 | M1 |
| `MKT.SUBSCRIBER.CALLBACK` | 回调正确触发 | M9 |
| `MKT.CACHE.INSTRUMENT_INFO` | 合约信息正确缓存 | M11 |
| `MKT.CACHE.EXPIRE_CHECK` | 过期检查正确 | M15 |
| `MKT.TICK.BUFFER_OVERFLOW` | 缓冲区溢出处理 | M10 |
| `MKT.TICK.TIMESTAMP_ORDER` | 时间戳顺序正确 | M7 |
| `MKT.KLINE.BUILD_CORRECT` | K线构建正确 | M7 |
| `MKT.KLINE.GAP_HANDLE` | 缺口处理正确 | M4 |
| `MKT.LIMIT.PRICE_CHECK` | 涨跌停价格检查 | M13 |
| `MKT.LIMIT.UPDATE_REALTIME` | 涨跌停实时更新 | M13 |
| `MKT.SESSION.NIGHT_CALENDAR` | 夜盘日历正确 | M15 |
| `MKT.SESSION.DAY_BOUNDARY` | 交易日边界正确 | M15 |

---

## §7 Phase 2: 审计层

### 7.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/audit/writer.py` | ~200 | 审计日志写入器 | ✅ |
| `src/audit/reader.py` | ~150 | 审计日志读取器 | ✅ |
| `src/audit/event.py` | ~180 | 审计事件定义 | ✅ |
| `src/audit/validator.py` | ~120 | 审计验证器 | ✅ |
| `src/audit/correlation.py` | ~100 | 关联ID管理 | ✅ |
| `src/audit/exporter.py` | ~150 | 审计导出器 | ✅ |
| `src/audit/compressor.py` | ~100 | 审计压缩器 | ✅ |

### 7.2 审计事件Schema

```python
@dataclass
class AuditEvent:
    """审计事件 (军规级 v4.0)"""

    # 必填字段
    ts: str                        # ISO8601时间戳
    event_type: str                # 事件类型
    run_id: str                    # 运行ID
    exec_id: str                   # 执行ID

    # 可选字段
    symbol: str | None = None      # 合约代码
    direction: str | None = None   # 方向: "LONG" | "SHORT"
    price: float | None = None     # 价格
    volume: int | None = None      # 数量
    strategy: str | None = None    # 策略名称
    signal_source: str | None = None  # 信号来源 (M1)
    cost_breakdown: dict | None = None  # 成本明细 (M5)
    risk_check: dict | None = None  # 风控检查结果 (M6)
    error: str | None = None       # 错误信息
    metadata: dict | None = None   # 扩展元数据
```

### 7.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `AUDIT.EVENT.STRUCTURE` | 事件结构完整 | M3 |
| `AUDIT.EVENT.JSONL_FORMAT` | JSONL格式正确 | M3 |
| `AUDIT.CORRELATION.RUN_EXEC` | run_id/exec_id关联 | M3 |
| `AUDIT.WRITER.PROPERTIES` | 写入器属性正确 | M3 |
| `AUDIT.WRITER.CLOSE_BEHAVIOR` | 关闭后行为正确 | M3 |
| `AUDIT.VALIDATE.MISSING_TS` | 缺少时间戳检测 | M3 |
| `AUDIT.VALIDATE.MISSING_TYPE` | 缺少类型检测 | M3 |
| `AUDIT.DICT.WRITE` | 字典写入正确 | M3 |
| `AUDIT.DICT.MISSING_REQUIRED` | 缺少必填字段检测 | M3 |
| `AUDIT.READ.EMPTY_FILE` | 读取空文件处理 | M4 |
| `AUDIT.CONTEXT.MANAGER` | 上下文管理器正确 | M3 |
| `AUDIT.EXEC_ID.DEFAULT` | exec_id默认值正确 | M3 |
| `AUDIT.COMPRESS.GZIP` | GZIP压缩正确 | M10 |
| `AUDIT.EXPORT.CSV` | CSV导出正确 | M3 |
| `AUDIT.EXPORT.PARQUET` | Parquet导出正确 | M3 |
| `AUDIT.RETENTION.POLICY` | 保留策略正确 | M3 |
| `AUDIT.SIGNAL_SOURCE.TRACK` | 信号来源追踪 | M1, M3 |
| `AUDIT.COST.BREAKDOWN` | 成本明细记录 | M5, M3 |

---

## §8 Phase 3: 策略降级与套利

### 8.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/strategy/fallback.py` | ~350 | 降级管理器 | ✅ |
| `src/strategy/calendar_arb/kalman_beta.py` | ~200 | Kalman滤波估计 | ✅ |
| `src/strategy/calendar_arb/strategy.py` | ~400 | 套利策略 | ✅ |
| `src/strategy/calendar_arb/__init__.py` | ~30 | 模块导出 | ✅ |

### 8.2 降级链配置

```python
DEFAULT_FALLBACK_CHAINS = {
    "calendar_arb": [
        "calendar_arb",      # 主策略: 日历套利
        "simple_ma",         # 降级1: 简单均线
        "stop_loss_only",    # 降级2: 仅止损
        "flat_all",          # 降级3: 全平
    ],
    "trend_follow": [
        "trend_follow",      # 主策略: 趋势跟踪
        "momentum",          # 降级1: 动量
        "stop_loss_only",    # 降级2: 仅止损
        "flat_all",          # 降级3: 全平
    ],
}
```

### 8.3 Kalman滤波参数

```python
@dataclass
class KalmanConfig:
    """Kalman滤波器配置"""

    process_noise: float = 1e-5      # 过程噪声 Q
    observation_noise: float = 1e-3  # 观测噪声 R
    initial_beta: float = 1.0        # 初始beta
    initial_variance: float = 1.0    # 初始方差
    beta_min: float = 0.5            # beta下界
    beta_max: float = 2.0            # beta上界
```

### 8.4 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `STRAT.FALLBACK.ON_EXCEPTION` | 异常触发降级 | M4 |
| `STRAT.FALLBACK.ON_TIMEOUT` | 超时触发降级 | M4 |
| `STRAT.FALLBACK.CHAIN_DEFINED` | 降级链已定义 | M4 |
| `ARB.KALMAN.BETA_ESTIMATE` | beta估计正确 | M7 |
| `ARB.KALMAN.RESIDUAL_ZSCORE` | 残差z分数计算 | M7 |
| `ARB.KALMAN.BETA_BOUND` | beta边界约束 | M6 |
| `ARB.LEGS.FIXED_NEAR_FAR` | 近远月腿固定 | M1 |
| `ARB.SIGNAL.HALF_LIFE_GATE` | 半衰期门禁 | M5 |
| `ARB.SIGNAL.STOP_Z_BREAKER` | 止损z值触发 | M6 |
| `ARB.SIGNAL.EXPIRY_GATE` | 到期日门禁 | M15 |
| `ARB.SIGNAL.CORRELATION_BREAK` | 相关性破裂检测 | M6 |
| `ARB.COST.ENTRY_GATE` | 成本门禁检查 | M5 |

---

## §9 Phase 4: 回放验证

### 9.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/replay/verifier.py` | ~280 | 回放验证器 | ✅ |
| `src/replay/__init__.py` | ~30 | 模块导出 | ✅ |

### 9.2 回放验证逻辑

```python
class ReplayVerifier:
    """回放验证器 (军规 M7)"""

    def verify_decision_sequence(
        self,
        original: list[Decision],
        replayed: list[Decision],
    ) -> VerifyResult:
        """验证决策序列一致性"""
        # SHA256哈希比较
        original_hash = self._compute_hash(original)
        replayed_hash = self._compute_hash(replayed)
        return VerifyResult(
            passed=original_hash == replayed_hash,
            original_hash=original_hash,
            replayed_hash=replayed_hash,
        )

    def verify_guardian_sequence(
        self,
        original: list[GuardianAction],
        replayed: list[GuardianAction],
    ) -> VerifyResult:
        """验证守护动作序列一致性"""
        # ...
```

### 9.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `REPLAY.DETERMINISTIC.DECISION` | 决策序列确定性 | M7 |
| `REPLAY.DETERMINISTIC.GUARDIAN` | 守护动作确定性 | M7 |

---

## §10 Phase 5: 成本层

### 10.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/cost/estimator.py` | ~328 | 成本估计器 | ✅ |
| `src/cost/china_fee_calculator.py` | ~300 | 中国期货手续费 | ⏸ 待新增 |

### 10.2 成本模型

```python
@dataclass
class CostBreakdown:
    """成本分解"""

    fee: float           # 手续费
    slippage: float      # 滑点
    impact: float        # 市场冲击
    total: float         # 总成本

    # 中国期货市场扩展
    fee_open: float = 0.0         # 开仓手续费
    fee_close: float = 0.0        # 平仓手续费
    fee_close_today: float = 0.0  # 平今手续费
    stamp_duty: float = 0.0       # 印花税 (仅股指)
```

### 10.3 中国期货手续费结构

| 交易所 | 品种示例 | 手续费类型 | 开仓 | 平仓 | 平今 |
|--------|----------|------------|------|------|------|
| SHFE | 铜 cu | 按金额 | 0.5‱ | 0.5‱ | 0 |
| SHFE | 螺纹钢 rb | 按手 | 1元/手 | 1元/手 | 1元/手 |
| DCE | 铁矿石 i | 按金额 | 1‱ | 1‱ | 1‱ |
| CZCE | 甲醇 MA | 按手 | 2元/手 | 2元/手 | 6元/手 |
| CFFEX | IF | 按金额 | 0.23‱ | 0.23‱ | 3.45‱ |
| GFEX | 碳酸锂 LC | 按金额 | 0.5‱ | 0.5‱ | 3‱ |
| INE | 原油 SC | 按手 | 20元/手 | 20元/手 | 0 |

### 10.4 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `COST.FEE.ESTIMATE` | 手续费估计正确 | M5 |
| `COST.SLIPPAGE.ESTIMATE` | 滑点估计正确 | M5 |
| `COST.IMPACT.ESTIMATE` | 市场冲击估计正确 | M5 |
| `COST.EDGE.GATE` | 边际收益门禁 | M5 |
| `COST.FEE.BY_VOLUME` | 按手收费计算 | M5 |
| `COST.FEE.BY_VALUE` | 按金额收费计算 | M5 |
| `COST.FEE.CLOSE_TODAY` | 平今手续费计算 | M14 |
| `COST.FEE.EXCHANGE_CONFIG` | 交易所配置正确 | M20 |

---

## §11 Phase 6: B类模型

### 11.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/strategy/dl/lstm_predictor.py` | ~400 | LSTM预测模型 | ⏸ 待新增 |
| `src/strategy/dl/transformer_model.py` | ~500 | Transformer模型 | ⏸ 待新增 |
| `src/strategy/dl/factor_miner.py` | ~350 | 因子挖掘器 | ⏸ 待新增 |
| `src/strategy/rl/ppo_agent.py` | ~450 | PPO强化学习 | ⏸ 待新增 |
| `src/strategy/rl/dqn_agent.py` | ~400 | DQN强化学习 | ⏸ 待新增 |
| `src/strategy/rl/reward_function.py` | ~200 | 奖励函数设计 | ⏸ 待新增 |

### 11.2 B类模型成熟度要求

| 维度 | 权重 | 及格线 | 良好线 | 优秀线 |
|------|------|--------|--------|--------|
| 收益稳定性 | 25% | 夏普≥1.0 | 夏普≥1.5 | 夏普≥2.0 |
| 风险控制 | 25% | 回撤≤20% | 回撤≤15% | 回撤≤10% |
| 市场适应性 | 20% | 覆盖3状态 | 覆盖5状态 | 覆盖7状态 |
| 训练充分度 | 20% | ≥90天 | ≥180天 | ≥365天 |
| 一致性 | 10% | 相关≥0.6 | 相关≥0.7 | 相关≥0.8 |

### 11.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `DL.LSTM.PREDICT` | LSTM预测输出 | M18 |
| `DL.LSTM.SEQUENCE_LENGTH` | 序列长度正确 | M7 |
| `DL.TRANSFORMER.ATTENTION` | 注意力计算正确 | M18 |
| `DL.TRANSFORMER.POSITION_ENCODING` | 位置编码正确 | M7 |
| `DL.FACTOR.MINE` | 因子挖掘正确 | M18 |
| `DL.FACTOR.IC_CALCULATE` | IC计算正确 | M19 |
| `RL.PPO.ACTION` | PPO动作选择 | M18 |
| `RL.PPO.REWARD` | PPO奖励计算 | M18 |
| `RL.DQN.QVALUE` | DQN Q值计算 | M18 |
| `RL.DQN.EPSILON_DECAY` | ε衰减正确 | M18 |
| `RL.REWARD.SHARPE_BASED` | 夏普奖励函数 | M18 |
| `RL.REWARD.RISK_ADJUSTED` | 风险调整奖励 | M18 |

---

## §12 Phase 7: 中国期货市场特化

### 12.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/market/exchange_config.py` | ~300 | 六大交易所配置 | ⏸ 待新增 |
| `src/market/trading_calendar.py` | ~250 | 夜盘交易日历 | ⏸ 待新增 |
| `src/cost/china_fee_calculator.py` | ~300 | 中国期货手续费 | ⏸ 待新增 |
| `src/execution/protection/limit_price.py` | ~200 | 涨跌停保护 | ⏸ 待新增 |
| `src/execution/protection/margin_monitor.py` | ~250 | 保证金监控 | ⏸ 待新增 |
| `src/guardian/triggers_china.py` | ~300 | 中国期货触发器 | ⏸ 待新增 |
| `src/risk/stress_test_china.py` | ~350 | 中国期货压力测试 | ⏸ 待新增 |
| `src/strategy/calendar_arb/delivery_aware.py` | ~250 | 交割感知套利 | ⏸ 待新增 |
| `src/compliance/china_futures_rules.py` | ~200 | 合规规则 | ⏸ 待新增 |
| `src/compliance/programmatic_trading.py` | ~300 | 程序化交易合规 | ⏸ 待新增 |

### 12.2 六大交易所配置

```python
class Exchange(Enum):
    """中国六大期货交易所"""

    SHFE = "上海期货交易所"
    DCE = "大连商品交易所"
    CZCE = "郑州商品交易所"
    CFFEX = "中国金融期货交易所"
    GFEX = "广州期货交易所"
    INE = "上海国际能源交易中心"


EXCHANGE_CONFIG = {
    Exchange.SHFE: {
        "trading_hours": [
            ("09:00", "10:15"),
            ("10:30", "11:30"),
            ("13:30", "15:00"),
        ],
        "night_session": ("21:00", "02:30"),  # 部分品种
        "settlement_time": "15:15",
        "products": ["cu", "al", "zn", "pb", "ni", "sn", "au", "ag", "rb", "hc", "ss", "bu", "ru", "sp", "nr", "ao"],
    },
    Exchange.DCE: {
        "trading_hours": [
            ("09:00", "10:15"),
            ("10:30", "11:30"),
            ("13:30", "15:00"),
        ],
        "night_session": ("21:00", "23:00"),
        "settlement_time": "15:15",
        "products": ["c", "cs", "a", "b", "m", "y", "p", "fb", "bb", "jd", "l", "v", "pp", "j", "jm", "i", "eg", "eb", "pg", "rr", "lh"],
    },
    # ... 其他交易所
}
```

### 12.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `CHINA.EXCHANGE.CONFIG_LOAD` | 交易所配置加载 | M20 |
| `CHINA.EXCHANGE.PRODUCT_MAP` | 品种映射正确 | M20 |
| `CHINA.CALENDAR.NIGHT_SESSION` | 夜盘时段正确 | M15 |
| `CHINA.CALENDAR.TRADING_DAY` | 交易日计算正确 | M15 |
| `CHINA.CALENDAR.HOLIDAY` | 节假日处理正确 | M15 |
| `CHINA.FEE.BY_VOLUME_CALC` | 按手收费计算 | M5 |
| `CHINA.FEE.BY_VALUE_CALC` | 按金额收费计算 | M5 |
| `CHINA.FEE.CLOSE_TODAY_CALC` | 平今手续费计算 | M14 |
| `CHINA.LIMIT.PRICE_CHECK` | 涨跌停价格检查 | M13 |
| `CHINA.LIMIT.ORDER_REJECT` | 超限订单拒绝 | M13 |
| `CHINA.MARGIN.RATIO_CHECK` | 保证金率检查 | M16 |
| `CHINA.MARGIN.USAGE_MONITOR` | 保证金使用监控 | M16 |
| `CHINA.MARGIN.WARNING_LEVEL` | 保证金预警等级 | M16 |
| `CHINA.TRIGGER.LIMIT_PRICE` | 涨跌停触发器 | M6, M13 |
| `CHINA.TRIGGER.MARGIN_CALL` | 保证金追缴触发 | M6, M16 |
| `CHINA.TRIGGER.DELIVERY` | 交割月接近触发 | M6, M15 |
| `CHINA.STRESS.2015_CRASH` | 2015股灾场景 | M6 |
| `CHINA.STRESS.2020_OIL` | 2020原油负价场景 | M6 |
| `CHINA.STRESS.2022_LITHIUM` | 2022碳酸锂场景 | M6 |
| `CHINA.ARB.DELIVERY_AWARE` | 交割感知套利 | M15 |
| `CHINA.ARB.POSITION_TRANSFER` | 移仓换月逻辑 | M15 |
| `CHINA.COMPLIANCE.RULE_CHECK` | 合规规则检查 | M17 |
| `CHINA.COMPLIANCE.REPORT_FREQUENCY` | 报撤单频率检查 | M17 |

---

## §13 Phase 8: 智能策略升级

### 13.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/execution/algo/twap.py` | ~200 | TWAP算法 | ⏸ 待新增 |
| `src/execution/algo/vwap.py` | ~250 | VWAP算法 | ⏸ 待新增 |
| `src/execution/algo/iceberg.py` | ~200 | 冰山单算法 | ⏸ 待新增 |
| `src/execution/algo/adaptive.py` | ~300 | 自适应执行 | ⏸ 待新增 |
| `src/execution/impact_model.py` | ~200 | 市场冲击模型 | ⏸ 待新增 |
| `src/compliance/throttle.py` | ~250 | 合规节流器 | ⏸ 待新增 |
| `src/strategy/experimental/maturity_evaluator.py` | ~810 | 成熟度评估 | ✅ |
| `src/strategy/experimental/training_gate.py` | ~375 | 训练门禁 | ✅ |
| `src/strategy/experimental/training_monitor.py` | ~615 | 训练监控 | ✅ |
| `src/strategy/experimental/__init__.py` | ~65 | 模块导出 | ✅ |

### 13.2 执行算法设计

#### TWAP算法

```python
class TWAPAlgo:
    """时间加权平均价格算法"""

    def __init__(
        self,
        total_volume: int,
        duration_minutes: int,
        interval_seconds: int = 60,
    ):
        self.total_volume = total_volume
        self.duration_minutes = duration_minutes
        self.interval_seconds = interval_seconds
        self.slice_count = duration_minutes * 60 // interval_seconds
        self.slice_volume = total_volume // self.slice_count

    def get_next_slice(self) -> OrderSlice:
        """获取下一个切片订单"""
        # ...
```

#### VWAP算法

```python
class VWAPAlgo:
    """成交量加权平均价格算法"""

    def __init__(
        self,
        total_volume: int,
        volume_profile: list[float],  # 历史成交量分布
        start_time: str,
        end_time: str,
    ):
        self.total_volume = total_volume
        self.volume_profile = volume_profile
        self.start_time = start_time
        self.end_time = end_time

    def get_next_slice(self, current_time: str) -> OrderSlice:
        """根据成交量分布获取下一个切片订单"""
        # ...
```

### 13.3 合规节流器

```python
class ComplianceThrottle:
    """合规节流器 (2025年新规)"""

    # 监管阈值
    REPORT_CANCEL_LIMIT_5S = 50    # 5秒内报撤单上限
    HIGH_FREQ_LIMIT_PER_SEC = 300  # 高频交易阈值 (笔/秒)
    HIGH_FREQ_LIMIT_DAILY = 20000  # 高频交易阈值 (笔/日)

    def __init__(self):
        self._order_history: deque = deque(maxlen=10000)
        self._5s_window: deque = deque()
        self._daily_count: int = 0

    def can_submit(self) -> tuple[bool, str]:
        """检查是否可以提交订单"""
        # 检查5秒窗口
        now = time.time()
        while self._5s_window and now - self._5s_window[0] > 5:
            self._5s_window.popleft()

        if len(self._5s_window) >= self.REPORT_CANCEL_LIMIT_5S:
            return False, "5秒报撤单频率超限"

        if self._daily_count >= self.HIGH_FREQ_LIMIT_DAILY:
            return False, "日内报撤单总量超限"

        return True, ""
```

### 13.4 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `ALGO.TWAP.SLICE_CALC` | TWAP切片计算 | M5 |
| `ALGO.TWAP.TIME_DISTRIBUTE` | TWAP时间分布 | M5 |
| `ALGO.VWAP.VOLUME_PROFILE` | VWAP成交量分布 | M5 |
| `ALGO.VWAP.PARTICIPATION` | VWAP参与率控制 | M5 |
| `ALGO.ICEBERG.DISPLAY_SIZE` | 冰山单显示量 | M5 |
| `ALGO.ICEBERG.REFRESH` | 冰山单刷新逻辑 | M5 |
| `ALGO.ADAPTIVE.MARKET_STATE` | 自适应市场状态 | M5 |
| `ALGO.ADAPTIVE.STRATEGY_SWITCH` | 自适应策略切换 | M4 |
| `ALGO.IMPACT.ALMGREN_CHRISS` | Almgren-Chriss模型 | M5 |
| `ALGO.IMPACT.TEMPORARY` | 临时冲击计算 | M5 |
| `ALGO.IMPACT.PERMANENT` | 永久冲击计算 | M5 |
| `THROTTLE.5S_LIMIT` | 5秒限制检查 | M17 |
| `THROTTLE.DAILY_LIMIT` | 日内限制检查 | M17 |
| `THROTTLE.HIGH_FREQ_DETECT` | 高频检测 | M17 |
| `THROTTLE.WARNING_LEVEL` | 预警等级 | M17 |
| `EXP.MATURITY.80_THRESHOLD` | 80%成熟度门槛 | M18 |
| `EXP.MATURITY.60_DIMENSION` | 60%维度门槛 | M18 |
| `EXP.MATURITY.90_DAYS` | 90天最低训练 | M18 |
| `EXP.GATE.NO_BYPASS` | 禁止绕过门禁 | M18 |
| `EXP.GATE.MANUAL_APPROVAL` | 需人工审批 | M12, M18 |
| `EXP.MONITOR.PROGRESS` | 进度监控正确 | M18 |
| `EXP.MONITOR.ALERT` | 告警生成正确 | M9 |

---

## §14 Phase 9: 合规与监控

### 14.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/compliance/china_futures_rules.py` | ~200 | 中国期货合规规则 | ⏸ 待新增 |
| `src/compliance/programmatic_trading.py` | ~300 | 程序化交易合规 | ⏸ 待新增 |
| `src/compliance/throttle.py` | ~250 | 合规节流器 | ⏸ 待新增 |
| `src/compliance/algo_registration.py` | ~200 | 算法备案 | ⏸ 待新增 |
| `src/monitoring/health.py` | ~220 | 健康检查 | ✅ |
| `src/monitoring/metrics.py` | ~328 | Prometheus指标 | ✅ |

### 14.2 2025年程序化交易新规

```
《期货市场程序化交易管理规定（试行）》(2025年10月9日实施)

核心要求：
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 备案要求：客户需向期货公司报告，经交易所确认后方可从事程序化交易 │
│ 2. 技术系统：异常监测、阈值管理、错误防范、应急处置                  │
│ 3. 算法备案：策略类型+历史回测+风险参数三位一体                      │
│ 4. 压力测试：每月极端行情模拟 (原油跳空10%等)                        │
│ 5. 人工复核：大额订单≤30秒二次确认                                   │
│ 6. 报撤单频率：5秒50笔预警阈值                                       │
│ 7. 高频交易定义：单账户每秒≥300笔 或 单日≥20000笔                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 14.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `COMPLIANCE.REGISTRATION` | 程序化交易备案 | M17 |
| `COMPLIANCE.ALGO_RECORD` | 算法备案记录 | M17 |
| `COMPLIANCE.REPORT_CANCEL` | 报撤单频率监控 | M17 |
| `COMPLIANCE.HIGH_FREQ_DETECT` | 高频交易检测 | M17 |
| `COMPLIANCE.LARGE_ORDER` | 大额订单复核 | M12, M17 |
| `COMPLIANCE.STRESS_TEST` | 压力测试执行 | M6, M17 |
| `COMPLIANCE.EMERGENCY_STOP` | 紧急停止机制 | M6, M17 |
| `MONITOR.HEALTH.CHECK` | 健康检查执行 | M9 |
| `MONITOR.HEALTH.COMPONENT` | 组件状态监控 | M9 |
| `MONITOR.HEALTH.DEGRADED` | 降级状态检测 | M4, M9 |
| `MONITOR.METRICS.COUNTER` | 计数器指标 | M9 |
| `MONITOR.METRICS.GAUGE` | 仪表盘指标 | M9 |
| `MONITOR.METRICS.HISTOGRAM` | 直方图指标 | M9 |
| `MONITOR.METRICS.PROMETHEUS` | Prometheus导出 | M9 |
| `MONITOR.ALERT.THRESHOLD` | 阈值告警 | M9 |
| `MONITOR.ALERT.CHANNEL` | 告警渠道 | M9 |

---

## §15 Phase 10: 组合与风控增强

### 15.1 文件清单

| 文件 | 行数 | 功能 | 状态 |
|------|------|------|------|
| `src/portfolio/manager.py` | ~318 | 组合管理器 | ✅ |
| `src/portfolio/analytics.py` | ~268 | 组合分析 | ✅ |
| `src/portfolio/aggregator.py` | ~216 | 持仓聚合 | ✅ |
| `src/portfolio/__init__.py` | ~30 | 模块导出 | ✅ |
| `src/risk/var_calculator.py` | ~362 | VaR计算器 | ✅ |
| `src/risk/var_enhanced.py` | ~400 | 增强VaR | ⏸ 待新增 |
| `src/risk/attribution.py` | ~300 | 风险归因 | ⏸ 待新增 |

### 15.2 VaR增强方法

```python
class EnhancedVaRCalculator(VaRCalculator):
    """增强VaR计算器 (中国期货市场特化)"""

    def evt_var(
        self,
        returns: list[float],
        confidence: float = 0.99,
        threshold_pct: float = 0.95,
    ) -> VaRResult:
        """极值理论VaR (POT + GPD)"""
        # ...

    def semiparametric_var(
        self,
        returns: list[float],
        confidence: float = 0.99,
    ) -> VaRResult:
        """半参数VaR (核密度 + GPD)"""
        # ...

    def limit_adjusted_var(
        self,
        returns: list[float],
        limit_pct: float,
        confidence: float = 0.99,
    ) -> VaRResult:
        """涨跌停调整VaR"""
        # ...

    def liquidity_adjusted_var(
        self,
        returns: list[float],
        position_value: float,
        adv: float,  # 平均日成交量
        confidence: float = 0.99,
    ) -> VaRResult:
        """流动性调整VaR"""
        # ...
```

### 15.3 场景覆盖

| Rule ID | 场景描述 | 军规 |
|---------|----------|------|
| `PORTFOLIO.POSITION.UPDATE` | 持仓更新正确 | M1 |
| `PORTFOLIO.POSITION.LIMIT` | 持仓限额检查 | M6 |
| `PORTFOLIO.POSITION.NET` | 净持仓计算 | M1 |
| `PORTFOLIO.RISK.EXPOSURE` | 风险敞口计算 | M6 |
| `PORTFOLIO.RISK.CONCENTRATION` | 集中度计算 | M6 |
| `PORTFOLIO.PNL.ATTRIBUTION` | 盈亏归因 | M19 |
| `PORTFOLIO.SHARPE.CALCULATE` | 夏普比率计算 | M19 |
| `PORTFOLIO.DRAWDOWN.MAX` | 最大回撤计算 | M6 |
| `PORTFOLIO.SNAPSHOT.TIMESERIES` | 时序快照 | M3 |
| `VAR.HISTORICAL.PERCENTILE` | 历史VaR计算 | M6 |
| `VAR.PARAMETRIC.NORMAL` | 参数VaR计算 | M6 |
| `VAR.MONTECARLO.SIMULATION` | 蒙特卡洛VaR | M6 |
| `VAR.ES.CALCULATE` | ES/CVaR计算 | M6 |
| `VAR.EVT.GPD` | EVT-GPD方法 | M6 |
| `VAR.SEMIPARAMETRIC.KERNEL` | 半参数方法 | M6 |
| `VAR.LIMIT_ADJUSTED` | 涨跌停调整 | M6, M13 |
| `VAR.LIQUIDITY_ADJUSTED` | 流动性调整 | M6 |
| `RISK.ATTRIBUTION.FACTOR` | 因子归因 | M19 |
| `RISK.ATTRIBUTION.STRATEGY` | 策略归因 | M19 |
| `RISK.ATTRIBUTION.POSITION` | 持仓归因 | M19 |
| `RISK.BREACH.DETECT` | 风险突破检测 | M6 |
| `RISK.BREACH.ACTION` | 风险突破动作 | M6 |
| `RISK.STRESS.SCENARIO` | 压力测试场景 | M6 |
| `RISK.STRESS.RESULT` | 压力测试结果 | M6 |
| `RISK.KILLSWITCH.TRIGGER` | 熔断触发 | M6 |

---

## §16 六大交易所配置

### 16.1 交易所基本信息

| 交易所 | 代码 | 成立时间 | 主要品种 | 交易时段 |
|--------|------|----------|----------|----------|
| 上海期货交易所 | SHFE | 1999 | 金属、能化 | 日盘+夜盘 |
| 大连商品交易所 | DCE | 1993 | 农产品、化工 | 日盘+夜盘 |
| 郑州商品交易所 | CZCE | 1990 | 农产品、化工 | 日盘+夜盘 |
| 中国金融期货交易所 | CFFEX | 2006 | 股指、国债 | 仅日盘 |
| 广州期货交易所 | GFEX | 2021 | 碳酸锂、工业硅 | 日盘+夜盘 |
| 上海国际能源交易中心 | INE | 2013 | 原油、低硫燃料油 | 日盘+夜盘 |

### 16.2 品种分类

```python
PRODUCT_CATEGORIES = {
    "金属": {
        "SHFE": ["cu", "al", "zn", "pb", "ni", "sn", "ao"],
        "GFEX": ["si"],
    },
    "贵金属": {
        "SHFE": ["au", "ag"],
    },
    "黑色系": {
        "SHFE": ["rb", "hc", "ss"],
        "DCE": ["i", "j", "jm"],
    },
    "能源化工": {
        "SHFE": ["bu", "ru", "sp", "nr"],
        "DCE": ["l", "v", "pp", "eg", "eb", "pg"],
        "CZCE": ["MA", "TA", "SA", "UR", "PF"],
        "INE": ["sc", "lu", "bc"],
    },
    "农产品": {
        "DCE": ["c", "cs", "a", "b", "m", "y", "p", "jd", "lh", "rr"],
        "CZCE": ["WH", "RI", "PM", "CF", "SR", "OI", "RM", "RS", "AP", "CJ", "PK"],
    },
    "金融": {
        "CFFEX": ["IF", "IH", "IC", "IM", "T", "TF", "TS"],
    },
    "新能源": {
        "GFEX": ["lc"],  # 碳酸锂
    },
}
```

---

## §17 交易时段与夜盘规则

### 17.1 日盘交易时段

| 时段 | 时间 | 说明 |
|------|------|------|
| 早盘第一节 | 09:00 - 10:15 | 75分钟 |
| 早盘休息 | 10:15 - 10:30 | 15分钟 |
| 早盘第二节 | 10:30 - 11:30 | 60分钟 |
| 午休 | 11:30 - 13:30 | 120分钟 |
| 午盘 | 13:30 - 15:00 | 90分钟 |

### 17.2 夜盘交易时段

| 结束时间 | 品种 | 交易所 |
|----------|------|--------|
| 23:00 | 农产品、软商品 | DCE, CZCE |
| 01:00 | 黑色系、能化 | SHFE, DCE, CZCE |
| 02:30 | 贵金属、有色金属 | SHFE |

### 17.3 夜盘交易日归属

```
夜盘交易日归属规则：
┌─────────────────────────────────────────────────────────────────────┐
│ 周一夜盘 21:00 → 周二 02:30 归属于 周二交易日                        │
│ 周五夜盘 无 (周五没有夜盘)                                           │
│ 节假日前一天 无夜盘                                                  │
│ 节假日后第一天 从日盘开始                                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## §18 涨跌停板规则

### 18.1 涨跌停幅度

| 品种类型 | 日常幅度 | 连续涨跌停后 | 交割月 |
|----------|----------|--------------|--------|
| 股指期货 | ±10% | ±15% | ±20% |
| 国债期货 | ±2% | ±3% | - |
| 商品期货 | 3%-8% | +2% | +3% |
| 贵金属 | 6%-8% | +4% | - |

### 18.2 2025年春节期间调整 (示例)

| 品种 | 涨跌停幅度 | 投机保证金率 |
|------|------------|--------------|
| 铜/铝/锌/铅 | 10% | 12% |
| 镍/锡/氧化铝 | 13% | 15% |
| 金/银 | 13% | 15% |
| 螺纹钢/热卷 | 8% | 10% |
| 天然橡胶/纸浆 | 9% | 11% |

### 18.3 涨跌停价格检查

```python
def check_limit_price(
    order_price: float,
    instrument: InstrumentInfo,
    last_settle: float,
) -> tuple[bool, str]:
    """检查订单价格是否在涨跌停范围内"""

    limit_up = last_settle * (1 + instrument.price_limit_pct)
    limit_down = last_settle * (1 - instrument.price_limit_pct)

    if order_price > limit_up:
        return False, f"订单价格 {order_price} 超过涨停价 {limit_up}"

    if order_price < limit_down:
        return False, f"订单价格 {order_price} 低于跌停价 {limit_down}"

    return True, ""
```

---

## §19 保证金制度

### 19.1 保证金类型

| 类型 | 说明 |
|------|------|
| 交易保证金 | 开仓时缴纳，维持持仓 |
| 结算保证金 | 结算时调整 |
| 追加保证金 | 权益不足时追缴 |

### 19.2 保证金水平

```python
class MarginLevel(Enum):
    """保证金使用率等级"""

    SAFE = "安全"       # < 50%
    NORMAL = "正常"     # 50% - 70%
    WARNING = "预警"    # 70% - 85%
    DANGER = "危险"     # 85% - 100%
    CRITICAL = "临界"   # >= 100% (触发强平)
```

### 19.3 保证金监控

```python
class MarginMonitor:
    """保证金监控器 (军规 M16)"""

    def __init__(self, config: MarginConfig):
        self.config = config
        self._usage_ratio: float = 0.0
        self._level: MarginLevel = MarginLevel.SAFE

    def update(
        self,
        equity: float,
        margin_used: float,
    ) -> MarginLevel:
        """更新保证金使用率"""
        self._usage_ratio = margin_used / equity if equity > 0 else 1.0
        self._level = self._calculate_level()
        return self._level

    def _calculate_level(self) -> MarginLevel:
        """计算保证金等级"""
        if self._usage_ratio < 0.5:
            return MarginLevel.SAFE
        elif self._usage_ratio < 0.7:
            return MarginLevel.NORMAL
        elif self._usage_ratio < 0.85:
            return MarginLevel.WARNING
        elif self._usage_ratio < 1.0:
            return MarginLevel.DANGER
        else:
            return MarginLevel.CRITICAL
```

---

## §20 手续费结构

### 20.1 手续费类型

| 类型 | 计算方式 | 示例 |
|------|----------|------|
| 按金额 | 成交金额 × 费率 | 铜: 0.5‱ |
| 按手 | 成交手数 × 固定费用 | 螺纹钢: 1元/手 |
| 混合 | 两者取高 | 部分品种 |

### 20.2 平今手续费

| 交易所 | 平今政策 | 倍数 |
|--------|----------|------|
| SHFE | 部分品种免收 | 0-3倍 |
| DCE | 正常收取 | 1倍 |
| CZCE | 加倍收取 | 1-3倍 |
| CFFEX | 大幅加倍 | 15倍 |
| GFEX | 加倍收取 | 3-6倍 |
| INE | 部分免收 | 0-1倍 |

### 20.3 手续费计算器

```python
class ChinaFeeCalculator:
    """中国期货手续费计算器"""

    def calculate(
        self,
        instrument: InstrumentInfo,
        price: float,
        volume: int,
        direction: str,  # "OPEN" | "CLOSE" | "CLOSE_TODAY"
    ) -> float:
        """计算手续费"""

        if instrument.fee_type == "ratio":
            # 按金额
            value = price * instrument.multiplier * volume
            if direction == "OPEN":
                return value * instrument.fee_open_ratio
            elif direction == "CLOSE":
                return value * instrument.fee_close_ratio
            else:  # CLOSE_TODAY
                return value * instrument.fee_close_today_ratio

        elif instrument.fee_type == "fixed":
            # 按手
            if direction == "OPEN":
                return instrument.fee_open_fixed * volume
            elif direction == "CLOSE":
                return instrument.fee_close_fixed * volume
            else:
                return instrument.fee_close_today_fixed * volume

        else:
            # 混合: 取两者较高值
            # ...
```

---

## §21 程序化交易合规

### 21.1 2025年新规要点

| 要求 | 描述 | 系统实现 |
|------|------|----------|
| 备案 | 向期货公司报告 | 算法备案模块 |
| 阈值管理 | 报撤单频率监控 | 合规节流器 |
| 压力测试 | 每月极端行情模拟 | 压力测试模块 |
| 人工复核 | 大额订单确认 | 双重确认机制 |
| 应急处置 | 熔断机制 | 风控熔断 |

### 21.2 高频交易判定

```
高频交易判定标准 (2025年7月7日实施):
┌─────────────────────────────────────────────────────────────────────┐
│ 条件1: 单账户每秒报撤单 ≥ 300 笔                                     │
│ 条件2: 单账户单日报撤单 ≥ 20000 笔                                   │
│ 满足任一条件即判定为高频交易                                         │
│ 高频交易者需缴纳更高手续费                                           │
└─────────────────────────────────────────────────────────────────────┘
```

### 21.3 报撤单频率预警

```python
THROTTLE_LEVELS = {
    ThrottleLevel.NORMAL: {
        "5s_limit": 30,
        "daily_limit": 15000,
        "action": "正常交易",
    },
    ThrottleLevel.WARNING: {
        "5s_limit": 40,
        "daily_limit": 18000,
        "action": "发送预警，降低频率",
    },
    ThrottleLevel.CRITICAL: {
        "5s_limit": 48,
        "daily_limit": 19500,
        "action": "暂停新开仓",
    },
    ThrottleLevel.EXCEEDED: {
        "5s_limit": 50,
        "daily_limit": 20000,
        "action": "停止所有报撤单",
    },
}
```

---

## §22 VaR风控增强

### 22.1 当前VaR方法

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| 历史模拟法 | 简单直观 | 依赖历史 | 一般市场 |
| 参数法 | 计算快速 | 假设正态 | 快速估计 |
| 蒙特卡洛法 | 灵活准确 | 计算慢 | 复杂组合 |

### 22.2 增强VaR方法 (待新增)

| 方法 | 描述 | 适用场景 |
|------|------|----------|
| EVT (极值理论) | POT + GPD分布 | 极端风险 |
| 半参数法 | 核密度 + GPD | 厚尾分布 |
| 涨跌停调整 | 截断效应修正 | 中国期货 |
| 流动性调整 | 平仓成本建模 | 大额头寸 |

### 22.3 EVT-GPD实现

```python
def evt_var(
    self,
    returns: list[float],
    confidence: float = 0.99,
    threshold_pct: float = 0.95,
) -> VaRResult:
    """极值理论VaR (POT + GPD方法)"""

    # 1. 确定阈值 (第95百分位)
    sorted_returns = sorted(returns)
    threshold_idx = int(len(sorted_returns) * threshold_pct)
    threshold = sorted_returns[threshold_idx]

    # 2. 提取超阈值样本
    exceedances = [r - threshold for r in returns if r < threshold]

    if len(exceedances) < 30:
        # 样本不足，回退到历史法
        return self.historical_var(returns, confidence)

    # 3. 估计GPD参数 (矩估计)
    xi, beta = self._estimate_gpd_params(exceedances)

    # 4. 计算VaR
    n = len(returns)
    nu = len(exceedances)
    p = 1 - confidence

    if xi != 0:
        var = threshold + (beta / xi) * (((n / nu) * p) ** (-xi) - 1)
    else:
        var = threshold - beta * math.log((n / nu) * p)

    return VaRResult(
        var=abs(var),
        confidence=confidence,
        method="EVT-GPD",
        expected_shortfall=self._evt_es(var, xi, beta),
        sample_size=len(returns),
        metadata={"xi": xi, "beta": beta, "threshold": threshold},
    )
```

---

## §23 压力测试场景

### 23.1 中国期货市场历史极端场景

| 场景 | 日期 | 品种 | 波动 | 持续时间 |
|------|------|------|------|----------|
| 2015年股灾 | 2015-06 | IF | -10%/日 | 5天 |
| 2016年黑色系暴涨 | 2016-04 | RB | +6%/日 | 3天 |
| 2020年原油负价 | 2020-04 | SC | -15% | 1天 |
| 2021年动力煤调控 | 2021-10 | ZC | -10%/日 | 3天 |
| 2022年碳酸锂暴跌 | 2022-11 | LC | -15%/日 | 5天 |
| 2024年碳酸锂继续下跌 | 2024-03 | LC | -8%/日 | 10天 |

### 23.2 压力测试配置

```python
@dataclass
class StressScenario:
    """压力测试场景"""

    name: str                 # 场景名称
    description: str          # 场景描述
    price_shock: float        # 价格冲击幅度
    duration_days: int        # 持续天数
    affected_products: list   # 受影响品种
    probability: float        # 历史概率


STRESS_SCENARIOS = [
    StressScenario(
        name="CRASH_2015",
        description="2015年股灾场景",
        price_shock=-0.10,
        duration_days=5,
        affected_products=["IF", "IH", "IC"],
        probability=0.01,
    ),
    StressScenario(
        name="OIL_NEGATIVE_2020",
        description="2020年原油负价场景",
        price_shock=-0.15,
        duration_days=1,
        affected_products=["sc", "fu", "lu"],
        probability=0.001,
    ),
    # ... 更多场景
]
```

---

## §24 实验性策略门禁

### 24.1 成熟度评估系统

```
实验性策略训练成熟度评估系统 (已实现 ✅)

核心门槛:
┌─────────────────────────────────────────────────────────────────────┐
│ 1. 总成熟度 ≥ 80%                                                    │
│ 2. 任意维度 ≥ 60%                                                    │
│ 3. 训练时间 ≥ 90天                                                   │
│ 4. 人工审批通过                                                      │
│ 5. BYPASS_FORBIDDEN = True (禁止绕过)                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 24.2 五维度评估

| 维度 | 权重 | 评估指标 |
|------|------|----------|
| 收益稳定性 | 25% | 夏普比率、收益CV、月度胜率 |
| 风险控制 | 25% | 最大回撤、卡玛比率、胜率、盈亏比 |
| 市场适应性 | 20% | 状态覆盖、一致性、存活率 |
| 训练充分度 | 20% | 训练天数、训练次数、样本多样性 |
| 一致性 | 10% | 信号相关、滚动一致性 |

### 24.3 成熟度等级

```python
class MaturityLevel(Enum):
    """成熟度等级"""

    EMBRYONIC = "胚胎期"    # 0-20%
    DEVELOPING = "发育期"   # 20-40%
    GROWING = "成长期"      # 40-60%
    MATURING = "成熟期"     # 60-80%
    MATURE = "完全成熟"     # 80-100%
```

---

## §25 审计日志规范

### 25.1 日志文件命名

```
命名格式: audit_{run_id}_{date}.jsonl

示例:
audit_202512160001_20251216.jsonl
```

### 25.2 日志保留策略

| 类型 | 保留时间 | 压缩 |
|------|----------|------|
| 原始日志 | 30天 | 无 |
| 压缩日志 | 365天 | GZIP |
| 归档日志 | 永久 | Parquet |

### 25.3 必记录事件

| 事件类型 | 触发时机 | 必填字段 |
|----------|----------|----------|
| `SIGNAL_GENERATED` | 信号生成 | symbol, direction, signal_source |
| `ORDER_SUBMITTED` | 订单提交 | symbol, price, volume, order_id |
| `ORDER_FILLED` | 订单成交 | order_id, fill_price, fill_volume |
| `ORDER_REJECTED` | 订单拒绝 | order_id, reason |
| `RISK_TRIGGERED` | 风控触发 | rule_id, threshold, actual |
| `POSITION_CHANGED` | 持仓变化 | symbol, direction, volume |
| `MARGIN_WARNING` | 保证金预警 | usage_ratio, level |
| `LIMIT_PRICE_HIT` | 涨跌停触发 | symbol, limit_type |
| `STRATEGY_FALLBACK` | 策略降级 | from_strategy, to_strategy |

---

## §26 配置管理

### 26.1 配置文件结构

```yaml
# config/trading.yml

environment: production  # dev | test | production

exchange:
  shfe:
    enabled: true
    trading_hours: [[09:00, 10:15], [10:30, 11:30], [13:30, 15:00]]
    night_session: [21:00, 02:30]

risk:
  max_drawdown_pct: 0.05
  max_position_value: 10000000
  margin_warning_level: 0.7
  margin_danger_level: 0.85

strategy:
  calendar_arb:
    enabled: true
    max_position: 100
    entry_z: 2.5
    exit_z: 0.5
    stop_z: 5.0

compliance:
  report_cancel_limit_5s: 50
  high_freq_limit_daily: 20000
  large_order_threshold: 100
```

### 26.2 环境隔离

| 环境 | 配置文件 | CTP前置 | 数据库 |
|------|----------|---------|--------|
| dev | config.dev.yml | simnow | dev_db |
| test | config.test.yml | simnow | test_db |
| prod | config.prod.yml | 生产前置 | prod_db |

---

## §27 FMEA故障模式分析

### 27.1 故障模式表

| 故障模式 | 严重度 | 发生概率 | 检测难度 | RPN | 缓解措施 |
|----------|--------|----------|----------|-----|----------|
| CTP断连 | 9 | 3 | 2 | 54 | 自动重连 + 降级 |
| 行情延迟 | 7 | 4 | 3 | 84 | 超时检测 + 降级 |
| 策略异常 | 8 | 3 | 4 | 96 | 降级链 + 熔断 |
| 订单拒绝 | 6 | 5 | 2 | 60 | 重试 + 告警 |
| 保证金不足 | 9 | 2 | 2 | 36 | 实时监控 + 预警 |
| 涨跌停封板 | 7 | 6 | 1 | 42 | 价格检查 + 撤单 |

### 27.2 RPN计算

```
RPN = 严重度 × 发生概率 × 检测难度

RPN等级:
- < 50: 低风险，监控即可
- 50-100: 中风险，需要缓解措施
- > 100: 高风险，必须优先处理
```

---

## §28 回滚策略

### 28.1 回滚触发条件

| 触发条件 | 回滚范围 | 自动/手动 |
|----------|----------|-----------|
| CI门禁失败 | 单次提交 | 自动 |
| 测试覆盖下降 | 单次提交 | 自动 |
| 生产异常 | 版本回滚 | 手动 |
| 资金异常 | 系统暂停 | 手动 |

### 28.2 回滚流程

```
1. 检测到异常
2. 触发熔断 (如需)
3. 记录当前状态
4. 执行回滚
5. 验证回滚成功
6. 恢复服务
7. 发送告警
8. 事后分析
```

---

## §29 测试规范

### 29.1 测试目录结构

```
tests/
├── unit/                    # 单元测试
│   ├── test_market/
│   ├── test_strategy/
│   ├── test_risk/
│   └── ...
├── integration/             # 集成测试
│   ├── test_trading_flow/
│   └── test_ctp_integration/
├── e2e/                     # 端到端测试
│   └── test_full_cycle/
├── stress/                  # 压力测试
│   └── test_high_load/
└── conftest.py              # 公共fixtures
```

### 29.2 测试覆盖要求

| 模块 | 最低覆盖率 | 当前覆盖率 |
|------|------------|------------|
| src/trading/ | 100% | 100% |
| src/risk/ | 100% | 95% |
| src/strategy/ | 90% | 88% |
| src/market/ | 90% | 92% |
| src/execution/ | 90% | 87% |
| 总体 | 85% | 88.22% |

### 29.3 场景测试命名

```python
# 测试函数命名规范
def test_{module}_{feature}_{scenario}():
    """
    RULE_ID: {MODULE}.{FEATURE}.{SCENARIO}
    军规: M{X}
    描述: ...
    """
    pass
```

---

## §30 CI/CD集成

### 30.1 GitHub Actions工作流

```yaml
# .github/workflows/ci.yml

name: CI Pipeline

on:
  push:
    branches: [main, feat/*]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ruff Check
        run: ruff check .
      - name: Ruff Format
        run: ruff format --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Mypy
        run: mypy .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Pytest
        run: pytest tests/ -q --cov=src --cov-fail-under=85

  policy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Policy
        run: python scripts/validate_policy.py --all
```

### 30.2 门禁检查顺序

```
1. Ruff Check (代码风格)
2. Ruff Format (代码格式)
3. Mypy (类型检查)
4. Pytest (单元测试)
5. Coverage (覆盖率)
6. Policy (策略验证)
```

### 30.3 本地执行命令

```powershell
# Windows PowerShell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy .
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe scripts/validate_policy.py --all
```

---

## §31 场景矩阵总表

### 31.1 场景统计

| Phase | 场景数 | 状态 |
|-------|--------|------|
| Phase 0 基础设施 | 15 | ✅ |
| Phase 1 行情层 | 12 | ✅ |
| Phase 2 审计层 | 18 | ✅ |
| Phase 3 策略降级 | 12 | ✅ |
| Phase 4 回放验证 | 2 | ✅ |
| Phase 5 成本层 | 8 | ⏸ |
| Phase 6 B类模型 | 12 | ⏸ |
| Phase 7 中国期货特化 | 23 | ⏸ |
| Phase 8 智能策略 | 22 | 部分✅ |
| Phase 9 合规监控 | 16 | 部分✅ |
| Phase 10 组合风控 | 25 | 部分✅ |
| **总计** | **165** | - |

### 31.2 军规覆盖统计

| 军规 | 场景数 | 覆盖率 |
|------|--------|--------|
| M1 单一信号源 | 8 | 100% |
| M3 完整审计 | 18 | 100% |
| M4 降级兜底 | 6 | 100% |
| M5 成本先行 | 14 | 80% |
| M6 熔断保护 | 22 | 90% |
| M7 回放一致 | 6 | 100% |
| M9 错误上报 | 12 | 85% |
| M13 涨跌停感知 | 6 | 待实现 |
| M14 平今平昨分离 | 3 | 待实现 |
| M15 夜盘跨日处理 | 5 | 待实现 |
| M16 保证金监控 | 5 | 待实现 |
| M17 程序化合规 | 8 | 待实现 |
| M18 实验性门禁 | 7 | ✅ |

---

## §32 文件清单

### 32.1 已完成文件 (71个)

| 目录 | 文件数 | 行数估计 |
|------|--------|----------|
| src/market/ | 7 | ~1200 |
| src/audit/ | 7 | ~900 |
| src/cost/ | 2 | ~650 |
| src/guardian/ | 6 | ~1000 |
| src/execution/auto/ | 8 | ~1500 |
| src/execution/protection/ | 4 | ~600 |
| src/execution/pair/ | 3 | ~500 |
| src/strategy/calendar_arb/ | 4 | ~900 |
| src/strategy/experimental/ | 4 | ~1865 |
| src/replay/ | 2 | ~310 |
| src/portfolio/ | 4 | ~833 |
| src/monitoring/ | 3 | ~579 |
| src/risk/ | 3 | ~900 |
| src/trading/ | 4 | ~600 |
| scripts/ | 6 | ~900 |
| tests/ | ~40 | ~5000 |

### 32.2 待新增文件 (28个)

| 文件路径 | 功能 | 预计行数 |
|----------|------|----------|
| `src/market/exchange_config.py` | 六大交易所配置 | ~300 |
| `src/market/trading_calendar.py` | 夜盘交易日历 | ~250 |
| `src/cost/china_fee_calculator.py` | 中国期货手续费 | ~300 |
| `src/execution/protection/limit_price.py` | 涨跌停保护 | ~200 |
| `src/execution/protection/margin_monitor.py` | 保证金监控 | ~250 |
| `src/execution/algo/twap.py` | TWAP算法 | ~200 |
| `src/execution/algo/vwap.py` | VWAP算法 | ~250 |
| `src/execution/algo/iceberg.py` | 冰山单算法 | ~200 |
| `src/execution/algo/adaptive.py` | 自适应执行 | ~300 |
| `src/execution/impact_model.py` | 市场冲击模型 | ~200 |
| `src/guardian/triggers_china.py` | 中国期货触发器 | ~300 |
| `src/risk/var_enhanced.py` | 增强VaR | ~400 |
| `src/risk/stress_test_china.py` | 中国期货压力测试 | ~350 |
| `src/risk/attribution.py` | 风险归因 | ~300 |
| `src/strategy/calendar_arb/delivery_aware.py` | 交割感知套利 | ~250 |
| `src/strategy/dl/lstm_predictor.py` | LSTM预测模型 | ~400 |
| `src/strategy/dl/transformer_model.py` | Transformer模型 | ~500 |
| `src/strategy/dl/factor_miner.py` | 因子挖掘器 | ~350 |
| `src/strategy/rl/ppo_agent.py` | PPO强化学习 | ~450 |
| `src/strategy/rl/dqn_agent.py` | DQN强化学习 | ~400 |
| `src/strategy/rl/reward_function.py` | 奖励函数设计 | ~200 |
| `src/compliance/china_futures_rules.py` | 合规规则 | ~200 |
| `src/compliance/programmatic_trading.py` | 程序化交易合规 | ~300 |
| `src/compliance/throttle.py` | 合规节流器 | ~250 |
| `src/compliance/algo_registration.py` | 算法备案 | ~200 |
| 测试文件 | - | ~3000 |

---

## §33 工时估算

### 33.1 Phase工时

| Phase | 预计工时 | 说明 |
|-------|----------|------|
| Phase 5 成本层 | 16h | 中国期货手续费 |
| Phase 6 B类模型 | 80h | DL+RL模型 |
| Phase 7 中国期货特化 | 90h | 全面特化 |
| Phase 8 智能策略 | 40h | 执行算法 |
| Phase 9 合规监控 | 30h | 合规模块 |
| Phase 10 组合风控 | 40h | VaR增强 |
| **总计** | **296h** | - |

### 33.2 按模块工时

| 模块 | 新文件 | 测试 | 文档 | 合计 |
|------|--------|------|------|------|
| 交易所配置 | 8h | 4h | 2h | 14h |
| 手续费计算 | 8h | 4h | 2h | 14h |
| 涨跌停保护 | 6h | 3h | 1h | 10h |
| 保证金监控 | 8h | 4h | 2h | 14h |
| 执行算法 | 20h | 10h | 4h | 34h |
| 合规节流 | 8h | 4h | 2h | 14h |
| VaR增强 | 16h | 8h | 4h | 28h |
| 压力测试 | 12h | 6h | 2h | 20h |
| DL模型 | 40h | 20h | 8h | 68h |
| RL模型 | 40h | 20h | 8h | 68h |

---

## §34 验收标准

### 34.1 功能验收

- [ ] 所有165条场景测试通过
- [ ] 军规M1-M20全部有测试覆盖
- [ ] 六大交易所配置正确
- [ ] 夜盘交易日历正确
- [ ] 涨跌停价格检查生效
- [ ] 保证金监控预警正常
- [ ] 程序化合规检查通过
- [ ] VaR计算结果准确

### 34.2 性能验收

| 指标 | 要求 | 测试方法 |
|------|------|----------|
| 订单延迟 | < 10ms | 压测 |
| 信号生成 | < 1ms | 压测 |
| VaR计算 | < 100ms | 单测 |
| 行情处理 | 10000 tick/s | 压测 |

### 34.3 质量验收

| 指标 | 要求 |
|------|------|
| 测试覆盖率 | ≥ 85% |
| Ruff检查 | 0 errors |
| Mypy检查 | 0 errors |
| 文档完整性 | 100% |

---

## §35 附录

### 35.1 术语表

| 术语 | 英文 | 解释 |
|------|------|------|
| 涨停板 | Limit Up | 价格上涨到最高限制 |
| 跌停板 | Limit Down | 价格下跌到最低限制 |
| 平今仓 | Close Today | 当日开仓当日平仓 |
| 平昨仓 | Close Yesterday | 平掉前一日持仓 |
| 夜盘 | Night Session | 21:00后的交易时段 |
| 保证金 | Margin | 开仓所需资金比例 |
| 强平 | Forced Liquidation | 保证金不足时强制平仓 |
| VaR | Value at Risk | 在险价值 |
| ES/CVaR | Expected Shortfall | 期望损失/条件VaR |
| EVT | Extreme Value Theory | 极值理论 |
| GPD | Generalized Pareto Distribution | 广义帕累托分布 |

### 35.2 参考资料

1. 《期货市场程序化交易管理规定（试行）》- 中国证监会 (2025)
2. 《程序化交易管理实施细则》- 沪深北交易所 (2025)
3. 各交易所交易规则及风控制度
4. CTP API技术文档
5. 风险管理理论与实践

### 35.3 文档版本历史

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2025-12-14 | CLAUDE上校 | 初始版本 |
| v2.0 | 2025-12-15 | CLAUDE上校 | 添加Phase 3-4 |
| v3.0 | 2025-12-16 | CLAUDE上校 | 添加中国期货特化 |
| **v4.0** | **2025-12-16** | ** | **军规级最高指示文件** |

---

**文档结束**

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│                    V4PRO 军规级中国期货交易系统                      │
│                                                                     │
│                                             │
│                                                                     │
│                                                               │
│                                                                     │
│                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```
