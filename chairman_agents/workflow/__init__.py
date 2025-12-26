"""工作流模块 - 6阶段标准流程.

本模块提供完整的工作流管理功能:
- StageManager: 阶段管理器，控制工作流阶段生命周期
- WorkflowPipeline: 工作流管道，协调整个工作流执行

6阶段标准流程:
    1. INITIALIZATION: 初始化阶段 - 加载配置、验证前置条件
    2. PLANNING: 规划阶段 - 任务分解、资源分配
    3. EXECUTION: 执行阶段 - 执行任务、生成工件
    4. REVIEW: 审查阶段 - 质量检查、代码审查
    5. REFINEMENT: 完善阶段 - 根据反馈修改、优化
    6. COMPLETION: 完成阶段 - 最终验证、资源清理

Example:
    >>> from chairman_agents.workflow import (
    ...     WorkflowStage,
    ...     StageManager,
    ...     WorkflowPipeline,
    ... )
    >>>
    >>> # 使用阶段管理器
    >>> manager = StageManager(workflow_id="wf_001")
    >>> await manager.enter_stage(WorkflowStage.INITIALIZATION)
    >>> await manager.complete_stage()
    >>>
    >>> # 使用工作流管道
    >>> pipeline = WorkflowPipeline(workflow_id="wf_001")
    >>> results = await pipeline.execute(tasks)
    >>> await pipeline.checkpoint("after_execution")
"""

from __future__ import annotations

from chairman_agents.workflow.stage_manager import (
    WorkflowStage,
    StageStatus,
    StageTransition,
    StageContext,
    StageManager,
    StageHook,
)
from chairman_agents.workflow.pipeline import (
    PipelineStatus,
    PipelineState,
    PipelineCheckpoint,
    WorkflowPipeline,
    TaskExecutor,
    StageHandler,
)


__all__ = [
    # stage_manager.py
    "WorkflowStage",
    "StageStatus",
    "StageTransition",
    "StageContext",
    "StageManager",
    "StageHook",
    # pipeline.py
    "PipelineStatus",
    "PipelineState",
    "PipelineCheckpoint",
    "WorkflowPipeline",
    "TaskExecutor",
    "StageHandler",
]
