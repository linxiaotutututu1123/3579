# V4PRO Workflows

工作流是多Agent协作的完整流程，覆盖从需求到上线的全生命周期。

## 核心工作流

| 工作流 | 命令 | 描述 |
|--------|------|------|
| [策略开发](strategy-dev.md) | `/v4:workflow strategy-dev` | 策略从设计到上线全流程 |
| [风险评估](risk-assessment.md) | `/v4:workflow risk-assessment` | VaR、压力测试、风险归因 |
| [生产部署](production-deploy.md) | `/v4:workflow production-deploy` | 安全可靠的生产部署 |
| [合规审计](compliance-audit.md) | `/v4:workflow compliance-audit` | 监管合规全面审计 |

## 工作流设计原则

### 1. 阶段分明
每个工作流分为清晰的阶段，每个阶段有明确的输入输出。

### 2. 质量门禁
每个阶段都有质量门禁，只有通过才能进入下一阶段。

### 3. Agent协作
每个阶段由最合适的Agent组合执行，充分发挥专业能力。

### 4. 可追溯
所有阶段产出物都有记录，支持审计追踪。

### 5. 可回滚
关键阶段支持回滚，确保安全性。

## 工作流使用

### 基本调用
```bash
/v4:workflow <workflow-name> "<目标描述>"
```

### 指定阶段
```bash
/v4:workflow strategy-dev "策略名" --phase 1-3
```

### 带参数
```bash
/v4:workflow risk-assessment "组合" --stress --report
```

### 查看状态
```bash
/v4:workflow status
```

## 自定义工作流

可以组合Agent创建自定义工作流：

```yaml
name: my-workflow
description: 自定义工作流
phases:
  - name: 分析
    agents: [strategy-master, market-analyst]
    outputs: [分析报告]
  - name: 实现
    agents: [code-generator, test-engineer]
    outputs: [代码, 测试]
```

## 工作流监控

所有工作流执行都会记录：
- 开始/结束时间
- 各阶段状态
- 质量门禁结果
- 产出物列表
- 异常和告警
