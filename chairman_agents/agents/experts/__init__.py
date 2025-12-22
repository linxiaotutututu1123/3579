"""专家智能体模块.

本模块包含所有专家智能体的实现，每个智能体专注于特定的技术领域。

智能体列表:
    - TechWriterAgent: 技术文档智能体，精通技术文档和 API 文档写作
    - CodeReviewerAgent: 代码审查智能体，精通代码质量和最佳实践

Example:
    >>> from chairman_agents.agents.experts import TechWriterAgent, CodeReviewerAgent
    >>> writer = TechWriterAgent(profile, llm_client, memory)
    >>> reviewer = CodeReviewerAgent(profile, llm_client, memory)
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

from chairman_agents.agents.experts.code_reviewer import (
    # Enums
    ReviewSeverity,
    ReviewCategory,
    # Data Classes
    ReviewContext,
    NamingIssue,
    ComplexityReport,
    RefactoringSuggestion,
    PatternViolation,
    QualityScores,
    CodeReview,
    # Agent
    CodeReviewerAgent,
)

__all__ = [
    # 枚举
    "DocStyle",
    "DocFormat",
    "ReviewSeverity",
    "ReviewCategory",
    # 数据类 - TechWriter
    "APIEndpoint",
    "APISpec",
    "APIDocumentation",
    "GuideSection",
    "UserGuide",
    "FeatureSpec",
    "ProjectInfo",
    "Commit",
    # 数据类 - CodeReviewer
    "ReviewContext",
    "NamingIssue",
    "ComplexityReport",
    "RefactoringSuggestion",
    "PatternViolation",
    "QualityScores",
    "CodeReview",
    # 基类
    "BaseExpertAgent",
    # 智能体
    "TechWriterAgent",
    "CodeReviewerAgent",
]
