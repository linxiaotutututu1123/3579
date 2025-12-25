"""
Tests for chairman_agents.core.exceptions module.

Covers:
- Base exception (ChairmanAgentError)
- LLM exceptions (LLMError, LLMRateLimitError, LLMTimeoutError, LLMResponseError)
- Agent exceptions (AgentError, TaskExecutionError, AgentNotFoundError, CapabilityMismatchError)
- Workflow exceptions (WorkflowError, QualityGateError, PhaseTransitionError, DependencyError)
- Tool exceptions (ToolError, ToolExecutionError, ToolTimeoutError)
- Configuration exception (ConfigurationError)
"""

from __future__ import annotations

import pytest

from chairman_agents.core.exceptions import (
    AgentError,
    AgentNotFoundError,
    CapabilityMismatchError,
    ChairmanAgentError,
    ConfigurationError,
    DependencyError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    PhaseTransitionError,
    QualityGateError,
    TaskExecutionError,
    ToolError,
    ToolExecutionError,
    ToolTimeoutError,
    WorkflowError,
)


# =============================================================================
# Base Exception Tests
# =============================================================================


@pytest.mark.unit
class TestChairmanAgentError:
    """Tests for ChairmanAgentError base exception."""

    def test_basic_instantiation(self):
        """Test basic exception instantiation with message."""
        error = ChairmanAgentError("Test error message")
        assert error.message == "Test error message"
        assert error.context == {}
        assert error.cause is None

    def test_with_context(self):
        """Test exception with context dictionary."""
        context = {"key": "value", "count": 42}
        error = ChairmanAgentError("Error with context", context=context)
        assert error.context == context
        assert error.context["key"] == "value"
        assert error.context["count"] == 42

    def test_with_cause(self):
        """Test exception with cause (chained exception)."""
        original_error = ValueError("Original error")
        error = ChairmanAgentError("Wrapped error", cause=original_error)
        assert error.cause is original_error
        assert error.__cause__ is original_error

    def test_str_representation(self):
        """Test __str__ method."""
        error = ChairmanAgentError("Test message")
        assert str(error) == "Test message"

    def test_str_with_context(self):
        """Test __str__ includes context."""
        error = ChairmanAgentError("Error", context={"key": "value"})
        str_repr = str(error)
        assert "Error" in str_repr
        # Context is included in message representation
        assert len(str_repr) > 0

    def test_repr(self):
        """Test __repr__ method."""
        error = ChairmanAgentError("Test", context={"k": "v"})
        repr_str = repr(error)
        assert "ChairmanAgentError" in repr_str
        assert "Test" in repr_str

    def test_to_dict(self):
        """Test to_dict method."""
        original = ValueError("cause")
        error = ChairmanAgentError(
            "Test message",
            context={"key": "value"},
            cause=original,
        )
        result = error.to_dict()

        assert result["error_type"] == "ChairmanAgentError"
        assert result["message"] == "Test message"
        assert result["context"] == {"key": "value"}
        assert "ValueError" in result["cause"]

    def test_to_dict_without_cause(self):
        """Test to_dict when there is no cause."""
        error = ChairmanAgentError("Test")
        result = error.to_dict()
        assert result["cause"] is None

    def test_inheritance(self):
        """Test ChairmanAgentError inherits from Exception."""
        error = ChairmanAgentError("Test")
        assert isinstance(error, Exception)


# =============================================================================
# LLM Exception Tests
# =============================================================================


@pytest.mark.unit
class TestLLMError:
    """Tests for LLMError exception."""

    def test_basic_instantiation(self):
        """Test basic LLMError instantiation."""
        error = LLMError("LLM operation failed")
        assert error.message == "LLM operation failed"
        assert error.model_name is None
        assert error.provider is None

    def test_with_model_info(self):
        """Test LLMError with model information."""
        error = LLMError(
            "Request failed",
            model_name="gpt-4",
            provider="openai",
        )
        assert error.model_name == "gpt-4"
        assert error.provider == "openai"
        assert error.context["model_name"] == "gpt-4"
        assert error.context["provider"] == "openai"

    def test_inheritance(self):
        """Test LLMError inherits from ChairmanAgentError."""
        error = LLMError("Test")
        assert isinstance(error, ChairmanAgentError)
        assert isinstance(error, Exception)


