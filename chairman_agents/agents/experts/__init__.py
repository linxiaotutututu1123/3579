"""专家智能体模块.

本模块包含所有专家智能体的实现，每个智能体专注于特定的技术领域。

智能体列表:
    - TechWriterAgent: 技术文档智能体，精通技术文档和 API 文档写作
    - DevOpsEngineerAgent: DevOps 工程师，精通 CI/CD 和基础设施

Example:
    >>> from chairman_agents.agents.experts import TechWriterAgent, DocStyle
    >>> agent = TechWriterAgent(profile, llm_client)
    >>> result = await agent.execute(task)

    >>> from chairman_agents.agents.experts import DevOpsEngineerAgent
    >>> devops = DevOpsEngineerAgent(profile, llm_client, memory)
    >>> pipeline = await devops.design_pipeline(project_spec)
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

from chairman_agents.agents.experts.devops_engineer import (
    # 枚举
    CISystem,
    DeploymentStrategy,
    K8sResourceType,
    MonitoringType,
    # 规格数据类
    ProjectSpec,
    ApplicationSpec,
    DeploymentSpec,
    ReleaseSpec,
    Service,
    # 输出数据类
    PipelineStage,
    CIPipeline,
    K8sManifest,
    MonitoringConfig,
    DeploymentPlan,
    # 智能体
    DevOpsEngineerAgent,
)

from chairman_agents.agents.experts.code_reviewer import (
    # 枚举
    ReviewSeverity,
    ReviewCategory,
    # 数据类
    ReviewContext,
    NamingIssue,
    ComplexityReport,
    RefactoringSuggestion,
    PatternViolation,
    QualityScores,
    CodeReview,
    # 智能体
    CodeReviewerAgent,
)

__all__ = [
    # =========================================================================
    # TechWriter 相关
    # =========================================================================
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
    # =========================================================================
    # DevOps 相关
    # =========================================================================
    # 枚举
    "CISystem",
    "DeploymentStrategy",
    "K8sResourceType",
    "MonitoringType",
    # 规格数据类
    "ProjectSpec",
    "ApplicationSpec",
    "DeploymentSpec",
    "ReleaseSpec",
    "Service",
    # 输出数据类
    "PipelineStage",
    "CIPipeline",
    "K8sManifest",
    "MonitoringConfig",
    "DeploymentPlan",
    # 智能体
    "DevOpsEngineerAgent",
]
