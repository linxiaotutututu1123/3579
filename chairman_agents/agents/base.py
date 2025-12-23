"""
专家智能体基类模块。

本模块定义了所有专家智能体的基类 BaseExpertAgent，提供:
- 任务执行框架 (execute, run)
- 认知推理能力 (reason)
- 记忆管理 (remember, recall)
- 协作机制 (request_review, provide_feedback)
- 状态管理与生命周期钩子

架构设计:
    BaseExpertAgent 使用组合模式集成 ReasoningEngine 和 MemorySystem，
    通过 Protocol 定义协作接口，支持灵活的智能体间通信。

Example:
    >>> class CodeReviewerAgent(BaseExpertAgent):
    ...     role = AgentRole.CODE_REVIEWER
    ...     capabilities = [AgentCapability.CODE_REVIEW]
    ...
    ...     async def execute(self, task: Task) -> TaskResult:
    ...         reasoning = await self.reason(
    ...             problem=task.description,
    ...             context={"code": task.context.get("code")}
    ...         )
    ...         return self.create_success_result(task.id, ...)
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from chairman_agents.cognitive.memory import MemoryItem, MemoryQuery, MemorySystem
from chairman_agents.cognitive.reasoning import (
    ReasoningEngine,
    ReasoningResult,
    ReasoningStrategy,
)
from chairman_agents.core.exceptions import (
    AgentError,
    CapabilityMismatchError,
    TaskExecutionError,
)
from chairman_agents.core.types import (
    AgentCapability,
    AgentId,
    AgentMessage,
    AgentProfile,
    AgentRole,
    AgentState,
    Artifact,
    ArtifactType,
    ExpertiseLevel,
    MessageType,
    ReasoningStep,
    ReviewComment,
    Task,
    TaskContext,
    TaskId,
    TaskResult,
    TaskStatus,
    ToolType,
    generate_id,
)

if TYPE_CHECKING:
    from pathlib import Path


# =============================================================================
# 协议定义
# =============================================================================


@runtime_checkable
class LLMClientProtocol(Protocol):
    """LLM 客户端协议。

    定义与大语言模型交互所需的接口。
    """

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成文本响应。

        Args:
            prompt: 输入提示
            temperature: 采样温度
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本响应
        """
        ...


