"""API模块 - FastAPI服务器配置.

本模块提供FastAPI应用的工厂函数和服务器配置,
支持灵活的应用初始化和中间件配置。

主要功能:
    - create_app: 应用工厂函数
    - 中间件配置
    - 异常处理
    - OpenAPI文档配置
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chairman_agents import __version__
from chairman_agents.core.config import init_config, reset_config, get_config
from chairman_agents.observability.logger import (
    configure_logging,
    reset_logger,
    get_logger,
    LogLevel,
    LogFormat,
)

from .routes import router
from .schemas import ErrorResponse


# =============================================================================
# 应用生命周期管理
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理器.

    处理应用启动和关闭时的资源初始化和清理。

    Args:
        app: FastAPI应用实例

    Yields:
        None
    """
    # =========================================================================
    # 启动时执行
    # =========================================================================

    # 1. 初始化配置 (从环境变量或配置文件加载, 并创建必要目录)
    config = init_config(ensure_directories=True)

    # 2. 配置结构化日志
    # 根据配置决定日志级别和格式
    log_level = LogLevel.DEBUG if app.debug else LogLevel(config.logging.level.lower())
    log_format = LogFormat.JSON if config.logging.enable_json else LogFormat.TEXT

    # 如果启用文件日志, 设置日志文件路径
    log_file = None
    if config.logging.enable_file:
        log_file = config.paths.logs / "api.log"

    logger = configure_logging(
        name="chairman-agents-api",
        level=log_level,
        format=log_format,
        log_file=log_file,
    )

    # 3. 记录启动信息
    logger.info(
        "API服务启动",
        version=__version__,
        environment=config.environment,
        debug=app.debug,
    )

    # 将配置和日志器存储到app.state以便路由访问
    app.state.config = config
    app.state.logger = logger

    yield

    # =========================================================================
    # 关闭时执行
    # =========================================================================

    # 1. 记录关闭信息
    logger.info("API服务正在关闭")

    # 2. 清理资源
    reset_logger()
    reset_config()


# =============================================================================
# 异常处理器
# =============================================================================


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """请求验证异常处理器.

    将Pydantic验证错误转换为标准错误响应格式。

    Args:
        request: 请求对象
        exc: 验证异常

    Returns:
        JSON错误响应
    """
    errors = exc.errors()
    error_details = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in errors
    ]

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="ValidationError",
            message="请求参数验证失败",
            detail={"errors": error_details},
        ).model_dump(),
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """通用异常处理器.

    捕获未处理的异常并返回标准错误响应。

    Args:
        request: 请求对象
        exc: 异常

    Returns:
        JSON错误响应
    """
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="服务器内部错误",
            detail={"exception": str(exc)},
        ).model_dump(),
    )


# =============================================================================
# 应用工厂函数
# =============================================================================


def create_app(
    *,
    title: str = "Chairman Agents API",
    description: str | None = None,
    debug: bool = False,
    cors_origins: list[str] | None = None,
    docs_url: str | None = "/docs",
    redoc_url: str | None = "/redoc",
    openapi_url: str | None = "/openapi.json",
) -> FastAPI:
    """创建FastAPI应用实例.

    应用工厂函数,支持灵活的配置选项。

    Args:
        title: API标题
        description: API描述
        debug: 调试模式
        cors_origins: CORS允许的源列表
        docs_url: Swagger文档URL (None禁用)
        redoc_url: ReDoc文档URL (None禁用)
        openapi_url: OpenAPI规范URL (None禁用)

    Returns:
        配置好的FastAPI应用实例

    Example:
        ```python
        from chairman_agents.api import create_app

        # 开发环境
        app = create_app(debug=True)

        # 生产环境
        app = create_app(
            debug=False,
            cors_origins=["https://example.com"],
            docs_url=None,  # 禁用文档
        )
        ```
    """
    # 默认描述
    if description is None:
        description = """
Chairman Agents API - 主席级智能体团队系统

一个世界级的多智能体协作框架REST API,提供:

- **任务管理**: 创建、查询、跟踪任务
- **团队管理**: 查看团队和代理信息
- **工作流管理**: 创建和管理开发工作流

## 特性

- 18种专家角色
- 35种细分能力
- 辩论/共识/结对编程协作机制
- 6阶段标准工作流程
        """

    # 创建应用
    app = FastAPI(
        title=title,
        description=description,
        version=__version__,
        debug=debug,
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        contact={
            "name": "Chairman Agents Team",
        },
    )

    # 配置CORS
    if cors_origins is None:
        cors_origins = ["*"] if debug else []

    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 注册异常处理器
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    if not debug:
        # 生产环境捕获所有未处理异常
        app.add_exception_handler(
            Exception,
            generic_exception_handler,
        )

    # 注册路由
    app.include_router(router, prefix="/api/v1")

    # 根路由重定向到文档
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """根路由,返回API信息."""
        return {
            "name": title,
            "version": __version__,
            "docs": docs_url or "disabled",
        }

    return app


# =============================================================================
# 默认应用实例
# =============================================================================

# 创建默认应用实例 (用于开发和测试)
app = create_app(debug=True)


# =============================================================================
# 开发服务器入口
# =============================================================================


def run_dev_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
) -> None:
    """运行开发服务器.

    使用uvicorn运行FastAPI开发服务器。

    Args:
        host: 绑定主机
        port: 绑定端口
        reload: 是否启用热重载

    Example:
        ```python
        from chairman_agents.api import run_dev_server

        if __name__ == "__main__":
            run_dev_server(port=8080)
        ```
    """
    try:
        import uvicorn
    except ImportError:
        print("错误: 需要安装uvicorn")
        print("运行: pip install uvicorn[standard]")
        return

    uvicorn.run(
        "chairman_agents.api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    "create_app",
    "app",
    "run_dev_server",
    "lifespan",
]
