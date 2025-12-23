"""
Chairman Agents 异常类层次结构模块。

本模块定义了 Chairman Agents 系统中使用的所有自定义异常类，
提供了清晰的异常层次结构，便于精确的错误处理和调试。

异常层次结构:
    ChairmanAgentError (Base)
    ├── LLMError
    │   ├── LLMRateLimitError
    │   ├── LLMTimeoutError
    │   └── LLMResponseError
    ├── AgentError
    │   ├── TaskExecutionError
    │   ├── AgentNotFoundError
    │   └── CapabilityMismatchError
    ├── WorkflowError
    │   ├── QualityGateError
    │   ├── PhaseTransitionError
    │   └── DependencyError
    ├── ToolError
    │   ├── ToolExecutionError
    │   └── ToolTimeoutError
    └── ConfigurationError
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# 基础异常类
# =============================================================================

class ChairmanAgentError(Exception):
    """
    Chairman Agents 系统的基础异常类。

    所有自定义异常都应继承此类，提供统一的异常处理接口。

    Attributes:
        message: 错误描述信息
        context: 附加的上下文信息字典
        cause: 导致此异常的原始异常（如果有）

    Example:
        >>> raise ChairmanAgentError("操作失败", context={"operation": "init"})
    """

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化基础异常。

        Args:
            message: 错误描述信息
            context: 附加的上下文信息字典
            cause: 导致此异常的原始异常
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.cause = cause

        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        """返回格式化的异常信息。"""
        base_msg = self.message
        if self.context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            base_msg = f"{base_msg} [{context_str}]"
        return base_msg

    def __repr__(self) -> str:
        """返回异常的详细表示。"""
        return f"{self.__class__.__name__}({self.message!r}, context={self.context!r})"

    def to_dict(self) -> dict[str, Any]:
        """
        将异常转换为字典格式，便于序列化和日志记录。

        Returns:
            包含异常信息的字典
        """
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
            "cause": str(self.cause) if self.cause else None,
        }


# =============================================================================
# LLM 相关异常
# =============================================================================

class LLMError(ChairmanAgentError):
    """
    LLM（大语言模型）相关操作的基础异常类。

    当与 LLM 服务交互过程中发生错误时抛出此异常或其子类。

    Attributes:
        model_name: 发生错误的模型名称
        provider: LLM 服务提供商名称
    """

    def __init__(
        self,
        message: str,
        *,
        model_name: str | None = None,
        provider: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化 LLM 异常。

        Args:
            message: 错误描述信息
            model_name: 发生错误的模型名称
            provider: LLM 服务提供商名称
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if model_name:
            ctx["model_name"] = model_name
        if provider:
            ctx["provider"] = provider

        super().__init__(message, context=ctx, cause=cause)
        self.model_name = model_name
        self.provider = provider


class LLMRateLimitError(LLMError):
    """
    LLM 服务速率限制异常。

    当 API 请求超过服务提供商的速率限制时抛出。

    Attributes:
        retry_after: 建议的重试等待时间（秒）
        limit_type: 限制类型（如 "requests_per_minute", "tokens_per_day"）
    """

    def __init__(
        self,
        message: str = "LLM API 速率限制已达到",
        *,
        retry_after: float | None = None,
        limit_type: str | None = None,
        model_name: str | None = None,
        provider: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化速率限制异常。

        Args:
            message: 错误描述信息
            retry_after: 建议的重试等待时间（秒）
            limit_type: 限制类型
            model_name: 发生错误的模型名称
            provider: LLM 服务提供商名称
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if retry_after is not None:
            ctx["retry_after"] = retry_after
        if limit_type:
            ctx["limit_type"] = limit_type

        super().__init__(
            message,
            model_name=model_name,
            provider=provider,
            context=ctx,
            cause=cause,
        )
        self.retry_after = retry_after
        self.limit_type = limit_type


class LLMTimeoutError(LLMError):
    """
    LLM 服务超时异常。

    当 LLM API 请求超过预设时间限制时抛出。

    Attributes:
        timeout_seconds: 超时时间设置（秒）
        elapsed_seconds: 实际经过的时间（秒）
    """

    def __init__(
        self,
        message: str = "LLM API 请求超时",
        *,
        timeout_seconds: float | None = None,
        elapsed_seconds: float | None = None,
        model_name: str | None = None,
        provider: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化超时异常。

        Args:
            message: 错误描述信息
            timeout_seconds: 超时时间设置（秒）
            elapsed_seconds: 实际经过的时间（秒）
            model_name: 发生错误的模型名称
            provider: LLM 服务提供商名称
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if timeout_seconds is not None:
            ctx["timeout_seconds"] = timeout_seconds
        if elapsed_seconds is not None:
            ctx["elapsed_seconds"] = elapsed_seconds

        super().__init__(
            message,
            model_name=model_name,
            provider=provider,
            context=ctx,
            cause=cause,
        )
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


class LLMResponseError(LLMError):
    """
    LLM 响应错误异常。

    当 LLM 返回无效、格式错误或不符合预期的响应时抛出。

    Attributes:
        response_text: 原始响应文本（部分或全部）
        expected_format: 期望的响应格式描述
        status_code: HTTP 状态码（如果适用）
    """

    def __init__(
        self,
        message: str = "LLM 响应无效或格式错误",
        *,
        response_text: str | None = None,
        expected_format: str | None = None,
        status_code: int | None = None,
        model_name: str | None = None,
        provider: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化响应错误异常。

        Args:
            message: 错误描述信息
            response_text: 原始响应文本
            expected_format: 期望的响应格式描述
            status_code: HTTP 状态码
            model_name: 发生错误的模型名称
            provider: LLM 服务提供商名称
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if expected_format:
            ctx["expected_format"] = expected_format
        if status_code is not None:
            ctx["status_code"] = status_code

        super().__init__(
            message,
            model_name=model_name,
            provider=provider,
            context=ctx,
            cause=cause,
        )
        self.response_text = response_text
        self.expected_format = expected_format
        self.status_code = status_code


# =============================================================================
# Agent 相关异常
# =============================================================================

class AgentError(ChairmanAgentError):
    """
    智能体相关操作的基础异常类。

    当智能体初始化、执行或通信过程中发生错误时抛出此异常或其子类。

    Attributes:
        agent_id: 发生错误的智能体ID
        agent_type: 智能体类型
    """

    def __init__(
        self,
        message: str,
        *,
        agent_id: str | None = None,
        agent_type: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化智能体异常。

        Args:
            message: 错误描述信息
            agent_id: 发生错误的智能体ID
            agent_type: 智能体类型
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if agent_id:
            ctx["agent_id"] = agent_id
        if agent_type:
            ctx["agent_type"] = agent_type

        super().__init__(message, context=ctx, cause=cause)
        self.agent_id = agent_id
        self.agent_type = agent_type


class TaskExecutionError(AgentError):
    """
    任务执行失败异常。

    当智能体在执行分配的任务时遇到无法恢复的错误时抛出。

    Attributes:
        task_id: 失败的任务ID
        phase: 任务执行阶段
        partial_result: 部分执行结果（如果有）
    """

    def __init__(
        self,
        message: str = "任务执行失败",
        *,
        task_id: str | None = None,
        phase: str | None = None,
        partial_result: Any = None,
        agent_id: str | None = None,
        agent_type: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化任务执行异常。

        Args:
            message: 错误描述信息
            task_id: 失败的任务ID
            phase: 任务执行阶段
            partial_result: 部分执行结果
            agent_id: 执行任务的智能体ID
            agent_type: 智能体类型
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if task_id:
            ctx["task_id"] = task_id
        if phase:
            ctx["phase"] = phase

        super().__init__(
            message,
            agent_id=agent_id,
            agent_type=agent_type,
            context=ctx,
            cause=cause,
        )
        self.task_id = task_id
        self.phase = phase
        self.partial_result = partial_result


class AgentNotFoundError(AgentError):
    """
    智能体未找到异常。

    当尝试访问或调用不存在的智能体时抛出。

    Attributes:
        requested_capability: 请求的能力（如果是按能力查找）
    """

    def __init__(
        self,
        message: str = "智能体未找到",
        *,
        agent_id: str | None = None,
        agent_type: str | None = None,
        requested_capability: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化智能体未找到异常。

        Args:
            message: 错误描述信息
            agent_id: 请求的智能体ID
            agent_type: 请求的智能体类型
            requested_capability: 请求的能力
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if requested_capability:
            ctx["requested_capability"] = requested_capability

        super().__init__(
            message,
            agent_id=agent_id,
            agent_type=agent_type,
            context=ctx,
            cause=cause,
        )
        self.requested_capability = requested_capability


class CapabilityMismatchError(AgentError):
    """
    能力不匹配异常。

    当分配给智能体的任务超出其能力范围时抛出。

    Attributes:
        required_capabilities: 任务所需的能力列表
        agent_capabilities: 智能体实际具备的能力列表
    """

    def __init__(
        self,
        message: str = "智能体能力与任务需求不匹配",
        *,
        required_capabilities: list[str] | None = None,
        agent_capabilities: list[str] | None = None,
        agent_id: str | None = None,
        agent_type: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化能力不匹配异常。

        Args:
            message: 错误描述信息
            required_capabilities: 任务所需的能力列表
            agent_capabilities: 智能体实际具备的能力列表
            agent_id: 智能体ID
            agent_type: 智能体类型
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if required_capabilities:
            ctx["required_capabilities"] = required_capabilities
        if agent_capabilities:
            ctx["agent_capabilities"] = agent_capabilities

        super().__init__(
            message,
            agent_id=agent_id,
            agent_type=agent_type,
            context=ctx,
            cause=cause,
        )
        self.required_capabilities = required_capabilities or []
        self.agent_capabilities = agent_capabilities or []

    @property
    def missing_capabilities(self) -> list[str]:
        """返回缺失的能力列表。"""
        return [
            cap for cap in self.required_capabilities
            if cap not in self.agent_capabilities
        ]


# =============================================================================
# Workflow 相关异常
# =============================================================================

class WorkflowError(ChairmanAgentError):
    """
    工作流相关操作的基础异常类。

    当工作流执行、状态转换或质量检查失败时抛出此异常或其子类。

    Attributes:
        workflow_id: 工作流ID
        workflow_name: 工作流名称
        current_phase: 当前工作流阶段
    """

    def __init__(
        self,
        message: str,
        *,
        workflow_id: str | None = None,
        workflow_name: str | None = None,
        current_phase: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化工作流异常。

        Args:
            message: 错误描述信息
            workflow_id: 工作流ID
            workflow_name: 工作流名称
            current_phase: 当前工作流阶段
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if workflow_id:
            ctx["workflow_id"] = workflow_id
        if workflow_name:
            ctx["workflow_name"] = workflow_name
        if current_phase:
            ctx["current_phase"] = current_phase

        super().__init__(message, context=ctx, cause=cause)
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.current_phase = current_phase


class QualityGateError(WorkflowError):
    """
    质量门禁检查失败异常。

    当工作流的质量门禁检查未通过时抛出，阻止工作流进入下一阶段。

    Attributes:
        gate_name: 质量门禁名称
        gate_criteria: 门禁检查标准
        actual_metrics: 实际检测指标
        threshold: 通过阈值
    """

    def __init__(
        self,
        message: str = "质量门禁检查未通过",
        *,
        gate_name: str | None = None,
        gate_criteria: dict[str, Any] | None = None,
        actual_metrics: dict[str, Any] | None = None,
        threshold: float | None = None,
        workflow_id: str | None = None,
        workflow_name: str | None = None,
        current_phase: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化质量门禁异常。

        Args:
            message: 错误描述信息
            gate_name: 质量门禁名称
            gate_criteria: 门禁检查标准
            actual_metrics: 实际检测指标
            threshold: 通过阈值
            workflow_id: 工作流ID
            workflow_name: 工作流名称
            current_phase: 当前工作流阶段
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if gate_name:
            ctx["gate_name"] = gate_name
        if threshold is not None:
            ctx["threshold"] = threshold

        super().__init__(
            message,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            current_phase=current_phase,
            context=ctx,
            cause=cause,
        )
        self.gate_name = gate_name
        self.gate_criteria = gate_criteria or {}
        self.actual_metrics = actual_metrics or {}
        self.threshold = threshold


class PhaseTransitionError(WorkflowError):
    """
    阶段转换失败异常。

    当工作流无法从当前阶段转换到目标阶段时抛出。

    Attributes:
        from_phase: 源阶段
        to_phase: 目标阶段
        transition_reason: 转换失败原因
    """

    def __init__(
        self,
        message: str = "工作流阶段转换失败",
        *,
        from_phase: str | None = None,
        to_phase: str | None = None,
        transition_reason: str | None = None,
        workflow_id: str | None = None,
        workflow_name: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化阶段转换异常。

        Args:
            message: 错误描述信息
            from_phase: 源阶段
            to_phase: 目标阶段
            transition_reason: 转换失败原因
            workflow_id: 工作流ID
            workflow_name: 工作流名称
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if from_phase:
            ctx["from_phase"] = from_phase
        if to_phase:
            ctx["to_phase"] = to_phase
        if transition_reason:
            ctx["transition_reason"] = transition_reason

        super().__init__(
            message,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            current_phase=from_phase,
            context=ctx,
            cause=cause,
        )
        self.from_phase = from_phase
        self.to_phase = to_phase
        self.transition_reason = transition_reason


class DependencyError(WorkflowError):
    """
    依赖解析失败异常。

    当工作流中的任务依赖无法满足时抛出（如循环依赖、缺失依赖等）。

    Attributes:
        dependency_type: 依赖类型 ("circular", "missing", "conflict")
        dependency_chain: 依赖链路
        blocking_tasks: 阻塞的任务列表
    """

    def __init__(
        self,
        message: str = "依赖解析失败",
        *,
        dependency_type: str | None = None,
        dependency_chain: list[str] | None = None,
        blocking_tasks: list[str] | None = None,
        workflow_id: str | None = None,
        workflow_name: str | None = None,
        current_phase: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化依赖异常。

        Args:
            message: 错误描述信息
            dependency_type: 依赖类型
            dependency_chain: 依赖链路
            blocking_tasks: 阻塞的任务列表
            workflow_id: 工作流ID
            workflow_name: 工作流名称
            current_phase: 当前工作流阶段
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if dependency_type:
            ctx["dependency_type"] = dependency_type
        if dependency_chain:
            ctx["dependency_chain"] = dependency_chain
        if blocking_tasks:
            ctx["blocking_tasks"] = blocking_tasks

        super().__init__(
            message,
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            current_phase=current_phase,
            context=ctx,
            cause=cause,
        )
        self.dependency_type = dependency_type
        self.dependency_chain = dependency_chain or []
        self.blocking_tasks = blocking_tasks or []


# =============================================================================
# Tool 相关异常
# =============================================================================

class ToolError(ChairmanAgentError):
    """
    工具相关操作的基础异常类。

    当智能体使用的工具执行失败时抛出此异常或其子类。

    Attributes:
        tool_name: 工具名称
        tool_version: 工具版本
    """

    def __init__(
        self,
        message: str,
        *,
        tool_name: str | None = None,
        tool_version: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化工具异常。

        Args:
            message: 错误描述信息
            tool_name: 工具名称
            tool_version: 工具版本
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if tool_name:
            ctx["tool_name"] = tool_name
        if tool_version:
            ctx["tool_version"] = tool_version

        super().__init__(message, context=ctx, cause=cause)
        self.tool_name = tool_name
        self.tool_version = tool_version


class ToolExecutionError(ToolError):
    """
    工具执行失败异常。

    当工具在执行过程中遇到错误时抛出。

    Attributes:
        input_params: 工具输入参数
        output: 工具输出（如果有部分输出）
        exit_code: 工具退出码（如果适用）
    """

    def __init__(
        self,
        message: str = "工具执行失败",
        *,
        input_params: dict[str, Any] | None = None,
        output: Any = None,
        exit_code: int | None = None,
        tool_name: str | None = None,
        tool_version: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化工具执行异常。

        Args:
            message: 错误描述信息
            input_params: 工具输入参数
            output: 工具输出
            exit_code: 工具退出码
            tool_name: 工具名称
            tool_version: 工具版本
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if exit_code is not None:
            ctx["exit_code"] = exit_code

        super().__init__(
            message,
            tool_name=tool_name,
            tool_version=tool_version,
            context=ctx,
            cause=cause,
        )
        self.input_params = input_params or {}
        self.output = output
        self.exit_code = exit_code


class ToolTimeoutError(ToolError):
    """
    工具执行超时异常。

    当工具执行时间超过预设限制时抛出。

    Attributes:
        timeout_seconds: 超时时间设置（秒）
        elapsed_seconds: 实际经过的时间（秒）
    """

    def __init__(
        self,
        message: str = "工具执行超时",
        *,
        timeout_seconds: float | None = None,
        elapsed_seconds: float | None = None,
        tool_name: str | None = None,
        tool_version: str | None = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化工具超时异常。

        Args:
            message: 错误描述信息
            timeout_seconds: 超时时间设置（秒）
            elapsed_seconds: 实际经过的时间（秒）
            tool_name: 工具名称
            tool_version: 工具版本
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if timeout_seconds is not None:
            ctx["timeout_seconds"] = timeout_seconds
        if elapsed_seconds is not None:
            ctx["elapsed_seconds"] = elapsed_seconds

        super().__init__(
            message,
            tool_name=tool_name,
            tool_version=tool_version,
            context=ctx,
            cause=cause,
        )
        self.timeout_seconds = timeout_seconds
        self.elapsed_seconds = elapsed_seconds


# =============================================================================
# Configuration 相关异常
# =============================================================================

class ConfigurationError(ChairmanAgentError):
    """
    配置错误异常。

    当系统配置无效、缺失或不一致时抛出。

    Attributes:
        config_key: 配置键名
        config_source: 配置来源（如 "env", "file", "default"）
        expected_type: 期望的配置类型
        actual_value: 实际的配置值
    """

    def __init__(
        self,
        message: str = "配置错误",
        *,
        config_key: str | None = None,
        config_source: str | None = None,
        expected_type: str | None = None,
        actual_value: Any = None,
        context: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        初始化配置异常。

        Args:
            message: 错误描述信息
            config_key: 配置键名
            config_source: 配置来源
            expected_type: 期望的配置类型
            actual_value: 实际的配置值
            context: 附加的上下文信息
            cause: 导致此异常的原始异常
        """
        ctx = context or {}
        if config_key:
            ctx["config_key"] = config_key
        if config_source:
            ctx["config_source"] = config_source
        if expected_type:
            ctx["expected_type"] = expected_type

        super().__init__(message, context=ctx, cause=cause)
        self.config_key = config_key
        self.config_source = config_source
        self.expected_type = expected_type
        self.actual_value = actual_value


# =============================================================================
# 便捷导出
# =============================================================================

__all__ = [
    # 基础异常
    "ChairmanAgentError",
    # LLM 异常
    "LLMError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMResponseError",
    # Agent 异常
    "AgentError",
    "TaskExecutionError",
    "AgentNotFoundError",
    "CapabilityMismatchError",
    # Workflow 异常
    "WorkflowError",
    "QualityGateError",
    "PhaseTransitionError",
    "DependencyError",
    # Tool 异常
    "ToolError",
    "ToolExecutionError",
    "ToolTimeoutError",
    # Configuration 异常
    "ConfigurationError",
]