@runtime_checkable
class ToolExecutorProtocol(Protocol):
    """工具执行器协议。

    定义工具执行所需的接口。
    """

    async def execute(
        self,
        tool_type: ToolType,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行工具。

        Args:
            tool_type: 工具类型
            params: 工具参数

        Returns:
            工具执行结果
        """
        ...


@runtime_checkable
class MessageBrokerProtocol(Protocol):
    """消息代理协议。

    定义智能体间消息传递的接口。
    """

    async def send_message(self, message: AgentMessage) -> None:
        """发送消息。

        Args:
            message: 要发送的消息
        """
        ...

    async def receive_messages(
        self,
        agent_id: AgentId,
        message_types: list[MessageType] | None = None,
        limit: int = 10,
    ) -> list[AgentMessage]:
        """接收消息。

        Args:
            agent_id: 接收者智能体ID
            message_types: 消息类型过滤
            limit: 最大返回数量

        Returns:
            消息列表
        """
        ...

    async def broadcast(
        self,
        message: AgentMessage,
        target_roles: list[AgentRole] | None = None,
    ) -> None:
        """广播消息。

        Args:
            message: 要广播的消息
            target_roles: 目标角色过滤
        """
        ...


@runtime_checkable
class AgentRegistryProtocol(Protocol):
    """智能体注册表协议。

    定义智能体发现和管理的接口。
    """

    def find_agents_by_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> list[AgentId]:
        """根据能力查找智能体。

        Args:
            capability: 所需能力
            min_level: 最低能力等级

        Returns:
            符合条件的智能体ID列表
        """
        ...

    def find_agents_by_role(self, role: AgentRole) -> list[AgentId]:
        """根据角色查找智能体。

        Args:
            role: 目标角色

        Returns:
            具有该角色的智能体ID列表
        """
        ...

    def get_agent_profile(self, agent_id: AgentId) -> AgentProfile | None:
        """获取智能体配置。

        Args:
            agent_id: 智能体ID

        Returns:
            智能体配置，不存在返回 None
        """
        ...


# =============================================================================
# 协作状态和数据类
# =============================================================================


class CollaborationStatus(Enum):
    """协作请求状态枚举。"""

    PENDING = "pending"
    """待处理"""

    IN_PROGRESS = "in_progress"
    """处理中"""

    COMPLETED = "completed"
    """已完成"""

    REJECTED = "rejected"
    """已拒绝"""

    EXPIRED = "expired"
    """已过期"""


@dataclass
class ReviewRequest:
    """代码审查请求。

    用于智能体之间的代码审查协作。

    Attributes:
        id: 请求唯一标识符
        requester_id: 请求者智能体ID
        artifact: 待审查的制品
        priority: 优先级 (1-5，数字越小优先级越高)
        context: 审查上下文信息
        status: 请求状态
        created_at: 创建时间
        deadline: 截止时间

    Example:
        >>> request = ReviewRequest(
        ...     requester_id="agent_123",
        ...     artifact=my_artifact,
        ...     priority=2,
        ...     context={"focus_areas": ["security", "performance"]}
        ... )
    """

    id: str = field(default_factory=lambda: generate_id("review"))
    """请求唯一标识符"""

    requester_id: AgentId = ""
    """请求者智能体ID"""

    artifact: Artifact | None = None
    """待审查的制品"""

    priority: int = 3
    """优先级 (1-5)"""

    context: dict[str, Any] = field(default_factory=dict)
    """审查上下文信息"""

    status: CollaborationStatus = CollaborationStatus.PENDING
    """请求状态"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    deadline: datetime | None = None
    """截止时间"""

    assigned_reviewer_id: AgentId | None = None
    """分配的审查者ID"""

    review_comments: list[ReviewComment] = field(default_factory=list)
    """审查评论列表"""

    def is_expired(self) -> bool:
        """检查请求是否已过期。"""
        if self.deadline is None:
            return False
        return datetime.now() > self.deadline

    def add_comment(self, comment: ReviewComment) -> None:
        """添加审查评论。"""
        self.review_comments.append(comment)

    def mark_completed(self) -> None:
        """标记为已完成。"""
        self.status = CollaborationStatus.COMPLETED


@dataclass
class HelpRequest:
    """帮助请求。

    用于智能体之间请求技术帮助或协作。

    Attributes:
        id: 请求唯一标识符
        requester_id: 请求者智能体ID
        problem_description: 问题描述
        required_capabilities: 所需能力列表
        context: 问题上下文
        status: 请求状态
    """

    id: str = field(default_factory=lambda: generate_id("help"))
    """请求唯一标识符"""

    requester_id: AgentId = ""
    """请求者智能体ID"""

    problem_description: str = ""
    """问题描述"""

    required_capabilities: list[AgentCapability] = field(default_factory=list)
    """所需能力列表"""

    context: dict[str, Any] = field(default_factory=dict)
    """问题上下文"""

    status: CollaborationStatus = CollaborationStatus.PENDING
    """请求状态"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    helper_id: AgentId | None = None
    """帮助者智能体ID"""

    response: str | None = None
    """帮助回复"""


@dataclass
class FeedbackItem:
    """反馈项。

    表示对审查请求的单条反馈。

    Attributes:
        id: 反馈ID
        review_id: 关联的审查请求ID
        provider_id: 提供反馈的智能体ID
        comment: 反馈内容
        severity: 严重程度
        category: 反馈类别
    """

    id: str = field(default_factory=lambda: generate_id("feedback"))
    """反馈ID"""

    review_id: str = ""
    """关联的审查请求ID"""

    provider_id: AgentId = ""
    """提供反馈的智能体ID"""

    comment: str = ""
    """反馈内容"""

    severity: str = "info"
    """严重程度: info, suggestion, warning, error, critical"""

    category: str = "general"
    """反馈类别: style, logic, security, performance, etc."""

    suggested_fix: str | None = None
    """建议的修复方案"""

    created_at: datetime = field(default_factory=datetime.now)
    """创建时间"""

    resolved: bool = False
    """是否已解决"""


# =============================================================================
# 智能体配置
# =============================================================================


@dataclass
class AgentConfig:
    """智能体配置。

    Attributes:
        name: 智能体名称
        description: 智能体描述
        expertise_level: 专业水平
        temperature: LLM 温度参数
        max_tokens: 最大 token 数
        max_retries: 最大重试次数
        timeout_seconds: 超时时间（秒）
        reflection_enabled: 是否启用反思
        planning_depth: 规划深度
        memory_storage_path: 记忆存储路径
    """

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


# =============================================================================
# 专家智能体基类
# =============================================================================


class BaseExpertAgent(ABC):
    """专家智能体抽象基类。

    所有专家智能体都应继承此类并实现 execute 方法。
    提供统一的任务执行框架、推理引擎集成、记忆系统和协作机制。

    Class Attributes:
        role: AgentRole - 智能体角色（子类必须定义）
        capabilities: list[AgentCapability] - 能力列表（子类必须定义）
        allowed_tools: list[ToolType] - 允许使用的工具

    Attributes:
        config: 智能体配置
        llm_client: LLM 客户端
        reasoning_engine: 推理引擎
        memory: 记忆系统
        state: 运行时状态

    Example:
        >>> class BackendEngineerAgent(BaseExpertAgent):
        ...     role = AgentRole.BACKEND_ENGINEER
        ...     capabilities = [
        ...         AgentCapability.CODE_GENERATION,
        ...         AgentCapability.API_DESIGN,
        ...     ]
        ...
        ...     async def execute(self, task: Task) -> TaskResult:
        ...         # 使用推理引擎分析
        ...         reasoning = await self.reason(
        ...             problem=task.description,
        ...             context=task.context
        ...         )
        ...         # 生成代码
        ...         code = await self._generate_code(reasoning)
        ...         # 创建结果
        ...         artifact = self.create_artifact(code, ArtifactType.SOURCE_CODE)
        ...         return self.create_success_result(task.id, [artifact])
    """

    # 子类必须定义的类属性
    role: AgentRole
    capabilities: list[AgentCapability] = []
    allowed_tools: list[ToolType] = []

    def __init__(
        self,
        llm_client: Any,  # LLMClientProtocol
        config: AgentConfig | None = None,
        *,
        tool_executor: Any | None = None,  # ToolExecutorProtocol
        memory_system: MemorySystem | None = None,
        message_broker: MessageBrokerProtocol | None = None,
        agent_registry: AgentRegistryProtocol | None = None,
    ) -> None:
        """初始化专家智能体。

        Args:
            llm_client: LLM 客户端实例
            config: 智能体配置
            tool_executor: 工具执行器（可选）
            memory_system: 记忆系统（可选，将自动创建）
            message_broker: 消息代理（可选）
            agent_registry: 智能体注册表（可选）
        """
        self.config = config or AgentConfig()
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.message_broker = message_broker
        self.agent_registry = agent_registry

        # 生成智能体 ID
        self._id: AgentId = generate_id("agent")

        # 创建智能体配置文件
        self._profile = self._create_profile()

        # 初始化推理引擎
        self._reasoning_engine = ReasoningEngine(
            llm_client=llm_client,
            max_depth=self.config.planning_depth + 2,
            branching_factor=3,
            temperature=self.config.temperature,
        )

        # 初始化记忆系统
        self._memory = memory_system or MemorySystem(
            storage_path=None,  # 内存模式
            use_embeddings=False,
        )

        # 初始化状态
        self._state = AgentState(
            agent_id=self._id,
            status="idle",
        )

        # 消息队列
        self._message_queue: list[AgentMessage] = []

        # 当前任务上下文
        self._current_context: TaskContext | None = None

        # 协作请求追踪
        self._pending_reviews: dict[str, ReviewRequest] = {}
        self._pending_help_requests: dict[str, HelpRequest] = {}

        # 执行历史
        self._execution_history: list[TaskResult] = []

    # =========================================================================
    # 属性访问器
    # =========================================================================

    @property
    def id(self) -> AgentId:
        """获取智能体 ID。"""
        return self._id

    @property
    def agent_id(self) -> AgentId:
        """获取智能体 ID（别名）。"""
        return self._id

    @property
    def profile(self) -> AgentProfile:
        """获取智能体配置文件。"""
        return self._profile

    @property
    def state(self) -> AgentState:
        """获取智能体状态。"""
        return self._state

    @property
    def reasoning_engine(self) -> ReasoningEngine:
        """获取推理引擎。"""
        return self._reasoning_engine

    @property
    def memory(self) -> MemorySystem:
        """获取记忆系统。"""
        return self._memory

    @property
    def is_idle(self) -> bool:
        """检查智能体是否空闲。"""
        return self._state.status == "idle"

    @property
    def is_working(self) -> bool:
        """检查智能体是否正在工作。"""
        return self._state.status == "working"

    @property
    def current_task_id(self) -> TaskId | None:
        """获取当前任务ID。"""
        return self._state.current_task_id

    # =========================================================================
    # 配置创建
    # =========================================================================

    def _create_profile(self) -> AgentProfile:
        """创建智能体配置文件。"""
        # 计算能力级别（基于专业水平）
        base_level = self.config.expertise_level.value * 2
        capability_levels = {
            cap: min(base_level + (i % 3), 10)
            for i, cap in enumerate(self.capabilities)
        }

        return AgentProfile(
            id=self._id,
            name=self.config.name or f"{self.role.value}_agent",
            role=self.role,
            capabilities=list(self.capabilities),
            capability_levels=capability_levels,
            expertise_level=self.config.expertise_level,
            thinking_style="analytical",
            reflection_enabled=self.config.reflection_enabled,
            planning_depth=self.config.planning_depth,
            collaboration_style="cooperative",
            debate_skill=self.config.expertise_level.value + 4,
            consensus_flexibility=0.7,
            allowed_tools=list(self.allowed_tools),
            system_prompt=self._build_system_prompt(),
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            model="gpt-4",
            max_retries=self.config.max_retries,
            timeout_seconds=self.config.timeout_seconds,
        )

    def _build_system_prompt(self) -> str:
        """构建系统提示词。"""
        capabilities_str = ", ".join(cap.value for cap in self.capabilities)
        return f"""你是一位资深的 {self.role.value}，专业水平为 {self.config.expertise_level.name}。

你的核心能力包括：{capabilities_str}

{self.config.description}

请始终以专业、严谨的态度完成任务，遵循最佳实践和行业标准。"""

    # =========================================================================
    # 核心执行方法
    # =========================================================================

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """执行任务 - 子类必须实现。

        这是智能体的核心方法，定义具体的任务执行逻辑。
        子类应该:
        1. 分析任务需求
        2. 使用推理引擎进行认知推理
        3. 执行具体操作
        4. 生成任务制品
        5. 返回执行结果

        Args:
            task: 要执行的任务

        Returns:
            任务执行结果

        Raises:
            TaskExecutionError: 任务执行失败时抛出

        Example:
            >>> async def execute(self, task: Task) -> TaskResult:
            ...     reasoning = await self.reason(task.description)
            ...     code = await self._generate_code(reasoning)
            ...     artifact = self.create_artifact(
            ...         code, ArtifactType.SOURCE_CODE, "output.py"
            ...     )
            ...     return self.create_success_result(task.id, [artifact])
        """
        ...

    async def run(
        self,
        task: Task,
        context: TaskContext | None = None,
    ) -> TaskResult:
        """执行任务的完整生命周期。

        提供完整的任务执行框架，包括：
        - 前置检查
        - 状态更新
        - 记忆存储
        - 任务执行
        - 后置处理
        - 异常处理

        Args:
            task: 要执行的任务
            context: 任务执行上下文

        Returns:
            任务执行结果

        Raises:
            CapabilityMismatchError: 当智能体能力不匹配任务需求时
            TaskExecutionError: 当任务执行失败时
        """
        start_time = time.time()
        self._current_context = context

        try:
            # 前置检查
            await self._pre_execute_check(task)

            # 更新状态
            self._update_state("working", task.id, f"执行任务: {task.title}")

            # 记录任务开始
            await self._remember_task_start(task)

            # 执行任务
            result = await self.execute(task)

            # 后置处理
            result = await self._post_execute(task, result, start_time)

            # 记录成功
            await self._remember_task_completion(task, result)

            # 更新状态
            self._update_state("idle")

            return result

        except Exception as e:
            # 记录失败
            self._state.tasks_failed += 1
            await self._remember_task_failure(task, e)
            self._update_state("idle")

            if isinstance(e, (AgentError, TaskExecutionError)):
                raise

            raise TaskExecutionError(
                f"任务执行失败: {str(e)}",
                task_id=task.id,
                agent_id=self._id,
                agent_type=self.role.value,
                cause=e,
            ) from e

    async def _pre_execute_check(self, task: Task) -> None:
        """执行前置检查。

        Args:
            task: 要执行的任务

        Raises:
            CapabilityMismatchError: 当能力不匹配时
        """
        # 检查任务有效性
        if not task.title and not task.description:
            raise TaskExecutionError(
                "任务缺少标题和描述",
                task_id=task.id,
                agent_id=self._id,
            )

        # 检查能力匹配
        if task.required_capabilities:
            missing = [
                cap for cap in task.required_capabilities
                if cap not in self.capabilities
            ]
            if missing:
                raise CapabilityMismatchError(
                    f"智能体缺少必需的能力: {[c.value for c in missing]}",
                    required_capabilities=[c.value for c in task.required_capabilities],
                    agent_capabilities=[c.value for c in self.capabilities],
                    agent_id=self._id,
                    agent_type=self.role.value,
                )

        # 检查角色匹配
        if task.required_role and task.required_role != self.role:
            raise CapabilityMismatchError(
                f"任务需要 {task.required_role.value}，但智能体是 {self.role.value}",
                agent_id=self._id,
                agent_type=self.role.value,
            )

        # 检查专业水平
        if task.min_expertise_level.value > self.config.expertise_level.value:
            raise CapabilityMismatchError(
                f"任务需要至少 {task.min_expertise_level.name} 级别",
                agent_id=self._id,
                agent_type=self.role.value,
            )

        # 检查任务依赖
        if task.blocked_by:
            raise TaskExecutionError(
                f"任务被阻塞，依赖任务: {', '.join(task.blocked_by)}",
                task_id=task.id,
                agent_id=self._id,
            )

    async def _post_execute(
        self,
        task: Task,
        result: TaskResult,
        start_time: float,
    ) -> TaskResult:
        """执行后置处理。

        Args:
            task: 执行的任务
            result: 执行结果
            start_time: 开始时间

        Returns:
            处理后的结果
        """
        # 计算执行时间
        result.execution_time_seconds = time.time() - start_time

        # 更新统计
        if result.success:
            self._state.tasks_completed += 1
            # 更新平均任务时间
            total_tasks = self._state.tasks_completed
            prev_avg = self._state.average_task_time
            self._state.average_task_time = (
                (prev_avg * (total_tasks - 1) + result.execution_time_seconds)
                / total_tasks
            )
            # 更新平均质量分数
            if result.quality_score > 0:
                prev_quality = self._state.average_quality_score
                self._state.average_quality_score = (
                    (prev_quality * (total_tasks - 1) + result.quality_score)
                    / total_tasks
                )
            # 更新成功率
            total = self._state.tasks_completed + self._state.tasks_failed
            self._state.success_rate = self._state.tasks_completed / total

        # 如果启用反思，执行反思
        if self.config.reflection_enabled and result.success:
            result = await self._reflect_on_result(result)

        # 保存到执行历史
        self._execution_history.append(result)

        return result

    async def _reflect_on_result(self, result: TaskResult) -> TaskResult:
        """对执行结果进行反思。

        Args:
            result: 原始执行结果

        Returns:
            反思后的结果
        """
        if not result.reasoning_trace:
            return result

        # 构建反思结果
        reasoning_result = ReasoningResult(
            conclusion=result.artifacts[0].content if result.artifacts else "",
            confidence=result.confidence_score,
            reasoning_path=[],
            metadata={"task_id": result.task_id},
        )

        # 执行反思
        try:
            reflected = await self._reasoning_engine.reflect(reasoning_result)
            # 添加反思内容到结果
            if reflected.metadata.get("reflections"):
                result.reflections.extend(reflected.metadata["reflections"])
            result.confidence_score = reflected.confidence
        except Exception:
            # 反思失败不影响主结果
            pass

        return result

    def _update_state(
        self,
        status: str,
        task_id: str | None = None,
        activity: str | None = None,
    ) -> None:
        """更新智能体状态。

        Args:
            status: 新状态
            task_id: 当前任务 ID
            activity: 当前活动描述
        """
        self._state.status = status
        self._state.current_task_id = task_id
        self._state.current_activity = activity
        self._state.last_active = datetime.now()
        self._state.thinking = status == "working"

    # =========================================================================
    # 认知推理方法
    # =========================================================================

    async def reason(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
        strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT,
    ) -> ReasoningResult:
        """使用推理引擎分析问题。

        执行认知推理，支持多种推理策略。

        Args:
            problem: 问题描述
            context: 上下文信息
            strategy: 推理策略

        Returns:
            推理结果

        Example:
            >>> result = await agent.reason(
            ...     problem="如何优化数据库查询性能？",
            ...     context={"current_latency": "500ms"},
            ...     strategy=ReasoningStrategy.TREE_OF_THOUGHT
            ... )
            >>> print(result.conclusion)
        """
        # 更新状态
        self._state.thinking = True
        self._state.current_thought = f"分析问题: {problem[:50]}..."

        try:
            context = context or {}

            # 添加智能体上下文
            enhanced_context = {
                **context,
                "agent_role": self.role.value,
                "agent_expertise": self.config.expertise_level.value,
            }

            # 根据策略选择推理方法
            if strategy == ReasoningStrategy.TREE_OF_THOUGHT:
                result = await self._reasoning_engine.tree_of_thought(
                    problem=problem,
                    context=enhanced_context,
                )
            elif strategy == ReasoningStrategy.SELF_CONSISTENCY:
                result = await self._reasoning_engine.self_consistency(
                    problem=problem,
                    context=enhanced_context,
                )
            else:
                result = await self._reasoning_engine.chain_of_thought(
                    problem=problem,
                    context=enhanced_context,
                )

            # 如果启用反思且置信度较低，进行反思优化
            if self.config.reflection_enabled and result.confidence < 0.8:
                result = await self._reasoning_engine.reflect(result)

            return result

        finally:
            self._state.thinking = False
            self._state.current_thought = None

    # =========================================================================
    # 记忆管理方法
    # =========================================================================

    async def remember(
        self,
        content: str,
        importance: float = 0.5,
        memory_type: str = "episodic",
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        """存储记忆。

        将信息存储到记忆系统中。

        Args:
            content: 要记忆的内容
            importance: 重要性 (0.0-1.0)
            memory_type: 记忆类型 (episodic, semantic, procedural)
            metadata: 附加元数据

        Returns:
            创建的记忆项

        Example:
            >>> await agent.remember(
            ...     content="用户偏好使用 PostgreSQL 而非 MySQL",
            ...     importance=0.8,
            ...     memory_type="semantic",
            ...     metadata={"category": "user_preference"}
            ... )
        """
        enhanced_metadata = {
            "agent_id": self._id,
            "agent_role": self.role.value,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        memory = self._memory.store(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=enhanced_metadata,
        )

        return memory

    async def recall(
        self,
        query: str,
        limit: int = 5,
        memory_types: list[str] | None = None,
        min_relevance: float = 0.3,
    ) -> list[MemoryItem]:
        """回忆相关记忆。

        根据查询检索相关的记忆内容。

        Args:
            query: 查询内容
            limit: 最大返回数量
            memory_types: 记忆类型过滤
            min_relevance: 最小相关度阈值

        Returns:
            相关记忆列表

        Example:
            >>> memories = await agent.recall(
            ...     query="数据库优化经验",
            ...     limit=3,
            ...     memory_types=["procedural", "semantic"]
            ... )
        """
        memory_query = MemoryQuery(
            query=query,
            memory_types=memory_types,
            limit=limit,
            min_relevance=min_relevance,
            time_decay=True,
        )

        results = self._memory.retrieve(memory_query)
        return [memory for memory, _score in results]

    async def _remember_task_start(self, task: Task) -> None:
        """记录任务开始。"""
        await self.remember(
            content=f"开始执行任务: {task.title or task.description[:50]}",
            importance=0.4,
            memory_type="episodic",
            metadata={
                "event": "task_start",
                "task_id": task.id,
                "task_type": task.type,
            },
        )

    async def _remember_task_completion(
        self,
        task: Task,
        result: TaskResult,
    ) -> None:
        """记录任务完成。"""
        content = (
            f"成功完成任务: {task.title or task.description[:50]}, "
            f"置信度: {result.confidence_score:.2f}"
        )

        await self.remember(
            content=content,
            importance=0.6 + result.quality_score * 0.3,
            memory_type="episodic",
            metadata={
                "event": "task_completion",
                "task_id": task.id,
                "success": True,
                "quality_score": result.quality_score,
            },
        )

        # 如果有重要的经验教训，存储为程序性记忆
        for lesson in result.learned_lessons:
            await self.remember(
                content=lesson,
                importance=0.8,
                memory_type="procedural",
                metadata={
                    "source": "task_completion",
                    "task_id": task.id,
                },
            )

    async def _remember_task_failure(self, task: Task, error: Exception) -> None:
        """记录任务失败。"""
        await self.remember(
            content=f"任务执行失败: {task.title or task.id}, 错误: {str(error)[:100]}",
            importance=0.7,
            memory_type="episodic",
            metadata={
                "event": "task_failure",
                "task_id": task.id,
                "error_type": type(error).__name__,
            },
        )

    # =========================================================================
    # 协作方法
    # =========================================================================

    async def request_review(
        self,
        artifact: Artifact,
        priority: int = 3,
        context: dict[str, Any] | None = None,
        deadline: datetime | None = None,
    ) -> ReviewRequest:
        """请求代码审查。

        创建审查请求并通过消息代理发送给其他智能体。

        Args:
            artifact: 待审查的制品
            priority: 优先级 (1-5)
            context: 审查上下文
            deadline: 截止时间

        Returns:
            创建的审查请求

        Example:
            >>> request = await agent.request_review(
            ...     artifact=my_code_artifact,
            ...     priority=2,
            ...     context={"focus_on": ["security", "performance"]}
            ... )
        """
        request = ReviewRequest(
            id=generate_id("review"),
            requester_id=self._id,
            artifact=artifact,
            priority=priority,
            context=context or {},
            deadline=deadline,
        )

        self._pending_reviews[request.id] = request

        # 发送审查请求消息
        if self.message_broker:
            message = AgentMessage(
                type=MessageType.REQUEST_REVIEW,
                sender_id=self._id,
                subject=f"请求审查: {artifact.name}",
                content=f"请审查制品: {artifact.name}，类型: {artifact.type.value}",
                data={
                    "review_request_id": request.id,
                    "artifact_id": artifact.id,
                    "artifact_type": artifact.type.value,
                    "priority": priority,
                },
                priority=priority,
            )
            await self.message_broker.broadcast(
                message,
                target_roles=[AgentRole.CODE_REVIEWER, AgentRole.TECH_LEAD],
            )

        return request

    async def provide_feedback(
        self,
        review_id: str,
        comments: list[str],
        severity: str = "info",
        category: str = "general",
    ) -> list[FeedbackItem]:
        """提供审查反馈。

        对审查请求提供反馈意见。

        Args:
            review_id: 审查请求ID
            comments: 反馈评论列表
            severity: 严重程度
            category: 反馈类别

        Returns:
            创建的反馈项列表

        Example:
            >>> feedback = await agent.provide_feedback(
            ...     review_id="review_abc123",
            ...     comments=["建议使用更具描述性的变量名", "缺少错误处理"],
            ...     severity="suggestion",
            ...     category="style"
            ... )
        """
        feedback_items: list[FeedbackItem] = []

        for comment in comments:
            feedback = FeedbackItem(
                review_id=review_id,
                provider_id=self._id,
                comment=comment,
                severity=severity,
                category=category,
            )
            feedback_items.append(feedback)

        # 发送反馈消息
        if self.message_broker:
            message = AgentMessage(
                type=MessageType.REVIEW_FEEDBACK,
                sender_id=self._id,
                subject=f"审查反馈: {review_id}",
                content=f"提供了 {len(comments)} 条反馈",
                data={
                    "review_id": review_id,
                    "feedback_count": len(comments),
                    "severity": severity,
                    "category": category,
                    "comments": comments,
                },
            )
            await self.message_broker.send_message(message)

        return feedback_items

    async def request_help(
        self,
        problem_description: str,
        required_capabilities: list[AgentCapability] | None = None,
        context: dict[str, Any] | None = None,
    ) -> HelpRequest:
        """请求帮助。

        向其他智能体请求技术帮助。

        Args:
            problem_description: 问题描述
            required_capabilities: 所需能力
            context: 问题上下文

        Returns:
            创建的帮助请求

        Example:
            >>> help_req = await agent.request_help(
            ...     problem_description="需要优化SQL查询性能",
            ...     required_capabilities=[AgentCapability.SQL_EXPERT]
            ... )
        """
        request = HelpRequest(
            requester_id=self._id,
            problem_description=problem_description,
            required_capabilities=required_capabilities or [],
            context=context or {},
        )

        self._pending_help_requests[request.id] = request

        # 发送帮助请求消息
        if self.message_broker:
            message = AgentMessage(
                type=MessageType.REQUEST_HELP,
                sender_id=self._id,
                subject="请求帮助",
                content=problem_description[:200],
                data={
                    "help_request_id": request.id,
                    "required_capabilities": [
                        c.value for c in (required_capabilities or [])
                    ],
                },
            )
            await self.message_broker.broadcast(message)

        return request

    # =========================================================================
    # 消息处理
    # =========================================================================

    async def receive_message(self, message: AgentMessage) -> None:
        """接收消息。

        Args:
            message: 接收到的消息
        """
        self._message_queue.append(message)
        self._state.pending_messages = len(self._message_queue)

    async def process_messages(self) -> list[AgentMessage]:
        """处理消息队列。

        Returns:
            处理后的响应消息列表
        """
        responses: list[AgentMessage] = []

        while self._message_queue:
            message = self._message_queue.pop(0)
            message.read = True

            response = await self._handle_message(message)
            if response:
                responses.append(response)

            message.processed = True

        self._state.pending_messages = 0
        return responses

    async def _handle_message(self, message: AgentMessage) -> AgentMessage | None:
        """处理单条消息。

        Args:
            message: 要处理的消息

        Returns:
            响应消息，如果无需响应则返回 None
        """
        # 基础实现：子类可以覆盖
        if message.type == MessageType.REQUEST_HELP:
            return AgentMessage(
                type=MessageType.PROVIDE_HELP,
                sender_id=self._id,
                receiver_id=message.sender_id,
                subject=f"Re: {message.subject}",
                content="收到帮助请求，正在处理...",
                reply_to=message.id,
            )
        elif message.type == MessageType.REQUEST_REVIEW:
            self._state.pending_reviews += 1
            return None
        return None

    # =========================================================================
    # 工具执行
    # =========================================================================

    async def use_tool(
        self,
        tool_type: ToolType,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """使用工具。

        Args:
            tool_type: 工具类型
            params: 工具参数

        Returns:
            工具执行结果

        Raises:
            AgentError: 当工具不可用或执行失败时
        """
        if tool_type not in self.allowed_tools:
            raise AgentError(
                f"智能体无权使用工具: {tool_type.value}",
                agent_id=self._id,
                agent_type=self.role.value,
            )

        if not self.tool_executor:
            raise AgentError(
                "未配置工具执行器",
                agent_id=self._id,
                agent_type=self.role.value,
            )

        return await self.tool_executor.execute(tool_type, params)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def has_capability(
        self,
        capability: AgentCapability,
        min_level: int = 1,
    ) -> bool:
        """检查是否具有指定能力。

        Args:
            capability: 要检查的能力
            min_level: 最低能力等级

        Returns:
            是否具有该能力
        """
        return self._profile.has_capability(capability, min_level)

    def can_handle_task(self, task: Task) -> bool:
        """检查智能体是否能处理指定任务。

        Args:
            task: 要检查的任务

        Returns:
            是否能处理该任务
        """
        # 检查角色匹配
        if task.required_role and task.required_role != self.role:
            return False

        # 检查能力匹配
        for cap in task.required_capabilities:
            if not self.has_capability(cap):
                return False

        # 检查专业等级
        if task.min_expertise_level.value > self.config.expertise_level.value:
            return False

        return True

    def create_artifact(
        self,
        content: str,
        artifact_type: ArtifactType,
        name: str = "",
        **metadata: Any,
    ) -> Artifact:
        """创建产出物。

        Args:
            content: 产出物内容
            artifact_type: 产出物类型
            name: 产出物名称
            **metadata: 额外元数据

        Returns:
            创建的产出物
        """
        return Artifact(
            type=artifact_type,
            name=name or f"{self.role.value}_output",
            content=content,
            created_by=self._id,
            language=metadata.get("language"),
            framework=metadata.get("framework"),
        )

    def create_success_result(
        self,
        task_id: str,
        artifacts: list[Artifact] | None = None,
        reasoning_trace: list[ReasoningStep] | None = None,
        confidence: float = 0.8,
        suggestions: list[str] | None = None,
        learned_lessons: list[str] | None = None,
        **metrics: float,
    ) -> TaskResult:
        """创建成功的任务结果。

        Args:
            task_id: 任务 ID
            artifacts: 产出物列表
            reasoning_trace: 推理轨迹
            confidence: 置信度
            suggestions: 改进建议
            learned_lessons: 经验教训
            **metrics: 额外指标

        Returns:
            任务结果
        """
        return TaskResult(
            task_id=task_id,
            success=True,
            artifacts=artifacts or [],
            reasoning_trace=reasoning_trace or [],
            confidence_score=confidence,
            quality_score=confidence * 0.9,
            metrics=metrics,
            suggestions=suggestions or [],
            learned_lessons=learned_lessons or [],
        )

    def create_failure_result(
        self,
        task_id: str,
        error_message: str,
        error_type: str = "execution_error",
        partial_artifacts: list[Artifact] | None = None,
    ) -> TaskResult:
        """创建失败的任务结果。

        Args:
            task_id: 任务 ID
            error_message: 错误信息
            error_type: 错误类型
            partial_artifacts: 部分产出物

        Returns:
            任务结果
        """
        return TaskResult(
            task_id=task_id,
            success=False,
            artifacts=partial_artifacts or [],
            error_message=error_message,
            error_type=error_type,
            confidence_score=0.0,
            quality_score=0.0,
        )

    def get_status_summary(self) -> dict[str, Any]:
        """获取状态摘要。

        Returns:
            状态信息字典
        """
        return {
            "agent_id": self._id,
            "name": self._profile.name,
            "role": self.role.value,
            "status": self._state.status,
            "current_task": self._state.current_task_id,
            "tasks_completed": self._state.tasks_completed,
            "tasks_failed": self._state.tasks_failed,
            "success_rate": f"{self._state.success_rate:.1%}",
            "average_quality": f"{self._state.average_quality_score:.2f}",
            "memory_count": len(self._memory),
            "pending_reviews": len(self._pending_reviews),
            "pending_messages": self._state.pending_messages,
        }

    def __repr__(self) -> str:
        """返回智能体的简洁表示。"""
        return (
            f"{self.__class__.__name__}("
            f"id={self._id!r}, "
            f"role={self.role.value!r}, "
            f"status={self._state.status!r})"
        )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 基类
    "BaseExpertAgent",
    # 配置
    "AgentConfig",
    # 协作类型
    "CollaborationStatus",
    "ReviewRequest",
    "HelpRequest",
    "FeedbackItem",
    # 协议
    "LLMClientProtocol",
    "ToolExecutorProtocol",
    "MessageBrokerProtocol",
    "AgentRegistryProtocol",
]
