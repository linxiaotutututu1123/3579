"""Base Expert Agent Module for Chairman Agents.

This module provides the abstract base class for all expert agents in the
Chairman Agents system. Expert agents are specialized AI agents that possess
domain-specific knowledge and capabilities.

Classes:
    BaseExpertAgent: Abstract base class for all expert agents

Example:
    >>> class CustomExpertAgent(BaseExpertAgent):
    ...     role = AgentRole.BACKEND_ENGINEER
    ...
    ...     async def execute(self, task: Task) -> TaskResult:
    ...         # Implementation here
    ...         pass
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ...core.types import (
    AgentCapability,
    AgentId,
    AgentProfile,
    AgentRole,
    AgentState,
    Artifact,
    ExpertiseLevel,
    ReasoningStep,
    Task,
    TaskResult,
    TaskStatus,
    ToolType,
    generate_id,
)

if TYPE_CHECKING:
    from ...cognitive.memory import MemorySystem
    from ...cognitive.reasoning import ReasoningEngine


# =============================================================================
# Logging Configuration
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# Protocol Definitions
# =============================================================================


@runtime_checkable
class LLMClientProtocol(Protocol):
    """Protocol for LLM client interface.

    Any LLM client used by expert agents must implement this protocol.
    """

    async def complete(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a completion for the given prompt.

        Args:
            prompt: The input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated completion text
        """
        ...


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ExecutionContext:
    """Context for task execution.

    Provides execution context including memory access, reasoning capabilities,
    and accumulated artifacts.

    Attributes:
        task: The task being executed
        memory_context: Retrieved relevant memories
        reasoning_trace: Steps of reasoning during execution
        artifacts: Artifacts produced during execution
        start_time: When execution started
        variables: Execution variables and state
    """

    task: Task
    """The task being executed"""

    memory_context: list[str] = field(default_factory=list)
    """Relevant memories retrieved for this execution"""

    reasoning_trace: list[ReasoningStep] = field(default_factory=list)
    """Steps of reasoning during execution"""

    artifacts: list[Artifact] = field(default_factory=list)
    """Artifacts produced during execution"""

    start_time: datetime = field(default_factory=datetime.now)
    """When execution started"""

    variables: dict[str, Any] = field(default_factory=dict)
    """Execution variables and state"""


# =============================================================================
# Base Expert Agent Class
# =============================================================================


