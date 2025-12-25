# Team 模块 API

团队构建和角色分配。

## team_builder 模块

### 枚举

#### TeamFormationStrategy

团队组建策略。

| 值 | 说明 |
|---|---|
| `MINIMAL` | 最小团队，只选择核心必需专家 |
| `BALANCED` | 平衡团队，兼顾能力覆盖和规模 |
| `COMPREHENSIVE` | 全面团队，尽可能覆盖所有相关能力 |
| `SPECIALIZED` | 专业团队，优先选择特定领域顶尖专家 |

#### TeamStatus

团队状态。

| 值 | 说明 |
|---|---|
| `FORMING` | 组建中 |
| `READY` | 就绪 |
| `ACTIVE` | 活跃 |
| `PAUSED` | 暂停 |
| `DISBANDED` | 已解散 |

### 数据类

#### TeamMember

团队成员。

```python
@dataclass
class TeamMember:
    agent_id: AgentId
    profile: AgentProfile
    team_role: str = "member"
    is_lead: bool = False
    assigned_capabilities: list[AgentCapability] = field(default_factory=list)
    availability: float = 1.0  # 0.0-1.0
    current_load: float = 0.0  # 0.0-1.0
    joined_at: datetime = field(default_factory=datetime.now)
```

#### TeamConfiguration

团队配置。

```python
@dataclass
class TeamConfiguration:
    min_size: int = 1
    max_size: int = 10
    required_capabilities: list[AgentCapability] = field(default_factory=list)
    preferred_roles: list[AgentRole] = field(default_factory=list)
    formation_strategy: TeamFormationStrategy = TeamFormationStrategy.BALANCED
    allow_role_overlap: bool = True
    require_lead: bool = True
    min_expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
```

#### Team

团队。

```python
@dataclass
class Team:
    id: str
    name: str
    members: list[TeamMember]
    configuration: TeamConfiguration
    status: TeamStatus = TeamStatus.FORMING
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def lead(self) -> TeamMember | None

    @property
    def size(self) -> int

    @property
    def capabilities(self) -> set[AgentCapability]

    def has_capability(self, capability: AgentCapability) -> bool
    def get_member(self, agent_id: AgentId) -> TeamMember | None
    def add_member(self, member: TeamMember) -> None
    def remove_member(self, agent_id: AgentId) -> bool
```

---

### TeamBuilder

团队构建器。

```python
class TeamBuilder:
    def __init__(
        self,
        agent_registry: AgentRegistryProtocol,
        *,
        default_strategy: TeamFormationStrategy = TeamFormationStrategy.BALANCED,
    ) -> None
```

#### build_team

构建团队。

```python
async def build_team(
    self,
    task: Task,
    *,
    min_experts: int = 1,
    max_experts: int = 5,
    strategy: TeamFormationStrategy | None = None,
    required_capabilities: list[AgentCapability] | None = None,
    name: str | None = None,
) -> Team
```

**参数：**
- `task` - 目标任务
- `min_experts` - 最少专家数
- `max_experts` - 最多专家数
- `strategy` - 组建策略
- `required_capabilities` - 必需能力
- `name` - 团队名称

**返回：** 组建的Team对象

#### select_experts

智能选择专家。

```python
async def select_experts(
    self,
    required_capabilities: list[AgentCapability],
    *,
    min_count: int = 1,
    max_count: int = 5,
    min_expertise: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE,
    strategy: TeamFormationStrategy | None = None,
) -> list[AgentProfile]
```

#### build_review_team

构建审查团队。

```python
async def build_review_team(
    self,
    artifact_type: str,
    *,
    size: int = 3,
) -> Team
```

#### build_development_team

构建开发团队。

```python
async def build_development_team(
    self,
    task: Task,
    *,
    include_tester: bool = True,
    include_reviewer: bool = True,
) -> Team
```

#### build_security_team

构建安全团队。

```python
async def build_security_team(
    self,
    *,
    size: int = 2,
) -> Team
```

**示例：**
```python
from chairman_agents.team.team_builder import TeamBuilder, TeamFormationStrategy

builder = TeamBuilder(agent_registry)

# 根据任务构建团队
team = await builder.build_team(
    task=complex_task,
    min_experts=3,
    max_experts=6,
    strategy=TeamFormationStrategy.COMPREHENSIVE,
)

print(f"团队成员: {team.size}")
print(f"团队能力: {team.capabilities}")

# 构建专门的开发团队
dev_team = await builder.build_development_team(
    task=dev_task,
    include_tester=True,
    include_reviewer=True,
)
```

