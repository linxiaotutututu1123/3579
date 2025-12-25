# Agents 模块 API

智能体基类和协作机制。

## base 模块

### 枚举

#### CollaborationStatus

协作请求状态。

| 值 | 说明 |
|---|---|
| `PENDING` | 待处理 |
| `IN_PROGRESS` | 处理中 |
| `COMPLETED` | 已完成 |
| `REJECTED` | 已拒绝 |
| `EXPIRED` | 已过期 |

### 数据类

#### AgentConfig

智能体配置。

```python
@dataclass
class AgentConfig:
    name: str = ""
    description: str = ""
    expertise_level: ExpertiseLevel = ExpertiseLevel.SENIOR
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3
    timeout_seconds: int = 300
    reflection_enabled: bool = True
    planning_depth: int = 3
    memory_storage_path: str | None = None
```

#### ReviewRequest

代码审查请求。

```python
@dataclass
class ReviewRequest:
    id: str
    requester_id: AgentId
    artifact: Artifact | None = None
    priority: int = 3  # 1-5, 数字越小优先级越高
    context: dict[str, Any]
    status: CollaborationStatus
    created_at: datetime
    deadline: datetime | None = None
    assigned_reviewer_id: AgentId | None = None
    review_comments: list[ReviewComment]

    def is_expired(self) -> bool
    def add_comment(self, comment: ReviewComment) -> None
    def mark_completed(self) -> None
```

#### HelpRequest

帮助请求。

```python
@dataclass
class HelpRequest:
    id: str
    requester_id: AgentId
    problem_description: str
    required_capabilities: list[AgentCapability]
    context: dict[str, Any]
    status: CollaborationStatus
    created_at: datetime
    helper_id: AgentId | None = None
    response: str | None = None
```

#### FeedbackItem

反馈项。

```python
@dataclass
class FeedbackItem:
    id: str
    review_id: str
    provider_id: AgentId
    comment: str
    severity: str = "info"  # info, suggestion, warning, error, critical
    category: str = "general"  # style, logic, security, performance
    suggested_fix: str | None = None
    created_at: datetime
    resolved: bool = False
```

---

### BaseExpertAgent

专家智能体抽象基类。

```python
class BaseExpertAgent(ABC):
    # 子类必须定义
    role: AgentRole
    capabilities: list[AgentCapability] = []
    allowed_tools: list[ToolType] = []
```

#### 初始化

```python
def __init__(
    self,
    llm_client: LLMClientProtocol,
    config: AgentConfig | None = None,
    *,
    tool_executor: ToolExecutorProtocol | None = None,
    memory_system: MemorySystem | None = None,
    message_broker: MessageBrokerProtocol | None = None,
    agent_registry: AgentRegistryProtocol | None = None,
) -> None
```

#### 属性

```python
@property
def id(self) -> AgentId

@property
def profile(self) -> AgentProfile

@property
def state(self) -> AgentState

@property
def reasoning_engine(self) -> ReasoningEngine

@property
def memory(self) -> MemorySystem

@property
def is_idle(self) -> bool

@property
def is_working(self) -> bool

@property
def current_task_id(self) -> TaskId | None
```

#### execute (抽象方法)

执行任务，子类必须实现。

```python
@abstractmethod
async def execute(self, task: Task) -> TaskResult
```

#### run

带生命周期管理的任务执行。

```python
async def run(self, task: Task) -> TaskResult
```

自动处理：
- 状态转换（idle → working → idle）
- 能力验证
- 错误处理
- 执行历史记录

#### reason

使用推理引擎分析问题。

```python
async def reason(
    self,
    problem: str,
    context: dict[str, Any] | None = None,
    *,
    strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT,
) -> ReasoningResult
```

#### remember

存储记忆。

```python
async def remember(
    self,
    content: str,
    memory_type: str = "episodic",
    importance: float = 0.5,
    metadata: dict[str, Any] | None = None,
) -> MemoryItem
```

#### recall

检索记忆。

```python
async def recall(
    self,
    query: str,
    memory_types: list[str] | None = None,
    limit: int = 5,
) -> list[tuple[MemoryItem, float]]
```

#### request_review

请求代码审查。