class BaseExpertAgent(ABC):
    """Abstract base class for all expert agents.

    Expert agents are specialized AI agents with domain-specific knowledge
    and capabilities. Each expert agent:
    - Has a specific role (e.g., QA Engineer, Security Architect)
    - Possesses relevant capabilities for their domain
    - Uses cognitive systems for reasoning and memory
    - Can execute tasks and produce artifacts

    Subclasses must:
    - Define the `role` class attribute
    - Implement the `execute` method
    - Optionally override capability configuration

    Attributes:
        id: Unique agent identifier
        name: Human-readable agent name
        profile: Full agent profile configuration
        state: Current runtime state

    Example:
        >>> class QAEngineerAgent(BaseExpertAgent):
        ...     role = AgentRole.QA_ENGINEER
        ...
        ...     async def execute(self, task: Task) -> TaskResult:
        ...         # QA-specific execution logic
        ...         pass
    """

    # Class-level role definition (must be overridden by subclasses)
    role: AgentRole = AgentRole.BACKEND_ENGINEER
    """The role of this expert agent"""

    # Default capabilities for this agent type
    default_capabilities: list[AgentCapability] = []
    """Default capabilities for this agent type"""

    # Default expertise level
    default_expertise_level: ExpertiseLevel = ExpertiseLevel.SENIOR
    """Default expertise level for this agent type"""

    def __init__(
        self,
        profile: AgentProfile | None = None,
        llm_client: LLMClientProtocol | None = None,
        reasoning_engine: ReasoningEngine | None = None,
        memory_system: MemorySystem | None = None,
        name: str | None = None,
    ):
        """Initialize the expert agent.

        Args:
            profile: Agent profile configuration. If None, creates default.
            llm_client: LLM client for text generation
            reasoning_engine: Reasoning engine for cognitive operations
            memory_system: Memory system for context retrieval
            name: Optional agent name override
        """
        # Generate or use provided profile
        if profile is None:
            profile = self._create_default_profile(name)

        self.profile = profile
        self._llm_client = llm_client
        self._reasoning_engine = reasoning_engine
        self._memory_system = memory_system

        # Initialize state
        self.state = AgentState(
            agent_id=profile.id,
            status="idle",
        )

        logger.info(
            "Initialized %s agent: id=%s, name=%s, expertise=%s",
            self.role.value,
            profile.id,
            profile.name,
            profile.expertise_level.value,
        )

    # =========================================================================
    # Properties
    # =========================================================================

    @property
    def id(self) -> AgentId:
        """Get the agent's unique identifier."""
        return self.profile.id

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self.profile.name

    @property
    def capabilities(self) -> list[AgentCapability]:
        """Get the agent's capabilities."""
        return self.profile.capabilities

    @property
    def expertise_level(self) -> ExpertiseLevel:
        """Get the agent's expertise level."""
        return self.profile.expertise_level

    @property
    def is_busy(self) -> bool:
        """Check if the agent is currently busy."""
        return self.state.status in ("working", "reviewing", "debating")

    # =========================================================================
    # Abstract Methods
    # =========================================================================

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute a task and return the result.

        This is the main method that subclasses must implement. It should:
        1. Validate the task is appropriate for this agent
        2. Use reasoning and memory systems as needed
        3. Produce artifacts and results
        4. Handle errors appropriately

        Args:
            task: The task to execute

        Returns:
            TaskResult containing execution outcome and artifacts
        """
        ...

    # =========================================================================
    # Task Validation
    # =========================================================================

    def can_execute(self, task: Task) -> bool:
        """Check if this agent can execute the given task.

        Validates:
        - Agent has required capabilities
        - Agent meets minimum expertise level
        - Agent role matches required role (if specified)
        - Agent has required tools

        Args:
            task: The task to validate

        Returns:
            True if the agent can execute the task
        """
        # Check role requirement
        if task.required_role is not None and task.required_role != self.role:
            return False

        # Check expertise level
        if self.expertise_level.value < task.min_expertise_level.value:
            return False

        # Check required capabilities
        for capability in task.required_capabilities:
            if not self.profile.has_capability(capability):
                return False

        # Check required tools
        for tool in task.required_tools:
            if not self.profile.can_use_tool(tool):
                return False

        return True

    def get_missing_requirements(self, task: Task) -> dict[str, list[str]]:
        """Get missing requirements for a task.

        Args:
            task: The task to check

        Returns:
            Dictionary of missing requirements by category
        """
        missing: dict[str, list[str]] = {
            "capabilities": [],
            "tools": [],
            "expertise": [],
            "role": [],
        }

        # Check role
        if task.required_role is not None and task.required_role != self.role:
            missing["role"].append(
                f"Required: {task.required_role.value}, Have: {self.role.value}"
            )

        # Check expertise
        if self.expertise_level.value < task.min_expertise_level.value:
            missing["expertise"].append(
                f"Required: {task.min_expertise_level.value}, "
                f"Have: {self.expertise_level.value}"
            )

        # Check capabilities
        for capability in task.required_capabilities:
            if not self.profile.has_capability(capability):
                missing["capabilities"].append(capability.value)

        # Check tools
        for tool in task.required_tools:
            if not self.profile.can_use_tool(tool):
                missing["tools"].append(tool.value)

        return {k: v for k, v in missing.items() if v}

    # =========================================================================
    # Execution Helpers
    # =========================================================================

    async def _prepare_execution(self, task: Task) -> ExecutionContext:
        """Prepare context for task execution.

        Retrieves relevant memories, sets up reasoning trace,
        and initializes execution context.

        Args:
            task: The task to prepare for

        Returns:
            ExecutionContext for the task
        """
        context = ExecutionContext(task=task)

        # Retrieve relevant memories if memory system is available
        if self._memory_system is not None:
            try:
                memories = await self._memory_system.retrieve(
                    query=f"{task.title} {task.description}",
                    limit=10,
                )
                context.memory_context = [m.content for m in memories]
            except Exception as e:
                logger.warning("Failed to retrieve memories: %s", e)

        # Update agent state
        self.state.status = "working"
        self.state.current_task_id = task.id
        self.state.current_activity = f"Executing: {task.title}"
        self.state.thinking = True

        # Update task status
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()

        logger.info(
            "Agent %s starting task %s: %s",
            self.id, task.id, task.title
        )

        return context

    async def _finalize_execution(
        self,
        context: ExecutionContext,
        success: bool,
        error_message: str | None = None,
    ) -> TaskResult:
        """Finalize task execution and create result.

        Updates agent state, calculates metrics, and creates
        the final TaskResult.

        Args:
            context: The execution context
            success: Whether execution succeeded
            error_message: Error message if failed

        Returns:
            TaskResult with execution outcome
        """
        # Calculate execution time
        execution_time = (datetime.now() - context.start_time).total_seconds()

        # Update task status
        context.task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        context.task.completed_at = datetime.now()

        # Update agent state
        self.state.status = "idle"
        self.state.current_task_id = None
        self.state.current_activity = None
        self.state.thinking = False
        self.state.last_active = datetime.now()

        if success:
            self.state.tasks_completed += 1
        else:
            self.state.tasks_failed += 1

        # Calculate average task time
        total_tasks = self.state.tasks_completed + self.state.tasks_failed
        self.state.average_task_time = (
            (self.state.average_task_time * (total_tasks - 1) + execution_time)
            / total_tasks
        )

        # Calculate success rate
        self.state.success_rate = self.state.tasks_completed / total_tasks

        # Create result
        result = TaskResult(
            task_id=context.task.id,
            success=success,
            artifacts=context.artifacts,
            reasoning_trace=context.reasoning_trace,
            execution_time_seconds=execution_time,
            error_message=error_message,
        )

        # Store result in task
        context.task.result = result

        logger.info(
            "Agent %s %s task %s in %.2fs",
            self.id,
            "completed" if success else "failed",
            context.task.id,
            execution_time,
        )

        return result

    # =========================================================================
    # Profile Creation
    # =========================================================================

    def _create_default_profile(self, name: str | None = None) -> AgentProfile:
        """Create a default profile for this agent type.

        Args:
            name: Optional name override

        Returns:
            Default AgentProfile for this agent type
        """
        role_name = self.role.value.replace("_", " ").title()
        agent_name = name or f"{role_name} Agent"

        return AgentProfile(
            id=generate_id("agent"),
            name=agent_name,
            role=self.role,
            capabilities=self.default_capabilities.copy(),
            expertise_level=self.default_expertise_level,
            allowed_tools=[
                ToolType.CODE_EXECUTOR,
                ToolType.FILE_SYSTEM,
                ToolType.GIT,
                ToolType.TERMINAL,
            ],
        )

    # =========================================================================
    # Message Handling (for pair programming compatibility)
    # =========================================================================

    async def receive_message(self, message: Any) -> None:
        """Receive and process a message.

        This method is used for pair programming and inter-agent
        communication.

        Args:
            message: The message to process
        """
        logger.debug(
            "Agent %s received message: %s",
            self.id,
            getattr(message, "content", str(message))[:100],
        )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "BaseExpertAgent",
    "ExecutionContext",
    "LLMClientProtocol",
]
