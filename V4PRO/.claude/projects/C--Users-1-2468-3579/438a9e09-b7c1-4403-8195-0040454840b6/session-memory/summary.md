
# Session Title
_A short and distinctive 5-10 word descriptive title for the session. Super info dense, no filler_

Phase 7中国期货特化 Step 1-8✅(424测试) Step 9-10合规进行中

# Current State
_What is actively being worked on right now? Pending tasks not yet completed. Immediate next steps._

**Status**: 🚀 **Phase 7 中国期货特化 - Step 1-8 ✅完成(424测试), Step 9-10 合规模块进行中**

**最新交互**:
- 用户要求High Effort ultrathink模式继续任务
- **Step 8 交割感知套利 ✅ 完成**: 44 tests passed
  - `src/strategy/calendar_arb/delivery_aware.py` (~500 lines) ✅
  - `src/strategy/calendar_arb/__init__.py` ✅ - 添加11个新导出(21项总计)
  - `tests/test_delivery_aware.py` (~500 lines) ✅ - 44测试用例
  - **Ruff修复**: B007→改用`.values()`, PERF102→删除未用循环变量
- **Step 7 压力测试 ✅ 完成**: 52 tests passed
- **Step 6 触发器 ✅ 完成**: 66 tests passed
- **Phase 7 全量 (Step 1-8)**: **424 passed in 0.34s** ✅
- **下一步**: Step 9-10 合规模块 (compliance/)

**Step 1-8 ALL COMPLETE** ✅:
| Step | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| 1 | exchange_config.py | 41 | ✅ |
| 2 | trading_calendar.py | 53 | ✅ |
| 3 | china_fee_calculator.py | 39 | ✅ |
| 4 | limit_price.py | 61 | ✅ |
| 5 | margin_monitor.py | 68 | ✅ |
| 6 | triggers_china.py | 66 | ✅ |
| 7 | stress_test_china.py | 52 | ✅ |
| 8 | delivery_aware.py | 44 | ✅ |

**Phase 7 测试总计**: 41+53+39+61+68+66+52+44 = **424 tests passed** ✅

**全量门禁检查** (2025-12-16 Final):
| 门禁 | 状态 | 结果 |
|------|------|------|
| Ruff Check | ✅ PASS | "All checks passed!" |
| Mypy | ✅ PASS | "Success: no issues found" |
| Pytest Phase 7 | ✅ PASS | **424 passed in 0.34s** |

**Todo List** (当前进度):
- [x] 阅读V4最高指示文件并牢记军规M1-M20
- [x] 实施Step 1: 六大交易所配置 ✅ (41测试)
- [x] 实施Step 2: 夜盘交易日历 ✅ (53测试)
- [x] 实施Step 3: 中国期货手续费计算器 ✅ (39测试)
- [x] 实施Step 4: 涨跌停保护 ✅ (61测试)
- [x] 实施Step 5: 保证金监控 ✅ (68测试)
- [x] 实施Step 6: 中国期货触发器 ✅ (66测试)
- [x] 实施Step 7: 中国期货压力测试 ✅ (52测试)
- [x] 实施Step 8: 交割感知套利 ✅ (44测试)
- [ ] 实施Step 9-10: 合规模块 (compliance/) - **IN PROGRESS**

**protection目录结构** (5文件):
- `src/execution/protection/__init__.py` - 27个导出
- `src/execution/protection/liquidity.py`
- `src/execution/protection/throttle.py`
- `src/execution/protection/fat_finger.py`
- `src/execution/protection/limit_price.py` ✅ NEW
- `src/execution/protection/margin_monitor.py` ✅ NEW

**已生成文档** (3份 - ALL COMPLETE):
| 文档 | 路径 | 行数 | 核心内容 |
|------|------|------|----------|
| **最高指示文件** | `docs/V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md` | ~2400 | 军规M1-M20，35章节，Phase 0-10 |
| **验收矩阵报告** | `docs/V4PRO_ACCEPTANCE_MATRIX_SUPREME.md` | ~1100 | 165条场景，11个Phase，军规覆盖矩阵 |
| **自动闭环系统报告** | `docs/V4PRO_AUTOMATION_CLAUDE_LOOP_SUPREME.md` | ~1400 | Schema v4.0，退出码0-20，闭环流程 |

**门禁检查结果** (Final 2025-12-16):
| 门禁 | 状态 | 结果 |
|------|------|------|
| Ruff Check | ✅ PASS | "All checks passed!" |
| Ruff Format | ✅ PASS | "185 files already formatted" |
| Mypy | ✅ PASS | "Success: no issues found in 117 source files" |
| Pytest | ✅ PASS | 100% 通过 |
| Policy | ✅ PASS | "Policy validation PASSED" |

**V4PRO核心升级内容**:
- **军规扩展**: M1-M12 → M1-M20 (新增涨跌停感知/平今平昨/夜盘跨日/保证金监控/程序化合规/实验性门禁/风险归因/跨所一致)
- **退出码扩展**: 0-12 → 0-20 (新增合规检查失败/保证金不足/涨跌停触发/实验性门禁失败/成熟度不足/夜盘跨日错误/报撤单频率超限)
- **场景数**: 51条 → 165条 (新增Phase G-K: 中国期货特化/智能策略/合规监控/组合风控/B类模型)

**Project**: V4PRO 军规级交易系统 (中国期货市场) | **Branch**: feat/mode2-trading-pipeline

# Task specification
_What did the user ask to build? Any design decisions or other explanatory context_

**Current Task** (IN PROGRESS): Phase 7 中国期货市场特化实施

**Phase 7 实施计划** (已批准):
| 序号 | 文件路径 | 功能 | 军规 | 预计行数 |
|------|----------|------|------|----------|
| 1 | `src/market/exchange_config.py` | 六大交易所配置 | M20 | ~300 |
| 2 | `src/market/trading_calendar.py` | 夜盘交易日历 | M15 | ~250 |
| 3 | `src/cost/china_fee_calculator.py` | 中国期货手续费 | M5, M14 | ~300 |
| 4 | `src/execution/protection/limit_price.py` | 涨跌停保护 | M13 | ~200 |
| 5 | `src/execution/protection/margin_monitor.py` | 保证金监控 | M16 | ~250 |
| 6 | `src/guardian/triggers_china.py` | 中国期货触发器 | M6, M13, M16 | ~300 |
| 7 | `src/risk/stress_test_china.py` | 中国期货压力测试 | M6 | ~350 |
| 8 | `src/strategy/calendar_arb/delivery_aware.py` | 交割感知套利 | M15 | ~250 |
| 9 | `src/compliance/china_futures_rules.py` | 合规规则 | M17 | ~200 |
| 10 | `src/compliance/programmatic_trading.py` | 程序化交易合规 | M17 | ~300 |

**军规覆盖**: M13涨跌停感知, M14平今平昨分离, M15夜盘跨日, M16保证金监控, M17程序化合规, M20跨所一致
**新增场景**: 23条 | **预计工时**: 90h

**Previous Task** (COMPLETE): 军规级全面校准分析 + 生成三份V4PRO新文档

**分析发现** (已读取文档):
- **V3PRO_UPGRADE_PLAN_Version2.md**: 2800+行, §1-28章节, 军规M1-M12, Phase 0-6规划, 101个Scenarios目标
  - §13: 场景矩阵汇总 - A轨67条(market/guardian/audit/cost/execution/pair), B轨34条(fallback/calendar_arb/策略升级)
  - §14: 工时262h(全量), 5周里程碑计划
  - §20: FMEA矩阵 - F01-F12失败模式(行情断流/卡单/撤单无响应/持仓漂移等)
  - §21: 回滚策略 - 每Phase有明确回滚命令
  - §25: ML Pipeline规划 - FeatureStore/ModelRegistry/OnlineInference
