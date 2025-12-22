# V4PRO AI Agents v2

> 中国期货量化交易系统的顶级AI Agent框架
> 基于SuperClaude框架设计，完全兼容军规M1-M33

## 快速开始

### 安装配置

1. 将`agents_v2`目录放置于项目根目录
2. 在Claude Code中加载Agent配置
3. 使用命令调用Agent

### 使用方式

**方式1: 直接调用命令**
```bash
/v4:strategy "开发夜盘跳空策略"
/v4:risk "评估当前持仓VaR"
/v4:codegen "实现双均线策略" --test
```

**方式2: 自然语言触发**
```
"我需要设计一个新的趋势策略"  → 自动触发 strategy-master
"检查风控规则配置是否正确"    → 自动触发 risk-guardian
```

**方式3: 组合工作流**
```bash
/v4:workflow strategy-dev "政策红利捕手策略"
/v4:workflow risk-assessment "期货组合"
```

---

## Agent目录

### 核心交易Agent (6个)

| Agent | 命令 | 优先级 | 军规 | 描述 |
|-------|------|--------|------|------|
| [quant-architect](agents/quant-architect.md) | `/v4:arch` | P1 | M1,M3,M6,M12 | 量化系统架构设计 |
| [strategy-master](agents/strategy-master.md) | `/v4:strategy` | P2 | M1,M6,M7,M13 | 策略开发与优化 |
| [risk-guardian](agents/risk-guardian.md) | `/v4:risk` | P1 | M6,M12,M16,M19 | 风控系统设计 |
| [ml-scientist](agents/ml-scientist.md) | `/v4:ml` | P3 | M3,M7 | 机器学习模型 |
| [execution-master](agents/execution-master.md) | `/v4:execute` | P2 | M12,M13,M14,M15,M17 | 订单执行优化 |
| [compliance-guard](agents/compliance-guard.md) | `/v4:compliance` | P1 | M3,M7,M13,M17 | 合规监控 |

### 编码专家Agent (6个)

| Agent | 命令 | 优先级 | 描述 |
|-------|------|--------|------|
| [code-generator](agents/code-generator.md) | `/v4:codegen` | P2 | 高质量代码生成 |
| [code-reviewer](agents/code-reviewer.md) | `/v4:review` | P2 | 代码审查与质量 |
| [test-engineer](agents/test-engineer.md) | `/v4:test` | P2 | 测试策略与执行 |
| [security-auditor](agents/security-auditor.md) | `/v4:security` | P1 | 安全审计与防护 |
| [performance-optimizer](agents/performance-optimizer.md) | `/v4:perf` | P2 | 性能优化 |
| [refactor-expert](agents/refactor-expert.md) | `/v4:refactor` | P3 | 代码重构 |

### 领域专家Agent (6个)

| Agent | 命令 | 优先级 | 描述 |
|-------|------|--------|------|
| [quant-modeler](agents/quant-modeler.md) | `/v4:quant` | P2 | 量化定价模型 |
| [market-analyst](agents/market-analyst.md) | `/v4:market` | P2 | 市场微观结构 |
| [risk-quant](agents/risk-quant.md) | `/v4:riskquant` | P1 | 风险量化分析 |
| [algo-trader](agents/algo-trader.md) | `/v4:algo` | P2 | 算法交易策略 |
| [regulatory-advisor](agents/regulatory-advisor.md) | `/v4:reg` | P1 | 监管法规咨询 |
| [research-scientist](agents/research-scientist.md) | `/v4:research` | P3 | 量化研究创新 |

### 功能支撑Agent (6个)

| Agent | 命令 | 优先级 | 描述 |
|-------|------|--------|------|
| [requirements-analyst](agents/requirements-analyst.md) | `/v4:req` | P2 | 需求分析管理 |
| [doc-master](agents/doc-master.md) | `/v4:doc` | P3 | 文档管理 |
| [devops-master](agents/devops-master.md) | `/v4:devops` | P2 | CI/CD与运维 |
| [data-engineer](agents/data-engineer.md) | `/v4:data` | P2 | 数据工程 |
| [api-designer](agents/api-designer.md) | `/v4:api` | P2 | API设计 |
| [integration-master](agents/integration-master.md) | `/v4:integrate` | P2 | 系统集成 |

---

## 工作流

