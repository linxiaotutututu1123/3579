"""专家智能体模块.

本模块包含所有专家智能体的实现，每个智能体专注于特定的技术领域。

智能体列表:
    - TechWriterAgent: 技术文档智能体，精通技术文档和 API 文档写作
    - DevOpsEngineerAgent: DevOps 工程师，精通 CI/CD 和基础设施
    - CodeReviewerAgent: 代码审查员，精通代码质量和最佳实践
    - FrontendEngineerAgent: 前端工程师，精通 UI 组件开发
    - FullstackEngineerAgent: 全栈工程师，精通端到端开发
    - QAEngineerAgent: QA 工程师，精通测试策略和自动化测试
    - SecurityArchitectAgent: 安全架构师，精通应用安全和漏洞分析

Example:
    >>> from chairman_agents.agents.experts import TechWriterAgent, DocStyle
    >>> agent = TechWriterAgent(profile, llm_client)
    >>> result = await agent.execute(task)

    >>> from chairman_agents.agents.experts import DevOpsEngineerAgent
    >>> devops = DevOpsEngineerAgent(profile, llm_client, memory)
    >>> pipeline = await devops.design_pipeline(project_spec)

    >>> from chairman_agents.agents.experts import CodeReviewerAgent
    >>> reviewer = CodeReviewerAgent(profile, llm_client, memory)
    >>> review = await reviewer.review_code(code, context)

    >>> from chairman_agents.agents.experts import FullstackEngineerAgent
    >>> fullstack = FullstackEngineerAgent(profile, llm_client, memory)
    >>> design = await fullstack.design_feature(spec)

    >>> from chairman_agents.agents.experts import QAEngineerAgent
    >>> qa = QAEngineerAgent(profile, llm_client)
    >>> test_cases = await qa.generate_test_cases(feature_spec)

    >>> from chairman_agents.agents.experts import SecurityArchitectAgent
    >>> security = SecurityArchitectAgent(profile, llm_client, memory)
    >>> report = await security.audit_code(source_code, "python")
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

from chairman_agents.agents.experts.frontend_engineer import (
    # 枚举
    FrontendFramework,
    ComponentType,
    StyleApproach,
    # 数据类
    ComponentSpec,
    ComponentDesign,
    UIReviewComment,
    PerformanceMetrics,
    Optimization,
    DesignTokens,
    # 策略类
    FrameworkStrategy,
    ReactStrategy,
    VueStrategy,
    SvelteStrategy,
    FrameworkStrategyFactory,
    # 智能体
    FrontendEngineerAgent,
)

from chairman_agents.agents.experts.fullstack_engineer import (
    # 枚举
    FrontendFramework as FullstackFrontendFramework,
    BackendFramework,
    DatabaseType,
    APIStyle,
    # 规格数据类
    FeatureSpec as FullstackFeatureSpec,
    EndpointSpec,
    Entity,
    ServiceSpec,
    # 输出数据类
    FeatureDesign,
    APIImplementation,
    DatabaseSchema,
    Prototype,
    IntegrationPlan,
    # 智能体
    FullstackEngineerAgent,
)

from chairman_agents.agents.experts.qa_engineer import (
    # 枚举
    TestSeverity,
    TestType,
    TestStatus,
    CoverageType,
    EdgeCaseCategory,
    # 输入规格数据类
    FeatureSpec as QAFeatureSpec,
    FunctionSpec,
    DataSchema,
    TestScope,
    # 输出数据类
    TestCase,
    TestSuite,
    TestStrategy,
    EdgeCase,
    TestDataSet,
    CoverageRequirement,
    DefectReport,
    # 智能体
    QAEngineerAgent,
)

from chairman_agents.agents.experts.security_architect import (
    # 枚举
    VulnerabilitySeverity,
    VulnerabilityType,
    DataType,
    # 数据类
    Vulnerability,
    SecurityAuditReport,
    AuthRequirements,
    AuthDesign,
    EncryptionPlan,
    Dependency,
    DependencyAudit,
    # 检测规则
    OWASP_DETECTION_RULES,
    # 智能体
    SecurityArchitectAgent,
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
    # =========================================================================
    # CodeReviewer 相关
    # =========================================================================
    # 枚举
    "ReviewSeverity",
    "ReviewCategory",
    # 数据类
    "ReviewContext",
    "NamingIssue",
    "ComplexityReport",
    "RefactoringSuggestion",
    "PatternViolation",
    "QualityScores",
    "CodeReview",
    # 智能体
    "CodeReviewerAgent",
    # =========================================================================
    # FrontendEngineer 相关
    # =========================================================================
    # 枚举
    "FrontendFramework",
    "ComponentType",
    "StyleApproach",
    # 数据类
    "ComponentSpec",
    "ComponentDesign",
    "UIReviewComment",
    "PerformanceMetrics",
    "Optimization",
    "DesignTokens",
    # 策略类
    "FrameworkStrategy",
    "ReactStrategy",
    "VueStrategy",
    "SvelteStrategy",
    "FrameworkStrategyFactory",
    # 智能体
    "FrontendEngineerAgent",
    # =========================================================================
    # FullstackEngineer 相关
    # =========================================================================
    # 枚举
    "FullstackFrontendFramework",
    "BackendFramework",
    "DatabaseType",
    "APIStyle",
    # 规格数据类
    "FullstackFeatureSpec",
    "EndpointSpec",
    "Entity",
    "ServiceSpec",
    # 输出数据类
    "FeatureDesign",
    "APIImplementation",
    "DatabaseSchema",
    "Prototype",
    "IntegrationPlan",
    # 智能体
    "FullstackEngineerAgent",
    # =========================================================================
    # QAEngineer 相关
    # =========================================================================
    # 枚举
    "TestSeverity",
    "TestType",
    "TestStatus",
    "CoverageType",
    "EdgeCaseCategory",
    # 输入规格数据类
    "QAFeatureSpec",
    "FunctionSpec",
    "DataSchema",
    "TestScope",
    # 输出数据类
    "TestCase",
    "TestSuite",
    "TestStrategy",
    "EdgeCase",
    "TestDataSet",
    "CoverageRequirement",
    "DefectReport",
    # 智能体
    "QAEngineerAgent",
    # =========================================================================
    # SecurityArchitect 相关
    # =========================================================================
    # 枚举
    "VulnerabilitySeverity",
    "VulnerabilityType",
    "DataType",
    # 数据类
    "Vulnerability",
    "SecurityAuditReport",
    "AuthRequirements",
    "AuthDesign",
    "EncryptionPlan",
    "Dependency",
    "DependencyAudit",
    # 检测规则
    "OWASP_DETECTION_RULES",
    # 智能体
    "SecurityArchitectAgent",
]
