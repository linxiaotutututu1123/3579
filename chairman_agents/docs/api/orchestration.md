# Orchestration 模块 API

任务调度和并行执行。

## task_scheduler 模块

### 枚举

#### SchedulingStrategy

调度策略。

| 值 | 说明 |
|---|---|
| `FIFO` | 先进先出 |
| `PRIORITY_FIRST` | 优先级优先 |
| `SHORTEST_FIRST` | 最短任务优先 |
| `DEPENDENCY_AWARE` | 依赖感知 |
| `BALANCED` | 平衡策略 |

#### SchedulerState

调度器状态。

| 值 | 说明 |
|---|---|
| `IDLE` | 空闲 |
| `RUNNING` | 运行中 |
| `PAUSED` | 暂停 |
| `STOPPED` | 已停止 |

### 数据类

#### SchedulerConfig

```python
@dataclass
class SchedulerConfig:
    max_queue_size: int = 10000
    max_concurrent: int = 10
    default_timeout: float = 300.0
    batch_size: int = 50
    enable_dependency_resolution: bool = True
    graceful_shutdown_timeout: float = 30.0
    task_fetch_timeout: float = 5.0
```

#### SchedulerStats

```python
@dataclass
class SchedulerStats:
    total_submitted: int = 0
    total_scheduled: int = 0
    total_completed: int = 0
    total_failed: int = 0
    total_cancelled: int = 0
    total_timed_out: int = 0
    current_queue_size: int = 0
    average_wait_time: float = 0.0
    average_execution_time: float = 0.0
    peak_queue_size: int = 0
    peak_concurrent: int = 0
```

#### ScheduledTask

已调度任务包装。

```python
@dataclass(order=True)
class ScheduledTask:
    priority_value: int
    submit_time: float
    sequence: int
    task: Task
    scheduled_at: datetime
    execution_deadline: datetime | None = None
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_task(
        cls,
        task: Task,
        sequence: int,
        *,
        priority_override: int | None = None,
    ) -> ScheduledTask
```

---

### TaskScheduler

任务调度器。

```python
class TaskScheduler:
    def __init__(
        self,
        strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIRST,
        *,
        config: SchedulerConfig | None = None,
        max_queue_size: int | None = None,
        enable_dependency_resolution: bool | None = None,
    ) -> None
```

#### start

启动调度器。

```python
async def start(self) -> None
```

#### stop

停止调度器。

```python
async def stop(self) -> None
```

#### shutdown

优雅关闭。

```python
async def shutdown(
    self,
    wait: bool = True,
    cancel_pending: bool = False,
) -> int
```

**返回：** 取消的任务数量

#### pause / resume

暂停/恢复调度。

```python
async def pause(self) -> None
async def resume(self) -> None
```

#### submit

提交单个任务。

```python
async def submit(
    self,
    task: Task,
    timeout: float | None = None,
) -> None
```

**异常：** `RuntimeError` - 队列已满

#### submit_batch

批量提交任务。

```python
async def submit_batch(
    self,
    tasks: Sequence[Task],
    timeout: float | None = None,
) -> int
```

**返回：** 成功提交的数量

**异常：**
- `RuntimeError` - 队列空间不足
- `DependencyError` - 依赖问题

#### next

获取下一个待执行任务。

```python
async def next(
    self,
    timeout: float | None = None,
) -> Task | None
```

#### cancel

取消任务。

```python
async def cancel(
    self,
    task_id: TaskId,
    reason: str | None = None,
) -> bool
```

#### cancel_all

取消所有任务。

```python
async def cancel_all(
    self,
    include_running: bool = False,
) -> int
```

#### mark_completed

标记任务完成。

```python
async def mark_completed(self, task_id: TaskId) -> None
```

#### mark_failed

标记任务失败。

```python
async def mark_failed(
    self,
    task_id: TaskId,
    error: Exception | None = None,
    timed_out: bool = False,
) -> None
```

#### retry

重试失败任务。

```python
async def retry(
    self,
    task_id: TaskId,
    max_retries: int = 3,
) -> bool
```

#### 属性

```python
@property
def stats(self) -> SchedulerStats

@property
def is_empty(self) -> bool

@property
def queue_size(self) -> int
```

#### 回调注册

```python
def on_task_scheduled(self, callback: Callable[[Task], None]) -> None
def on_task_completed(self, callback: Callable[[Task], None]) -> None
def on_task_failed(self, callback: Callable[[Task, Exception], None]) -> None
```

