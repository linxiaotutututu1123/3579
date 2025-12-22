"""技术文档智能体 - 精通技术文档和 API 文档的写作专家.

本模块实现了 TechWriterAgent，一个专注于技术文档生成和优化的智能体。
支持多种文档格式和风格，能够生成高质量的技术文档、API 文档、用户指南等。

核心能力:
    - API 文档生成 (OpenAPI, Markdown, RST)
    - 用户指南编写
    - 代码注释优化 (Google, NumPy, Sphinx 风格)
    - README 生成
    - 变更日志维护

Example:
    >>> agent = TechWriterAgent(profile, llm_client)
    >>> result = await agent.execute(documentation_task)
    >>> api_docs = await agent.generate_api_docs(api_spec)
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from chairman_agents.core.types import (
    AgentCapability,
    AgentProfile,
    AgentRole,
    Artifact,
    ArtifactType,
    Task,
    TaskContext,
    TaskResult,
    TaskStatus,
    generate_id,
)

if TYPE_CHECKING:
    pass


# =============================================================================
# LLM 客户端协议
# =============================================================================


class LLMClientProtocol(Protocol):
    """LLM 客户端协议，定义智能体所需的接口."""

    async def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """生成文本响应."""
        ...


# =============================================================================
# 文档风格枚举
# =============================================================================


class DocStyle(Enum):
    """文档风格枚举.

    支持主流的 Python 文档风格规范:
    - GOOGLE: Google 风格，简洁明了
    - NUMPY: NumPy 风格，科学计算社区常用
    - SPHINX: Sphinx 风格，reStructuredText 格式
    - EPYTEXT: Epytext 风格，类似 Javadoc
    """

    GOOGLE = "google"
    """Google 风格文档字符串"""

    NUMPY = "numpy"
    """NumPy 风格文档字符串"""

    SPHINX = "sphinx"
    """Sphinx/reStructuredText 风格"""

    EPYTEXT = "epytext"
    """Epytext 风格（类 Javadoc）"""


class DocFormat(Enum):
    """文档输出格式枚举."""

    MARKDOWN = "markdown"
    """Markdown 格式"""

    RST = "rst"
    """reStructuredText 格式"""

    OPENAPI = "openapi"
    """OpenAPI/Swagger 格式"""

    HTML = "html"
    """HTML 格式"""

    ASCIIDOC = "asciidoc"
    """AsciiDoc 格式"""


# =============================================================================
# 数据类定义
# =============================================================================


@dataclass
class APIEndpoint:
    """API 端点定义.

    Attributes:
        path: 端点路径 (e.g., "/users/{id}")
        method: HTTP 方法 (GET, POST, PUT, DELETE, PATCH)
        summary: 端点简要描述
        description: 端点详细描述
        parameters: 请求参数列表
        request_body: 请求体定义
        responses: 响应定义
        tags: 标签分类
    """

    path: str = ""
    method: str = "GET"
    summary: str = ""
    description: str = ""
    parameters: list[dict[str, Any]] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    responses: dict[str, dict[str, Any]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    deprecated: bool = False
    security: list[dict[str, list[str]]] = field(default_factory=list)


@dataclass
class APISpec:
    """API 规范定义.

    Attributes:
        title: API 标题
        version: API 版本
        description: API 描述
        base_url: 基础 URL
        endpoints: 端点列表
        schemas: 数据模型定义
        security_schemes: 安全方案定义
    """

    title: str = ""
    version: str = "1.0.0"
    description: str = ""
    base_url: str = ""
    endpoints: list[APIEndpoint] = field(default_factory=list)
    schemas: dict[str, dict[str, Any]] = field(default_factory=dict)
    security_schemes: dict[str, dict[str, Any]] = field(default_factory=dict)
    contact: dict[str, str] = field(default_factory=dict)
    license_info: dict[str, str] = field(default_factory=dict)


@dataclass
class APIDocumentation:
    """生成的 API 文档.

    Attributes:
        spec: 原始 API 规范
        content: 生成的文档内容
        format: 文档格式
        sections: 文档章节
        examples: 使用示例
        generated_at: 生成时间
    """

    spec: APISpec
    content: str = ""
    format: DocFormat = DocFormat.MARKDOWN
    sections: dict[str, str] = field(default_factory=dict)
    examples: list[dict[str, str]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def word_count(self) -> int:
        """文档字数."""
        return len(self.content.split())


@dataclass
class GuideSection:
    """用户指南章节.

    Attributes:
        title: 章节标题
        content: 章节内容
        subsections: 子章节列表
        code_examples: 代码示例
        notes: 注意事项
        order: 章节顺序
    """

    title: str = ""
    content: str = ""
    subsections: list["GuideSection"] = field(default_factory=list)
    code_examples: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    order: int = 0


@dataclass
class UserGuide:
    """用户指南文档.

    Attributes:
        title: 指南标题
        description: 指南描述
        sections: 章节列表
        prerequisites: 前置要求
        examples: 完整示例
        faq: 常见问题
        glossary: 术语表
    """

    title: str = ""
    description: str = ""
    sections: list[GuideSection] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    faq: list[dict[str, str]] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)
    version: str = "1.0.0"
    last_updated: datetime = field(default_factory=datetime.now)

    def to_markdown(self) -> str:
        """将用户指南转换为 Markdown 格式."""
        lines = [f"# {self.title}", "", self.description, ""]

        if self.prerequisites:
            lines.extend(["## Prerequisites", ""])
            for prereq in self.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")

        for section in sorted(self.sections, key=lambda s: s.order):
            lines.extend([f"## {section.title}", "", section.content, ""])

            for example in section.code_examples:
                lang = example.get("language", "")
                code = example.get("code", "")
                lines.extend([f"```{lang}", code, "```", ""])

        if self.faq:
            lines.extend(["## FAQ", ""])
            for qa in self.faq:
                lines.extend([f"**Q: {qa.get('question', '')}**", ""])
                lines.extend([f"A: {qa.get('answer', '')}", ""])

        return "\n".join(lines)


@dataclass
class FeatureSpec:
    """功能规范定义.

    Attributes:
        name: 功能名称
        description: 功能描述
        use_cases: 使用场景
        requirements: 功能需求
        api_endpoints: 相关 API 端点
        code_samples: 代码示例
    """

    name: str = ""
    description: str = ""
    use_cases: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    api_endpoints: list[str] = field(default_factory=list)
    code_samples: list[dict[str, str]] = field(default_factory=list)
    version: str = "1.0.0"


@dataclass
class ProjectInfo:
    """项目信息.

    Attributes:
        name: 项目名称
        description: 项目描述
        version: 项目版本
        language: 主要编程语言
        features: 功能特性列表
        installation: 安装说明
        usage: 使用说明
        dependencies: 依赖列表
        license: 许可证
        authors: 作者列表
        repository: 仓库地址
    """

    name: str = ""
    description: str = ""
    version: str = "0.1.0"
    language: str = "Python"
    features: list[str] = field(default_factory=list)
    installation: str = ""
    usage: str = ""
    dependencies: list[str] = field(default_factory=list)
    license: str = "MIT"
    authors: list[str] = field(default_factory=list)
    repository: str = ""
    badges: list[dict[str, str]] = field(default_factory=list)


@dataclass
class Commit:
    """Git 提交信息.

    Attributes:
        hash: 提交哈希
        message: 提交消息
        author: 作者
        date: 提交日期
        type: 提交类型 (feat, fix, docs, etc.)
        scope: 影响范围
        breaking: 是否是破坏性变更
    """

    hash: str = ""
    message: str = ""
    author: str = ""
    date: datetime = field(default_factory=datetime.now)
    type: str = "chore"
    scope: str = ""
    breaking: bool = False
    body: str = ""
    footer: str = ""

    def parse_conventional_commit(self) -> None:
        """解析约定式提交消息."""
        pattern = r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<breaking>!)?: (?P<message>.+)$"
        match = re.match(pattern, self.message)
        if match:
            self.type = match.group("type")
            self.scope = match.group("scope") or ""
            self.breaking = match.group("breaking") == "!"
            self.message = match.group("message")


# =============================================================================
# 基础专家智能体
# =============================================================================


class BaseExpertAgent(ABC):
    """基础专家智能体抽象类.

    所有专家智能体的基类，定义了通用接口和基础功能。

    Attributes:
        profile: 智能体配置
        llm_client: LLM 客户端
        role: 智能体角色
    """

    role: AgentRole = AgentRole.TECH_WRITER

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any,  # LLMClientProtocol
    ) -> None:
        """初始化专家智能体.

        Args:
            profile: 智能体配置
            llm_client: LLM 客户端
        """
        self.profile = profile
        self.llm_client = llm_client
        self._task_history: list[TaskResult] = []

    @property
    def agent_id(self) -> str:
        """智能体 ID."""
        return self.profile.id

    @property
    def capabilities(self) -> list[AgentCapability]:
        """智能体能力列表."""
        return self.profile.capabilities

    @abstractmethod
    async def execute(self, task: Task, context: TaskContext | None = None) -> TaskResult:
        """执行任务.

        Args:
            task: 要执行的任务
            context: 任务上下文

        Returns:
            任务执行结果
        """
        ...

    async def _generate_with_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """使用 LLM 生成内容.

        Args:
            prompt: 输入提示
            temperature: 采样温度
            max_tokens: 最大 token 数

        Returns:
            生成的内容
        """
        return await self.llm_client.generate(
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )


# =============================================================================
# 技术文档智能体
# =============================================================================


class TechWriterAgent(BaseExpertAgent):
    """技术文档智能体 - 精通技术文档和 API 文档的写作专家.

    专注于生成高质量的技术文档，包括 API 文档、用户指南、README、
    变更日志等。支持多种文档格式和风格。

    Attributes:
        role: 智能体角色 (TECH_WRITER)
        default_doc_style: 默认文档风格
        default_doc_format: 默认文档格式

    Example:
        >>> profile = AgentProfile(
        ...     name="TechWriter",
        ...     role=AgentRole.TECH_WRITER,
        ...     capabilities=[AgentCapability.DOCUMENTATION, AgentCapability.API_DOCUMENTATION]
        ... )
        >>> agent = TechWriterAgent(profile, llm_client)
        >>> result = await agent.execute(task)
    """

    role = AgentRole.TECH_WRITER

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: Any,
        default_doc_style: DocStyle = DocStyle.GOOGLE,
        default_doc_format: DocFormat = DocFormat.MARKDOWN,
    ) -> None:
        """初始化技术文档智能体.

        Args:
            profile: 智能体配置
            llm_client: LLM 客户端
            default_doc_style: 默认文档风格
            default_doc_format: 默认文档格式
        """
        super().__init__(profile, llm_client)
        self.default_doc_style = default_doc_style
        self.default_doc_format = default_doc_format

    async def execute(self, task: Task, context: TaskContext | None = None) -> TaskResult:
        """执行文档任务.

        根据任务类型分派到具体的文档生成方法。

        Args:
            task: 文档任务
            context: 任务上下文

        Returns:
            任务执行结果
        """
        import time

        start_time = time.time()

        try:
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now()

            task_type = task.context.get("doc_type", "general")
            artifacts: list[Artifact] = []

            if task_type == "api_docs":
                api_spec = self._extract_api_spec(task)
                api_docs = await self.generate_api_docs(api_spec)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.API_SPEC,
                        name=f"{api_spec.title} API Documentation",
                        content=api_docs.content,
                        language="markdown",
                        created_by=self.agent_id,
                    )
                )

            elif task_type == "readme":
                project_info = self._extract_project_info(task)
                readme_content = await self.write_readme(project_info)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.DESIGN_DOC,
                        name="README.md",
                        content=readme_content,
                        language="markdown",
                        created_by=self.agent_id,
                    )
                )

            elif task_type == "user_guide":
                feature_spec = self._extract_feature_spec(task)
                user_guide = await self.create_user_guide(feature_spec)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.DESIGN_DOC,
                        name=f"{feature_spec.name} User Guide",
                        content=user_guide.to_markdown(),
                        language="markdown",
                        created_by=self.agent_id,
                    )
                )

            elif task_type == "docstrings":
                code = task.context.get("code", "")
                improved_code = await self.improve_docstrings(code)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.SOURCE_CODE,
                        name="Improved Code with Docstrings",
                        content=improved_code,
                        language=task.context.get("language", "python"),
                        created_by=self.agent_id,
                    )
                )

            elif task_type == "changelog":
                commits = self._extract_commits(task)
                changelog = await self.generate_changelog(commits)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.DESIGN_DOC,
                        name="CHANGELOG.md",
                        content=changelog,
                        language="markdown",
                        created_by=self.agent_id,
                    )
                )

            else:
                # 通用文档生成
                content = await self._generate_general_documentation(task, context)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.DESIGN_DOC,
                        name=task.title,
                        content=content,
                        language="markdown",
                        created_by=self.agent_id,
                    )
                )

            execution_time = time.time() - start_time
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            result = TaskResult(
                task_id=task.id,
                success=True,
                artifacts=artifacts,
                confidence_score=0.9,
                quality_score=0.85,
                execution_time_seconds=execution_time,
                suggestions=[
                    "Review generated documentation for accuracy",
                    "Add more examples if needed",
                ],
            )
            self._task_history.append(result)
            return result

        except Exception as e:
            task.status = TaskStatus.FAILED
            execution_time = time.time() - start_time
            return TaskResult(
                task_id=task.id,
                success=False,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_seconds=execution_time,
            )

    async def generate_api_docs(
        self,
        api: APISpec,
        format: DocFormat | None = None,
    ) -> APIDocumentation:
        """生成 API 文档.

        根据 API 规范生成完整的 API 文档，包括端点描述、
        请求/响应示例、认证说明等。

        Args:
            api: API 规范
            format: 输出格式，默认使用实例默认格式

        Returns:
            生成的 API 文档

        Example:
            >>> spec = APISpec(title="User API", endpoints=[...])
            >>> docs = await agent.generate_api_docs(spec)
            >>> print(docs.content)
        """
        doc_format = format or self.default_doc_format
        sections: dict[str, str] = {}
        examples: list[dict[str, str]] = []

        # 生成概述
        overview_prompt = f"""Generate an API overview section for:
