"""工作流引擎 (Workflow Engine).

V4PRO Platform Component - 工作流定义和执行引擎
军规覆盖: M3(审计), M7(回放一致性), M31(置信度)

定义标准工作流模板和执行逻辑。

示例:
    >>> engine = WorkflowEngine()
    >>> workflow = engine.get_workflow("feature_development")
    >>> result = await engine.execute(workflow, context)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class WorkflowType(Enum):
    """工作流类型枚举."""

    FEATURE_DEVELOPMENT = "feature_development"  # 功能开发
    BUG_FIX = "bug_fix"  # Bug修复
    REFACTORING = "refactoring"  # 代码重构
    SECURITY_AUDIT = "security_audit"  # 安全审计
    PERFORMANCE_OPTIMIZATION = "performance_optimization"  # 性能优化
    DOCUMENTATION = "documentation"  # 文档编写
    CODE_REVIEW = "code_review"  # 代码审查
    DEPLOYMENT = "deployment"  # 部署发布


class PhaseType(Enum):
    """阶段类型枚举."""

    ANALYSIS = "analysis"  # 分析
    DESIGN = "design"  # 设计
    IMPLEMENTATION = "implementation"  # 实现
    TESTING = "testing"  # 测试
    REVIEW = "review"  # 审查
    DOCUMENTATION = "documentation"  # 文档
    DEPLOYMENT = "deployment"  # 部署


class GateType(Enum):
    """门禁类型枚举."""

    CONFIDENCE_CHECK = "confidence_check"  # 置信度检查
    APPROVAL = "approval"  # 人工审批
    AUTO_TEST = "auto_test"  # 自动测试
    SECURITY_SCAN = "security_scan"  # 安全扫描
    CODE_REVIEW = "code_review"  # 代码审查


@dataclass
class WorkflowGate:
    """工作流门禁.

    定义阶段之间的质量门禁。
    """

    gate_id: str
    gate_type: GateType
    condition: str
    required_confidence: float = 0.90
    auto_pass: bool = False  # 是否自动通过
    timeout_ms: int = 300000  # 超时时间


@dataclass
class WorkflowPhase:
    """工作流阶段.

    定义工作流的一个阶段及其配置。
    """

    phase_id: str
    phase_type: PhaseType
    name: str
    description: str
    assigned_roles: list[str] = field(default_factory=list)
    parallel_execution: bool = False
    required_inputs: list[str] = field(default_factory=list)
    expected_outputs: list[str] = field(default_factory=list)
    gate: WorkflowGate | None = None
    timeout_ms: int = 120000
    retry_count: int = 3

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "phase_id": self.phase_id,
            "phase_type": self.phase_type.value,
            "name": self.name,
            "description": self.description,
            "assigned_roles": self.assigned_roles,
            "parallel_execution": self.parallel_execution,
            "required_inputs": self.required_inputs,
            "expected_outputs": self.expected_outputs,
            "gate": {
                "gate_id": self.gate.gate_id,
                "gate_type": self.gate.gate_type.value,
                "condition": self.gate.condition,
            } if self.gate else None,
        }


@dataclass
class Workflow:
    """工作流定义.

    完整的工作流定义，包含所有阶段和配置。
    """

    workflow_id: str
    workflow_type: WorkflowType
    name: str
    description: str
    phases: list[WorkflowPhase] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()  # noqa: DTZ005
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    # 全局配置
    min_confidence: float = 0.90
    require_all_gates: bool = True
    enable_parallel_phases: bool = True

    @property
    def total_phases(self) -> int:
        """总阶段数."""
        return len(self.phases)

    @property
    def has_gates(self) -> bool:
        """是否有门禁."""
        return any(phase.gate is not None for phase in self.phases)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type.value,
            "name": self.name,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "version": self.version,
            "min_confidence": self.min_confidence,
        }


@dataclass
class WorkflowExecution:
    """工作流执行实例.

    记录工作流的一次执行。
    """

    execution_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    workflow_id: str = ""
    status: str = "pending"  # pending, running, completed, failed, cancelled
    current_phase_id: str = ""
    completed_phases: list[str] = field(default_factory=list)
    failed_phases: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    total_duration_ms: int = 0
    confidence_score: float = 0.0
    artifacts: list[str] = field(default_factory=list)
    error_message: str = ""

    @property
    def is_completed(self) -> bool:
        """是否完成."""
        return self.status == "completed"

    @property
    def is_failed(self) -> bool:
        """是否失败."""
        return self.status == "failed"


# ============================================================
# 预定义工作流模板
# ============================================================


def create_feature_development_workflow() -> Workflow:
    """创建功能开发工作流.

    标准的软件功能开发流程:
    需求分析 → 架构设计 → 开发实现 → 测试验证 → 代码审查 → 文档编写
    """
    return Workflow(
        workflow_id="WF-FEAT-001",
        workflow_type=WorkflowType.FEATURE_DEVELOPMENT,
        name="功能开发工作流",
        description="完整的功能开发流程，从需求到交付",
        phases=[
            # Phase 1: 需求分析
            WorkflowPhase(
                phase_id="P1-REQ",
                phase_type=PhaseType.ANALYSIS,
                name="需求分析",
                description="分析和细化功能需求",
                assigned_roles=["project_manager", "tech_lead"],
                required_inputs=["user_story", "acceptance_criteria"],
                expected_outputs=["requirement_spec", "task_breakdown"],
                gate=WorkflowGate(
                    gate_id="G1-REQ",
                    gate_type=GateType.CONFIDENCE_CHECK,
                    condition="需求理解置信度 >= 90%",
                    required_confidence=0.90,
                ),
            ),
            # Phase 2: 架构设计
            WorkflowPhase(
                phase_id="P2-ARCH",
                phase_type=PhaseType.DESIGN,
                name="架构设计",
                description="系统架构和技术方案设计",
                assigned_roles=["system_architect", "security_architect"],
                required_inputs=["requirement_spec"],
                expected_outputs=["architecture_doc", "api_design", "security_review"],
                gate=WorkflowGate(
                    gate_id="G2-ARCH",
                    gate_type=GateType.APPROVAL,
                    condition="架构设计已审批",
                ),
            ),
            # Phase 3: 开发实现
            WorkflowPhase(
                phase_id="P3-DEV",
                phase_type=PhaseType.IMPLEMENTATION,
                name="开发实现",
                description="代码开发和实现",
                assigned_roles=["backend_engineer", "frontend_engineer"],
                parallel_execution=True,  # 前后端并行开发
                required_inputs=["architecture_doc", "api_design"],
                expected_outputs=["source_code", "unit_tests"],
                gate=WorkflowGate(
                    gate_id="G3-DEV",
                    gate_type=GateType.AUTO_TEST,
                    condition="单元测试通过率 >= 95%",
                ),
            ),
            # Phase 4: 测试验证
            WorkflowPhase(
                phase_id="P4-TEST",
                phase_type=PhaseType.TESTING,
                name="测试验证",
                description="集成测试和验收测试",
                assigned_roles=["qa_engineer"],
                required_inputs=["source_code", "unit_tests"],
                expected_outputs=["test_report", "coverage_report"],
                gate=WorkflowGate(
                    gate_id="G4-TEST",
                    gate_type=GateType.AUTO_TEST,
                    condition="测试覆盖率 >= 80%",
                ),
            ),
            # Phase 5: 代码审查
            WorkflowPhase(
                phase_id="P5-REVIEW",
                phase_type=PhaseType.REVIEW,
                name="代码审查",
                description="代码质量和安全审查",
                assigned_roles=["code_reviewer", "security_architect"],
                parallel_execution=True,
                required_inputs=["source_code"],
                expected_outputs=["review_comments", "security_report"],
                gate=WorkflowGate(
                    gate_id="G5-REVIEW",
                    gate_type=GateType.CODE_REVIEW,
                    condition="无严重问题",
                ),
            ),
            # Phase 6: 文档编写
            WorkflowPhase(
                phase_id="P6-DOC",
                phase_type=PhaseType.DOCUMENTATION,
                name="文档编写",
                description="技术文档和API文档",
                assigned_roles=["tech_writer"],
                required_inputs=["source_code", "api_design"],
                expected_outputs=["api_docs", "user_guide"],
            ),
        ],
        min_confidence=0.90,
    )


def create_bug_fix_workflow() -> Workflow:
    """创建Bug修复工作流.

    快速Bug修复流程:
    问题分析 → 根因定位 → 修复实现 → 测试验证 → 审查发布
    """
    return Workflow(
        workflow_id="WF-BUG-001",
        workflow_type=WorkflowType.BUG_FIX,
        name="Bug修复工作流",
        description="快速Bug修复流程",
        phases=[
            # Phase 1: 问题分析
            WorkflowPhase(
                phase_id="P1-ANALYZE",
                phase_type=PhaseType.ANALYSIS,
                name="问题分析",
                description="分析Bug现象和影响范围",
                assigned_roles=["qa_engineer", "backend_engineer"],
                required_inputs=["bug_report", "error_logs"],
                expected_outputs=["analysis_report"],
            ),
            # Phase 2: 根因定位
            WorkflowPhase(
                phase_id="P2-ROOT",
                phase_type=PhaseType.ANALYSIS,
                name="根因定位",
                description="定位问题根本原因",
                assigned_roles=["backend_engineer", "tech_lead"],
                required_inputs=["analysis_report", "source_code"],
                expected_outputs=["root_cause_analysis"],
                gate=WorkflowGate(
                    gate_id="G2-ROOT",
                    gate_type=GateType.CONFIDENCE_CHECK,
                    condition="根因确认置信度 >= 95%",
                    required_confidence=0.95,
                ),
            ),
            # Phase 3: 修复实现
            WorkflowPhase(
                phase_id="P3-FIX",
                phase_type=PhaseType.IMPLEMENTATION,
                name="修复实现",
                description="实现Bug修复",
                assigned_roles=["backend_engineer"],
                required_inputs=["root_cause_analysis"],
                expected_outputs=["fix_code", "regression_tests"],
            ),
            # Phase 4: 测试验证
            WorkflowPhase(
                phase_id="P4-VERIFY",
                phase_type=PhaseType.TESTING,
                name="测试验证",
                description="验证修复有效性",
                assigned_roles=["qa_engineer"],
                required_inputs=["fix_code", "regression_tests"],
                expected_outputs=["verification_report"],
                gate=WorkflowGate(
                    gate_id="G4-VERIFY",
                    gate_type=GateType.AUTO_TEST,
                    condition="回归测试全部通过",
                ),
            ),
            # Phase 5: 审查发布
            WorkflowPhase(
                phase_id="P5-RELEASE",
                phase_type=PhaseType.REVIEW,
                name="审查发布",
                description="代码审查和发布",
                assigned_roles=["code_reviewer", "devops_engineer"],
                required_inputs=["fix_code", "verification_report"],
                expected_outputs=["release_notes"],
            ),
        ],
        min_confidence=0.95,  # Bug修复需要更高置信度
    )


def create_security_audit_workflow() -> Workflow:
    """创建安全审计工作流.

    安全审计流程:
    资产识别 → 威胁建模 → 漏洞扫描 → 渗透测试 → 修复验证
    """
    return Workflow(
        workflow_id="WF-SEC-001",
        workflow_type=WorkflowType.SECURITY_AUDIT,
        name="安全审计工作流",
        description="全面的安全审计流程",
        phases=[
            WorkflowPhase(
                phase_id="P1-ASSET",
                phase_type=PhaseType.ANALYSIS,
                name="资产识别",
                description="识别系统资产和攻击面",
                assigned_roles=["security_architect"],
                expected_outputs=["asset_inventory", "attack_surface_map"],
            ),
            WorkflowPhase(
                phase_id="P2-THREAT",
                phase_type=PhaseType.DESIGN,
                name="威胁建模",
                description="分析潜在威胁和风险",
                assigned_roles=["security_architect"],
                required_inputs=["asset_inventory"],
                expected_outputs=["threat_model", "risk_assessment"],
            ),
            WorkflowPhase(
                phase_id="P3-SCAN",
                phase_type=PhaseType.TESTING,
                name="漏洞扫描",
                description="自动化漏洞扫描",
                assigned_roles=["security_architect", "devops_engineer"],
                required_inputs=["attack_surface_map"],
                expected_outputs=["scan_report"],
                gate=WorkflowGate(
                    gate_id="G3-SCAN",
                    gate_type=GateType.SECURITY_SCAN,
                    condition="无高危漏洞",
                ),
            ),
            WorkflowPhase(
                phase_id="P4-PENTEST",
                phase_type=PhaseType.TESTING,
                name="渗透测试",
                description="手动渗透测试",
                assigned_roles=["security_architect"],
                required_inputs=["scan_report", "threat_model"],
                expected_outputs=["pentest_report"],
            ),
            WorkflowPhase(
                phase_id="P5-REMEDIATE",
                phase_type=PhaseType.IMPLEMENTATION,
                name="修复验证",
                description="漏洞修复和验证",
                assigned_roles=["backend_engineer", "security_architect"],
                required_inputs=["pentest_report"],
                expected_outputs=["remediation_report", "verification_evidence"],
            ),
        ],
        min_confidence=0.95,
    )


# ============================================================
# 工作流引擎
# ============================================================


class WorkflowEngine:
    """工作流引擎.

    负责工作流的管理和执行。
    """

    def __init__(self) -> None:
        """初始化工作流引擎."""
        self._workflows: dict[str, Workflow] = {}
        self._executions: dict[str, WorkflowExecution] = {}
        self._register_default_workflows()

    def _register_default_workflows(self) -> None:
        """注册默认工作流."""
        self.register_workflow(create_feature_development_workflow())
        self.register_workflow(create_bug_fix_workflow())
        self.register_workflow(create_security_audit_workflow())

    def register_workflow(self, workflow: Workflow) -> None:
        """注册工作流.

        参数:
            workflow: 工作流定义
        """
        self._workflows[workflow.workflow_id] = workflow
        self._workflows[workflow.workflow_type.value] = workflow

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """获取工作流.

        参数:
            workflow_id: 工作流ID或类型

        返回:
            工作流定义
        """
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        """列出所有工作流."""
        # 去重
        seen = set()
        result = []
        for wf in self._workflows.values():
            if wf.workflow_id not in seen:
                seen.add(wf.workflow_id)
                result.append(wf)
        return result

    def create_execution(self, workflow: Workflow) -> WorkflowExecution:
        """创建工作流执行实例.

        参数:
            workflow: 工作流定义

        返回:
            执行实例
        """
        execution = WorkflowExecution(
            workflow_id=workflow.workflow_id,
            status="pending",
            start_time=datetime.now().isoformat(),  # noqa: DTZ005
        )
        self._executions[execution.execution_id] = execution
        return execution

    def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """获取执行实例."""
        return self._executions.get(execution_id)

    def update_execution_phase(
        self,
        execution_id: str,
        phase_id: str,
        success: bool,
    ) -> None:
        """更新执行阶段状态.

        参数:
            execution_id: 执行ID
            phase_id: 阶段ID
            success: 是否成功
        """
        execution = self._executions.get(execution_id)
        if execution is None:
            return

        if success:
            execution.completed_phases.append(phase_id)
        else:
            execution.failed_phases.append(phase_id)
            execution.status = "failed"

    def complete_execution(
        self,
        execution_id: str,
        success: bool,
        confidence_score: float = 0.0,
    ) -> None:
        """完成执行.

        参数:
            execution_id: 执行ID
            success: 是否成功
            confidence_score: 置信度分数
        """
        execution = self._executions.get(execution_id)
        if execution is None:
            return

        execution.status = "completed" if success else "failed"
        execution.end_time = datetime.now().isoformat()  # noqa: DTZ005
        execution.confidence_score = confidence_score

        # 计算总时长
        if execution.start_time:
            start = datetime.fromisoformat(execution.start_time)
            end = datetime.fromisoformat(execution.end_time)
            execution.total_duration_ms = int(
                (end - start).total_seconds() * 1000
            )


# ============================================================
# 便捷函数
# ============================================================


def get_workflow_for_task(task_type: str) -> Workflow:
    """根据任务类型获取合适的工作流.

    参数:
        task_type: 任务类型 (feature, bug, security, etc.)

    返回:
        匹配的工作流
    """
    engine = WorkflowEngine()

    type_mapping = {
        "feature": WorkflowType.FEATURE_DEVELOPMENT,
        "bug": WorkflowType.BUG_FIX,
        "fix": WorkflowType.BUG_FIX,
        "security": WorkflowType.SECURITY_AUDIT,
        "audit": WorkflowType.SECURITY_AUDIT,
    }

    workflow_type = type_mapping.get(
        task_type.lower(),
        WorkflowType.FEATURE_DEVELOPMENT,
    )

    return engine.get_workflow(workflow_type.value) or create_feature_development_workflow()
