"""前端工程师智能体模块.

本模块实现了精通 React/Vue/CSS 的前端专家智能体，提供:
- UI 组件设计与实现
- 响应式布局和 CSS 架构
- 前端性能优化
- 可访问性 (a11y) 最佳实践
- 状态管理策略

架构设计:
    FrontendEngineerAgent: 前端工程师智能体
    FrameworkStrategy: 框架策略接口
    ReactStrategy/VueStrategy/SvelteStrategy: 具体框架策略

Example:
    >>> agent = FrontendEngineerAgent(llm_client, config)
    >>> result = await agent.run(ui_task, context)
    >>> design = await agent.design_component(component_spec)
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

from chairman_agents.agents.base import AgentConfig, BaseExpertAgent
from chairman_agents.cognitive.reasoning import ReasoningStrategy
from chairman_agents.core.exceptions import AgentError, TaskExecutionError
from chairman_agents.core.types import (
    AgentCapability,
    AgentRole,
    Artifact,
    ArtifactType,
    ReasoningStep,
    ReviewComment,
    Task,
    TaskResult,
    ToolType,
    generate_id,
)


# =============================================================================
# 枚举和类型定义
# =============================================================================


class FrontendFramework(Enum):
    """前端框架枚举."""

    REACT = "react"
    VUE = "vue"
    SVELTE = "svelte"
    ANGULAR = "angular"
    VANILLA = "vanilla"


class ComponentType(Enum):
    """组件类型枚举."""

    ATOMIC = "atomic"  # 原子组件（Button, Input）
    MOLECULE = "molecule"  # 分子组件（SearchBox, Card）
    ORGANISM = "organism"  # 有机体组件（Header, Sidebar）
    TEMPLATE = "template"  # 模板组件（PageLayout）
    PAGE = "page"  # 页面组件


class StyleApproach(Enum):
    """样式方案枚举."""

    CSS_MODULES = "css_modules"
    STYLED_COMPONENTS = "styled_components"
    TAILWIND = "tailwind"
    SCSS = "scss"
    CSS_IN_JS = "css_in_js"
    VANILLA_CSS = "vanilla_css"


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class ComponentSpec:
    """组件规格定义.

    Attributes:
        name: 组件名称
        type: 组件类型
        description: 组件描述
        props: 组件属性定义
        state: 组件状态定义
        events: 组件事件定义
        children: 子组件规格
        accessibility: 可访问性要求
        responsive: 响应式设计要求
        framework: 目标框架
        style_approach: 样式方案
    """

    name: str
    type: ComponentType = ComponentType.MOLECULE
    description: str = ""
    props: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    accessibility: dict[str, Any] = field(default_factory=dict)
    responsive: dict[str, Any] = field(default_factory=dict)
    framework: FrontendFramework = FrontendFramework.REACT
    style_approach: StyleApproach = StyleApproach.CSS_MODULES


@dataclass
class ComponentDesign:
    """组件设计结果.

    Attributes:
        spec: 原始规格
        component_code: 组件代码
        style_code: 样式代码
        test_code: 测试代码
        storybook_code: Storybook 文档代码
        props_interface: 属性接口定义
        documentation: 组件文档
        accessibility_notes: 可访问性说明
        performance_notes: 性能说明
    """

    spec: ComponentSpec
    component_code: str = ""
    style_code: str = ""
    test_code: str = ""
    storybook_code: str = ""
    props_interface: str = ""
    documentation: str = ""
    accessibility_notes: list[str] = field(default_factory=list)
    performance_notes: list[str] = field(default_factory=list)


@dataclass
class UIReviewComment(ReviewComment):
    """UI 代码审查评论.

    扩展 ReviewComment，添加 UI 特定字段。

    Attributes:
        ui_category: UI 问题类别
        accessibility_impact: 可访问性影响
        responsive_issue: 响应式问题
        browser_compatibility: 浏览器兼容性问题
    """

    ui_category: str = ""  # layout, styling, interaction, accessibility
    accessibility_impact: str | None = None
    responsive_issue: str | None = None
    browser_compatibility: list[str] = field(default_factory=list)


@dataclass
class PerformanceMetrics:
    """性能指标.

    Attributes:
        lcp: Largest Contentful Paint (ms)
        fid: First Input Delay (ms)
        cls: Cumulative Layout Shift
        ttfb: Time to First Byte (ms)
        bundle_size_kb: 打包大小 (KB)
        component_render_time_ms: 组件渲染时间 (ms)
        re_render_count: 重渲染次数
        memory_usage_mb: 内存使用 (MB)
    """

    lcp: float = 0.0
    fid: float = 0.0
    cls: float = 0.0
    ttfb: float = 0.0
    bundle_size_kb: float = 0.0
    component_render_time_ms: float = 0.0
    re_render_count: int = 0
    memory_usage_mb: float = 0.0


@dataclass
class Optimization:
    """优化建议.

    Attributes:
        type: 优化类型
        description: 描述
        impact: 预期影响
        effort: 实现难度
        code_changes: 代码变更建议
        priority: 优先级
    """

    type: str  # render, bundle, memory, network
    description: str
    impact: str  # high, medium, low
    effort: str  # high, medium, low
    code_changes: list[str] = field(default_factory=list)
    priority: int = 3


@dataclass
class DesignTokens:
    """设计令牌.

    Attributes:
        colors: 颜色令牌
        typography: 排版令牌
        spacing: 间距令牌
        breakpoints: 断点令牌
        shadows: 阴影令牌
        borders: 边框令牌
        animations: 动画令牌
    """

    colors: dict[str, str] = field(default_factory=dict)
    typography: dict[str, Any] = field(default_factory=dict)
    spacing: dict[str, str] = field(default_factory=dict)
    breakpoints: dict[str, str] = field(default_factory=dict)
    shadows: dict[str, str] = field(default_factory=dict)
    borders: dict[str, Any] = field(default_factory=dict)
    animations: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 框架策略模式
# =============================================================================


class FrameworkStrategy(ABC):
    """框架策略抽象基类.

    定义不同前端框架的代码生成策略。
    """

    @property
    @abstractmethod
    def framework(self) -> FrontendFramework:
        """返回框架类型."""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """返回文件扩展名."""
        ...

    @abstractmethod
    def generate_component_template(
        self,
        name: str,
        props: dict[str, Any],
        state: dict[str, Any],
    ) -> str:
        """生成组件模板代码."""
        ...

    @abstractmethod
    def generate_props_interface(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        """生成属性接口定义."""
        ...

    @abstractmethod
    def generate_state_management(
        self,
        state: dict[str, Any],
    ) -> str:
        """生成状态管理代码."""
        ...

    @abstractmethod
    def generate_event_handlers(
        self,
        events: list[str],
    ) -> str:
        """生成事件处理器代码."""
        ...

    @abstractmethod
    def generate_test_template(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        """生成测试模板代码."""
        ...


class ReactStrategy(FrameworkStrategy):
    """React 框架策略."""

    @property
    def framework(self) -> FrontendFramework:
        return FrontendFramework.REACT

    @property
    def file_extension(self) -> str:
        return ".tsx"

    def generate_component_template(
        self,
        name: str,
        props: dict[str, Any],
        state: dict[str, Any],
    ) -> str:
        props_interface = self.generate_props_interface(name, props)
        state_hooks = self.generate_state_management(state)

        return f'''import React, {{ useState, useCallback, useMemo }} from 'react';
import styles from './{name}.module.css';

{props_interface}

/**
 * {name} 组件
 *
 * @component
 * @example
 * <{name} />
 */
export const {name}: React.FC<{name}Props> = ({{
  {", ".join(props.keys()) if props else ""}
}}) => {{
{state_hooks}

  return (
    <div className={{styles.container}}>
      {{/* 组件内容 */}}
    </div>
  );
}};

{name}.displayName = '{name}';

export default {name};
'''

    def generate_props_interface(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        if not props:
            return f"export interface {name}Props {{}}"

        prop_lines = []
        for prop_name, prop_def in props.items():
            prop_type = prop_def.get("type", "any") if isinstance(prop_def, dict) else prop_def
            required = prop_def.get("required", True) if isinstance(prop_def, dict) else True
            description = prop_def.get("description", "") if isinstance(prop_def, dict) else ""

            optional = "" if required else "?"
            doc = f"  /** {description} */\n" if description else ""
            prop_lines.append(f"{doc}  {prop_name}{optional}: {prop_type};")

        return f"""export interface {name}Props {{
{chr(10).join(prop_lines)}
}}"""

    def generate_state_management(
        self,
        state: dict[str, Any],
    ) -> str:
        if not state:
            return ""

        lines = []
        for state_name, state_def in state.items():
            initial = state_def.get("initial", "null") if isinstance(state_def, dict) else "null"
            state_type = state_def.get("type", "any") if isinstance(state_def, dict) else "any"

            setter_name = f"set{state_name[0].upper()}{state_name[1:]}"
            lines.append(
                f"  const [{state_name}, {setter_name}] = useState<{state_type}>({initial});"
            )

        return "\n".join(lines)

    def generate_event_handlers(
        self,
        events: list[str],
    ) -> str:
        if not events:
            return ""

        handlers = []
        for event in events:
            handler_name = f"handle{event[0].upper()}{event[1:]}"
            handlers.append(f"""  const {handler_name} = useCallback((event?: React.SyntheticEvent) => {{
    // 处理 {event} 事件
    console.log('{event} event triggered', event);
    // 在此处添加具体的业务逻辑
  }}, []);""")

        return "\n\n".join(handlers)

    def generate_test_template(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        return f'''import React from 'react';
import {{ render, screen, fireEvent }} from '@testing-library/react';
import {{ {name} }} from './{name}';

describe('{name}', () => {{
  it('renders without crashing', () => {{
    render(<{name} />);
  }});

  it('matches snapshot', () => {{
    const {{ container }} = render(<{name} />);
    expect(container).toMatchSnapshot();
  }});

  it('handles user interactions correctly', () => {{
    render(<{name} />);
    // TODO: 添加交互测试
  }});

  it('is accessible', async () => {{
    const {{ container }} = render(<{name} />);
    // TODO: 添加可访问性测试
  }});
}});
'''


class VueStrategy(FrameworkStrategy):
    """Vue 框架策略."""

    @property
    def framework(self) -> FrontendFramework:
        return FrontendFramework.VUE

    @property
    def file_extension(self) -> str:
        return ".vue"

    def generate_component_template(
        self,
        name: str,
        props: dict[str, Any],
        state: dict[str, Any],
    ) -> str:
        props_def = self._generate_props_definition(props)
        state_refs = self.generate_state_management(state)

        return f'''<template>
  <div class="{self._to_kebab_case(name)}">
    <!-- 组件内容 -->
  </div>
</template>

<script setup lang="ts">
import {{ ref, computed, onMounted }} from 'vue';

{props_def}

{state_refs}

// 生命周期钩子
onMounted(() => {{
  // 初始化逻辑
}});
</script>

<style scoped>
.{self._to_kebab_case(name)} {{
  /* 组件样式 */
}}
</style>
'''

    def _generate_props_definition(self, props: dict[str, Any]) -> str:
        if not props:
            return "// 无属性定义"

        lines = []
        for prop_name, prop_def in props.items():
            prop_type = prop_def.get("type", "String") if isinstance(prop_def, dict) else "String"
            required = prop_def.get("required", True) if isinstance(prop_def, dict) else True
            default = prop_def.get("default") if isinstance(prop_def, dict) else None

            default_str = f", default: {json.dumps(default)}" if default is not None else ""
            lines.append(f"  {prop_name}: {{ type: {prop_type}, required: {str(required).lower()}{default_str} }},")

        return f"""const props = defineProps({{
{chr(10).join(lines)}
}});"""

    def generate_props_interface(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        return self._generate_props_definition(props)

    def generate_state_management(
        self,
        state: dict[str, Any],
    ) -> str:
        if not state:
            return ""

        lines = []
        for state_name, state_def in state.items():
            initial = state_def.get("initial", "null") if isinstance(state_def, dict) else "null"
            lines.append(f"const {state_name} = ref({initial});")

        return "\n".join(lines)

    def generate_event_handlers(
        self,
        events: list[str],
    ) -> str:
        if not events:
            return ""

        handlers = []
        for event in events:
            handler_name = f"handle{event[0].upper()}{event[1:]}"
            handlers.append(f"""const {handler_name} = () => {{
  // TODO: 实现 {event} 处理逻辑
}};""")

        return "\n\n".join(handlers)

    def generate_test_template(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        return f'''import {{ mount }} from '@vue/test-utils';
import {name} from './{name}.vue';

describe('{name}', () => {{
  it('renders properly', () => {{
    const wrapper = mount({name});
    expect(wrapper.exists()).toBe(true);
  }});

  it('matches snapshot', () => {{
    const wrapper = mount({name});
    expect(wrapper.html()).toMatchSnapshot();
  }});

  it('handles events correctly', async () => {{
    const wrapper = mount({name});
    // TODO: 添加事件测试
  }});
}});
'''

    @staticmethod
    def _to_kebab_case(name: str) -> str:
        """将 PascalCase 转换为 kebab-case."""
        return re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()


class SvelteStrategy(FrameworkStrategy):
    """Svelte 框架策略."""

    @property
    def framework(self) -> FrontendFramework:
        return FrontendFramework.SVELTE

    @property
    def file_extension(self) -> str:
        return ".svelte"

    def generate_component_template(
        self,
        name: str,
        props: dict[str, Any],
        state: dict[str, Any],
    ) -> str:
        props_exports = self._generate_props_exports(props)
        state_vars = self.generate_state_management(state)

        return f'''<script lang="ts">
{props_exports}

{state_vars}
</script>

<div class="container">
  <!-- 组件内容 -->
</div>

<style>
  .container {{
    /* 组件样式 */
  }}
</style>
'''

    def _generate_props_exports(self, props: dict[str, Any]) -> str:
        if not props:
            return "// 无属性定义"

        lines = []
        for prop_name, prop_def in props.items():
            prop_type = prop_def.get("type", "any") if isinstance(prop_def, dict) else "any"
            default = prop_def.get("default") if isinstance(prop_def, dict) else None

            default_str = f" = {json.dumps(default)}" if default is not None else ""
            lines.append(f"  export let {prop_name}: {prop_type}{default_str};")

        return "\n".join(lines)

    def generate_props_interface(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        return self._generate_props_exports(props)

    def generate_state_management(
        self,
        state: dict[str, Any],
    ) -> str:
        if not state:
            return ""

        lines = []
        for state_name, state_def in state.items():
            initial = state_def.get("initial", "null") if isinstance(state_def, dict) else "null"
            state_type = state_def.get("type", "any") if isinstance(state_def, dict) else "any"
            lines.append(f"  let {state_name}: {state_type} = {initial};")

        return "\n".join(lines)

    def generate_event_handlers(
        self,
        events: list[str],
    ) -> str:
        if not events:
            return ""

        handlers = []
        for event in events:
            handler_name = f"handle{event[0].upper()}{event[1:]}"
            handlers.append(f"""  function {handler_name}() {{
    // TODO: 实现 {event} 处理逻辑
  }}""")

        return "\n\n".join(handlers)

    def generate_test_template(
        self,
        name: str,
        props: dict[str, Any],
    ) -> str:
        return f'''import {{ render }} from '@testing-library/svelte';
import {name} from './{name}.svelte';

describe('{name}', () => {{
  it('renders', () => {{
    const {{ container }} = render({name});
    expect(container).toBeTruthy();
  }});

  it('matches snapshot', () => {{
    const {{ container }} = render({name});
    expect(container).toMatchSnapshot();
  }});
}});
'''


# =============================================================================
# 策略工厂
# =============================================================================


class FrameworkStrategyFactory:
    """框架策略工厂."""

    _strategies: dict[FrontendFramework, type[FrameworkStrategy]] = {
        FrontendFramework.REACT: ReactStrategy,
        FrontendFramework.VUE: VueStrategy,
        FrontendFramework.SVELTE: SvelteStrategy,
    }

    @classmethod
    def get_strategy(cls, framework: FrontendFramework) -> FrameworkStrategy:
        """获取指定框架的策略.

        Args:
            framework: 前端框架

        Returns:
            框架策略实例

        Raises:
            ValueError: 当框架不支持时
        """
        strategy_class = cls._strategies.get(framework)
        if not strategy_class:
            raise ValueError(f"不支持的框架: {framework.value}")
        return strategy_class()

    @classmethod
    def register_strategy(
        cls,
        framework: FrontendFramework,
        strategy_class: type[FrameworkStrategy],
    ) -> None:
        """注册新的框架策略.

        Args:
            framework: 前端框架
            strategy_class: 策略类
        """
        cls._strategies[framework] = strategy_class


# =============================================================================
# 前端工程师智能体
# =============================================================================


class FrontendEngineerAgent(BaseExpertAgent):
    """前端工程师智能体.

    精通 React/Vue/CSS 的前端专家，具备以下核心能力:
    - UI 组件设计与实现
    - 响应式布局和 CSS 架构
    - 前端性能优化
    - 可访问性 (a11y) 最佳实践
    - 状态管理策略

    使用策略模式支持多种前端框架 (React/Vue/Svelte)。

    Attributes:
        role: FRONTEND_ENGINEER
        capabilities: 前端相关能力列表
        allowed_tools: 允许使用的工具

    Example:
        >>> agent = FrontendEngineerAgent(llm_client)
        >>> result = await agent.run(task, context)
        >>> design = await agent.design_component(spec)
    """

    role = AgentRole.FRONTEND_ENGINEER

    capabilities = [
        AgentCapability.CODE_GENERATION,
        AgentCapability.CODE_REVIEW,
        AgentCapability.CODE_REFACTORING,
        AgentCapability.CODE_OPTIMIZATION,
        AgentCapability.JAVASCRIPT_EXPERT,
        AgentCapability.TYPESCRIPT_EXPERT,
        AgentCapability.UNIT_TESTING,
        AgentCapability.E2E_TESTING,
    ]

    allowed_tools = [
        ToolType.CODE_EXECUTOR,
        ToolType.FILE_SYSTEM,
        ToolType.LINTER,
        ToolType.TEST_RUNNER,
        ToolType.BROWSER,
    ]

    def __init__(
        self,
        llm_client: Any,
        config: AgentConfig | None = None,
        tool_executor: Any | None = None,
        memory_system: Any | None = None,
        default_framework: FrontendFramework = FrontendFramework.REACT,
    ) -> None:
        """初始化前端工程师智能体.

        Args:
            llm_client: LLM 客户端
            config: 智能体配置
            tool_executor: 工具执行器
            memory_system: 记忆系统
            default_framework: 默认前端框架
        """
        # 设置默认配置
        if config is None:
            config = AgentConfig(
                name="Frontend Engineer",
                description="精通 React/Vue/CSS 的前端专家，擅长组件设计、性能优化和可访问性实现。",
            )

        super().__init__(
            llm_client=llm_client,
            config=config,
            tool_executor=tool_executor,
            memory_system=memory_system,
        )

        self.default_framework = default_framework
        self._current_strategy: FrameworkStrategy | None = None

    # =========================================================================
    # 核心执行方法
    # =========================================================================

    async def execute(self, task: Task) -> TaskResult:
        """执行前端任务.

        分析任务类型，使用推理引擎决策，执行相应的前端任务。

        Args:
            task: 要执行的任务

        Returns:
            任务执行结果
        """
        reasoning_trace: list[ReasoningStep] = []

        # 步骤1: 分析任务类型
        task_analysis = await self._analyze_task(task)
        reasoning_trace.append(ReasoningStep(
            step_number=1,
            thought=f"任务分析: {task_analysis['type']}",
            action="analyze_task",
            observation=json.dumps(task_analysis, ensure_ascii=False),
            confidence=0.9,
        ))

        # 步骤2: 使用推理引擎决策
        reasoning_result = await self.reason(
            problem=f"如何实现前端任务: {task.title}\n\n{task.description}",
            context={
                "task_type": task_analysis["type"],
                "framework": task_analysis.get("framework", self.default_framework.value),
                "requirements": task_analysis.get("requirements", []),
            },
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        )

        reasoning_trace.extend([
            ReasoningStep(
                step_number=i + 2,
                thought=node.thought,
                confidence=node.score,
            )
            for i, node in enumerate(reasoning_result.reasoning_path)
        ])

        # 步骤3: 根据任务类型执行
        try:
            artifacts = await self._execute_by_type(task, task_analysis)

            return self.create_success_result(
                task_id=task.id,
                artifacts=artifacts,
                reasoning_trace=reasoning_trace,
                confidence=reasoning_result.confidence,
            )

        except Exception as e:
            return self.create_failure_result(
                task_id=task.id,
                error_message=str(e),
                error_type="frontend_execution_error",
            )

    async def _analyze_task(self, task: Task) -> dict[str, Any]:
        """分析任务类型和需求.

        Args:
            task: 任务

        Returns:
            任务分析结果
        """
        prompt = f"""分析以下前端开发任务，提取关键信息:

