# V4PRO AI Agents v2.0 - SuperClaude Framework Edition

> **版本**: v2.0 | **框架**: SuperClaude Compatible | **Agent数量**: 24个

## 快速开始

### 安装配置
```bash
# 1. 复制agents到.claude目录
cp -r agents_v2/agents ~/.claude/site-packages/v4pro/agents/
cp -r agents_v2/commands ~/.claude/commands/v4pro/

# 2. 在CLAUDE.md中添加引用
echo "@v4pro/agents/*.md" >> ~/.claude/CLAUDE.md
```

### 使用方式

**方式1: 直接调用命令**
```
/v4:strategy "开发夜盘跳空策略"
/v4:risk "评估当前持仓VaR"
/v4:execute "执行大单拆分 --amount 1000000"
```

**方式2: 自然语言触发**
```
用户: 我需要开发一个高频套利策略
系统: [自动激活 strategy-master Agent]
```

**方式3: 组合工作流**
```
/v4:workflow strategy-dev "政策红利捕手策略"
# 自动协调: 策略Agent → 风控Agent → 合规Agent → 执行Agent
```

---

## Agent目录

### 核心交易Agent (6个)
| Agent | 命令 | 触发场景 |
|-------|------|----------|
| [quant-architect](agents/quant-architect.md) | `/v4:arch` | 架构设计、系统集成 |
| [strategy-master](agents/strategy-master.md) | `/v4:strategy` | 策略开发、因子挖掘 |
| [risk-guardian](agents/risk-guardian.md) | `/v4:risk` | 风控规则、VaR计算 |
| [ml-scientist](agents/ml-scientist.md) | `/v4:ml` | 模型训练、特征工程 |
| [execution-master](agents/execution-master.md) | `/v4:execute` | 订单执行、拆单 |
| [compliance-guard](agents/compliance-guard.md) | `/v4:compliance` | 合规检查、审计 |

### 编码专家Agent (6个)
| Agent | 命令 | 触发场景 |
|-------|------|----------|
| [code-generator](agents/code-generator.md) | `/v4:codegen` | 代码生成 |
| [code-reviewer](agents/code-reviewer.md) | `/v4:review` | 代码审查 |
| [test-engineer](agents/test-engineer.md) | `/v4:test` | 测试开发 |
| [security-auditor](agents/security-auditor.md) | `/v4:security` | 安全审计 |
| [performance-optimizer](agents/performance-optimizer.md) | `/v4:perf` | 性能优化 |
| [refactor-expert](agents/refactor-expert.md) | `/v4:refactor` | 代码重构 |

### 领域专家Agent (6个)
| Agent | 命令 | 触发场景 |
|-------|------|----------|
| [quant-modeler](agents/quant-modeler.md) | `/v4:model` | 金融建模 |
| [market-analyst](agents/market-analyst.md) | `/v4:market` | 市场分析 |
| [risk-quant](agents/risk-quant.md) | `/v4:riskquant` | 风险量化 |
| [algo-trader](agents/algo-trader.md) | `/v4:algo` | 算法交易 |
| [regulatory-advisor](agents/regulatory-advisor.md) | `/v4:reg` | 监管咨询 |
| [research-scientist](agents/research-scientist.md) | `/v4:research` | 研究调研 |

### 功能支持Agent (6个)
| Agent | 命令 | 触发场景 |
|-------|------|----------|
| [requirements-analyst](agents/requirements-analyst.md) | `/v4:req` | 需求分析 |
| [doc-master](agents/doc-master.md) | `/v4:doc` | 文档生成 |
| [devops-master](agents/devops-master.md) | `/v4:devops` | DevOps |
| [data-engineer](agents/data-engineer.md) | `/v4:data` | 数据工程 |
| [api-designer](agents/api-designer.md) | `/v4:api` | API设计 |
| [integration-master](agents/integration-master.md) | `/v4:integrate` | 系统集成 |

---

## 工作流

| 工作流 | 命令 | 参与Agent |
|--------|------|-----------|
| [strategy-development](workflows/strategy-dev.md) | `/v4:workflow strategy-dev` | 策略→风控→合规→执行 |
| [risk-audit](workflows/risk-audit.md) | `/v4:workflow risk-audit` | 风控→量化→合规 |
| [model-training](workflows/model-train.md) | `/v4:workflow model-train` | ML→数据→测试 |
| [code-review](workflows/code-review.md) | `/v4:workflow code-review` | 审查→安全→测试 |

---

## 军规合规矩阵

所有Agent必须遵守V4PRO军规M1-M33:

| 军规 | 说明 | 关联Agent |
|------|------|-----------|
| M1 | 单一信号源 | strategy-master |
| M3 | 审计日志 | compliance-guard |
| M6 | 熔断保护 | risk-guardian |
| M12 | 双重确认 | execution-master |
| M17 | 程序化合规 | compliance-guard |

---

## 配置示例

```yaml
# v4pro-agents.yaml
agents:
  quant-architect:
    enabled: true
    priority: 1
    auto_activate: true

  strategy-master:
    enabled: true
    priority: 2
    quality_gates:
      sharpe_ratio: ">=2.0"
      max_drawdown: "<=10%"

  risk-guardian:
    enabled: true
    priority: 1  # 高优先级
    circuit_breaker:
      daily_loss: 0.03
      position_loss: 0.05
```

---

## 文档结构说明

每个Agent文档包含:
- **YAML Frontmatter**: 元数据定义
- **Triggers**: 触发条件列表
- **Behavioral Mindset**: 行为心智模型
- **Focus Areas**: 聚焦领域
- **Key Actions**: 关键动作步骤
- **Outputs**: 输出物规范
- **Boundaries**: 权限边界
- **Examples**: 使用示例
- **Integration**: MCP/工具集成

---

**文档维护**: V4PRO开发团队
**更新日期**: 2025-12-22