```python
async def request_review(
    self,
    artifact: Artifact,
    priority: int = 3,
    context: dict[str, Any] | None = None,
    deadline: datetime | None = None,
) -> ReviewRequest
```

#### provide_feedback

提供反馈。

```python
async def provide_feedback(
    self,
    review_id: str,
    comment: str,
    severity: str = "info",
    category: str = "general",
    suggested_fix: str | None = None,
) -> FeedbackItem
```

#### request_help

请求帮助。

```python
async def request_help(
    self,
    problem: str,
    required_capabilities: list[AgentCapability] | None = None,
    context: dict[str, Any] | None = None,
) -> HelpRequest
```

#### 辅助方法

```python
def has_capability(self, capability: AgentCapability) -> bool

def create_artifact(
    self,
    content: Any,
    artifact_type: ArtifactType,
    name: str = "",
    metadata: dict[str, Any] | None = None,
) -> Artifact

def create_success_result(
    self,
    task_id: TaskId,
    artifacts: list[Artifact] | None = None,
    output: Any = None,
    metrics: dict[str, Any] | None = None,
) -> TaskResult

def create_failure_result(
    self,
    task_id: TaskId,
    error: str,
    metrics: dict[str, Any] | None = None,
) -> TaskResult
```

---

## 使用示例

### 创建自定义智能体

```python
from chairman_agents.agents.base import BaseExpertAgent, AgentConfig
from chairman_agents.core.types import (
    AgentRole,
    AgentCapability,
    Task,
    TaskResult,
    ArtifactType,
)
from chairman_agents.cognitive.reasoning import ReasoningStrategy

class CodeReviewerAgent(BaseExpertAgent):
    """代码审查智能体。"""

    role = AgentRole.REVIEWER
    capabilities = [
        AgentCapability.CODE_REVIEW,
        AgentCapability.SECURITY_ANALYSIS,
    ]

    async def execute(self, task: Task) -> TaskResult:
        # 获取代码
        code = task.context.get("code", "")

        # 使用推理引擎分析
        analysis = await self.reason(
            problem=f"审查以下代码：\n{code}",
            context={"focus": ["security", "performance"]},
            strategy=ReasoningStrategy.REFLECTION,
        )

        # 存储审查记忆
        await self.remember(
            content=f"审查了 {task.title}",
            memory_type="episodic",
            importance=0.7,
        )

        # 创建审查报告
        report = self._generate_report(analysis)
        artifact = self.create_artifact(
            content=report,
            artifact_type=ArtifactType.DOCUMENT,
            name="review_report.md",
        )

        return self.create_success_result(
            task_id=task.id,
            artifacts=[artifact],
            output={"issues_found": len(analysis.steps)},
        )

    def _generate_report(self, analysis) -> str:
        # 生成报告逻辑
        return f"# 代码审查报告\n\n{analysis.conclusion}"
```

### 使用智能体

```python
from chairman_agents.integration.llm_client import create_llm_client, LLMConfig

# 创建LLM客户端
config = LLMConfig(api_key="sk-xxx")
llm_client = create_llm_client("anthropic", config)

# 创建智能体
agent = CodeReviewerAgent(
    llm_client=llm_client,
    config=AgentConfig(
        name="代码审查专家",
        expertise_level=ExpertiseLevel.EXPERT,
    ),
)

# 执行任务
task = Task(
    id="task_001",
    title="审查用户认证模块",
    description="审查auth.py中的安全问题",
    context={"code": open("auth.py").read()},
)

result = await agent.run(task)
print(f"审查完成: {result.success}")
```

### 智能体协作

```python
# 请求代码审查
review_request = await developer_agent.request_review(
    artifact=code_artifact,
    priority=2,
    context={"focus_areas": ["security"]},
)

# 另一个智能体提供反馈
feedback = await reviewer_agent.provide_feedback(
    review_id=review_request.id,
    comment="发现SQL注入风险",
    severity="critical",
    category="security",
    suggested_fix="使用参数化查询",
)

# 请求帮助
help_request = await junior_agent.request_help(
    problem="不确定如何实现事务处理",
    required_capabilities=[AgentCapability.DATABASE_DESIGN],
)
```
