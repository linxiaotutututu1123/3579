"""
Workflow Pipeline and Stage Manager Test Suite.

This module provides comprehensive tests for:
- WorkflowPipeline: Pipeline creation, configuration, execution, checkpoints
- StageManager: Stage state management, transitions, hooks, rollback

Test Organization:
- TestPipelineState: PipelineState data class tests
- TestPipelineCheckpoint: PipelineCheckpoint data class tests
- TestWorkflowPipeline: WorkflowPipeline class tests
- TestStageManager: StageManager class tests
- TestStageTransition: Stage transition record tests
- TestStageContext: StageContext data class tests
- TestPipelineExecution: End-to-end execution flow tests
- TestHookSystem: Hook registration and execution tests
- TestErrorHandling: Error handling and recovery tests
- TestCheckpointMechanism: Checkpoint save/restore tests
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chairman_agents.core.exceptions import (
    PhaseTransitionError,
    WorkflowError,
)
from chairman_agents.core.types import (
    Task,
    TaskResult,
    TaskStatus,
)
from chairman_agents.workflow.pipeline import (
    PipelineCheckpoint,
    PipelineState,
    PipelineStatus,
    WorkflowPipeline,
)
from chairman_agents.workflow.stage_manager import (
    StageContext,
    StageManager,
    StageStatus,
    StageTransition,
    WorkflowStage,
)


# =============================================================================
# Pytest Markers
# =============================================================================

pytestmark = [
    pytest.mark.unit,
    pytest.mark.workflow,
]


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_task() -> Task:
    """Create a sample task for testing."""
    return Task(
        id="task_test_001",
        title="Test Task",
        description="A test task for pipeline testing",
        status=TaskStatus.PENDING,
    )


@pytest.fixture
def sample_tasks() -> list[Task]:
    """Create multiple sample tasks for testing."""
    return [
        Task(
            id=f"task_test_{i:03d}",
            title=f"Test Task {i}",
            description=f"Test task number {i}",
            status=TaskStatus.PENDING,
        )
        for i in range(1, 4)
    ]


@pytest.fixture
def mock_task_executor() -> AsyncMock:
    """Create a mock task executor."""
    async def executor(task: Task, context: StageContext) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            success=True,
            confidence_score=0.95,
            quality_score=0.9,
        )
    return AsyncMock(side_effect=executor)


@pytest.fixture
def mock_stage_handler() -> AsyncMock:
    """Create a mock stage handler."""
    async def handler(context: StageContext, tasks: list[Task]) -> list[TaskResult]:
        return [
            TaskResult(task_id=task.id, success=True)
            for task in tasks
        ]
    return AsyncMock(side_effect=handler)


@pytest.fixture
def workflow_pipeline(tmp_path: Path) -> WorkflowPipeline:
    """Create a WorkflowPipeline instance for testing."""
    return WorkflowPipeline(
        pipeline_id="test_pipe_001",
        workflow_id="test_wf_001",
        checkpoint_dir=tmp_path / "checkpoints",
        max_retries=2,
        retry_delay_seconds=0.1,
        parallel_limit=3,
    )


@pytest.fixture
def stage_manager() -> StageManager:
    """Create a StageManager instance for testing."""
    return StageManager(
        workflow_id="test_wf_001",
        allow_skip=True,
        allow_rollback=True,
        max_rollback_depth=3,
    )


# =============================================================================
# PipelineState Tests
# =============================================================================


class TestPipelineState:
    """Tests for PipelineState data class."""

    def test_default_initialization(self):
        """Test PipelineState default values."""
        state = PipelineState()

        assert state.pipeline_id.startswith("pipe_")
        assert state.workflow_id == ""
        assert state.status == PipelineStatus.IDLE
        assert state.current_stage is None
        assert state.started_at is None
        assert state.completed_at is None
        assert state.task_queue == []
        assert state.completed_tasks == []
        assert state.failed_tasks == []
        assert state.artifacts == {}
        assert state.results == {}
        assert state.metrics == {}
        assert state.metadata == {}
        assert state.last_error is None
        assert state.error_count == 0

    def test_custom_initialization(self):
        """Test PipelineState with custom values."""
        state = PipelineState(
            pipeline_id="custom_pipe",
            workflow_id="custom_wf",
            status=PipelineStatus.RUNNING,
            current_stage=WorkflowStage.EXECUTION,
        )

        assert state.pipeline_id == "custom_pipe"
        assert state.workflow_id == "custom_wf"
        assert state.status == PipelineStatus.RUNNING
        assert state.current_stage == WorkflowStage.EXECUTION

    def test_progress_calculation_empty(self):
        """Test progress calculation with no tasks."""
        state = PipelineState()
        assert state.progress == 0.0

    def test_progress_calculation_partial(self):
        """Test progress calculation with partial completion."""
        state = PipelineState(
            task_queue=["task1", "task2"],
            completed_tasks=["task3", "task4"],
            failed_tasks=["task5"],
        )
        # 2 completed / 5 total = 0.4
        assert state.progress == pytest.approx(0.4)

    def test_success_rate_no_completed(self):
        """Test success rate with no completed tasks."""
        state = PipelineState()
        assert state.success_rate == 1.0

    def test_success_rate_with_failures(self):
        """Test success rate with failures."""
        state = PipelineState(
            completed_tasks=["task1", "task2", "task3"],
            failed_tasks=["task4"],
        )
        # 3 completed / 4 total processed = 0.75
        assert state.success_rate == pytest.approx(0.75)

    def test_is_running(self):
        """Test is_running property."""
        state = PipelineState(status=PipelineStatus.RUNNING)
        assert state.is_running is True

        state.status = PipelineStatus.IDLE
        assert state.is_running is False

    def test_is_terminal(self):
        """Test is_terminal property for terminal states."""
        for status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED, PipelineStatus.CANCELLED]:
            state = PipelineState(status=status)
            assert state.is_terminal is True

        for status in [PipelineStatus.IDLE, PipelineStatus.RUNNING, PipelineStatus.PAUSED]:
            state = PipelineState(status=status)
            assert state.is_terminal is False

    def test_execution_time_not_started(self):
        """Test execution time when not started."""
        state = PipelineState()
        assert state.execution_time_seconds == 0.0

    def test_execution_time_running(self):
        """Test execution time while running."""
        state = PipelineState(
            started_at=datetime.now() - timedelta(seconds=5)
        )
        assert state.execution_time_seconds >= 5.0

    def test_to_dict_serialization(self):
        """Test PipelineState serialization to dict."""
        state = PipelineState(
            pipeline_id="test_pipe",
            workflow_id="test_wf",
            status=PipelineStatus.RUNNING,
            current_stage=WorkflowStage.EXECUTION,
            task_queue=["task1"],
            completed_tasks=["task2"],
            failed_tasks=["task3"],
        )

        data = state.to_dict()

        assert data["pipeline_id"] == "test_pipe"
        assert data["workflow_id"] == "test_wf"
        assert data["status"] == "running"
        assert data["current_stage"] == "execution"
        assert data["task_queue"] == ["task1"]
        assert data["completed_tasks"] == ["task2"]
        assert data["failed_tasks"] == ["task3"]

    def test_from_dict_deserialization(self):
        """Test PipelineState deserialization from dict."""
        data = {
            "pipeline_id": "restored_pipe",
            "workflow_id": "restored_wf",
            "status": "completed",
            "current_stage": "completion",
            "task_queue": [],
            "completed_tasks": ["task1", "task2"],
            "failed_tasks": [],
            "started_at": datetime.now().isoformat(),
        }

        state = PipelineState.from_dict(data)

        assert state.pipeline_id == "restored_pipe"
        assert state.workflow_id == "restored_wf"
        assert state.status == PipelineStatus.COMPLETED
        assert state.current_stage == WorkflowStage.COMPLETION
        assert state.completed_tasks == ["task1", "task2"]
        assert state.started_at is not None

    def test_repr(self):
        """Test PipelineState string representation."""
        state = PipelineState(
            pipeline_id="test_pipe",
            status=PipelineStatus.RUNNING,
            current_stage=WorkflowStage.EXECUTION,
            completed_tasks=["task1"],
            task_queue=["task2"],
        )

        repr_str = repr(state)
        assert "test_pipe" in repr_str
        assert "running" in repr_str
        assert "execution" in repr_str


# =============================================================================
# PipelineCheckpoint Tests
# =============================================================================


class TestPipelineCheckpoint:
    """Tests for PipelineCheckpoint data class."""

    def test_default_initialization(self):
        """Test PipelineCheckpoint default values."""
        checkpoint = PipelineCheckpoint()

        assert checkpoint.checkpoint_id.startswith("ckpt_")
        assert checkpoint.name == ""
        assert isinstance(checkpoint.pipeline_state, PipelineState)
        assert checkpoint.stage_contexts == {}
        assert checkpoint.description == ""
        assert isinstance(checkpoint.created_at, datetime)

    def test_custom_initialization(self):
        """Test PipelineCheckpoint with custom values."""
        state = PipelineState(
            pipeline_id="test_pipe",
            status=PipelineStatus.PAUSED,
        )

        checkpoint = PipelineCheckpoint(
            checkpoint_id="test_ckpt",
            name="before_execution",
            pipeline_state=state,
            description="Checkpoint before execution phase",
        )

        assert checkpoint.checkpoint_id == "test_ckpt"
        assert checkpoint.name == "before_execution"
        assert checkpoint.pipeline_state.pipeline_id == "test_pipe"
        assert checkpoint.description == "Checkpoint before execution phase"

    def test_to_dict_serialization(self):
        """Test PipelineCheckpoint serialization."""
        checkpoint = PipelineCheckpoint(
            name="test_checkpoint",
            pipeline_state=PipelineState(pipeline_id="test_pipe"),
            stage_contexts={"initialization": {"inputs": {}, "outputs": {}}},
            description="Test description",
        )

        data = checkpoint.to_dict()

        assert data["name"] == "test_checkpoint"
        assert "pipeline_state" in data
        assert "stage_contexts" in data
        assert data["description"] == "Test description"
        assert "created_at" in data

    def test_from_dict_deserialization(self):
        """Test PipelineCheckpoint deserialization."""
        data = {
            "checkpoint_id": "restored_ckpt",
            "name": "restored_checkpoint",
            "pipeline_state": {
                "pipeline_id": "restored_pipe",
                "status": "paused",
            },
            "stage_contexts": {},
            "created_at": datetime.now().isoformat(),
            "description": "Restored checkpoint",
        }

        checkpoint = PipelineCheckpoint.from_dict(data)

        assert checkpoint.checkpoint_id == "restored_ckpt"
        assert checkpoint.name == "restored_checkpoint"
        assert checkpoint.pipeline_state.pipeline_id == "restored_pipe"
        assert checkpoint.description == "Restored checkpoint"


# =============================================================================
# WorkflowPipeline Tests
# =============================================================================


class TestWorkflowPipeline:
    """Tests for WorkflowPipeline class."""

    def test_initialization_with_defaults(self):
        """Test WorkflowPipeline initialization with defaults."""
        pipeline = WorkflowPipeline()

        assert pipeline.pipeline_id.startswith("pipe_")
        assert pipeline.workflow_id.startswith("wf_")
        assert pipeline.state.status == PipelineStatus.IDLE
        assert pipeline.is_running is False
        assert pipeline.is_completed is False

    def test_initialization_with_custom_values(self, tmp_path: Path):
        """Test WorkflowPipeline initialization with custom values."""
        pipeline = WorkflowPipeline(
            pipeline_id="custom_pipe",
            workflow_id="custom_wf",
            checkpoint_dir=tmp_path / "ckpts",
            max_retries=5,
            retry_delay_seconds=2.0,
            parallel_limit=10,
        )

        assert pipeline.pipeline_id == "custom_pipe"
        assert pipeline.workflow_id == "custom_wf"
        assert pipeline._checkpoint_dir == tmp_path / "ckpts"
        assert pipeline._max_retries == 5
        assert pipeline._retry_delay == 2.0
        assert pipeline._parallel_limit == 10

    def test_register_handler(self, workflow_pipeline: WorkflowPipeline, mock_stage_handler: AsyncMock):
        """Test registering a stage handler."""
        workflow_pipeline.register_handler(WorkflowStage.EXECUTION, mock_stage_handler)

        assert WorkflowStage.EXECUTION in workflow_pipeline._stage_handlers
        assert workflow_pipeline._stage_handlers[WorkflowStage.EXECUTION] == mock_stage_handler

    def test_set_task_executor(self, workflow_pipeline: WorkflowPipeline, mock_task_executor: AsyncMock):
        """Test setting a task executor."""
        workflow_pipeline.set_task_executor(mock_task_executor)

        assert workflow_pipeline._task_executor == mock_task_executor

    def test_get_task(self, workflow_pipeline: WorkflowPipeline, sample_task: Task):
        """Test getting a task by ID."""
        workflow_pipeline._tasks[sample_task.id] = sample_task

        result = workflow_pipeline.get_task(sample_task.id)
        assert result == sample_task

        result = workflow_pipeline.get_task("nonexistent")
        assert result is None

    def test_get_result(self, workflow_pipeline: WorkflowPipeline):
        """Test getting a task result by ID."""
        result = TaskResult(task_id="task_001", success=True)
        workflow_pipeline._state.results["task_001"] = result

        retrieved = workflow_pipeline.get_result("task_001")
        assert retrieved == result

        retrieved = workflow_pipeline.get_result("nonexistent")
        assert retrieved is None

    def test_get_pending_tasks(self, workflow_pipeline: WorkflowPipeline, sample_tasks: list[Task]):
        """Test getting pending tasks."""
        for task in sample_tasks:
            workflow_pipeline._tasks[task.id] = task
        workflow_pipeline._state.task_queue = [task.id for task in sample_tasks]

        pending = workflow_pipeline.get_pending_tasks()
        assert len(pending) == 3
        assert all(task in sample_tasks for task in pending)

    def test_get_completed_tasks(self, workflow_pipeline: WorkflowPipeline, sample_tasks: list[Task]):
        """Test getting completed tasks."""
        for task in sample_tasks:
            workflow_pipeline._tasks[task.id] = task
        workflow_pipeline._state.completed_tasks = [sample_tasks[0].id, sample_tasks[1].id]

        completed = workflow_pipeline.get_completed_tasks()
        assert len(completed) == 2

    def test_get_failed_tasks(self, workflow_pipeline: WorkflowPipeline, sample_tasks: list[Task]):
        """Test getting failed tasks."""
        for task in sample_tasks:
            workflow_pipeline._tasks[task.id] = task
        workflow_pipeline._state.failed_tasks = [sample_tasks[2].id]

        failed = workflow_pipeline.get_failed_tasks()
        assert len(failed) == 1
        assert failed[0].id == sample_tasks[2].id

    def test_get_metrics(self, workflow_pipeline: WorkflowPipeline, sample_tasks: list[Task]):
        """Test getting pipeline metrics."""
        for task in sample_tasks:
            workflow_pipeline._tasks[task.id] = task
        workflow_pipeline._state.completed_tasks = [sample_tasks[0].id]
        workflow_pipeline._state.failed_tasks = [sample_tasks[1].id]
        workflow_pipeline._state.task_queue = [sample_tasks[2].id]

        metrics = workflow_pipeline.get_metrics()

        assert "progress" in metrics
        assert "success_rate" in metrics
        assert "total_tasks" in metrics
        assert metrics["total_tasks"] == 3
        assert metrics["completed_tasks"] == 1
        assert metrics["failed_tasks"] == 1
        assert metrics["pending_tasks"] == 1

    def test_to_dict(self, workflow_pipeline: WorkflowPipeline):
        """Test pipeline serialization to dict."""
        data = workflow_pipeline.to_dict()

        assert data["pipeline_id"] == "test_pipe_001"
        assert data["workflow_id"] == "test_wf_001"
        assert "state" in data
        assert "stage_manager" in data
        assert "checkpoints" in data
        assert "metrics" in data

    def test_repr(self, workflow_pipeline: WorkflowPipeline):
        """Test pipeline string representation."""
        repr_str = repr(workflow_pipeline)

        assert "test_pipe_001" in repr_str
        assert "idle" in repr_str

    def test_checkpoints_property(self, workflow_pipeline: WorkflowPipeline):
        """Test checkpoints property returns copy."""
        checkpoint = PipelineCheckpoint(name="test")
        workflow_pipeline._checkpoints["test"] = checkpoint

        checkpoints = workflow_pipeline.checkpoints
        assert "test" in checkpoints

        # Verify it's a copy
        checkpoints["new"] = checkpoint
        assert "new" not in workflow_pipeline._checkpoints

    def test_list_checkpoints(self, workflow_pipeline: WorkflowPipeline):
        """Test listing checkpoint names."""
        workflow_pipeline._checkpoints["ckpt1"] = PipelineCheckpoint(name="ckpt1")
        workflow_pipeline._checkpoints["ckpt2"] = PipelineCheckpoint(name="ckpt2")

        names = workflow_pipeline.list_checkpoints()

        assert set(names) == {"ckpt1", "ckpt2"}


# =============================================================================
# StageManager Tests
# =============================================================================


class TestStageManager:
    """Tests for StageManager class."""

    def test_initialization(self, stage_manager: StageManager):
        """Test StageManager initialization."""
        assert stage_manager.workflow_id == "test_wf_001"
        assert stage_manager.allow_skip is True
        assert stage_manager.allow_rollback is True
        assert stage_manager.max_rollback_depth == 3
        assert stage_manager.current_stage is None

    def test_stage_status_initialization(self, stage_manager: StageManager):
        """Test all stages start as PENDING."""
        for stage in WorkflowStage:
            assert stage_manager.stage_status[stage] == StageStatus.PENDING

    def test_progress_no_stage(self, stage_manager: StageManager):
        """Test progress with no current stage."""
        assert stage_manager.progress == 0.0

    def test_is_completed_false(self, stage_manager: StageManager):
        """Test is_completed when not completed."""
        assert stage_manager.is_completed is False

    @pytest.mark.asyncio
    async def test_enter_first_stage(self, stage_manager: StageManager):
        """Test entering the first stage (INITIALIZATION)."""
        context = await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        assert stage_manager.current_stage == WorkflowStage.INITIALIZATION
        assert stage_manager.stage_status[WorkflowStage.INITIALIZATION] == StageStatus.ACTIVE
        assert context.stage == WorkflowStage.INITIALIZATION
        assert len(stage_manager.transitions) == 1

    @pytest.mark.asyncio
    async def test_enter_stage_with_inputs(self, stage_manager: StageManager):
        """Test entering a stage with inputs."""
        inputs = {"key": "value"}
        context = await stage_manager.enter_stage(
            WorkflowStage.INITIALIZATION,
            inputs=inputs,
        )

        assert context.inputs == inputs

    @pytest.mark.asyncio
    async def test_enter_invalid_first_stage(self, stage_manager: StageManager):
        """Test entering invalid first stage raises error."""
        with pytest.raises(PhaseTransitionError) as exc_info:
            await stage_manager.enter_stage(WorkflowStage.EXECUTION)

        assert "INITIALIZATION" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_stage_auto_advance(self, stage_manager: StageManager):
        """Test completing a stage with auto-advance."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        next_stage = await stage_manager.complete_stage(auto_advance=True)

        assert next_stage == WorkflowStage.PLANNING
        assert stage_manager.stage_status[WorkflowStage.INITIALIZATION] == StageStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_complete_stage_with_outputs(self, stage_manager: StageManager):
        """Test completing a stage with outputs."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        outputs = {"result": "success"}
        await stage_manager.complete_stage(outputs=outputs, auto_advance=False)

        context = stage_manager.get_stage_context(WorkflowStage.INITIALIZATION)
        assert context.outputs["result"] == "success"

    @pytest.mark.asyncio
    async def test_complete_stage_no_active_stage(self, stage_manager: StageManager):
        """Test completing when no active stage raises error."""
        with pytest.raises(WorkflowError) as exc_info:
            await stage_manager.complete_stage()

        assert "没有活动的阶段" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fail_stage(self, stage_manager: StageManager):
        """Test failing a stage."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        await stage_manager.fail_stage("Test error")

        assert stage_manager.stage_status[WorkflowStage.INITIALIZATION] == StageStatus.FAILED
        context = stage_manager.get_stage_context(WorkflowStage.INITIALIZATION)
        assert "Test error" in context.errors

    @pytest.mark.asyncio
    async def test_fail_stage_with_retry(self, stage_manager: StageManager):
        """Test failing a stage with retry enabled."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        await stage_manager.fail_stage("Retryable error", retry=True)

        # Stage should still be active for retry
        assert stage_manager.current_stage == WorkflowStage.INITIALIZATION

    @pytest.mark.asyncio
    async def test_rollback(self, stage_manager: StageManager):
        """Test rollback to previous stage."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.PLANNING, force=True)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.EXECUTION, force=True)

        target = await stage_manager.rollback()

        assert target == WorkflowStage.PLANNING
        assert stage_manager.current_stage == WorkflowStage.PLANNING
        assert stage_manager.stage_status[WorkflowStage.EXECUTION] == StageStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_to_specific_stage(self, stage_manager: StageManager):
        """Test rollback to a specific earlier stage."""
        # Go through multiple stages
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.PLANNING, force=True)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.EXECUTION, force=True)

        target = await stage_manager.rollback(target_stage=WorkflowStage.INITIALIZATION)

        assert target == WorkflowStage.INITIALIZATION
        assert stage_manager.stage_status[WorkflowStage.PLANNING] == StageStatus.ROLLED_BACK

    @pytest.mark.asyncio
    async def test_rollback_exceeds_max_depth(self, stage_manager: StageManager):
        """Test rollback exceeding max depth raises error."""
        stage_manager.max_rollback_depth = 1

        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.PLANNING, force=True)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.EXECUTION, force=True)

        with pytest.raises(PhaseTransitionError) as exc_info:
            await stage_manager.rollback(target_stage=WorkflowStage.INITIALIZATION)

        assert "回滚深度" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_disabled(self):
        """Test rollback when disabled raises error."""
        manager = StageManager(workflow_id="test", allow_rollback=False)

        await manager.enter_stage(WorkflowStage.INITIALIZATION)
        await manager.complete_stage(auto_advance=False)
        await manager.enter_stage(WorkflowStage.PLANNING, force=True)

        with pytest.raises(WorkflowError) as exc_info:
            await manager.rollback()

        assert "回滚已被禁用" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_skip_stage(self, stage_manager: StageManager):
        """Test skipping a stage."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        next_stage = await stage_manager.skip_stage(reason="Not needed")

        assert next_stage == WorkflowStage.PLANNING
        assert stage_manager.stage_status[WorkflowStage.INITIALIZATION] == StageStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_skip_stage_disabled(self):
        """Test skip when disabled raises error."""
        manager = StageManager(workflow_id="test", allow_skip=False)

        await manager.enter_stage(WorkflowStage.INITIALIZATION)

        with pytest.raises(WorkflowError) as exc_info:
            await manager.skip_stage()

        assert "跳过已被禁用" in str(exc_info.value)

    def test_can_transition_to(self, stage_manager: StageManager):
        """Test transition validation check."""
        # First stage should be INITIALIZATION
        assert stage_manager.can_transition_to(WorkflowStage.INITIALIZATION) is True
        assert stage_manager.can_transition_to(WorkflowStage.EXECUTION) is False

    def test_get_stage_context_not_exists(self, stage_manager: StageManager):
        """Test getting context for stage that hasn't been entered."""
        context = stage_manager.get_stage_context(WorkflowStage.INITIALIZATION)
        assert context is None

    @pytest.mark.asyncio
    async def test_get_stage_context_exists(self, stage_manager: StageManager):
        """Test getting context for entered stage."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        context = stage_manager.get_stage_context(WorkflowStage.INITIALIZATION)
        assert context is not None
        assert context.stage == WorkflowStage.INITIALIZATION

    def test_get_transition_history_all(self, stage_manager: StageManager):
        """Test getting all transition history."""
        history = stage_manager.get_transition_history()
        assert history == []

    @pytest.mark.asyncio
    async def test_get_transition_history_filtered(self, stage_manager: StageManager):
        """Test getting filtered transition history."""
        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)
        await stage_manager.complete_stage(auto_advance=False)
        await stage_manager.enter_stage(WorkflowStage.PLANNING, force=True)

        history = stage_manager.get_transition_history(stage=WorkflowStage.INITIALIZATION)
        assert len(history) >= 1

    def test_to_dict(self, stage_manager: StageManager):
        """Test StageManager serialization to dict."""
        data = stage_manager.to_dict()

        assert data["workflow_id"] == "test_wf_001"
        assert data["current_stage"] is None
        assert "stage_status" in data
        assert data["progress"] == 0.0
        assert data["is_completed"] is False

    def test_repr(self, stage_manager: StageManager):
        """Test StageManager string representation."""
        repr_str = repr(stage_manager)

        assert "test_wf_001" in repr_str
        assert "None" in repr_str


# =============================================================================
# StageTransition Tests
# =============================================================================


class TestStageTransition:
    """Tests for StageTransition data class."""

    def test_default_initialization(self):
        """Test StageTransition default values."""
        transition = StageTransition()

        assert transition.id.startswith("trans_")
        assert transition.from_stage is None
        assert transition.to_stage == WorkflowStage.INITIALIZATION
        assert transition.status == StageStatus.ACTIVE
        assert isinstance(transition.timestamp, datetime)
        assert transition.duration_seconds is None
        assert transition.metadata == {}

    def test_custom_initialization(self):
        """Test StageTransition with custom values."""
        transition = StageTransition(
            from_stage=WorkflowStage.INITIALIZATION,
            to_stage=WorkflowStage.PLANNING,
            status=StageStatus.COMPLETED,
            duration_seconds=5.5,
            metadata={"reason": "test"},
        )

        assert transition.from_stage == WorkflowStage.INITIALIZATION
        assert transition.to_stage == WorkflowStage.PLANNING
        assert transition.status == StageStatus.COMPLETED
        assert transition.duration_seconds == 5.5
        assert transition.metadata["reason"] == "test"

    def test_repr(self):
        """Test StageTransition string representation."""
        transition = StageTransition(
            from_stage=WorkflowStage.INITIALIZATION,
            to_stage=WorkflowStage.PLANNING,
            status=StageStatus.COMPLETED,
        )

        repr_str = repr(transition)
        assert "initialization" in repr_str
        assert "planning" in repr_str
        assert "completed" in repr_str


# =============================================================================
# StageContext Tests
# =============================================================================


class TestStageContext:
    """Tests for StageContext data class."""

    def test_default_initialization(self):
        """Test StageContext default values."""
        context = StageContext()

        assert context.stage == WorkflowStage.INITIALIZATION
        assert isinstance(context.started_at, datetime)
        assert context.inputs == {}
        assert context.outputs == {}
        assert context.errors == []
        assert context.warnings == []

    def test_has_errors_false(self):
        """Test has_errors when no errors."""
        context = StageContext()
        assert context.has_errors is False

    def test_has_errors_true(self):
        """Test has_errors when errors exist."""
        context = StageContext(errors=["An error occurred"])
        assert context.has_errors is True

    def test_has_warnings_false(self):
        """Test has_warnings when no warnings."""
        context = StageContext()
        assert context.has_warnings is False

    def test_has_warnings_true(self):
        """Test has_warnings when warnings exist."""
        context = StageContext(warnings=["A warning"])
        assert context.has_warnings is True


# =============================================================================
# WorkflowStage Tests
# =============================================================================


class TestWorkflowStage:
    """Tests for WorkflowStage enum."""

    def test_get_order(self):
        """Test getting stage order."""
        order = WorkflowStage.get_order()

        assert len(order) == 6
        assert order[0] == WorkflowStage.INITIALIZATION
        assert order[1] == WorkflowStage.PLANNING
        assert order[2] == WorkflowStage.EXECUTION
        assert order[3] == WorkflowStage.REVIEW
        assert order[4] == WorkflowStage.REFINEMENT
        assert order[5] == WorkflowStage.COMPLETION

    def test_get_index(self):
        """Test getting stage index."""
        assert WorkflowStage.get_index(WorkflowStage.INITIALIZATION) == 0
        assert WorkflowStage.get_index(WorkflowStage.PLANNING) == 1
        assert WorkflowStage.get_index(WorkflowStage.EXECUTION) == 2
        assert WorkflowStage.get_index(WorkflowStage.REVIEW) == 3
        assert WorkflowStage.get_index(WorkflowStage.REFINEMENT) == 4
        assert WorkflowStage.get_index(WorkflowStage.COMPLETION) == 5

    def test_get_next(self):
        """Test getting next stage."""
        assert WorkflowStage.get_next(WorkflowStage.INITIALIZATION) == WorkflowStage.PLANNING
        assert WorkflowStage.get_next(WorkflowStage.PLANNING) == WorkflowStage.EXECUTION
        assert WorkflowStage.get_next(WorkflowStage.COMPLETION) is None

    def test_get_previous(self):
        """Test getting previous stage."""
        assert WorkflowStage.get_previous(WorkflowStage.PLANNING) == WorkflowStage.INITIALIZATION
        assert WorkflowStage.get_previous(WorkflowStage.INITIALIZATION) is None


# =============================================================================
# Pipeline Execution Tests
# =============================================================================


class TestPipelineExecution:
    """Tests for pipeline execution flow."""

    @pytest.mark.asyncio
    async def test_execute_single_task(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
        mock_stage_handler: AsyncMock,
    ):
        """Test executing a single task through the pipeline."""
        # Register handlers for all stages
        for stage in WorkflowStage:
            workflow_pipeline.register_handler(stage, mock_stage_handler)

        results = await workflow_pipeline.execute(sample_task, auto_checkpoint=False)

        assert workflow_pipeline.state.status == PipelineStatus.COMPLETED
        assert sample_task.id in workflow_pipeline._tasks
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_execute_multiple_tasks(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_tasks: list[Task],
        mock_stage_handler: AsyncMock,
    ):
        """Test executing multiple tasks through the pipeline."""
        for stage in WorkflowStage:
            workflow_pipeline.register_handler(stage, mock_stage_handler)

        results = await workflow_pipeline.execute(sample_tasks, auto_checkpoint=False)

        assert workflow_pipeline.state.status == PipelineStatus.COMPLETED
        assert len(workflow_pipeline._tasks) == 3

    @pytest.mark.asyncio
    async def test_execute_while_running_raises_error(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
    ):
        """Test executing while already running raises error."""
        workflow_pipeline._state.status = PipelineStatus.RUNNING

        with pytest.raises(WorkflowError) as exc_info:
            await workflow_pipeline.execute(sample_task)

        assert "正在运行" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pause_pipeline(
        self,
        workflow_pipeline: WorkflowPipeline,
    ):
        """Test pausing a running pipeline."""
        workflow_pipeline._state.status = PipelineStatus.RUNNING

        await workflow_pipeline.pause()

        assert workflow_pipeline.state.status == PipelineStatus.PAUSED
        assert workflow_pipeline._cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_cancel_pipeline(
        self,
        workflow_pipeline: WorkflowPipeline,
    ):
        """Test cancelling a running pipeline."""
        workflow_pipeline._state.status = PipelineStatus.RUNNING

        await workflow_pipeline.cancel()

        assert workflow_pipeline.state.status == PipelineStatus.CANCELLED
        assert workflow_pipeline._cancel_event.is_set()

    @pytest.mark.asyncio
    async def test_parallel_task_execution(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_tasks: list[Task],
        mock_task_executor: AsyncMock,
    ):
        """Test parallel task execution with semaphore."""
        workflow_pipeline.set_task_executor(mock_task_executor)

        # Manually test parallel execution
        context = StageContext(stage=WorkflowStage.EXECUTION)
        results = await workflow_pipeline._execute_tasks_parallel(sample_tasks, context)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_task_executor.call_count == 3


# =============================================================================
# Hook System Tests
# =============================================================================


class TestHookSystem:
    """Tests for hook registration and execution."""

    @pytest.mark.asyncio
    async def test_on_enter_hook(self, stage_manager: StageManager):
        """Test on_enter hook execution."""
        hook_called = []

        async def on_enter_hook(context: StageContext):
            hook_called.append(context.stage)

        stage_manager.on_enter(WorkflowStage.INITIALIZATION, on_enter_hook)

        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        assert WorkflowStage.INITIALIZATION in hook_called

    @pytest.mark.asyncio
    async def test_on_exit_hook(self, stage_manager: StageManager):
        """Test on_exit hook execution."""
        hook_called = []

        async def on_exit_hook(context: StageContext):
            hook_called.append(context.stage)

        stage_manager.on_exit(WorkflowStage.INITIALIZATION, on_exit_hook)

        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)
        await stage_manager.complete_stage(auto_advance=False)

        assert WorkflowStage.INITIALIZATION in hook_called

    @pytest.mark.asyncio
    async def test_multiple_hooks(self, stage_manager: StageManager):
        """Test multiple hooks for same stage."""
        hook_order = []

        async def hook1(context: StageContext):
            hook_order.append("hook1")

        async def hook2(context: StageContext):
            hook_order.append("hook2")

        stage_manager.on_enter(WorkflowStage.INITIALIZATION, hook1)
        stage_manager.on_enter(WorkflowStage.INITIALIZATION, hook2)

        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        assert hook_order == ["hook1", "hook2"]

    @pytest.mark.asyncio
    async def test_hook_error_handling(self, stage_manager: StageManager):
        """Test hook errors are captured as warnings."""
        async def failing_hook(context: StageContext):
            raise ValueError("Hook failed")

        stage_manager.on_enter(WorkflowStage.INITIALIZATION, failing_hook)

        await stage_manager.enter_stage(WorkflowStage.INITIALIZATION)

        context = stage_manager.get_stage_context(WorkflowStage.INITIALIZATION)
        assert len(context.warnings) > 0
        assert "进入钩子执行失败" in context.warnings[0]


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling and recovery."""

    @pytest.mark.asyncio
    async def test_execution_failure_updates_state(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
    ):
        """Test pipeline state update on execution failure."""
        async def failing_handler(context: StageContext, tasks: list[Task]) -> list[TaskResult]:
            raise RuntimeError("Handler failed")

        workflow_pipeline.register_handler(WorkflowStage.INITIALIZATION, failing_handler)

        with pytest.raises(RuntimeError):
            await workflow_pipeline.execute(sample_task, auto_checkpoint=False)

        assert workflow_pipeline.state.status == PipelineStatus.FAILED
        assert workflow_pipeline.state.last_error is not None
        assert workflow_pipeline.state.error_count == 1

    @pytest.mark.asyncio
    async def test_task_retry_mechanism(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
    ):
        """Test task retry mechanism on failure."""
        call_count = 0

        async def flaky_executor(task: Task, context: StageContext) -> TaskResult:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Temporary failure")
            return TaskResult(task_id=task.id, success=True)

        workflow_pipeline.set_task_executor(flaky_executor)

        context = StageContext(stage=WorkflowStage.EXECUTION)
        results = await workflow_pipeline._execute_tasks_parallel([sample_task], context)

        assert len(results) == 1
        assert results[0].success
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_task_max_retries_exceeded(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
    ):
        """Test task failure when max retries exceeded."""
        async def always_failing(task: Task, context: StageContext) -> TaskResult:
            raise RuntimeError("Permanent failure")

        workflow_pipeline.set_task_executor(always_failing)

        context = StageContext(stage=WorkflowStage.EXECUTION)
        results = await workflow_pipeline._execute_tasks_parallel([sample_task], context)

        assert len(results) == 1
        assert not results[0].success
        assert results[0].error_message == "Permanent failure"
        assert results[0].error_type == "RuntimeError"


