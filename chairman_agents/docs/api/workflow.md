# Workflow 模块 API

工作流管道和阶段管理。

## pipeline 模块

### 枚举

#### PipelineStatus

管道状态。

| 值 | 说明 |
|---|---|
| `IDLE` | 空闲 |
| `RUNNING` | 运行中 |
| `PAUSED` | 暂停 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |

### 类型别名

```python
TaskExecutor = Callable[[Task], Awaitable[TaskResult]]
StageHandler = Callable[[WorkflowStage, list[Task]], Awaitable[list[Task]]]
```

### 数据类

#### PipelineState

管道状态快照。

```python
@dataclass
class PipelineState:
    pipeline_id: str
    name: str
    status: PipelineStatus
    current_stage: WorkflowStage | None
    tasks: dict[TaskId, Task]
    results: dict[TaskId, TaskResult]
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineState
```

#### PipelineCheckpoint

检查点。

```python
@dataclass
class PipelineCheckpoint:
    checkpoint_id: str
    pipeline_id: str
    state: PipelineState
    created_at: datetime
    description: str = ""
```

---

### WorkflowPipeline

工作流管道。

```python
class WorkflowPipeline:
    def __init__(
        self,
        name: str = "workflow",
        *,
        checkpoint_dir: Path | None = None,
        auto_checkpoint: bool = True,
    ) -> None
```

**参数：**
- `name` - 管道名称
- `checkpoint_dir` - 检查点存储目录
- `auto_checkpoint` - 是否自动创建检查点

#### execute

执行工作流。

```python
async def execute(
    self,
    tasks: Sequence[Task],
    executor: TaskExecutor,
    *,
    stage_handler: StageHandler | None = None,
) -> dict[TaskId, TaskResult]
```

**参数：**
- `tasks` - 任务列表
- `executor` - 任务执行函数
- `stage_handler` - 阶段处理器（可选）

**返回：** 任务ID到结果的映射

**示例：**
```python
from chairman_agents.workflow.pipeline import WorkflowPipeline

async def executor(task: Task) -> TaskResult:
    # 执行任务
    return TaskResult(task_id=task.id, success=True)

pipeline = WorkflowPipeline(
    name="my-workflow",
    checkpoint_dir=Path("./checkpoints"),
)

results = await pipeline.execute(tasks, executor)
```

#### pause

暂停执行。

```python
async def pause(self) -> None
```

#### cancel

取消执行。

```python
async def cancel(self) -> None
```

#### checkpoint

创建检查点。

```python
async def checkpoint(
    self,
    description: str = "",
) -> PipelineCheckpoint
```

#### resume

从检查点恢复。

```python
async def resume(
    self,
    checkpoint_id: str,
    executor: TaskExecutor,
) -> dict[TaskId, TaskResult]
```

#### list_checkpoints

列出检查点。

```python
async def list_checkpoints(self) -> list[PipelineCheckpoint]
```

#### delete_checkpoint

删除检查点。

```python
async def delete_checkpoint(self, checkpoint_id: str) -> bool
```

#### get_task

获取任务。

```python
def get_task(self, task_id: TaskId) -> Task | None
```

#### get_result

获取任务结果。

```python
def get_result(self, task_id: TaskId) -> TaskResult | None
```

#### get_metrics

获取执行指标。

```python
def get_metrics(self) -> dict[str, Any]
```

**返回：**
```python
{
    "total_tasks": 10,
    "completed_tasks": 8,
    "failed_tasks": 2,
    "success_rate": 0.8,
    "total_duration_seconds": 120.5,
    "average_task_duration": 12.05,
}
```

#### 属性

```python
@property
def pipeline_id(self) -> str

@property
def status(self) -> PipelineStatus

@property
def current_stage(self) -> WorkflowStage | None

@property
def state(self) -> PipelineState
```

---

## stage_manager 模块

### 枚举

#### WorkflowStage

工作流阶段。

| 值 | 说明 |
|---|---|
| `INITIALIZATION` | 初始化 |
| `PLANNING` | 规划 |
| `EXECUTION` | 执行 |
| `REVIEW` | 评审 |
| `REFINEMENT` | 优化 |
| `COMPLETION` | 完成 |

阶段流转顺序：
```
INITIALIZATION → PLANNING → EXECUTION → REVIEW → REFINEMENT → COMPLETION
```

#### StageStatus

阶段状态。

| 值 | 说明 |
|---|---|
| `PENDING` | 等待 |
| `IN_PROGRESS` | 进行中 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `SKIPPED` | 已跳过 |

### 类型别名

```python
StageHook = Callable[[StageContext], Awaitable[None]]
```

### 数据类

#### StageContext

阶段上下文。

```python
@dataclass
class StageContext:
    stage: WorkflowStage
    status: StageStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    tasks: list[Task] = field(default_factory=list)
    results: list[TaskResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: Exception | None = None
```

#### StageTransition

阶段转换记录。

```python
@dataclass
class StageTransition:
    from_stage: WorkflowStage | None
    to_stage: WorkflowStage
    timestamp: datetime
    reason: str = ""
```

---

### StageManager

阶段管理器。

```python
class StageManager:
    def __init__(self) -> None
```

#### enter_stage

进入阶段。

```python
async def enter_stage(
    self,
    stage: WorkflowStage,
    tasks: list[Task] | None = None,
) -> StageContext
```

**异常：** `ValueError` - 无效的阶段转换

#### complete_stage

完成当前阶段。

```python
async def complete_stage(
    self,
    results: list[TaskResult] | None = None,
) -> None
```

#### fail_stage

标记阶段失败。

```python
async def fail_stage(
    self,
    error: Exception,
) -> None
```

#### rollback

回滚到指定阶段。

```python
async def rollback(
    self,
    target_stage: WorkflowStage,
    reason: str = "",
) -> None
```

#### skip_stage

跳过阶段。

```python
async def skip_stage(
    self,
    stage: WorkflowStage,
    reason: str = "",
) -> None
```

#### on_enter / on_exit

注册阶段钩子。

```python
def on_enter(
    self,
    stage: WorkflowStage,
    hook: StageHook,
) -> None

def on_exit(
    self,
    stage: WorkflowStage,
    hook: StageHook,
) -> None
```

#### can_transition_to

检查是否可转换到目标阶段。

```python
def can_transition_to(
    self,
    target_stage: WorkflowStage,
) -> bool
```

#### 属性

```python
@property
def current_stage(self) -> WorkflowStage | None

@property
def current_context(self) -> StageContext | None

@property
def history(self) -> list[StageTransition]
```

**示例：**
```python
from chairman_agents.workflow.stage_manager import StageManager, WorkflowStage

manager = StageManager()

# 注册钩子
async def on_execution_enter(ctx: StageContext):
    print(f"进入执行阶段，{len(ctx.tasks)}个任务")

manager.on_enter(WorkflowStage.EXECUTION, on_execution_enter)

# 阶段流转
await manager.enter_stage(WorkflowStage.INITIALIZATION)
await manager.complete_stage()

await manager.enter_stage(WorkflowStage.PLANNING, tasks)
await manager.complete_stage()

await manager.enter_stage(WorkflowStage.EXECUTION, tasks)
# 执行任务...
await manager.complete_stage(results)

# 检查历史
for transition in manager.history:
    print(f"{transition.from_stage} → {transition.to_stage}")
```