任务标题: {task.title}
任务描述: {task.description}

请以 JSON 格式返回:
{{
  "type": "component_design|ui_review|performance_optimization|style_generation|general",
  "framework": "react|vue|svelte|vanilla",
  "component_type": "atomic|molecule|organism|template|page",
  "requirements": ["需求1", "需求2"],
  "accessibility_needs": ["a11y需求"],
  "responsive_needs": ["响应式需求"],
  "performance_concerns": ["性能关注点"]
}}"""

        response = await self.llm_client.generate(
            prompt,
            temperature=0.3,
            max_tokens=500,
        )

        # 解析 JSON
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # 默认返回
        return {
            "type": "general",
            "framework": self.default_framework.value,
            "requirements": [],
        }

    async def _execute_by_type(
        self,
        task: Task,
        analysis: dict[str, Any],
    ) -> list[Artifact]:
        """根据任务类型执行.

        Args:
            task: 任务
            analysis: 任务分析结果

        Returns:
            产出物列表
        """
        task_type = analysis.get("type", "general")
        framework = FrontendFramework(analysis.get("framework", self.default_framework.value))

        if task_type == "component_design":
            spec = ComponentSpec(
                name=task.title.replace(" ", ""),
                framework=framework,
                description=task.description,
            )
            design = await self.design_component(spec)
            return [
                self.create_artifact(
                    content=design.component_code,
                    artifact_type=ArtifactType.SOURCE_CODE,
                    name=f"{spec.name}{FrameworkStrategyFactory.get_strategy(framework).file_extension}",
                    language="typescript",
                    framework=framework.value,
                ),
                self.create_artifact(
                    content=design.style_code,
                    artifact_type=ArtifactType.SOURCE_CODE,
                    name=f"{spec.name}.module.css",
                    language="css",
                ),
            ]

        elif task_type == "ui_review":
            code = task.context.get("code", "")
            comments = await self.review_ui(code)
            return [
                self.create_artifact(
                    content=json.dumps(
                        [{"comment": c.comment, "severity": c.severity, "category": c.ui_category}
                         for c in comments],
                        ensure_ascii=False,
                        indent=2,
                    ),
                    artifact_type=ArtifactType.REVIEW_REPORT,
                    name="ui_review_report.json",
                ),
            ]

        elif task_type == "performance_optimization":
            metrics = PerformanceMetrics(**task.context.get("metrics", {}))
            optimizations = await self.optimize_performance(metrics)
            return [
                self.create_artifact(
                    content=json.dumps(
                        [{"type": o.type, "description": o.description, "impact": o.impact}
                         for o in optimizations],
                        ensure_ascii=False,
                        indent=2,
                    ),
                    artifact_type=ArtifactType.PERFORMANCE_REPORT,
                    name="optimization_report.json",
                ),
            ]

        elif task_type == "style_generation":
            tokens = DesignTokens(**task.context.get("design_tokens", {}))
            styles = await self.generate_styles(tokens)
            return [
                self.create_artifact(
                    content=styles,
                    artifact_type=ArtifactType.SOURCE_CODE,
                    name="design-tokens.css",
                    language="css",
                ),
            ]

        else:
            # 通用任务处理
            code = await self._generate_frontend_code(task, framework)
            return [
                self.create_artifact(
                    content=code,
                    artifact_type=ArtifactType.SOURCE_CODE,
                    name="output.tsx",
                    language="typescript",
                    framework=framework.value,
                ),
            ]

    # =========================================================================
    # 核心功能方法
    # =========================================================================

    async def design_component(self, spec: ComponentSpec) -> ComponentDesign:
        """设计 UI 组件.

        根据组件规格生成完整的组件代码、样式、测试和文档。

        Args:
            spec: 组件规格

        Returns:
            组件设计结果

        Example:
            >>> spec = ComponentSpec(
            ...     name="Button",
            ...     type=ComponentType.ATOMIC,
            ...     props={"label": {"type": "string", "required": True}},
            ... )
            >>> design = await agent.design_component(spec)
        """
        # 获取框架策略
        strategy = FrameworkStrategyFactory.get_strategy(spec.framework)
        self._current_strategy = strategy

        # 生成组件代码
        component_code = strategy.generate_component_template(
            name=spec.name,
            props=spec.props,
            state=spec.state,
        )

        # 生成事件处理器
        if spec.events:
            event_handlers = strategy.generate_event_handlers(spec.events)
            # 将事件处理器插入组件代码
            component_code = self._inject_event_handlers(component_code, event_handlers)

        # 生成样式代码
        style_code = await self._generate_component_styles(spec)

        # 生成测试代码
        test_code = strategy.generate_test_template(spec.name, spec.props)

        # 生成 Storybook 文档
        storybook_code = await self._generate_storybook(spec)

        # 生成文档
        documentation = await self._generate_component_docs(spec)

        # 可访问性说明
        accessibility_notes = await self._analyze_accessibility(spec)

        # 性能说明
        performance_notes = await self._analyze_component_performance(spec)

        return ComponentDesign(
            spec=spec,
            component_code=component_code,
            style_code=style_code,
            test_code=test_code,
            storybook_code=storybook_code,
            props_interface=strategy.generate_props_interface(spec.name, spec.props),
            documentation=documentation,
            accessibility_notes=accessibility_notes,
            performance_notes=performance_notes,
        )

    async def review_ui(self, code: str) -> list[UIReviewComment]:
        """审查 UI 代码.

        对前端代码进行全面审查，包括:
        - 代码质量和最佳实践
        - 可访问性问题
        - 响应式设计问题
        - 性能问题
        - 浏览器兼容性

        Args:
            code: 要审查的代码

        Returns:
            审查评论列表

        Example:
            >>> comments = await agent.review_ui(component_code)
            >>> for c in comments:
            ...     print(f"[{c.severity}] {c.comment}")
        """
        prompt = f"""作为资深前端工程师，请审查以下代码并提供详细的审查意见:

