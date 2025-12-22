---
name: system-design
description: 系统设计全流程
agents: [product-visionary, supreme-architect, database-oracle, api-master, security-guardian]
---

# System Design Workflow (系统设计工作流)

> `/workflow:design [系统名] [--flags]`

## 概述
从需求到架构设计的完整流程。

## 阶段

### Phase 1: 需求理解 (product-visionary)
```
输入: 业务需求
输出: PRD + 用户场景 + 约束条件
```

### Phase 2: 架构设计 (supreme-architect)
```
输入: PRD
输出: 架构图 + 技术选型 + ADR
```

### Phase 3: 数据设计 (database-oracle)
```
输入: 架构设计
输出: 数据模型 + 存储方案
```

### Phase 4: API设计 (api-master)
```
输入: 架构设计
输出: API规范 + 接口文档
```

### Phase 5: 安全评审 (security-guardian)
```
输入: 完整设计
输出: 安全评审 + 威胁模型
```

## 质量门禁

| 阶段 | 门禁 |
|------|------|
| 需求 | 利益相关者确认 |
| 架构 | 架构评审通过 |
| 数据 | 模型评审通过 |
| API | 接口评审通过 |
| 安全 | 安全评审通过 |

## 示例
```bash
/workflow:design "电商平台"
/workflow:design "支付系统" --scale large
```