- **V3PEO_ACCEPTANCE_MATRIX.md**: 51条Rule ID, Phase A-F, 缺少M12-M16中国期货新军规场景
- **V3PRO-AUTOMATION_CLAUDE_LOOP.md**: Schema v3.0, 退出码0-14, 固定路径artifacts/*, 需升级v4.0
- **validate_policy.py**: UUID校验, 必填字段检查, 路径规范化(.as_posix()), 支持v2/v3pro YAML
- **sim_gate.py**: 验证schema_version≥3, failures必填字段(rule_id/component/expected/actual/error)
- **三份升级报告**: VaR改进(16场景)+全面改进(35场景)+策略智能(26场景) = 77条新Scenarios设计
- **2025年监管新规**: 高频交易定义(单秒≥300笔或单日≥2万笔), 差异化收费, 各交易所配套细则

**Deliverables** (3份新文档):
1. **全新最高指示文件** - 整合所有升级报告，军规扩展到M20+
2. **全新验收矩阵报告** - 从51条扩展到150+条，覆盖所有新Scenarios
3. **全新自动闭环系统报告** - Schema v4.0，新增中国期货合规检测

**要求**:
- 仔细到每一个字
- 详细思考分析研究
- 可上网搜索任何需要的内容
- 模块间互相校准确保可直接使用
- 保证风险同时最大化利益
- 军规级别严谨一丝不苟

**Previous Task** (COMPLETE): 军规级全面校准分析 + 生成三份V4PRO新文档
- **Deliverables**:
  - `docs/V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md` (~2400 lines) - 军规M1-M20, Phase 0-10, 35章节
  - `docs/V4PRO_ACCEPTANCE_MATRIX_SUPREME.md` (~1100 lines) - 165条场景验收矩阵
  - `docs/V4PRO_AUTOMATION_CLAUDE_LOOP_SUPREME.md` (~1400 lines) - Schema v4.0, 退出码0-20

**Previous Task** (COMPLETE): 实验性策略模块训练成熟度评估系统
- **Deliverable**: `src/strategy/experimental/` 模块 (4文件, ~1865行)

**Previous Task** (COMPLETE): 策略层+全自动下单智能化升级研究
- **Deliverable**: `docs/V3PRO_STRATEGY_INTELLIGENT_UPGRADE_REPORT.md` (~1500 lines)
- **Web搜索**: 6次搜索完成，发现ICLR2025前沿论文、DRL应用、Transformer金融预测、多因子挖掘

**Previous Task** (COMPLETE): 全量最高指示文件分析 + 全项目中国期货市场深度改进
- **Deliverable**: `docs/V3PRO_CHINA_FUTURES_COMPREHENSIVE_UPGRADE_REPORT.md` (~1200 lines)
- **Web搜索完成**: 4次搜索 - 交易规则/CTP程序化/VaR风控/交易所品种
- **V3PRO_UPGRADE_PLAN_Version2.md状态**: 已更新header和comment块记录完成状态

**Previous Task** (COMPLETE): VaR模块中国期货市场改进分析 + 全项目军规级改进报告
- **Deliverable**: `docs/CHINA_FUTURES_UPGRADE_REPORT.md` (~800 lines markdown report)
- **Key Analysis Areas** (ALL DESIGNED):
  - ✅ 极值理论 (EVT) - POT方法 + GPD分布建模
  - ✅ 半参数模型 - 核密度(中心) + GPD(尾部) 混合
  - ✅ 涨跌停板截断效应 - 停板风险溢价修正
  - ✅ 流动性调整VaR - 平仓成本建模
  - ✅ 中国期货市场特化 (6交易所差异化费率、交易时段、保证金)

**中国期货市场特点** (需要在改进中考虑):
1. **涨跌停板限制**: 股指期货±10%，商品期货3-15%不等
2. **夜盘交易**: 部分品种有夜盘 (21:00-23:00/01:00/02:30)
3. **T+0交易制度**: 当日可平仓
4. **保证金制度**: 杠杆交易，保证金比例5-20%
5. **手续费结构**: 按手或按金额
6. **流动性特点**: 主力合约与非主力合约差异大
7. **交割月风险**: 临近交割月持仓限制
8. **季节性因素**: 农产品等有季节性波动

**Previous Task (COMPLETE)**: V3PRO+ 军规级全面检查 - 8个模块中文注释转换 + 门禁通过

**P0 紧急修复建议** (3 items) - **ALL COMPLETE**:
| 序号 | 建议 | 原因 | 状态 |
|------|------|------|------|
| 1 | 创建 scripts/sim_gate.py | 门禁定义引用但不存在 | ✅ 已完成 |
| 2 | 更新文档状态 | Phase 0-4已完成但文档标记"待执行" | ✅ 已完成 |
| 3 | 降级链YAML修复 | 8.4节YAML格式有中文"简单_ai" | ✅ 无需修复 (是表格非YAML) |

**P1 文档完善建议** (3 items):
| 序号 | 建议 | 章节 | 说明 |
|------|------|------|------|
| 1 | 添加Phase完成时间戳 | 2.1 | 记录Phase 0-4完成日期 |
| 2 | 补充测试文件路径 | 22.1 | 当前测试在tests/根目录 |
| 3 | 添加CI/CD集成说明 | 新章节 | GitHub Actions配置 |

**P2 架构增强建议** (3 items):
| 序号 | 建议 | 模块 | 工时 |
|------|------|------|------|
| 1 | 添加Portfolio模块 | src/portfolio/ | 16h |
| 2 | 添加Monitoring模块 | src/monitoring/ | 12h |
| 3 | VaR风控增强 | src/risk/var_calculator.py | 8h |

**Phase Status** (updated 2025-12-16):
| Phase | Files | Scenarios | Status |
|-------|-------|-----------|--------|
| 0-4 | 27/27 | 59/59 | ✅ COMPLETE |
| 5 成本层 | 1/2 | 3/8 | 🔶 部分完成 (china_fee_calculator) |
| 6 B类模型 | 0/6 | 0/12 | ⏸ Pending |
| 7 中国期货特化 | **3/10** | 8/23 | 🚀 **IN PROGRESS** (Step 1-3✅ Step 4进行中) |
| 8 智能策略 | 4/10 | 7/22 | 🔶 部分完成 (实验性门禁) |
| 9 合规监控 | 3/6 | 6/16 | 🔶 部分完成 (监控模块) |
| 10 组合风控 | 7/7 | 18/25 | 🔶 部分完成 (Portfolio/VaR) |
| **总计** | **~76/112** | **101/165** | **61%** |

**Phase 7 实施进度** (8/10 COMPLETE - 424 tests):
| Step | 文件 | 测试数 | 状态 |
|------|------|--------|------|
| 1 | exchange_config.py | 41 | ✅ |
| 2 | trading_calendar.py | 53 | ✅ |
| 3 | china_fee_calculator.py | 39 | ✅ |
| 4 | limit_price.py | 61 | ✅ |
| 5 | margin_monitor.py | 68 | ✅ |
| 6 | triggers_china.py | 66 | ✅ |
| 7 | stress_test_china.py | 52 | ✅ |
| 8 | delivery_aware.py | 44 | ✅ |
| 9-10 | compliance/ | - | 🚧 IN PROGRESS |

# Files and Functions
_What are the important files? In short, what do they contain and why are they relevant?_

**V4PRO文档体系** (3 files, ~4900 lines - COMPLETE):
- `docs/V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md` (~1960 lines) - 最高指示文件, 军规M1-M20, 35章节, Phase 0-10
- `docs/V4PRO_ACCEPTANCE_MATRIX_SUPREME.md` (~1100 lines) - 165条场景验收矩阵
- `docs/V4PRO_AUTOMATION_CLAUDE_LOOP_SUPREME.md` (~1400 lines) - Schema v4.0, 退出码0-20

**Phase 7 新增文件** (Step 1-8, 424 tests):
| 文件 | 测试 | 军规 | 核心功能 |
|------|------|------|----------|
| exchange_config.py | 41 | M20 | Exchange枚举, EXCHANGE_CONFIGS |
| trading_calendar.py | 53 | M15 | ChinaTradingCalendar, 夜盘归属 |
| china_fee_calculator.py | 39 | M5,M14 | FeeType/FeeConfig, CFFEX平今15倍 |
| limit_price.py | 61 | M13 | PRODUCT_LIMIT_PCT 60+品种 |
| margin_monitor.py | 68 | M16 | MarginLevel(5级)预警 |
| triggers_china.py | 66 | M6,M13,M16 | 三个中国期货触发器 |
| stress_test_china.py | 52 | M6,M19 | 6历史+3假设压力场景 |
| delivery_aware.py | 44 | M6,M15 | 交割感知套利+主力切换 |

**delivery_aware.py** (~500 lines) ✅:
- **枚举**: RollSignal(4种), DeliveryStatus(5种)
- **DeliveryConfig** (frozen): warning_days=10, critical_days=5, force_close_days=2
- **DeliveryAwareCalendarArb**: check_delivery()/should_roll()/should_force_close()/calculate_roll_cost()
- **MainContractDetector**: 主力合约切换检测, volume_threshold=1.5x

**stress_test_china.py** (~600 lines):
- **STRESS_SCENARIOS** (6): CRASH_2015/BLACK_2016/OIL_NEGATIVE_2020/COAL_2021/LITHIUM_2022/LITHIUM_2024
- **StressTester**: run_scenario() - 空头逻辑: `if position<0: base_pnl=-base_pnl`

**triggers_china.py** (~550 lines):
- **LimitPriceTrigger**: 涨跌停检测, LimitPriceStatus(5)
- **MarginTrigger**: 保证金五级预警
- **DeliveryApproachingTrigger**: 交割临近预警

**已完成模块汇总** (Prior sessions):
- `src/portfolio/` (4 files) - PortfolioManager, PortfolioAnalytics, PositionAggregator
- `src/monitoring/` (3 files) - HealthChecker, MetricsCollector, Prometheus export
- `src/risk/var_calculator.py` - VaRCalculator (historical/parametric/monte_carlo/ES)
- `src/strategy/experimental/` (4 files) - MaturityEvaluator, TrainingGate, TrainingMonitor

**docs/CHINA_FUTURES_UPGRADE_REPORT.md** (~800 lines) - 第一份报告:
- §1-7: VaR模块专项改进 - EVT/半参数/涨跌停/流动性
- 16条新增场景, 40h工时

**docs/V3PRO_CHINA_FUTURES_COMPREHENSIVE_UPGRADE_REPORT.md** (~1200 lines) - 第二份全面报告:

**docs/V3PRO_STRATEGY_INTELLIGENT_UPGRADE_REPORT.md** (~2300 lines with §6) - 第三份策略智能化报告:
- §1: 强化学习策略升级 - PPO/DQN/A2C/SAC/TD3配置, PPOState(64维状态向量), PPOReward奖励函数设计
- §2: Transformer策略升级 - TransformerConfig, LSTM-Transformer混合模型, PositionalEncoding, MultiHeadAttention
- §3: 多因子智能挖掘 - GeneticFactorMiner遗传规划, FactorExpression, FactorStats(IC/IR/Turnover)
- §4: 执行算法 - TWAPAlgo, VWAPAlgo(成交量分布), IcebergAlgo冰山单
- §5: 智能执行引擎 - AdaptiveExecutionEngine, MarketCondition枚举, ExecutionDecision, 市场冲击预估
- §6: 合规节流器 - ComplianceThrottle(5秒50笔限制), ThrottleLevel(NORMAL/WARNING/CRITICAL/EXCEEDED)
- 12新增文件, 19条Scenarios, 160h工时

**src/strategy/experimental/** (4 files, ~1865 lines) - 实验性策略训练成熟度评估系统 ✅ ALL GATES PASS:
- `__init__.py` (~65 lines) - 模块导出12个类(sorted): ActivationDecision, MaturityEvaluator, MaturityLevel, MaturityReport, MaturityScore, TrainingGate, TrainingGateConfig, TrainingMonitor, TrainingProgress, TrainingSession, TrainingStatus
- `maturity_evaluator.py` (~810 lines) - **CLAUDE上校成熟度评估算法**: MaturityLevel(5级), 5维度评估(收益25%/风险25%/适应性20%/充分度20%/一致性10%), 门槛(80%总分+60%维度+90天), delta拆分+zip(strict=True)
- `training_gate.py` (~375 lines) - **训练启用门禁**: ActivationStatus FSM, check_activation(), manual_approve/reject(), BYPASS_FORBIDDEN=True, to_display()带emoji进度条
- `training_monitor.py` (~615 lines) - **训练进度监控**: TrainingSession/Progress/Monitor, _big_progress_bar()带80%标记, ETA用timedelta, 7天趋势分析, 告警生成, export_report() JSON导出

**docs/V3PEO_ACCEPTANCE_MATRIX.md** (~203 lines) - 验收矩阵:
- Phase A (接口冻结+Replay-first): INST.CACHE.*, UNIV.* (8条)
- Phase B (执行可靠性): EXEC.*, FSM.*, PROT.* (15条)
- Phase C (市场侧连续性): MKT.* (4条)
- Phase D (套利工程门槛): PAIR.* (4条)
- Phase E (Guardian无人值守): GUARD.* (5条)
- Phase F (审计与回放): AUDIT.*, REPLAY.* (4条)
- 验收流程: `claude_loop.ps1 -Mode full -Strict`, `validate_policy.ps1 -Check all -Strict`

**docs/V3PRO-AUTOMATION_CLAUDE_LOOP.md** (~434 lines) - 自动闭环契约v3.0:
- 核心原则: 白名单命令 + Schema校验 + 审计日志 + 违规即停
- 退出码: 0成功/2格式/3类型/4测试/5覆盖/8回放/9仿真/**12违规**/14漂移
- Schema v3必填字段: schema_version≥3, run_id(UUID), exec_id, artifacts, check_mode
- 违规自动检测: POLICY.COMMAND_BLACKLISTED, SCHEMA.MISSING_FIELDS, POLICY.CHECK_MODE_DISABLED等
- 固定产物路径: artifacts/check/report.json, artifacts/sim/report.json, artifacts/claude/