Title: {api.title}
Version: {api.version}
Description: {api.description}
Base URL: {api.base_url}

Include:
1. Brief introduction
2. Authentication requirements
3. Rate limiting info (if applicable)
4. Response format conventions

Format: {doc_format.value}"""

        sections["overview"] = await self._generate_with_llm(
            overview_prompt, temperature=0.5, max_tokens=1024
        )

        # 生成端点文档
        endpoints_content = []
        for endpoint in api.endpoints:
            endpoint_prompt = f"""Generate documentation for this API endpoint:

Path: {endpoint.path}
Method: {endpoint.method}
Summary: {endpoint.summary}
Description: {endpoint.description}
Parameters: {endpoint.parameters}
Request Body: {endpoint.request_body}
Responses: {endpoint.responses}
Tags: {endpoint.tags}

Include:
1. Endpoint description
2. Parameter details with types
3. Request example
4. Response examples for each status code
5. Error handling notes

Format: {doc_format.value}"""

            endpoint_doc = await self._generate_with_llm(
                endpoint_prompt, temperature=0.3, max_tokens=1500
            )
            endpoints_content.append(endpoint_doc)

            # 生成示例
            example_prompt = f"""Generate a practical code example for calling:
{endpoint.method} {endpoint.path}

Provide examples in:
1. cURL
2. Python (requests)
3. JavaScript (fetch)"""

            example = await self._generate_with_llm(
                example_prompt, temperature=0.3, max_tokens=800
            )
            examples.append({
                "endpoint": f"{endpoint.method} {endpoint.path}",
                "code": example,
            })

        sections["endpoints"] = "\n\n---\n\n".join(endpoints_content)

        # 生成数据模型文档
        if api.schemas:
            schemas_prompt = f"""Document these API data models/schemas:
{api.schemas}

