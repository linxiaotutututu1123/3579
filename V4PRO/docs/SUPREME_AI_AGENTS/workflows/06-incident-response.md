---
name: incident-response
description: 事故响应全流程
agents: [sre-guardian, debug-detective, devops-commander, doc-master]
---

# Incident Response Workflow (事故响应工作流)

> `/workflow:incident [事故描述] [--severity P0|P1|P2]`

## 概述
快速响应和恢复的事故处理流程。

## 阶段

### Phase 1: 事故响应 (sre-guardian)
```
输入: 告警/报告
输出: 影响评估 + 通知相关方
```

### Phase 2: 问题诊断 (debug-detective)
```
输入: 事故信息
输出: 根因分析 + 临时方案
```

### Phase 3: 恢复执行 (devops-commander)
```
输入: 恢复方案
输出: 服务恢复 + 验证确认
```

### Phase 4: 事后分析 (sre-guardian + doc-master)
```
输入: 事故记录
输出: Postmortem + 改进措施
```

## 响应时间

| 严重级别 | 响应时间 | 恢复目标 |
|----------|----------|----------|
| P0 | 5分钟 | 1小时 |
| P1 | 15分钟 | 4小时 |
| P2 | 1小时 | 24小时 |

## 示例
```bash
/workflow:incident "网站无法访问" --severity P0
/workflow:incident "支付延迟" --severity P1
```
