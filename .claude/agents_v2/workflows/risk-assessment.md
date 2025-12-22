---
name: risk-assessment
description: 风险评估全流程工作流
agents: [risk-guardian, risk-quant, compliance-guard, quant-modeler]
phases: 4
---

# Risk Assessment Workflow (风险评估工作流)

> **命令**: `/v4:workflow risk-assessment [评估对象] [--flags]`

## 工作流概述

完整的风险评估流程，包括VaR计算、压力测试、风险归因和合规检查。

## 工作流阶段

### Phase 1: 风险识别 (risk-guardian)

```
输入: 持仓数据 + 市场数据
输出: 风险清单 + 风险矩阵
```

**步骤:**
1. 收集持仓和市场数据
2. 识别市场风险
3. 识别信用风险
4. 识别流动性风险
5. 识别操作风险
6. 生成风险矩阵

### Phase 2: 风险量化 (risk-quant + quant-modeler)

```
输入: 风险清单 + 历史数据
输出: VaR报告 + 敏感性分析
```

**步骤:**
1. 选择VaR方法(参数/历史/蒙特卡洛)
2. 计算日度VaR/CVaR
3. 计算Greeks(Delta/Gamma/Vega)
4. 敏感性分析
5. 相关性分析
6. 生成量化报告

### Phase 3: 压力测试 (risk-quant + risk-guardian)

```
输入: 持仓 + 场景定义
输出: 压力测试报告
```

**步骤:**
1. 定义历史场景(2015股灾等)
2. 定义假设场景
3. 执行场景模拟
4. 损失评估
5. 极端事件分析
6. 生成压力测试报告

### Phase 4: 合规检查与归因 (compliance-guard + risk-quant)

```
输入: 风险报告 + 监管要求
输出: 合规报告 + 风险归因
```

**步骤:**
1. 监管要求对照
2. 限额符合性检查
3. SHAP风险归因
4. 因子分解
5. 改进建议
6. 生成最终报告

## 质量门禁

| 阶段 | 门禁要求 |
|------|----------|
| Phase 1 | 风险识别完整性100% |
| Phase 2 | VaR回测通过率≥95% |
| Phase 3 | 场景覆盖率100% |
| Phase 4 | 合规检查通过 |

## 使用示例

```bash
# 完整评估
/v4:workflow risk-assessment "期货组合"

# 快速VaR
/v4:workflow risk-assessment "持仓" --type var --quick

# 压力测试
/v4:workflow risk-assessment "策略组合" --stress --report
```

## 输出物清单

- [ ] 风险识别报告
- [ ] 风险矩阵
- [ ] VaR计算报告
- [ ] Greeks分析
- [ ] 压力测试报告
- [ ] 风险归因报告
- [ ] 合规检查报告
- [ ] 改进建议