Include:
1. Model name and purpose
2. Field descriptions with types
3. Required vs optional fields
4. Example JSON

Format: {doc_format.value}"""

            sections["schemas"] = await self._generate_with_llm(
                schemas_prompt, temperature=0.3, max_tokens=1500
            )

        # 组合完整文档
        full_content = self._assemble_api_doc(api, sections, doc_format)

        return APIDocumentation(
            spec=api,
            content=full_content,
            format=doc_format,
            sections=sections,
            examples=examples,
            generated_at=datetime.now(),
        )

    async def write_readme(self, project: ProjectInfo) -> str:
        """生成 README 文件.

        根据项目信息生成完整的 README.md 文件。

        Args:
            project: 项目信息

        Returns:
            README 内容

        Example:
            >>> info = ProjectInfo(name="MyProject", description="A cool project")
            >>> readme = await agent.write_readme(info)
        """
        prompt = f"""Generate a professional README.md for this project:

Project Name: {project.name}
Description: {project.description}
Version: {project.version}
Language: {project.language}
Features: {project.features}
Dependencies: {project.dependencies}
License: {project.license}
Authors: {project.authors}
Repository: {project.repository}

Include these sections:
1. Title with badges (build status, version, license)
2. Description and key features
3. Installation instructions
4. Quick start / Usage examples
5. Configuration options
6. API reference (brief)
7. Contributing guidelines
8. License
9. Acknowledgments

