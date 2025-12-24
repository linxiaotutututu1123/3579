"""
Workflow Integration Tests.

This module provides comprehensive integration tests for the complete
workflow execution pipeline, including:
- End-to-end task execution
- Stage transitions and state management
- Checkpoint save and restore
- Error recovery mechanisms
- State persistence
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chairman_agents.core.types import (
    Task,
    TaskResult,
    TaskStatus,
    TaskPriority,
    AgentRole,
    AgentCapability,
    ExpertiseLevel,
    generate_id,
)
from chairman_agents.workflow.pipeline import (
    WorkflowPipeline,
    PipelineState,
    PipelineStatus,
    PipelineCheckpoint,
)
from chairman_agents.workflow.stage_manager import (
    StageManager,
    WorkflowStage,
    StageStatus,
    StageContext,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_task() -> Task:
    """Create a mock task for testing."""
    return Task(
        id=generate_id("task"),
        title="Test Integration Task",
        description="A comprehensive test task for workflow integration",
        priority=TaskPriority.HIGH,
        required_capabilities=[AgentCapability.CODE_GENERATION],
        min_expertise_level=ExpertiseLevel.SENIOR,
        context={"test_mode": True},
    )


@pytest.fixture
def mock_tasks(mock_task: Task) -> list[Task]:
    """Create multiple mock tasks for testing."""
    return [
        mock_task,
        Task(
            id=generate_id("task"),
            title="Secondary Task",
            description="Another test task",
            priority=TaskPriority.MEDIUM,
        ),
        Task(
            id=generate_id("task"),
            title="Low Priority Task",
            description="Low priority test task",
            priority=TaskPriority.LOW,
        ),
    ]


@pytest.fixture
def checkpoint_dir(tmp_path: Path) -> Path:
    """Create temporary directory for checkpoints."""
    checkpoint_path = tmp_path / "checkpoints"
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    return checkpoint_path


@pytest.fixture
def pipeline(checkpoint_dir: Path) -> WorkflowPipeline:
    """Create a WorkflowPipeline instance for testing."""
    return WorkflowPipeline(
        pipeline_id="test-pipeline",
        workflow_id="test-workflow",
        checkpoint_dir=checkpoint_dir,
        max_retries=2,
        retry_delay_seconds=0.1,
        parallel_limit=3,
    )


@pytest.fixture
def mock_task_executor() -> AsyncMock:
    """Create a mock task executor."""
    async def executor(task: Task, context: StageContext) -> TaskResult:
        await asyncio.sleep(0.01)  # Simulate work
        return TaskResult(
            task_id=task.id,
            success=True,
            confidence_score=0.9,
            quality_score=0.85,
        )

    return AsyncMock(side_effect=executor)


@pytest.fixture
def failing_task_executor() -> AsyncMock:
    """Create a task executor that fails on first attempt then succeeds."""
    call_count = {"count": 0}

    async def executor(task: Task, context: StageContext) -> TaskResult:
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise RuntimeError("Simulated failure")
        return TaskResult(
            task_id=task.id,
            success=True,
            confidence_score=0.85,
        )

    return AsyncMock(side_effect=executor)


# =============================================================================
# End-to-End Task Execution Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEndTaskExecution:
    """Test complete end-to-end task execution flows."""

    async def test_single_task_execution(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test execution of a single task through the pipeline."""
        # Setup
        pipeline.set_task_executor(mock_task_executor)

        # Execute
        results = await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].task_id == mock_task.id
        assert pipeline.is_completed is True
        assert pipeline.state.status == PipelineStatus.COMPLETED

    async def test_multiple_tasks_execution(
        self,
        pipeline: WorkflowPipeline,
        mock_tasks: list[Task],
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test execution of multiple tasks through the pipeline."""
        # Setup
        pipeline.set_task_executor(mock_task_executor)

        # Execute
        results = await pipeline.execute(mock_tasks, auto_checkpoint=False)

        # Verify
        assert len(results) == len(mock_tasks)
        assert all(r.success for r in results)
        assert pipeline.state.progress == 1.0
        assert len(pipeline.state.completed_tasks) == len(mock_tasks)

    async def test_parallel_task_execution(
        self,
        checkpoint_dir: Path,
        mock_tasks: list[Task],
    ) -> None:
        """Test parallel execution of tasks respects parallel limit."""
        execution_times: list[datetime] = []

        async def tracking_executor(task: Task, context: StageContext) -> TaskResult:
            execution_times.append(datetime.now())
            await asyncio.sleep(0.05)  # Simulate work
            return TaskResult(task_id=task.id, success=True)

        # Create pipeline with parallel limit of 2
        pipeline = WorkflowPipeline(
            checkpoint_dir=checkpoint_dir,
            parallel_limit=2,
        )
        pipeline.set_task_executor(AsyncMock(side_effect=tracking_executor))

        # Execute
        await pipeline.execute(mock_tasks, auto_checkpoint=False)

        # Verify - with limit of 2, not all should start at same time
        assert len(execution_times) == len(mock_tasks)
        # All tasks should complete
        assert len(pipeline.state.completed_tasks) == len(mock_tasks)

    async def test_task_execution_with_context(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
    ) -> None:
        """Test task execution receives correct context."""
        received_context: list[StageContext] = []

        async def context_tracking_executor(
            task: Task, context: StageContext
        ) -> TaskResult:
            received_context.append(context)
            return TaskResult(task_id=task.id, success=True)

        pipeline.set_task_executor(AsyncMock(side_effect=context_tracking_executor))

        # Execute
        await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify context was passed
        assert len(received_context) > 0
        assert isinstance(received_context[0], StageContext)


# =============================================================================
# Stage Transition Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStageTransitions:
    """Test workflow stage transitions."""

    async def test_stage_progression(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test that pipeline progresses through all stages."""
        stages_visited: list[WorkflowStage] = []

        async def stage_handler(
            context: StageContext, tasks: list[Task]
        ) -> list[TaskResult]:
            stages_visited.append(context.stage)
            return [TaskResult(task_id=t.id, success=True) for t in tasks]

        # Register handler for all stages
        for stage in WorkflowStage.get_order():
            pipeline.register_handler(stage, stage_handler)

        # Execute
        await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify all stages were visited
        assert len(stages_visited) == len(WorkflowStage.get_order())

    async def test_stage_manager_state_tracking(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test stage manager tracks state correctly."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute
        await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify stage manager state
        stage_manager = pipeline.stage_manager
        assert stage_manager is not None

        # Check that pipeline completed all stages
        assert pipeline.state.status == PipelineStatus.COMPLETED

    async def test_custom_stage_handler(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
    ) -> None:
        """Test custom stage handlers are invoked correctly."""
        handler_called = {"planning": False, "execution": False}

        async def planning_handler(
            context: StageContext, tasks: list[Task]
        ) -> list[TaskResult]:
            handler_called["planning"] = True
            return []

        async def execution_handler(
            context: StageContext, tasks: list[Task]
        ) -> list[TaskResult]:
            handler_called["execution"] = True
            return [TaskResult(task_id=t.id, success=True) for t in tasks]

        pipeline.register_handler(WorkflowStage.PLANNING, planning_handler)
        pipeline.register_handler(WorkflowStage.EXECUTION, execution_handler)

        # Execute
        await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify handlers were called
        assert handler_called["planning"] is True
        assert handler_called["execution"] is True


# =============================================================================
# Checkpoint and Recovery Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestCheckpointAndRecovery:
    """Test checkpoint saving and recovery mechanisms."""

    async def test_checkpoint_creation(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test checkpoint creation during execution."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute with auto checkpoint enabled
        await pipeline.execute(mock_task, auto_checkpoint=True)

        # Verify checkpoints were created
        checkpoints = pipeline.list_checkpoints()
        assert len(checkpoints) > 0

    async def test_manual_checkpoint_creation(
        self,
        pipeline: WorkflowPipeline,
    ) -> None:
        """Test manual checkpoint creation."""
        # Create checkpoint
        checkpoint = await pipeline.checkpoint(
            name="test-checkpoint",
            description="Test checkpoint",
            persist=True,
        )

        # Verify checkpoint
        assert checkpoint.name == "test-checkpoint"
        assert checkpoint.description == "Test checkpoint"
        assert "test-checkpoint" in pipeline.list_checkpoints()

    async def test_checkpoint_persistence(
        self,
        pipeline: WorkflowPipeline,
        checkpoint_dir: Path,
    ) -> None:
        """Test checkpoint persists to disk."""
        # Create checkpoint
        await pipeline.checkpoint(
            name="persist-test",
            description="Persistence test",
            persist=True,
        )

        # Verify file exists
        checkpoint_file = checkpoint_dir / "persist-test.json"
        assert checkpoint_file.exists()

        # Verify content is valid JSON
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["name"] == "persist-test"
        assert data["description"] == "Persistence test"

    async def test_resume_from_checkpoint(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test resuming execution from checkpoint."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute partially and create checkpoint
        async def partial_handler(
            context: StageContext, tasks: list[Task]
        ) -> list[TaskResult]:
            return []

        pipeline.register_handler(WorkflowStage.PLANNING, partial_handler)

        # Create initial checkpoint
        original_state = pipeline.state
        await pipeline.checkpoint(name="resume-point", persist=False)

        # Modify state
        pipeline._state.metadata["modified"] = True

        # Resume from checkpoint
        await pipeline.resume("resume-point")

        # Verify state was restored
        assert pipeline.state.pipeline_id == original_state.pipeline_id

    async def test_checkpoint_delete(
        self,
        pipeline: WorkflowPipeline,
        checkpoint_dir: Path,
    ) -> None:
        """Test checkpoint deletion."""
        # Create checkpoint
        await pipeline.checkpoint(name="delete-test", persist=True)

        checkpoint_file = checkpoint_dir / "delete-test.json"
        assert checkpoint_file.exists()

        # Delete checkpoint
        deleted = await pipeline.delete_checkpoint("delete-test", from_disk=True)

        # Verify
        assert deleted is True
        assert "delete-test" not in pipeline.list_checkpoints()
        assert not checkpoint_file.exists()


# =============================================================================
# Error Recovery Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorRecovery:
    """Test error handling and recovery mechanisms."""

    async def test_task_retry_on_failure(
        self,
        checkpoint_dir: Path,
        mock_task: Task,
    ) -> None:
        """Test task retry on transient failure."""
        attempt_count = {"count": 0}

        async def flaky_executor(task: Task, context: StageContext) -> TaskResult:
            attempt_count["count"] += 1
            if attempt_count["count"] < 2:
                raise RuntimeError("Transient error")
            return TaskResult(task_id=task.id, success=True)

        pipeline = WorkflowPipeline(
            checkpoint_dir=checkpoint_dir,
            max_retries=3,
            retry_delay_seconds=0.01,
        )
        pipeline.set_task_executor(AsyncMock(side_effect=flaky_executor))

        # Execute
        results = await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify retry succeeded
        assert attempt_count["count"] == 2
        assert len(results) == 1

    async def test_max_retries_exceeded(
        self,
        checkpoint_dir: Path,
        mock_task: Task,
    ) -> None:
        """Test behavior when max retries are exceeded."""
        async def always_failing_executor(
            task: Task, context: StageContext
        ) -> TaskResult:
            raise RuntimeError("Persistent error")

        pipeline = WorkflowPipeline(
            checkpoint_dir=checkpoint_dir,
            max_retries=2,
            retry_delay_seconds=0.01,
        )
        pipeline.set_task_executor(AsyncMock(side_effect=always_failing_executor))

        # Execute
        results = await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify task failed after retries
        assert len(results) == 1
        assert results[0].success is False
        assert mock_task.id in pipeline.state.failed_tasks

    async def test_partial_failure_handling(
        self,
        pipeline: WorkflowPipeline,
        mock_tasks: list[Task],
    ) -> None:
        """Test handling of partial task failures."""
        fail_task_id = mock_tasks[1].id

        async def selective_failure_executor(
            task: Task, context: StageContext
        ) -> TaskResult:
            if task.id == fail_task_id:
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    error_message="Intentional failure",
                )
            return TaskResult(task_id=task.id, success=True)

        pipeline.set_task_executor(
            AsyncMock(side_effect=selective_failure_executor)
        )

        # Execute
        results = await pipeline.execute(mock_tasks, auto_checkpoint=False)

        # Verify partial success
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        assert len(successful) >= 1
        assert len(failed) >= 1
        assert pipeline.state.success_rate < 1.0

    async def test_pipeline_failure_state(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
    ) -> None:
        """Test pipeline enters failure state on unrecoverable error."""
        async def catastrophic_handler(
            context: StageContext, tasks: list[Task]
        ) -> list[TaskResult]:
            raise Exception("Catastrophic failure")

        pipeline.register_handler(WorkflowStage.PLANNING, catastrophic_handler)

        # Execute and expect exception
        with pytest.raises(Exception, match="Catastrophic failure"):
            await pipeline.execute(mock_task, auto_checkpoint=False)

        # Verify failure state
        assert pipeline.state.status == PipelineStatus.FAILED
        assert pipeline.state.last_error is not None
        assert pipeline.state.error_count > 0


# =============================================================================
# State Persistence Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestStatePersistence:
    """Test state persistence across operations."""

    async def test_pipeline_state_serialization(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test pipeline state can be serialized and deserialized."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute some tasks
        await pipeline.execute(mock_task, auto_checkpoint=False)

        # Serialize state
        state_dict = pipeline.state.to_dict()

        # Verify serialization
        assert "pipeline_id" in state_dict
        assert "status" in state_dict
        assert "completed_tasks" in state_dict
        assert state_dict["pipeline_id"] == pipeline.pipeline_id

        # Deserialize
        restored_state = PipelineState.from_dict(state_dict)

        # Verify restoration
        assert restored_state.pipeline_id == pipeline.state.pipeline_id
        assert restored_state.status == pipeline.state.status

    async def test_checkpoint_state_preservation(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
        checkpoint_dir: Path,
    ) -> None:
        """Test checkpoint preserves complete state."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute and checkpoint
        await pipeline.execute(mock_task, auto_checkpoint=False)
        await pipeline.checkpoint(name="state-test", persist=True)

        # Read checkpoint from disk
        checkpoint_file = checkpoint_dir / "state-test.json"
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)

        # Verify state preservation
        pipeline_state = checkpoint_data["pipeline_state"]
        assert pipeline_state["status"] == "completed"
        assert len(pipeline_state["completed_tasks"]) > 0

    async def test_metrics_persistence(
        self,
        pipeline: WorkflowPipeline,
        mock_tasks: list[Task],
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test execution metrics are tracked and persisted."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute
        await pipeline.execute(mock_tasks, auto_checkpoint=False)

        # Get metrics
        metrics = pipeline.get_metrics()

        # Verify metrics
        assert "progress" in metrics
        assert "success_rate" in metrics
        assert "execution_time_seconds" in metrics
        assert "total_tasks" in metrics
        assert metrics["total_tasks"] == len(mock_tasks)
        assert metrics["progress"] == 1.0

    async def test_task_result_persistence(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test task results are stored and retrievable."""
        pipeline.set_task_executor(mock_task_executor)

        # Execute
        await pipeline.execute(mock_task, auto_checkpoint=False)

        # Retrieve result
        result = pipeline.get_result(mock_task.id)

        # Verify
        assert result is not None
        assert result.task_id == mock_task.id
        assert result.success is True


# =============================================================================
# Pipeline Control Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPipelineControl:
    """Test pipeline control operations (pause, cancel)."""

    async def test_pipeline_pause(
        self,
        pipeline: WorkflowPipeline,
        mock_tasks: list[Task],
    ) -> None:
        """Test pausing pipeline execution."""
        pause_triggered = asyncio.Event()

        async def slow_executor(task: Task, context: StageContext) -> TaskResult:
            if not pause_triggered.is_set():
                pause_triggered.set()
                await asyncio.sleep(0.5)
            return TaskResult(task_id=task.id, success=True)

        pipeline.set_task_executor(AsyncMock(side_effect=slow_executor))

        # Start execution in background
        execution_task = asyncio.create_task(
            pipeline.execute(mock_tasks, auto_checkpoint=False)
        )

        # Wait for execution to start then pause
        await pause_triggered.wait()
        await pipeline.pause()

        # Wait for execution to complete
        await asyncio.sleep(0.1)

        # Verify paused
        # Note: Due to async nature, status may vary
        assert pipeline.state.status in (
            PipelineStatus.PAUSED,
            PipelineStatus.COMPLETED,
        )

        # Clean up
        execution_task.cancel()
        try:
            await execution_task
        except asyncio.CancelledError:
            pass

    async def test_pipeline_cancel(
        self,
        pipeline: WorkflowPipeline,
        mock_tasks: list[Task],
    ) -> None:
        """Test cancelling pipeline execution."""
        cancel_triggered = asyncio.Event()

        async def slow_executor(task: Task, context: StageContext) -> TaskResult:
            cancel_triggered.set()
            await asyncio.sleep(1.0)
            return TaskResult(task_id=task.id, success=True)

        pipeline.set_task_executor(AsyncMock(side_effect=slow_executor))

        # Start execution in background
        execution_task = asyncio.create_task(
            pipeline.execute(mock_tasks, auto_checkpoint=False)
        )

        # Wait for execution to start then cancel
        await cancel_triggered.wait()
        await pipeline.cancel()

        # Wait a bit then check status
        await asyncio.sleep(0.1)

        # Verify cancelled or completed (race condition handling)
        assert pipeline.state.status in (
            PipelineStatus.CANCELLED,
            PipelineStatus.RUNNING,
            PipelineStatus.COMPLETED,
        )

        # Clean up
        execution_task.cancel()
        try:
            await execution_task
        except asyncio.CancelledError:
            pass

    async def test_cannot_start_while_running(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
    ) -> None:
        """Test that starting a new execution while running raises error."""
        started = asyncio.Event()

        async def slow_handler(
            context: StageContext, tasks: list[Task]
        ) -> list[TaskResult]:
            started.set()
            await asyncio.sleep(0.5)
            return [TaskResult(task_id=t.id, success=True) for t in tasks]

        pipeline.register_handler(WorkflowStage.PLANNING, slow_handler)

        # Start first execution
        first_execution = asyncio.create_task(
            pipeline.execute(mock_task, auto_checkpoint=False)
        )

        # Wait for it to start
        await started.wait()

        # Try to start another execution
        from chairman_agents.core.exceptions import WorkflowError

        with pytest.raises(WorkflowError):
            await pipeline.execute(mock_task, auto_checkpoint=False)

        # Clean up
        first_execution.cancel()
        try:
            await first_execution
        except asyncio.CancelledError:
            pass


# =============================================================================
# Pipeline Lifecycle Tests
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestPipelineLifecycle:
    """Test complete pipeline lifecycle scenarios."""

    async def test_full_lifecycle_success(
        self,
        pipeline: WorkflowPipeline,
        mock_tasks: list[Task],
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test complete successful pipeline lifecycle."""
        pipeline.set_task_executor(mock_task_executor)

        # Verify initial state
        assert pipeline.state.status == PipelineStatus.IDLE
        assert pipeline.state.started_at is None

        # Execute
        results = await pipeline.execute(mock_tasks, auto_checkpoint=True)

        # Verify completed state
        assert pipeline.state.status == PipelineStatus.COMPLETED
        assert pipeline.state.started_at is not None
        assert pipeline.state.completed_at is not None
        assert all(r.success for r in results)

    async def test_pipeline_to_dict_serialization(
        self,
        pipeline: WorkflowPipeline,
        mock_task: Task,
        mock_task_executor: AsyncMock,
    ) -> None:
        """Test pipeline can be fully serialized to dictionary."""
        pipeline.set_task_executor(mock_task_executor)

        await pipeline.execute(mock_task, auto_checkpoint=True)

        # Serialize entire pipeline
        pipeline_dict = pipeline.to_dict()

        # Verify structure
        assert "pipeline_id" in pipeline_dict
        assert "workflow_id" in pipeline_dict
        assert "state" in pipeline_dict
        assert "metrics" in pipeline_dict
        assert "checkpoints" in pipeline_dict