| 工作流 | 命令 | 描述 |
|--------|------|------|
| [策略开发](workflows/strategy-dev.md) | `/v4:workflow strategy-dev` | 从设计到上线全流程 |
| [风险评估](workflows/risk-assessment.md) | `/v4:workflow risk-assessment` | VaR+压力测试+归因 |
| [生产部署](workflows/production-deploy.md) | `/v4:workflow production-deploy` | 安全部署流程 |
| [合规审计](workflows/compliance-audit.md) | `/v4:workflow compliance-audit` | 全面合规审计 |

---

## 命令参考

### 通用标志

| 标志 | 描述 |
|------|------|
| `--ultrathink` | 深度思考模式 |
| `--token-efficient` | 令牌高效模式 |
| `--realtime` | 实时处理 |
| `--report` | 生成详细报告 |
| `--test` | 包含测试验证 |
| `--doc` | 生成文档 |
| `--strict` | 严格模式 |
| `--backtest` | 回测验证 |

### 常用命令示例

```bash
# 策略开发
/v4:strategy "开发均值回归策略" --type reversion --backtest

# 风控配置
/v4:risk "配置熔断规则" --type circuit --strict

# VaR计算
/v4:riskquant "计算99% VaR" --type var --backtest

# 代码生成
/v4:codegen "实现TWAP执行算法" --type strategy --test --doc

# 性能优化
/v4:perf "优化订单延迟" --type latency --profile

# 合规检查
/v4:compliance "检查报撤单合规" --type monitor --realtime

# 完整工作流
/v4:workflow strategy-dev "跨期套利策略" --strict
```

---

## 军规合规

所有Agent严格遵守V4PRO军规M1-M33：

| 军规 | 描述 | 相关Agent |
|------|------|-----------|
| M1 | 单一信号源 | strategy-master, quant-architect |
| M3 | 审计日志 | compliance-guard, 所有Agent |
| M6 | 熔断保护 | risk-guardian, devops-master |
| M7 | 场景回放 | ml-scientist, compliance-guard |
| M12 | 大额确认 | risk-guardian, execution-master |
| M13 | 涨跌停边界 | strategy-master, execution-master |
| M14 | 平今仓规则 | execution-master, algo-trader |
| M15 | 夜盘规则 | execution-master, market-analyst |
| M16 | 保证金监控 | risk-guardian, risk-quant |
| M17 | 程序化合规 | compliance-guard, execution-master |
| M18 | 系统安全 | security-auditor, api-designer |
| M19 | 风险归因 | risk-guardian, risk-quant |

---

## 目录结构

```
agents_v2/
├── README.md                    # 本文件
├── agents/                      # Agent定义
│   ├── quant-architect.md      # 核心交易
│   ├── strategy-master.md
│   ├── risk-guardian.md
│   ├── ml-scientist.md
│   ├── execution-master.md
│   ├── compliance-guard.md
│   ├── code-generator.md       # 编码专家
│   ├── code-reviewer.md
│   ├── test-engineer.md
│   ├── security-auditor.md
│   ├── performance-optimizer.md
│   ├── refactor-expert.md
│   ├── quant-modeler.md        # 领域专家
│   ├── market-analyst.md
│   ├── risk-quant.md
│   ├── algo-trader.md
│   ├── regulatory-advisor.md
│   ├── research-scientist.md
│   ├── requirements-analyst.md # 功能支撑
│   ├── doc-master.md
│   ├── devops-master.md
│   ├── data-engineer.md
│   ├── api-designer.md
│   └── integration-master.md
├── commands/                    # 命令定义
│   └── README.md
└── workflows/                   # 工作流定义
    ├── README.md
    ├── strategy-dev.md
    ├── risk-assessment.md
    ├── production-deploy.md
    └── compliance-audit.md
```

---

## 质量标准

| 指标 | 标准 |
|------|------|
| 代码覆盖率 | ≥90% |
| 夏普比率 | ≥2.0 |
| 最大回撤 | ≤10% |
| VaR回测通过率 | ≥95% |
| 系统延迟 | ≤100ms |
| 合规违规 | 0次 |

---

## 版本信息

- **版本**: v2.0.0
- **框架**: SuperClaude兼容
- **语言**: 中文
- **更新**: 2024-12

## 维护

山东齐沥开发团队
