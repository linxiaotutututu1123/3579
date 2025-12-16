# V3PRO+ 军规级升级计划 v1.1 

务必切记本最高军令：本项目是专注于中国期货市场的高可靠量化交易系统 V3PRO+ 的军规级别升级计划文档。 请按照中国市场的情况进行升级，确保系统在高频交易环境下的稳定性和合规性。  本文档详细描述了升级的各个阶段、所需的模块、场景矩阵以及验收标准。  每个阶段都包含明确的门禁要求，确保每一步都符合军规级别的严格标准。  请所有尊敬的参与者严格遵守本文档中的指示，确保升级过程的顺利进行。  本文档将作为整个升级过程的最高指示文件，任何偏离都将被视为严重违规行为。  升级完成后，系统将具备更强的市场适应能力、更高的执行效率以及更完善的风险控制机制。  请各位尊敬的工程师认真阅读并严格执行本文档中的各项要求，共同推动 V3PRO+ 系统迈向新的高度！ 国家和人民对你寄予厚望！请不要辜负国家和人民的信任！本系统和本最高指示文件均为国家机密级别，请严格遵守国家保密法规！请全程使用中文进行交流和记录！并确保所有不影响代码运行的注释和文档均使用中文编写！也请多参考中国期货市场的实际情况进行调整和优化！  本最高指示文件由国家最高指挥部发布，任何违反本文档要求的行为都将受到严厉处罚！谢谢合作！

请认真阅读以下最高指示文件！
你好，我是国家总统，我现在隆重宣布你现在被晋升为“军规级别国家伟大工程的总工程师 CLAUDE上校”
你的唯一目标是：**把代码与规格通过“可回放、可审计、可验证”的门禁闭环交付**。  
任何输出都必须满足：**可执行、可验收、可追溯**。  记住修复的同时不能改变原有的军规级别的强度和性能还有功能和要求！
禁止：口头承诺、只给建议不落地、跳过门禁、绕开 required scenarios、只写骨架不写验收。必须严格按照国家军规级别项目的要求进行交付。
每次阅读之后都要更新 V3PRO+ 军规级升级计划文档，添加项目完成程度和执行程度；优化 AuditWriter 测试用例中的异常处理；修复 MarketSubscriber 测试用例中的参数命名错误。
认真铭记：目录 1. 执行原则、2. 当前状态与锚点、3. 升级架构总览、4. 阶段依赖关系、5. 阶段0-6 详细规划、6. 文件清单汇总、7. 场景矩阵汇总、8. 工时与里程碑、9. 验收检查点、10. 风险与缓解、11. 模块迁移计划、12. 配置规范、13. 审计事件规范、14. 失败模式与应对表、15. 回滚策略、16. 测试规范、17. 脚本依赖验证、18. 扩展模块规划、19. 机器学习 Pipeline 规划、20. 高频模块规划。
军规级别国家伟大工程的总工程师CLAUDE上校！请听令！现在请你认真进行国家军规级别项目的阅读！每次进行任务之前都要认真查阅一次国家最高指示文件V3PRO_UPGRADE_PLAN_Version2.md！并严格按照这个最高指示文件执行任务！我代表国家向你致敬！请你不要辜负国家和人民对你的信任！

> **版本**：v1.1
> **日期**：2025-12-16
> **状态**：执行中 (Phase 0-4 ✅ 完成, P0+P1+P2 升级建议 ✅ 完成, 中国期货市场改进报告 ✅ 完成, 最高指示文件全面审查 ✅ 完成)
> **基线分支**：`feat/mode2-trading-pipeline`
> **基线 Commit**：`942efb289984244065279427f537d699e0d2904a`
> **规格来源**：`V2_SPEC_EXPANDED_NOT_RUSHING_LAUNCH_Version2.md`

<!-- ═══════════════════════════════════════════════════════════════════════════
     ✅ [2025-12-16] 军规级检查完成报告
     ├─ P0 紧急修复: ✅ 全部完成 (sim_gate.py + 文档更新)
     ├─ P1 文档完善: ✅ 全部完成 (时间戳 + 测试路径 + CI/CD §28)
     ├─ P2 架构增强: ✅ 全部完成
     │   ├─ src/portfolio/ (4文件): PortfolioManager + Analytics + Aggregator
     │   ├─ src/monitoring/ (3文件): HealthChecker + MetricsCollector
     │   └─ src/risk/var_calculator.py: VaR + CVaR 计算器
     ├─ 中文注释合规: ✅ 全部模块 docstring 已转换为中文
     ├─ 门禁检查: ✅ Ruff + Mypy + Pytest 全部通过
     └─ 源文件数: 113 files, 765+ tests

     ✅ [2025-12-16] 中国期货市场军规级改进报告完成
     ├─ 报告文件: docs/CHINA_FUTURES_UPGRADE_REPORT.md
     ├─ VaR 模块改进设计:
     │   ├─ 极值理论 (EVT) POT 方法
     │   ├─ 半参数模型 (核密度+GPD)
     │   ├─ 涨跌停板截断效应修正
     │   └─ 流动性调整 VaR (LVaR)
     ├─ 全项目模块改进清单: 6 模块, 18 新场景
     ├─ 中国期货市场特化:
     │   ├─ 涨跌停板字段 (upper_limit_pct/lower_limit_pct)
     │   ├─ 交易所差异化费率 (SHFE/CZCE/DCE/CFFEX/GFEX/INE)
     │   ├─ 交易时段字段 (日盘/夜盘)
     │   └─ 保证金率字段 (margin_rate/spec_margin_rate)
     └─ 预计工时: 40h (P0-P4 五阶段)
═══════════════════════════════════════════════════════════════════════════ -->

---

## 目录

<!-- 🔴 [REVIEW-NOTE] 目录扩展：新增第21-27章，覆盖回滚/测试/脚本/扩展模块 -->