```
{code}
```

请从以下维度进行审查:
1. 代码质量和最佳实践
2. 可访问性 (a11y) 问题
3. 响应式设计问题
4. 性能问题
5. 浏览器兼容性

请以 JSON 数组格式返回审查意见:
[
  {{
    "line_start": 10,
    "line_end": 15,
    "comment": "问题描述",
    "severity": "error|warning|suggestion|info",
    "ui_category": "layout|styling|interaction|accessibility|performance",
    "suggestion": "改进建议",
    "accessibility_impact": "可访问性影响（如有）",
    "responsive_issue": "响应式问题（如有）",
    "browser_compatibility": ["不兼容的浏览器列表"]
  }}
]"""

        response = await self.llm_client.generate(
            prompt,
            temperature=0.3,
            max_tokens=2000,
        )

        # 解析响应
        comments: list[UIReviewComment] = []
        try:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                raw_comments = json.loads(json_match.group())
                for raw in raw_comments:
                    comments.append(UIReviewComment(
                        reviewer_id=self._id,
                        file_path=None,
                        line_start=raw.get("line_start"),
                        line_end=raw.get("line_end"),
                        comment=raw.get("comment", ""),
                        severity=raw.get("severity", "info"),
                        category="ui",
                        suggestion=raw.get("suggestion"),
                        ui_category=raw.get("ui_category", ""),
                        accessibility_impact=raw.get("accessibility_impact"),
                        responsive_issue=raw.get("responsive_issue"),
                        browser_compatibility=raw.get("browser_compatibility", []),
                    ))
        except json.JSONDecodeError:
            # 如果解析失败，创建一个通用评论
            comments.append(UIReviewComment(
                reviewer_id=self._id,
                comment="无法解析代码审查结果",
                severity="warning",
                ui_category="general",
            ))

        return comments

    async def optimize_performance(
        self,
        metrics: PerformanceMetrics,
    ) -> list[Optimization]:
        """优化前端性能.

        基于性能指标分析，提供具体的优化建议。

        Args:
            metrics: 当前性能指标

        Returns:
            优化建议列表

        Example:
            >>> metrics = PerformanceMetrics(lcp=3500, fid=150, cls=0.2)
            >>> optimizations = await agent.optimize_performance(metrics)
        """
        optimizations: list[Optimization] = []

        # LCP 优化
        if metrics.lcp > 2500:
            optimizations.append(Optimization(
                type="render",
                description="Largest Contentful Paint (LCP) 超过 2.5 秒阈值",
                impact="high",
                effort="medium",
                code_changes=[
                    "使用 <link rel='preload'> 预加载关键资源",
                    "优化首屏图片，使用 WebP 格式",
                    "实现服务端渲染 (SSR) 或静态生成 (SSG)",
                    "使用 <img loading='lazy'> 延迟加载非首屏图片",
                ],
                priority=1,
            ))

        # FID 优化
        if metrics.fid > 100:
            optimizations.append(Optimization(
                type="render",
                description="First Input Delay (FID) 超过 100ms 阈值",
                impact="high",
                effort="medium",
                code_changes=[
                    "将长任务拆分为小任务，使用 requestIdleCallback",
                    "使用 Web Workers 处理复杂计算",
                    "减少 JavaScript 执行时间",
                    "延迟加载非关键 JavaScript",
                ],
                priority=1,
            ))

        # CLS 优化
        if metrics.cls > 0.1:
            optimizations.append(Optimization(
                type="render",
                description="Cumulative Layout Shift (CLS) 超过 0.1 阈值",
                impact="medium",
                effort="low",
                code_changes=[
                    "为图片和视频设置明确的宽高",
                    "避免在已有内容上方插入新内容",
                    "使用 transform 代替改变布局的属性",
                    "预留广告位空间",
                ],
                priority=2,
            ))

        # 包大小优化
        if metrics.bundle_size_kb > 500:
            optimizations.append(Optimization(
                type="bundle",
                description=f"包大小 ({metrics.bundle_size_kb}KB) 较大",
                impact="high",
                effort="medium",
                code_changes=[
                    "实现代码分割 (Code Splitting)",
                    "使用动态导入 import()",
                    "移除未使用的依赖",
                    "使用 Tree Shaking 消除死代码",
                    "压缩和混淆生产代码",
                ],
                priority=1,
            ))

        # 重渲染优化
        if metrics.re_render_count > 10:
            optimizations.append(Optimization(
                type="render",
                description=f"组件重渲染次数过多 ({metrics.re_render_count} 次)",
                impact="medium",
                effort="medium",
                code_changes=[
                    "使用 React.memo 或 useMemo 缓存组件",
                    "使用 useCallback 缓存回调函数",
                    "优化状态管理，避免不必要的状态更新",
                    "使用 shouldComponentUpdate 或 PureComponent",
                ],
                priority=2,
            ))

        # 内存优化
        if metrics.memory_usage_mb > 100:
            optimizations.append(Optimization(
                type="memory",
                description=f"内存使用 ({metrics.memory_usage_mb}MB) 较高",
                impact="medium",
                effort="high",
                code_changes=[
                    "清理未使用的事件监听器",
                    "使用虚拟列表处理长列表",
                    "及时清理定时器和订阅",
                    "避免内存泄漏的闭包模式",
                ],
                priority=3,
            ))

        # 使用 LLM 生成更多建议
        if not optimizations:
            prompt = f"""基于以下性能指标，提供前端优化建议:

