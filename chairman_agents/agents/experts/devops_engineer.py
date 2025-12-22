"""DevOps 工程师智能体 - 精通 CI/CD 和基础设施的专家.

本模块实现 DevOps 工程师智能体，提供:
- CI/CD 流水线设计 (GitHub Actions, GitLab CI, Jenkins)
- Docker/Kubernetes 配置生成
- 基础设施即代码 (IaC)
- 监控告警配置
- 部署策略设计 (Blue-Green, Canary, Rolling)

Example:
    >>> agent = DevOpsEngineerAgent(profile, llm_client, memory)
    >>> pipeline = await agent.design_pipeline(project_spec)
    >>> dockerfile = await agent.generate_dockerfile(app_spec)
"""

from __future__ import annotations

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
    ExpertiseLevel,
    ReasoningStep,
    Task,
    TaskResult,
    generate_id,
)

if TYPE_CHECKING:
    from chairman_agents.cognitive.memory import MemorySystem
    from chairman_agents.cognitive.reasoning import LLMClientProtocol, ReasoningEngine


# =============================================================================
# CI 系统枚举
# =============================================================================


class CISystem(Enum):
    """支持的 CI/CD 系统枚举."""

    GITHUB_ACTIONS = "github_actions"
    """GitHub Actions - GitHub 原生 CI/CD"""

    GITLAB_CI = "gitlab_ci"
    """GitLab CI/CD - GitLab 集成流水线"""

    JENKINS = "jenkins"
    """Jenkins - 开源自动化服务器"""

    AZURE_DEVOPS = "azure_devops"
    """Azure DevOps Pipelines"""

    CIRCLECI = "circleci"
    """CircleCI - 云原生 CI/CD"""


class DeploymentStrategy(Enum):
    """部署策略枚举."""

    ROLLING = "rolling"
    """滚动更新 - 逐步替换旧实例"""

    BLUE_GREEN = "blue_green"
    """蓝绿部署 - 双环境切换"""

    CANARY = "canary"
    """金丝雀发布 - 渐进式流量迁移"""

    RECREATE = "recreate"
    """重建部署 - 停机后重新创建"""

    A_B_TESTING = "a_b_testing"
    """A/B 测试 - 基于特征的流量分割"""


class K8sResourceType(Enum):
    """Kubernetes 资源类型枚举."""

    DEPLOYMENT = "Deployment"
    SERVICE = "Service"
    CONFIGMAP = "ConfigMap"
    SECRET = "Secret"
    INGRESS = "Ingress"
    HPA = "HorizontalPodAutoscaler"
    PDB = "PodDisruptionBudget"
    NETWORK_POLICY = "NetworkPolicy"
    SERVICE_ACCOUNT = "ServiceAccount"
    ROLE = "Role"
    ROLE_BINDING = "RoleBinding"


class MonitoringType(Enum):
    """监控类型枚举."""

    PROMETHEUS = "prometheus"
    """Prometheus 指标监控"""

    GRAFANA = "grafana"
    """Grafana 可视化"""

    ALERTMANAGER = "alertmanager"
    """AlertManager 告警"""

    JAEGER = "jaeger"
    """Jaeger 分布式追踪"""

    ELK = "elk"
    """ELK 日志栈"""


# =============================================================================
# 规格数据类
# =============================================================================


@dataclass
class ProjectSpec:
    """项目规格定义.

    Attributes:
        name: 项目名称
        language: 主要编程语言
        framework: 使用的框架
        build_tool: 构建工具 (npm, pip, cargo, etc.)
        test_command: 测试命令
        build_command: 构建命令
        environments: 环境列表 (dev, staging, prod)
    """

    name: str = ""
    language: str = "python"
    framework: str = ""
    build_tool: str = "pip"
    test_command: str = "pytest"
    build_command: str = "pip install -e ."
    lint_command: str = "ruff check ."
    environments: list[str] = field(default_factory=lambda: ["dev", "staging", "prod"])
    source_dir: str = "src"
    test_dir: str = "tests"
    docker_registry: str = ""
    artifact_registry: str = ""


@dataclass
class ApplicationSpec:
    """应用程序规格定义.

    Attributes:
        name: 应用名称
        language: 编程语言
        version: Python/Node 版本
        port: 服务端口
        dependencies: 依赖文件路径
        entrypoint: 入口命令
        health_check: 健康检查路径
    """

    name: str = ""
    language: str = "python"
    version: str = "3.12"
    port: int = 8000
    dependencies: str = "requirements.txt"
    entrypoint: str = "python -m uvicorn main:app --host 0.0.0.0"
    health_check: str = "/health"
    env_vars: dict[str, str] = field(default_factory=dict)
    build_args: dict[str, str] = field(default_factory=dict)
    multi_stage: bool = True
    base_image: str = ""
    working_dir: str = "/app"


@dataclass
class DeploymentSpec:
    """部署规格定义.

    Attributes:
        name: 部署名称
        namespace: Kubernetes 命名空间
        replicas: 副本数
        image: 容器镜像
        resources: 资源限制
        environment: 目标环境
    """

    name: str = ""
    namespace: str = "default"
    replicas: int = 3
    image: str = ""
    tag: str = "latest"
    resources: dict[str, Any] = field(
        default_factory=lambda: {
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "500m", "memory": "512Mi"},
        }
    )
    environment: str = "production"
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)
    env_vars: dict[str, str] = field(default_factory=dict)
    secrets: list[str] = field(default_factory=list)
    config_maps: list[str] = field(default_factory=list)
    ports: list[dict[str, Any]] = field(
        default_factory=lambda: [{"name": "http", "port": 8000, "protocol": "TCP"}]
    )
    health_check: dict[str, Any] = field(
        default_factory=lambda: {
            "path": "/health",
            "port": 8000,
            "initial_delay": 30,
            "period": 10,
        }
    )
    autoscaling: dict[str, Any] | None = None