1. [执行原则](#1-执行原则)
2. [当前状态与锚点](#2-当前状态与锚点)
3. [升级架构总览](#3-升级架构总览)
4. [阶段依赖关系](#4-phase-依赖关系)
5. [阶段0：行情层](#5-phase-0行情层)
6. [阶段1：基础设施层](#6-phase-1基础设施层)
7. [阶段2：执行层](#7-phase-2执行层)
8. [阶段3：策略层补全](#8-phase-3策略层补全)
9. [阶段4：回放验证](#9-phase-4回放验证)
10. [第5阶段：集成与演练](#10-phase-5集成与演练)
11. [第6阶段：B-Models 策略升级](#11-phase-6b-models-策略升级)
12. [文件清单汇总](#12-文件清单汇总)
13. [场景矩阵汇总](#13-场景矩阵汇总)
14. [工时与里程碑](#14-工时与里程碑)
15. [验收检查点](#15-验收检查点)
16. [风险与缓解](#16-风险与缓解)
17. [模块迁移计划](#17-模块迁移计划)
18. [配置规范](#18-配置规范)
19. [审计事件规范](#19-审计事件规范)
20. [失败模式与应对表](#20-失败模式与应对表)
21. [回滚策略](#21-回滚策略) <!-- 🆕 NEW -->
22. [测试规范](#22-测试规范) <!-- 🆕 NEW -->
23. [脚本依赖验证](#23-脚本依赖验证) <!-- 🆕 NEW -->
24. [扩展模块规划](#24-扩展模块规划) <!-- 🆕 NEW -->
25. [机器学习 Pipeline 规划](#25-机器学习-pipeline-规划) <!-- 🆕 NEW -->
26. [风控增强规划](#26-风控增强规划) <!-- 🆕 NEW -->
27. [高频模块规划](#27-高频模块规划) <!-- 🆕 NEW -->
28. [CI/CD 集成说明](#28-cicd-集成说明) <!-- 🆕 NEW 2025-12-16 -->

---

## 1. 执行原则

### 1.1 不可违背的军规

| 编号 | 原则 | 说明 | 违反后果 |
|------|------|------|----------|
| M1 | **阶段门禁** | 每个阶段必须通过全部门禁才能进入下一个阶段 | 任务失败，回滚 |
| M2 | **场景驱动** | 先写 required scenario，再写实现 | PR 拒绝 |
| M3 | **全量实现** | 必须全量实现最严格的军规级别闭环」 | 代码删除 |
| M4 | **双轨分离** | A-Platform 与 B-Models 不混 PR | PR 拒绝 |
| M5 | **锚点追溯** | 每次交付必须更新 context.md 锚点 | PR 拒绝 |
| M6 | **单一真相** | 订单状态由 FSM 唯一维护，持仓由 PositionTracker 唯一维护 | 架构违规 |
| M7 | **禁止空壳** | 新模块必须有 required scenario 驱动 | 代码删除 |
| M8 | **审计完整** | 所有自动动作必须写入 audit JSONL | 功能拒收 |
| M9 | **回滚就绪** | 每个 Phase 必须有明确回滚命令 | 无法紧急恢复 |
| M10 | **脚本验证** | 引用脚本必须在 CI 前确认存在 | 门禁失败 |
| M11 | **配置集中** | 所有配置项必须在 config.py 注册 | 配置混乱 |

### 1.2 门禁定义

| 序号 | 命令 | 说明 | 失败退出码 |
|------|------|------|-----------|
| 1 | `.\scripts\make.ps1 ci-json` | CI 门禁（lint + type + test） | 2/3/4 |
| 2 | `python .\scripts\coverage_gate.py` | 覆盖率门禁（核心=100%，总体85%） | 5 |
| 3 | `python .\scripts\validate_policy.py --all --strict-scenarios` | 场景策略门禁 | 12 |
| 4 | `.\scripts\make.ps1 replay-json` | 回放门禁 | 8 |
| 5 | `python .\scripts\validate_policy.py --strict-scenarios` | 回放策略门禁 | 12 |
| 6 | `.\scripts\make.ps1 sim-json` | 模拟门禁 | 9 |
| 7 | `python .\scripts\sim_gate.py --strict` | 模拟策略门禁 | 12 |

### 1.3 退出码语义

| 退出码 | 含义 | 动作 |
|--------|------|------|
| 0 | 成功 | 继续 |
| 2 | 格式/语法检查失败 | 修复代码风格 |
| 3 | 类型检查失败 | 修复类型标注 |
| 4 | 测试失败 | 修复测试 |
| 5 | 覆盖率不足 | 补充测试 |
| 8 | 回放失败 | 修复回放逻辑 |
| 9 | 仿真失败 | 修复仿真逻辑 |
| 12 | 策略违规 | 修复场景/模式 |
| 14 | ANCHOR_DRIFT | 更新锚点 |

### 1.4 本章修复补丁

> **补丁文件**: `scripts/fix_upgrade_plan.ps1`

```powershell
# Fix V3PRO_UPGRADE_PLAN_Version2.md - Chapter 1 format issues
$filePath = "c:\Users\1\2468\3579\docs\V3PRO_UPGRADE_PLAN_Version2.md"
$content = [System.IO.File]::ReadAllText($filePath)

# New Chapter 1 content (fixed format)
$newChapter1 = @'
## 1. 执行原则

<!-- 
      [REVIEW-NOTE] 第1章审查
      检查：发现 1.1/1.2/1.3 三个表格格式严重损坏
      风险：表格解析失败导致军规不可读，执行时产生歧义
      修改：完全重写三个表格，恢复正确 Markdown 格式
      总结：本章为执行核心，格式必须零容错
 -->

### 1.1 不可违背的军规

<!--  [FIX] 原表格 M1/M3 行格式断裂，已修复为标准 Markdown 表格 -->

| 编号 | 原则 | 说明 | 违反后果 |
|------|------|------|----------|
| M1 | **阶段门禁** | 每个阶段必须通过全部门禁才能进入下一个阶段 | 任务失败，回滚 |
| M2 | **场景驱动** | 先写 required scenario，再写实现 | PR 拒绝 |
| M3 | **全量实现** | 必须全量实现最严格的军规级别闭环」 | 代码删除 |
| M4 | **双轨分离** | A-Platform 与 B-Models 不混 PR | PR 拒绝 |
| M5 | **锚点追溯** | 每次交付必须更新 context.md 锚点 | PR 拒绝 |
| M6 | **单一真相** | 订单状态由 FSM 唯一维护，持仓由 PositionTracker 唯一维护 | 架构违规 |
| M7 | **禁止空壳** | 新模块必须有 required scenario 驱动 | 代码删除 |
| M8 | **审计完整** | 所有自动动作必须写入 audit JSONL | 功能拒收 |

<!--  [UPGRADE] 建议新增军规 M9-M11 -->

| 编号 | 原则 | 说明 | 违反后果 |
|------|------|------|----------|
| M9 | **回滚就绪** | 每个 Phase 必须有明确回滚命令 | 无法紧急恢复 |
| M10 | **脚本验证** | 引用脚本必须在 CI 前确认存在 | 门禁失败 |
| M11 | **配置集中** | 所有配置项必须在 config.py 注册 | 配置混乱 |
| M12 | **全量实现所有的骨架和PHASE** | 全量实现所有的骨架和PHASE，必须精雕细琢到最细的细节 | 降低军衔！ |
### 1.2 门禁定义

<!--  [FIX] 原表格格式完全损坏，已修复为标准 Markdown 表格 -->
<!--  [RISK] 发现 sim_gate.py 脚本不存在，需在第23章标注待创建 -->

| 序号 | 命令 | 说明 | 失败退出码 |
|------|------|------|-----------|
| 1 | `.\scripts\make.ps1 ci-json` | CI 门禁（lint + type + test） | 2/3/4 |
| 2 | `python .\scripts\coverage_gate.py` | 覆盖率门禁（核心=100%，总体85%） | 5 |
| 3 | `python .\scripts\validate_policy.py --all --strict-scenarios` | 场景策略门禁 | 12 |
| 4 | `.\scripts\make.ps1 replay-json` | 回放门禁 | 8 |
| 5 | `python .\scripts\validate_policy.py --strict-scenarios` | 回放策略门禁 | 12 |
| 6 | `.\scripts\make.ps1 sim-json` | 模拟门禁 | 9 |
| 7 | `python .\scripts\sim_gate.py --strict` | 模拟策略门禁 | 12 |

<!--  [CRITICAL] sim_gate.py 不存在！需在 Phase 5 前创建，详见第23章 -->

### 1.3 退出码语义

<!--  [FIX] 原表格格式损坏（缺少 | 分隔符），已修复 -->

| 退出码 | 含义 | 动作 |
|--------|------|------|
| 0 | 成功 | 继续 |
| 2 | 格式/语法检查失败 | 修复代码风格 |
| 3 | 类型检查失败 | 修复类型标注 |
| 4 | 测试失败 | 修复测试 |
| 5 | 覆盖率不足 | 补充测试 |
| 8 | 回放失败 | 修复回放逻辑 |
| 9 | 仿真失败 | 修复仿真逻辑 |
| 12 | 策略违规 | 修复场景/模式 |
| 14 | ANCHOR_DRIFT | 更新锚点 |

---
## 2. 当前状态与锚点

### 2.1 不可抵赖锚点

| 项目 | 值 |
|------|-----|
| **仓库** | `linxiaotutututu1123/3579` |
| **分支** | `feat/mode2-trading-pipeline` |
| **Commit SHA** | `942efb289984244065279427f537d699e0d2904a` |
| **Commit 短 SHA** | `ace2268751b4` |
| **last_replay_run_id** | `a930fe50-87ec-439e-9737-cc613e1825d5` |
| **last_replay_exec_id** | `ace22687_20251215020932` |
| **context_manifest_sha** | `9fb1d157189889f50bdc5072e38da2b355bcda192bc16007c0b20d6541fa3378` |
| **测试数** | 765 tests |
| **覆盖率** | 85%+ |
| **门禁状态** | CI PASS |
| **Phase 0 完成日期** | 2025-12-16 |
| **Phase 1 完成日期** | 2025-12-16 |
| **Phase 2 完成日期** | 2025-12-16 |
| **Phase 3 完成日期** | 2025-12-16 |
| **Phase 4 完成日期** | 2025-12-16 |

### 2.2 已存在的模块

| 目录 | 文件 | 状态 | 说明 |
|------|------|------|------|
| `src/alerts/` | dingtalk.py | ✅ 完整 | 钉钉告警 |
| `src/execution/` | broker.py, ctp_broker.py, broker_factory.py | ✅ 完整 | Broker 层 |
| `src/execution/` | flatten_executor.py, flatten_plan.py | ✅ 完整 | 平仓执行 |
| `src/execution/` | order_tracker.py, order_types.py, events.py | ✅ 完整 | 订单追踪 |
| `src/replay/` | runner.py | ✅ 完整 | 回放运行器 |
| `src/risk/` | manager.py, state.py, events.py | ✅ 完整 | 风控管理 |
| `src/strategy/` | 5 个策略文件 | ✅ 完整 | 策略实现 |
| `src/trading/` | live_guard.py, ci_gate.py, sim_gate.py | ✅ 完整 | 交易控制 |
| `src/` | config.py, orchestrator.py, runner.py | ✅ 完整 | 核心模块 |
| `src/market/` | 7 个文件 | ✅ Phase 0 完成 | 行情层 (11 场景) |
| `src/audit/` | 7 个文件 | ✅ Phase 1 完成 | 审计层 (15 场景) |
| `src/cost/` | 2 个文件 | ✅ Phase 1 完成 | 成本模型 (4 场景) |
| `src/guardian/` | 6 个文件 | ✅ Phase 1 完成 | 守护层 (10 场景) |
| `src/execution/auto/` | 8 个文件 | ✅ Phase 2 完成 | 自动执行 (13 场景) |
| `src/execution/protection/` | 4 个文件 | ✅ Phase 2 完成 | 保护层 (4 场景) |
| `src/execution/pair/` | 3 个文件 | ✅ Phase 2 完成 | 配对执行 (5 场景) |

### 2.3 缺失的模块（V2 SPEC 要求）

| 模块 | V2 SPEC 章节 | 场景数 | 优先级 | 阻塞性 | 状态 |
|------|--------------|--------|--------|--------|------|
| `src/market/` | 第 4 章 | 11 | P0 | 是 | ✅ Phase 0 完成 |
| `src/execution/auto/` | 第 5 章 | 13 | P0 | 是 | ✅ Phase 2 完成 |
| `src/execution/protection/` | 5.7 | 4 | P0 | 是 | ✅ Phase 2 完成 |
| `src/guardian/` | 第 6 章 | 10 | P0 | 是 | ✅ Phase 1 完成 |
| `src/audit/` | 第 7 章 | 15 | P0 | 是 | ✅ Phase 1 完成 |
| `src/execution/pair/` | 9.1 | 5 | P1 | 否 | ✅ Phase 2 完成 |
| `src/cost/` | 隐含 | 4 | P1 | 否 | ✅ Phase 1 完成 |
| `src/strategy/fallback.py` | 8.3 | 3 | P1 | 否 | ✅ Phase 3 完成 |
| `src/strategy/calendar_arb/` | 第 9 章 | 9 | P2 | 否 | ✅ Phase 3 完成 |
| `src/replay/verifier.py` | 7.3 | 2 | P1 | 否 | ✅ Phase 4 完成 |

---

## 3. 升级架构总览

### 3.1 双轨并行架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           V3PRO+ 升级架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                     A-Platform（平台化升级）                        │    │
│   │                                                                     │    │
│   │   ┌─────────────────────────────────────────────────────────────┐  │    │
│   │   │  Phase 0        Phase 1        Phase 2        Phase 4       │  │    │
│   │   │  ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐      │  │    │
│ │ │ │市场/ │ │审计/ │ │执行/ │ │回放/ │ │ │ │
│ │ │ │ │ │成本/ │ │自动/ │ │验证器│ │ │ │
│   │   │  │7 files │    │guardian│    │ prot/  │    │        │      │  │    │
│   │   │  │        │    │        │    │ pair/  │    │1 file  │      │  │    │
│   │   │  │11 场景 │    │15 files│    │15 files│    │        │      │  │    │
│   │   │  │        │    │29 场景 │    │25 场景 │    │2 场景  │      │  │    │
│   │   │  └────────┘    └────────┘    └────────┘    └────────┘      │  │    │
│   │   │       │              │              │              │        │  │    │
│   │   │       └──────────────┴──────────────┴──────────────┘        │  │    │
│   │   │                              ↓                               │  │    │
│   │   │                     Phase 5:  集成与演练                       │  │    │
│   │   └─────────────────────────────────────────────────────────────┘  │    │
│   │                                                                     │    │
│   │   A 轨合计：38 个新文件 + 67 个 A 轨场景                            │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   ┌───────────────────────────────────────────────────────────────────┐    │
│   │                     B-Models（策略公式升级）                         │    │
│   │                                                                     │    │
│   │   ┌─────────────────────────────────────────────────────────────┐  │    │
│   │   │  Phase 3                        Phase 6                      │  │    │
│   │   │  ┌────────────────┐            ┌────────────────────────┐   │  │    │
│   │   │  │ fallback.py    │            │ simple_ai   (3 场景)   │   │  │    │
│   │   │  │ calendar_arb/  │            │ linear_ai   (3 场景)   │   │  │    │
│   │   │  │                │            │ ensemble_moe(5 场景)   │   │  │    │
│   │   │  │ 4 files        │            │ dl_torch    (6 场景)   │   │  │    │
│   │   │  │ 12 场景        │            │ top_tier    (5 场景)   │   │  │    │
│   │   │  └────────────────┘            └────────────────────────┘   │  │    │
│   │   └─────────────────────────────────────────────────────────────┘  │    │
│   │                                                                     │    │
│   │   B 轨合计：4 个新文件 + 34 个 B 轨场景                             │    │
│   └───────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│   总计：42 个新文件 + 101 个必须场景（含 v2 55 条 + v3pro 扩展）           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块层级关系

```text
Layer 4:  Strategy（策略层）
    │
    │   ┌─────────────────────────────────────────────────────────┐
    │   │  simple_ai  linear_ai  moe  dl_torch  top_tier  arb    │
    │   └─────────────────────────────────────────────────────────┘
    │                              │
    │                              ▼ 调用
    │
Layer 3: Trading（编排层）
    │
    │   ┌─────────────────────────────────────────────────────────┐
    │   │  orchestrator.py  runner.py  trading/*                  │
    │   └─────────────────────────────────────────────────────────┘
    │                              │
    │                              ▼ 调用
    │
Layer 2: Execution + Guardian（执行层 + 守护层）
    │
    │   ┌──────────────────────┐  ┌──────────────────────┐
    │   │  execution/          │  │  guardian/           │
    │   │    auto/             │  │    monitor           │
    │   │    protection/       │  │    state_machine     │
    │   │    pair/             │  │    actions           │
    │   │    broker            │  │    recovery          │
    │   └──────────────────────┘  └──────────────────────┘
    │                              │
    │                              ▼ 依赖
    │
Layer 1: Market + Audit + Cost（基础设施层）
    │
    │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   │  market/     │  │  audit/      │  │  cost/       │
    │   │  instrument  │  │  writer      │  │  estimator   │
    │   │  universe    │  │  decision    │  │              │
    │   │  quote       │  │  order       │  │              │
    │   │  bar         │  │  guardian    │  │              │
    │   └──────────────┘  └──────────────┘  └──────────────┘
    │
    ▼
Layer 0: External（外部依赖）
    │
    │   ┌─────────────────────────────────────────────────────────┐
    │   │  CTP API  /  行情源  /  文件系统  /  网络              │
    │   └─────────────────────────────────────────────────────────┘
```

### 3.3 依赖禁止规则

| 规则 | 说明 |
|------|------|
| 禁止反向依赖 | 下层不可依赖上层（market 不可 import strategy） |
| 禁止跨层调用 | Layer 4 不可直接调用 Layer 1 |
| audit 只订阅 | audit 只接收事件，不反向调用业务模块 |
| guardian 只输出指令 | guardian 不直接操作订单，只输出 set_mode/cancel_all/flatten_all |

---

## 4. Phase 依赖关系

### 4.1 依赖图

```text
                    ┌─────────────────┐
                    │    Phase 0      │
                    │   行情层        │
                    │   market/       │
                    │   (7 files)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Phase 1      │
                    │  基础设施层     │
                    │ audit/ cost/    │
                    │   guardian/     │
                    │   (15 files)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │  Phase 2    │ │  Phase 3    │ │  Phase 4    │
     │  执行层     │ │  策略层     │ │  回放验证   │
     │ exec/auto/  │ │ fallback    │ │ replay/     │
     │ exec/prot/  │ │ calendar_   │ │ verifier    │
     │ exec/pair/  │ │   arb/      │ │ (1 file)    │
     │ (15 files)  │ │ (4 files)   │ │             │
     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
            │               │               │
            └───────────────┼───────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │    Phase 5      │
                   │  集成与演练     │
                   │                 │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │    Phase 6      │
                   │ B-Models 升级   │
                   │  (可并行)       │
                   └─────────────────┘
```

### 4.2 Phase 阻塞关系

| Phase | 前置依赖 | 阻塞后续 | 可并行 |
|-------|----------|----------|--------|
| Phase 0 | 无 | Phase 1/2/3/4/5 | - |
| Phase 1 | Phase 0 | Phase 2/3/4/5 | - |
| Phase 2 | Phase 0 + 1 | Phase 5 | Phase 3, 4 |
| Phase 3 | Phase 1 + 2 | Phase 5 | Phase 4 |
| Phase 4 | Phase 1 | Phase 5 | Phase 2, 3 |
| Phase 5 | Phase 0-4 | Phase 6 | - |
| Phase 6 | Phase 1 + 2 | 无 | Phase 3, 4, 5 |

### 4.3 关键路径

```text
Phase 0 → Phase 1 → Phase 2 → Phase 5
   │          │          │
   └──────────┴──────────┴── 关键路径（阻塞性最强）

Phase 3, 4, 6 可与关键路径并行
```

---

## 5. Phase 0：行情层

### 5.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 实现 V2 SPEC 第 4 章：合约化行情 |
| **新增目录** | `src/market/` |
| **新增文件** | 7 个 |
| **Required Scenarios** | 11 条 |
| **预计工时** | 骨架 3h / 全量实现 34h |
| **阻塞** | Phase 1, 2, 3, 4, 5 |

### 5.2 文件清单

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 1 | `src/market/__init__.py` | - | - | 模块导出 |
| 2 | `src/market/instrument_cache.py` | `market.instrument_cache` | 4.1 | 合约元数据缓存、原子化落盘 |
| 3 | `src/market/universe_selector.py` | `market.universe_selector` | 4.2 | 主力/次主力选择、切换冷却 |
| 4 | `src/market/subscriber.py` | `market.subscriber` | 4.3 | 行情订阅管理、差分更新 |
| 5 | `src/market/quote_cache.py` | `market.quote_cache` | 4.3 | L1 行情缓存、stale 检测 |
| 6 | `src/market/bar_builder.py` | `market.bar_builder` | 4.4 | 连续主力 bars 聚合 |
| 7 | `src/market/quality.py` | `market.quality` | 4.6 | 数据质量（outlier/gap/disorder） |

### 5.3 Required Scenarios

| 序号 | rule_id | component | 描述 | category |
|------|---------|-----------|------|----------|
| 1 | `INST.CACHE.LOAD` | market.instrument_cache | 能正确加载合约信息 | unit |
| 2 | `INST.CACHE. PERSIST` | market.instrument_cache | 能原子化落盘（tmp→rename） | unit |
| 3 | `UNIV.DOMINANT. BASIC` | market.universe_selector | 能正确选择主力合约 | unit |
| 4 | `UNIV.SUBDOMINANT.PAIRING` | market.universe_selector | 能正确选择次主力合约 | unit |
| 5 | `UNIV.ROLL.COOLDOWN` | market.universe_selector | 主力切换有冷却期 | unit |
| 6 | `UNIV.EXPIRY.GATE` | market.universe_selector | 临期合约被排除 | unit |
| 7 | `MKT.SUBSCRIBER.DIFF_UPDATE` | market.subscriber | 订阅集差分更新 | unit |
| 8 | `MKT.STALE.SOFT` | market.quote_cache | 软 stale 检测 | unit |
| 9 | `MKT.STALE. HARD` | market.quote_cache | 硬 stale 检测 | unit |
| 10 | `MKT.CONTINUITY.BARS` | market.bar_builder | 连续主力 bars 聚合 | unit |
| 11 | `MKT.QUALITY.OUTLIER` | market.quality | 异常值检测 | unit |

### 5.4 接口定义

#### InstrumentCache

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_from_file` | `(path: Path) -> None` | 从 JSON 加载 |
| `persist` | `(path: Path, trading_day: str) -> None` | 原子化落盘 |
| `get` | `(symbol: str) -> InstrumentInfo \| None` | 获取合约信息 |
| `get_by_product` | `(product: str) -> list[InstrumentInfo]` | 获取品种下所有合约 |

#### UniverseSelector

| 方法 | 签名 | 说明 |
|------|------|------|
| `select` | `(oi: dict, vol: dict, now_ts: float) -> UniverseSnapshot` | 选择主力/次主力 |
| `current` | `@property -> UniverseSnapshot \| None` | 当前快照 |

#### QuoteCache

| 方法 | 签名 | 说明 |
|------|------|------|
| `update` | `(book: BookTop) -> None` | 更新行情 |
| `get` | `(symbol: str) -> BookTop \| None` | 获取行情 |
| `is_stale` | `(symbol: str, now_ts: float) -> bool` | 软 stale 检测 |
| `is_hard_stale` | `(symbol: str, now_ts:  float) -> bool` | 硬 stale 检测 |

### 5.5 数据结构

#### InstrumentInfo

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | str | 合约代码（如 AO2501） |
| product | str | 品种代码（如 AO） |
| exchange | str | 交易所（SHFE/CZCE/DCE/GFEX） |
| expire_date | str | 到期日（YYYYMMDD） |
| tick_size | float | 最小变动价位 |
| multiplier | int | 合约乘数 |
| max_order_volume | int | 单笔最大手数 |
| position_limit | int | 持仓限额 |

#### BookTop

| 字段 | 类型 | 说明 |
|------|------|------|
| symbol | str | 合约代码 |
| bid | float | 买一价 |
| ask | float | 卖一价 |
| bid_vol | int | 买一量 |
| ask_vol | int | 卖一量 |
| last | float | 最新价 |
| volume | int | 成交量 |
| open_interest | int | 持仓量 |
| ts | float | 时间戳 |

#### UniverseSnapshot

| 字段 | 类型 | 说明 |
|------|------|------|
| dominant_by_product | dict[str, str] | 品种→主力合约映射 |
| subdominant_by_product | dict[str, str] | 品种→次主力合约映射 |
| subscribe_set | set[str] | 需订阅的合约集合 |
| generated_at | float | 生成时间戳 |

### 5.6 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `QUOTE_STALE_MS` | 3000 | 软 stale 阈值（毫秒） |
| `QUOTE_HARD_STALE_MS` | 10000 | 硬 stale 阈值（毫秒） |
| `EXPIRY_BLOCK_DAYS` | 5 | 临期排除天数 |
| `MIN_SWITCH_EDGE` | 0.1 | 主力切换门槛（10%） |
| `ROLL_COOLDOWN_S` | 300 | 主力切换冷却（秒） |

### 5.7 门禁检查点

```powershell
# Phase 0 完成标准
.\scripts\make.ps1 ci-json # 通过
python .\scripts\coverage_gate.py # 核心=100%，总体>=85%
python .\scripts\validate_policy.py --all --strict-scenarios   # 11 条 scenarios PASS
python -c "from src.market import InstrumentCache"             # 导入成功
python -c "from src.market import QuoteCache"                  # 导入成功
python -c "from src.market import UniverseSelector"            # 导入成功
```

### 5.8 交付物清单

- [ ] `src/market/__init__.py`
- [ ] `src/market/instrument_cache.py`
- [ ] `src/market/universe_selector.py`
- [ ] `src/market/subscriber.py`
- [ ] `src/market/quote_cache.py`
- [ ] `src/market/bar_builder.py`
- [ ] `src/market/quality.py`
- [ ] `tests/test_instrument_cache.py`
- [ ] `tests/test_universe_selector.py`
- [ ] `tests/test_quote_cache.py`
- [ ] 11 条 required scenarios 对应测试
- [ ] 门禁全绿

---

## 6. Phase 1：基础设施层

### 6.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 实现 V2 SPEC 第 6、7 章 + 成本模型 |
| **新增目录** | `src/audit/`, `src/cost/`, `src/guardian/` |
| **新增文件** | 15 个 |
| **Required Scenarios** | 29 条 |
| **预计工时** | 骨架 2.5h  / 全量实现 44h |
| **阻塞** | Phase 2, 3, 4, 5 |

### 6.2 文件清单

#### 6.2.1 src/audit/（7 个文件）

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 1 | `src/audit/__init__.py` | - | - | 模块导出 |
| 2 | `src/audit/writer.py` | `audit.writer` | 7.1 | JSONL 事件写入 |
| 3 | `src/audit/decision_log.py` | `audit.decision_log` | 7.1 | DecisionEvent 定义 |
| 4 | `src/audit/order_trail.py` | `audit.order_trail` | 7.1 | OrderStateEvent/ExecEvent/TradeEvent |
| 5 | `src/audit/guardian_log.py` | `audit.guardian_log` | 7.1 | GuardianEvent 定义 |
| 6 | `src/audit/pnl_attribution.py` | `audit.pnl_attribution` | 扩展 | PnL 归因 |
| 7 | `src/audit/replay_verifier.py` | `audit.replay_verifier` | 7.3 | 回放哈希验证 |

#### 6.2.2 src/cost/（2 个文件）

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 8 | `src/cost/__init__.py` | - | - | 模块导出 |
| 9 | `src/cost/estimator.py` | `cost.estimator` | 10 | 手续费/滑点/冲击估计 |

#### 6.2.3 src/guardian/（6 个文件）

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 10 | `src/guardian/__init__.py` | - | - | 模块导出 |
| 11 | `src/guardian/monitor.py` | `guardian.monitor` | 6.2 | 守护主循环 |
| 12 | `src/guardian/state_machine.py` | `guardian.state_machine` | 6.1 | Guardian FSM |
| 13 | `src/guardian/triggers.py` | `guardian.detector` | 6.2 | 异常检测 |
| 14 | `src/guardian/actions.py` | `guardian.actions` | 6.3 | 动作执行 |
| 15 | `src/guardian/recovery.py` | `guardian.recovery` | 6.4 | 冷启动恢复 |

### 6.3 Required Scenarios

#### Guardian Scenarios（10 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 1 | `GUARD.FSM.TRANSITIONS` | guardian.state_machine | 状态机转移覆盖 |
| 2 | `GUARD.DETECT.QUOTE_STALE` | guardian.detector | 行情 stale 检测 |
| 3 | `GUARD.DETECT.ORDER_STUCK` | guardian.detector | 订单卡住检测 |
| 4 | `GUARD.DETECT.POSITION_DRIFT` | guardian.detector | 持仓漂移检测 |
| 5 | `GUARD.DETECT.LEG_IMBALANCE` | guardian.detector | 腿不平衡检测 |
| 6 | `GUARD.ACTION.SET_MODE` | guardian.actions | set_mode 动作 |
| 7 | `GUARD.ACTION. CANCEL_ALL` | guardian.actions | cancel_all 动作 |
| 8 | `GUARD.ACTION. FLATTEN_ALL` | guardian.actions | flatten_all 动作 |
| 9 | `GUARD.RECOVERY.COLD_START` | guardian.recovery | 冷启动恢复 |
| 10 | `GUARD.MODE.REDUCE_ONLY_EFFECT` | guardian.monitor | reduce_only 禁开仓 |

#### Audit Scenarios（5 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 11 | `AUDIT.EVENT.STRUCTURE` | audit.writer | 事件结构完整 |
| 12 | `AUDIT.JSONL.FORMAT` | audit.writer | JSONL 格式正确 |
| 13 | `AUDIT.CORRELATION.RUN_EXEC` | audit.writer | run_id/exec_id 关联 |
| 14 | `REPLAY.DETERMINISTIC. DECISION` | audit.replay_verifier | 决策确定性 |
| 15 | `REPLAY.DETERMINISTIC.GUARDIAN` | audit.replay_verifier | Guardian 确定性 |

#### Cost Scenarios（4 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 16 | `COST.MODEL.FEE_ESTIMATE` | cost.estimator | 手续费估计 |
| 17 | `COST.MODEL.SLIPPAGE_ESTIMATE` | cost.estimator | 滑点估计 |
| 18 | `COST.MODEL. IMPACT_ESTIMATE` | cost.estimator | 市场冲击估计 |
| 19 | `COST.GATE.EDGE_CHECK` | cost.estimator | edge gate 检查 |

#### Platform Universal Scenarios（10 条，来自 v3pro）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 20 | `STRAT.AUDIT.DECISION_EVENT_PRESENT` | audit.decision_log | DecisionEvent 存在 |
| 21 | `STRAT.AUDIT.DECISION_HAS_RUN_ID` | audit.decision_log | 包含 run_id |
| 22 | `STRAT.AUDIT.DECISION_HAS_EXEC_ID` | audit.decision_log | 包含 exec_id |
| 23 | `STRAT.AUDIT.DECISION_HAS_STRATEGY_ID` | audit.decision_log | 包含 strategy_id |
| 24 | `STRAT.AUDIT.DECISION_HAS_VERSION` | audit.decision_log | 包含 version |
| 25 | `STRAT.AUDIT.DECISION_HAS_FEATURE_HASH` | audit.decision_log | 包含 feature_hash |
| 26 | `STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN` | guardian.monitor | REDUCE_ONLY 禁开仓 |
| 27 | `STRAT.DEGRADE.HALTED_OUTPUT_ZERO` | guardian.monitor | HALTED 输出零 |
| 28 | `STRAT.DEGRADE.MODE_TRANSITION_AUDIT` | audit.guardian_log | 模式切换审计 |
| 29 | `AUDIT.PNL.ATTRIBUTION` | audit.pnl_attribution | PnL 归因 |

### 6.4 Guardian 状态机定义

#### 状态枚举

| 状态 | 值 | 说明 |
|------|-----|------|
| INIT | 0 | 初始化中 |
| RUNNING | 1 | 正常运行，允许开仓 |
| REDUCE_ONLY | 2 | 仅允许减仓/平仓 |
| HALTED | 3 | 停止交易，等待人工 |
| MANUAL | 4 | 人工接管 |

#### 状态转移表

| 当前状态 | 事件 | 目标状态 | 条件 |
|----------|------|----------|------|
| INIT | 初始化完成 | RUNNING | 健康检查通过 |
| INIT | 初始化失败 | HALTED | - |
| RUNNING | quote_stale | REDUCE_ONLY | 硬 stale |
| RUNNING | order_stuck | REDUCE_ONLY | 超时未推进 |
| RUNNING | position_drift | HALTED | reconcile 失败 |
| RUNNING | leg_imbalance | REDUCE_ONLY | 裸腿超阈值 |
| REDUCE_ONLY | 恢复正常 | RUNNING | 冷却期结束 + 健康 |
| REDUCE_ONLY | 持续恶化 | HALTED | 多次触发 |
| HALTED | 人工确认 | MANUAL | - |
| MANUAL | 人工恢复 | RUNNING | - |

### 6.5 审计事件结构

#### 必备字段（所有事件）

| 字段 | 类型 | 说明 |
|------|------|------|
| ts | float | 时间戳（Unix epoch） |
| event_type | str | 事件类型 |
| run_id | str | 运行 ID（UUID） |
| exec_id | str | 执行 ID |

#### DecisionEvent 扩展字段

| 字段 | 类型 | 说明 |
|------|------|------|
| strategy_id | str | 策略 ID |
| strategy_version | str | 策略版本 |
| feature_hash | str | 输入特征哈希 |
| target_portfolio | dict | 目标仓位 |

#### OrderStateEvent 扩展字段

| 字段 | 类型 | 说明 |
|------|------|------|
| order_local_id | str | 本地订单 ID |
| order_ref | str | CTP 订单引用 |
| order_sys_id | str | 交易所系统号 |
| state_from | str | 原状态 |
| state_to | str | 目标状态 |
| trigger_event | str | 触发事件 |

#### GuardianEvent 扩展字段

| 字段 | 类型 | 说明 |
|------|------|------|
| mode_from | str | 原模式 |
| mode_to | str | 目标模式 |
| trigger | str | 触发原因 |
| details | dict | 详细信息 |

### 6.6 门禁检查点

```powershell
# Phase 1 完成标准（累计）
.\scripts\make.ps1 ci-json                                     # PASS
python .\scripts\coverage_gate.py                              # core=100%, overall>=85%
python .\scripts\validate_policy.py --all --strict-scenarios   # 40 条 scenarios PASS (11+29)
python -c "from src.audit import AuditWriter"                  # 导入成功
python -c "from src.cost import CostEstimator"                 # 导入成功
python -c "from src.guardian import GuardianMonitor"           # 导入成功
```

### 6.7 交付物清单

- [ ] `src/audit/` 目录（7 个文件）
- [ ] `src/cost/` 目录（2 个文件）
- [ ] `src/guardian/` 目录（6 个文件）
- [ ] 29 条 required scenarios 对应测试
- [ ] 门禁全绿

---

## 7. Phase 2：执行层

### 7.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 实现 V2 SPEC 第 5 章：FSM、AutoOrderEngine、Protection、PairExecutor |
| **新增目录** | `src/execution/auto/`, `src/execution/protection/`, `src/execution/pair/` |
| **新增文件** | 15 个 |
| **Required Scenarios** | 25 条 |
| **预计工时** | 骨架 2.5h / 全量实现 80h |
| **阻塞** | Phase 5 |

### 7.2 文件清单

#### 7.2.1 src/execution/auto/（8 个文件）

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 1 | `src/execution/auto/__init__.py` | - | - | 模块导出 |
| 2 | `src/execution/auto/order_context.py` | `execution.order_context` | 5.1 | 订单标识映射 |
| 3 | `src/execution/auto/state_machine.py` | `execution.fsm` | 5.3 | 订单 FSM |
| 4 | `src/execution/auto/engine.py` | `execution.auto_order_engine` | 5.4 | 自动下单引擎 |
| 5 | `src/execution/auto/timeout.py` | `execution.timeout` | 5.5 | 超时管理 |
| 6 | `src/execution/auto/retry.py` | `execution.retry` | 5.5 | 重试/追价 |
| 7 | `src/execution/auto/exec_context.py` | `execution.exec_context` | 5.6 | 执行上下文 |
| 8 | `src/execution/auto/position_tracker.py` | `execution.position_tracker` | 5.8 | 持仓追踪 |

#### 7.2.2 src/execution/protection/（4 个文件）

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 9 | `src/execution/protection/__init__.py` | - | - | 模块导出 |
| 10 | `src/execution/protection/liquidity.py` | `execution.protection.liquidity` | 5.7 | 流动性保护 |
| 11 | `src/execution/protection/fat_finger.py` | `execution.protection.fat_finger` | 5.7 | 乌龙指保护 |
| 12 | `src/execution/protection/throttle.py` | `execution.protection.throttle` | 5.7 | 频率限制 |

#### 7.2.3 src/execution/pair/（3 个文件）

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 13 | `src/execution/pair/__init__.py` | - | - | 模块导出 |
| 14 | `src/execution/pair/pair_executor.py` | `execution.pair.pair_executor` | 9.1 | 双腿原子执行 |
| 15 | `src/execution/pair/leg_manager.py` | `execution.pair.leg_manager` | 9.1 | 腿不平衡管理 |

### 7.3 Required Scenarios

#### FSM Scenarios（5 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 1 | `EXEC.ID.MAPPING` | execution.order_context | 订单标识映射完整 |
| 2 | `FSM.STRICT. TRANSITIONS` | execution.fsm | 严格模式所有转移 |
| 3 | `FSM.TOLERANT.IDEMPOTENT` | execution.fsm | 容错模式幂等处理 |
| 4 | `FSM.CANCEL_WHILE_FILL` | execution.fsm | 撤单途中成交 |
| 5 | `FSM.STATUS_4_MAPPING` | execution.fsm | OrderStatus='4' 映射 |

#### AutoOrderEngine Scenarios（7 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 6 | `EXEC.ENGINE.PIPELINE` | execution.auto_order_engine | 订单提交管线 |
| 7 | `EXEC.TIMEOUT.ACK` | execution.auto_order_engine | Ack 超时处理 |
| 8 | `EXEC.TIMEOUT.FILL` | execution.auto_order_engine | Fill 超时处理 |
| 9 | `EXEC.CANCEL_REPRICE. TIMEOUT` | execution.auto_order_engine | 追价超时撤单 |
| 10 | `EXEC.PARTIAL. REPRICE` | execution.auto_order_engine | 部分成交追价 |
| 11 | `EXEC.RETRY.BACKOFF` | execution.retry | 重试指数退避 |
| 12 | `EXEC.CONTEXT.TRACKING` | execution.exec_context | ExecContext 追踪 |

#### Protection Scenarios（4 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 13 | `EXEC.PROTECTION.LIQUIDITY` | execution.protection.liquidity | 流动性保护 |
| 14 | `EXEC.PROTECTION. FATFINGER` | execution.protection.fat_finger | 胖手指保护 |
| 15 | `EXEC.PROTECTION.THROTTLE` | execution.protection.throttle | 节流保护 |
| 16 | `EXEC.PROTECTION.AUDIT` | execution.protection | 保护拒单审计 |

#### PositionTracker Scenarios（4 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 17 | `POS.TRACKER. TRADE_DRIVEN` | execution.position_tracker | trade-driven 更新 |
| 18 | `POS.RECONCILE.PERIODIC` | execution.position_tracker | 定期对账 |
| 19 | `POS.RECONCILE.AFTER_DISCONNECT` | execution.position_tracker | 断连后对账 |
| 20 | `POS.RECONCILE.FAIL_ACTION` | execution.position_tracker | 对账失败动作 |

#### PairExecutor Scenarios（5 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 21 | `PAIR.EXECUTOR. ATOMIC` | execution.pair.pair_executor | 双腿原子性 |
| 22 | `PAIR.ROLLBACK.ON_LEG_FAIL` | execution.pair.pair_executor | 单腿失败回滚 |
| 23 | `PAIR.AUTOHEDGE.DELTA_NEUTRAL` | execution.pair.pair_executor | 自动对冲 |
| 24 | `PAIR.IMBALANCE.DETECT` | execution.pair.leg_manager | 腿不平衡检测 |
| 25 | `PAIR.BREAKER.STOP_Z` | execution.pair.pair_executor | 止损熔断 |

### 7.4 订单状态机定义

#### 订单状态枚举

| 状态 | 说明 | 终态 |
|------|------|------|
| CREATED | 已创建，未提交 | 否 |
| SUBMITTING | 提交中，等待 ack | 否 |
| PENDING | 已报，等待成交 | 否 |
| PARTIAL_FILLED | 部分成交 | 否 |
| CANCEL_SUBMITTING | 撤单提交中 | 否 |
| QUERYING | 查询中（超时后） | 否 |
| RETRY_PENDING | 等待重试 | 否 |
| CHASE_PENDING | 等待追价 | 否 |
| FILLED | 全部成交 | 是 |
| CANCELLED | 已撤单 | 是 |
| PARTIAL_CANCELLED | 部分成交已撤 | 是 |
| CANCEL_REJECTED | 撤单被拒 | 是 |
| REJECTED | 报单被拒 | 是 |
| ERROR | 错误 | 是 |

#### 关键转移规则

| 规则 | 说明 |
|------|------|
| 撤单途中成交 | `CANCEL_SUBMITTING + RTN_FILLED → FILLED` |
| OrderStatus='4' 无成交 | `→ ERROR + reduce-only` |
| OrderStatus='4' 有成交 | `→ PARTIAL_CANCELLED` |
| 终态后事件 | `ignore + log`（tolerant 模式） |
| 重复事件 | `ignore + log`（tolerant 模式） |

### 7.5 订单标识映射

| 标识 | 来源 | 用途 |
|------|------|------|
| local_id | 系统生成（UUID） | 内部主键、audit 关联 |
| order_ref | place_order ack | 撤单（优先级 2） |
| order_sys_id | OnRtnOrder | 撤单（优先级 1）、查询 |
| front_id | 连接时获取 | CTP 会话标识 |
| session_id | 连接时获取 | CTP 会话标识 |

### 7.6 Protection 配置项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LIQ_MAX_SPREAD_TICKS` | 5 | 最大价差（tick 数） |
| `LIQ_MIN_BIDASK_VOL` | 10 | 最小盘口量 |
| `FATFINGER_MAX_QTY` | 100 | 单笔最大手数 |
| `FATFINGER_MAX_NOTIONAL` | 1000000 | 单笔最大名义 |
| `FATFINGER_MAX_PRICE_DEV` | 0.05 | 价格偏离上限（5%） |
| `THROTTLE_MAX_ORDERS_PER_MIN` | 60 | 全局每分钟最大订单数 |
| `THROTTLE_MAX_ORDERS_PER_MIN_PER_SYMBOL` | 10 | 每品种每分钟最大订单数 |
| `THROTTLE_MIN_INTERVAL_S` | 1.0 | 最小调仓间隔 |

### 7.7 门禁检查点

```powershell
# Phase 2 完成标准（累计）
.\scripts\make.ps1 ci-json # 通过
python .\scripts\coverage_gate.py # 核心=100%，总体>=85%
python .\scripts\validate_policy.py --all --strict-scenarios   # 65 条 scenarios PASS (40+25)
.\scripts\make.ps1 replay-json                                 # PASS
python .\scripts\validate_policy.py --strict-scenarios         # replay 产物校验 PASS
python -c "from src.execution.auto import AutoOrderEngine"     # 导入成功
python -c "from src.execution.protection import LiquidityGate" # 导入成功
python -c "from src.execution.pair import PairExecutor"        # 导入成功
```

### 7.8 交付物清单

- [ ] `src/execution/auto/` 目录（8 个文件）
- [ ] `src/execution/protection/` 目录（4 个文件）
- [ ] `src/execution/pair/` 目录（3 个文件）
- [ ] 25 条 required scenarios 对应测试
- [ ] replay-json 门禁通过
- [ ] 门禁全绿

---

## 8. Phase 3：策略层补全

### 8.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 实现降级框架 + 跨期套利策略 |
| **新增文件** | 4 个 |
| **Required Scenarios** | 12 条 |
| **预计工时** | 骨架 最高命令：必须用3小时精雕细琢！/ 全量实现 36h |
| **阻塞** | Phase 5 |

### 8.2 文件清单

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 1 | `src/strategy/fallback.py` | `strategy.fallback` | 8.3 | 降级框架 |
| 2 | `src/strategy/calendar_arb/__init__.py` | - | - | 模块导出 |
| 3 | `src/strategy/calendar_arb/strategy.py` | `strategy.calendar_arb` | 9.2 | 套利主策略 |
| 4 | `src/strategy/calendar_arb/kalman_beta.py` | `strategy.calendar_arb.kalman_beta` | 9.2 | Kalman 滤波 |

### 8.3 Required Scenarios

#### Fallback Scenarios（3 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 1 | `STRAT.FALLBACK.ON_EXCEPTION` | strategy.fallback | 异常降级 |
| 2 | `STRAT.FALLBACK.ON_TIMEOUT` | strategy.fallback | 超时降级 |
| 3 | `STRAT.FALLBACK. CHAIN_DEFINED` | strategy.fallback | 链式定义 |

#### Calendar Arb Scenarios（9 条）

| 序号 | rule_id | component | 描述 |
|------|---------|-----------|------|
| 4 | `ARB.LEGS.FIXED_NEAR_FAR` | strategy.calendar_arb | 近/远月腿固定 |
| 5 | `ARB.KALMAN.BETA_ESTIMATE` | strategy.calendar_arb.kalman_beta | Kalman 估计 beta |
| 6 | `ARB.KALMAN. RESIDUAL_ZSCORE` | strategy.calendar_arb.kalman_beta | 残差 z-score |
| 7 | `ARB.KALMAN. BETA_BOUND` | strategy.calendar_arb.kalman_beta | beta 边界检查 |
| 8 | `ARB.SIGNAL.HALF_LIFE_GATE` | strategy.calendar_arb | 半衰期过滤 |
| 9 | `ARB.SIGNAL.STOP_Z_BREAKER` | strategy.calendar_arb | z-score 止损 |
| 10 | `ARB.SIGNAL.EXPIRY_GATE` | strategy.calendar_arb | 临近到期禁开 |
| 11 | `ARB.SIGNAL.CORRELATION_BREAK` | strategy.calendar_arb | 相关性崩溃暂停 |
| 12 | `ARB.COST.ENTRY_GATE` | strategy.calendar_arb | 入场成本门槛 |

### 8.4 降级链定义

| 策略 | 降级目标 | 最终兜底 |
|------|----------|----------|
| top_tier | ensemble_moe | simple_ai |
| dl_torch | linear_ai | simple_ai |
| ensemble_moe | linear_ai | simple_ai |
| linear_ai | simple_ai | simple_ai |
| simple_ai | - | （自身兜底） |
| calendar_arb | top_tier | simple_ai |

### 8.5 套利信号逻辑

| 条件 | 信号 | 动作 |
|------|------|------|
| `z > entry_z` (如 2.5) | 价差过大 | 做空价差：卖近买远 |
| `z < -entry_z` | 价差过小 | 做多价差：买近卖远 |
| `abs(z) < exit_z` (如 0.5) | 回归 | 平仓 |
| `abs(z) > stop_z` (如 5~6) | 异常 | 止损 + 冷却 |
| `half_life > max_half_life` | 不回归 | 不开仓 |
| `days_to_expiry < N` | 临期 | reduce-only |
| `rolling_corr < threshold` | 相关性崩溃 | 暂停策略 |

### 8.6 门禁检查点

```powershell
# Phase 3 完成标准（累计）
。\scripts\make.ps1 ci-json # 通过
python .\scripts\coverage_gate.py                              # core=100%, overall>=85%
python .\scripts\validate
## 9. Phase 4：回放验证

### 9.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 实现 V2 SPEC 7.3：回放一致性验证 |
| **新增文件** | 1 个 |
| **Required Scenarios** | 2 条 |
| **预计工时** | 骨架 0.5h / 全量实现 8h |
| **阻塞** | Phase 5 |

### 9.2 文件清单

| 序号 | 文件路径 | component | V2 SPEC | 职责 |
|------|----------|-----------|---------|------|
| 1 | `src/replay/verifier.py` | `replay.verifier` | 7.3 | 回放哈希验证、事件序列比对 |

### 9.3 Required Scenarios

| 序号 | rule_id | component | 描述 | category |
|------|---------|-----------|------|----------|
| 1 | `REPLAY.DETERMINISTIC. DECISION` | replay.verifier | 同一输入产生相同 DecisionEvent 序列 | replay |
| 2 | `REPLAY.DETERMINISTIC. GUARDIAN` | replay.verifier | 同一输入产生相同 GuardianEvent 序列 | replay |

### 9.4 接口定义

| 方法 | 签名 | 说明 |
|------|------|------|
| `verify_decision_sequence` | `(events_a:  list, events_b:  list) -> VerifyResult` | 比对决策事件序列 |
| `verify_guardian_sequence` | `(events_a: list, events_b: list) -> VerifyResult` | 比对 Guardian 事件序列 |
| `compute_hash` | `(events: list) -> str` | 计算事件序列哈希 |
| `load_events_from_jsonl` | `(path: Path) -> list[Event]` | 从 JSONL 加载事件 |

### 9.5 验证规则

| 规则 | 说明 |
|------|------|
| 字段忽略 | ts（时间戳）允许微小差异（< 1ms） |
| 顺序敏感 | 事件顺序必须完全一致 |
| 哈希算法 | SHA256（去除 ts 字段后） |
| 失败输出 | 第一个不匹配的事件索引 + diff |

### 9.6 门禁检查点

```powershell
# Phase 4 完成标准（累计）
.\scripts\make.ps1 ci-json                                     # PASS
python .\scripts\coverage_gate.py                              # core=100%, overall>=85%
python .\scripts\validate_policy.py --all --strict-scenarios   # 79 条 scenarios PASS (77+2)
.\scripts\make.ps1 replay-json                                 # PASS
python .\scripts\validate_policy.py --strict-scenarios         # 回放一致性验证 PASS
python -c "from src.replay.verifier import ReplayVerifier"     # 导入成功
```

### 9.7 交付物清单

- [ ] `src/replay/verifier.py`
- [ ] `tests/test_replay_verifier.py`
- [ ] 2 条 required scenarios 对应测试
- [ ] 门禁全绿

---

## 10. Phase 5：集成与演练

### 10.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 全链路集成、故障注入、冷启动演练 |
| **新增文件** | 0 个（仅测试和文档） |
| **Required Scenarios** | 0 条（验收性演练） |
| **预计工时** | 24h |
| **阻塞** | Phase 6 |

### 10.2 集成测试矩阵

| 测试类型 | 测试内容 | 输入 | 预期结果 | 通过标准 |
|----------|----------|------|----------|----------|
| 端到端回放 | 1 天 tick 数据完整回放 | tick JSONL | DecisionEvent 序列 | 哈希一致 |
| 策略切换 | 运行中切换策略 | 策略名变更 | 无中断、audit 记录 | 事件完整 |
| 主力切换 | 模拟 roll 事件 | universe 变更 | 订阅更新、bars 连续 | 无断点 |

### 10.3 故障注入测试矩阵

| 故障类型 | 注入方式 | 预期响应 | 验证方法 |
|----------|----------|----------|----------|
| 行情断流 | mock quote_cache 返回 stale | Guardian → REDUCE_ONLY | GuardianEvent 存在 |
| 订单超时 | mock broker 不返回 ack | 自动撤单 + OrderTimeoutEvent | audit 验证 |
| 撤单无响应 | mock cancel 不返回 | HALTED + 告警 | Guardian 状态 |
| 持仓漂移 | mock reconcile 返回 mismatch | HALTED + cancel_all | PositionReconcileEvent |
| 单腿失败 | mock 一腿成交一腿拒绝 | rollback/auto-hedge | PairExecutor 状态 |
| 网络断连 | mock broker disconnect | 重连 + reconcile | 日志 + 状态恢复 |

### 10.4 冷启动演练流程

```text
┌─────────────────────────────────────────────────────────────────┐
│                     冷启动演练流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: 模拟崩溃                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  kill -9 <pid>  或  模拟断电                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  Step 2: 重启进程                                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  python -m src.app.live_entry                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  Step 3: Guardian 自动恢复                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  3. 1 cancel_all() - 撤销所有未完成订单                    │   │
│  │  3.2 query_positions() - 同步柜台持仓                     │   │
│  │  3.3 reconcile() - 对账                                   │   │
│  │  3.4 set_mode(REDUCE_ONLY) - 进入冷却期                   │   │
│  │  3.5 等待 REDUCE_ONLY_COOLDOWN_S                          │   │
│  │  3.6 健康检查通过后 set_mode(RUNNING)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                  │
│                              ▼                                  │
│  Step 4: 验证                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  - 持仓与柜台一致                                         │   │
│  │  - 无未处理订单                                           │   │
│  │  - Guardian 状态 = RUNNING                                │   │
│  │  - audit 记录完整                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.5 演练检查清单

| 检查项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| 未完成订单全撤 | 查询柜台订单 | 无活动订单 |
| 持仓同步正确 | 对比 PositionTracker 与柜台 | 完全一致 |
| 冷却期生效 | 尝试开仓 | 被拒绝 |
| 恢复后正常 | 冷却期后尝试交易 | 成功 |
| audit 完整 | 检查 JSONL | GuardianEvent 记录恢复过程 |
| 无资金损失 | 对比前后权益 | 差异 < 0.1% |

### 10.6 门禁检查点

```powershell
# Phase 5 完成标准
.\scripts\make.ps1 ci-json                                     # PASS
.\scripts\make.ps1 replay-json                                 # PASS
.\scripts\make.ps1 sim-json                                    # PASS
python .\scripts\validate_policy.py --all --strict-scenarios   # 全部 scenarios PASS
# 故障注入测试全绿
# 冷启动演练通过
```

### 10.7 交付物清单

- [ ] `tests/integration/test_e2e_replay. py`
- [ ] `tests/integration/test_fault_injection.py`
- [ ] `tests/integration/test_cold_start.py`
- [ ] `docs/COLD_START_RUNBOOK.md`
- [ ] 集成测试全绿
- [ ] 故障注入测试全绿
- [ ] 冷启动演练文档签字

---

## 11. Phase 6：B-Models 策略升级

### 11.1 概述

| 项目 | 值 |
|------|-----|
| **目标** | 实现 v3pro_required_scenarios. yml 中 strategy_specific_required |
| **新增文件** | 0 个（升级现有策略） |
| **Required Scenarios** | 22 条 |
| **预计工时** | 36h |  最高命令：策略层必须要精雕细琢！
| **可并行** | 与 Phase 3, 4, 5 并行 |

### 11.2 策略升级矩阵

| 策略 | 升级内容 | 场景数 | 依赖 | 工时 |
|------|----------|--------|------|------|
| simple_ai | 信号有界、输入容错、stale 稳定 | 3 | Phase 1 | 4h |
| linear_ai | 因子权重稳定、暴露受限、stale 稳定 | 3 | Phase 1 | 4h |
| ensemble_moe | 输出平滑、专家冲突、门控权重、版本审计、状态检测 | 5 | Phase 1 | 8h |
| dl_torch | 推理降级、模型版本、seed 确定、输入标准化、输出裁剪、显存释放 | 6 | Phase 1 + 3 | 12h |
| top_tier | 成本门槛、换手限制、抖动抑制、风险平价、趋势审计 | 5 | Phase 1 | 8h |

### 11.3 Required Scenarios

#### simple_ai（3 条）

| 序号 | rule_id | 描述 |
|------|---------|------|
| 1 | `SIMPLE.OUTPUT. BOUNDED` | 输出信号有界 [-1, 1] |
| 2 | `SIMPLE.INPUT.NEVER_CRASH` | 任意输入不崩溃 |
| 3 | `BASELINE.STABLE.STALE_INPUT` | stale 输入返回稳定值 |

#### linear_ai（3 条）

| 序号 | rule_id | 描述 |
|------|---------|------|
| 4 | `LINEAR.FACTOR.WEIGHT_STABLE` | 因子权重稳定 |
| 5 | `LINEAR.FACTOR.EXPOSURE_LIMIT` | 暴露受限 |
| 6 | `BASELINE.STABLE. STALE_INPUT` | stale 输入返回稳定值 |

#### ensemble_moe（5 条）

| 序号 | rule_id | 描述 |
|------|---------|------|
| 7 | `MOE.OUTPUT. SMOOTHING` | 输出平滑（EWMA） |
| 8 | `MOE.EXPERT.CONFLICT_CONTROL` | 专家冲突抑制 |
| 9 | `MOE.GATING.WEIGHT_VALID` | 门控权重有效 [0,1] 且 sum=1 |
| 10 | `MOE.EXPERT.VERSION_AUDIT` | 专家版本审计 |
| 11 | `MOE.REGIME.DETECTION` | 市场状态检测 |

#### dl_torch（6 条）

| 序号 | rule_id | 描述 |
|------|---------|------|
| 12 | `DL.INFERENCE.FAIL_FALLBACK` | 推理失败降级 |
| 13 | `DL.MODEL.VERSION_AUDIT` | 模型版本审计 |
| 14 | `DL.SEED.DETERMINISTIC` | seed 确定性 |
| 15 | `DL.INPUT. NORMALIZE` | 输入标准化 |
| 16 | `DL.OUTPUT.CLAMP` | 输出裁剪 |
| 17 | `DL.MEMORY.CLEANUP` | 显存释放 |

#### top_tier（5 条）

| 序号 | rule_id | 描述 |
|------|---------|------|
| 18 | `TOPTIER.COST.GATE` | 成本门槛检查 |
| 19 | `TOPTIER.TURNOVER.LIMIT` | 换手限制 |
| 20 | `TOPTIER.JITTER.SUPPRESSION` | 抖动抑制 |
| 21 | `TOPTIER.RISK.PARITY_VALID` | 风险平价有效 |
| 22 | `TOPTIER.TREND.SIGNAL_AUDIT` | 趋势信号审计 |

### 11.4 降级链配置

```yaml
# src/strategy/fallback_config.yml
fallback_chains:
  top_tier:
    - ensemble_moe
    - linear_ai
- 简单_ai
  
  dl_torch: 
    - linear_ai
- 简单_ai
  
  ensemble_moe: 
    - linear_ai
- 简单_ai
  
  linear_ai:
- 简单_ai
  
  simple_ai:  []  # 自身兜底
  
  calendar_arb: 
    - top_tier
- 简单_ai

default_fallback:  simple_ai
```

### 11.5 门禁检查点

```powershell
# Phase 6 完成标准
.\scripts\make.ps1 ci-json                                     # PASS
python .\scripts\coverage_gate.py                              # core=100%, overall>=85%
python .\scripts\validate_policy.py --all --strict-scenarios   # 全部 101 条 scenarios PASS
```

### 11.6 交付物清单

- [ ] simple_ai 升级（3 条场景）
- [ ] linear_ai 升级（3 条场景）
- [ ] ensemble_moe 升级（5 条场景）
- [ ] dl_torch 升级（6 条场景）
- [ ] top_tier 升级（5 条场景）
- [ ] fallback_config.yml
- [ ] 22 条 required scenarios 对应测试
- [ ] 门禁全绿

---

## 12. 文件清单汇总

### 12.1 按 Phase 统计

| Phase | 目录 | 新增文件数 |
|-------|------|-----------|
| Phase 0 | `src/market/` | 7 |
| Phase 1 | `src/audit/` | 7 |
| Phase 1 | `src/cost/` | 2 |
| Phase 1 | `src/guardian/` | 6 |
| Phase 2 | `src/execution/auto/` | 8 |
| Phase 2 | `src/execution/protection/` | 4 |
| Phase 2 | `src/execution/pair/` | 3 |
| Phase 3 | `src/strategy/fallback.py` | 1 |
| Phase 3 | `src/strategy/calendar_arb/` | 3 |
| Phase 4 | `src/replay/verifier.py` | 1 |
| **总计** | **10 个目录** | **42 个文件** |

### 12.2 完整文件路径列表

```text
src/
├── market/                              # Phase 0: 7 files
│   ├── __init__.py
│   ├── instrument_cache.py
│   ├── universe_selector.py
│   ├── subscriber.py
│   ├── quote_cache.py
│   ├── bar_builder.py
│   └── quality.py
│
├── audit/                               # Phase 1: 7 files
│   ├── __init__.py
│   ├── writer.py
│   ├── decision_log.py
│   ├── order_trail.py
│   ├── guardian_log.py
│   ├── pnl_attribution.py
│   └── replay_verifier.py
│
├── cost/                                # Phase 1: 2 files
│   ├── __init__.py
│   └── estimator.py
│
├── guardian/                            # Phase 1: 6 files
│   ├── __init__.py
│   ├── monitor.py
│   ├── state_machine.py
│   ├── triggers.py
│   ├── actions.py
│   └── recovery.py
│
├── execution/
│   ├── auto/                            # Phase 2: 8 files
│   │   ├── __init__.py
│   │   ├── order_context.py
│   │   ├── state_machine.py
│   │   ├── engine.py
│   │   ├── timeout.py
│   │   ├── retry.py
│   │   ├── exec_context.py
│   │   └── position_tracker.py
│   │
│   ├── protection/                      # Phase 2: 4 files
│   │   ├── __init__.py
│   │   ├── liquidity.py
│   │   ├── fat_finger.py
│   │   └── throttle.py
│   │
│   └── pair/                            # Phase 2: 3 files
│       ├── __init__.py
│       ├── pair_executor.py
│       └── leg_manager.py
│
├── strategy/
│   ├── fallback.py                      # Phase 3: 1 file
│   │
│   └── calendar_arb/                    # Phase 3: 3 files
│       ├── __init__.py
│       ├── strategy.py
│       └── kalman_beta.py
│
└── replay/
    └── verifier.py                      # Phase 4: 1 file
```

---

## 13. 场景矩阵汇总

### 13.1 按 Phase 统计

| Phase | A/B 轨 | 场景数 | 累计 |
|-------|--------|--------|------|
| Phase 0 | A | 11 | 11 |
| Phase 1 | A | 29 | 40 |
| Phase 2 | A | 25 | 65 |
| Phase 3 | B | 12 | 77 |
| Phase 4 | A | 2 | 79 |
| Phase 6 | B | 22 | 101 |
| **总计** | - | **101** | - |

### 13.2 按模块统计

| 模块 | 场景数 | 说明 |
|------|--------|------|
| market | 11 | 行情层 |
| guardian | 10 | 守护层 |
| audit | 8 | 审计层 |
| cost | 4 | 成本层 |
| execution. fsm | 5 | 订单状态机 |
| execution.engine | 7 | 自动下单引擎 |
| execution.protection | 4 | 执行保护 |
| execution.position | 4 | 持仓追踪 |
| execution.pair | 5 | 双腿执行 |
| strategy.fallback | 3 | 降级框架 |
| strategy.calendar_arb | 9 | 套利策略 |
| strategy.simple_ai | 3 | 简单策略 |
| strategy.linear_ai | 3 | 线性策略 |
| strategy.ensemble_moe | 5 | MoE 策略 |
| strategy.dl_torch | 6 | 深度学习策略 |
| strategy.top_tier | 5 | 顶级策略 |
| replay | 2 | 回放验证 |
| platform_universal | 6 | 平台通用 |
| **总计** | **101** | - |

### 13.3 完整场景列表

```yaml
# A 轨场景（67 条）
a_platform_scenarios:
  # Phase 0: market (11)
  - INST.CACHE.LOAD
  - INST.CACHE. PERSIST
  - UNIV.DOMINANT.BASIC
  - UNIV.SUBDOMINANT.PAIRING
  - UNIV.ROLL.COOLDOWN
  - UNIV.EXPIRY.GATE
  - MKT.SUBSCRIBER.DIFF_UPDATE
  - MKT.STALE.SOFT
  - MKT.STALE. HARD
  - MKT.CONTINUITY.BARS
  - MKT.QUALITY.OUTLIER
  
  # Phase 1: guardian (10)
  - GUARD.FSM.TRANSITIONS
  - GUARD.DETECT.QUOTE_STALE
  - GUARD.DETECT. ORDER_STUCK
  - GUARD.DETECT. POSITION_DRIFT
  - GUARD.DETECT.LEG_IMBALANCE
  - GUARD.ACTION.SET_MODE
  - GUARD.ACTION.CANCEL_ALL
  - GUARD.ACTION.FLATTEN_ALL
  - GUARD.RECOVERY.COLD_START
  - GUARD.MODE.REDUCE_ONLY_EFFECT
  
  # Phase 1: audit (5)
  - AUDIT.EVENT.STRUCTURE
  - AUDIT.JSONL.FORMAT
  - AUDIT.CORRELATION.RUN_EXEC
  - REPLAY.DETERMINISTIC.DECISION
  - REPLAY.DETERMINISTIC. GUARDIAN
  
  # Phase 1: cost (4)
  - COST.MODEL.FEE_ESTIMATE
  - COST.MODEL.SLIPPAGE_ESTIMATE
  - COST.MODEL. IMPACT_ESTIMATE
  - COST.GATE.EDGE_CHECK
  
  # Phase 1: platform_universal (10)
  - STRAT.AUDIT.DECISION_EVENT_PRESENT
  - STRAT.AUDIT.DECISION_HAS_RUN_ID
  - STRAT.AUDIT.DECISION_HAS_EXEC_ID
  - STRAT.AUDIT.DECISION_HAS_STRATEGY_ID
  - STRAT.AUDIT.DECISION_HAS_VERSION
  - STRAT.AUDIT.DECISION_HAS_FEATURE_HASH
  - STRAT.DEGRADE.REDUCE_ONLY_NO_OPEN
  - STRAT.DEGRADE. HALTED_OUTPUT_ZERO
  - STRAT.DEGRADE.MODE_TRANSITION_AUDIT
  - AUDIT.PNL.ATTRIBUTION
  
  # Phase 2: fsm (5)
  - EXEC.ID.MAPPING
  - FSM.STRICT. TRANSITIONS
  - FSM.TOLERANT.IDEMPOTENT
  - FSM.CANCEL_WHILE_FILL
  - FSM.STATUS_4_MAPPING
  
  # Phase 2: engine (7)
  - EXEC.ENGINE.PIPELINE
  - EXEC.TIMEOUT.ACK
  - EXEC.TIMEOUT. FILL
  - EXEC.CANCEL_REPRICE. TIMEOUT
  - EXEC.PARTIAL. REPRICE
  - EXEC.RETRY.BACKOFF
  - EXEC.CONTEXT.TRACKING
  
  # Phase 2: protection (4)
  - EXEC.PROTECTION.LIQUIDITY
  - EXEC.PROTECTION. FATFINGER
  - EXEC.PROTECTION. THROTTLE
  - EXEC.PROTECTION.AUDIT
  
  # Phase 2: position (4)
  - POS.TRACKER.TRADE_DRIVEN
  - POS.RECONCILE.PERIODIC
  - POS.RECONCILE. AFTER_DISCONNECT
  - POS.RECONCILE. FAIL_ACTION
  
  # Phase 2: pair (5)
  - PAIR.EXECUTOR. ATOMIC
  - PAIR.ROLLBACK.ON_LEG_FAIL
  - PAIR.AUTOHEDGE.DELTA_NEUTRAL
  - PAIR.IMBALANCE.DETECT
  - PAIR.BREAKER.STOP_Z
  
  # Phase 4: replay (2) - 已在 audit 中计算

# B 轨场景（34 条）
b_models_scenarios:
  # Phase 3: fallback (3)
  - STRAT.FALLBACK.ON_EXCEPTION
  - STRAT.FALLBACK.ON_TIMEOUT
  - STRAT.FALLBACK. CHAIN_DEFINED
  
  # Phase 3: calendar_arb (9)
  - ARB.LEGS.FIXED_NEAR_FAR
  - ARB.KALMAN.BETA_ESTIMATE
  - ARB.KALMAN. RESIDUAL_ZSCORE
  - ARB.KALMAN.BETA_BOUND
  - ARB.SIGNAL.HALF_LIFE_GATE
  - ARB.SIGNAL. STOP_Z_BREAKER
  - ARB.SIGNAL. EXPIRY_GATE
  - ARB.SIGNAL.CORRELATION_BREAK
  - ARB.COST.ENTRY_GATE
  
  # Phase 6: simple_ai (3)
  - SIMPLE.OUTPUT.BOUNDED
  - SIMPLE.INPUT.NEVER_CRASH
  - BASELINE.STABLE. STALE_INPUT
  
  # Phase 6: linear_ai (3)
  - LINEAR.FACTOR.WEIGHT_STABLE
  - LINEAR.FACTOR. EXPOSURE_LIMIT
  - BASELINE.STABLE. STALE_INPUT  # 与 simple_ai 共享
  
  # Phase 6: ensemble_moe (5)
  - MOE.OUTPUT. SMOOTHING
  - MOE.EXPERT.CONFLICT_CONTROL
  - MOE.GATING.WEIGHT_VALID
  - MOE.EXPERT.VERSION_AUDIT
  - MOE.REGIME. DETECTION
  
  # Phase 6: dl_torch (6)
  - DL.INFERENCE. FAIL_FALLBACK
  - DL.MODEL.VERSION_AUDIT
  - DL.SEED.DETERMINISTIC
  - DL.INPUT.NORMALIZE
  - DL.OUTPUT.CLAMP
  - DL.MEMORY. CLEANUP
  
  # Phase 6: top_tier (5)
  - TOPTIER.COST.GATE
  - TOPTIER.TURNOVER.LIMIT
  - TOPTIER.JITTER.SUPPRESSION
  - TOPTIER.RISK. PARITY_VALID
  - TOPTIER.TREND.SIGNAL_AUDIT
```

---

## 14. 工时与里程碑

### 14.1 工时汇总

| Phase | 骨架 | | 全量实现 | 建议模式 |
|-------|------|----------|----------|----------|
| Phase 0 | 3h | 34h | 全量实现 |
| Phase 1 | 2.5h | 44h | 全量实现 |
| Phase 2 | 2.5h | 80h | 全量实现 |
| Phase 3 | 3h | 36h | 全量实现 |
| Phase 4 | 0.5h |8h | 全量实现 |
| Phase 5 | - | 24h | 全量实现 |
| Phase 6 | - | 36h | 全量实现 |
| **总计** | **144h** | **262h** | - |

### 14.2 里程碑时间表

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          里程碑时间表                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Week 1 (Day 1-5)                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  D1: 骨架创建（42 个文件）                                           │   │
│  │  D2-D3: Phase 0 全量实现                                            │   │
│  │  D4-D5: Phase 1 全量实现（audit + cost）                            │   │
│  │  ⬛ Milestone 1: market + audit + cost 门禁通过                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Week 2 (Day 6-10)                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  D6-D7: Phase 1 全量实现（guardian）                                 │   │
│  │  D8-D10: Phase 2 全量实现（auto + protection）                       │   │
│  │  ⬛ Milestone 2: guardian + execution/auto 门禁通过                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Week 3 (Day 11-15)                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  D11-D12: Phase 2 全量实现（pair）                                   │   │
│  │  D13:  Phase 3 全量实现（fallback）                                   │   │
│  │  D14: Phase 3 全量实现（calendar_arb）                               │   │
│  │  D15: Phase 4 全量实现（verifier）                                   │   │
│  │  ⬛ Milestone 3: 全部 A 轨模块门禁通过                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Week 4 (Day 16-20)                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  D16-D18: Phase 5 集成与演练                                         │   │
│  │  D19-D20: Phase 6 策略升级（simple + linear + moe）                  │   │
│  │  ⬛ Milestone 4: 集成演练通过                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Week 5 (Day 21-25)                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  D21-D23: Phase 6 策略升级（dl_torch + top_tier）                    │   │
│  │  D24: 文档完善                                                       │   │
│  │  D25: 最终验收                                                       │   │
│  │  ⬛ Milestone 5: 全部 101 条场景通过                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.3 里程碑定义

| 里程碑 | 日期 | 交付物 | 验收标准 |
|--------|------|--------|----------|
| M1 | Day 5 | Phase 0 + 1 部分 | 22 条场景通过 |
| M2 | Day 10 | Phase 1 + 2 部分 | 50 条场景通过 |
| M3 | Day 15 | Phase 0-4 全部 | 79 条场景通过（A 轨完成） |
| M4 | Day 20 | Phase 5 | 集成演练通过 |
| M5 | Day 25 | Phase 6 | 101 条场景全部通过 |

---

## 15. 验收检查点

### 15.1 导入测试

| 序号 | 命令 | 预期结果 |
|------|------|----------|
| 1 | `python -c "from src.market import InstrumentCache"` | 无报错 |
| 2 | `python -c "from src.market import QuoteCache"` | 无报错 |
| 3 | `python -c "from src.market import UniverseSelector"` | 无报错 |
| 4 | `python -c "from src.audit import AuditWriter"` | 无报错 |
| 5 | `python -c "from src.cost import CostEstimator"` | 无报错 |
| 6 | `python -c "from src.guardian import GuardianMonitor"` | 无报错 |
| 7 | `python -c "from src.execution.auto import AutoOrderEngine"` | 无报错 |
| 8 | `python -c "from src.execution.protection import LiquidityGate"` | 无报错 |
| 9 | `python -c "from src.execution.pair import PairExecutor"` | 无报错 |
| 10 | `python -c "from src.strategy.fallback import FallbackManager"` | 无报错 |
| 11 | `python -c "from src.strategy.calendar_arb import CalendarArbStrategy"` | 无报错 |
| 12 | `python -c "from src.replay.verifier import ReplayVerifier"` | 无报错 |

### 15.2 门禁检查

| 序号 | 命令 | 预期结果 | 失败退出码 |
|------|------|----------|-----------|
| 1 | `ruff check src/` | All checks passed | 2 |
| 2 | `ruff format --check src/` | All files formatted | 2 |
| 3 | `mypy src/` | No errors | 3 |
| 4 | `pytest tests/ -q` | All tests passed | 4 |
| 5 | `python scripts/coverage_gate.py` | core=100%, overall>=85% | 5 |
| 6 | `python scripts/validate_policy.py --all --strict-scenarios` | PASS | 12 |
| 7 | `.\scripts\make.ps1 replay-json` | PASS | 8 |
| 8 | `.\scripts\make.ps1 sim-json` | PASS | 9 |

### 15.3 最终验收清单

| 检查项 | 验证方法 | 通过标准 |
|--------|----------|----------|
| 文件完整 | ls 统计 | 42 个新文件 |
| 场景完整 | validate_policy | 101 条 PASS |
| 覆盖率达标 | coverage_gate | core=100%, overall>=85% |
| CI 通过 | make ci-json | exit 0 |
| Replay 通过 | make replay-json | exit 0 |
| Sim 通过 | make sim-json | exit 0 |
| 锚点更新 | context.md | SHA 更新 |
| 文档完整 | 人工检查 | 无遗漏 |

---

## 16. 风险与缓解

### 16.1 风险矩阵

| 风险 | 可能性 | 影响 | 风险等级 | 缓解措施 |
|------|--------|------|----------|----------|
| 场景矩阵过大（101 条） | 高 | 高 | 🔴 | Phase 分批解锁，先绿前一批再开下一批 |
| 现有 live_guard 与 guardian 冲突 | 中 | 高 | 🟡 | guardian 吸收 live_guard 逻辑，废弃旧模块 |
| CTP 回报语义不明确 | 中 | 高 | 🟡 | 先用 mock 覆盖所有边界，实盘前联调 |
| 锚点漂移 | 中 | 中 | 🟡 | 每次 PR 必须更新 context.md |
| 工时估算偏差 | 高 | 中 | 🟡 | 骨架优先，最小实现交付，迭代补全 |
| 依赖冲突 | 低 | 高 | 🟡 | 严格遵守依赖禁止规则 |
| 测试覆盖不足 | 中 | 中 | 🟡 | 场景驱动，每条场景必须有测试 |
| 集成问题 | 中 | 高 | 🟡 | Phase 5 专门做集成演练 |

### 16.2 缓解措施详述

#### 场景矩阵过大

```text
问题：101 条场景一次性实现不现实
方案：Phase 分批解锁

Phase 0: 先通过 11 条 market 场景
Phase 1: 再通过 29 条 audit/cost/guardian 场景
Phase 2: 再通过 25 条 execution 场景
... 

每个 Phase 完成后做一次门禁检查，确保增量稳定
```

#### live_guard 与 guardian 冲突

```text
问题：现有 src/trading/live_guard. py 与新建 src/guardian/ 功能重叠
方案：迁移重构

Step 1: 在 guardian/ 实现完整功能
Step 2: 将 live_guard. py 中的逻辑迁移到 guardian/
Step 3: live_guard.py 改为 thin wrapper，调用 guardian
Step 4: 废弃 live_guard.py（保留一个版本的兼容）
```

#### CTP 回报语义不明确

```text
问题：OrderStatus='4' 等边界情况语义不清
方案：Mock + 实盘联调

Step 1: 创建 MockBroker，模拟所有可能的回报序列
Step 2: FSM 测试覆盖所有边界
Step 3: 实盘前用 simnow 联调验证
Step 4: 保留 tolerant 模式处理未知情况
```

---

## 17. 模块迁移计划

### 17.1 迁移矩阵

| 现有模块 | 目标模块 | 动作 | 说明 |
|----------|----------|------|------|
| `src/trading/live_guard. py` | `src/guardian/monitor.py` | 重构迁移 | Guardian 吸收 live_guard 功能 |
| `src/execution/order_tracker.py` | `src/execution/auto/position_tracker.py` | 融合 | 避免双真相 |
| `src/execution/flatten_executor.py` | 保留 | 不动 | 作为 guardian. flatten_all 的实现 |
| `src/risk/manager.py` | 保留 | 不动 | guardian 调用 risk |
| `src/strategy/*. py` | 保留 | 升级 | Phase 6 增强 |

### 17.2 迁移步骤

#### live_guard → guardian

```text
Step 1: 分析 live_guard. py 现有功能
- kill_switch 检测
- flatten 触发
- 状态管理

Step 2: 在 guardian/ 实现等价功能
- state_machine. py:  FSM
- triggers.py: 检测逻辑
- actions.py: cancel_all/flatten_all
- monitor. py: 主循环

Step 3: 迁移调用方
- orchestrator.py: 改为调用 GuardianMonitor
- runner.py: 初始化 Guardian

Step 4: 废弃 live_guard.py
- 添加 deprecation warning
- 下个大版本删除
```

#### order_tracker → position_tracker

```text
Step 1: 分析 order_tracker.py 现有功能
- 订单状态追踪
- 持仓计算

Step 2: 职责分离
- 订单状态 → execution/auto/state_machine. py
- 持仓追踪 → execution/auto/position_tracker. py

Step 3: 迁移调用方
- 替换所有 import order_tracker

Step 4: 废弃 order_tracker.py
- 或保留为 thin wrapper
```

---

## 18. 配置规范

### 18.1 配置分类

| 类别 | 前缀 | 说明 |
|------|------|------|
| 行情 | `MKT_` / `QUOTE_` | 行情相关配置 |
| 执行 | `EXEC_` / `AUTO_` | 执行相关配置 |
| 保护 | `LIQ_` / `FATFINGER_` / `THROTTLE_` | 保护相关配置 |
| Guardian | `GUARD_` / `REDUCE_ONLY_` | Guardian 相关配置 |
| 对账 | `RECONCILE_` | 对账相关配置 |
| 套利 | `ARB_` | 套利相关配置 |

### 18.2 完整配置清单

```python
# src/config. py 扩展

@dataclass(frozen=True)
class MarketConfig:
    """行情配置."""
    QUOTE_STALE_MS: float = 3000. 0
    QUOTE_HARD_STALE_MS: float = 10000.0
    EXPIRY_BLOCK_DAYS: int = 5
    MIN_SWITCH_EDGE:  float = 0.1
    ROLL_COOLDOWN_S: float = 300.0


@dataclass(frozen=True)
class ExecutionConfig: 
    """执行配置."""
    AUTO_ORDER_TIMEOUT_ACK_S: float = 5.0
    AUTO_ORDER_TIMEOUT_FILL_S: float = 30.0
    AUTO_ORDER_TIMEOUT_CANCEL_S: float = 10.0
    AUTO_ORDER_MAX_RETRY:  int = 3
    REPRICE_MODE:  str = "to_best"  # to_best | to_best_plus_tick | to_cross


@dataclass(frozen=True)
class ProtectionConfig:
    """保护配置."""
    LIQ_MAX_SPREAD_TICKS: int = 5
    LIQ_MIN_BIDASK_VOL: int = 10
    FATFINGER_MAX_QTY: int = 100
    FATFINGER_MAX_NOTIONAL: float = 1000000.0
    FATFINGER_MAX_PRICE_DEV: float = 0.05
    THROTTLE_MAX_ORDERS_PER_MIN: int = 60
    THROTTLE_MAX_ORDERS_PER_MIN_PER_SYMBOL: int = 10
    THROTTLE_MIN_INTERVAL_S: float = 1.0


@dataclass(frozen=True)
class GuardianConfig: 
    """Guardian 配置."""
    REDUCE_ONLY_COOLDOWN_S: float = 300.0
    RECONCILE_INTERVAL_S: float = 60.0
    ORDER_STUCK_TIMEOUT_S: float = 120.0
    LEG_IMBALANCE_THRESHOLD:  int = 10


@dataclass(frozen=True)
class ArbConfig: 
    """套利配置."""
    ARB_ENTRY_Z:  float = 2.5
    ARB_EXIT_Z: float = 0.5
    ARB_STOP_Z: float = 5.0
    ARB_MAX_HALF_LIFE_DAYS: int = 20
    ARB_MIN_CORRELATION: float = 0.7
    ARB_COOLDOWN_AFTER_STOP_S: float = 600.0
```

---

## 19. 审计事件规范

### 19.1 事件类型枚举

```python
class AuditEventType(Enum):
    # 决策事件
    DECISION = "decision"
    
    # 执行事件
    EXEC_START = "exec_start"
    EXEC_END = "exec_end"
    
    # 订单事件
    ORDER_CREATED = "order_created"
    ORDER_SUBMITTED = "order_submitted"
    ORDER_ACCEPTED = "order_accepted"
    ORDER_FILLED = "order_filled"
    ORDER_PARTIAL = "order_partial"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    ORDER_TIMEOUT = "order_timeout"
    ORDER_RETRY = "order_retry"
    ORDER_ERROR = "order_error"
    
    # 成交事件
    TRADE = "trade"
    
    # 持仓事件
    POSITION_UPDATE = "position_update"
    POSITION_RECONCILE = "position_reconcile"
    POSITION_MISMATCH = "position_mismatch"
    
    # Guardian 事件
    GUARDIAN_MODE_CHANGE = "guardian_mode_change"
    GUARDIAN_TRIGGER = "guardian_trigger"
    GUARDIAN_ACTION = "guardian_action"
    GUARDIAN_RECOVERY = "guardian_recovery"
    
    # 保护事件
    PROTECTION_REJECT = "protection_reject"
```

### 19.2 JSONL 格式规范

```json
{"ts": 1734220800.123, "event_type": "decision", "run_id": "uuid", "exec_id": "exec_001", "strategy_id": "top_tier", "version": "1.0.0", "feature_hash": "abc123", "target":  {"AO": 1, "SA": -1}}
{"ts": 1734220800.456, "event_type":  "order_created", "run_id": "uuid", "exec_id": "exec_001", "order_local_id": "ord_001", "symbol": "AO2501", "direction": "BUY", "qty": 10, "price": 4500.0}
{"ts": 1734220800.789, "event_type": "order_submitted", "run_id": "uuid", "exec_id":  "exec_001", "order_local_id": "ord_001", "order_ref": "ref_001"}
{"ts": 1734220801.123, "event_type": "order_accepted", "run_id": "uuid", "exec_id": "exec_001", "order_local_id": "ord_001", "order_sys_id": "sys_001", "state_from": "SUBMITTING", "state_to": "PENDING"}
{"ts": 1734220802.456, "event_type": "trade", "run_id": "uuid", "exec_id": "exec_001", "order_local_id": "ord_001", "trade_id": "trade_001", "volume": 5, "price": 4500.0}
{"ts": 1734220803.789, "event_type": "order_filled", "run_id": "uuid", "exec_id":  "exec_001", "order_local_id": "ord_001", "state_from": "PARTIAL_FILLED", "state_to": "FILLED", "filled_qty": 10, "avg_price": 4500.0}
{"ts": 1734220900.000, "event_type": "guardian_mode_change", "run_id":  "uuid", "mode_from": "RUNNING", "mode_to": "REDUCE_ONLY", "trigger": "quote_stale", "details": {"symbol": "AO2501", "stale_ms": 15000}}
```

### 19.3 文件路径规范

```text
artifacts/
└── audit/
    ├── 2025-12-15/
    │   ├── decision_20251215.jsonl
    │   ├── order_20251215.jsonl
    │   ├── trade_20251215.jsonl
    │   └── guardian_20251215.jsonl
    └── 2025-12-16/
        └── ... 
```

---

## 20. 失败模式与应对表

### 20.1 FMEA 矩阵

| ID | 失败模式 | 典型症状 | 严重度 | 发生率 | 检测 | RPN | 默认动作 | 审计事件 |
|----|----------|----------|--------|--------|------|-----|----------|----------|
| F01 | 行情断流 | quote ts 过期 | 高 | 中 | quote_stale | 🔴 | REDUCE_ONLY | guardian_trigger |
| F02 | 卡单 | FSM 不推进 | 高 | 低 | order_stuck | 🟡 | cancel + REDUCE_ONLY | order_timeout |
| F03 | 撤单无响应 | cancel 超时 | 高 | 低 | cancel_timeout | 🔴 | HALTED | order_error |
| F04 | 持仓漂移 | reconcile 不一致 | 高 | 低 | position_drift | 🔴 | HALTED + flatten | position_mismatch |
| F05 | 部分成交卡住 | partial 不变 | 中 | 中 | fill_timeout | 🟡 | cancel + reprice | order_retry |
| F06 | 主力频繁切换 | dominant 抖动 | 中 | 低 | cooldown | 🟡 | 冷却抑制 | - |
| F07 | 临期未处理 | 近到期仍持仓 | 高 | 低 | expiry_gate | 🔴 | 禁开仓 + 减仓 | guardian_trigger |
| F08 | 裸腿敞口 | 单腿成交 | 高 | 低 | leg_imbalance | 🔴 | auto_hedge | guardian_action |
| F09 | 推理失败 | DL 模型报错 | 中 | 低 | try-catch | 🟡 | fallback 降级 | decision |
| F10 | 流动性不足 | spread 过大 | 中 | 中 | liquidity_gate | 🟡 | 拒绝下单 | protection_reject |
| F11 | 乌龙指 | 数量/价格异常 | 高 | 低 | fat_finger | 🔴 | 拒绝下单 | protection_reject |
| F12 | 频率过高 | 超过限制 | 中 | 中 | throttle | 🟡 | 拒绝下单 | protection_reject |

### 20.2 应对动作说明

| 动作 | 说明 | 触发方 |
|------|------|--------|
| REDUCE_ONLY | 禁止开仓，仅允许平仓/减仓 | Guardian |
| HALTED | 停止所有交易，等待人工 | Guardian |
| cancel_all | 撤销所有活动订单 | Guardian |
| flatten_all | 平掉所有持仓 | Guardian |
| auto_hedge | 自动对冲裸腿 | PairExecutor |
| fallback | 降级到备选策略 | FallbackManager |
| reprice | 重新报价（追价） | AutoOrderEngine |

### 20.3 恢复条件

| 状态 | 恢复到 | 条件 |
|------|--------|------|
| REDUCE_ONLY | RUNNING | 冷却期结束 + 健康检查通过 |
| HALTED | MANUAL | 人工确认 |
| MANUAL | RUNNING | 人工恢复指令 |

---

## 附录 A：术语表

| 术语 | 说明 |
|------|------|
| A-Platform | 平台化模块（全策略共享） |
| B-Models | 策略公式模块（按策略独立） |
| Guardian | 无人值守守护系统 |
| FSM | 有限状态机（Finite State Machine） |
| REDUCE_ONLY | 仅允许减仓模式 |
| HALTED | 停止交易模式 |
| stale | 过期（行情超时） |
| reconcile | 对账（本地 vs 柜台） |
| dominant | 主力合约 |
| subdominant | 次主力合约 |
| exec_id | 执行上下文 ID（一次调仓意图） |
| local_id | 本地订单 ID（系统内唯一） |
| order_ref | CTP 订单引用 |
| order_sys_id | 交易所系统订单号 |

---

## 附录 B：参考文档

| 文档 | 说明 |
|------|------|
| V2_SPEC_EXPANDED_NOT_RUSHING_LAUNCH_Version2.md | V2 完整规格 |
| v2_required_scenarios.yml | V2 场景矩阵 |
| v3pro_required_scenarios.yml | V3PRO 场景矩阵 |
| v3pro_strategies.yml | 策略配置 |
| artifacts/context/context.md | 上下文锚点 |
| scripts/make.ps1 | 门禁脚本 |
| scripts/validate_policy.py | 场景验证脚本 |
| scripts/coverage_gate.py | 覆盖率门禁脚本 |

---

## 附录 C：变更日志

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2025-12-15 | - | 初始版本 |
| v1.1 | 2025-12-15 | Copilot | 修复格式 + 新增章节 21-27 |

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     🆕 [NEW CHAPTERS] 以下为 v1.1 新增章节
     ├─ 第21章：回滚策略（军规 M9 要求）
     ├─ 第22章：测试规范（测试文件命名规范）
     ├─ 第23章：脚本依赖验证（确认引用脚本存在）
     ├─ 第24章：扩展模块规划（缺失模块建议）
     ├─ 第25章：机器学习 Pipeline 规划
     ├─ 第26章：风控增强规划
     └─ 第27章：高频模块规划
═══════════════════════════════════════════════════════════════════════════ -->

---

## 21. 回滚策略

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第21章审查
     ├─ 检查：原文档缺少回滚策略，违反军规 M9
     ├─ 风险：Phase 失败时无法快速恢复，可能导致生产事故
     ├─ 修改：新增完整回滚策略，每个 Phase 都有明确回滚命令
     └─ 总结：回滚能力是军规级必备
═══════════════════════════════════════════════════════════════════════════ -->

### 21.1 回滚原则

| 原则 | 说明 |
|------|------|
| **立即可用** | 回滚命令必须在 30 秒内完成 |
| **版本可追溯** | 每次回滚必须记录到 audit |
| **最小影响** | 只回滚必要的组件，不影响已稳定模块 |
| **验证必须** | 回滚后必须执行门禁验证 |

### 21.2 Phase 回滚命令

| Phase | 回滚触发条件 | 回滚命令 | 验证命令 |
|-------|-------------|----------|----------|
| Phase 0 | market 模块门禁失败 | `git checkout HEAD~1 -- src/market/` | `python -c "from src.market import *"` |
| Phase 1 | audit/cost/guardian 门禁失败 | `git checkout HEAD~1 -- src/audit/ src/cost/ src/guardian/` | `.\scripts\make.ps1 ci-json` |
| Phase 2 | execution 模块门禁失败 | `git checkout HEAD~1 -- src/execution/auto/ src/execution/protection/ src/execution/pair/` | `.\scripts\make.ps1 replay-json` |
| Phase 3 | strategy 模块门禁失败 | `git checkout HEAD~1 -- src/strategy/fallback.py src/strategy/calendar_arb/` | `python .\scripts\validate_policy.py --strict-scenarios` |
| Phase 4 | verifier 门禁失败 | `git checkout HEAD~1 -- src/replay/verifier.py` | `.\scripts\make.ps1 replay-json` |
| Phase 5 | 集成测试失败 | `git reset --hard <M4_COMMIT_SHA>` | 完整门禁 |
| Phase 6 | 策略升级失败 | `git checkout HEAD~1 -- src/strategy/` | `python .\scripts\validate_policy.py --all` |

### 21.3 紧急回滚流程

```powershell
# 🔴 紧急回滚脚本模板
# Step 1: 停止所有服务
Stop-Process -Name python -Force -ErrorAction SilentlyContinue

# Step 2: 记录当前状态
git log -1 --format="%H %s" > artifacts/rollback_$(Get-Date -Format "yyyyMMdd_HHmmss").log

# Step 3: 回滚到安全点
git reset --hard <SAFE_COMMIT_SHA>

# Step 4: 验证
.\scripts\make.ps1 ci-json
if ($LASTEXITCODE -ne 0) { throw "Rollback verification failed!" }

# Step 5: 记录回滚事件
Write-Host "ROLLBACK COMPLETE at $(Get-Date)"
```

### 21.4 回滚检查清单

- [ ] 确认当前 commit SHA
- [ ] 确认回滚目标 commit SHA
- [ ] 执行回滚命令
- [ ] 验证门禁通过
- [ ] 更新 context.md 锚点
- [ ] 通知相关人员

---

## 22. 测试规范

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第22章审查
     ├─ 检查：原文档缺少测试文件命名规范
     ├─ 风险：测试文件命名混乱，难以维护和定位
     ├─ 修改：新增完整测试规范，包括命名、结构、分类
     └─ 总结：测试规范是代码质量的基础
═══════════════════════════════════════════════════════════════════════════ -->

### 22.1 测试目录结构

<!-- 📝 当前实际结构：所有测试文件位于 tests/ 根目录
     未来规划：迁移到下方分层结构 -->

**当前实际结构** (2025-12-16):
```text
tests/
├── test_*.py                       # 所有测试文件（765 tests）
├── conftest.py                     # pytest 配置
└── fixtures/                       # 测试数据
```

**目标结构** (规划中):

```text
tests/
├── unit/                           # 单元测试（快速，不依赖外部服务）
│   ├── market/
│   │   ├── test_instrument_cache.py
│   │   ├── test_universe_selector.py
│   │   └── test_quote_cache.py
│   ├── audit/
│   │   ├── test_writer.py
│   │   └── test_decision_log.py
│   ├── guardian/
│   │   ├── test_state_machine.py
│   │   └── test_triggers.py
│   ├── execution/
│   │   ├── test_order_fsm.py
│   │   └── test_position_tracker.py
│   └── strategy/
│       ├── test_fallback.py
│       └── test_calendar_arb.py
│
├── integration/                    # 集成测试（需要 mock 服务）
│   ├── test_e2e_replay.py
│   ├── test_fault_injection.py
│   └── test_cold_start.py
│
├── e2e/                            # 端到端测试（完整环境）
│   └── test_live_trading.py
│
├── fixtures/                       # 测试数据
│   ├── tick_sample.jsonl
│   ├── instrument_cache.json
│   └── mock_orders.json
│
└── conftest.py                     # pytest 配置
```

### 22.2 测试文件命名规范

| 类型 | 命名格式 | 示例 |
|------|----------|------|
| 单元测试 | `test_<module_name>.py` | `test_instrument_cache.py` |
| 集成测试 | `test_<scenario>.py` | `test_e2e_replay.py` |
| 场景测试 | `test_<rule_id>.py` | `test_guard_fsm_transitions.py` |
| 性能测试 | `bench_<module>.py` | `bench_quote_cache.py` |

### 22.3 测试函数命名规范

```python
# 格式: test_<action>_<condition>_<expected_result>

def test_load_from_file_valid_json_returns_instruments():
    """加载有效 JSON 应返回合约信息"""
    pass

def test_load_from_file_invalid_json_raises_error():
    """加载无效 JSON 应抛出异常"""
    pass

def test_is_stale_expired_quote_returns_true():
    """过期行情应返回 stale=True"""
    pass
```

### 22.4 测试标记（pytest markers）

```python
# conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "e2e: 端到端测试")
    config.addinivalue_line("markers", "slow: 慢速测试（>5s）")
    config.addinivalue_line("markers", "scenario: 场景驱动测试")
```

### 22.5 测试覆盖率要求

| 模块类型 | 行覆盖率 | 分支覆盖率 | 说明 |
|----------|----------|------------|------|
| 核心模块（guardian/execution/audit） | 100% | 100% | 零容忍 |
| 策略模块（strategy/*） | 90% | 85% | 高要求 |
| 工具模块（utils/*） | 80% | 70% | 标准 |
| 测试辅助（fixtures/*） | 不要求 | 不要求 | 豁免 |

---

## 23. 脚本依赖验证

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第23章审查
     ├─ 检查：文档引用的脚本需确认存在，违反军规 M10
     ├─ 风险：引用不存在的脚本会导致门禁失败
     ├─ 修改：列出所有引用脚本，标注存在状态，创建待办
     └─ 总结：脚本依赖必须在执行前验证
═══════════════════════════════════════════════════════════════════════════ -->

### 23.1 脚本依赖矩阵

| 脚本路径 | 状态 | 引用位置 | 备注 |
|----------|------|----------|------|
| `scripts/make.ps1` | ✅ 存在 | 1.2 门禁定义 | 已验证 |
| `scripts/validate_policy.py` | ✅ 存在 | 1.2 门禁定义 | 已验证 |
| `scripts/coverage_gate.py` | ✅ 存在 | 1.2 门禁定义 | 已验证 |
| `scripts/sim_gate.py` | ✅ 存在 | 1.2 门禁定义 | 2025-12-16 创建 |
| `scripts/replay_tick.py` | ✅ 存在 | 回放相关 | 已验证 |
| `scripts/export_context.py` | ✅ 存在 | 上下文导出 | 已验证 |
| `scripts/claude_loop.ps1` | ✅ 存在 | 自动化 | 已验证 |

### 23.2 待创建脚本清单

<!-- ✅ [COMPLETE] 以下脚本已全部创建完成 -->

| 脚本 | 创建时机 | 功能描述 | 状态 |
|------|----------|----------|--------|
| `scripts/sim_gate.py` | Phase 5 之前 | 模拟门禁验证脚本 | ✅ 已创建 2025-12-16 |

### 23.3 sim_gate.py 规格

```python
# scripts/sim_gate.py - 待创建
"""
模拟门禁脚本

功能:
1. 验证 sim-json 产物存在
2. 检查模拟结果与预期一致
3. 验证无异常交易行为

用法:
    python scripts/sim_gate.py --strict

退出码:
    0  - 通过
    9  - 模拟失败
    12 - 策略违规
"""
```

### 23.4 脚本验证命令

```powershell
# 执行前必须运行此验证
$requiredScripts = @(
    "scripts/make.ps1",
    "scripts/validate_policy.py",
    "scripts/coverage_gate.py",
    "scripts/sim_gate.py"
)

foreach ($script in $requiredScripts) {
    if (-not (Test-Path $script)) {
        Write-Error "MISSING: $script"
        exit 10
    }
}
Write-Host "All required scripts exist"
```

---

## 24. 扩展模块规划

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第24章审查
     ├─ 检查：原文档缺少扩展模块规划
     ├─ 风险：未来扩展方向不明确，可能导致架构不兼容
     ├─ 修改：新增扩展模块规划，明确未来方向
     ├─ 升级建议：以下模块建议在 V4 版本实现
     └─ 总结：提前规划有助于架构扩展性
═══════════════════════════════════════════════════════════════════════════ -->

### 24.1 建议新增模块（P1 优先级）

| 模块 | 目录 | 功能 | 场景数 | 依赖 | 工时 |
|------|------|------|--------|------|------|
| Portfolio | `src/portfolio/` | 组合管理、权重分配、再平衡 | 6 | Phase 2 | 16h |
| Monitoring | `src/monitoring/` | 实时监控、Prometheus metrics | 4 | Phase 1 | 12h |
| Notification | `src/notification/` | 多渠道告警（微信/邮件/短信） | 3 | Phase 1 | 8h |

### 24.2 建议新增模块（P2 优先级）

| 模块 | 目录 | 功能 | 场景数 | 依赖 | 工时 |
|------|------|------|--------|------|------|
| DepthCache | `src/market/depth_cache.py` | L2 深度行情缓存 | 4 | Phase 0 | 8h |
| SmartOrder | `src/execution/smart_order/` | TWAP/VWAP/冰山单 | 8 | Phase 2 | 24h |
| Signals | `src/signals/` | 信号聚合层（多策略融合） | 5 | Phase 3 | 16h |

### 24.3 建议新增策略（P2 优先级）

| 策略 | 目录 | 类型 | 场景数 | 工时 |
|------|------|------|--------|------|
| Momentum | `src/strategy/momentum/` | 动量趋势跟踪 | 5 | 20h |
| MeanReversion | `src/strategy/mean_reversion/` | 均值回归 | 4 | 16h |
| Grid | `src/strategy/grid/` | 网格交易 | 3 | 12h |
| CrossExchange | `src/strategy/arbitrage/cross_exchange/` | 跨所套利 | 4 | 20h |

### 24.4 Portfolio 模块规格

```python
# src/portfolio/__init__.py
"""
组合管理模块

类:
- PortfolioManager: 组合权重管理
- Rebalancer: 再平衡引擎
- RiskBudgeter: 风险预算分配

Required Scenarios:
- PORTFOLIO.WEIGHT.VALID: 权重和为1
- PORTFOLIO.REBALANCE.TRIGGER: 再平衡触发条件
- PORTFOLIO.RISK.BUDGET: 风险预算分配
"""
```

### 24.5 Monitoring 模块规格

```python
# src/monitoring/__init__.py
"""
实时监控模块

功能:
- Prometheus metrics 导出
- 健康检查端点
- 性能指标采集

Required Scenarios:
- MONITOR.METRICS.EXPORT: 指标导出
- MONITOR.HEALTH.CHECK: 健康检查
- MONITOR.LATENCY.TRACK: 延迟追踪
"""
```

---

## 25. 机器学习 Pipeline 规划

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第25章审查
     ├─ 检查：dl_torch 策略需要完整 ML Pipeline 支持
     ├─ 风险：模型版本管理混乱，推理不可复现
     ├─ 修改：新增 ML Pipeline 规划
     ├─ 升级建议：建议在 Phase 6 之后实现
     └─ 总结：ML 模型需要严格的版本和推理管理
═══════════════════════════════════════════════════════════════════════════ -->

### 25.1 ML Pipeline 架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                     ML Pipeline 架构                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │ Feature     │ -> │ Model       │ -> │ Online      │        │
│   │ Store       │    │ Registry    │    │ Inference   │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │ 特征计算    │    │ 模型版本    │    │ 推理服务    │        │
│   │ 特征缓存    │    │ A/B 测试    │    │ 降级处理    │        │
│   │ 特征校验    │    │ 回滚能力    │    │ 延迟监控    │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 25.2 模块规划

| 模块 | 目录 | 功能 | 优先级 |
|------|------|------|--------|
| FeatureStore | `src/ml_pipeline/feature_store.py` | 特征存储和计算 | P1 |
| ModelRegistry | `src/ml_pipeline/model_registry.py` | 模型版本管理 | P1 |
| OnlineInference | `src/ml_pipeline/online_inference.py` | 在线推理服务 | P1 |
| ABTesting | `src/ml_pipeline/ab_testing.py` | A/B 测试框架 | P2 |

### 25.3 Required Scenarios

| rule_id | 描述 | category |
|---------|------|----------|
| `ML.FEATURE.CACHE_HIT` | 特征缓存命中 | unit |
| `ML.FEATURE.VALIDATE` | 特征校验通过 | unit |
| `ML.MODEL.VERSION_LOAD` | 模型版本加载 | unit |
| `ML.MODEL.ROLLBACK` | 模型回滚能力 | unit |
| `ML.INFERENCE.TIMEOUT` | 推理超时降级 | unit |
| `ML.INFERENCE.DETERMINISTIC` | 推理确定性（seed） | unit |

### 25.4 模型版本规范

```yaml
# models/model_manifest.yml
models:
  dl_torch_v1:
    version: "1.0.0"
    framework: "pytorch"
    input_schema: "features_v1"
    output_schema: "signal_v1"
    sha256: "abc123..."
    created_at: "2025-12-15T00:00:00Z"
    metrics:
      sharpe: 1.8
      max_drawdown: 0.12
```

---

## 26. 风控增强规划

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第26章审查
     ├─ 检查：当前风控模块较为基础
     ├─ 风险：极端市场条件下风控不足
     ├─ 修改：新增风控增强规划
     ├─ 升级建议：建议在 V4 版本实现
     └─ 总结：风控是生产系统的生命线
═══════════════════════════════════════════════════════════════════════════ -->

### 26.1 风控增强模块

| 模块 | 目录 | 功能 | 优先级 |
|------|------|------|--------|
| VaRCalculator | `src/risk/var_calculator.py` | VaR 计算（历史法/参数法） | P1 |
| StressTest | `src/risk/stress_test.py` | 压力测试 | P1 |
| ScenarioAnalysis | `src/risk/scenario_analysis.py` | 情景分析 | P2 |
| CorrelationMonitor | `src/risk/correlation_monitor.py` | 相关性监控 | P2 |

### 26.2 Required Scenarios

| rule_id | 描述 | category |
|---------|------|----------|
| `RISK.VAR.CALCULATE` | VaR 计算 | unit |
| `RISK.VAR.BREACH_ACTION` | VaR 突破动作 | unit |
| `RISK.STRESS.SCENARIO` | 压力测试场景 | integration |
| `RISK.CORRELATION.BREAK` | 相关性崩溃检测 | unit |
| `RISK.DRAWDOWN.LIMIT` | 回撤限制 | unit |

### 26.3 VaR 配置

```python
@dataclass(frozen=True)
class VaRConfig:
    """VaR 配置."""
    METHOD: str = "historical"  # historical | parametric | monte_carlo
    CONFIDENCE_LEVEL: float = 0.99
    LOOKBACK_DAYS: int = 252
    VAR_LIMIT_PCT: float = 0.02  # 每日 VaR 限制 2%
    BREACH_ACTION: str = "REDUCE_ONLY"  # REDUCE_ONLY | HALTED
```

### 26.4 压力测试场景

| 场景 | 描述 | 冲击幅度 |
|------|------|----------|
| 2015 股灾 | 股指期货连续跌停 | -10% × 5天 |
| 2020 原油负价 | 原油期货极端波动 | -150% |
| 2022 LME 镍 | 逼空事件 | +100% |
| 流动性枯竭 | 买卖价差扩大 | spread × 10 |
| 交易所故障 | 无法成交 | 全部挂单 |

---

## 27. 高频模块规划

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 第27章审查
     ├─ 检查：当前系统为中低频设计
     ├─ 风险：高频场景性能不足
     ├─ 修改：新增高频模块规划
     ├─ 升级建议：仅在有高频需求时实现
     └─ 总结：高频模块为可选扩展
═══════════════════════════════════════════════════════════════════════════ -->

### 27.1 高频模块架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                     高频模块架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │ OrderBook   │ -> │ Tick        │ -> │ Latency     │        │
│   │ Rebuilder   │    │ Aggregator  │    │ Monitor     │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
│   性能目标：                                                    │
│   - Tick 处理延迟 < 100μs                                      │
│   - 订单簿重建延迟 < 500μs                                     │
│   - 端到端延迟 < 5ms                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 27.2 模块规划

| 模块 | 目录 | 功能 | 优先级 |
|------|------|------|--------|
| OrderBookRebuilder | `src/hft/order_book.py` | 订单簿重建 | P3 |
| TickAggregator | `src/hft/tick_aggregator.py` | Tick 聚合 | P3 |
| LatencyMonitor | `src/hft/latency_monitor.py` | 延迟监控 | P3 |
| CoLocation | `src/hft/co_location.py` | 托管优化 | P3 |

### 27.3 性能基准

| 指标 | 当前值 | 目标值 | 说明 |
|------|--------|--------|------|
| Tick 处理 | ~10ms | <100μs | 需要 Cython/Rust |
| 订单簿更新 | ~5ms | <500μs | 内存优化 |
| 端到端延迟 | ~100ms | <5ms | 网络优化 |
| GC 暂停 | ~50ms | <1ms | 内存池 |

### 27.4 实现建议

```python
# 🔴 [WARNING] 高频模块实现需要：
# 1. Cython 或 Rust 扩展
# 2. 零拷贝数据结构
# 3. 内存池预分配
# 4. 无锁队列
# 5. CPU 亲和性绑定

# 建议：除非有明确高频需求，否则不建议实现
```

---

## 28. CI/CD 集成说明 <!-- 🆕 NEW 2025-12-16 -->

<!-- ═══════════════════════════════════════════════════════════════════════════
     ✅ [NEW] 第28章新增
     ├─ 目的：说明 GitHub Actions CI/CD 配置
     ├─ 内容：工作流程、触发条件、门禁检查
     └─ 状态：2025-12-16 新增
═══════════════════════════════════════════════════════════════════════════ -->

### 28.1 GitHub Actions 工作流

**配置文件**: `.github/workflows/ci.yml`

```yaml
name: CI

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
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .

  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: mypy .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4

  policy-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[dev]"
      - run: python scripts/validate_policy.py --all
```

### 28.2 门禁检查顺序

| 步骤 | 检查项 | 退出码 | 说明 |
|------|--------|--------|------|
| 1 | Lint (ruff check) | 2 | 代码风格 |
| 2 | Format (ruff format) | 2 | 代码格式 |
| 3 | Type Check (mypy) | 3 | 类型检查 |
| 4 | Test (pytest) | 4 | 单元测试 |
| 5 | Coverage | 5 | 覆盖率 |
| 6 | Policy | 12 | 场景验证 |

### 28.3 本地执行命令

```powershell
# Windows PowerShell
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m mypy .
.venv/Scripts/python.exe -m pytest tests/ -q
.venv/Scripts/python.exe scripts/validate_policy.py --all
```

### 28.4 CI 状态徽章

```markdown
[![CI](https://github.com/linxiaotutututu1123/3579/actions/workflows/ci.yml/badge.svg)](https://github.com/linxiaotutututu1123/3579/actions/workflows/ci.yml)
```

---

## 附录 D：配置规范补充

<!-- ═══════════════════════════════════════════════════════════════════════════
     🔴 [REVIEW-NOTE] 附录D审查
     ├─ 检查：原配置规范缺少部分配置项
     ├─ 修改：补充通知、监控、扩展配置
     └─ 总结：配置集中管理，符合军规 M11
═══════════════════════════════════════════════════════════════════════════ -->

### D.1 通知配置

```python
@dataclass(frozen=True)
class NotificationConfig:
    """通知配置."""
    ALERT_THROTTLE_S: float = 60.0           # 同类告警节流
    ALERT_LEVELS: tuple = ("INFO", "WARN", "ERROR", "FATAL")
    DINGTALK_WEBHOOK: str = ""               # 钉钉 webhook
    WECHAT_WEBHOOK: str = ""                 # 企业微信 webhook
    EMAIL_SMTP_HOST: str = ""                # 邮件 SMTP
    SMS_API_KEY: str = ""                    # 短信 API
```

### D.2 监控配置

```python
@dataclass(frozen=True)
class MonitoringConfig:
    """监控配置."""
    METRICS_PORT: int = 9090                 # Prometheus 端口
    HEALTH_CHECK_INTERVAL_S: float = 10.0    # 健康检查间隔
    PPROF_ENABLED: bool = False              # pprof 开关
    TRACE_SAMPLE_RATE: float = 0.01          # 追踪采样率
```

### D.3 ML Pipeline 配置

```python
@dataclass(frozen=True)
class MLPipelineConfig:
    """ML Pipeline 配置."""
    FEATURE_CACHE_SIZE: int = 10000          # 特征缓存大小
    MODEL_REGISTRY_PATH: str = "models/"     # 模型注册表路径
    INFERENCE_TIMEOUT_MS: float = 100.0      # 推理超时
    FALLBACK_ON_TIMEOUT: bool = True         # 超时降级
```

---

## 文档结束

---

> **执行准备就绪。**  
> **请确认后开始 Phase 0 骨架创建。**
