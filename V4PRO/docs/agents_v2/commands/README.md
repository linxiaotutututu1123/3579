# V4PRO Commands

命令是调用Agent的快捷方式，支持参数和标志。

## 核心交易命令

| 命令 | Agent | 描述 |
|------|-------|------|
| `/v4:arch` | quant-architect | 系统架构设计 |
| `/v4:strategy` | strategy-master | 策略开发优化 |
| `/v4:risk` | risk-guardian | 风控规则设计 |
| `/v4:ml` | ml-scientist | 机器学习模型 |
| `/v4:execute` | execution-master | 订单执行优化 |
| `/v4:compliance` | compliance-guard | 合规监控 |

## 编码专家命令

| 命令 | Agent | 描述 |
|------|-------|------|
| `/v4:codegen` | code-generator | 代码生成 |
| `/v4:review` | code-reviewer | 代码审查 |
| `/v4:test` | test-engineer | 测试开发 |
| `/v4:security` | security-auditor | 安全审计 |
| `/v4:perf` | performance-optimizer | 性能优化 |
| `/v4:refactor` | refactor-expert | 代码重构 |

## 领域专家命令

| 命令 | Agent | 描述 |
|------|-------|------|
| `/v4:quant` | quant-modeler | 量化建模 |
| `/v4:market` | market-analyst | 市场分析 |
| `/v4:riskquant` | risk-quant | 风险量化 |
| `/v4:algo` | algo-trader | 算法交易 |
| `/v4:reg` | regulatory-advisor | 监管顾问 |
| `/v4:research` | research-scientist | 量化研究 |

## 功能支撑命令

| 命令 | Agent | 描述 |
|------|-------|------|
| `/v4:req` | requirements-analyst | 需求分析 |
| `/v4:doc` | doc-master | 文档管理 |
| `/v4:devops` | devops-master | 运维管理 |
| `/v4:data` | data-engineer | 数据工程 |
| `/v4:api` | api-designer | API设计 |
| `/v4:integrate` | integration-master | 系统集成 |

## 工作流命令

| 命令 | 描述 |
|------|------|
| `/v4:workflow strategy-dev` | 策略开发全流程 |
| `/v4:workflow risk-assessment` | 风险评估流程 |
| `/v4:workflow production-deploy` | 生产部署流程 |
| `/v4:workflow compliance-audit` | 合规审计流程 |

## 通用标志

```
--ultrathink     深度思考模式
--token-efficient  令牌高效模式
--realtime      实时处理模式
--report        生成详细报告
--test          包含测试验证
--doc           生成文档
--strict        严格模式
```

## 使用示例

```bash
# 开发新策略
/v4:strategy "开发夜盘跳空策略" --type trend --backtest

# 风控配置
/v4:risk "配置日亏损熔断" --type circuit --strict

# 代码生成
/v4:codegen "实现双均线策略" --type strategy --test --doc

# 性能优化
/v4:perf "优化订单延迟" --type latency --profile

# 完整工作流
/v4:workflow strategy-dev "政策红利捕手策略"
```