@dataclass
class ReleaseSpec:
    """发布规格定义.

    Attributes:
        version: 发布版本
        strategy: 部署策略
        rollback_on_failure: 失败时是否回滚
        traffic_percentage: 初始流量百分比 (for canary)
        verification_period: 验证周期 (秒)
    """

    version: str = "1.0.0"
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    rollback_on_failure: bool = True
    traffic_percentage: int = 10
    verification_period: int = 300
    approval_required: bool = True
    notification_channels: list[str] = field(default_factory=list)
    pre_deploy_hooks: list[str] = field(default_factory=list)
    post_deploy_hooks: list[str] = field(default_factory=list)
    health_check_timeout: int = 120
    max_surge: str = "25%"
    max_unavailable: str = "25%"


@dataclass
class Service:
    """服务定义.

    Attributes:
        name: 服务名称
        type: 服务类型 (api, worker, scheduler)
        metrics_path: 指标暴露路径
        log_format: 日志格式
    """

    name: str = ""
    type: str = "api"
    port: int = 8000
    metrics_path: str = "/metrics"
    log_format: str = "json"
    sla_target: float = 99.9
    latency_threshold_ms: int = 200
    error_rate_threshold: float = 0.01


# =============================================================================
# 输出数据类
# =============================================================================


@dataclass
class PipelineStage:
    """CI/CD 流水线阶段.

    Attributes:
        name: 阶段名称
        jobs: 作业列表
        depends_on: 依赖的阶段
        condition: 执行条件
    """

    id: str = field(default_factory=lambda: generate_id("stage"))
    name: str = ""
    jobs: list[dict[str, Any]] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    environment: str | None = None
    timeout_minutes: int = 30
    retry_count: int = 0
    allow_failure: bool = False
    artifacts: list[str] = field(default_factory=list)
    cache: dict[str, Any] = field(default_factory=dict)

    def to_github_actions(self) -> dict[str, Any]:
        """转换为 GitHub Actions 格式."""
        job: dict[str, Any] = {
            "name": self.name,
            "runs-on": "ubuntu-latest",
            "steps": self.jobs,
        }
        if self.depends_on:
            job["needs"] = self.depends_on
        if self.condition:
            job["if"] = self.condition
        if self.timeout_minutes:
            job["timeout-minutes"] = self.timeout_minutes
        if self.environment:
            job["environment"] = self.environment
        return job

    def to_gitlab_ci(self) -> dict[str, Any]:
        """转换为 GitLab CI 格式."""
        stage: dict[str, Any] = {
            "stage": self.name,
            "script": [j.get("run", "") for j in self.jobs if "run" in j],
        }
        if self.depends_on:
            stage["needs"] = self.depends_on
        if self.condition:
            stage["rules"] = [{"if": self.condition}]
        if self.allow_failure:
            stage["allow_failure"] = True
        if self.artifacts:
            stage["artifacts"] = {"paths": self.artifacts}
        return stage


@dataclass
class CIPipeline:
    """CI/CD 流水线配置.

    Attributes:
        name: 流水线名称
        ci_system: CI 系统类型
        stages: 阶段列表
        triggers: 触发条件
        variables: 环境变量
    """

    id: str = field(default_factory=lambda: generate_id("pipeline"))
    name: str = ""
    ci_system: CISystem = CISystem.GITHUB_ACTIONS
    stages: list[PipelineStage] = field(default_factory=list)
    triggers: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    secrets: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_yaml(self) -> str:
        """将流水线转换为 YAML 配置."""
        if self.ci_system == CISystem.GITHUB_ACTIONS:
            return self._to_github_actions_yaml()
        elif self.ci_system == CISystem.GITLAB_CI:
            return self._to_gitlab_ci_yaml()
        elif self.ci_system == CISystem.JENKINS:
            return self._to_jenkinsfile()
        return ""

    def _to_github_actions_yaml(self) -> str:
        """生成 GitHub Actions 工作流 YAML."""
        lines = [
            f"name: {self.name}",
            "",
            "on:",
        ]

        # 触发器
        if self.triggers.get("push"):
            lines.append("  push:")
            if branches := self.triggers["push"].get("branches"):
                lines.append(f"    branches: {branches}")
        if self.triggers.get("pull_request"):
            lines.append("  pull_request:")
            if branches := self.triggers["pull_request"].get("branches"):
                lines.append(f"    branches: {branches}")

        # 环境变量
        if self.variables:
            lines.extend(["", "env:"])
            for key, value in self.variables.items():
                lines.append(f"  {key}: {value}")

        # 作业
        lines.extend(["", "jobs:"])
        for stage in self.stages:
            job = stage.to_github_actions()
            lines.append(f"  {stage.name.lower().replace(' ', '-')}:")
            lines.append(f"    name: {job['name']}")
            lines.append(f"    runs-on: {job['runs-on']}")
            if "needs" in job:
                lines.append(f"    needs: {job['needs']}")
            if "if" in job:
                lines.append(f"    if: {job['if']}")
            lines.append("    steps:")
            for step in job.get("steps", []):
                if "uses" in step:
                    lines.append(f"      - uses: {step['uses']}")
                if "run" in step:
                    lines.append(f"      - run: {step['run']}")

        return "\n".join(lines)

    def _to_gitlab_ci_yaml(self) -> str:
        """生成 GitLab CI 配置 YAML."""
        lines = []

        # 阶段定义
        stage_names = [s.name for s in self.stages]
        lines.append(f"stages: {stage_names}")
        lines.append("")

        # 变量
        if self.variables:
            lines.append("variables:")
            for key, value in self.variables.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        # 作业
        for stage in self.stages:
            gitlab_stage = stage.to_gitlab_ci()
            lines.append(f"{stage.name.lower().replace(' ', '_')}:")
            for key, value in gitlab_stage.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        return "\n".join(lines)

    def _to_jenkinsfile(self) -> str:
        """生成 Jenkinsfile (Declarative Pipeline)."""
        lines = [
            "pipeline {",
            "    agent any",
            "",
        ]

        # 环境变量
        if self.variables:
            lines.append("    environment {")
            for key, value in self.variables.items():
                lines.append(f"        {key} = '{value}'")
            lines.append("    }")
            lines.append("")

        # 阶段
        lines.append("    stages {")
        for stage in self.stages:
            lines.append(f"        stage('{stage.name}') {{")
            lines.append("            steps {")
            for job in stage.jobs:
                if "run" in job:
                    lines.append(f"                sh '{job['run']}'")
            lines.append("            }")
            lines.append("        }")
        lines.append("    }")

        # 后置操作
        lines.extend([
            "",
            "    post {",
            "        always {",
            "            cleanWs()",
            "        }",
            "        failure {",
            "            echo 'Pipeline failed!'",
            "        }",
            "    }",
            "}",
        ])

        return "\n".join(lines)