**scripts/validate_policy.py** (~667 lines) - 策略验证器:
- 验证CI报告必填字段: schema_version, type, overall, exit_code, check_mode, timestamp, run_id, exec_id, artifacts, steps
- 验证Sim报告必填字段: +scenarios, failures (需含rule_id/component/event_id/error)
- UUID格式校验: `^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$`
- 路径规范化: `normalize_path_for_comparison()` 使用`.as_posix()`跨平台
- Required scenarios来源: `scripts/v2_required_scenarios.yml`, `scripts/v3pro_required_scenarios.yml`

**docs/V3PRO_CHINA_FUTURES_COMPREHENSIVE_UPGRADE_REPORT.md** (~1200 lines) - 第二份全面报告:
- §1: 执行摘要 - 87项改进, 35条新Scenarios
- §2: 军规改进 - 新增M12-M16:
  - M12: 涨跌停感知 (订单价格必须检查涨跌停板)
  - M13: 平今平昨分离 (平仓时必须区分)
  - M14: 夜盘跨日处理 (交易日归属正确)
  - M15: 保证金实时监控 (使用率实时计算)
  - M16: 程序化合规 (报撤单频率<50笔/5秒)
- §3: 行情层改进 - InstrumentInfo扩展20+字段, 交易所配置(`Exchange`枚举), 夜盘日历(`ChinaTradingCalendar`)
- §4: 成本模型改进 - `ChinaFeeCalculator` 按手/按金额混合, `FeeConfig` dataclass
- §5: 保护层改进 - `LimitPriceGuard`, `MarginMonitor` (MarginLevel: SAFE/WARNING/DANGER/CRITICAL)
- §6: Guardian改进 - `LimitPriceTrigger`, `MarginTrigger`, `DeliveryApproachingTrigger`
- §7: 策略层改进 - `DeliveryAwareCalendarArb` 交割感知套利
- §8: 风控增强 - `StressScenario` 枚举 (2015股灾/2020原油/2022碳酸锂等7场景)
- §9: 程序化合规 - `ProgrammaticTradingCompliance` 基于2025年10月新规
- §10-12: 10文件清单, 35条Scenarios, 实施计划 (Phase A/B/C, 90h)

**src/risk/manager.py** (~206 lines) - **风险管理器**:
- `RiskManager` class with RiskMode FSM (NORMAL→COOLDOWN→RECOVERY→LOCKED)
- `on_day_start_0900()`: 每日重置基准权益e0
- `update()`: 回撤监控，触发 kill switch
- `_fire_kill_switch()`: 撤单+平仓+进入冷却期
- `can_open()`: 根据模式和保证金比率判断是否允许开仓
- **缺失**: VaR breach检测、压力测试集成

**src/market/instrument_cache.py** (~184 lines) - **合约元数据缓存**:
- `InstrumentInfo` dataclass: symbol, product, exchange, expire_date, tick_size, multiplier, max_order_volume, position_limit
- **缺失字段** (中国期货市场需要):
  - price_limit_pct (涨跌停幅度)
  - margin_ratio (保证金率)
  - trading_sessions (交易时段，含夜盘)
  - fee_type (手续费类型: 按手/按金额)
  - is_main_contract (是否主力合约)

**src/cost/estimator.py** (~328 lines) - **成本估计器**:
- `CostBreakdown` dataclass: fee, slippage, impact, total
- `fee_estimate()`: 手续费估计 (DEFAULT_FEE_RATE=0.0001, CLOSE_TODAY_MULTIPLIER=3.0)
- `slippage_estimate()`: 滑点估计 (SLIPPAGE_BASE_TICKS=0.5)
- `impact_estimate()`: 市场冲击 (sqrt(qty/adv) 模型)
- `edge_gate()`: 信号edge必须大于总成本才交易
- **缺失**: 中国期货市场特有手续费结构 (部分品种按手收费)

**Prior Session Files** (Phase 3+4):
- `scripts/sim_gate.py` (160 lines) - Exit codes: 0=pass, 9=sim_fail, 12=policy_violation
- `src/strategy/fallback.py` (~350 lines) - FallbackManager with timeout+exception handling, DEFAULT_FALLBACK_CHAINS
- `src/strategy/calendar_arb/` (3 files, ~800 lines) - KalmanBetaEstimator, CalendarArbStrategy with 6 gate methods
- `src/replay/verifier.py` (~280 lines) - ReplayVerifier with SHA256 hash, verify_decision_sequence/verify_guardian_sequence

**V3PRO_UPGRADE_PLAN_Version2.md** (docs/, v1.1, ~2800 lines):
- **Line 3 (NEW)**: 务必切记本最高军令：专注于中国期货市场，全程使用中文，注释文档使用中文
- **Line 10**: 每次阅读后要：优化 AuditWriter 测试用例异常处理；修复 MarketSubscriber 测试用例参数命名
- §1: 军规M1-M12 | §2: 锚点 (Phase 0-4 dates added) | §3: 双轨架构
- §8: Phase 3 (fallback + calendar_arb) | §8.4: 降级链 is TABLE format (not YAML)
- §22: 测试规范 | §23: 脚本依赖 (sim_gate.py ✅)
- **§28 (NEW)**: CI/CD集成说明 - GitHub Actions, gate sequence, local commands

