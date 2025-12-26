# Chairman Agents API 文档

## 概览

Chairman Agents 是一个多智能体协作系统，提供完整的任务调度、工作流管理和团队协作能力。

## 模块架构

```
chairman_agents/
├── core/           # 核心类型和协议定义
├── cognitive/      # 认知推理和记忆系统
├── integration/    # LLM客户端集成
├── orchestration/  # 任务调度和并行执行
├── workflow/       # 工作流管道和阶段管理
├── agents/         # 智能体基础实现
└── team/           # 团队构建和角色分配
```

## 快速导航

| 模块 | 说明 | 文档 |
|------|------|------|
| core | 核心类型、枚举、协议定义 | [core.md](core.md) |
| cognitive | 记忆系统、推理引擎 | [cognitive.md](cognitive.md) |
| integration | LLM客户端、响应缓存 | [integration.md](integration.md) |
| orchestration | 任务调度、并行执行 | [orchestration.md](orchestration.md) |
| workflow | 工作流管道、阶段管理 | [workflow.md](workflow.md) |
| agents | 智能体基类 | [agents.md](agents.md) |
| team | 团队构建、角色分配 | [team.md](team.md) |

## 核心概念

### 智能体角色

系统定义了18种智能体角色：

- `ARCHITECT` - 架构师
- `DEVELOPER` - 开发者
- `REVIEWER` - 评审员
- `TESTER` - 测试员
- `RESEARCHER` - 研究员
- `COORDINATOR` - 协调员
- 等...

### 任务状态流转

```
PENDING → ASSIGNED → IN_PROGRESS → COMPLETED
                  ↘ BLOCKED ↗    ↘ FAILED
                                  ↘ CANCELLED
```

### 工作流阶段

```
INITIALIZATION → PLANNING → EXECUTION → REVIEW → REFINEMENT → COMPLETION
```

## 快速开始

### 创建LLM客户端

```python
from chairman_agents.integration.llm_client import create_llm_client, LLMConfig

config = LLMConfig(
    api_key="your-api-key",
    model="claude-3-5-sonnet-20241022",
)
client = create_llm_client("anthropic", config)

result = await client.chat([
    Message(role=MessageRole.USER, content="Hello")
])
```

### 任务调度

```python
from chairman_agents.orchestration.task_scheduler import TaskScheduler, SchedulingStrategy

scheduler = TaskScheduler(strategy=SchedulingStrategy.PRIORITY_FIRST)
await scheduler.start()
await scheduler.submit(task)
next_task = await scheduler.next()
```

### 工作流执行

```python
from chairman_agents.workflow.pipeline import WorkflowPipeline

pipeline = WorkflowPipeline(name="my-workflow")
await pipeline.execute(tasks, executor_fn)
```

## 版本要求

- Python >= 3.10
- 可选依赖：
  - `anthropic` - Anthropic API
  - `openai` - OpenAI API
  - `sentence-transformers` - 向量嵌入
  - `jieba` - 中文分词