@dataclass
class K8sManifest:
    """Kubernetes 清单配置.

    Attributes:
        name: 资源名称
        resource_type: 资源类型
        content: YAML 内容
        namespace: 命名空间
    """

    id: str = field(default_factory=lambda: generate_id("k8s"))
    name: str = ""
    resource_type: K8sResourceType = K8sResourceType.DEPLOYMENT
    content: dict[str, Any] = field(default_factory=dict)
    namespace: str = "default"
    labels: dict[str, str] = field(default_factory=dict)
    annotations: dict[str, str] = field(default_factory=dict)

    def to_yaml(self) -> str:
        """将清单转换为 YAML 格式."""
        import yaml

        return yaml.dump(self.content, default_flow_style=False, allow_unicode=True)


@dataclass
class MonitoringConfig:
    """监控配置.

    Attributes:
        services: 被监控的服务列表
        metrics: 指标配置
        alerts: 告警规则
        dashboards: 仪表板配置
    """

    id: str = field(default_factory=lambda: generate_id("mon"))
    services: list[str] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    dashboards: list[dict[str, Any]] = field(default_factory=list)
    scrape_interval: str = "15s"
    evaluation_interval: str = "15s"
    retention_days: int = 15

    def to_prometheus_config(self) -> str:
        """生成 Prometheus 配置."""
        lines = [
            "global:",
            f"  scrape_interval: {self.scrape_interval}",
            f"  evaluation_interval: {self.evaluation_interval}",
            "",
            "scrape_configs:",
        ]

        for service in self.services:
            lines.extend([
                f"  - job_name: '{service}'",
                "    static_configs:",
                f"      - targets: ['{service}:8000']",
            ])

        return "\n".join(lines)

    def to_alertmanager_rules(self) -> str:
        """生成 AlertManager 规则."""
        lines = ["groups:", "  - name: service_alerts", "    rules:"]

        for alert in self.alerts:
            lines.extend([
                f"      - alert: {alert.get('name', 'UnnamedAlert')}",
                f"        expr: {alert.get('expr', '')}",
                f"        for: {alert.get('for', '5m')}",
                "        labels:",
                f"          severity: {alert.get('severity', 'warning')}",
                "        annotations:",
                f"          summary: {alert.get('summary', '')}",
            ])

        return "\n".join(lines)


@dataclass
class DeploymentPlan:
    """部署计划.

    Attributes:
        release: 发布规格
        strategy: 部署策略
        steps: 部署步骤
        rollback_plan: 回滚计划
        verification: 验证步骤
    """

    id: str = field(default_factory=lambda: generate_id("deploy"))
    release: ReleaseSpec | None = None
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    steps: list[dict[str, Any]] = field(default_factory=list)
    rollback_plan: list[dict[str, Any]] = field(default_factory=list)
    verification: list[dict[str, Any]] = field(default_factory=list)
    estimated_duration_minutes: int = 30
    risk_level: str = "medium"
    approval_gates: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def generate_runbook(self) -> str:
        """生成部署运行手册."""
        lines = [
            f"# Deployment Runbook - {self.release.version if self.release else 'N/A'}",
            "",
            f"## Strategy: {self.strategy.value}",
            f"## Estimated Duration: {self.estimated_duration_minutes} minutes",
            f"## Risk Level: {self.risk_level}",
            "",
            "## Pre-deployment Checklist",
            "- [ ] All tests passing",
            "- [ ] Configuration validated",
            "- [ ] Rollback plan reviewed",
            "- [ ] Monitoring alerts configured",
            "",
            "## Deployment Steps",
        ]

        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step.get('description', step.get('name', 'Step'))}")
            if cmd := step.get("command"):
                lines.append(f"   ```bash\n   {cmd}\n   ```")

        lines.extend([
            "",
            "## Verification Steps",
        ])

        for i, check in enumerate(self.verification, 1):
            lines.append(f"{i}. {check.get('description', check.get('name', 'Check'))}")

        lines.extend([
            "",
            "## Rollback Plan",
        ])

        for i, step in enumerate(self.rollback_plan, 1):
            lines.append(f"{i}. {step.get('description', step.get('name', 'Rollback'))}")

        return "\n".join(lines)