**示例：**
```python
from chairman_agents.orchestration.task_scheduler import (
    TaskScheduler,
    SchedulingStrategy,
    SchedulerConfig,
)

config = SchedulerConfig(max_concurrent=5, default_timeout=60.0)
scheduler = TaskScheduler(
    strategy=SchedulingStrategy.BALANCED,
    config=config,
)

await scheduler.start()

# 提交任务
await scheduler.submit(task1)
await scheduler.submit_batch([task2, task3, task4])

# 获取并执行任务
while True:
    task = await scheduler.next(timeout=5.0)
    if task is None:
        break
    try:
        result = await execute_task(task)
        await scheduler.mark_completed(task.id)
    except Exception as e:
        await scheduler.mark_failed(task.id, e)

await scheduler.shutdown()
```

---

## parallel_executor 模块

### 枚举

#### ExecutionMode

执行模式。

| 值 | 说明 |
|---|---|
| `PARALLEL` | 完全并行 |
| `SEQUENTIAL` | 顺序执行 |
| `BATCHED` | 分批并行 |
| `ADAPTIVE` | 自适应 |

#### ExecutorState

| 值 | 说明 |
|---|---|
| `IDLE` | 空闲 |
| `RUNNING` | 执行中 |
| `PAUSED` | 暂停 |
| `SHUTTING_DOWN` | 正在关闭 |
| `STOPPED` | 已停止 |

### 类型别名

```python
TaskExecutorFn = Callable[[Task], Awaitable[TaskResult]]
```

### 数据类

#### ExecutorConfig

```python
@dataclass
class ExecutorConfig:
    max_workers: int = 4
    default_timeout: float = 300.0
    max_retries: int = 3
    retry_delay: float = 1.0
    mode: ExecutionMode = ExecutionMode.PARALLEL
    batch_size: int = 10
    graceful_shutdown_timeout: float = 30.0
```

#### ExecutionResult

```python
@dataclass
class ExecutionResult:
    task_id: TaskId
    task: Task
    success: bool = False
    result: TaskResult | None = None
    error: Exception | None = None
    started_at: datetime
    completed_at: datetime | None = None
    execution_time: float = 0.0
    retry_count: int = 0

    @property
    def duration_ms(self) -> float
```

#### BatchResult

```python
@dataclass
class BatchResult:
    total: int = 0
    successful: int = 0
    failed: int = 0
    results: list[ExecutionResult]
    total_time: float = 0.0
    started_at: datetime
    completed_at: datetime | None = None

    @property
    def success_rate(self) -> float

    def get_failed_tasks(self) -> list[ExecutionResult]
    def get_successful_tasks(self) -> list[ExecutionResult]
```

---

### ParallelExecutor

并行执行器。

```python
class ParallelExecutor:
    def __init__(self, config: ExecutorConfig | None = None) -> None
```

#### start / shutdown

```python
async def start(self) -> None
async def shutdown(self, wait: bool = True) -> None
```

#### execute

执行单个任务。

```python
async def execute(
    self,
    task: Task,
    executor_fn: TaskExecutorFn,
    *,
    timeout: float | None = None,
) -> ExecutionResult
```

#### execute_batch

批量执行。

```python
async def execute_batch(
    self,
    tasks: Sequence[Task],
    executor_fn: TaskExecutorFn,
    *,
    timeout: float | None = None,
) -> BatchResult
```

#### execute_with_dependencies

按依赖层级执行。

```python
async def execute_with_dependencies(
    self,
    tasks: Sequence[Task],
    executor_fn: TaskExecutorFn,
    execution_levels: list[list[TaskId]],
    *,
    timeout: float | None = None,
) -> BatchResult
```

#### cancel_task / cancel_all

```python
async def cancel_task(self, task_id: TaskId) -> bool
async def cancel_all(self) -> int
```

#### 属性

```python
@property
def stats(self) -> ExecutorStats

@property
def current_load(self) -> float  # 0.0 - 1.0

@property
def available_slots(self) -> int
```

#### 回调注册

```python
def on_task_start(self, callback: Callable[[Task], None]) -> None
def on_task_complete(self, callback: Callable[[ExecutionResult], None]) -> None
def on_task_error(self, callback: Callable[[Task, Exception], None]) -> None
```

---

### execute_tasks_parallel

便捷函数。

```python
async def execute_tasks_parallel(
    tasks: Sequence[Task],
    executor_fn: TaskExecutorFn,
    *,
    max_workers: int = 4,
    timeout: float = 300.0,
) -> BatchResult
```

**示例：**
```python
from chairman_agents.orchestration.parallel_executor import execute_tasks_parallel

async def my_executor(task: Task) -> TaskResult:
    # 执行任务逻辑
    return TaskResult(task_id=task.id, success=True)

result = await execute_tasks_parallel(
    tasks,
    my_executor,
    max_workers=8,
    timeout=60.0,
)
print(f"成功率: {result.success_rate:.2%}")
```
