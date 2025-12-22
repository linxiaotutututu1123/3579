---
name: feature-development
description: 功能开发全流程
agents: [requirements-sage, supreme-architect, code-craftsman, test-champion, code-reviewer]
---

# Feature Development Workflow (功能开发工作流)

> `/workflow:feature [功能名] [--flags]`

## 概述
从需求到上线的完整功能开发流程。

## 阶段

### Phase 1: 需求分析 (requirements-sage)
```
输入: 功能描述
输出: 需求文档 + 用户故事 + 验收标准
```

### Phase 2: 技术设计 (supreme-architect)
```
输入: 需求文档
输出: 技术方案 + 接口设计 + 数据模型
```

### Phase 3: 编码实现 (code-craftsman)
```
输入: 技术方案
输出: 功能代码 + 单元测试
```

### Phase 4: 测试验证 (test-champion)
```
输入: 功能代码
输出: 测试报告 + 覆盖率报告
```

### Phase 5: 代码审查 (code-reviewer)
```
输入: PR
输出: 审查意见 + 合并确认
```

## 质量门禁

| 阶段 | 门禁 |
|------|------|
| 需求 | 验收标准完整 |
| 设计 | 方案评审通过 |
| 编码 | 覆盖率>80% |
| 测试 | 全部通过 |
| 审查 | 无阻塞问题 |

## 示例
```bash
/workflow:feature "用户注册功能"
/workflow:feature "支付集成" --priority high
```