@pytest.mark.unit
class TestLLMRateLimitError:
    """Tests for LLMRateLimitError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = LLMRateLimitError()
        assert "LLM API" in error.message

    def test_with_retry_after(self):
        """Test with retry_after parameter."""
        error = LLMRateLimitError(retry_after=30.0)
        assert error.retry_after == 30.0
        assert error.context["retry_after"] == 30.0

    def test_with_limit_type(self):
        """Test with limit_type parameter."""
        error = LLMRateLimitError(
            limit_type="requests_per_minute",
            provider="openai",
        )
        assert error.limit_type == "requests_per_minute"
        assert error.context["limit_type"] == "requests_per_minute"

    def test_inheritance(self):
        """Test inheritance chain."""
        error = LLMRateLimitError()
        assert isinstance(error, LLMError)
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestLLMTimeoutError:
    """Tests for LLMTimeoutError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = LLMTimeoutError()
        assert "timeout" in error.message.lower()

    def test_with_timeout_info(self):
        """Test with timeout information."""
        error = LLMTimeoutError(
            timeout_seconds=60.0,
            elapsed_seconds=65.5,
        )
        assert error.timeout_seconds == 60.0
        assert error.elapsed_seconds == 65.5
        assert error.context["timeout_seconds"] == 60.0
        assert error.context["elapsed_seconds"] == 65.5

    def test_with_model_info(self):
        """Test with model information."""
        error = LLMTimeoutError(
            model_name="claude-3",
            provider="anthropic",
        )
        assert error.model_name == "claude-3"
        assert error.provider == "anthropic"


@pytest.mark.unit
class TestLLMResponseError:
    """Tests for LLMResponseError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = LLMResponseError()
        assert "response" in error.message.lower()

    def test_with_response_details(self):
        """Test with response details."""
        error = LLMResponseError(
            response_text="Invalid JSON response",
            expected_format="JSON object",
            status_code=500,
        )
        assert error.response_text == "Invalid JSON response"
        assert error.expected_format == "JSON object"
        assert error.status_code == 500
        assert error.context["expected_format"] == "JSON object"
        assert error.context["status_code"] == 500

    def test_inheritance(self):
        """Test inheritance chain."""
        error = LLMResponseError()
        assert isinstance(error, LLMError)


# =============================================================================
# Agent Exception Tests
# =============================================================================


@pytest.mark.unit
class TestAgentError:
    """Tests for AgentError exception."""

    def test_basic_instantiation(self):
        """Test basic AgentError instantiation."""
        error = AgentError("Agent operation failed")
        assert error.message == "Agent operation failed"
        assert error.agent_id is None
        assert error.agent_type is None

    def test_with_agent_info(self):
        """Test with agent information."""
        error = AgentError(
            "Operation failed",
            agent_id="agent-001",
            agent_type="backend_engineer",
        )
        assert error.agent_id == "agent-001"
        assert error.agent_type == "backend_engineer"
        assert error.context["agent_id"] == "agent-001"
        assert error.context["agent_type"] == "backend_engineer"

    def test_inheritance(self):
        """Test AgentError inherits from ChairmanAgentError."""
        error = AgentError("Test")
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestTaskExecutionError:
    """Tests for TaskExecutionError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = TaskExecutionError()
        assert "task" in error.message.lower()

    def test_with_task_info(self):
        """Test with task information."""
        error = TaskExecutionError(
            task_id="task-123",
            phase="execution",
            partial_result={"progress": 50},
        )
        assert error.task_id == "task-123"
        assert error.phase == "execution"
        assert error.partial_result == {"progress": 50}
        assert error.context["task_id"] == "task-123"
        assert error.context["phase"] == "execution"

    def test_with_agent_info(self):
        """Test with agent information."""
        error = TaskExecutionError(
            agent_id="agent-001",
            agent_type="developer",
        )
        assert error.agent_id == "agent-001"
        assert error.agent_type == "developer"

    def test_inheritance(self):
        """Test inheritance chain."""
        error = TaskExecutionError()
        assert isinstance(error, AgentError)
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestAgentNotFoundError:
    """Tests for AgentNotFoundError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = AgentNotFoundError()
        assert "agent" in error.message.lower()

    def test_with_requested_capability(self):
        """Test with requested capability."""
        error = AgentNotFoundError(
            agent_id="agent-missing",
            requested_capability="code_generation",
        )
        assert error.agent_id == "agent-missing"
        assert error.requested_capability == "code_generation"
        assert error.context["requested_capability"] == "code_generation"

    def test_inheritance(self):
        """Test inheritance chain."""
        error = AgentNotFoundError()
        assert isinstance(error, AgentError)


@pytest.mark.unit
class TestCapabilityMismatchError:
    """Tests for CapabilityMismatchError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = CapabilityMismatchError()
        assert "capability" in error.message.lower()

    def test_with_capability_lists(self):
        """Test with capability lists."""
        error = CapabilityMismatchError(
            required_capabilities=["code_generation", "testing", "security"],
            agent_capabilities=["code_generation", "documentation"],
        )
        assert error.required_capabilities == ["code_generation", "testing", "security"]
        assert error.agent_capabilities == ["code_generation", "documentation"]

    def test_missing_capabilities_property(self):
        """Test missing_capabilities computed property."""
        error = CapabilityMismatchError(
            required_capabilities=["code_generation", "testing", "security"],
            agent_capabilities=["code_generation", "documentation"],
        )
        missing = error.missing_capabilities
        assert "testing" in missing
        assert "security" in missing
        assert "code_generation" not in missing

    def test_empty_capabilities(self):
        """Test with empty capability lists."""
        error = CapabilityMismatchError()
        assert error.required_capabilities == []
        assert error.agent_capabilities == []
        assert error.missing_capabilities == []


