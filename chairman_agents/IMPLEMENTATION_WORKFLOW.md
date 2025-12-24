# Chairman Agents 实现工作流

> 自动生成于系统化分析 | 策略: systematic

## 项目状态概览

### ✅ 已完成模块 (4个)
| 模块 | 文件 | 行数 | 状态 |
|------|------|------|------|
| cognitive | `reasoning.py` | 1245 | 完整 |
| cognitive | `memory.py` | 657 | 完整 |
| collaboration | `pair_programming.py` | 1243 | 完整 |
| agents/experts | `base_expert.py` | 524 | 完整 |

### ❌ 待实现模块 (7个)
| 模块 | 描述 | 优先级 |
|------|------|--------|
| integration | LLM客户端、模型注册 | P0 |
| tools | 代码执行、文件操作 | P0 |
| orchestration | 任务调度、并行执行 | P0 |
| team | 团队创建和管理 | P1 |
| workflow | 6阶段标准流程 | P1 |
| observability | 监控、追踪、日志 | P1 |
| api | REST API服务 | P2 |

---

## 模块依赖图

```
                    ┌─────────────┐
                    │   core/     │
                    │   types     │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   integration   │ │     tools       │ │   cognitive     │
│   (LLM客户端)   │ │  (代码/文件)    │ │   (已完成)      │
└────────┬────────┘ └────────┬────────┘ └─────────────────┘
         │                   │
         └─────────┬─────────┘
                   ▼
         ┌─────────────────┐
         │  orchestration  │
         │  (任务调度)      │
         └────────┬────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐ ┌──────────┐ ┌─────────────┐
│  team  │ │ workflow │ │observability│
└────┬───┘ └────┬─────┘ └─────────────┘
     │          │
     └────┬─────┘
          ▼
    ┌───────────┐
    │    api    │
    └───────────┘
```

---

## Phase 1: 基础层 (P0)

### 1.1 integration/llm_client.py
```python
# 核心接口
class LLMClient(Protocol):
    async def complete(self, prompt: str, **kwargs) -> CompletionResult: ...
    async def chat(self, messages: list[Message], **kwargs) -> ChatResult: ...
    async def stream(self, prompt: str) -> AsyncIterator[str]: ...

# 实现类
class AnthropicClient(LLMClient): ...
class OpenAIClient(LLMClient): ...
class LocalClient(LLMClient): ...
```

**依赖**: `core/types.py`
**复杂度**: 高
**预计文件**: ~400行

### 1.2 integration/model_registry.py
```python
@dataclass
class ModelConfig:
    name: str
    provider: str
    context_window: int
    capabilities: list[str]

class ModelRegistry:
    def register(self, config: ModelConfig) -> None: ...
    def get(self, name: str) -> ModelConfig: ...
    def list_by_capability(self, capability: str) -> list[ModelConfig]: ...
```

**依赖**: 1.1
**复杂度**: 中
**预计文件**: ~200行

### 1.3 tools/code_executor.py
```python
@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    duration: float

class CodeExecutor:
    async def execute(self, code: str, language: str) -> ExecutionResult: ...
    async def execute_with_timeout(self, code: str, timeout: float) -> ExecutionResult: ...
```

**依赖**: `core/types.py`
**复杂度**: 高
**预计文件**: ~350行

### 1.4 tools/file_operations.py
```python
class FileOperations:
    async def read(self, path: Path) -> str: ...
    async def write(self, path: Path, content: str) -> None: ...
    async def search(self, pattern: str, directory: Path) -> list[Path]: ...
    async def diff(self, original: str, modified: str) -> str: ...
```

**依赖**: 无
**复杂度**: 低
**预计文件**: ~150行

### 1.5 tools/tool_registry.py
```python
class ToolRegistry:
    def register(self, name: str, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool: ...
    def execute(self, name: str, **kwargs) -> ToolResult: ...
```

**依赖**: 1.3, 1.4
**复杂度**: 中
**预计文件**: ~200行

---

## Phase 2: 编排层 (P0)

### 2.1 orchestration/task_scheduler.py
```python
@dataclass
class ScheduledTask:
    id: str
    task: Task
    priority: int
    dependencies: list[str]
    status: TaskStatus

class TaskScheduler:
    async def schedule(self, task: Task) -> ScheduledTask: ...
    async def execute_next(self) -> TaskResult: ...
    async def get_ready_tasks(self) -> list[ScheduledTask]: ...
```

**依赖**: Phase 1
**复杂度**: 高
**预计文件**: ~400行

### 2.2 orchestration/parallel_executor.py
```python
class ParallelExecutor:
    def __init__(self, max_workers: int = 4): ...
    async def execute_parallel(self, tasks: list[Task]) -> list[TaskResult]: ...
    async def execute_with_semaphore(self, tasks: list[Task], limit: int) -> list[TaskResult]: ...
```

**依赖**: 2.1
**复杂度**: 高
**预计文件**: ~300行

### 2.3 orchestration/dependency_resolver.py
```python
class DependencyResolver:
    def build_graph(self, tasks: list[Task]) -> DependencyGraph: ...
    def topological_sort(self, graph: DependencyGraph) -> list[Task]: ...
    def find_cycles(self, graph: DependencyGraph) -> list[list[Task]]: ...
```

**依赖**: 2.1
**复杂度**: 中
**预计文件**: ~250行

---

## Phase 3: 团队与工作流 (P1)

