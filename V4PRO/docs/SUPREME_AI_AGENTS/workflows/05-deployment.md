---
name: deployment
description: 部署发布全流程
agents: [devops-commander, test-champion, security-guardian, sre-guardian]
---

# Deployment Workflow (部署发布工作流)

> `/workflow:deploy [版本] [--env staging|prod]`

## 概述
安全可靠的部署发布流程。

## 阶段

### Phase 1: 部署准备 (devops-commander)
```
输入: 发布版本
输出: 部署计划 + 回滚方案
```

### Phase 2: 测试验证 (test-champion)
```
输入: 部署包
输出: 回归测试 + 冒烟测试
```

### Phase 3: 安全检查 (security-guardian)
```
输入: 部署配置
输出: 安全扫描 + 合规检查
```

### Phase 4: 发布执行 (devops-commander)
```
输入: 审批通过
输出: 部署执行 + 健康检查
```

### Phase 5: 监控确认 (sre-guardian)
```
输入: 部署完成
输出: 监控确认 + SLO验证
```

## 质量门禁

| 阶段 | 门禁 |
|------|------|
| 准备 | 回滚方案就绪 |
| 测试 | 测试全部通过 |
| 安全 | 无安全问题 |
| 发布 | 健康检查通过 |
| 监控 | SLO正常 |

## 示例
```bash
/workflow:deploy "v1.2.0" --env staging
/workflow:deploy "v1.2.0" --env prod --canary
```