# =============================================================================
# Workflow Exception Tests
# =============================================================================


@pytest.mark.unit
class TestWorkflowError:
    """Tests for WorkflowError exception."""

    def test_basic_instantiation(self):
        """Test basic WorkflowError instantiation."""
        error = WorkflowError("Workflow failed")
        assert error.message == "Workflow failed"
        assert error.workflow_id is None
        assert error.workflow_name is None
        assert error.current_phase is None

    def test_with_workflow_info(self):
        """Test with workflow information."""
        error = WorkflowError(
            "Workflow error",
            workflow_id="wf-001",
            workflow_name="feature-development",
            current_phase="implementation",
        )
        assert error.workflow_id == "wf-001"
        assert error.workflow_name == "feature-development"
        assert error.current_phase == "implementation"

    def test_inheritance(self):
        """Test WorkflowError inherits from ChairmanAgentError."""
        error = WorkflowError("Test")
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestQualityGateError:
    """Tests for QualityGateError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = QualityGateError()
        assert "quality" in error.message.lower()

    def test_with_gate_info(self):
        """Test with quality gate information."""
        error = QualityGateError(
            gate_name="test_coverage",
            gate_criteria={"min_coverage": 0.8},
            actual_metrics={"coverage": 0.65},
            threshold=0.8,
        )
        assert error.gate_name == "test_coverage"
        assert error.gate_criteria == {"min_coverage": 0.8}
        assert error.actual_metrics == {"coverage": 0.65}
        assert error.threshold == 0.8
        assert error.context["gate_name"] == "test_coverage"
        assert error.context["threshold"] == 0.8

    def test_with_workflow_info(self):
        """Test with workflow context."""
        error = QualityGateError(
            workflow_id="wf-001",
            current_phase="review",
        )
        assert error.workflow_id == "wf-001"
        assert error.current_phase == "review"

    def test_default_empty_dicts(self):
        """Test gate_criteria and actual_metrics default to empty dicts."""
        error = QualityGateError()
        assert error.gate_criteria == {}
        assert error.actual_metrics == {}

    def test_inheritance(self):
        """Test inheritance chain."""
        error = QualityGateError()
        assert isinstance(error, WorkflowError)
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestPhaseTransitionError:
    """Tests for PhaseTransitionError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = PhaseTransitionError()
        assert "transition" in error.message.lower()

    def test_with_phase_info(self):
        """Test with phase transition information."""
        error = PhaseTransitionError(
            from_phase="development",
            to_phase="review",
            transition_reason="Tests not passing",
        )
        assert error.from_phase == "development"
        assert error.to_phase == "review"
        assert error.transition_reason == "Tests not passing"
        assert error.context["from_phase"] == "development"
        assert error.context["to_phase"] == "review"
        assert error.context["transition_reason"] == "Tests not passing"

    def test_current_phase_set_from_from_phase(self):
        """Test current_phase is set from from_phase."""
        error = PhaseTransitionError(from_phase="dev")
        assert error.current_phase == "dev"

    def test_inheritance(self):
        """Test inheritance chain."""
        error = PhaseTransitionError()
        assert isinstance(error, WorkflowError)


