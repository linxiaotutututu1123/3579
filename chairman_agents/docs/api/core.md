# Core 模块 API

核心类型定义、枚举和协议接口。

## 类型别名

```python
AgentId = str      # 智能体唯一标识
TaskId = str       # 任务唯一标识
ArtifactId = str   # 制品唯一标识
```

### generate_id

生成带前缀的唯一ID。

```python
def generate_id(prefix: str = "id") -> str
```

**参数：**
- `prefix` - ID前缀，默认"id"

**返回：** 格式为 `{prefix}_{uuid}` 的字符串

**示例：**
```python
task_id = generate_id("task")  # "task_a1b2c3d4..."
```

---

## 枚举

### AgentRole

智能体角色枚举，定义18种角色。

| 值 | 说明 |
|---|---|
| `ARCHITECT` | 架构师 |
| `DEVELOPER` | 开发者 |
| `SENIOR_DEVELOPER` | 高级开发者 |
| `JUNIOR_DEVELOPER` | 初级开发者 |
| `REVIEWER` | 评审员 |
| `TESTER` | 测试员 |
| `RESEARCHER` | 研究员 |
| `COORDINATOR` | 协调员 |
| `ANALYST` | 分析师 |
| `DESIGNER` | 设计师 |
| `SECURITY_EXPERT` | 安全专家 |
| `PERFORMANCE_EXPERT` | 性能专家 |
| `DOCUMENTATION_WRITER` | 文档编写者 |
| `PROJECT_MANAGER` | 项目经理 |
| `DOMAIN_EXPERT` | 领域专家 |
| `QA_ENGINEER` | QA工程师 |
| `DEVOPS_ENGINEER` | DevOps工程师 |
| `GENERAL` | 通用智能体 |

### ExpertiseLevel

专业级别枚举。

| 值 | 说明 |
|---|---|
| `NOVICE` | 新手 |
| `BEGINNER` | 初学者 |
| `INTERMEDIATE` | 中级 |
| `ADVANCED` | 高级 |
| `EXPERT` | 专家 |
| `MASTER` | 大师 |

### TaskStatus

任务状态枚举。

| 值 | 说明 |
|---|---|
| `PENDING` | 等待中 |
| `ASSIGNED` | 已分配 |
| `IN_PROGRESS` | 执行中 |
| `BLOCKED` | 阻塞 |
| `COMPLETED` | 已完成 |
| `FAILED` | 失败 |
| `CANCELLED` | 已取消 |

### TaskPriority

任务优先级枚举。

| 值 | 数值 | 说明 |
|---|---|---|
| `CRITICAL` | 0 | 紧急 |
| `HIGH` | 1 | 高 |
| `MEDIUM` | 2 | 中 |
| `LOW` | 3 | 低 |
| `OPTIONAL` | 4 | 可选 |

### AgentCapability

智能体能力枚举，定义35种能力。

主要能力类别：
- 代码相关：`CODE_GENERATION`, `CODE_REVIEW`, `CODE_REFACTORING`, `CODE_DEBUGGING`
- 测试相关：`UNIT_TESTING`, `INTEGRATION_TESTING`, `PERFORMANCE_TESTING`
- 分析相关：`REQUIREMENT_ANALYSIS`, `ARCHITECTURE_DESIGN`, `SECURITY_ANALYSIS`
- 文档相关：`DOCUMENTATION`, `API_DESIGN`, `TECHNICAL_WRITING`

---

## 数据类

### Task

任务定义。

```python
@dataclass
class Task:
    id: TaskId
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[TaskId] = field(default_factory=list)
    assigned_to: AgentId | None = None
    estimated_hours: float = 1.0
    complexity: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

**属性：**
- `id` - 任务唯一ID
- `title` - 任务标题
- `description` - 任务描述
- `priority` - 优先级
- `status` - 当前状态
- `dependencies` - 依赖的任务ID列表
- `assigned_to` - 分配的智能体ID
- `estimated_hours` - 预估工时
- `complexity` - 复杂度(1-10)

### TaskResult

任务执行结果。

```python
@dataclass
class TaskResult:
    task_id: TaskId
    success: bool
    output: Any = None
    error: str | None = None
    artifacts: list[Artifact] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=datetime.now)
```

### AgentProfile

智能体配置文件。

```python
@dataclass
class AgentProfile:
    id: AgentId
    name: str
    role: AgentRole
    capabilities: set[AgentCapability]
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    specializations: list[str] = field(default_factory=list)
    max_concurrent_tasks: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Artifact

任务产出物。

```python
@dataclass
class Artifact:
    id: ArtifactId
    name: str
    artifact_type: ArtifactType
    content: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
```

---

## 协议接口

### LLMClientProtocol

LLM客户端协议。

```python
@runtime_checkable
class LLMClientProtocol(Protocol):
    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> str: ...

    async def complete(
        self,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> dict[str, Any]: ...
```

### ToolExecutorProtocol

工具执行协议。

```python
@runtime_checkable
class ToolExecutorProtocol(Protocol):
    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> Any: ...
```

### MessageBrokerProtocol

消息代理协议。

```python
@runtime_checkable
class MessageBrokerProtocol(Protocol):
    async def send_message(
        self,
        sender_id: AgentId,
        receiver_id: AgentId,
        message: AgentMessage,
    ) -> None: ...

    async def receive_messages(
        self,
        agent_id: AgentId,
        timeout: float | None = None,
    ) -> list[AgentMessage]: ...

    async def broadcast(
        self,
        sender_id: AgentId,
        message: AgentMessage,
    ) -> None: ...
```

### AgentRegistryProtocol

智能体注册协议。

```python
@runtime_checkable
class AgentRegistryProtocol(Protocol):
    def find_agents_by_capability(
        self,
        capability: AgentCapability,
    ) -> list[AgentProfile]: ...

    def find_agents_by_role(
        self,
        role: AgentRole,
    ) -> list[AgentProfile]: ...

    def get_agent_profile(
        self,
        agent_id: AgentId,
    ) -> AgentProfile | None: ...
```
