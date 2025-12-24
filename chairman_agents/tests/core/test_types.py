"""
Tests for chairman_agents.core.types module.

Covers:
- Type aliases (AgentId, TaskId, ArtifactId)
- ID generation function (generate_id)
- All enumerations (AgentRole, ExpertiseLevel, AgentCapability, etc.)
- All data classes (QualityRequirements, ReasoningStep, ReviewComment, etc.)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from chairman_agents.core.types import (
    # Type aliases and functions
    AgentId,
    ArtifactId,
    TaskId,
    generate_id,
    # Enums
    AgentCapability,
    AgentRole,
    ArtifactType,
    ExpertiseLevel,
    MessageType,
    TaskPriority,
    TaskStatus,
    ToolType,
    # Data classes
    AgentMessage,
    AgentProfile,
    AgentState,
    Artifact,
    QualityRequirements,
    ReasoningStep,
    ReviewComment,
    Task,
    TaskContext,
    TaskResult,
)


# =============================================================================
# Type Alias Tests
# =============================================================================


@pytest.mark.unit
class TestTypeAliases:
    """Tests for type aliases."""

    def test_agent_id_is_str(self):
        """Test AgentId is a string type alias."""
        agent_id: AgentId = "agent-001"
        assert isinstance(agent_id, str)

    def test_task_id_is_str(self):
        """Test TaskId is a string type alias."""
        task_id: TaskId = "task-001"
        assert isinstance(task_id, str)

    def test_artifact_id_is_str(self):
        """Test ArtifactId is a string type alias."""
        artifact_id: ArtifactId = "artifact-001"
        assert isinstance(artifact_id, str)


# =============================================================================
# ID Generation Tests
# =============================================================================


@pytest.mark.unit
class TestGenerateId:
    """Tests for generate_id function."""

    def test_generate_id_without_prefix(self):
        """Test generating ID without prefix."""
        id1 = generate_id()
        id2 = generate_id()

        assert isinstance(id1, str)
        assert len(id1) == 12  # 12 hex characters
        assert id1 != id2  # Should be unique

    def test_generate_id_with_prefix(self):
        """Test generating ID with prefix."""
        agent_id = generate_id("agent")
        task_id = generate_id("task")

        assert agent_id.startswith("agent_")
        assert task_id.startswith("task_")
        assert len(agent_id) == len("agent_") + 12

    def test_generate_id_uniqueness(self):
        """Test ID uniqueness across multiple generations."""
        ids = [generate_id("test") for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_generate_id_hex_format(self):
        """Test generated IDs use hex characters."""
        for _ in range(10):
            uid = generate_id()
            # Should only contain valid hex characters
            assert all(c in "0123456789abcdef" for c in uid)


# =============================================================================
# AgentRole Enum Tests
# =============================================================================


@pytest.mark.unit
class TestAgentRole:
    """Tests for AgentRole enumeration."""

    def test_all_roles_exist(self):
        """Test all 16 agent roles exist."""
        expected_roles = [
            "PROJECT_MANAGER",
            "TECH_DIRECTOR",
            "SYSTEM_ARCHITECT",
            "SOLUTION_ARCHITECT",
            "TECH_LEAD",
            "BACKEND_ENGINEER",
            "FRONTEND_ENGINEER",
            "FULLSTACK_ENGINEER",
            "QA_ENGINEER",
            "QA_LEAD",
            "CODE_REVIEWER",
            "PERFORMANCE_ENGINEER",
            "SECURITY_ARCHITECT",
            "DEVOPS_ENGINEER",
            "SRE_ENGINEER",
            "TECH_WRITER",
        ]
        for role_name in expected_roles:
            assert hasattr(AgentRole, role_name)

    def test_role_values(self):
        """Test role values are snake_case strings."""
        assert AgentRole.PROJECT_MANAGER.value == "project_manager"
        assert AgentRole.BACKEND_ENGINEER.value == "backend_engineer"
        assert AgentRole.SECURITY_ARCHITECT.value == "security_architect"

    def test_role_iteration(self):
        """Test iterating over all roles."""
        roles = list(AgentRole)
        assert len(roles) == 16

    def test_role_comparison(self):
        """Test role equality comparison."""
        assert AgentRole.PROJECT_MANAGER == AgentRole.PROJECT_MANAGER
        assert AgentRole.PROJECT_MANAGER != AgentRole.TECH_LEAD


# =============================================================================
# ExpertiseLevel Enum Tests
# =============================================================================


@pytest.mark.unit
class TestExpertiseLevel:
    """Tests for ExpertiseLevel enumeration."""

    def test_all_levels_exist(self):
        """Test all 6 expertise levels exist."""
        expected_levels = [
            "JUNIOR", "INTERMEDIATE", "SENIOR",
            "STAFF", "PRINCIPAL", "FELLOW",
        ]
        for level_name in expected_levels:
            assert hasattr(ExpertiseLevel, level_name)

    def test_level_values(self):
        """Test expertise level values are integers 1-6."""
        assert ExpertiseLevel.JUNIOR.value == 1
        assert ExpertiseLevel.INTERMEDIATE.value == 2
        assert ExpertiseLevel.SENIOR.value == 3
        assert ExpertiseLevel.STAFF.value == 4
        assert ExpertiseLevel.PRINCIPAL.value == 5
        assert ExpertiseLevel.FELLOW.value == 6

    def test_level_ordering(self):
        """Test levels can be compared by value."""
        assert ExpertiseLevel.JUNIOR.value < ExpertiseLevel.SENIOR.value
        assert ExpertiseLevel.FELLOW.value > ExpertiseLevel.STAFF.value


# =============================================================================
# AgentCapability Enum Tests
# =============================================================================


@pytest.mark.unit
class TestAgentCapability:
    """Tests for AgentCapability enumeration."""

    def test_capability_count(self):
        """Test there are 37 capabilities."""
        assert len(list(AgentCapability)) == 37

    def test_requirements_capabilities(self):
        """Test requirements & planning capabilities exist."""
        assert AgentCapability.REQUIREMENT_ANALYSIS.value == "requirement_analysis"
        assert AgentCapability.TASK_DECOMPOSITION.value == "task_decomposition"
        assert AgentCapability.EFFORT_ESTIMATION.value == "effort_estimation"
        assert AgentCapability.RISK_ASSESSMENT.value == "risk_assessment"
        assert AgentCapability.ROADMAP_PLANNING.value == "roadmap_planning"

    def test_architecture_capabilities(self):
        """Test architecture design capabilities exist."""
        assert AgentCapability.SYSTEM_DESIGN.value == "system_design"
        assert AgentCapability.API_DESIGN.value == "api_design"
        assert AgentCapability.DATABASE_DESIGN.value == "database_design"
        assert AgentCapability.MICROSERVICES_DESIGN.value == "microservices_design"
        assert AgentCapability.DISTRIBUTED_SYSTEMS.value == "distributed_systems"

    def test_coding_capabilities(self):
        """Test coding capabilities exist."""
        assert AgentCapability.CODE_GENERATION.value == "code_generation"
        assert AgentCapability.CODE_REVIEW.value == "code_review"
        assert AgentCapability.CODE_REFACTORING.value == "code_refactoring"
        assert AgentCapability.CODE_OPTIMIZATION.value == "code_optimization"
        assert AgentCapability.CODE_DEBUGGING.value == "code_debugging"

    def test_language_capabilities(self):
        """Test language expertise capabilities exist."""
        assert AgentCapability.PYTHON_EXPERT.value == "python_expert"
        assert AgentCapability.JAVASCRIPT_EXPERT.value == "javascript_expert"
        assert AgentCapability.TYPESCRIPT_EXPERT.value == "typescript_expert"
        assert AgentCapability.SQL_EXPERT.value == "sql_expert"

    def test_testing_capabilities(self):
        """Test testing capabilities exist."""
        assert AgentCapability.TEST_PLANNING.value == "test_planning"
        assert AgentCapability.UNIT_TESTING.value == "unit_testing"
        assert AgentCapability.INTEGRATION_TESTING.value == "integration_testing"
        assert AgentCapability.E2E_TESTING.value == "e2e_testing"
        assert AgentCapability.PERFORMANCE_TESTING.value == "performance_testing"

    def test_security_capabilities(self):
        """Test security capabilities exist."""
        assert AgentCapability.SECURITY_ANALYSIS.value == "security_analysis"
        assert AgentCapability.VULNERABILITY_ASSESSMENT.value == "vulnerability_assessment"
        assert AgentCapability.SECURITY_AUDIT.value == "security_audit"
        assert AgentCapability.PENETRATION_TESTING.value == "penetration_testing"

    def test_devops_capabilities(self):
        """Test DevOps capabilities exist."""
        assert AgentCapability.CI_CD_PIPELINE.value == "ci_cd_pipeline"
        assert AgentCapability.CONTAINERIZATION.value == "containerization"
        assert AgentCapability.ORCHESTRATION.value == "orchestration"
        assert AgentCapability.INFRASTRUCTURE_AS_CODE.value == "iac"
        assert AgentCapability.MONITORING.value == "monitoring"


# =============================================================================
# TaskStatus Enum Tests
# =============================================================================


@pytest.mark.unit
class TestTaskStatus:
    """Tests for TaskStatus enumeration."""

    def test_initial_states(self):
        """Test initial task states exist."""
        assert TaskStatus.DRAFT.value == "draft"
        assert TaskStatus.PENDING.value == "pending"

    def test_execution_states(self):
        """Test execution states exist."""
        assert TaskStatus.QUEUED.value == "queued"
        assert TaskStatus.ASSIGNED.value == "assigned"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"

    def test_collaboration_states(self):
        """Test collaboration states exist."""
        assert TaskStatus.IN_REVIEW.value == "in_review"
        assert TaskStatus.IN_DEBATE.value == "in_debate"
        assert TaskStatus.AWAITING_CONSENSUS.value == "awaiting_consensus"
        assert TaskStatus.REVISION_REQUIRED.value == "revision_required"

    def test_blocked_states(self):
        """Test blocked states exist."""
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.WAITING_DEPENDENCY.value == "waiting_dependency"

    def test_terminal_states(self):
        """Test terminal states exist."""
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


# =============================================================================
# TaskPriority Enum Tests
# =============================================================================


@pytest.mark.unit
class TestTaskPriority:
    """Tests for TaskPriority enumeration."""

    def test_all_priorities_exist(self):
        """Test all 5 priority levels exist."""
        assert TaskPriority.CRITICAL.value == 1
        assert TaskPriority.HIGH.value == 2
        assert TaskPriority.MEDIUM.value == 3
        assert TaskPriority.LOW.value == 4
        assert TaskPriority.BACKLOG.value == 5

    def test_priority_ordering(self):
        """Test priority values are ordered (lower = higher priority)."""
        assert TaskPriority.CRITICAL.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.MEDIUM.value
        assert TaskPriority.MEDIUM.value < TaskPriority.LOW.value
        assert TaskPriority.LOW.value < TaskPriority.BACKLOG.value


# =============================================================================
# MessageType Enum Tests
# =============================================================================


@pytest.mark.unit
class TestMessageType:
    """Tests for MessageType enumeration."""

    def test_task_messages(self):
        """Test task-related message types exist."""
        assert MessageType.TASK_ASSIGNMENT.value == "task_assignment"
        assert MessageType.TASK_UPDATE.value == "task_update"
        assert MessageType.TASK_COMPLETED.value == "task_completed"
        assert MessageType.TASK_FAILED.value == "task_failed"

    def test_collaboration_messages(self):
        """Test collaboration message types exist."""
        assert MessageType.REQUEST_REVIEW.value == "request_review"
        assert MessageType.REVIEW_FEEDBACK.value == "review_feedback"
        assert MessageType.REQUEST_HELP.value == "request_help"
        assert MessageType.PROVIDE_HELP.value == "provide_help"

    def test_debate_messages(self):
        """Test debate message types exist."""
        assert MessageType.DEBATE_START.value == "debate_start"
        assert MessageType.DEBATE_ARGUMENT.value == "debate_argument"
        assert MessageType.DEBATE_REBUTTAL.value == "debate_rebuttal"
        assert MessageType.DEBATE_CONCLUSION.value == "debate_conclusion"

    def test_consensus_messages(self):
        """Test consensus message types exist."""
        assert MessageType.CONSENSUS_PROPOSAL.value == "consensus_proposal"
        assert MessageType.CONSENSUS_VOTE.value == "consensus_vote"
        assert MessageType.CONSENSUS_REACHED.value == "consensus_reached"

    def test_system_messages(self):
        """Test system message types exist."""
        assert MessageType.STATUS_UPDATE.value == "status_update"
        assert MessageType.ERROR_REPORT.value == "error_report"
        assert MessageType.NOTIFICATION.value == "notification"


# =============================================================================
# ArtifactType Enum Tests
# =============================================================================


@pytest.mark.unit
class TestArtifactType:
    """Tests for ArtifactType enumeration."""

    def test_document_artifacts(self):
        """Test document artifact types exist."""
        assert ArtifactType.REQUIREMENT_DOC.value == "requirement_doc"
        assert ArtifactType.DESIGN_DOC.value == "design_doc"
        assert ArtifactType.ARCHITECTURE_DOC.value == "architecture_doc"
        assert ArtifactType.API_SPEC.value == "api_spec"
        assert ArtifactType.TEST_PLAN.value == "test_plan"
        assert ArtifactType.RUNBOOK.value == "runbook"

    def test_code_artifacts(self):
        """Test code artifact types exist."""
        assert ArtifactType.SOURCE_CODE.value == "source_code"
        assert ArtifactType.TEST_CODE.value == "test_code"
        assert ArtifactType.CONFIG_FILE.value == "config_file"
        assert ArtifactType.SCRIPT.value == "script"
        assert ArtifactType.MIGRATION.value == "migration"

    def test_configuration_artifacts(self):
        """Test configuration artifact types exist."""
        assert ArtifactType.DOCKERFILE.value == "dockerfile"
        assert ArtifactType.K8S_MANIFEST.value == "k8s_manifest"
        assert ArtifactType.CI_CONFIG.value == "ci_config"

    def test_report_artifacts(self):
        """Test report artifact types exist."""
        assert ArtifactType.REVIEW_REPORT.value == "review_report"
        assert ArtifactType.SECURITY_REPORT.value == "security_report"
        assert ArtifactType.PERFORMANCE_REPORT.value == "performance_report"


# =============================================================================
# ToolType Enum Tests
# =============================================================================


@pytest.mark.unit
class TestToolType:
    """Tests for ToolType enumeration."""

    def test_all_tools_exist(self):
        """Test all 9 tool types exist."""
        expected_tools = [
            ("CODE_EXECUTOR", "code_executor"),
            ("FILE_SYSTEM", "file_system"),
            ("GIT", "git"),
            ("TERMINAL", "terminal"),
            ("BROWSER", "browser"),
            ("SEARCH", "search"),
            ("LINTER", "linter"),
            ("TEST_RUNNER", "test_runner"),
            ("DATABASE", "database"),
        ]
        for name, value in expected_tools:
            assert hasattr(ToolType, name)
            assert getattr(ToolType, name).value == value


# =============================================================================
# QualityRequirements Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestQualityRequirements:
    """Tests for QualityRequirements data class."""

    def test_default_values(self):
        """Test default values."""
        req = QualityRequirements()
        assert req.min_test_coverage == 0.8
        assert req.max_complexity == 10
        assert req.require_type_hints is True
        assert req.require_docstrings is True
        assert req.security_scan_required is True
        assert req.allowed_vulnerabilities == 0
        assert req.performance_test_required is False
        assert req.max_response_time_ms is None
        assert req.require_architecture_review is False
        assert req.require_security_review is False

    def test_custom_values(self):
        """Test with custom values."""
        req = QualityRequirements(
            min_test_coverage=0.95,
            max_complexity=5,
            require_security_review=True,
            max_response_time_ms=500,
        )
        assert req.min_test_coverage == 0.95
        assert req.max_complexity == 5
        assert req.require_security_review is True
        assert req.max_response_time_ms == 500


# =============================================================================
# ReasoningStep Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestReasoningStep:
    """Tests for ReasoningStep data class."""

    def test_default_values(self):
        """Test default values."""
        step = ReasoningStep()
        assert step.step_number == 0
        assert step.thought == ""
        assert step.action is None
        assert step.observation is None
        assert step.reflection is None
        assert step.confidence == 0.0
        assert isinstance(step.timestamp, datetime)

    def test_custom_values(self):
        """Test with custom values."""
        step = ReasoningStep(
            step_number=1,
            thought="Analyzing the problem",
            action="Read file content",
            observation="Found 100 lines of code",
            reflection="Need to focus on main function",
            confidence=0.85,
        )
        assert step.step_number == 1
        assert step.thought == "Analyzing the problem"
        assert step.action == "Read file content"
        assert step.observation == "Found 100 lines of code"
        assert step.reflection == "Need to focus on main function"
        assert step.confidence == 0.85


# =============================================================================
# ReviewComment Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestReviewComment:
    """Tests for ReviewComment data class."""

    def test_default_values(self):
        """Test default values."""
        comment = ReviewComment()
        assert comment.id.startswith("comment_")
        assert comment.reviewer_id == ""
        assert comment.file_path is None
        assert comment.line_start is None
        assert comment.line_end is None
        assert comment.comment == ""
        assert comment.severity == "info"
        assert comment.category == ""
        assert comment.suggestion is None
        assert comment.suggested_code is None
        assert comment.auto_fixable is False
        assert comment.resolved is False
        assert comment.resolution is None

    def test_custom_values(self):
        """Test with custom values."""
        comment = ReviewComment(
            reviewer_id="agent-001",
            file_path="src/main.py",
            line_start=10,
            line_end=15,
            comment="Consider using a context manager",
            severity="warning",
            category="style",
            suggestion="Use 'with' statement",
            auto_fixable=True,
        )
        assert comment.reviewer_id == "agent-001"
        assert comment.file_path == "src/main.py"
        assert comment.line_start == 10
        assert comment.line_end == 15
        assert comment.comment == "Consider using a context manager"
        assert comment.severity == "warning"
        assert comment.category == "style"
        assert comment.auto_fixable is True

    def test_id_uniqueness(self):
        """Test review comment IDs are unique."""
        comments = [ReviewComment() for _ in range(10)]
        ids = [c.id for c in comments]
        assert len(set(ids)) == 10


# =============================================================================
# Artifact Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestArtifact:
    """Tests for Artifact data class."""

    def test_default_values(self):
        """Test default values."""
        artifact = Artifact()
        assert artifact.id.startswith("artifact_")
        assert artifact.type == ArtifactType.SOURCE_CODE
        assert artifact.name == ""
        assert artifact.content == ""
        assert artifact.file_path is None
        assert artifact.language is None
        assert artifact.framework is None
        assert artifact.version == "1.0.0"
        assert isinstance(artifact.created_at, datetime)
        assert artifact.created_by is None
        assert artifact.quality_score is None
        assert artifact.test_coverage is None
        assert artifact.reviewed is False
        assert artifact.approved is False
        assert artifact.review_comments == []

    def test_custom_values(self):
        """Test with custom values."""
        artifact = Artifact(
            type=ArtifactType.TEST_CODE,
            name="test_main.py",
            content="import pytest",
            language="python",
            framework="pytest",
            created_by="agent-001",
            quality_score=0.95,
            test_coverage=0.88,
        )
        assert artifact.type == ArtifactType.TEST_CODE
        assert artifact.name == "test_main.py"
        assert artifact.content == "import pytest"
        assert artifact.language == "python"
        assert artifact.framework == "pytest"
        assert artifact.created_by == "agent-001"
        assert artifact.quality_score == 0.95
        assert artifact.test_coverage == 0.88

    def test_with_file_path(self):
        """Test artifact with file path."""
        artifact = Artifact(
            file_path=Path("/project/src/main.py"),
        )
        assert artifact.file_path == Path("/project/src/main.py")

    def test_with_review_comments(self):
        """Test artifact with review comments."""
        comments = [
            ReviewComment(comment="Fix typo"),
            ReviewComment(comment="Add docstring"),
        ]
        artifact = Artifact(review_comments=comments)
        assert len(artifact.review_comments) == 2


# =============================================================================
# TaskResult Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestTaskResult:
    """Tests for TaskResult data class."""

    def test_default_values(self):
        """Test default values."""
        result = TaskResult()
        assert result.task_id == ""
        assert result.success is False
        assert result.artifacts == []
        assert result.reasoning_trace == []
        assert result.reflections == []
        assert result.confidence_score == 0.0
        assert result.quality_score == 0.0
        assert result.metrics == {}
        assert result.execution_time_seconds == 0.0
        assert result.token_usage == {}
        assert result.tools_used == []
        assert result.error_message is None
        assert result.error_type is None
        assert result.suggestions == []
        assert result.warnings == []
        assert result.learned_lessons == []

    def test_successful_result(self):
        """Test successful task result."""
        result = TaskResult(
            task_id="task-001",
            success=True,
            confidence_score=0.95,
            quality_score=0.90,
            execution_time_seconds=120.5,
        )
        assert result.task_id == "task-001"
        assert result.success is True
        assert result.confidence_score == 0.95
        assert result.quality_score == 0.90
        assert result.execution_time_seconds == 120.5

    def test_failed_result(self):
        """Test failed task result."""
        result = TaskResult(
            task_id="task-002",
            success=False,
            error_message="Connection timeout",
            error_type="TimeoutError",
        )
        assert result.success is False
        assert result.error_message == "Connection timeout"
        assert result.error_type == "TimeoutError"

    def test_with_artifacts(self):
        """Test result with artifacts."""
        artifacts = [
            Artifact(name="main.py"),
            Artifact(name="test_main.py", type=ArtifactType.TEST_CODE),
        ]
        result = TaskResult(artifacts=artifacts)
        assert len(result.artifacts) == 2

    def test_with_tools_used(self):
        """Test result with tools used."""
        result = TaskResult(
            tools_used=[ToolType.FILE_SYSTEM, ToolType.GIT, ToolType.LINTER],
        )
        assert len(result.tools_used) == 3
        assert ToolType.FILE_SYSTEM in result.tools_used


# =============================================================================
# Task Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestTask:
    """Tests for Task data class."""

    def test_default_values(self):
        """Test default values."""
        task = Task()
        assert task.id.startswith("task_")
        assert task.title == ""
        assert task.description == ""
        assert task.type == "development"
        assert task.priority == TaskPriority.MEDIUM
        assert task.status == TaskStatus.PENDING
        assert task.required_capabilities == []
        assert task.required_role is None
        assert task.min_expertise_level == ExpertiseLevel.INTERMEDIATE
        assert task.complexity == 5
        assert task.estimated_hours == 4.0
        assert task.risk_level == "medium"
        assert task.quality_requirements is None
        assert task.requires_review is True
        assert task.requires_debate is False
        assert task.requires_pair_programming is False
        assert task.min_reviewers == 1
        assert task.required_tools == []
        assert task.dependencies == []
        assert task.blocked_by == []
        assert task.subtasks == []
        assert task.parent_task_id is None
        assert task.assigned_to is None
        assert task.reviewers == []
        assert isinstance(task.created_at, datetime)
        assert task.started_at is None
        assert task.completed_at is None
        assert task.deadline is None
        assert task.context == {}
        assert task.result is None

    def test_custom_values(self):
        """Test with custom values."""
        task = Task(
            title="Implement User Authentication",
            description="Add JWT-based authentication",
            priority=TaskPriority.HIGH,
            status=TaskStatus.IN_PROGRESS,
            required_capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.SECURITY_ANALYSIS,
            ],
            required_role=AgentRole.BACKEND_ENGINEER,
            complexity=8,
            estimated_hours=16.0,
        )
        assert task.title == "Implement User Authentication"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.IN_PROGRESS
        assert len(task.required_capabilities) == 2
        assert task.required_role == AgentRole.BACKEND_ENGINEER
        assert task.complexity == 8

    def test_with_dependencies(self):
        """Test task with dependencies."""
        task = Task(
            dependencies=["task-001", "task-002"],
            blocked_by=["task-001"],
        )
        assert len(task.dependencies) == 2
        assert len(task.blocked_by) == 1

    def test_with_quality_requirements(self):
        """Test task with quality requirements."""
        quality = QualityRequirements(min_test_coverage=0.9)
        task = Task(quality_requirements=quality)
        assert task.quality_requirements is not None
        assert task.quality_requirements.min_test_coverage == 0.9

    def test_id_uniqueness(self):
        """Test task IDs are unique."""
        tasks = [Task() for _ in range(10)]
        ids = [t.id for t in tasks]
        assert len(set(ids)) == 10


# =============================================================================
# AgentProfile Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestAgentProfile:
    """Tests for AgentProfile data class."""

    def test_default_values(self):
        """Test default values."""
        profile = AgentProfile()
        assert profile.id.startswith("agent_")
        assert profile.name == ""
        assert profile.role == AgentRole.BACKEND_ENGINEER
        assert profile.capabilities == []
        assert profile.capability_levels == {}
        assert profile.expertise_level == ExpertiseLevel.SENIOR
        assert profile.thinking_style == "analytical"
        assert profile.reflection_enabled is True
        assert profile.planning_depth == 3
        assert profile.collaboration_style == "cooperative"
        assert profile.debate_skill == 7
        assert profile.consensus_flexibility == 0.7
        assert profile.allowed_tools == []
        assert profile.system_prompt == ""
        assert profile.temperature == 0.7
        assert profile.max_tokens == 4096
        assert profile.model == "gpt-4"
        assert profile.max_retries == 3
        assert profile.timeout_seconds == 300

    def test_custom_values(self):
        """Test with custom values."""
        profile = AgentProfile(
            name="Senior Backend Developer",
            role=AgentRole.BACKEND_ENGINEER,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.PYTHON_EXPERT,
            ],
            capability_levels={
                AgentCapability.CODE_GENERATION: 8,
                AgentCapability.PYTHON_EXPERT: 9,
            },
            expertise_level=ExpertiseLevel.STAFF,
        )
        assert profile.name == "Senior Backend Developer"
        assert profile.role == AgentRole.BACKEND_ENGINEER
        assert len(profile.capabilities) == 2
        assert profile.capability_levels[AgentCapability.CODE_GENERATION] == 8
        assert profile.expertise_level == ExpertiseLevel.STAFF

    def test_has_capability_true(self):
        """Test has_capability returns True when agent has capability."""
        profile = AgentProfile(
            capabilities=[AgentCapability.CODE_GENERATION],
            capability_levels={AgentCapability.CODE_GENERATION: 7},
        )
        assert profile.has_capability(AgentCapability.CODE_GENERATION) is True
        assert profile.has_capability(AgentCapability.CODE_GENERATION, min_level=5) is True
        assert profile.has_capability(AgentCapability.CODE_GENERATION, min_level=7) is True

    def test_has_capability_false_missing(self):
        """Test has_capability returns False when capability missing."""
        profile = AgentProfile(capabilities=[])
        assert profile.has_capability(AgentCapability.CODE_GENERATION) is False

    def test_has_capability_false_low_level(self):
        """Test has_capability returns False when level too low."""
        profile = AgentProfile(
            capabilities=[AgentCapability.CODE_GENERATION],
            capability_levels={AgentCapability.CODE_GENERATION: 5},
        )
        assert profile.has_capability(AgentCapability.CODE_GENERATION, min_level=8) is False

    def test_can_use_tool_true(self):
        """Test can_use_tool returns True when tool allowed."""
        profile = AgentProfile(
            allowed_tools=[ToolType.FILE_SYSTEM, ToolType.GIT],
        )
        assert profile.can_use_tool(ToolType.FILE_SYSTEM) is True
        assert profile.can_use_tool(ToolType.GIT) is True

    def test_can_use_tool_false(self):
        """Test can_use_tool returns False when tool not allowed."""
        profile = AgentProfile(allowed_tools=[ToolType.FILE_SYSTEM])
        assert profile.can_use_tool(ToolType.DATABASE) is False


# =============================================================================
# TaskContext Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestTaskContext:
    """Tests for TaskContext data class."""

    def test_default_values(self):
        """Test default values."""
        context = TaskContext()
        assert context.project_name == ""
        assert context.project_description == ""
        assert context.project_root is None
        assert context.tech_stack == {}
        assert context.coding_standards == {}
        assert context.architecture_decisions == []
        assert context.design_patterns == []
        assert context.existing_artifacts == []
        assert context.completed_tasks == []
        assert context.domain_knowledge == {}
        assert context.learned_patterns == []
        assert context.constraints == []
        assert context.non_functional_requirements == {}
        assert context.conversation_history == []
        assert context.variables == {}

    def test_custom_values(self):
        """Test with custom values."""
        context = TaskContext(
            project_name="My Project",
            project_description="A sample project",
            project_root=Path("/projects/my-project"),
            tech_stack={
                "backend": ["python", "fastapi"],
                "frontend": ["react", "typescript"],
            },
            constraints=["Must use PostgreSQL", "No third-party auth"],
        )
        assert context.project_name == "My Project"
        assert context.project_root == Path("/projects/my-project")
        assert "backend" in context.tech_stack
        assert len(context.constraints) == 2


# =============================================================================
# AgentMessage Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestAgentMessage:
    """Tests for AgentMessage data class."""

    def test_default_values(self):
        """Test default values."""
        msg = AgentMessage()
        assert msg.id.startswith("msg_")
        assert msg.type == MessageType.NOTIFICATION
        assert msg.sender_id == ""
        assert msg.receiver_id is None
        assert msg.subject == ""
        assert msg.content == ""
        assert msg.data == {}
        assert msg.task_id is None
        assert msg.artifact_id is None
        assert msg.reply_to is None
        assert msg.thread_id is None
        assert msg.priority == 3
        assert msg.expires_at is None
        assert isinstance(msg.timestamp, datetime)
        assert msg.read is False
        assert msg.processed is False

    def test_custom_values(self):
        """Test with custom values."""
        msg = AgentMessage(
            type=MessageType.TASK_ASSIGNMENT,
            sender_id="agent-001",
            receiver_id="agent-002",
            subject="New task assigned",
            content="Please implement feature X",
            task_id="task-123",
            priority=1,
        )
        assert msg.type == MessageType.TASK_ASSIGNMENT
        assert msg.sender_id == "agent-001"
        assert msg.receiver_id == "agent-002"
        assert msg.subject == "New task assigned"
        assert msg.task_id == "task-123"
        assert msg.priority == 1

    def test_broadcast_message(self):
        """Test broadcast message (no receiver_id)."""
        msg = AgentMessage(
            type=MessageType.STATUS_UPDATE,
            sender_id="agent-001",
            content="Status update for all",
        )
        assert msg.receiver_id is None

    def test_reply_chain(self):
        """Test message reply chain."""
        original = AgentMessage(sender_id="agent-001")
        reply = AgentMessage(
            sender_id="agent-002",
            reply_to=original.id,
            thread_id=original.id,
        )
        assert reply.reply_to == original.id
        assert reply.thread_id == original.id

    def test_id_uniqueness(self):
        """Test message IDs are unique."""
        messages = [AgentMessage() for _ in range(10)]
        ids = [m.id for m in messages]
        assert len(set(ids)) == 10


# =============================================================================
# AgentState Data Class Tests
# =============================================================================


@pytest.mark.unit
class TestAgentState:
    """Tests for AgentState data class."""

    def test_default_values(self):
        """Test default values."""
        state = AgentState()
        assert state.agent_id == ""
        assert state.status == "idle"
        assert state.current_task_id is None
        assert state.current_activity is None
        assert state.thinking is False
        assert state.current_thought is None
        assert state.pending_messages == 0
        assert state.pending_reviews == 0
        assert state.tasks_completed == 0
        assert state.tasks_failed == 0
        assert state.reviews_completed == 0
        assert state.average_task_time == 0.0
        assert state.average_quality_score == 0.0
        assert state.success_rate == 1.0
        assert isinstance(state.last_active, datetime)
        assert isinstance(state.session_start, datetime)

    def test_working_state(self):
        """Test agent in working state."""
        state = AgentState(
            agent_id="agent-001",
            status="working",
            current_task_id="task-123",
            current_activity="Writing unit tests",
            thinking=True,
            current_thought="Analyzing test coverage requirements",
        )
        assert state.status == "working"
        assert state.current_task_id == "task-123"
        assert state.thinking is True
        assert state.current_thought == "Analyzing test coverage requirements"

    def test_with_statistics(self):
        """Test agent state with statistics."""
        state = AgentState(
            agent_id="agent-001",
            tasks_completed=50,
            tasks_failed=2,
            reviews_completed=25,
            average_task_time=180.5,
            average_quality_score=0.92,
            success_rate=0.96,
        )
        assert state.tasks_completed == 50
        assert state.tasks_failed == 2
        assert state.success_rate == 0.96

    def test_all_valid_statuses(self):
        """Test all valid status values."""
        valid_statuses = ["idle", "working", "reviewing", "debating", "blocked"]
        for status in valid_statuses:
            state = AgentState(status=status)
            assert state.status == status


# =============================================================================
# Integration Tests
# =============================================================================


@pytest.mark.unit
class TestTypeIntegration:
    """Integration tests for types working together."""

    def test_task_with_full_result(self):
        """Test Task with complete TaskResult."""
        artifact = Artifact(
            name="main.py",
            type=ArtifactType.SOURCE_CODE,
            content="print('hello')",
            language="python",
        )

        result = TaskResult(
            task_id="task-001",
            success=True,
            artifacts=[artifact],
            confidence_score=0.95,
            quality_score=0.90,
            tools_used=[ToolType.FILE_SYSTEM, ToolType.LINTER],
        )

        task = Task(
            id="task-001",
            title="Create main module",
            status=TaskStatus.COMPLETED,
            result=result,
        )

        assert task.result is not None
        assert task.result.success is True
        assert len(task.result.artifacts) == 1
        assert task.result.artifacts[0].language == "python"

    def test_agent_with_full_profile(self):
        """Test AgentProfile with full capabilities."""
        profile = AgentProfile(
            name="Expert Python Developer",
            role=AgentRole.BACKEND_ENGINEER,
            capabilities=[
                AgentCapability.CODE_GENERATION,
                AgentCapability.CODE_REVIEW,
                AgentCapability.PYTHON_EXPERT,
                AgentCapability.UNIT_TESTING,
            ],
            capability_levels={
                AgentCapability.CODE_GENERATION: 9,
                AgentCapability.CODE_REVIEW: 8,
                AgentCapability.PYTHON_EXPERT: 10,
                AgentCapability.UNIT_TESTING: 8,
            },
            expertise_level=ExpertiseLevel.PRINCIPAL,
            allowed_tools=[
                ToolType.FILE_SYSTEM,
                ToolType.GIT,
                ToolType.LINTER,
                ToolType.TEST_RUNNER,
            ],
        )

        # Check capability checks
        assert profile.has_capability(AgentCapability.PYTHON_EXPERT, min_level=9)
        assert profile.has_capability(AgentCapability.CODE_GENERATION, min_level=8)
        assert not profile.has_capability(AgentCapability.SECURITY_ANALYSIS)

        # Check tool permissions
        assert profile.can_use_tool(ToolType.GIT)
        assert profile.can_use_tool(ToolType.LINTER)
        assert not profile.can_use_tool(ToolType.DATABASE)

    def test_message_chain(self):
        """Test creating a chain of messages."""
        # Create initial request
        request = AgentMessage(
            type=MessageType.REQUEST_REVIEW,
            sender_id="developer-001",
            receiver_id="reviewer-001",
            subject="Review PR #123",
            content="Please review my changes",
            task_id="task-123",
        )

        # Create feedback response
        feedback = AgentMessage(
            type=MessageType.REVIEW_FEEDBACK,
            sender_id="reviewer-001",
            receiver_id="developer-001",
            subject="Re: Review PR #123",
            content="Found some issues",
            reply_to=request.id,
            thread_id=request.id,
            task_id="task-123",
        )

        assert feedback.reply_to == request.id
        assert feedback.thread_id == request.id
        assert feedback.task_id == request.task_id