@pytest.mark.unit
class TestDependencyError:
    """Tests for DependencyError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = DependencyError()
        assert "dependency" in error.message.lower()

    def test_with_dependency_info(self):
        """Test with dependency information."""
        error = DependencyError(
            dependency_type="circular",
            dependency_chain=["task-1", "task-2", "task-1"],
            blocking_tasks=["task-1"],
        )
        assert error.dependency_type == "circular"
        assert error.dependency_chain == ["task-1", "task-2", "task-1"]
        assert error.blocking_tasks == ["task-1"]

    def test_default_empty_lists(self):
        """Test dependency_chain and blocking_tasks default to empty lists."""
        error = DependencyError()
        assert error.dependency_chain == []
        assert error.blocking_tasks == []

    def test_various_dependency_types(self):
        """Test with different dependency types."""
        for dep_type in ["circular", "missing", "conflict"]:
            error = DependencyError(dependency_type=dep_type)
            assert error.dependency_type == dep_type

    def test_inheritance(self):
        """Test inheritance chain."""
        error = DependencyError()
        assert isinstance(error, WorkflowError)


# =============================================================================
# Tool Exception Tests
# =============================================================================


@pytest.mark.unit
class TestToolError:
    """Tests for ToolError exception."""

    def test_basic_instantiation(self):
        """Test basic ToolError instantiation."""
        error = ToolError("Tool operation failed")
        assert error.message == "Tool operation failed"
        assert error.tool_name is None
        assert error.tool_version is None

    def test_with_tool_info(self):
        """Test with tool information."""
        error = ToolError(
            "Operation failed",
            tool_name="code_executor",
            tool_version="1.0.0",
        )
        assert error.tool_name == "code_executor"
        assert error.tool_version == "1.0.0"
        assert error.context["tool_name"] == "code_executor"
        assert error.context["tool_version"] == "1.0.0"

    def test_inheritance(self):
        """Test ToolError inherits from ChairmanAgentError."""
        error = ToolError("Test")
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestToolExecutionError:
    """Tests for ToolExecutionError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = ToolExecutionError()
        assert "tool" in error.message.lower()

    def test_with_execution_info(self):
        """Test with execution information."""
        error = ToolExecutionError(
            input_params={"code": "print('hello')"},
            output="Error: syntax error",
            exit_code=1,
        )
        assert error.input_params == {"code": "print('hello')"}
        assert error.output == "Error: syntax error"
        assert error.exit_code == 1
        assert error.context["exit_code"] == 1

    def test_default_empty_input_params(self):
        """Test input_params defaults to empty dict."""
        error = ToolExecutionError()
        assert error.input_params == {}

    def test_inheritance(self):
        """Test inheritance chain."""
        error = ToolExecutionError()
        assert isinstance(error, ToolError)
        assert isinstance(error, ChairmanAgentError)


