"""专家智能体基类模块.

本模块定义了所有专家智能体的抽象基类，提供:
- 统一的智能体生命周期管理
- 推理引擎集成
- 任务执行框架
- 状态管理和消息处理

架构设计:
    BaseExpertAgent: 所有专家智能体的抽象基类

Example:
    >>> class MyExpertAgent(BaseExpertAgent):
    ...     role = AgentRole.BACKEND_ENGINEER
    ...
    ...     async def execute(self, task: Task) -> TaskResult:
    ...         # 实现具体的执行逻辑
    ...         pass
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

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
    ExpertiseLevel,
    MessageType,
    ReasoningStep,
    Task,
    TaskContext,
    TaskResult,
    TaskStatus,
    ToolType,
    generate_id,
)

if TYPE_CHECKING:
    from chairman_agents.cognitive.memory import MemorySystem


# =============================================================================
# 协议定义
# =============================================================================


class LLMClientProtocol(Protocol):
    """LLM 客户端协议."""

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成文本响应."""
        ...


class ToolExecutorProtocol(Protocol):
    """工具执行器协议."""

    async def execute(
        self,
        tool_type: ToolType,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """执行工具."""
        ...


# =============================================================================
# 智能体配置
# =============================================================================


@dataclass
class AgentConfig:
    """智能体配置.

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


# =============================================================================
# 专家智能体基类
# =============================================================================


class BaseExpertAgent(ABC):
    """专家智能体抽象基类.

    所有专家智能体都应继承此类并实现 execute 方法。
    提供统一的任务执行框架、推理引擎集成和状态管理。

    Attributes:
        role: 智能体角色（子类必须定义）
        capabilities: 智能体能力列表（子类必须定义）

    Class Attributes:
        role: AgentRole - 智能体角色
        capabilities: list[AgentCapability] - 能力列表
        allowed_tools: list[ToolType] - 允许使用的工具

    Example:
        >>> class BackendEngineerAgent(BaseExpertAgent):
        ...     role = AgentRole.BACKEND_ENGINEER
        ...     capabilities = [
        ...         AgentCapability.CODE_GENERATION,
        ...         AgentCapability.API_DESIGN,
        ...     ]
        ...
        ...     async def execute(self, task: Task) -> TaskResult:
        ...         # 实现具体逻辑
        ...         pass
    """

    # 子类必须定义的类属性
    role: AgentRole
    capabilities: list[AgentCapability] = []
    allowed_tools: list[ToolType] = []

    def __init__(
        self,
        llm_client: Any,  # LLMClientProtocol
        config: AgentConfig | None = None,
        tool_executor: Any | None = None,  # ToolExecutorProtocol
        memory_system: Any | None = None,  # MemorySystem
    ) -> None:
        """初始化专家智能体.

        Args:
            llm_client: LLM 客户端实例
            config: 智能体配置
            tool_executor: 工具执行器
            memory_system: 记忆系统
        """
        self.config = config or AgentConfig()
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.memory_system = memory_system

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

        # 初始化状态
        self._state = AgentState(
            agent_id=self._id,
            status="idle",
        )

        # 消息队列
        self._message_queue: list[AgentMessage] = []

        # 当前任务上下文
        self._current_context: TaskContext | None = None

    @property
    def id(self) -> AgentId:
        """获取智能体 ID."""
        return self._id

    @property
    def profile(self) -> AgentProfile:
        """获取智能体配置文件."""
        return self._profile

    @property
    def state(self) -> AgentState:
        """获取智能体状态."""
        return self._state

    @property
    def reasoning_engine(self) -> ReasoningEngine:
        """获取推理引擎."""
        return self._reasoning_engine

    def _create_profile(self) -> AgentProfile:
        """创建智能体配置文件."""
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
        """构建系统提示词."""
        capabilities_str = ", ".join(cap.value for cap in self.capabilities)
        return f"""你是一位资深的 {self.role.value}，专业水平为 {self.config.expertise_level.name}。

你的核心能力包括：{capabilities_str}

{self.config.description}

请始终以专业、严谨的态度完成任务，遵循最佳实践和行业标准。"""

    # =========================================================================
    # 任务执行框架
    # =========================================================================

    async def run(
        self,
        task: Task,
        context: TaskContext | None = None,
    ) -> TaskResult:
        """执行任务的主入口.

        提供完整的任务执行框架，包括：
        - 前置检查
        - 状态更新
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

            # 执行任务
            result = await self.execute(task)

            # 后置处理
            result = await self._post_execute(task, result, start_time)

            # 更新状态
            self._update_state("idle")

            return result

        except Exception as e:
            # 记录失败
            self._state.tasks_failed += 1
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
        """执行前置检查.

        Args:
            task: 要执行的任务

        Raises:
            CapabilityMismatchError: 当能力不匹配时
        """
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

    async def _post_execute(
        self,
        task: Task,
        result: TaskResult,
        start_time: float,
    ) -> TaskResult:
        """执行后置处理.

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

        # 如果启用反思，执行反思
        if self.config.reflection_enabled and result.success:
            result = await self._reflect_on_result(result)

        return result

    async def _reflect_on_result(self, result: TaskResult) -> TaskResult:
        """对执行结果进行反思.

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
        """更新智能体状态.

        Args:
            status: 新状态
            task_id: 当前任务 ID
            activity: 当前活动描述
        """
        self._state.status = status
        self._state.current_task_id = task_id
        self._state.current_activity = activity
        self._state.last_active = datetime.now()

    # =========================================================================
    # 抽象方法
    # =========================================================================

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """执行任务 - 子类必须实现.

        Args:
            task: 要执行的任务

        Returns:
            任务执行结果
        """
        ...

    # =========================================================================
    # 推理辅助方法
    # =========================================================================

    async def reason(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
        strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT,
    ) -> ReasoningResult:
        """使用推理引擎分析问题.

        Args:
            problem: 问题描述
            context: 上下文信息
            strategy: 推理策略

        Returns:
            推理结果
        """
        if strategy == ReasoningStrategy.TREE_OF_THOUGHT:
            return await self._reasoning_engine.tree_of_thought(
                problem=problem,
                context=context,
            )
        elif strategy == ReasoningStrategy.SELF_CONSISTENCY:
            return await self._reasoning_engine.self_consistency(
                problem=problem,
                context=context,
            )
        else:
            return await self._reasoning_engine.chain_of_thought(
                problem=problem,
                context=context,
            )

    # =========================================================================
    # 消息处理
    # =========================================================================

    async def receive_message(self, message: AgentMessage) -> None:
        """接收消息.

        Args:
            message: 接收到的消息
        """
        self._message_queue.append(message)
        self._state.pending_messages = len(self._message_queue)

    async def process_messages(self) -> list[AgentMessage]:
        """处理消息队列.

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
        """处理单条消息.

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
                content=f"收到帮助请求，正在处理...",
                reply_to=message.id,
            )
        return None

    # =========================================================================
    # 工具执行
    # =========================================================================

    async def use_tool(
        self,
        tool_type: ToolType,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """使用工具.

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
        """检查是否具有指定能力.

        Args:
            capability: 要检查的能力
            min_level: 最低能力等级

        Returns:
            是否具有该能力
        """
        return self._profile.has_capability(capability, min_level)

    def create_artifact(
        self,
        content: str,
        artifact_type: Any,
        name: str = "",
        **metadata: Any,
    ) -> Artifact:
        """创建产出物.

        Args:
            content: 产出物内容
            artifact_type: 产出物类型
            name: 产出物名称
            **metadata: 额外元数据

        Returns:
            创建的产出物
        """
        from chairman_agents.core.types import ArtifactType

        return Artifact(
            type=artifact_type if isinstance(artifact_type, ArtifactType)
                 else ArtifactType.SOURCE_CODE,
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
        **metrics: float,
    ) -> TaskResult:
        """创建成功的任务结果.

        Args:
            task_id: 任务 ID
            artifacts: 产出物列表
            reasoning_trace: 推理轨迹
            confidence: 置信度
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
        )

    def create_failure_result(
        self,
        task_id: str,
        error_message: str,
        error_type: str = "execution_error",
        partial_artifacts: list[Artifact] | None = None,
    ) -> TaskResult:
        """创建失败的任务结果.

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

    def __repr__(self) -> str:
        """返回智能体的简洁表示."""
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
    "BaseExpertAgent",
    "AgentConfig",
    "LLMClientProtocol",
    "ToolExecutorProtocol",
]
