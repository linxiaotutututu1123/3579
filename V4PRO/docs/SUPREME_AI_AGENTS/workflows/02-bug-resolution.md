---
name: bug-resolution
description: 问题解决全流程
agents: [debug-detective, code-craftsman, test-champion, code-reviewer]
---

# Bug Resolution Workflow (问题解决工作流)

> `/workflow:bug [问题描述] [--flags]`

## 概述
从问题发现到修复验证的完整流程。

## 阶段

### Phase 1: 问题诊断 (debug-detective)
```
输入: 问题描述 + 错误日志
输出: 根因分析 + 重现步骤
```

### Phase 2: 修复实现 (code-craftsman)
```
输入: 根因分析
输出: 修复代码 + 回归测试
```

### Phase 3: 测试验证 (test-champion)
```
输入: 修复代码
输出: 测试报告 + 回归确认
```

### Phase 4: 审查合并 (code-reviewer)
```
输入: PR
输出: 审查通过 + 合并
```

## 质量门禁

| 阶段 | 门禁 |
|------|------|
| 诊断 | 根因确认 |
| 修复 | 回归测试通过 |
| 测试 | 无新问题 |
| 审查 | 审查通过 |

## 示例
```bash
/workflow:bug "登录超时问题" --priority critical
/workflow:bug "内存泄漏" --type memory
```