Use clear, professional language. Add code examples where appropriate.
Format: Markdown with proper headers, code blocks, and formatting."""

        readme = await self._generate_with_llm(prompt, temperature=0.5, max_tokens=3000)

        # 添加徽章
        badges = self._generate_badges(project)
        if badges:
            readme = badges + "\n\n" + readme

        return readme

    async def create_user_guide(self, feature: FeatureSpec) -> UserGuide:
        """创建用户指南.

        根据功能规范创建详细的用户指南。

        Args:
            feature: 功能规范

        Returns:
            用户指南
        """
        # 生成章节
        sections: list[GuideSection] = []

        # 概述章节
        overview_prompt = f"""Write an overview section for a user guide about:
Feature: {feature.name}
Description: {feature.description}
Use Cases: {feature.use_cases}

Include:
1. What this feature does
2. Key benefits
3. When to use it"""

        overview_content = await self._generate_with_llm(
            overview_prompt, temperature=0.5, max_tokens=800
        )
        sections.append(
            GuideSection(
                title="Overview",
                content=overview_content,
                order=1,
            )
        )

        # 快速开始章节
        quickstart_prompt = f"""Write a quick start guide for:
Feature: {feature.name}
Requirements: {feature.requirements}
Code Samples: {feature.code_samples}

Include:
1. Prerequisites
2. Step-by-step setup
3. First example"""

        quickstart_content = await self._generate_with_llm(
            quickstart_prompt, temperature=0.4, max_tokens=1000
        )
        sections.append(
            GuideSection(
                title="Quick Start",
                content=quickstart_content,
                order=2,
                code_examples=feature.code_samples,
            )
        )

        # 详细使用章节
        for i, use_case in enumerate(feature.use_cases, start=3):
            use_case_prompt = f"""Write a detailed guide section for this use case:
