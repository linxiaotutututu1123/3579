"""置信度评估模块 (军规级 v4.0).

V4PRO Platform Component - 置信度评估系统
军规覆盖: M3(完整审计), M19(风险归因)

V4PRO Scenarios:
- K50: CONFIDENCE.PRE_EXEC - 预执行置信度检查
- K51: CONFIDENCE.SIGNAL - 信号置信度评估
- K52: CONFIDENCE.AUDIT - 置信度审计追踪

集成 superclaude ConfidenceChecker 模式与 V4PRO 信号系统。

示例:
    >>> assessor = ConfidenceAssessor()
    >>> context = ConfidenceContext(
    ...     task_type=TaskType.STRATEGY_EXECUTION,
    ...     has_official_docs=True,
    ...     architecture_verified=True,
    ... )
    >>> result = assessor.assess(context)
    >>> if result.can_proceed:
    ...     execute_strategy()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar


class TaskType(Enum):
    """任务类型枚举."""

    STRATEGY_EXECUTION = "STRATEGY_EXECUTION"  # 策略执行
    SIGNAL_GENERATION = "SIGNAL_GENERATION"  # 信号生成
    RISK_ASSESSMENT = "RISK_ASSESSMENT"  # 风险评估
    ORDER_PLACEMENT = "ORDER_PLACEMENT"  # 下单操作
    POSITION_ADJUSTMENT = "POSITION_ADJUSTMENT"  # 仓位调整


class ConfidenceLevel(Enum):
    """置信度等级枚举."""

    HIGH = "HIGH"  # ≥90% - 可直接执行
    MEDIUM = "MEDIUM"  # 70-89% - 需要确认/替代方案
    LOW = "LOW"  # <70% - 停止并调查


@dataclass
class ConfidenceCheck:
    """单项置信度检查结果."""

    name: str
    passed: bool
    weight: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "name": self.name,
            "passed": self.passed,
            "weight": self.weight,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ConfidenceContext:
    """置信度评估上下文.

    属性:
        task_type: 任务类型
        task_name: 任务名称
        symbol: 合约代码(可选)
        strategy_id: 策略ID(可选)

        # 预执行检查项 (superclaude 模式)
        duplicate_check_complete: 是否完成重复检查
        architecture_verified: 是否验证架构合规
        has_official_docs: 是否有官方文档
        has_oss_reference: 是否有OSS参考
        root_cause_identified: 是否识别根因

        # 信号检查项 (V4PRO 模式)
        signal_strength: 信号强度
        signal_consistency: 信号一致性
        market_condition: 市场状态
        risk_within_limits: 风险在限制内

        # 扩展检查项 (v4.3增强)
        volatility: 市场波动率 (0.0-1.0)
        liquidity_score: 流动性评分 (0.0-1.0)
        historical_win_rate: 策略历史胜率 (0.0-1.0)
        position_concentration: 持仓集中度 (0.0-1.0)

        # 元数据
        metadata: 附加元数据
    """

    task_type: TaskType
    task_name: str = ""
    symbol: str = ""
    strategy_id: str = ""

    # 预执行检查项 (superclaude 模式)
    duplicate_check_complete: bool = False
    architecture_verified: bool = False
    has_official_docs: bool = False
    has_oss_reference: bool = False
    root_cause_identified: bool = False

    # 信号检查项 (V4PRO 模式)
    signal_strength: float = 0.0
    signal_consistency: float = 0.0
    market_condition: str = "NORMAL"
    risk_within_limits: bool = True

    # 扩展检查项 (v4.3增强)
    volatility: float = 0.0  # 市场波动率
    liquidity_score: float = 1.0  # 流动性评分 (默认高流动性)
    historical_win_rate: float = 0.5  # 策略历史胜率
    position_concentration: float = 0.0  # 持仓集中度 (0=分散, 1=集中)

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConfidenceResult:
    """置信度评估结果 (不可变).

    属性:
        score: 置信度分数 (0.0-1.0)
        level: 置信度等级
        can_proceed: 是否可以继续
        checks: 各项检查结果
        recommendation: 建议操作
        timestamp: 时间戳
        context_summary: 上下文摘要
    """

    score: float
    level: ConfidenceLevel
    can_proceed: bool
    checks: tuple[ConfidenceCheck, ...]
    recommendation: str
    timestamp: str = ""
    context_summary: dict[str, Any] = field(default_factory=dict)

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式 (M3)."""
        return {
            "event_type": "CONFIDENCE_ASSESSMENT",
            "score": round(self.score, 4),
            "level": self.level.value,
            "can_proceed": self.can_proceed,
            "checks": [c.to_dict() for c in self.checks],
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "context_summary": self.context_summary,
        }

    @property
    def passed_checks(self) -> list[ConfidenceCheck]:
        """获取通过的检查项."""
        return [c for c in self.checks if c.passed]

    @property
    def failed_checks(self) -> list[ConfidenceCheck]:
        """获取失败的检查项."""
        return [c for c in self.checks if not c.passed]