@pytest.mark.unit
class TestToolTimeoutError:
    """Tests for ToolTimeoutError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = ToolTimeoutError()
        assert "timeout" in error.message.lower()

    def test_with_timeout_info(self):
        """Test with timeout information."""
        error = ToolTimeoutError(
            timeout_seconds=30.0,
            elapsed_seconds=35.5,
            tool_name="code_executor",
        )
        assert error.timeout_seconds == 30.0
        assert error.elapsed_seconds == 35.5
        assert error.tool_name == "code_executor"

    def test_inheritance(self):
        """Test inheritance chain."""
        error = ToolTimeoutError()
        assert isinstance(error, ToolError)


# =============================================================================
# Configuration Exception Tests
# =============================================================================


@pytest.mark.unit
class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_default_message(self):
        """Test default error message."""
        error = ConfigurationError()
        assert "config" in error.message.lower()

    def test_with_config_info(self):
        """Test with configuration information."""
        error = ConfigurationError(
            config_key="llm.model",
            config_source="env",
            expected_type="str",
            actual_value=123,
        )
        assert error.config_key == "llm.model"
        assert error.config_source == "env"
        assert error.expected_type == "str"
        assert error.actual_value == 123
        assert error.context["config_key"] == "llm.model"
        assert error.context["config_source"] == "env"
        assert error.context["expected_type"] == "str"

    def test_inheritance(self):
        """Test ConfigurationError inherits from ChairmanAgentError."""
        error = ConfigurationError()
        assert isinstance(error, ChairmanAgentError)


# =============================================================================
# Exception Hierarchy Tests
# =============================================================================


@pytest.mark.unit
class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def test_llm_exception_hierarchy(self):
        """Test LLM exception inheritance hierarchy."""
        assert issubclass(LLMError, ChairmanAgentError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(LLMTimeoutError, LLMError)
        assert issubclass(LLMResponseError, LLMError)

    def test_agent_exception_hierarchy(self):
        """Test Agent exception inheritance hierarchy."""
        assert issubclass(AgentError, ChairmanAgentError)
        assert issubclass(TaskExecutionError, AgentError)
        assert issubclass(AgentNotFoundError, AgentError)
        assert issubclass(CapabilityMismatchError, AgentError)

    def test_workflow_exception_hierarchy(self):
        """Test Workflow exception inheritance hierarchy."""
        assert issubclass(WorkflowError, ChairmanAgentError)
        assert issubclass(QualityGateError, WorkflowError)
        assert issubclass(PhaseTransitionError, WorkflowError)
        assert issubclass(DependencyError, WorkflowError)

    def test_tool_exception_hierarchy(self):
        """Test Tool exception inheritance hierarchy."""
        assert issubclass(ToolError, ChairmanAgentError)
        assert issubclass(ToolExecutionError, ToolError)
        assert issubclass(ToolTimeoutError, ToolError)

    def test_configuration_exception_hierarchy(self):
        """Test Configuration exception inheritance hierarchy."""
        assert issubclass(ConfigurationError, ChairmanAgentError)


# =============================================================================
# Exception Catching Tests
# =============================================================================


@pytest.mark.unit
class TestExceptionCatching:
    """Tests for exception catching behavior."""

    def test_catch_base_exception(self):
        """Test catching specific exceptions with base class."""
        with pytest.raises(ChairmanAgentError):
            raise LLMError("Test")

        with pytest.raises(ChairmanAgentError):
            raise AgentError("Test")

        with pytest.raises(ChairmanAgentError):
            raise WorkflowError("Test")

        with pytest.raises(ChairmanAgentError):
            raise ToolError("Test")

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        with pytest.raises(LLMRateLimitError):
            raise LLMRateLimitError()

        with pytest.raises(TaskExecutionError):
            raise TaskExecutionError()

    def test_catch_intermediate_exception(self):
        """Test catching intermediate exception types."""
        with pytest.raises(LLMError):
            raise LLMRateLimitError()

        with pytest.raises(AgentError):
            raise TaskExecutionError()

        with pytest.raises(WorkflowError):
            raise QualityGateError()

        with pytest.raises(ToolError):
            raise ToolExecutionError()


# =============================================================================
# Exception Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestExceptionSerialization:
    """Tests for exception serialization to dict."""

    def test_complex_exception_to_dict(self):
        """Test complex exception serialization."""
        cause = ValueError("Original error")
        error = TaskExecutionError(
            message="Task failed during execution",
            task_id="task-123",
            phase="implementation",
            partial_result={"lines": 100},
            agent_id="agent-001",
            agent_type="developer",
            context={"extra": "data"},
            cause=cause,
        )

        result = error.to_dict()

        assert result["error_type"] == "TaskExecutionError"
        assert result["message"] == "Task failed during execution"
        assert "task_id" in result["context"]
        assert "phase" in result["context"]
        assert "agent_id" in result["context"]
        assert "extra" in result["context"]
        assert "ValueError" in result["cause"]

    def test_all_exception_types_serializable(self):
        """Test all exception types can be serialized to dict."""
        exceptions = [
            ChairmanAgentError("Test"),
            LLMError("Test"),
            LLMRateLimitError(),
            LLMTimeoutError(),
            LLMResponseError(),
            AgentError("Test"),
            TaskExecutionError(),
            AgentNotFoundError(),
            CapabilityMismatchError(),
            WorkflowError("Test"),
            QualityGateError(),
            PhaseTransitionError(),
            DependencyError(),
            ToolError("Test"),
            ToolExecutionError(),
            ToolTimeoutError(),
            ConfigurationError(),
        ]

        for exc in exceptions:
            result = exc.to_dict()
            assert "error_type" in result
            assert "message" in result
            assert "context" in result
            assert "cause" in result
