"""API模块 - REST API服务.

本模块提供Chairman Agents系统的REST API接口,
基于FastAPI实现,支持任务、团队和工作流管理。

子模块:
    - schemas: Pydantic数据模型
    - routes: FastAPI路由定义
    - server: 服务器配置和工厂函数

示例:
    ```python
    from chairman_agents.api import create_app, run_dev_server

    # 创建应用
    app = create_app(debug=True)

    # 或者直接运行开发服务器
    run_dev_server(port=8000)
    ```
"""

from __future__ import annotations

from .schemas import (
    # 枚举
    AgentRoleEnum,
    TaskPriorityEnum,
    TaskStatusEnum,
    WorkflowStatusEnum,
    # Task模型
    TaskListResponse,
    TaskRequest,
    TaskResponse,
    # Team模型
    AgentInfo,
    TeamListResponse,
    TeamRequest,
    TeamResponse,
    # Workflow模型
    WorkflowListResponse,
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStageInfo,
    # 通用模型
    ErrorResponse,
    HealthResponse,
)
from .routes import router, tasks_router, teams_router, workflows_router
from .server import app, create_app, run_dev_server

__all__ = [
    # 枚举
    "TaskStatusEnum",
    "TaskPriorityEnum",
    "AgentRoleEnum",
    "WorkflowStatusEnum",
    # Task模型
    "TaskRequest",
    "TaskResponse",
    "TaskListResponse",
    # Team模型
    "AgentInfo",
    "TeamRequest",
    "TeamResponse",
    "TeamListResponse",
    # Workflow模型
    "WorkflowStageInfo",
    "WorkflowRequest",
    "WorkflowResponse",
    "WorkflowListResponse",
    # 通用模型
    "ErrorResponse",
    "HealthResponse",
    # 路由
    "router",
    "tasks_router",
    "teams_router",
    "workflows_router",
    # 服务器
    "create_app",
    "app",
    "run_dev_server",
]