LCP: {metrics.lcp}ms
FID: {metrics.fid}ms
CLS: {metrics.cls}
TTFB: {metrics.ttfb}ms
包大小: {metrics.bundle_size_kb}KB
组件渲染时间: {metrics.component_render_time_ms}ms
重渲染次数: {metrics.re_render_count}
内存使用: {metrics.memory_usage_mb}MB

请提供 3-5 条具体的优化建议。"""

            response = await self.llm_client.generate(
                prompt,
                temperature=0.5,
                max_tokens=1000,
            )

            optimizations.append(Optimization(
                type="general",
                description="通用性能优化建议",
                impact="medium",
                effort="medium",
                code_changes=response.strip().split("\n"),
                priority=3,
            ))

        return sorted(optimizations, key=lambda x: x.priority)

    async def generate_styles(self, design_tokens: DesignTokens) -> str:
        """生成 CSS 样式.

        基于设计令牌生成 CSS 变量和基础样式。

        Args:
            design_tokens: 设计令牌

        Returns:
            生成的 CSS 代码

        Example:
            >>> tokens = DesignTokens(
            ...     colors={"primary": "#007bff", "secondary": "#6c757d"},
            ...     spacing={"sm": "0.5rem", "md": "1rem", "lg": "2rem"},
            ... )
            >>> css = await agent.generate_styles(tokens)
        """
        css_parts = [
            "/* ========================================",
            " * Design System - CSS Variables",
            " * Generated by FrontendEngineerAgent",
            " * ======================================== */",
            "",
            ":root {",
        ]

        # 颜色令牌
        if design_tokens.colors:
            css_parts.append("  /* Colors */")
            for name, value in design_tokens.colors.items():
                css_parts.append(f"  --color-{name}: {value};")
            css_parts.append("")

        # 排版令牌
        if design_tokens.typography:
            css_parts.append("  /* Typography */")
            for name, value in design_tokens.typography.items():
                if isinstance(value, dict):
                    for prop, val in value.items():
                        css_parts.append(f"  --typography-{name}-{prop}: {val};")
                else:
                    css_parts.append(f"  --typography-{name}: {value};")
            css_parts.append("")

        # 间距令牌
        if design_tokens.spacing:
            css_parts.append("  /* Spacing */")
            for name, value in design_tokens.spacing.items():
                css_parts.append(f"  --spacing-{name}: {value};")
            css_parts.append("")

        # 断点令牌
        if design_tokens.breakpoints:
            css_parts.append("  /* Breakpoints */")
            for name, value in design_tokens.breakpoints.items():
                css_parts.append(f"  --breakpoint-{name}: {value};")
            css_parts.append("")

        # 阴影令牌
        if design_tokens.shadows:
            css_parts.append("  /* Shadows */")
            for name, value in design_tokens.shadows.items():
                css_parts.append(f"  --shadow-{name}: {value};")
            css_parts.append("")

        # 边框令牌
        if design_tokens.borders:
            css_parts.append("  /* Borders */")
            for name, value in design_tokens.borders.items():
                if isinstance(value, dict):
                    for prop, val in value.items():
                        css_parts.append(f"  --border-{name}-{prop}: {val};")
                else:
                    css_parts.append(f"  --border-{name}: {value};")
            css_parts.append("")

        # 动画令牌
        if design_tokens.animations:
            css_parts.append("  /* Animations */")
            for name, value in design_tokens.animations.items():
                if isinstance(value, dict):
                    for prop, val in value.items():
                        css_parts.append(f"  --animation-{name}-{prop}: {val};")
                else:
                    css_parts.append(f"  --animation-{name}: {value};")

        css_parts.append("}")
        css_parts.append("")

        # 生成媒体查询
        if design_tokens.breakpoints:
            css_parts.append("/* Responsive Breakpoints */")
            for name, value in design_tokens.breakpoints.items():
                css_parts.append(f"""@media (min-width: {value}) {{
  /* {name} breakpoint styles */
}}
""")

        return "\n".join(css_parts)

    # =========================================================================
    # 辅助方法
    # =========================================================================

    def _inject_event_handlers(self, code: str, handlers: str) -> str:
        """将事件处理器注入组件代码.

        Args:
            code: 组件代码
            handlers: 事件处理器代码

        Returns:
            注入后的代码
        """
        if not handlers:
            return code

        # 查找合适的注入位置
        if "return (" in code:
            insert_pos = code.find("return (")
            return code[:insert_pos] + handlers + "\n\n  " + code[insert_pos:]

        return code

    async def _generate_component_styles(self, spec: ComponentSpec) -> str:
        """生成组件样式.

        Args:
            spec: 组件规格

        Returns:
            CSS 代码
        """
        kebab_name = re.sub(r'(?<!^)(?=[A-Z])', '-', spec.name).lower()

        return f""".container {{
  /* 容器样式 */
}}