### 3.1 team/team_builder.py
```python
@dataclass
class Team:
    id: str
    name: str
    members: list[BaseExpertAgent]
    roles: dict[str, BaseExpertAgent]

class TeamBuilder:
    def create_team(self, task: Task) -> Team: ...
    def select_experts(self, requirements: list[str]) -> list[BaseExpertAgent]: ...
```

**依赖**: Phase 2, agents/experts
**复杂度**: 中
**预计文件**: ~300行

### 3.2 team/role_assignment.py
```python
class RoleAssignment:
    def assign_roles(self, team: Team, task: Task) -> dict[str, BaseExpertAgent]: ...
    def reassign(self, team: Team, feedback: Feedback) -> dict[str, BaseExpertAgent]: ...
```

**依赖**: 3.1
**复杂度**: 中
**预计文件**: ~200行

### 3.3 workflow/stage_manager.py
```python
class WorkflowStage(Enum):
    INITIALIZATION = "initialization"
    PLANNING = "planning"
    EXECUTION = "execution"
    REVIEW = "review"
    REFINEMENT = "refinement"
    COMPLETION = "completion"

class StageManager:
    async def enter_stage(self, stage: WorkflowStage) -> None: ...
    async def complete_stage(self) -> WorkflowStage: ...
    async def rollback(self, to_stage: WorkflowStage) -> None: ...
```

**依赖**: Phase 2
**复杂度**: 高
**预计文件**: ~350行

### 3.4 workflow/pipeline.py
```python
class WorkflowPipeline:
    def __init__(self, stages: list[WorkflowStage]): ...
    async def execute(self, task: Task, team: Team) -> WorkflowResult: ...
    async def checkpoint(self) -> PipelineState: ...
    async def resume(self, state: PipelineState) -> WorkflowResult: ...
```

**依赖**: 3.3
**复杂度**: 高
**预计文件**: ~400行

---

## Phase 4: 可观测性 (P1)

### 4.1 observability/tracer.py
```python
@dataclass
class Span:
    trace_id: str
    span_id: str
    name: str
    start_time: datetime
    end_time: datetime | None
    attributes: dict[str, Any]

class Tracer:
    def start_span(self, name: str) -> Span: ...
    def end_span(self, span: Span) -> None: ...
    @contextmanager
    def trace(self, name: str) -> Iterator[Span]: ...
```

**依赖**: 无
**复杂度**: 中
**预计文件**: ~250行

### 4.2 observability/metrics.py
```python
class MetricsCollector:
    def counter(self, name: str, value: int = 1) -> None: ...
    def gauge(self, name: str, value: float) -> None: ...
    def histogram(self, name: str, value: float) -> None: ...
    def export(self) -> dict[str, Any]: ...
```

**依赖**: 无
**复杂度**: 低
**预计文件**: ~150行

### 4.3 observability/logger.py
```python
class StructuredLogger:
    def info(self, message: str, **context) -> None: ...
    def error(self, message: str, exc: Exception | None = None, **context) -> None: ...
    def with_context(self, **context) -> "StructuredLogger": ...
```

**依赖**: 无
**复杂度**: 低
**预计文件**: ~100行

---

## Phase 5: API层 (P2)

### 5.1 api/schemas.py
```python
from pydantic import BaseModel

class TaskRequest(BaseModel):
    description: str
    requirements: list[str]
    priority: int = 1

class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None
```

**依赖**: core/types
**复杂度**: 低
**预计文件**: ~150行

### 5.2 api/routes.py
```python
from fastapi import APIRouter

router = APIRouter()

@router.post("/tasks")
async def create_task(request: TaskRequest) -> TaskResponse: ...

@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> TaskResponse: ...

@router.get("/teams")
async def list_teams() -> list[TeamResponse]: ...
```

**依赖**: Phase 3, 4
**复杂度**: 中
**预计文件**: ~300行

### 5.3 api/server.py
```python
from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="Chairman Agents API")
    app.include_router(routes.router)
    return app
```

**依赖**: 5.1, 5.2
**复杂度**: 中
**预计文件**: ~200行

---

## 实现顺序总结

```
Week 1-2: Phase 1 (基础层)
├── 1.1 llm_client.py
├── 1.2 model_registry.py
├── 1.3 code_executor.py
├── 1.4 file_operations.py
└── 1.5 tool_registry.py

Week 3-4: Phase 2 (编排层)
├── 2.1 task_scheduler.py
├── 2.2 parallel_executor.py
└── 2.3 dependency_resolver.py

Week 5-6: Phase 3 (团队与工作流)
├── 3.1 team_builder.py
├── 3.2 role_assignment.py
├── 3.3 stage_manager.py
└── 3.4 pipeline.py

Week 7: Phase 4 (可观测性)
├── 4.1 tracer.py
├── 4.2 metrics.py
└── 4.3 logger.py

Week 8: Phase 5 (API层)
├── 5.1 schemas.py
├── 5.2 routes.py
└── 5.3 server.py
```

---

## 代码规范

### 参考模式
- **Protocol 模式**: 参考 `base_expert.py:LLMClientProtocol`
- **dataclass 模式**: 参考 `reasoning.py:ThoughtNode`
- **异步模式**: 参考 `memory.py:MemorySystem`
- **Session 管理**: 参考 `pair_programming.py:PairSession`

### 编码标准
- Python 3.12+
- 类型注解完整
- 中文文档字符串
- asyncio 异步优先
- Protocol 定义接口

---

## 测试策略

每个模块需要:
1. 单元测试 (`tests/unit/`)
2. 集成测试 (`tests/integration/`)
3. 至少 80% 代码覆盖率

---

*生成于 Chairman Agents 工作流分析系统*