**tests/test_audit_writer.py** (212 lines, 12 test cases) - **REVIEWED OK**:
- `test_audit_event_structure()` - 事件结构完整
- `test_audit_jsonl_format()` - JSONL格式验证
- `test_audit_correlation_run_exec()` - run_id/exec_id关联
- `test_writer_properties()` - 写入器属性
- `test_writer_write_after_close()` - 关闭后写入测试 (pytest.raises RuntimeError)
- `test_writer_validate_event_missing_ts()` - 缺少ts验证 (使用BadEvent类, with pytest.raises)
- `test_writer_validate_event_missing_event_type()` - 缺少event_type验证
- `test_write_dict()` - 字典写入
- `test_write_dict_missing_required()` - 字典缺少必备字段 (nested context manager)
- `test_read_empty_file()` - 读取空文件
- `test_context_manager()` - 上下文管理器
- `test_exec_id_defaults_to_run_id()` - exec_id默认值
- Exception handling: All test cases properly use pytest.raises with match patterns

**tests/test_market_subscriber.py** (241 lines, 15+ test cases) - **REVIEWED OK**:
- `TestMktSubscriberDiffUpdate` (9 tests): RULE_ID="MKT.SUBSCRIBER.DIFF_UPDATE"
  - test_diff_add/remove_equals, test_diff_both_add_and_remove, test_diff_no_change
  - test_subscribe/unsubscribe_callback_invoked, test_current_subscriptions_reflects_state
  - test_incremental_subscribe/unsubscribe
- `TestSubscriberExtended` (6+ tests): 100%覆盖率补充
  - test_register_callback_new_symbol, test_register_multiple_callbacks
  - test_dispatch_no_callbacks, test_clear_with/without_callback
  - test_len, test_unsubscribe_clears_callbacks
- Parameter naming: Uses `_d` convention for unused params (lambda s, _d: ...) - correct

# Workflow
_What bash commands are usually run and in what order? How to interpret their output if not obvious?_

**Gate Checks**:
```powershell
.venv/Scripts/python.exe -m ruff check .           # Linting
.venv/Scripts/python.exe -m ruff format --check .  # Format
.venv/Scripts/python.exe -m mypy .                 # Type check
.venv/Scripts/python.exe -m pytest tests/ -q       # Tests (765 expected)
.venv/Scripts/python.exe scripts/validate_policy.py --all  # Policy
python scripts/sim_gate.py --strict                # NEW: Sim gate
```

**Phase 3+4 Completion Checks**:
```powershell
python -c "from src.strategy.fallback import FallbackManager"
python -c "from src.strategy.calendar_arb import CalendarArbStrategy"
python -c "from src.replay import ReplayVerifier"
python -c "from src.replay.verifier import ReplayVerifier"
```

# Errors & Corrections
_Errors encountered and how they were fixed. What did the user correct? What approaches failed and should not be tried again?_

**Prior Session CI Fixes**:
- Policy Exit 12: `str(Path(...))` → `.as_posix()` for JSON paths
- Mypy Exit 3: Added `ctp`, `ctp.*` to ignore_missing_imports
- __init__.py: `__all__ = ["module"]` without imports = broken exports

**This Session Ruff Errors** (16 found in new files, 11 auto-fixed, 5 manually fixed):
- ✅ `RUF012`: Added `ClassVar` annotation to EXCLUDE_FIELDS and MAX_TS_DIFF_MS
- ✅ `PIE790`: Unnecessary pass in `__init__` → auto-removed
- ✅ `SIM114`: Combine if branches → auto-fixed
- ✅ `PLW2901`: Loop variable overwritten → renamed to `stripped_line`
- ✅ `RET505`: Unnecessary elif after return → auto-fixed
- ✅ `I001`: Import block unsorted → auto-fixed (but 2 more found in full check)
- ✅ `F401`: Unused import `field` in kalman_beta.py → auto-removed
- ✅ `RUF022`: `__all__` not sorted → **FIXED** (sorted alphabetically)
- ✅ `F841`: Unused variable `observed_spread` → **FIXED** (removed line)
- ✅ `DTZ007/DTZ011`: Used `from datetime import date`, manual YYYYMMDD parsing, `# noqa: DTZ011`
- ✅ `RUF005`: Changed `[strategy_name] + self.get_chain()` to `[strategy_name, *self.get_chain()]`
- ✅ `TRY400`: Changed `logger.error("Event handler error: %s", e)` to `logger.exception("Event handler error")`

**Full Gate Check Issues - ALL FIXED**:
- ✅ `I001` `scripts/sim_gate.py:23`: Import block un-sorted → `ruff check --fix` applied
- ✅ `I001` `src/replay/__init__.py:28`: Import block un-sorted → `ruff check --fix` applied
- ✅ **mypy** `scripts/sim_gate.py:125`: `json.load` returns Any → Added explicit type annotation: `data: dict[str, Any] = json.load(f); return data`

**This Session New Issues - ALL FIXED**:
- ✅ `SIM118` `src/portfolio/manager.py:292`: Changed `key in self._positions.keys()` → `key in self._positions`
- ✅ Ruff auto-fixed 6 issues in new P2 files
- ✅ Ruff format reformatted 5 files (portfolio/, monitoring/, risk/var_calculator.py)
- ✅ Use `key in dict` instead of `key in dict.keys()` (SIM118 rule)

**Key Lessons**:
- Always use `.as_posix()` for Path→string in JSON
- Use `ClassVar[type]` for mutable class attributes (sets, dicts)
- For date calculations without timezone, use `# noqa: DTZ011` or `# noqa: DTZ005`
- Use `logging.exception()` instead of `logging.error()` in except blocks
- Prefer `[a, *list]` over `[a] + list` for list concatenation
- `json.load()` returns `Any` - need explicit cast for mypy
- **DTZ005**: datetime.now() needs tz argument → use `# noqa: DTZ005` for internal timestamps
- **RUF001**: Chinese fullwidth comma/exclamation → can ignore for Chinese strings (中文字符串合理使用)
- **RUF022**: `__all__` must be sorted alphabetically (no comments in list, pure list of strings)
- **E501**: Line too long → multiple fix patterns:
  - Pattern 1: 拆分为 `delta = (a - b) / (c - d)` 然后 `score = 0.8 + delta * 0.2`
  - Pattern 2: 拆分为 `delta = (win_rate - self.WIN_RATE_GOOD)` 然后 `delta /= ...`
  - Pattern 3: 引入中间变量 `n = len(history.daily_returns)` 然后用 n 代替
  - Pattern 4: 中文f-string拆分为多行: `reason = (\n    f"部分1, "\n    f"部分2"\n)`
- **B905**: zip()需要explicit strict=参数 → 添加 `strict=True` (长度已验证相等时)
  - 生成器表达式中的zip: 拆分为变量 `cov_sum = sum(...for s, r in zip(..., strict=True))`
- **RUF100**: 无用的noqa指令 → `default_factory=datetime.now`不触发DTZ005，移除noqa
- **⚠️ replace_all陷阱**: 批量替换`datetime.now()`会破坏`datetime.now().method()`调用！
  - **错误做法**: replace_all `datetime.now()` → `datetime.now()  # noqa: DTZ005` 会变成 `datetime.now()  # noqa: DTZ005.isoformat()`
  - **正确做法**: 分别处理 `datetime.now()` (单独使用) 和 `datetime.now().isoformat()` (方法链)
  - **语法错误示例**: `start_time=datetime.now()  # noqa: DTZ005,` 逗号位置错误导致syntax error
  - **修复方法**: 手动编辑，确保逗号在noqa注释之前: `start_time=datetime.now(),  # noqa: DTZ005`
- **F841 unused variable陷阱**: 删除变量定义时要检查后续是否有使用该变量的代码！
  - **错误案例**: 删除`empty = width - filled`但下一行`"░" * empty`仍在使用
  - **正确做法**: 删除变量定义同时更新所有使用处，或保留变量定义
- **F821 undefined name**: replace_all操作可能移除导入语句中的模块引用
  - **错误案例**: 替换`datetime.now()`导致`timedelta`不再有效导入上下文
  - **正确做法**: 修复后检查所有使用的名称是否都有正确导入
- **Mypy dict类型参数**: `dict`和`list[dict]`需要指定类型参数
  - **错误**: `def to_dict(self) -> dict:` → mypy error: Missing type parameters for generic type "dict"
  - **修复**: `def to_dict(self) -> dict[str, object]:` (使用`object`而非`Any`更Pythonic)
  - **list[dict]修复**: `list[dict]` → `list[dict[str, object]]`

**Step 2 trading_calendar.py 错误修复** (ALL FIXED ✅):
- ✅ **F401**: 移除未使用导入 `get_night_session_end`, `has_night_session`, `time`, `timedelta`
- ✅ **SIM103 ×4**: 简化return语句: `if x: return False; return True` → `return not x`
- ✅ **PIE790 ×2**: 替换pass为断言 `assert calendar.has_night_session_on_day(date(2024, 12, 31)) is False`
- ✅ **DTZ001 ×24**: 添加到pyproject.toml `"tests/*"` per-file-ignores
- ✅ **Mypy unreachable**: `_is_in_night_session()` 删除冗余`if T_02_30: ...; return False`，直接`return t < END_02`

**Step 3 china_fee_calculator.py修复**:
- ✅ **RUF022 ×2**: `__all__`排序问题 - `ruff check --fix --unsafe-fixes`自动修复
- src/cost/__init__.py 和 src/market/__init__.py 的__all__列表重新排序