# =============================================================================
# 基类定义
# =============================================================================


class BaseExpertAgent(ABC):
    """专家智能体基类.

    所有专家智能体的抽象基类，定义通用接口和行为。

    Attributes:
        profile: 智能体配置文件
        reasoning: 推理引擎实例
        memory: 记忆系统实例
        role: 智能体角色
    """

    role: AgentRole = AgentRole.BACKEND_ENGINEER

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClientProtocol,
        memory: MemorySystem | None = None,
    ) -> None:
        """初始化专家智能体.

        Args:
            profile: 智能体配置文件
            llm_client: LLM 客户端实例
            memory: 记忆系统实例 (可选)
        """
        self.profile = profile
        self.llm_client = llm_client
        self.memory = memory
        self._reasoning_engine: ReasoningEngine | None = None

    @property
    def reasoning(self) -> ReasoningEngine:
        """获取推理引擎实例 (延迟初始化)."""
        if self._reasoning_engine is None:
            from chairman_agents.cognitive.reasoning import ReasoningEngine

            self._reasoning_engine = ReasoningEngine(self.llm_client)
        return self._reasoning_engine

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """执行任务.

        Args:
            task: 要执行的任务

        Returns:
            任务执行结果
        """
        ...

    async def _generate_with_reasoning(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """使用推理引擎生成响应.

        Args:
            prompt: 输入提示
            context: 上下文信息

        Returns:
            生成的响应
        """
        result = await self.reasoning.chain_of_thought(prompt, context or {})
        return result.conclusion


# =============================================================================
# DevOps 工程师智能体
# =============================================================================


class DevOpsEngineerAgent(BaseExpertAgent):
    """DevOps 工程师智能体.

    精通 CI/CD 和基础设施的 DevOps 专家，具备以下核心能力:
    - CI/CD 流水线设计
    - Docker/Kubernetes 配置
    - 基础设施即代码 (IaC)
    - 监控告警配置
    - 部署策略设计

    Example:
        >>> agent = DevOpsEngineerAgent(profile, llm_client, memory)
        >>> result = await agent.execute(task)
        >>> pipeline = await agent.design_pipeline(project_spec)
    """

    role = AgentRole.DEVOPS_ENGINEER

    def __init__(
        self,
        profile: AgentProfile,
        llm_client: LLMClientProtocol,
        memory: MemorySystem | None = None,
    ) -> None:
        """初始化 DevOps 工程师智能体."""
        super().__init__(profile, llm_client, memory)

        # 确保配置正确的能力
        self._required_capabilities = [
            AgentCapability.CI_CD_PIPELINE,
            AgentCapability.CONTAINERIZATION,
            AgentCapability.ORCHESTRATION,
            AgentCapability.INFRASTRUCTURE_AS_CODE,
            AgentCapability.MONITORING,
        ]

    async def execute(self, task: Task) -> TaskResult:
        """执行 DevOps 相关任务.

        根据任务类型分派到对应的专业方法执行。

        Args:
            task: 要执行的任务

        Returns:
            任务执行结果，包含生成的配置文件等产物
        """
        reasoning_trace: list[ReasoningStep] = []
        artifacts: list[Artifact] = []
        start_time = datetime.now()

        try:
            # 分析任务类型
            task_type = task.context.get("devops_task_type", "pipeline")

            reasoning_trace.append(
                ReasoningStep(
                    step_number=1,
                    thought=f"分析 DevOps 任务类型: {task_type}",
                    action="task_analysis",
                    confidence=0.9,
                )
            )

            if task_type == "pipeline":
                project_spec = self._extract_project_spec(task)
                pipeline = await self.design_pipeline(project_spec)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.CI_CONFIG,
                        name=f"{pipeline.name}.yml",
                        content=pipeline.to_yaml(),
                        language="yaml",
                    )
                )

            elif task_type == "dockerfile":
                app_spec = self._extract_app_spec(task)
                dockerfile = await self.generate_dockerfile(app_spec)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.DOCKERFILE,
                        name="Dockerfile",
                        content=dockerfile,
                    )
                )

            elif task_type == "kubernetes":
                deployment_spec = self._extract_deployment_spec(task)
                manifests = await self.create_k8s_manifests(deployment_spec)
                for manifest in manifests:
                    artifacts.append(
                        Artifact(
                            type=ArtifactType.K8S_MANIFEST,
                            name=f"{manifest.name}.yaml",
                            content=manifest.to_yaml(),
                            language="yaml",
                        )
                    )

            elif task_type == "monitoring":
                services = self._extract_services(task)
                monitoring = await self.design_monitoring(services)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.CONFIG_FILE,
                        name="prometheus.yml",
                        content=monitoring.to_prometheus_config(),
                        language="yaml",
                    )
                )
                artifacts.append(
                    Artifact(
                        type=ArtifactType.CONFIG_FILE,
                        name="alerts.yml",
                        content=monitoring.to_alertmanager_rules(),
                        language="yaml",
                    )
                )

            elif task_type == "deployment":
                release_spec = self._extract_release_spec(task)
                plan = await self.plan_deployment(release_spec)
                artifacts.append(
                    Artifact(
                        type=ArtifactType.RUNBOOK,
                        name="deployment_runbook.md",
                        content=plan.generate_runbook(),
                        language="markdown",
                    )
                )

            execution_time = (datetime.now() - start_time).total_seconds()

            return TaskResult(
                task_id=task.id,
                success=True,
                artifacts=artifacts,
                reasoning_trace=reasoning_trace,
                confidence_score=0.85,
                quality_score=0.9,
                execution_time_seconds=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return TaskResult(
                task_id=task.id,
                success=False,
                artifacts=[],
                reasoning_trace=reasoning_trace,
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_seconds=execution_time,
            )

    async def design_pipeline(
        self,
        project: ProjectSpec,
        ci_system: CISystem = CISystem.GITHUB_ACTIONS,
    ) -> CIPipeline:
        """设计 CI/CD 流水线.

        根据项目规格生成完整的 CI/CD 流水线配置。

        Args:
            project: 项目规格
            ci_system: 目标 CI 系统

        Returns:
            CI/CD 流水线配置
        """
        stages: list[PipelineStage] = []

        # 代码检出阶段
        checkout_stage = PipelineStage(
            name="Checkout",
            jobs=[{"uses": "actions/checkout@v4"}],
        )
        stages.append(checkout_stage)

        # 环境设置阶段
        setup_jobs = []
        if project.language == "python":
            setup_jobs.extend([
                {"uses": "actions/setup-python@v5", "with": {"python-version": "3.12"}},
                {"run": f"pip install -r {project.source_dir}/requirements.txt"},
            ])
        elif project.language == "node":
            setup_jobs.extend([
                {"uses": "actions/setup-node@v4", "with": {"node-version": "20"}},
                {"run": "npm ci"},
            ])

        setup_stage = PipelineStage(
            name="Setup",
            jobs=setup_jobs,
            depends_on=["checkout"],
        )
        stages.append(setup_stage)

        # 代码检查阶段
        lint_stage = PipelineStage(
            name="Lint",
            jobs=[{"run": project.lint_command}],
            depends_on=["setup"],
        )
        stages.append(lint_stage)

        # 测试阶段
        test_stage = PipelineStage(
            name="Test",
            jobs=[
                {"run": project.test_command},
                {"run": f"{project.test_command} --cov --cov-report=xml"},
            ],
            depends_on=["setup"],
            artifacts=["coverage.xml"],
        )
        stages.append(test_stage)

        # 构建阶段
        build_stage = PipelineStage(
            name="Build",
            jobs=[{"run": project.build_command}],
            depends_on=["lint", "test"],
        )
        stages.append(build_stage)

        # 为每个环境创建部署阶段
        previous_deploy = "build"
        for env in project.environments:
            deploy_stage = PipelineStage(
                name=f"Deploy-{env.capitalize()}",
                jobs=[{"run": f"echo 'Deploying to {env}'"}],
                depends_on=[previous_deploy],
                environment=env,
                condition=f"github.ref == 'refs/heads/{env}'" if env != "prod" else "github.ref == 'refs/heads/main'",
            )
            stages.append(deploy_stage)
            previous_deploy = f"deploy-{env}"

        return CIPipeline(
            name=f"{project.name}-ci",
            ci_system=ci_system,
            stages=stages,
            triggers={
                "push": {"branches": ["main", "develop"]},
                "pull_request": {"branches": ["main"]},
            },
            variables={
                "PYTHON_VERSION": "3.12" if project.language == "python" else "",
            },
        )

    async def generate_dockerfile(self, app: ApplicationSpec) -> str:
        """生成 Dockerfile.

        根据应用规格生成优化的 Dockerfile。

        Args:
            app: 应用程序规格

        Returns:
            Dockerfile 内容
        """
        if app.language == "python":
            return self._generate_python_dockerfile(app)
        elif app.language in ("node", "javascript", "typescript"):
            return self._generate_node_dockerfile(app)
        else:
            return self._generate_generic_dockerfile(app)

    def _generate_python_dockerfile(self, app: ApplicationSpec) -> str:
        """生成 Python 应用的 Dockerfile."""
        base_image = app.base_image or f"python:{app.version}-slim"

        if app.multi_stage:
            return f"""# Stage 1: Builder
FROM {base_image} AS builder

WORKDIR {app.working_dir}

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY {app.dependencies} .
RUN pip install --no-cache-dir --user -r {app.dependencies}

# Stage 2: Runtime
FROM {base_image}

WORKDIR {app.working_dir}

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY . .

# Set ownership
RUN chown -R appuser:appuser {app.working_dir}

USER appuser

EXPOSE {app.port}

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:{app.port}{app.health_check} || exit 1

CMD [{", ".join(f'"{arg}"' for arg in app.entrypoint.split())}]
"""
        else:
            return f"""FROM {base_image}

WORKDIR {app.working_dir}

COPY {app.dependencies} .
RUN pip install --no-cache-dir -r {app.dependencies}

COPY . .

EXPOSE {app.port}

CMD [{", ".join(f'"{arg}"' for arg in app.entrypoint.split())}]
"""

    def _generate_node_dockerfile(self, app: ApplicationSpec) -> str:
        """生成 Node.js 应用的 Dockerfile."""
        base_image = app.base_image or f"node:{app.version}-alpine"

        return f"""# Stage 1: Builder
FROM {base_image} AS builder

WORKDIR {app.working_dir}

COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Runtime
FROM {base_image}

WORKDIR {app.working_dir}

RUN addgroup -g 1001 -S nodejs && adduser -S nodejs -u 1001

COPY --from=builder --chown=nodejs:nodejs {app.working_dir}/node_modules ./node_modules
COPY --chown=nodejs:nodejs . .

USER nodejs

EXPOSE {app.port}

CMD ["node", "dist/main.js"]
"""

    def _generate_generic_dockerfile(self, app: ApplicationSpec) -> str:
        """生成通用 Dockerfile."""
        return f"""FROM ubuntu:22.04

WORKDIR {app.working_dir}

COPY . .

EXPOSE {app.port}

CMD {app.entrypoint.split()}
"""

    async def create_k8s_manifests(
        self,
        deployment: DeploymentSpec,
    ) -> list[K8sManifest]:
        """创建 Kubernetes 清单配置.

        根据部署规格生成完整的 K8s 资源清单。

        Args:
            deployment: 部署规格

        Returns:
            K8s 清单列表
        """
        manifests: list[K8sManifest] = []

        # 创建 Deployment
        deployment_manifest = self._create_deployment_manifest(deployment)
        manifests.append(deployment_manifest)

        # 创建 Service
        service_manifest = self._create_service_manifest(deployment)
        manifests.append(service_manifest)

        # 创建 HPA (如果配置了自动扩缩)
        if deployment.autoscaling:
            hpa_manifest = self._create_hpa_manifest(deployment)
            manifests.append(hpa_manifest)

        # 创建 ConfigMap (如果有配置)
        if deployment.config_maps:
            for cm_name in deployment.config_maps:
                cm_manifest = self._create_configmap_manifest(deployment, cm_name)
                manifests.append(cm_manifest)

        return manifests

    def _create_deployment_manifest(self, spec: DeploymentSpec) -> K8sManifest:
        """创建 Deployment 清单."""
        content = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": spec.name,
                "namespace": spec.namespace,
                "labels": {"app": spec.name, **spec.labels},
                "annotations": spec.annotations,
            },
            "spec": {
                "replicas": spec.replicas,
                "selector": {"matchLabels": {"app": spec.name}},
                "template": {
                    "metadata": {"labels": {"app": spec.name}},
                    "spec": {
                        "containers": [
                            {
                                "name": spec.name,
                                "image": f"{spec.image}:{spec.tag}",
                                "ports": spec.ports,
                                "resources": spec.resources,
                                "livenessProbe": {
                                    "httpGet": {
                                        "path": spec.health_check["path"],
                                        "port": spec.health_check["port"],
                                    },
                                    "initialDelaySeconds": spec.health_check["initial_delay"],
                                    "periodSeconds": spec.health_check["period"],
                                },
                                "readinessProbe": {
                                    "httpGet": {
                                        "path": spec.health_check["path"],
                                        "port": spec.health_check["port"],
                                    },
                                    "initialDelaySeconds": 5,
                                    "periodSeconds": 5,
                                },
                            }
                        ]
                    },
                },
            },
        }

        return K8sManifest(
            name=f"{spec.name}-deployment",
            resource_type=K8sResourceType.DEPLOYMENT,
            content=content,
            namespace=spec.namespace,
        )

    def _create_service_manifest(self, spec: DeploymentSpec) -> K8sManifest:
        """创建 Service 清单."""
        content = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": spec.name,
                "namespace": spec.namespace,
            },
            "spec": {
                "selector": {"app": spec.name},
                "ports": [
                    {
                        "name": p["name"],
                        "port": p["port"],
                        "targetPort": p["port"],
                        "protocol": p.get("protocol", "TCP"),
                    }
                    for p in spec.ports
                ],
                "type": "ClusterIP",
            },
        }

        return K8sManifest(
            name=f"{spec.name}-service",
            resource_type=K8sResourceType.SERVICE,
            content=content,
            namespace=spec.namespace,
        )

    def _create_hpa_manifest(self, spec: DeploymentSpec) -> K8sManifest:
        """创建 HorizontalPodAutoscaler 清单."""
        autoscaling = spec.autoscaling or {}
        content = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{spec.name}-hpa",
                "namespace": spec.namespace,
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": spec.name,
                },
                "minReplicas": autoscaling.get("min_replicas", 2),
                "maxReplicas": autoscaling.get("max_replicas", 10),
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": autoscaling.get("target_cpu", 70),
                            },
                        },
                    }
                ],
            },
        }

        return K8sManifest(
            name=f"{spec.name}-hpa",
            resource_type=K8sResourceType.HPA,
            content=content,
            namespace=spec.namespace,
        )

    def _create_configmap_manifest(
        self,
        spec: DeploymentSpec,
        name: str,
    ) -> K8sManifest:
        """创建 ConfigMap 清单."""
        content = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": name,
                "namespace": spec.namespace,
            },
            "data": {},
        }

        return K8sManifest(
            name=name,
            resource_type=K8sResourceType.CONFIGMAP,
            content=content,
            namespace=spec.namespace,
        )

    async def design_monitoring(self, services: list[Service]) -> MonitoringConfig:
        """设计监控配置.

        为服务列表生成完整的监控和告警配置。

        Args:
            services: 服务列表

        Returns:
            监控配置
        """
        metrics: list[dict[str, Any]] = []
        alerts: list[dict[str, Any]] = []

        for service in services:
            # 添加标准指标
            metrics.extend([
                {
                    "name": f"{service.name}_request_total",
                    "type": "counter",
                    "description": f"Total requests to {service.name}",
                },
                {
                    "name": f"{service.name}_request_duration_seconds",
                    "type": "histogram",
                    "description": f"Request duration for {service.name}",
                },
                {
                    "name": f"{service.name}_error_total",
                    "type": "counter",
                    "description": f"Total errors in {service.name}",
                },
            ])

            # 添加告警规则
            alerts.extend([
                {
                    "name": f"{service.name}HighErrorRate",
                    "expr": f"rate({service.name}_error_total[5m]) / rate({service.name}_request_total[5m]) > {service.error_rate_threshold}",
                    "for": "5m",
                    "severity": "critical",
                    "summary": f"High error rate detected in {service.name}",
                },
                {
                    "name": f"{service.name}HighLatency",
                    "expr": f"histogram_quantile(0.95, rate({service.name}_request_duration_seconds_bucket[5m])) > {service.latency_threshold_ms / 1000}",
                    "for": "5m",
                    "severity": "warning",
                    "summary": f"High latency detected in {service.name}",
                },
                {
                    "name": f"{service.name}Down",
                    "expr": f"up{{job=\"{service.name}\"}} == 0",
                    "for": "1m",
                    "severity": "critical",
                    "summary": f"Service {service.name} is down",
                },
            ])

        return MonitoringConfig(
            services=[s.name for s in services],
            metrics=metrics,
            alerts=alerts,
            dashboards=[
                {
                    "name": "Service Overview",
                    "panels": [
                        {"title": "Request Rate", "type": "graph"},
                        {"title": "Error Rate", "type": "graph"},
                        {"title": "Latency P95", "type": "graph"},
                    ],
                }
            ],
        )

    async def plan_deployment(self, release: ReleaseSpec) -> DeploymentPlan:
        """规划部署策略.

        根据发布规格生成详细的部署计划。

        Args:
            release: 发布规格

        Returns:
            部署计划
        """
        steps: list[dict[str, Any]] = []
        verification: list[dict[str, Any]] = []
        rollback_plan: list[dict[str, Any]] = []

        if release.strategy == DeploymentStrategy.ROLLING:
            steps = self._generate_rolling_steps(release)
        elif release.strategy == DeploymentStrategy.BLUE_GREEN:
            steps = self._generate_blue_green_steps(release)
        elif release.strategy == DeploymentStrategy.CANARY:
            steps = self._generate_canary_steps(release)
        else:
            steps = self._generate_recreate_steps(release)

        # 标准验证步骤
        verification = [
            {"name": "health_check", "description": "验证所有实例健康检查通过"},
            {"name": "smoke_test", "description": "运行冒烟测试套件"},
            {"name": "metrics_check", "description": "验证关键指标正常"},
            {"name": "log_check", "description": "检查是否有异常日志"},
        ]

        # 回滚计划
        rollback_plan = [
            {"name": "identify_issue", "description": "识别问题根源"},
            {"name": "notify_team", "description": "通知相关团队"},
            {"name": "rollback_deployment", "description": "执行 kubectl rollout undo"},
            {"name": "verify_rollback", "description": "验证回滚成功"},
            {"name": "post_mortem", "description": "安排事后分析会议"},
        ]

        return DeploymentPlan(
            release=release,
            strategy=release.strategy,
            steps=steps,
            rollback_plan=rollback_plan,
            verification=verification,
            estimated_duration_minutes=self._estimate_duration(release),
            risk_level=self._assess_risk(release),
            approval_gates=["qa_approval", "pm_approval"] if release.approval_required else [],
        )

    def _generate_rolling_steps(self, release: ReleaseSpec) -> list[dict[str, Any]]:
        """生成滚动更新步骤."""
        return [
            {"name": "pre_deploy", "description": "执行预部署钩子", "command": "; ".join(release.pre_deploy_hooks) or "echo 'No pre-deploy hooks'"},
            {"name": "update_image", "description": "更新容器镜像", "command": f"kubectl set image deployment/app app=app:{release.version}"},
            {"name": "wait_rollout", "description": "等待滚动更新完成", "command": "kubectl rollout status deployment/app"},
            {"name": "post_deploy", "description": "执行后部署钩子", "command": "; ".join(release.post_deploy_hooks) or "echo 'No post-deploy hooks'"},
        ]

    def _generate_blue_green_steps(self, release: ReleaseSpec) -> list[dict[str, Any]]:
        """生成蓝绿部署步骤."""
        return [
            {"name": "deploy_green", "description": "部署新版本到 Green 环境", "command": f"kubectl apply -f green-deployment-{release.version}.yaml"},
            {"name": "wait_green_ready", "description": "等待 Green 环境就绪", "command": "kubectl rollout status deployment/app-green"},
            {"name": "run_tests", "description": "在 Green 环境运行测试", "command": "pytest tests/e2e --env=green"},
            {"name": "switch_traffic", "description": "切换流量到 Green 环境", "command": "kubectl patch service app -p '{\"spec\":{\"selector\":{\"version\":\"green\"}}}'"},
            {"name": "cleanup_blue", "description": "清理 Blue 环境", "command": "kubectl delete deployment app-blue"},
        ]

    def _generate_canary_steps(self, release: ReleaseSpec) -> list[dict[str, Any]]:
        """生成金丝雀部署步骤."""
        return [
            {"name": "deploy_canary", "description": f"部署金丝雀版本 ({release.traffic_percentage}% 流量)", "command": f"kubectl apply -f canary-{release.version}.yaml"},
            {"name": "wait_canary", "description": "等待金丝雀就绪", "command": "kubectl rollout status deployment/app-canary"},
            {"name": "monitor_canary", "description": f"监控金丝雀 {release.verification_period}s", "command": f"sleep {release.verification_period}"},
            {"name": "increase_traffic", "description": "逐步增加流量", "command": "istioctl configure --canary-weight 50"},
            {"name": "full_rollout", "description": "完成全量发布", "command": "kubectl apply -f production.yaml"},
            {"name": "cleanup_canary", "description": "清理金丝雀部署", "command": "kubectl delete deployment app-canary"},
        ]

    def _generate_recreate_steps(self, release: ReleaseSpec) -> list[dict[str, Any]]:
        """生成重建部署步骤."""
        return [
            {"name": "scale_down", "description": "缩容现有部署", "command": "kubectl scale deployment/app --replicas=0"},
            {"name": "wait_termination", "description": "等待旧实例终止", "command": "kubectl wait --for=delete pod -l app=app --timeout=60s"},
            {"name": "update_deployment", "description": "更新部署配置", "command": f"kubectl set image deployment/app app=app:{release.version}"},
            {"name": "scale_up", "description": "恢复副本数", "command": "kubectl scale deployment/app --replicas=3"},
        ]

    def _estimate_duration(self, release: ReleaseSpec) -> int:
        """估算部署持续时间 (分钟)."""
        base_duration = {
            DeploymentStrategy.RECREATE: 10,
            DeploymentStrategy.ROLLING: 15,
            DeploymentStrategy.BLUE_GREEN: 20,
            DeploymentStrategy.CANARY: 30 + (release.verification_period // 60),
            DeploymentStrategy.A_B_TESTING: 45,
        }
        return base_duration.get(release.strategy, 20)

    def _assess_risk(self, release: ReleaseSpec) -> str:
        """评估部署风险."""
        if release.strategy == DeploymentStrategy.RECREATE:
            return "high"
        elif release.strategy in (DeploymentStrategy.CANARY, DeploymentStrategy.BLUE_GREEN):
            return "low"
        return "medium"

    # =========================================================================
    # 辅助方法 - 从任务中提取规格
    # =========================================================================

    def _extract_project_spec(self, task: Task) -> ProjectSpec:
        """从任务上下文中提取项目规格."""
        ctx = task.context
        return ProjectSpec(
            name=ctx.get("project_name", "project"),
            language=ctx.get("language", "python"),
            framework=ctx.get("framework", ""),
            build_tool=ctx.get("build_tool", "pip"),
            test_command=ctx.get("test_command", "pytest"),
            build_command=ctx.get("build_command", "pip install -e ."),
            environments=ctx.get("environments", ["dev", "staging", "prod"]),
        )

    def _extract_app_spec(self, task: Task) -> ApplicationSpec:
        """从任务上下文中提取应用规格."""
        ctx = task.context
        return ApplicationSpec(
            name=ctx.get("app_name", "app"),
            language=ctx.get("language", "python"),
            version=ctx.get("version", "3.12"),
            port=ctx.get("port", 8000),
            dependencies=ctx.get("dependencies", "requirements.txt"),
            entrypoint=ctx.get("entrypoint", "python -m uvicorn main:app"),
            multi_stage=ctx.get("multi_stage", True),
        )

    def _extract_deployment_spec(self, task: Task) -> DeploymentSpec:
        """从任务上下文中提取部署规格."""
        ctx = task.context
        return DeploymentSpec(
            name=ctx.get("deployment_name", "app"),
            namespace=ctx.get("namespace", "default"),
            replicas=ctx.get("replicas", 3),
            image=ctx.get("image", "app"),
            tag=ctx.get("tag", "latest"),
            environment=ctx.get("environment", "production"),
        )

    def _extract_services(self, task: Task) -> list[Service]:
        """从任务上下文中提取服务列表."""
        services_data = task.context.get("services", [])
        if not services_data:
            return [Service(name="default-service", type="api", port=8000)]
        return [
            Service(
                name=s.get("name", "service"),
                type=s.get("type", "api"),
                port=s.get("port", 8000),
            )
            for s in services_data
        ]

    def _extract_release_spec(self, task: Task) -> ReleaseSpec:
        """从任务上下文中提取发布规格."""
        ctx = task.context
        strategy_str = ctx.get("strategy", "rolling")
        strategy_map = {
            "rolling": DeploymentStrategy.ROLLING,
            "blue_green": DeploymentStrategy.BLUE_GREEN,
            "canary": DeploymentStrategy.CANARY,
            "recreate": DeploymentStrategy.RECREATE,
        }
        return ReleaseSpec(
            version=ctx.get("version", "1.0.0"),
            strategy=strategy_map.get(strategy_str, DeploymentStrategy.ROLLING),
            rollback_on_failure=ctx.get("rollback_on_failure", True),
            traffic_percentage=ctx.get("traffic_percentage", 10),
            verification_period=ctx.get("verification_period", 300),
            approval_required=ctx.get("approval_required", True),
        )


# =============================================================================
# 导出
# =============================================================================

__all__ = [
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
    # 基类
    "BaseExpertAgent",
    # 智能体
    "DevOpsEngineerAgent",
]
