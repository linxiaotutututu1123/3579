"""Chairman Agents - 主席级智能体团队系统.

一个世界级的多智能体协作框架，包含：
- 18种专家角色
- 35种细分能力
- 辩论/共识/结对编程协作机制
- 6阶段标准工作流程

版本: 0.1.0
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Chairman Agents Team"

# 延迟导入以避免循环依赖
def __getattr__(name: str):
    """延迟加载模块."""
    if name == "core":
        from . import core
        return core
    if name == "agents":
        from . import agents
        return agents
    if name == "cognitive":
        from . import cognitive
        return cognitive
    if name == "collaboration":
        from . import collaboration
        return collaboration
    if name == "orchestration":
        from . import orchestration
        return orchestration
    if name == "workflow":
        from . import workflow
        return workflow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
