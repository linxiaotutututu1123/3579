---
name: strategy-dev
description: 策略开发全流程工作流
agents: [strategy-master, ml-scientist, risk-guardian, test-engineer, code-reviewer]
phases: 5
---

# Strategy Development Workflow (策略开发工作流)

> **命令**: `/v4:workflow strategy-dev [策略名称] [--flags]`

## 工作流概述

完整的策略开发工作流，从需求到上线的全流程管理。

## 工作流阶段

### Phase 1: 需求分析与设计 (strategy-master + requirements-analyst)

```
输入: 策略需求描述
输出: 策略设计文档 + 技术规格
```

**步骤:**
1. 收集策略需求和约束
2. 市场分析和可行性评估
3. 策略逻辑设计
4. 风控规则定义
5. 输出策略设计文档

### Phase 2: 模型开发 (ml-scientist + quant-modeler)

```
输入: 策略设计文档
输出: 模型代码 + 训练结果
```

**步骤:**
1. 特征工程和因子挖掘
2. 模型选择和设计
3. 模型训练和验证
4. 过拟合检测
5. 模型输出和文档

### Phase 3: 代码实现 (code-generator + strategy-master)

```
输入: 策略设计 + 模型
输出: 策略代码 + 单元测试
```

**步骤:**
1. 策略代码框架
2. 信号生成模块
3. 仓位管理模块
4. 风控集成模块
5. 单元测试编写

### Phase 4: 测试验证 (test-engineer + risk-guardian)

```
输入: 策略代码
输出: 测试报告 + 回测报告
```

**步骤:**
1. 单元测试执行
2. 回测验证
3. 压力测试
4. 风控验证
5. 合规检查

### Phase 5: 审查上线 (code-reviewer + compliance-guard)

```
输入: 代码 + 测试报告
输出: 上线审批 + 部署配置
```

**步骤:**
1. 代码审查
2. 安全审计
3. 合规验证
4. 部署配置
5. 上线审批

## 质量门禁

| 阶段 | 门禁要求 |
|------|----------|
| Phase 1 | 设计评审通过 |
| Phase 2 | IC>0.05, 过拟合检测通过 |
| Phase 3 | 代码覆盖率>90% |
| Phase 4 | 夏普>2.0, 回撤<10% |
| Phase 5 | 审查通过, 合规通过 |

## 使用示例

```bash
# 完整流程
/v4:workflow strategy-dev "夜盘跳空闪电战"

# 指定阶段
/v4:workflow strategy-dev "均值回归策略" --phase 1-3

# 带参数
/v4:workflow strategy-dev "动量策略" --backtest --strict
```

## 输出物清单

- [ ] 策略设计文档
- [ ] 模型训练报告
- [ ] 策略代码
- [ ] 单元测试
- [ ] 回测报告
- [ ] 代码审查报告
- [ ] 合规检查报告
- [ ] 部署配置
