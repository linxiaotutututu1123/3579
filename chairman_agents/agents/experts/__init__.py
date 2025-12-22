"""专家智能体模块.

本模块包含所有专家智能体的实现，每个智能体专注于特定的技术领域。

智能体列表:
    - TechWriterAgent: 技术文档智能体，精通技术文档和 API 文档写作

Example:
    >>> from chairman_agents.agents.experts import TechWriterAgent, DocStyle
    >>> agent = TechWriterAgent(profile, llm_client)
    >>> result = await agent.execute(task)
"""

from __future__ import annotations

from chairman_agents.agents.experts.tech_writer import (
    APIDocumentation,
    APIEndpoint,
    APISpec,
    BaseExpertAgent,
    Commit,
    DocFormat,
    DocStyle,
    FeatureSpec,
    GuideSection,
    ProjectInfo,
    TechWriterAgent,
    UserGuide,
)

__all__ = [
    # 枚举
    "DocStyle",
    "DocFormat",
    # 数据类
    "APIEndpoint",
    "APISpec",
    "APIDocumentation",
    "GuideSection",
    "UserGuide",
    "FeatureSpec",
    "ProjectInfo",
    "Commit",
    # 基类
    "BaseExpertAgent",
    # 智能体
    "TechWriterAgent",
]