Feature: {feature.name}
Use Case: {use_case}

Include:
1. Scenario description
2. Step-by-step instructions
3. Code examples
4. Expected results
5. Troubleshooting tips"""

            use_case_content = await self._generate_with_llm(
                use_case_prompt, temperature=0.4, max_tokens=1000
            )
            sections.append(
                GuideSection(
                    title=f"Use Case: {use_case[:50]}",
                    content=use_case_content,
                    order=i,
                )
            )

        # 生成 FAQ
        faq_prompt = f"""Generate 5 common FAQs for:
Feature: {feature.name}
Description: {feature.description}

Format each as:
Q: [question]
A: [answer]"""

        faq_content = await self._generate_with_llm(
            faq_prompt, temperature=0.5, max_tokens=800
        )
        faq = self._parse_faq(faq_content)

        return UserGuide(
            title=f"{feature.name} User Guide",
            description=feature.description,
            sections=sections,
            prerequisites=feature.requirements,
            faq=faq,
            version=feature.version,
        )

    async def improve_docstrings(
        self,
        code: str,
        style: DocStyle | None = None,
    ) -> str:
        """优化代码文档字符串.

        为代码添加或改进文档字符串。

        Args:
            code: 原始代码
            style: 文档风格，默认使用实例默认风格

        Returns:
            优化后的代码
        """
        doc_style = style or self.default_doc_style
        style_examples = self._get_docstring_style_example(doc_style)

        prompt = f"""Improve the docstrings in this code using {doc_style.value} style.