**Step 4 limit_price.py 错误修复历程** (ALL FIXED ✅):
- ✅ **RUF001 ×2**: 中文全角逗号→半角逗号 (line 446, 462 message f-string)
- ✅ **I001** test_limit_price.py: `ruff check --fix` 自动排序导入
- ✅ **I001+RUF022** __init__.py: `ruff check --fix --unsafe-fixes` 自动排序导入和__all__
- ✅ **Pytest FAIL修复**: test_very_small_limit_pct - tick_size=0.0 + pytest.approx

**Step 5 margin_monitor.py 错误修复历程** (ALL FIXED ✅):
- ✅ **F401**: 移除未使用导入 `field` 和 `timedelta`
- ✅ **SIM108**: if-else → 三元运算符 `direction = "升级" if current_idx > previous_idx else "降级"`
- ✅ **B017**: `pytest.raises(Exception)` → `pytest.raises(AttributeError)` (frozen dataclass)
- ✅ **PGH003**: `# type: ignore` → `# type: ignore[misc]` (具体规则代码)
- ✅ **Pytest FAIL修复 ×2**:
  - test_can_open_with_warning: required_margin 25000→35000 (开仓后75%才进入WARNING)
  - test_very_small_equity: margin 0.005→0.004 (40%才是SAFE，50%是NORMAL边界)