# =============================================================================
# Checkpoint Mechanism Tests
# =============================================================================


class TestCheckpointMechanism:
    """Tests for checkpoint save and restore."""

    @pytest.mark.asyncio
    async def test_create_checkpoint(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
    ):
        """Test creating a checkpoint."""
        workflow_pipeline._tasks[sample_task.id] = sample_task
        workflow_pipeline._state.task_queue.append(sample_task.id)
        workflow_pipeline._state.status = PipelineStatus.RUNNING

        checkpoint = await workflow_pipeline.checkpoint(
            name="test_checkpoint",
            description="Test checkpoint description",
            persist=False,
        )

        assert checkpoint.name == "test_checkpoint"
        assert checkpoint.description == "Test checkpoint description"
        assert checkpoint.pipeline_state.status == PipelineStatus.RUNNING
        assert "test_checkpoint" in workflow_pipeline._checkpoints

    @pytest.mark.asyncio
    async def test_checkpoint_persistence(
        self,
        workflow_pipeline: WorkflowPipeline,
        tmp_path: Path,
    ):
        """Test checkpoint persistence to disk."""
        workflow_pipeline._checkpoint_dir = tmp_path / "checkpoints"

        await workflow_pipeline.checkpoint(
            name="persistent_checkpoint",
            persist=True,
        )

        checkpoint_file = workflow_pipeline._checkpoint_dir / "persistent_checkpoint.json"
        assert checkpoint_file.exists()

        # Verify content
        content = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        assert content["name"] == "persistent_checkpoint"

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(
        self,
        workflow_pipeline: WorkflowPipeline,
    ):
        """Test resuming from a checkpoint."""
        # Create checkpoint in paused state
        workflow_pipeline._state.status = PipelineStatus.PAUSED
        workflow_pipeline._state.current_stage = WorkflowStage.EXECUTION
        workflow_pipeline._state.task_queue = ["task1", "task2"]

        await workflow_pipeline.checkpoint("pause_point", persist=False)

        # Reset pipeline state
        workflow_pipeline._state.status = PipelineStatus.IDLE
        workflow_pipeline._state.task_queue = []

        # Resume from checkpoint
        await workflow_pipeline.resume("pause_point")

        # Verify state is restored and running
        assert workflow_pipeline.state.status == PipelineStatus.RUNNING
        assert workflow_pipeline.state.task_queue == ["task1", "task2"]

    @pytest.mark.asyncio
    async def test_resume_nonexistent_checkpoint_raises_error(
        self,
        workflow_pipeline: WorkflowPipeline,
    ):
        """Test resuming from nonexistent checkpoint raises error."""
        with pytest.raises(WorkflowError) as exc_info:
            await workflow_pipeline.resume("nonexistent")

        assert "不存在" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_checkpoint(
        self,
        workflow_pipeline: WorkflowPipeline,
    ):
        """Test deleting a checkpoint."""
        await workflow_pipeline.checkpoint("to_delete", persist=False)

        assert "to_delete" in workflow_pipeline._checkpoints

        deleted = await workflow_pipeline.delete_checkpoint("to_delete", from_disk=False)

        assert deleted is True
        assert "to_delete" not in workflow_pipeline._checkpoints

    @pytest.mark.asyncio
    async def test_delete_checkpoint_with_disk(
        self,
        workflow_pipeline: WorkflowPipeline,
        tmp_path: Path,
    ):
        """Test deleting a checkpoint with disk file."""
        workflow_pipeline._checkpoint_dir = tmp_path / "checkpoints"

        await workflow_pipeline.checkpoint("disk_checkpoint", persist=True)

        checkpoint_file = workflow_pipeline._checkpoint_dir / "disk_checkpoint.json"
        assert checkpoint_file.exists()

        await workflow_pipeline.delete_checkpoint("disk_checkpoint", from_disk=True)

        assert not checkpoint_file.exists()

    @pytest.mark.asyncio
    async def test_load_checkpoint_from_disk(
        self,
        workflow_pipeline: WorkflowPipeline,
        tmp_path: Path,
    ):
        """Test loading checkpoint from disk."""
        workflow_pipeline._checkpoint_dir = tmp_path / "checkpoints"

        # Create and persist checkpoint
        workflow_pipeline._state.status = PipelineStatus.PAUSED
        await workflow_pipeline.checkpoint("disk_load_test", persist=True)

        # Clear memory checkpoints
        workflow_pipeline._checkpoints.clear()

        # Reset state
        workflow_pipeline._state.status = PipelineStatus.IDLE

        # Resume from disk
        await workflow_pipeline.resume("disk_load_test", from_disk=True)

        assert workflow_pipeline.state.status == PipelineStatus.RUNNING