Style Example:
{style_examples}

Code to improve:
```python
{code}
```

Requirements:
1. Add missing docstrings to all public functions, classes, and methods
2. Follow {doc_style.value} style conventions exactly
3. Include type hints in docstrings if not present in function signatures
4. Add Args, Returns, Raises sections as appropriate
5. Add usage Examples where helpful
6. Keep existing comments that are useful
7. Return the complete improved code

Return ONLY the improved code, no explanations."""

        improved = await self._generate_with_llm(
            prompt, temperature=0.2, max_tokens=4000
        )

        # 提取代码块
        code_match = re.search(r"```python\n(.*?)```", improved, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()
        return improved.strip()

    async def generate_changelog(
        self,
        commits: list[Commit],
        version: str = "Unreleased",
    ) -> str:
        """生成变更日志.

        根据提交记录生成规范的 CHANGELOG。

        Args:
            commits: 提交记录列表
            version: 版本号

        Returns:
            CHANGELOG 内容
        """
        # 解析约定式提交
        for commit in commits:
            commit.parse_conventional_commit()

        # 按类型分组
        grouped: dict[str, list[Commit]] = {
            "feat": [],
            "fix": [],
            "docs": [],
            "style": [],
            "refactor": [],
            "perf": [],
            "test": [],
            "chore": [],
            "breaking": [],
        }

        for commit in commits:
            if commit.breaking:
                grouped["breaking"].append(commit)
            elif commit.type in grouped:
                grouped[commit.type].append(commit)
            else:
                grouped["chore"].append(commit)

        # 生成变更日志
        lines = [
            "# Changelog",
            "",
            "All notable changes to this project will be documented in this file.",
            "",
            "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),",
            "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).",
            "",
            f"## [{version}] - {datetime.now().strftime('%Y-%m-%d')}",
            "",
        ]

        section_titles = {
            "breaking": "BREAKING CHANGES",
            "feat": "Added",
            "fix": "Fixed",
            "docs": "Documentation",
            "style": "Style",
            "refactor": "Refactored",
            "perf": "Performance",
            "test": "Tests",
            "chore": "Chores",
        }

        for commit_type, title in section_titles.items():
            if grouped[commit_type]:
                lines.append(f"### {title}")
                lines.append("")
                for commit in grouped[commit_type]:
                    scope_str = f"**{commit.scope}**: " if commit.scope else ""
                    lines.append(f"- {scope_str}{commit.message}")
                lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _extract_api_spec(self, task: Task) -> APISpec:
        """从任务中提取 API 规范."""
        ctx = task.context
        return APISpec(
            title=ctx.get("api_title", task.title),
            version=ctx.get("api_version", "1.0.0"),
            description=ctx.get("api_description", task.description),
            base_url=ctx.get("base_url", ""),
            endpoints=[
                APIEndpoint(**ep) for ep in ctx.get("endpoints", [])
            ],
            schemas=ctx.get("schemas", {}),
        )

    def _extract_project_info(self, task: Task) -> ProjectInfo:
        """从任务中提取项目信息."""
        ctx = task.context
        return ProjectInfo(
            name=ctx.get("project_name", task.title),
            description=ctx.get("project_description", task.description),
            version=ctx.get("version", "0.1.0"),
            language=ctx.get("language", "Python"),
            features=ctx.get("features", []),
            dependencies=ctx.get("dependencies", []),
            license=ctx.get("license", "MIT"),
            authors=ctx.get("authors", []),
            repository=ctx.get("repository", ""),
        )

    def _extract_feature_spec(self, task: Task) -> FeatureSpec:
        """从任务中提取功能规范."""
        ctx = task.context
        return FeatureSpec(
            name=ctx.get("feature_name", task.title),
            description=ctx.get("feature_description", task.description),
            use_cases=ctx.get("use_cases", []),
            requirements=ctx.get("requirements", []),
            code_samples=ctx.get("code_samples", []),
        )

    def _extract_commits(self, task: Task) -> list[Commit]:
        """从任务中提取提交记录."""
        commits_data = task.context.get("commits", [])
        return [Commit(**c) if isinstance(c, dict) else c for c in commits_data]

    async def _generate_general_documentation(
        self,
        task: Task,
        context: TaskContext | None,
    ) -> str:
        """生成通用文档."""
        ctx_info = ""
        if context:
            ctx_info = f"""
