---
name: code-review
description: 代码审查全流程
agents: [code-reviewer, security-guardian, performance-hunter, test-champion]
---

# Code Review Workflow (代码审查工作流)

> `/workflow:review [PR] [--flags]`

## 概述
全面的代码审查流程，覆盖质量、安全、性能。

## 阶段

### Phase 1: 代码审查 (code-reviewer)
```
输入: PR代码
输出: 逻辑审查 + 风格检查
```

### Phase 2: 安全检查 (security-guardian)
```
输入: PR代码
输出: 安全扫描 + 漏洞报告
```

### Phase 3: 性能评估 (performance-hunter)
```
输入: PR代码
输出: 性能影响分析
```

### Phase 4: 测试验证 (test-champion)
```
输入: PR代码
输出: 测试覆盖 + 回归验证
```

## 质量门禁

| 检查项 | 要求 |
|--------|------|
| 逻辑正确 | 无逻辑错误 |
| 安全 | 无高危漏洞 |
| 性能 | 无性能退化 |
| 测试 | 覆盖率不降 |

## 示例
```bash
/workflow:review "PR#123"
/workflow:review "PR#456" --depth deep
```