.{kebab_name} {{
  /* 组件主样式 */
  display: flex;
  flex-direction: column;
}}

/* 响应式样式 */
@media (max-width: 768px) {{
  .{kebab_name} {{
    /* 移动端样式 */
  }}
}}

/* 交互状态 */
.{kebab_name}:hover {{
  /* 悬停状态 */
}}

.{kebab_name}:focus {{
  /* 聚焦状态 */
  outline: 2px solid var(--color-primary, #007bff);
  outline-offset: 2px;
}}

/* 无障碍支持 */
.{kebab_name}[aria-disabled="true"] {{
  opacity: 0.5;
  cursor: not-allowed;
}}
"""

    async def _generate_storybook(self, spec: ComponentSpec) -> str:
        """生成 Storybook 文档.

        Args:
            spec: 组件规格

        Returns:
            Storybook 代码
        """
        return f'''import type {{ Meta, StoryObj }} from '@storybook/react';
import {{ {spec.name} }} from './{spec.name}';

const meta: Meta<typeof {spec.name}> = {{
  title: 'Components/{spec.name}',
  component: {spec.name},
  parameters: {{
    layout: 'centered',
  }},
  tags: ['autodocs'],
}};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {{
  args: {{}},
}};

export const Variant: Story = {{
  args: {{
    // 变体参数
  }},
}};
'''

    async def _generate_component_docs(self, spec: ComponentSpec) -> str:
        """生成组件文档.

        Args:
            spec: 组件规格

        Returns:
            Markdown 文档
        """
        props_table = ""
        if spec.props:
            props_table = """
| Prop | Type | Required | Description |
|------|------|----------|-------------|
"""
            for name, prop in spec.props.items():
                prop_type = prop.get("type", "any") if isinstance(prop, dict) else prop
                required = prop.get("required", True) if isinstance(prop, dict) else True
                desc = prop.get("description", "") if isinstance(prop, dict) else ""
                props_table += f"| {name} | {prop_type} | {required} | {desc} |\n"

        return f"""# {spec.name}

{spec.description}

## Usage

```tsx
import {{ {spec.name} }} from '@/components/{spec.name}';

function Example() {{
  return <{spec.name} />;
}}
```

## Props
{props_table}

## Accessibility

组件遵循 WAI-ARIA 最佳实践。

## Examples

### Basic

```tsx
<{spec.name} />
```
"""

    async def _analyze_accessibility(self, spec: ComponentSpec) -> list[str]:
        """分析组件可访问性.

        Args:
            spec: 组件规格

        Returns:
            可访问性说明列表
        """
        notes = []

        # 基于组件类型提供建议
        if spec.type == ComponentType.ATOMIC:
            notes.append("确保组件有正确的 ARIA 角色")
            notes.append("支持键盘导航 (Tab, Enter, Escape)")

        if "button" in spec.name.lower():
            notes.append("使用 <button> 元素而非 <div>")
            notes.append("添加 aria-label 或可见文本")

        if "input" in spec.name.lower() or "form" in spec.name.lower():
            notes.append("关联 <label> 元素")
            notes.append("提供表单验证错误的 aria-describedby")

        if "modal" in spec.name.lower() or "dialog" in spec.name.lower():
            notes.append("管理焦点 (打开时聚焦，关闭时恢复)")
            notes.append("使用 aria-modal 和 role='dialog'")
            notes.append("按 Escape 键可关闭")

        if "list" in spec.name.lower():
            notes.append("使用语义化列表元素 (<ul>, <ol>)")
            notes.append("支持键盘箭头导航")

        return notes

    async def _analyze_component_performance(self, spec: ComponentSpec) -> list[str]:
        """分析组件性能.

        Args:
            spec: 组件规格

        Returns:
            性能说明列表
        """
        notes = []

        if spec.state:
            notes.append("考虑使用 useMemo 缓存计算结果")
            notes.append("避免在渲染中创建新对象/数组")

        if spec.events:
            notes.append("使用 useCallback 包装事件处理函数")

        if spec.children:
            notes.append("考虑使用 React.memo 优化子组件")
            notes.append("避免不必要的 props 传递")

        if spec.type in [ComponentType.ORGANISM, ComponentType.TEMPLATE, ComponentType.PAGE]:
            notes.append("考虑代码分割和懒加载")
            notes.append("使用虚拟化处理长列表")

        return notes

    async def _generate_frontend_code(
        self,
        task: Task,
        framework: FrontendFramework,
    ) -> str:
        """生成通用前端代码.

        Args:
            task: 任务
            framework: 框架

        Returns:
            生成的代码
        """
        prompt = f"""作为资深前端工程师，请为以下任务生成 {framework.value} 代码:

任务: {task.title}
描述: {task.description}

要求:
1. 使用 TypeScript
2. 遵循最佳实践
3. 包含类型定义
4. 添加必要的注释

请直接输出代码:"""

        response = await self.llm_client.generate(
            prompt,
            temperature=0.5,
            max_tokens=2000,
        )

        # 提取代码块
        code_match = re.search(r'```(?:tsx?|jsx?)?\n([\s\S]*?)```', response)
        if code_match:
            return code_match.group(1)

        return response


# =============================================================================
# 导出
# =============================================================================

__all__ = [
    # 主类
    "FrontendEngineerAgent",
    # 数据类
    "ComponentSpec",
    "ComponentDesign",
    "UIReviewComment",
    "PerformanceMetrics",
    "Optimization",
    "DesignTokens",
    # 枚举
    "FrontendFramework",
    "ComponentType",
    "StyleApproach",
    # 策略
    "FrameworkStrategy",
    "ReactStrategy",
    "VueStrategy",
    "SvelteStrategy",
    "FrameworkStrategyFactory",
]