Project: {context.project_name}
Tech Stack: {context.tech_stack}
Standards: {context.coding_standards}"""

        prompt = f"""Generate technical documentation for:

Title: {task.title}
Description: {task.description}
Context: {ctx_info}

Requirements:
1. Clear structure with headers
2. Technical accuracy
3. Code examples where appropriate
4. Professional tone

Format: Markdown"""

        return await self._generate_with_llm(prompt, temperature=0.5, max_tokens=2500)

    def _assemble_api_doc(
        self,
        api: APISpec,
        sections: dict[str, str],
        format: DocFormat,
    ) -> str:
        """组装完整的 API 文档."""
        lines = [
            f"# {api.title}",
            "",
            f"**Version:** {api.version}",
            "",
        ]

        if api.description:
            lines.extend([api.description, ""])

        for section_name, content in sections.items():
            lines.extend([
                f"## {section_name.title().replace('_', ' ')}",
                "",
                content,
                "",
            ])

        return "\n".join(lines)

    def _generate_badges(self, project: ProjectInfo) -> str:
        """生成 README 徽章."""
        badges = []

        if project.repository:
            repo_name = project.repository.split("/")[-2:]
            if len(repo_name) == 2:
                owner, repo = repo_name
                badges.append(
                    f"![Build Status](https://github.com/{owner}/{repo}/workflows/CI/badge.svg)"
                )

        badges.append(f"![Version](https://img.shields.io/badge/version-{project.version}-blue)")
        badges.append(f"![License](https://img.shields.io/badge/license-{project.license}-green)")

        return " ".join(badges)

    def _get_docstring_style_example(self, style: DocStyle) -> str:
        """获取文档风格示例."""
        examples = {
            DocStyle.GOOGLE: '''def function(arg1: str, arg2: int) -> bool:
    """Brief description of the function.

    Longer description if needed.

    Args:
        arg1: Description of arg1.
        arg2: Description of arg2.

    Returns:
        Description of return value.

    Raises:
        ValueError: Description of when this is raised.

    Example:
        >>> function("test", 42)
        True
    """''',
            DocStyle.NUMPY: '''def function(arg1: str, arg2: int) -> bool:
    """Brief description of the function.

    Longer description if needed.

    Parameters
    ----------
    arg1 : str
        Description of arg1.
    arg2 : int
        Description of arg2.

    Returns
    -------
    bool
        Description of return value.

    Raises
    ------
    ValueError
        Description of when this is raised.

    Examples
    --------
    >>> function("test", 42)
    True
    """''',
            DocStyle.SPHINX: '''def function(arg1: str, arg2: int) -> bool:
    """Brief description of the function.

    Longer description if needed.

    :param arg1: Description of arg1.
    :type arg1: str
    :param arg2: Description of arg2.
    :type arg2: int
    :returns: Description of return value.
    :rtype: bool
    :raises ValueError: Description of when this is raised.

    .. code-block:: python

        >>> function("test", 42)
        True
    """''',
            DocStyle.EPYTEXT: '''def function(arg1: str, arg2: int) -> bool:
    """Brief description of the function.

    Longer description if needed.

    @param arg1: Description of arg1.
    @type arg1: str
    @param arg2: Description of arg2.
    @type arg2: int
    @return: Description of return value.
    @rtype: bool
    @raise ValueError: Description of when this is raised.
    """''',
        }
        return examples.get(style, examples[DocStyle.GOOGLE])

    def _parse_faq(self, content: str) -> list[dict[str, str]]:
        """解析 FAQ 内容."""
        faq = []
        pattern = r"Q:\s*(.+?)\nA:\s*(.+?)(?=Q:|$)"
        matches = re.findall(pattern, content, re.DOTALL)
        for q, a in matches:
            faq.append({
                "question": q.strip(),
                "answer": a.strip(),
            })
        return faq


# =============================================================================
# 导出
# =============================================================================

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