# =============================================================================
# Integration Tests
# =============================================================================


class TestPipelineIntegration:
    """Integration tests for pipeline and stage manager."""

    @pytest.mark.asyncio
    async def test_full_workflow_execution(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_tasks: list[Task],
    ):
        """Test full workflow execution through all stages."""
        results_collected = []

        async def collecting_handler(context: StageContext, tasks: list[Task]) -> list[TaskResult]:
            results = [
                TaskResult(
                    task_id=task.id,
                    success=True,
                    confidence_score=0.9,
                )
                for task in tasks
            ]
            results_collected.extend(results)
            return results

        for stage in WorkflowStage:
            workflow_pipeline.register_handler(stage, collecting_handler)

        final_results = await workflow_pipeline.execute(
            sample_tasks,
            auto_checkpoint=False,
        )

        assert workflow_pipeline.state.status == PipelineStatus.COMPLETED
        assert len(results_collected) == 3 * 6  # 3 tasks * 6 stages

    @pytest.mark.asyncio
    async def test_stage_manager_and_pipeline_coordination(
        self,
        workflow_pipeline: WorkflowPipeline,
        sample_task: Task,
    ):
        """Test coordination between StageManager and WorkflowPipeline."""
        stage_order = []

        async def tracking_handler(context: StageContext, tasks: list[Task]) -> list[TaskResult]:
            stage_order.append(context.stage)
            return [TaskResult(task_id=task.id, success=True) for task in tasks]

        for stage in WorkflowStage:
            workflow_pipeline.register_handler(stage, tracking_handler)

        await workflow_pipeline.execute(sample_task, auto_checkpoint=False)

        # Verify stages were executed in order
        expected_order = WorkflowStage.get_order()
        assert stage_order == expected_order