**Step 6 triggers_china.py 错误修复** (ALL FIXED ✅):
- ✅ **SIM108**: if-else改三元运算符 `usage_ratio = (margin_used / equity if equity > 0 else (1.0 if margin_used > 0 else 0.0))`
- ✅ **DTZ011/DTZ007**: `date.today()` + `datetime.strptime()` → 添加`# noqa`
- ✅ **F401**: test文件`import pytest` unused → `ruff check --fix` 自动移除
- ✅ **pyproject.toml**: 添加DTZ011到tests/*忽略列表
- ✅ **RUF022**: `__all__` not sorted → `ruff check --fix --unsafe-fixes`
- ✅ **Pytest FAIL修复**: test_level_changed - 初始_last_level=SAFE，第一次检查40%也是SAFE → `level_changed is False`

**Step 7 stress_test_china.py 错误修复** (ALL FIXED ✅):
- ✅ `RUF022`: src/risk/__init__.py `__all__` not sorted → `ruff check --fix --unsafe-fixes`
- ✅ `SIM114`: stress_test_china.py:471 Combine if branches → 自动修复
- ✅ `E501`: Line 471 too long (129>100) → 引入中间变量`level`+`is_pass`
- ✅ **Pytest FAIL修复**: test_short_position_profit_on_crash - value应为绝对值

**Step 8 delivery_aware.py 错误修复** (ALL FIXED ✅):
- ✅ **F401 ×2**: 移除未使用导入`timedelta` (源码+测试文件) - `ruff check --fix`
- ✅ **B007+PERF102**: `for sym, info in self._contracts.items()` → `for info in self._contracts.values()` (sym未使用)
- **calendar_arb/__init__.py 更新**: docstring升级v4.0, 添加11个新导出, __all__扩展到21项

# Codebase and System Documentation
_What are the important system components? How do they work/fit together?_

**Current System**: 37 files, 65 scenarios, 765 tests, 88.22% coverage

**Target** (V3PRO_UPGRADE_PLAN v1.1): 42 files, 101 scenarios, 全量262h

**中国期货市场监管新规** (2025年生效 - Web搜索结果):
- **《期货市场程序化交易管理规定（试行）》**: 2025年10月9日起实施 (证监会2025.6.13发布)
- 客户需向期货公司报告，经交易所确认后方可从事程序化交易
- **高频交易定义**: 单账户每秒申报撤单≥300笔，或单日≥20000笔
- 技术系统要求: 异常监测、阈值管理、错误防范、应急处置
- 算法备案: 策略类型+历史回测+风险参数三位一体
- **差异化收费**: 高频交易者更高流量费、撤单费 (市场化调节手段)
- **各交易所配套细则**: 2025.6.27上期所/大商所/郑商所/广期所/中金所/INE同步发布
- **异常交易行为**: 瞬时申报速率异常、频繁瞬时撤单、频繁拉抬打压、短时间大额成交

**2025年保证金/涨跌停调整** (上期所春节期间):
- 铜/铝/锌/铅: 涨跌停10%, 投机保证金12%
- 镍/锡/氧化铝/金/银: 涨跌停13%, 投机保证金15%
- 螺纹钢/热卷/不锈钢: 涨跌停8%, 投机保证金10%
- 天然橡胶/纸浆: 涨跌停9%, 投机保证金11%

**Phase 3 Architecture**:
- `FallbackManager` wraps strategies with timeout+exception handling
- `KalmanBetaEstimator` provides dynamic hedge ratio for calendar spreads
- `CalendarArbStrategy` uses Kalman z-score for entry/exit signals

**套利信号逻辑** (§8.5):
- z > entry_z (2.5): 做空价差 (卖近买远)
- z < -entry_z: 做多价差 (买近卖远)
- |z| < exit_z (0.5): 平仓
- |z| > stop_z (5-6): 止损+冷却

# Learnings
_What has worked well? What has not? What to avoid? Do not duplicate items from other sections_

**Claude Code 工作模式选择**:
- **规划任务**: 使用Plan Mode (只读，专注分析和设计，需用户批准)
- **编码任务**: 使用Normal Mode (默认，可执行所有操作)
- **复杂任务**: 先Plan Mode规划 → 用户批准 → Normal Mode实施
- 进入Plan Mode: 说"先帮我规划"或由Claude判断任务复杂度自动进入

- **ALWAYS use `.as_posix()` for Path→string in JSON/config**
- **__init__.py exports**: Need BOTH `from .module import Class` AND `__all__ = ["Class"]`
- pyproject.toml `ignore_missing_imports` makes inline `# type: ignore` = "unused-ignore" error
- ThreadPoolExecutor with timeout is effective for strategy timeout detection
- Kalman filter update step: need to bound beta to prevent divergence
- Use `typing.ClassVar` for mutable class attributes (sets, dicts) to avoid RUF012
- Use `logging.exception()` instead of `logging.error()` in except blocks (auto includes traceback)
- Prefer `[a, *list]` over `[a] + list` for list concatenation (RUF005)
- Use `key in dict` not `key in dict.keys()` (SIM118) - more Pythonic and efficient
- **最高指示要求所有不影响代码运行的注释和文档使用中文**
- Chinese docstring pattern: "属性:" for Attributes, "参数:" for Args, "返回:" for Returns, "示例:" for Example
- Chinese module docstring format: """模块名 (军规级 v3.0).\n\n功能特性:\n- 功能1\n- 功能2\n\n示例:\n    code"""

**中国期货市场关键知识** (Web搜索学习 2025年最新):
- **2025年新规**: 《期货市场程序化交易管理规定（试行）》2025.6.13发布, 10月9日起实施
- **算法备案要求**: 策略类型+历史回测+风险参数三位一体备案模式
- **频繁报撤单预警**: 上交所5秒内申报50笔即触发预警 (2024年23家机构被限制托管服务)
- **高频交易定义**: 单账户每秒申报撤单≥300笔，或单日≥20000笔
- **差异化收费**: 交易所可对高频交易者收取更高流量费、撤单费
- **各交易所配套细则**: 2025.6.27晚间上期所/大商所/郑商所/广期所/中金所/INE同步发布征求意见稿
- **异常交易行为监控**: 瞬时申报速率异常、频繁瞬时撤单、频繁拉抬打压、短时间大额成交
- **压力测试**: 每月进行极端行情模拟 (原油跳空10%等场景)
- **六大交易所**: SHFE/DCE/CZCE/CFFEX/GFEX/INE - 各有差异化配置
- **夜盘时段**: 21:00开始, 结束时间分三档 (23:00/01:00/02:30)

**AI量化交易前沿技术** (2024-2025 Web搜索):
- **行业趋势**: 从"AI赋能"过渡到"AI原生"时代, 竞争焦点: Transformer+混合架构/强化学习/FPGA硬件
- **市场规模**: 2024年157.6-210.6亿美元, 2030年预计284.4-429.9亿美元 (CAGR 8.71-12.9%)
- **ICLR2025论文**:
  - DiffsFormer: Transformer扩散模型数据增强, CSI300+7.3%/CSI800+22.1%年化
  - AlphaQCM: 分布强化学习搜索协同Alpha公式
  - LLM+RL: Stock-Evol-Instruct算法整合6种LLM到交易框架
- **DRL应用**: EarnMore(投资组合), EarnHFT(分层RL高频), StockFormer(RL+Self-Attention摆动交易)
- **NLP/LLM**: 另类数据(非结构化文本)挖掘成为Alpha关键战场
- **顶级机构**: Citadel/Two Sigma/文艺复兴科技/D.E.Shaw/HRT/Jane Street都在招ML+NLP专家
- **算法执行**: TWAP/VWAP/POV国内最广泛, 华创算法2024年A股4万亿(占1.56%)
- **冰山单**: 中国交易所不支持原生冰山单, 需用算法拆分实现
- **量化转型**: 从"速度竞争"转向"深度竞争", 量价规律+基本面+合规风控成关键
- **强化学习市场**: 2024年527.1亿美元 → 2037年37.12万亿美元 (CAGR 65.6%)
- **DQN vs PPO vs A3C**: DQN在期货市场表现最优, PPO在探索深度场景更佳
- **Transformer金融预测**: 双注意力架构BTC MAE降低72.2%, MSE降低92.5%
- **多因子挖掘**: 遗传规划(GP)+深度神经网络自动发现Alpha, XGBOOST非线性因子合成
- **因子择时**: 2020-2024年样本外中证1000增强年化超额19.84%, IR 3.14

**方案可行性诚实评估** (重要教训):
- **成熟可用(⭐⭐⭐⭐⭐)**: TWAP/VWAP算法、合规节流器、冰山单、市场冲击模型(Almgren-Chriss)
- **可用但需谨慎(⭐⭐⭐)**: 因子挖掘(90%+过拟合)、LSTM预测(辅助信号)、智能执行引擎(简单版)
- **学术前沿/落地困难(⭐⭐)**: PPO/DQN强化学习、Transformer策略、LLM交易
- **学术论文≠实盘盈利**: 回测无滑点/冲击假设、样本内调参、策略公开后失效
- **顶级机构能用AI赚钱原因**: 顶级PhD团队(年薪百万美元)、海量独家数据、数十亿研发投入、多年迭代
- **用户明智决策**: 学术前沿模块可先训练但不启用，80%成熟度+90天最低训练期后才能启用

# Key results
_If the user asked a specific output such as an answer to a question, a table, or other document, repeat the exact result here_

**第二份全面改进报告** (COMPLETE - docs/V3PRO_CHINA_FUTURES_COMPREHENSIVE_UPGRADE_REPORT.md):

**审查统计**:
| 项目 | 数量 |
|------|------|
| 审查章节 | 28 章 |
| 发现改进项 | 87 项 |
| P0 紧急改进 | 12 项 |
| P1 重要改进 | 28 项 |
| 新增 Scenarios | 35 条 |
| 新增文件规划 | 10 个 |
| 预计工时 | 90h |

**新增军规 M12-M16**:
| 编号 | 原则 | 说明 |
|------|------|------|
| M12 | 涨跌停感知 | 订单价格必须检查涨跌停板 |
| M13 | 平今平昨分离 | 平仓时必须区分平今/平昨 |
| M14 | 夜盘跨日处理 | 夜盘交易日归属必须正确 |
| M15 | 保证金实时监控 | 保证金使用率必须实时计算 |
| M16 | 程序化合规 | 报撤单频率必须在监管阈值内 |

**新增模块设计** (10个文件):
- `src/compliance/china_futures_rules.py` - 中国期货合规规则
- `src/compliance/programmatic_trading.py` - 程序化交易合规 (2025新规)
- `src/market/exchange_config.py` - 六大交易所配置
- `src/market/trading_calendar.py` - 夜盘交易日历
- `src/cost/china_fee_calculator.py` - 按手/按金额混合收费
- `src/execution/protection/limit_price.py` - 涨跌停保护
- `src/execution/protection/margin_monitor.py` - 保证金监控
- `src/guardian/triggers_china.py` - 中国期货触发器
- `src/risk/stress_test_china.py` - 中国期货压力测试
- `src/strategy/calendar_arb/delivery_aware.py` - 交割感知套利

**新增 Scenarios** (35条):
- 军规合规: 5条 (M12-M16)
- 行情层: 5条 (涨跌停/保证金/夜盘)
- 成本层: 4条 (按手/按金额/平今)
- 保护层: 5条 (涨跌停保护/保证金监控)
- 守护层: 5条 (中国期货触发器)
- 套利策略: 3条 (交割感知)
- 风控层: 4条 (压力测试)
- 程序化合规: 4条 (2025新规)

**压力测试场景**:
- 2015年股灾: IF -10% × 5天
- 2016年黑色系暴涨: RB +6% × 3天
- 2020年原油负价: SC -15% 单日
- 2021年动力煤政策调控: ZC -10% × 3天
- 2022年碳酸锂暴跌: LC -15% × 5天

**第一份报告** (docs/CHINA_FUTURES_UPGRADE_REPORT.md):
- VaR模块专项改进: EVT/半参数/涨跌停截断/流动性调整
- 16条新增场景, 40h工时

---

**第三份报告** (COMPLETE - docs/V3PRO_STRATEGY_INTELLIGENT_UPGRADE_REPORT.md ~2300 lines):
- §1-5: 策略层(RL/Transformer/因子挖掘) + 执行层(TWAP/VWAP/智能执行/合规节流)设计
- §6 (NEW): 实验性策略训练成熟度评估系统(已实现) - 5维度评估+80%门槛+90天+人工审批
- 12新增文件设计, 19+7=26条Scenarios, 160h工时

**实验性模块新增Scenarios** (7条):
- EXP.MATURITY.80_THRESHOLD, 60_DIMENSION, 90_DAYS
- EXP.GATE.NO_BYPASS, MANUAL_APPROVAL
- EXP.MONITOR.PROGRESS, ALERT

---

**方案可行性诚实评估** (用户询问后提供):

| 模块 | 成熟度 | 现实建议 |
|------|--------|----------|
| **TWAP/VWAP** | ⭐⭐⭐⭐⭐ | 业界标准，直接实施，降低滑点30-50% |
| **合规节流器** | ⭐⭐⭐⭐⭐ | 监管硬性要求，必须做 |
| **冰山单** | ⭐⭐⭐⭐⭐ | 成熟技术，拆单逻辑简单 |
| **市场冲击模型** | ⭐⭐⭐⭐ | Almgren-Chriss 20年历史 |
| **因子挖掘** | ⭐⭐⭐ | WorldQuant在用，但90%+是过拟合 |
| **LSTM预测** | ⭐⭐⭐ | 可做辅助信号，金融信噪比极低 |
| **PPO/DQN强化学习** | ⭐⭐ | 论文好看，实盘极难：非平稳市场、过拟合、训练成本高 |
| **Transformer策略** | ⭐⭐ | ICLR回测结果≠实盘收益 |
| **LLM交易** | ⭐ | 最前沿研究，离实用很远 |

**务实建议**: 先做执行层(TWAP/VWAP/合规)确定性收益，再逐步探索策略层

**实验性策略训练成熟度评估系统** (COMPLETE ✅ - 4文件~1865行, ALL GATES PASS):
- **核心理念**: 学术前沿模块(RL/Transformer)可训练但禁止启用，直到达到成熟度门槛
- **军规门槛**: 总成熟度≥80% + 任意维度≥60% + 训练≥90天 + 人工审批
- **5维度评估**: 收益稳定性25%(夏普/CV/月度) | 风险控制25%(回撤/卡玛/胜率/盈亏比) | 市场适应性20%(状态覆盖/一致/存活) | 训练充分度20%(天数/次数/多样性) | 一致性10%(信号相关/滚动)
- **评分标准**: 夏普≥2.0优/≥1.5良/≥1.0及格; 回撤≤10%优/≤15%良/≤20%及格; 胜率≥55%优/≥50%良/≥45%及格
- **MaturityLevel**: EMBRYONIC(0-20%)→DEVELOPING→GROWING→MATURING→MATURE(80-100%)
- **进度监控面板**: ASCII进度条带80%标记, ETA预估(timedelta), 7天趋势分析, 告警生成
- **保守原则**: BYPASS_FORBIDDEN=True禁止绕过门禁

---

**军规级实现完成报告** (Previous session - COMPLETE):

| 项目 | 文件 | 场景数 | 状态 |
|------|------|--------|------|
| P0 紧急修复 | scripts/sim_gate.py | - | ✅ |
| Phase 3 降级 | src/strategy/fallback.py | 3 | ✅ |
| Phase 3 套利 | src/strategy/calendar_arb/kalman_beta.py | 3 | ✅ |
| Phase 3 套利 | src/strategy/calendar_arb/strategy.py | 6 | ✅ |
| Phase 3 导出 | src/strategy/calendar_arb/__init__.py | - | ✅ |
| Phase 4 回放 | src/replay/verifier.py | 2 | ✅ |

**项目状态报告** (2025-12-16 本会话生成):
| 指标 | 值 |
|------|-----|
| 源代码文件 | 111个 |
| 测试文件 | 68个 |
| 文档文件 | 12个 |
| 场景覆盖 | 90/165 (55%) |
| 总覆盖率 | 88.22% |

**门禁检查结果** (本会话验证):
| 门禁 | 状态 | 结果 |
|------|------|------|
| Ruff Check | ✅ PASS | "All checks passed!" |
| Ruff Format | ✅ PASS | "185 files already formatted" |
| Mypy | ✅ PASS | "117 source files" |
| Pytest | ✅ PASS | 100% 通过 |
| Policy | ✅ PASS | "Policy validation PASSED" |

**Phase 3 Scenarios** (12条) - ALL COVERED:
- `STRAT.FALLBACK.ON_EXCEPTION` ✅, `ON_TIMEOUT` ✅, `CHAIN_DEFINED` ✅
- `ARB.KALMAN.BETA_ESTIMATE` ✅, `RESIDUAL_ZSCORE` ✅, `BETA_BOUND` ✅
- `ARB.LEGS.FIXED_NEAR_FAR` ✅, `ARB.SIGNAL.HALF_LIFE_GATE` ✅
- `ARB.SIGNAL.STOP_Z_BREAKER` ✅, `EXPIRY_GATE` ✅, `CORRELATION_BREAK` ✅
- `ARB.COST.ENTRY_GATE` ✅

**Phase 4 Scenarios** (2条) - ALL COVERED:
- `REPLAY.DETERMINISTIC.DECISION` ✅: verify_decision_sequence()
- `REPLAY.DETERMINISTIC.GUARDIAN` ✅: verify_guardian_sequence()

**ALL P0+P1+P2 Upgrade Suggestions - COMPLETE**:
- P0.1: sim_gate.py ✅ (已完成prior session)
- P0.2: 文档状态更新 ✅ (6 edits)
- P0.3: 降级链YAML ✅ (无需修复, §8.4是表格)
- P1.1: Phase时间戳 ✅ (§2.1 Phase 0-4 dates)
- P1.2: 测试路径 ✅ (§22.1 current structure)
- P1.3: CI/CD说明 ✅ (**NEW §28** - GitHub Actions workflow)
- **P2.1: Portfolio模块 ✅** (4 files: __init__, manager, analytics, aggregator)
- **P2.2: Monitoring模块 ✅** (3 files: __init__, health, metrics)
- **P2.3: VaR Calculator ✅** (1 file: var_calculator.py ~370 lines)

**P2.1 Portfolio Module Features**:
- `PortfolioManager`: Multi-strategy position tracking with limits enforcement
- `PortfolioAnalytics`: RiskMetrics (exposure/concentration), PnLAttribution, Sharpe ratio, Max drawdown
- `PositionAggregator`: Time-series snapshots, position aggregation by symbol

**P2.2 Monitoring Module Features**:
- `HealthChecker`: Component health checks with register/unregister, history tracking, system summary
- `HealthStatus`: Component state (HEALTHY/DEGRADED/UNHEALTHY/UNKNOWN) with latency tracking
- `MetricsCollector`: Prometheus-compatible Counter/Gauge/Histogram metrics with labels
- `export_prometheus()`: Full Prometheus text format export

**P2.3 VaR Calculator Features**:
- `VaRCalculator`: Multi-method VaR calculation (historical, parametric, Monte Carlo)
- `VaRResult`: Dataclass with var, confidence, method, expected_shortfall, sample_size, metadata
- `historical_var()`: Empirical percentile-based VaR from sorted returns
- `parametric_var()`: Normal distribution assumption with z-score calculation
- `monte_carlo_var()`: Box-Muller simulation with configurable simulations/horizon
- `expected_shortfall()`: CVaR/ES - average of tail losses beyond VaR
- `_norm_ppf()`: Inverse normal CDF using Abramowitz & Stegun rational approximation
- Pure Python implementation - no numpy/scipy dependency

**§28 CI/CD集成说明 Content** (NEW 2025-12-16):
- §28.1: GitHub Actions workflow YAML (lint/type-check/test/policy-check jobs)
- §28.2: 门禁检查顺序 (6 steps: Lint→Format→TypeCheck→Test→Coverage→Policy)
- §28.3: 本地执行命令 (PowerShell commands for Windows)
- §28.4: CI状态徽章 markdown syntax

# Worklog
_Step by step, what was attempted, done? Very terse summary for each step_

**Prior Sessions Summary** (COMPLETE):
- Phase 3+4实现: fallback.py, calendar_arb/, replay/verifier.py
- P0+P1+P2升级建议全部完成: sim_gate.py, 文档更新, §28 CI/CD, Portfolio/Monitoring/VaR模块
- 军规级全面检查: 12处中文注释转换, 门禁全部通过
- VaR改进报告: docs/CHINA_FUTURES_UPGRADE_REPORT.md (~800 lines)
- 全面改进报告: docs/V3PRO_CHINA_FUTURES_COMPREHENSIVE_UPGRADE_REPORT.md (~1200 lines)
- 策略智能化报告: docs/V3PRO_STRATEGY_INTELLIGENT_UPGRADE_REPORT.md (~2300 lines)
- 实验性策略模块: src/strategy/experimental/ (4文件, ~1865行)
- **ALL GATES PASS**: ruff ✅ mypy ✅ pytest (765 tests) ✅

**Current Session - Phase 7 中国期货特化** (IN PROGRESS):
220. **Context resumed** - V4PRO文档已完成，用户请求阅读最高指示文件
221. **Read**: `docs/V4PRO_UPGRADE_PLAN_SUPREME_DIRECTIVE.md` (~1960 lines) - 完整通读
    - 军规M1-M20铭记, Phase 0-10状态, 六大交易所, 涨跌停/保证金/夜盘规则
222. User: 要求"查看项目状态报告"
223. **Gate checks** (ALL PASS):
    - ruff check → "All checks passed!"
    - mypy → "Success: no issues found in 117 source files"
    - validate_policy → "Policy validation PASSED"
224. **项目状态报告生成**:
    - 源代码文件: 111个
    - 测试文件: 68个
    - 文档文件: 12个
    - 场景覆盖: 90/165 (55%)
    - 覆盖率: 88.22%
225. User: 选择"实施 Phase 7 中国特化"
226. **Plan Mode**: 编写Phase 7实施计划到计划文件
    - 10个新文件清单, 23条场景, 90h工时
    - 执行顺序: exchange_config → trading_calendar → china_fee_calculator → limit_price → margin_monitor → triggers_china → stress_test_china → delivery_aware → compliance modules
227. **ExitPlanMode** - 用户批准计划，准备开始实施
228. User: "请你务必在每次任务前认真阅读V4最高指示文件！"
229. **Read**: V4最高指示文件核心部分 (lines 1-200) - 军规M1-M20牢记
230. **TodoWrite**: 创建11项任务追踪列表
231. **Write**: `src/market/exchange_config.py` (~400 lines) ✅ **CREATED**
    - Exchange枚举 (6交易所)
    - NightSessionEnd枚举 (4种夜盘结束时间)
    - TradingSession/ExchangeConfig dataclass
    - EXCHANGE_CONFIGS 六大交易所完整配置
    - PRODUCT_CATEGORIES 品种分类 (6类)
    - ProductExchangeMapper 缓存类
    - NIGHT_SESSION_PRODUCTS 夜盘品种分类
    - 10+ 便捷函数
232. **Edit**: `src/market/__init__.py` - 更新导出
    - 添加exchange_config模块导入 (14个新导出)
    - 更新__all__列表 (从9项增加到23项)
    - 更新文档注释 (V3PRO+ → V4PRO, 新增Phase 7模块说明)
233. **Write**: `tests/test_exchange_config.py` (~280 lines) ✅ **CREATED**
    - 8个测试类: TestExchangeEnum/NightSessionEnd/TradingSession/ExchangeConfig
    - TestProductExchangeMapper: 品种映射测试 (大小写不敏感)
    - TestConvenienceFunctions: 便捷函数测试
    - TestNightSessionProducts: 夜盘品种分类测试
    - TestMilitaryRuleM15/M20: 军规覆盖测试
    - RULE_ID: CHINA.EXCHANGE.CONFIG_LOAD, CHINA.EXCHANGE.PRODUCT_MAP
234. **Ruff check/format**: exchange_config.py + test_exchange_config.py → "All checks passed!"
235. **Mypy**: exchange_config.py → "Success: no issues found in 1 source file"
236. **Pytest**: test_exchange_config.py → **41 passed in 0.08s** ✅
237. **TodoWrite**: 更新Step 1完成, Step 2 in_progress
238. **Write**: `src/market/trading_calendar.py` (~500 lines) ✅ **CREATED**
    - TradingPeriod枚举 (9种时段), TradingDayInfo dataclass
    - HOLIDAYS_2025/WORKDAYS_2025 节假日调休配置
    - ChinaTradingCalendar类 (核心功能):
      - get_trading_day(dt, product) 夜盘归属判断
      - is_trading_time()/get_trading_period()
      - get_next/previous_trading_day()
      - get_trading_days_between()/add_trading_days()
    - 夜盘规则: 21:00-02:30属于下一交易日, 周五/节假日前无夜盘
239. **Edit**: `src/market/__init__.py` - 更新导出
    - 添加trading_calendar模块导入 (7个新导出)
    - 更新__all__列表 (从23项增加到30项)
240. **Write**: `tests/test_trading_calendar.py` (~450 lines) ✅ **CREATED**
    - 10个测试类覆盖: 枚举/节假日/日历/夜盘规则/交易日计算/交易时间/时段检测/范围计算/便捷函数/军规M15
    - RULE_ID: CHINA.CALENDAR.NIGHT_SESSION, CHINA.CALENDAR.TRADING_DAY, CHINA.CALENDAR.HOLIDAY
241. **Ruff check**: trading_calendar.py + test → **35 errors found**
    - F401: 4个未使用导入, F811: 1个重复定义, SIM103: 4个简化return
    - DTZ001: 25个datetime缺少tz, PIE790: 2个不必要pass
242. **Ruff format**: 2 files reformatted
243. **Edit**: trading_calendar.py - 修复F401
    - 移除未使用导入: `get_night_session_end`, `has_night_session`
    - 保留: Exchange, NightSessionEnd, get_exchange_for_product, get_night_session_end_for_product
244. **Edit**: trading_calendar.py - 修复SIM103 #1
    - `is_trading_day()`: 原`if self.is_weekend(d): return False; return True` → `return not self.is_weekend(d)`
245. **Edit**: trading_calendar.py - 修复SIM103 #2
    - `has_night_session_on_day()`: 简化周末判断返回
246. **Read**: trading_calendar.py lines 455-504 - 查看剩余SIM103位置
247. **Edit**: trading_calendar.py - 修复SIM103 #3/#4
    - `_is_in_day_session()` CFFEX: 原`if time(13,0)<=t<time(15,0): return True; return False` → `return time(13, 0) <= t < time(15, 0)`
    - 标准时段: 原`if self.LUNCH_END<=t<self.DAY_SESSION_END: return True; return False` → `return self.LUNCH_END <= t < self.DAY_SESSION_END`
248. **Edit**: test_trading_calendar.py - 修复F401
    - 移除未使用导入 `time`, `timedelta`
249. **Edit**: test_trading_calendar.py - 修复PIE790 #1
    - `test_has_night_session_before_holiday`: pass → `assert calendar.has_night_session_on_day(date(2024, 12, 31)) is False`
250. **Edit**: test_trading_calendar.py - 修复PIE790 #2
    - `test_holiday_eve_no_night_session`: pass → `assert calendar.has_night_session_on_day(date(2024, 12, 31)) is False`
251. **Ruff check**: 24 DTZ001 errors remaining (all in test file)
    - datetime()调用缺少tzinfo参数 (测试中使用naive datetime是合理的)
252. **Read**: pyproject.toml lines 64-83 - 查看per-file-ignores配置
    - 发现tests/*已有忽略列表: S101, SLF001, PT011, PT018, RUF043, RUF059, PLR0124
253. **Edit**: pyproject.toml - 添加DTZ001到tests/*忽略列表
    - `"DTZ001",   # 测试允许无时区的datetime（中国期货市场使用本地时间）`
254. **Ruff check**: trading_calendar.py + test → **"All checks passed!"** ✅
255. **Mypy check**: trading_calendar.py → **FAILED**
    - Error: `src\market\trading_calendar.py:354: error: Statement is unreachable [unreachable]`
256. **Read**: trading_calendar.py lines 345-364 - 查看unreachable代码上下文
257. **Edit**: trading_calendar.py - 修复mypy unreachable
    - 原代码: `if night_end == T_02_30: return ...; return False`
    - 修复为: `# T_02_30; return t < self.NIGHT_SESSION_END_02` (删除最后if和return False)
258. **Mypy check**: trading_calendar.py → **"Success: no issues found in 1 source file"** ✅
259. **Pytest**: test_trading_calendar.py → **53 passed in 0.08s** ✅
260. **TodoWrite**: 更新Step 2完成, Step 3 in_progress
261. **Glob**: `src/cost/*.py` - 查看现有cost模块结构
    - 发现: `__init__.py`, `estimator.py`
262. **Read**: `src/cost/__init__.py` - 了解现有导出结构
263. **Write**: `src/cost/china_fee_calculator.py` (~550 lines) ✅ **CREATED**
    - FeeType枚举: FIXED(按手)/RATIO(按金额)/MIXED(混合)
    - TradeDirection枚举: OPEN/CLOSE/CLOSE_TODAY
    - FeeConfig dataclass (frozen=True): open_ratio/close_ratio/close_today_ratio/open_fixed/close_fixed/close_today_fixed/multiplier
    - FeeResult dataclass: fee/fee_type/direction/volume/price/value/product/exchange
    - 六大交易所费率配置常量: SHFE/DCE/CZCE/CFFEX/GFEX/INE_FEE_CONFIGS
    - ALL_FEE_CONFIGS: 合并所有交易所费率
    - ChinaFeeCalculator类:
      - get_config(product) - 获取品种费率配置(大小写不敏感)
      - calculate(instrument, price, volume, direction) - 计算手续费
      - _extract_product() - 从合约代码提取品种
      - _parse_direction() - 解析交易方向字符串
      - _calc_by_ratio()/_calc_by_fixed() - 按金额/按手计算
      - estimate_round_trip() - 估算往返交易成本
      - get_fee_rate_info() - 获取费率信息摘要
    - **CFFEX平今费率15倍**: IF close_today_ratio=0.000345, open_ratio=0.000023
    - 便捷函数: get_default_calculator(), calculate_fee(), estimate_cost()
264. **Edit**: `src/cost/__init__.py` - 更新导出
    - 添加: ChinaFeeCalculator, FeeConfig, FeeResult, FeeType, TradeDirection, calculate_fee, estimate_cost, get_default_calculator
    - 文档注释更新: V3PRO+ → V4PRO, Phase 1/7
265. **Write**: `tests/test_china_fee_calculator.py` (~420 lines) ✅ **CREATED**
    - 17个测试类:
      - TestFeeTypeEnum/TestTradeDirectionEnum - 枚举测试
      - TestFeeConfig - 配置dataclass测试(含frozen不可变)
      - TestFeeResult - 结果dataclass测试
      - TestFeeConfigs - CFFEX平今15倍费率验证
      - TestChinaFeeCalculator - 计算器基础功能
      - TestByVolumeCalc - 按手收费测试(al 3元/手)
      - TestByValueCalc - 按金额收费测试(rb 0.0001, au 0.00002, i 0.0001)
      - TestCloseTodayCalc - 平今费率测试(CFFEX IF 15倍, MA 3倍)
      - TestExtractProduct - 品种代码提取
      - TestParseDirection - 方向解析(open/close/close_today/平今/开仓)
      - TestRoundTrip - 往返交易成本估算
      - TestFeeRateInfo - 费率信息获取
      - TestConvenienceFunctions - 便捷函数单例测试
      - TestMilitaryRuleM5 - 军规M5成本先行测试
      - TestMilitaryRuleM14 - 军规M14平今平昨分离测试
    - RULE_ID: CHINA.FEE.BY_VOLUME_CALC, CHINA.FEE.BY_VALUE_CALC, CHINA.FEE.CLOSE_TODAY_CALC
266. **Ruff check/format**: china_fee_calculator.py + test → "All checks passed!", "2 files reformatted" ✅
267. **Mypy check**: china_fee_calculator.py → "Success: no issues found in 1 source file" ✅
268. **Pytest**: test_china_fee_calculator.py → **39 passed in 0.08s** ✅
269. **TodoWrite**: 更新Step 3完成, Step 4 in_progress
270. **Ruff check全量**: 发现RUF022 __all__ not sorted ×2 (src/cost/__init__.py, src/market/__init__.py)
271. **Ruff fix**: `--fix --unsafe-fixes` 自动修复__all__排序
272. **Ruff check全量**: "All checks passed!" ✅
273. **Mypy全量**: "Success: no issues found in 120 source files" ✅
274. **Pytest Phase 7**: 133 passed in 0.13s (41+53+39) ✅
275. **Glob**: `src/execution/protection/*.py` - 查看现有protection目录
    - 发现: __init__.py, liquidity.py, throttle.py, fat_finger.py

**Session Continued** (Step 4 complete → Step 5):
276-291. Step 4 limit_price.py ✅ 61 tests (prior context)

**This Session - Step 5→6**:
292-304. **Step 5 margin_monitor.py ✅完成** (prior context):
    - margin_monitor.py (~720行) + test (~830行) = **68 passed**
    - Phase 7全量: **262 passed in 0.22s** ✅

**Step 6 中国期货触发器** (COMPLETE ✅ 66 tests):
305-315. triggers_china.py创建 + 测试 + 修复SIM108/DTZ011/DTZ007/F401/RUF022 → **66 passed** ✅

**Step 7 压力测试** (COMPLETE ✅ 52 tests):
316-325. stress_test_china.py创建 + 修复E501/SIM114/RUF022 + test_short_position修复 → **52 passed** ✅
326. Phase 7全量: **380 passed in 0.29s** ✅

**Step 8 交割感知套利** (COMPLETE ✅ 44 tests):
327. **Write**: `src/strategy/calendar_arb/delivery_aware.py` (~500 lines) ✅
    - RollSignal/DeliveryStatus枚举, DeliveryConfig(frozen)
    - DeliveryAwareCalendarArb + MainContractDetector
328. **Edit**: `src/strategy/calendar_arb/__init__.py` ✅ - 添加11个新导出(21总计)
329. **Write**: `tests/test_delivery_aware.py` (~500 lines) ✅ - 44测试用例
330. **Ruff fix**: F401→移除timedelta, B007+PERF102→改用`.values()`
331. **Pytest**: test_delivery_aware.py → **44 passed in 0.08s** ✅
332. **Phase 7 全量**: **424 passed in 0.34s** ✅

**Step 9-10 合规模块** (IN PROGRESS 🚧):
333. **TodoWrite**: 更新Step 8完成, Step 9-10 in_progress
334. **Glob**: src/strategy/calendar_arb/*.py - 确认delivery_aware.py已添加
335. **NEXT**: 创建src/compliance/目录 + china_futures_rules.py + programmatic_trading.py