class ConfidenceAssessor:
    """置信度评估器 (军规 M3/M19).

    统一 superclaude 预实现置信度检查与 V4PRO 信号置信度评估。

    功能:
    - 预执行置信度检查 (防止错误方向执行)
    - 信号置信度评估 (交易决策支持)
    - 审计追踪 (M3)
    - 风险归因 (M19)

    置信度阈值:
    - ≥90%: 高置信度 - 可直接执行
    - 70-89%: 中等置信度 - 需要确认或替代方案
    - <70%: 低置信度 - 停止并调查

    示例:
        >>> assessor = ConfidenceAssessor()
        >>> context = ConfidenceContext(
        ...     task_type=TaskType.STRATEGY_EXECUTION,
        ...     has_official_docs=True,
        ... )
        >>> result = assessor.assess(context)
        >>> print(f"置信度: {result.score:.0%}")
    """

    # 阈值常量
    HIGH_THRESHOLD: ClassVar[float] = 0.90
    MEDIUM_THRESHOLD: ClassVar[float] = 0.70

    # 检查项权重 (superclaude 模式)
    WEIGHT_NO_DUPLICATES: ClassVar[float] = 0.25
    WEIGHT_ARCHITECTURE: ClassVar[float] = 0.25
    WEIGHT_OFFICIAL_DOCS: ClassVar[float] = 0.20
    WEIGHT_OSS_REFERENCE: ClassVar[float] = 0.15
    WEIGHT_ROOT_CAUSE: ClassVar[float] = 0.15

    # 检查项权重 (V4PRO 信号模式)
    WEIGHT_SIGNAL_STRENGTH: ClassVar[float] = 0.30
    WEIGHT_SIGNAL_CONSISTENCY: ClassVar[float] = 0.25
    WEIGHT_MARKET_CONDITION: ClassVar[float] = 0.25
    WEIGHT_RISK_LIMITS: ClassVar[float] = 0.20

    # 扩展检查项权重 (v4.3增强)
    WEIGHT_VOLATILITY: ClassVar[float] = 0.15
    WEIGHT_LIQUIDITY: ClassVar[float] = 0.15
    WEIGHT_WIN_RATE: ClassVar[float] = 0.10
    WEIGHT_CONCENTRATION: ClassVar[float] = 0.10

    def __init__(
        self,
        high_threshold: float = 0.90,
        medium_threshold: float = 0.70,
    ) -> None:
        """初始化置信度评估器.

        参数:
            high_threshold: 高置信度阈值
            medium_threshold: 中等置信度阈值
        """
        self._high_threshold = high_threshold
        self._medium_threshold = medium_threshold
        self._assessment_count = 0
        self._high_count = 0
        self._medium_count = 0
        self._low_count = 0

    def assess(self, context: ConfidenceContext) -> ConfidenceResult:
        """评估置信度.

        根据任务类型选择适当的评估策略。

        参数:
            context: 评估上下文

        返回:
            置信度评估结果
        """
        self._assessment_count += 1
        timestamp = datetime.now().isoformat()  # noqa: DTZ005

        # 根据任务类型选择评估策略
        if context.task_type in (TaskType.STRATEGY_EXECUTION, TaskType.ORDER_PLACEMENT):
            checks = self._assess_pre_execution(context)
        elif context.task_type == TaskType.SIGNAL_GENERATION:
            checks = self._assess_signal(context)
        else:
            checks = self._assess_combined(context)

        # 计算总分
        score = sum(c.weight for c in checks if c.passed)

        # 确定等级
        if score >= self._high_threshold:
            level = ConfidenceLevel.HIGH
            can_proceed = True
            self._high_count += 1
        elif score >= self._medium_threshold:
            level = ConfidenceLevel.MEDIUM
            can_proceed = False  # 需要确认
            self._medium_count += 1
        else:
            level = ConfidenceLevel.LOW
            can_proceed = False
            self._low_count += 1

        recommendation = self._get_recommendation(level, checks)

        context_summary = {
            "task_type": context.task_type.value,
            "task_name": context.task_name,
            "symbol": context.symbol,
            "strategy_id": context.strategy_id,
        }

        return ConfidenceResult(
            score=score,
            level=level,
            can_proceed=can_proceed,
            checks=tuple(checks),
            recommendation=recommendation,
            timestamp=timestamp,
            context_summary=context_summary,
        )

    def _assess_pre_execution(
        self, context: ConfidenceContext
    ) -> list[ConfidenceCheck]:
        """预执行置信度评估 (superclaude 模式).

        检查项:
        1. 无重复实现 (25%)
        2. 架构合规 (25%)
        3. 官方文档验证 (20%)
        4. OSS参考实现 (15%)
        5. 根因识别 (15%)
        """
        checks: list[ConfidenceCheck] = []

        # 检查1: 无重复实现
        checks.append(
            ConfidenceCheck(
                name="no_duplicates",
                passed=context.duplicate_check_complete,
                weight=self.WEIGHT_NO_DUPLICATES,
                message=(
                    "✅ 无重复实现"
                    if context.duplicate_check_complete
                    else "❌ 请先检查现有实现"
                ),
            )
        )

        # 检查2: 架构合规
        checks.append(
            ConfidenceCheck(
                name="architecture_verified",
                passed=context.architecture_verified,
                weight=self.WEIGHT_ARCHITECTURE,
                message=(
                    "✅ 架构合规"
                    if context.architecture_verified
                    else "❌ 请验证架构合规性"
                ),
            )
        )

        # 检查3: 官方文档
        checks.append(
            ConfidenceCheck(
                name="official_docs",
                passed=context.has_official_docs,
                weight=self.WEIGHT_OFFICIAL_DOCS,
                message=(
                    "✅ 官方文档已验证"
                    if context.has_official_docs
                    else "❌ 请查阅官方文档"
                ),
            )
        )

        # 检查4: OSS参考
        checks.append(
            ConfidenceCheck(
                name="oss_reference",
                passed=context.has_oss_reference,
                weight=self.WEIGHT_OSS_REFERENCE,
                message=(
                    "✅ OSS参考已找到"
                    if context.has_oss_reference
                    else "❌ 请搜索OSS参考实现"
                ),
            )
        )

        # 检查5: 根因识别
        checks.append(
            ConfidenceCheck(
                name="root_cause",
                passed=context.root_cause_identified,
                weight=self.WEIGHT_ROOT_CAUSE,
                message=(
                    "✅ 根因已识别"
                    if context.root_cause_identified
                    else "❌ 请继续调查根因"
                ),
            )
        )

        return checks

    def _assess_signal(self, context: ConfidenceContext) -> list[ConfidenceCheck]:
        """信号置信度评估 (V4PRO 模式).

        检查项:
        1. 信号强度 (30%)
        2. 信号一致性 (25%)
        3. 市场状态 (25%)
        4. 风险限制 (20%)
        """
        checks: list[ConfidenceCheck] = []

        # 检查1: 信号强度
        strength_ok = context.signal_strength >= 0.5
        checks.append(
            ConfidenceCheck(
                name="signal_strength",
                passed=strength_ok,
                weight=self.WEIGHT_SIGNAL_STRENGTH if strength_ok else 0.0,
                message=(
                    f"✅ 信号强度: {context.signal_strength:.0%}"
                    if strength_ok
                    else f"❌ 信号强度不足: {context.signal_strength:.0%}"
                ),
                details={"value": context.signal_strength},
            )
        )

        # 检查2: 信号一致性
        consistency_ok = context.signal_consistency >= 0.6
        checks.append(
            ConfidenceCheck(
                name="signal_consistency",
                passed=consistency_ok,
                weight=self.WEIGHT_SIGNAL_CONSISTENCY if consistency_ok else 0.0,
                message=(
                    f"✅ 信号一致性: {context.signal_consistency:.0%}"
                    if consistency_ok
                    else f"❌ 信号一致性不足: {context.signal_consistency:.0%}"
                ),
                details={"value": context.signal_consistency},
            )
        )

        # 检查3: 市场状态
        normal_conditions = {"NORMAL", "TRENDING", "RANGE"}
        market_ok = context.market_condition in normal_conditions
        checks.append(
            ConfidenceCheck(
                name="market_condition",
                passed=market_ok,
                weight=self.WEIGHT_MARKET_CONDITION if market_ok else 0.0,
                message=(
                    f"✅ 市场状态: {context.market_condition}"
                    if market_ok
                    else f"❌ 市场状态异常: {context.market_condition}"
                ),
                details={"condition": context.market_condition},
            )
        )

        # 检查4: 风险限制
        checks.append(
            ConfidenceCheck(
                name="risk_limits",
                passed=context.risk_within_limits,
                weight=self.WEIGHT_RISK_LIMITS if context.risk_within_limits else 0.0,
                message=(
                    "✅ 风险在限制内"
                    if context.risk_within_limits
                    else "❌ 风险超出限制"
                ),
            )
        )

        return checks

    def _assess_extended(self, context: ConfidenceContext) -> list[ConfidenceCheck]:
        """扩展置信度评估 (v4.3增强).

        检查项:
        1. 波动率检查 (15%) - 低波动率更安全
        2. 流动性检查 (15%) - 高流动性更可靠
        3. 历史胜率检查 (10%) - 高胜率策略更可信
        4. 持仓集中度检查 (10%) - 分散持仓更稳健
        """
        checks: list[ConfidenceCheck] = []

        # 检查1: 波动率 (低于0.3为正常)
        volatility_ok = context.volatility <= 0.3
        checks.append(
            ConfidenceCheck(
                name="volatility",
                passed=volatility_ok,
                weight=self.WEIGHT_VOLATILITY if volatility_ok else 0.0,
                message=(
                    f"✅ 波动率正常: {context.volatility:.0%}"
                    if volatility_ok
                    else f"⚠️ 波动率偏高: {context.volatility:.0%}"
                ),
                details={"value": context.volatility, "threshold": 0.3},
            )
        )

        # 检查2: 流动性 (高于0.6为良好)
        liquidity_ok = context.liquidity_score >= 0.6
        checks.append(
            ConfidenceCheck(
                name="liquidity",
                passed=liquidity_ok,
                weight=self.WEIGHT_LIQUIDITY if liquidity_ok else 0.0,
                message=(
                    f"✅ 流动性良好: {context.liquidity_score:.0%}"
                    if liquidity_ok
                    else f"⚠️ 流动性不足: {context.liquidity_score:.0%}"
                ),
                details={"value": context.liquidity_score, "threshold": 0.6},
            )
        )

        # 检查3: 历史胜率 (高于0.5为正向期望)
        win_rate_ok = context.historical_win_rate >= 0.5
        checks.append(
            ConfidenceCheck(
                name="win_rate",
                passed=win_rate_ok,
                weight=self.WEIGHT_WIN_RATE if win_rate_ok else 0.0,
                message=(
                    f"✅ 历史胜率: {context.historical_win_rate:.0%}"
                    if win_rate_ok
                    else f"⚠️ 历史胜率偏低: {context.historical_win_rate:.0%}"
                ),
                details={"value": context.historical_win_rate, "threshold": 0.5},
            )
        )

        # 检查4: 持仓集中度 (低于0.5为分散)
        concentration_ok = context.position_concentration <= 0.5
        checks.append(
            ConfidenceCheck(
                name="concentration",
                passed=concentration_ok,
                weight=self.WEIGHT_CONCENTRATION if concentration_ok else 0.0,
                message=(
                    f"✅ 持仓分散: {context.position_concentration:.0%}"
                    if concentration_ok
                    else f"⚠️ 持仓集中: {context.position_concentration:.0%}"
                ),
                details={"value": context.position_concentration, "threshold": 0.5},
            )
        )

        return checks

    def _assess_combined(self, context: ConfidenceContext) -> list[ConfidenceCheck]:
        """组合评估 (预执行 + 信号 + 扩展)."""
        pre_exec_checks = self._assess_pre_execution(context)
        signal_checks = self._assess_signal(context)
        extended_checks = self._assess_extended(context)

        # 调整权重 (预执行40% + 信号40% + 扩展20%)
        for check in pre_exec_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.4

        for check in signal_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.4

        for check in extended_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.2

        return pre_exec_checks + signal_checks + extended_checks

    def _get_recommendation(
        self, level: ConfidenceLevel, checks: list[ConfidenceCheck]
    ) -> str:
        """获取建议操作.

        参数:
            level: 置信度等级
            checks: 检查结果列表

        返回:
            建议操作字符串
        """
        if level == ConfidenceLevel.HIGH:
            return "✅ 高置信度 (≥90%) - 可直接执行"

        failed = [c for c in checks if not c.passed]
        failed_names = ", ".join(c.name for c in failed[:3])

        if level == ConfidenceLevel.MEDIUM:
            return f"⚠️ 中等置信度 (70-89%) - 建议确认: {failed_names}"

        return f"❌ 低置信度 (<70%) - 停止并调查: {failed_names}"

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        total = self._assessment_count
        return {
            "total_assessments": total,
            "high_confidence_count": self._high_count,
            "medium_confidence_count": self._medium_count,
            "low_confidence_count": self._low_count,
            "high_rate": self._high_count / total if total > 0 else 0.0,
            "medium_rate": self._medium_count / total if total > 0 else 0.0,
            "low_rate": self._low_count / total if total > 0 else 0.0,
        }

    def reset_statistics(self) -> None:
        """重置统计信息."""
        self._assessment_count = 0
        self._high_count = 0
        self._medium_count = 0
        self._low_count = 0


