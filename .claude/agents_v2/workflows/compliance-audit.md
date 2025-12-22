---
name: compliance-audit
description: 合规审计全流程工作流
agents: [compliance-guard, regulatory-advisor, security-auditor, code-reviewer]
phases: 4
---

# Compliance Audit Workflow (合规审计工作流)

> **命令**: `/v4:workflow compliance-audit [审计范围] [--flags]`

## 工作流概述

完整的合规审计流程，包括法规对照、系统检查、日志审计和报告生成。

## 工作流阶段

### Phase 1: 审计准备 (compliance-guard + regulatory-advisor)

```
输入: 审计范围 + 时间周期
输出: 审计计划 + 检查清单
```

**步骤:**
1. 确定审计范围
2. 收集最新监管法规
3. 制定审计计划
4. 准备检查清单
5. 通知相关方
6. 获取必要权限

### Phase 2: 系统检查 (compliance-guard + security-auditor)

```
输入: 检查清单 + 系统访问
输出: 检查结果
```

**步骤:**
1. 报撤单频率检查(M17)
2. 审计日志完整性(M3)
3. 熔断机制验证(M6)
4. 大额确认机制(M12)
5. 权限控制检查
6. 安全配置审查

### Phase 3: 日志审计 (compliance-guard + code-reviewer)

```
输入: 审计日志 + 时间范围
输出: 审计发现
```

**步骤:**
1. 提取审计日志
2. 异常交易识别
3. 违规行为检测
4. HFT行为分析
5. 操作记录验证
6. 生成审计发现

### Phase 4: 报告生成 (regulatory-advisor + compliance-guard)

```
输入: 检查结果 + 审计发现
输出: 审计报告 + 整改建议
```

**步骤:**
1. 汇总检查结果
2. 分析问题根因
3. 评估合规风险
4. 制定整改建议
5. 生成审计报告
6. 准备监管报送

## 审计检查项

### M3 审计日志
- [ ] 所有交易操作记录
- [ ] 日志不可篡改
- [ ] 保留期限≥5年
- [ ] 异地备份

### M6 熔断机制
- [ ] 日亏损熔断
- [ ] 单持仓熔断
- [ ] 保证金熔断
- [ ] 恢复机制

### M12 大额确认
- [ ] 阈值配置正确
- [ ] 确认流程完整
- [ ] 记录可追溯

### M17 程序化合规
- [ ] 报撤单频率
- [ ] 撤单比例
- [ ] HFT检测
- [ ] 备案有效

## 质量门禁

| 阶段 | 门禁要求 |
|------|----------|
| Phase 1 | 法规覆盖完整 |
| Phase 2 | 检查项100%执行 |
| Phase 3 | 日志完整可追溯 |
| Phase 4 | 报告符合监管要求 |

## 使用示例

```bash
# 全面审计
/v4:workflow compliance-audit "全系统" --period "2024Q4"

# 专项审计
/v4:workflow compliance-audit "程序化交易" --focus M17

# 快速检查
/v4:workflow compliance-audit "策略A" --quick
```

## 输出物清单

- [ ] 审计计划
- [ ] 检查清单
- [ ] 系统检查报告
- [ ] 日志审计报告
- [ ] 问题清单
- [ ] 整改建议
- [ ] 监管报送材料
- [ ] 跟踪验证计划
