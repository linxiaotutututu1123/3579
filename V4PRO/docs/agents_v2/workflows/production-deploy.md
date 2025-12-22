---
name: production-deploy
description: 生产部署全流程工作流
agents: [devops-master, security-auditor, test-engineer, code-reviewer, compliance-guard]
phases: 5
---

# Production Deploy Workflow (生产部署工作流)

> **命令**: `/v4:workflow production-deploy [模块名] [--flags]`

## 工作流概述

安全可靠的生产部署流程，包括测试验证、安全审计、部署执行和监控确认。

## 工作流阶段

### Phase 1: 部署准备 (devops-master + code-reviewer)

```
输入: 代码变更 + 部署请求
输出: 部署计划 + 检查清单
```

**步骤:**
1. 代码变更审查
2. 依赖检查
3. 配置验证
4. 制定部署计划
5. 准备回滚方案
6. 生成检查清单

### Phase 2: 测试验证 (test-engineer)

```
输入: 部署包
输出: 测试报告
```

**步骤:**
1. 单元测试执行
2. 集成测试执行
3. 回归测试执行
4. 性能测试
5. 验证测试结果
6. 生成测试报告

### Phase 3: 安全审计 (security-auditor + compliance-guard)

```
输入: 代码 + 配置
输出: 安全报告 + 合规确认
```

**步骤:**
1. 漏洞扫描
2. 依赖安全检查
3. 配置安全审查
4. 权限验证
5. 合规性检查
6. 生成安全报告

### Phase 4: 部署执行 (devops-master)

```
输入: 部署计划 + 部署包
输出: 部署结果
```

**步骤:**
1. 备份当前版本
2. 蓝绿部署准备
3. 执行部署
4. 健康检查
5. 流量切换
6. 验证部署结果

### Phase 5: 监控确认 (devops-master + risk-guardian)

```
输入: 部署完成
输出: 监控报告 + 确认
```

**步骤:**
1. 监控指标检查
2. 日志分析
3. 错误监控
4. 性能监控
5. 业务指标验证
6. 最终确认或回滚

## 质量门禁

| 阶段 | 门禁要求 |
|------|----------|
| Phase 1 | 代码审查通过 |
| Phase 2 | 测试100%通过 |
| Phase 3 | 无高危漏洞 |
| Phase 4 | 健康检查通过 |
| Phase 5 | 监控正常15分钟 |

## 回滚策略

```yaml
回滚触发条件:
  - 健康检查失败
  - 错误率>1%
  - 延迟P99>阈值
  - 业务指标异常

回滚步骤:
  1. 流量切回旧版本
  2. 验证旧版本正常
  3. 分析失败原因
  4. 记录事件报告
```

## 使用示例

```bash
# 完整部署
/v4:workflow production-deploy "strategy-engine"

# 金丝雀发布
/v4:workflow production-deploy "risk-service" --canary 10%

# 紧急修复
/v4:workflow production-deploy "hotfix-123" --fast --rollback-ready
```

## 输出物清单

- [ ] 部署计划
- [ ] 测试报告
- [ ] 安全审计报告
- [ ] 部署日志
- [ ] 监控仪表板
- [ ] 回滚方案
- [ ] 部署确认