---

## role_assignment 模块

### 枚举

#### AssignmentStrategy

角色分配策略。

| 值 | 说明 |
|---|---|
| `GREEDY` | 贪心策略，优先分配最佳匹配 |
| `BALANCED` | 平衡策略，均衡负载 |
| `ROUND_ROBIN` | 轮询策略 |
| `PRIORITY_FIRST` | 优先级优先 |
| `EXPERTISE_MATCH` | 专业匹配 |

#### AssignmentStatus

分配状态。

| 值 | 说明 |
|---|---|
| `PENDING` | 待分配 |
| `ASSIGNED` | 已分配 |
| `ACCEPTED` | 已接受 |
| `REJECTED` | 已拒绝 |
| `COMPLETED` | 已完成 |

### 数据类

#### RoleAssignment

角色分配。

```python
@dataclass
class RoleAssignment:
    id: str
    task_id: TaskId
    agent_id: AgentId
    role: AgentRole
    capabilities_required: list[AgentCapability]
    status: AssignmentStatus = AssignmentStatus.PENDING
    assigned_at: datetime = field(default_factory=datetime.now)
    score: float = 0.0  # 匹配分数
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### AssignmentPlan

分配计划。

```python
@dataclass
class AssignmentPlan:
    id: str
    task_id: TaskId
    assignments: list[RoleAssignment]
    strategy: AssignmentStrategy
    created_at: datetime
    total_score: float = 0.0
    coverage: float = 0.0  # 能力覆盖率
```

---

### RoleAssigner

角色分配器。

```python
class RoleAssigner:
    def __init__(
        self,
        agent_registry: AgentRegistryProtocol,
        *,
        default_strategy: AssignmentStrategy = AssignmentStrategy.BALANCED,
    ) -> None
```

#### assign_roles

为任务分配角色。

```python
async def assign_roles(
    self,
    task: Task,
    available_agents: list[AgentId],
    *,
    strategy: AssignmentStrategy | None = None,
) -> AssignmentPlan
```

#### assign_single

分配单个角色。

```python
async def assign_single(
    self,
    task: Task,
    role: AgentRole,
    available_agents: list[AgentId],
) -> RoleAssignment | None
```

#### reassign

重新分配。

```python
async def reassign(
    self,
    assignment: RoleAssignment,
    available_agents: list[AgentId],
    exclude_current: bool = True,
) -> RoleAssignment | None
```

#### auto_assign

自动分配（基于任务分析）。

```python
async def auto_assign(
    self,
    task: Task,
) -> AssignmentPlan
```

#### optimize_assignments

优化现有分配。

```python
async def optimize_assignments(
    self,
    plan: AssignmentPlan,
    available_agents: list[AgentId],
) -> AssignmentPlan
```

**示例：**
```python
from chairman_agents.team.role_assignment import RoleAssigner, AssignmentStrategy

assigner = RoleAssigner(agent_registry)

# 自动分配
plan = await assigner.auto_assign(task)
print(f"分配方案评分: {plan.total_score}")
print(f"能力覆盖率: {plan.coverage:.2%}")

# 指定策略分配
plan = await assigner.assign_roles(
    task=task,
    available_agents=available_agent_ids,
    strategy=AssignmentStrategy.EXPERTISE_MATCH,
)

# 优化分配
optimized_plan = await assigner.optimize_assignments(
    plan=plan,
    available_agents=all_agent_ids,
)
```

---

## 完整工作流示例

```python
from chairman_agents.team import TeamBuilder, RoleAssigner
from chairman_agents.team.team_builder import TeamFormationStrategy
from chairman_agents.team.role_assignment import AssignmentStrategy

# 1. 构建团队
builder = TeamBuilder(agent_registry)
team = await builder.build_team(
    task=project_task,
    strategy=TeamFormationStrategy.BALANCED,
)

# 2. 分配角色
assigner = RoleAssigner(agent_registry)
available_agents = [m.agent_id for m in team.members]
plan = await assigner.assign_roles(
    task=project_task,
    available_agents=available_agents,
    strategy=AssignmentStrategy.EXPERTISE_MATCH,
)

# 3. 激活团队
team.status = TeamStatus.ACTIVE

# 4. 执行任务
for assignment in plan.assignments:
    agent = agent_registry.get_agent(assignment.agent_id)
    result = await agent.run(project_task)

# 5. 解散团队
team.status = TeamStatus.DISBANDED
```
