#!/usr/bin/env python3
"""Script to fix routes.py type errors."""

CONTENT = '''"""API模块 - FastAPI路由定义.

本模块定义了REST API的所有路由端点,
包括任务、团队和工作流的CRUD操作。

路由分组:
    - /tasks: 任务管理
    - /teams: 团队管理
    - /workflows: 工作流管理
    - /health: 健康检查
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status

from .schemas import (
    ErrorResponse,
    HealthResponse,
    TaskListResponse,
    TaskRequest,
    TaskResponse,
    TaskStatusEnum,
    TeamListResponse,
    TeamResponse,
    WorkflowListResponse,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStageInfo,
    WorkflowStatusEnum,
)


# =============================================================================
# 路由器定义
# =============================================================================

# 主路由器
router = APIRouter()

# 任务路由器
tasks_router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={
        404: {"model": ErrorResponse, "description": "任务未找到"},
        422: {"model": ErrorResponse, "description": "验证错误"},
    },
)

# 团队路由器
teams_router = APIRouter(
    prefix="/teams",
    tags=["teams"],
    responses={
        404: {"model": ErrorResponse, "description": "团队未找到"},
    },
)

# 工作流路由器
workflows_router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={
        404: {"model": ErrorResponse, "description": "工作流未找到"},
        422: {"model": ErrorResponse, "description": "验证错误"},
    },
)


# =============================================================================
# 内存存储 (临时实现,后续替换为持久化存储)
# =============================================================================

_tasks_store: dict[str, dict[str, Any]] = {}
_teams_store: dict[str, dict[str, Any]] = {}
_workflows_store: dict[str, dict[str, Any]] = {}
_id_counter: dict[str, int] = {"task": 0, "team": 0, "workflow": 0}


def _generate_id(prefix: str) -> str:
    """生成唯一ID.

    Args:
        prefix: ID前缀 (task, team, workflow)

    Returns:
        格式化的唯一ID
    """
    _id_counter[prefix] += 1
    return f"{prefix}_{_id_counter[prefix]:06d}"


def _to_task_response(task_data: dict[str, Any]) -> TaskResponse:
    """将任务数据转换为TaskResponse.

    只提取TaskResponse模型所需的字段。

    Args:
        task_data: 完整的任务数据字典

    Returns:
        TaskResponse实例
    """
    return TaskResponse(
        id=task_data["id"],
        title=task_data["title"],
        description=task_data["description"],
        status=task_data["status"],
        priority=task_data["priority"],
        assigned_to=task_data.get("assigned_to"),
        created_at=task_data["created_at"],
        updated_at=task_data.get("updated_at"),
        completed_at=task_data.get("completed_at"),
        result=task_data.get("result"),
    )


def _to_workflow_response(workflow_data: dict[str, Any]) -> WorkflowResponse:
    """将工作流数据转换为WorkflowResponse.

    只提取WorkflowResponse模型所需的字段。

    Args:
        workflow_data: 完整的工作流数据字典

    Returns:
        WorkflowResponse实例
    """
    stages_data: list[dict[str, Any]] = workflow_data.get("stages", [])
    stages = [WorkflowStageInfo(**stage) for stage in stages_data]
    return WorkflowResponse(
        id=workflow_data["id"],
        name=workflow_data["name"],
        description=workflow_data.get("description", ""),
        status=workflow_data["status"],
        team_id=workflow_data.get("team_id"),
        stages=stages,
        current_stage=workflow_data.get("current_stage"),
        progress=workflow_data.get("progress", 0.0),
        created_at=workflow_data["created_at"],
        started_at=workflow_data.get("started_at"),
        completed_at=workflow_data.get("completed_at"),
    )


# =============================================================================
# 任务路由
# =============================================================================


@tasks_router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建任务",
    description="创建一个新任务并返回任务详情。",
)
async def create_task(request: TaskRequest) -> TaskResponse:
    """创建新任务.

    Args:
        request: 任务创建请求

    Returns:
        创建的任务详情
    """
    task_id = _generate_id("task")
    now = datetime.now()

    task_data: dict[str, Any] = {
        "id": task_id,
        "title": request.title,
        "description": request.description,
        "status": TaskStatusEnum.PENDING,
        "priority": request.priority,
        "assigned_to": None,
        "created_at": now,
        "updated_at": None,
        "completed_at": None,
        "result": None,
        "required_capabilities": request.required_capabilities,
        "required_role": request.required_role,
        "estimated_hours": request.estimated_hours,
        "deadline": request.deadline,
        "context": request.context,
    }

    _tasks_store[task_id] = task_data

    return _to_task_response(task_data)


@tasks_router.get(
    "",
    response_model=TaskListResponse,
    summary="获取任务列表",
    description="获取任务列表,支持分页和状态过滤。",
)
async def list_tasks(
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
    status_filter: Annotated[
        TaskStatusEnum | None,
        Query(alias="status", description="任务状态过滤"),
    ] = None,
) -> TaskListResponse:
    """获取任务列表.

    Args:
        page: 页码
        page_size: 每页数量
        status_filter: 状态过滤

    Returns:
        任务列表响应
    """
    tasks = list(_tasks_store.values())

    # 应用状态过滤
    if status_filter is not None:
        tasks = [t for t in tasks if t["status"] == status_filter]

    # 按创建时间倒序排序
    tasks.sort(key=lambda x: x["created_at"], reverse=True)

    total = len(tasks)

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    paginated_tasks = tasks[start:end]

    return TaskListResponse(
        tasks=[_to_task_response(t) for t in paginated_tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@tasks_router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="获取任务详情",
    description="根据任务ID获取任务详细信息。",
)
async def get_task(task_id: str) -> TaskResponse:
    """获取任务详情.

    Args:
        task_id: 任务ID

    Returns:
        任务详情

    Raises:
        HTTPException: 任务不存在时抛出404错误
    """
    if task_id not in _tasks_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在",
        )

    return _to_task_response(_tasks_store[task_id])


# =============================================================================
# 团队路由
# =============================================================================


@teams_router.get(
    "",
    response_model=TeamListResponse,
    summary="获取团队列表",
    description="获取所有团队的列表。",
)
async def list_teams() -> TeamListResponse:
    """获取团队列表.

    Returns:
        团队列表响应
    """
    teams = list(_teams_store.values())

    # 按创建时间倒序排序
    teams.sort(key=lambda x: x["created_at"], reverse=True)

    return TeamListResponse(
        teams=[TeamResponse(**t) for t in teams],
        total=len(teams),
    )


@teams_router.get(
    "/{team_id}",
    response_model=TeamResponse,
    summary="获取团队详情",
    description="根据团队ID获取团队详细信息。",
)
async def get_team(team_id: str) -> TeamResponse:
    """获取团队详情.

    Args:
        team_id: 团队ID

    Returns:
        团队详情

    Raises:
        HTTPException: 团队不存在时抛出404错误
    """
    if team_id not in _teams_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"团队 {team_id} 不存在",
        )

    return TeamResponse(**_teams_store[team_id])


# =============================================================================
# 工作流路由
# =============================================================================


@workflows_router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建工作流",
    description="创建一个新工作流并返回工作流详情。",
)
async def create_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """创建新工作流.

    Args:
        request: 工作流创建请求

    Returns:
        创建的工作流详情
    """
    workflow_id = _generate_id("workflow")
    now = datetime.now()

    # 默认6阶段工作流
    default_stages = [
        "requirement_analysis",
        "architecture_design",
        "implementation",
        "testing",
        "code_review",
        "deployment",
    ]

    stages = request.stages or default_stages
    stage_info: list[dict[str, Any]] = [
        {
            "name": stage,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "tasks": [],
        }
        for stage in stages
    ]

    workflow_data: dict[str, Any] = {
        "id": workflow_id,
        "name": request.name,
        "description": request.description,
        "status": WorkflowStatusEnum.CREATED,
        "team_id": request.team_id,
        "stages": stage_info,
        "current_stage": None,
        "progress": 0.0,
        "created_at": now,
        "started_at": None,
        "completed_at": None,
        "project_goal": request.project_goal,
        "config": request.config,
    }

    _workflows_store[workflow_id] = workflow_data

    return _to_workflow_response(workflow_data)


@workflows_router.get(
    "",
    response_model=WorkflowListResponse,
    summary="获取工作流列表",
    description="获取所有工作流的列表。",
)
async def list_workflows(
    status_filter: Annotated[
        WorkflowStatusEnum | None,
        Query(alias="status", description="工作流状态过滤"),
    ] = None,
) -> WorkflowListResponse:
    """获取工作流列表.

    Args:
        status_filter: 状态过滤

    Returns:
        工作流列表响应
    """
    workflows = list(_workflows_store.values())

    # 应用状态过滤
    if status_filter is not None:
        workflows = [w for w in workflows if w["status"] == status_filter]

    # 按创建时间倒序排序
    workflows.sort(key=lambda x: x["created_at"], reverse=True)

    return WorkflowListResponse(
        workflows=[_to_workflow_response(w) for w in workflows],
        total=len(workflows),
    )


@workflows_router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
    summary="获取工作流详情",
    description="根据工作流ID获取工作流详细信息。",
)
async def get_workflow(workflow_id: str) -> WorkflowResponse:
    """获取工作流详情.

    Args:
        workflow_id: 工作流ID

    Returns:
        工作流详情

    Raises:
        HTTPException: 工作流不存在时抛出404错误
    """
    if workflow_id not in _workflows_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"工作流 {workflow_id} 不存在",
        )

    return _to_workflow_response(_workflows_store[workflow_id])


# =============================================================================
# 健康检查路由
# =============================================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="健康检查",
    description="检查服务健康状态。",
)
async def health_check() -> HealthResponse:
    """健康检查端点.

    Returns:
        健康状态响应
    """
    from chairman_agents import __version__

    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(),
    )


# =============================================================================
# 注册子路由器
# =============================================================================

router.include_router(tasks_router)
router.include_router(teams_router)
router.include_router(workflows_router)


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "router",
    "tasks_router",
    "teams_router",
    "workflows_router",
]
'''

if __name__ == "__main__":
    import os
    target = os.path.join(os.path.dirname(__file__), "chairman_agents", "api", "routes.py")
    with open(target, "w", encoding="utf-8") as f:
        f.write(CONTENT)
    print(f"Successfully written to {target}")