# ============================================================
# 便捷函数
# ============================================================


def assess_pre_execution(
    task_name: str,
    *,
    duplicate_check: bool = False,
    architecture_verified: bool = False,
    has_docs: bool = False,
    has_oss: bool = False,
    root_cause: bool = False,
) -> ConfidenceResult:
    """快速预执行置信度评估.

    参数:
        task_name: 任务名称
        duplicate_check: 是否完成重复检查
        architecture_verified: 是否验证架构
        has_docs: 是否有官方文档
        has_oss: 是否有OSS参考
        root_cause: 是否识别根因

    返回:
        置信度评估结果
    """
    assessor = ConfidenceAssessor()
    context = ConfidenceContext(
        task_type=TaskType.STRATEGY_EXECUTION,
        task_name=task_name,
        duplicate_check_complete=duplicate_check,
        architecture_verified=architecture_verified,
        has_official_docs=has_docs,
        has_oss_reference=has_oss,
        root_cause_identified=root_cause,
    )
    return assessor.assess(context)


def assess_signal(
    symbol: str,
    strategy_id: str,
    *,
    strength: float = 0.0,
    consistency: float = 0.0,
    market_condition: str = "NORMAL",
    risk_ok: bool = True,
) -> ConfidenceResult:
    """快速信号置信度评估.

    参数:
        symbol: 合约代码
        strategy_id: 策略ID
        strength: 信号强度
        consistency: 信号一致性
        market_condition: 市场状态
        risk_ok: 风险是否在限制内

    返回:
        置信度评估结果
    """
    assessor = ConfidenceAssessor()
    context = ConfidenceContext(
        task_type=TaskType.SIGNAL_GENERATION,
        symbol=symbol,
        strategy_id=strategy_id,
        signal_strength=strength,
        signal_consistency=consistency,
        market_condition=market_condition,
        risk_within_limits=risk_ok,
    )
    return assessor.assess(context)


def format_confidence_report(result: ConfidenceResult) -> str:
    """格式化置信度报告.

    参数:
        result: 置信度评估结果

    返回:
        格式化的报告字符串
    """
    lines = [
        "📋 置信度评估报告",
        "=" * 40,
        "",
    ]

    for check in result.checks:
        lines.append(f"   {check.message}")

    lines.extend([
        "",
        f"📊 置信度: {result.score:.0%}",
        result.recommendation,
    ])

    return "\n".join(lines)
