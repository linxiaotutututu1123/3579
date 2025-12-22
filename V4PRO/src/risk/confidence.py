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

        # 高级检查项 (v4.4增强)
        backtest_sample_size: 回测样本数量 (>=100为充足)
        backtest_sharpe: 回测夏普比率 (>=1.0为良好)
        external_signal_valid: 外部信号有效性
        external_signal_correlation: 外部信号相关性 (0.0-1.0)
        regime_alignment: 市场体制对齐
        current_regime: 当前市场体制 (TRENDING/RANGE/VOLATILE/UNKNOWN)
        strategy_regime: 策略适用体制
        cross_asset_correlation: 跨资产相关性风险 (0=低相关, 1=高相关)

        # v4.5 并行执行检查
        parallel_execution_mode: 是否启用并行执行模式
        independent_operations: 独立操作数量 (可并行执行的操作数)
        has_dependencies: 是否存在依赖关系 (False=可完全并行)

        # v4.5 令牌效率检查
        estimated_tokens: 预估令牌消耗
        task_complexity: 任务复杂度 (SIMPLE/MEDIUM/COMPLEX)
        token_budget_ok: 令牌预算是否充足

        # v4.5 工具优化检查
        uses_optimal_tools: 是否使用最优工具组合
        tool_selection_score: 工具选择评分 (0.0-1.0)

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

    # 高级检查项 (v4.4增强)
    backtest_sample_size: int = 0  # 回测样本数量
    backtest_sharpe: float = 0.0  # 回测夏普比率
    external_signal_valid: bool = False  # 外部信号有效性
    external_signal_correlation: float = 0.0  # 外部信号相关性 (0.0-1.0)
    regime_alignment: bool = False  # 市场体制对齐
    current_regime: str = "UNKNOWN"  # 当前市场体制 (TRENDING/RANGE/VOLATILE/UNKNOWN)
    strategy_regime: str = "UNKNOWN"  # 策略适用体制
    cross_asset_correlation: float = 0.0  # 跨资产相关性风险 (0=低相关, 1=高相关)

    # v4.5 并行执行检查
    parallel_execution_mode: bool = False  # 是否启用并行执行模式
    independent_operations: int = 0  # 独立操作数量 (可并行执行的操作数)
    has_dependencies: bool = True  # 是否存在依赖关系 (False=可完全并行)

    # v4.5 令牌效率检查
    estimated_tokens: int = 0  # 预估令牌消耗
    task_complexity: str = "MEDIUM"  # 任务复杂度 (SIMPLE/MEDIUM/COMPLEX)
    token_budget_ok: bool = True  # 令牌预算是否充足

    # v4.5 工具优化检查
    uses_optimal_tools: bool = False  # 是否使用最优工具组合
    tool_selection_score: float = 0.0  # 工具选择评分 (0.0-1.0)

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

    # 高级检查项权重 (v4.4增强)
    WEIGHT_BACKTEST_DATA: ClassVar[float] = 0.15  # 回测数据验证
    WEIGHT_EXTERNAL_SIGNAL: ClassVar[float] = 0.10  # 外部信号相关性
    WEIGHT_REGIME_ALIGNMENT: ClassVar[float] = 0.10  # 市场体制对齐
    WEIGHT_CORRELATION: ClassVar[float] = 0.10  # 跨资产相关性

    # v4.5 增强检查项权重
    WEIGHT_PARALLEL_EXECUTION: ClassVar[float] = 0.10  # 并行执行优化
    WEIGHT_TOKEN_EFFICIENCY: ClassVar[float] = 0.10  # 令牌效率
    WEIGHT_TOOL_OPTIMIZATION: ClassVar[float] = 0.10  # 工具选择优化

    def __init__(
        self,
        high_threshold: float = 0.90,
        medium_threshold: float = 0.70,
        adaptive_mode: bool = False,
    ) -> None:
        """初始化置信度评估器.

        参数:
            high_threshold: 高置信度阈值
            medium_threshold: 中等置信度阈值
            adaptive_mode: 是否启用自适应阈值模式
        """
        self._high_threshold = high_threshold
        self._medium_threshold = medium_threshold
        self._adaptive_mode = adaptive_mode
        self._assessment_count = 0
        self._high_count = 0
        self._medium_count = 0
        self._low_count = 0
        self._score_history: list[float] = []  # 置信度历史记录
        self._max_history = 100  # 最大历史记录数

    def assess(self, context: ConfidenceContext) -> ConfidenceResult:
        """评估置信度.

        根据任务类型选择适当的评估策略。
        支持自适应阈值模式 (v4.3增强)。

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

        # 记录分数历史
        self._record_score(score)

        # 获取阈值 (支持自适应模式)
        if self._adaptive_mode:
            high_thresh, medium_thresh = self.get_adaptive_thresholds(context)
        else:
            high_thresh = self._high_threshold
            medium_thresh = self._medium_threshold

        # 确定等级
        if score >= high_thresh:
            level = ConfidenceLevel.HIGH
            can_proceed = True
            self._high_count += 1
        elif score >= medium_thresh:
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
            "adaptive_mode": self._adaptive_mode,
            "thresholds": {"high": high_thresh, "medium": medium_thresh},
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

    def _assess_advanced(self, context: ConfidenceContext) -> list[ConfidenceCheck]:
        """高级置信度评估 (v4.4增强).

        检查项:
        1. 回测数据检查 (15%) - 验证回测样本量和夏普比率
        2. 外部信号检查 (10%) - 验证外部信号来源
        3. 市场体制对齐检查 (10%) - 验证策略与当前市场体制匹配
        4. 跨资产相关性检查 (10%) - 验证相关性风险可控
        """
        checks: list[ConfidenceCheck] = []

        # 检查1: 回测数据充足性
        backtest_ok = (
            context.backtest_sample_size >= 100 and context.backtest_sharpe >= 1.0
        )
        checks.append(
            ConfidenceCheck(
                name="backtest_data",
                passed=backtest_ok,
                weight=self.WEIGHT_BACKTEST_DATA if backtest_ok else 0.0,
                message=(
                    f"✅ 回测数据充足: {context.backtest_sample_size}样本, "
                    f"夏普={context.backtest_sharpe:.2f}"
                    if backtest_ok
                    else f"⚠️ 回测数据不足: {context.backtest_sample_size}样本, "
                    f"夏普={context.backtest_sharpe:.2f}"
                ),
                details={
                    "sample_size": context.backtest_sample_size,
                    "sharpe": context.backtest_sharpe,
                    "min_sample": 100,
                    "min_sharpe": 1.0,
                },
            )
        )

        # 检查2: 外部信号有效性
        external_ok = (
            context.external_signal_valid
            and context.external_signal_correlation >= 0.5
        )
        checks.append(
            ConfidenceCheck(
                name="external_signal",
                passed=external_ok,
                weight=self.WEIGHT_EXTERNAL_SIGNAL if external_ok else 0.0,
                message=(
                    f"✅ 外部信号有效: 相关性={context.external_signal_correlation:.0%}"
                    if external_ok
                    else f"⚠️ 外部信号无效或相关性低: {context.external_signal_correlation:.0%}"
                ),
                details={
                    "valid": context.external_signal_valid,
                    "correlation": context.external_signal_correlation,
                    "threshold": 0.5,
                },
            )
        )

        # 检查3: 市场体制对齐
        regime_ok = context.regime_alignment or (
            context.current_regime != "UNKNOWN"
            and context.current_regime == context.strategy_regime
        )
        checks.append(
            ConfidenceCheck(
                name="regime_alignment",
                passed=regime_ok,
                weight=self.WEIGHT_REGIME_ALIGNMENT if regime_ok else 0.0,
                message=(
                    f"✅ 市场体制对齐: {context.current_regime}"
                    if regime_ok
                    else f"⚠️ 市场体制不匹配: 当前={context.current_regime}, "
                    f"策略适用={context.strategy_regime}"
                ),
                details={
                    "current_regime": context.current_regime,
                    "strategy_regime": context.strategy_regime,
                    "aligned": regime_ok,
                },
            )
        )

        # 检查4: 跨资产相关性风险
        correlation_ok = context.cross_asset_correlation <= 0.7
        checks.append(
            ConfidenceCheck(
                name="cross_correlation",
                passed=correlation_ok,
                weight=self.WEIGHT_CORRELATION if correlation_ok else 0.0,
                message=(
                    f"[PASS] 相关性风险可控: {context.cross_asset_correlation:.0%}"
                    if correlation_ok
                    else f"[WARN] 相关性风险偏高: {context.cross_asset_correlation:.0%}"
                ),
                details={
                    "correlation": context.cross_asset_correlation,
                    "threshold": 0.7,
                },
            )
        )

        return checks

    def _assess_v45_enhanced(
        self, context: ConfidenceContext
    ) -> list[ConfidenceCheck]:
        """v4.5 增强置信度评估.

        军规覆盖: M3(完整审计), M19(风险归因)

        检查项:
        1. 并行执行检查 (10%) - 验证是否启用并行执行模式及独立操作数
        2. 令牌效率检查 (10%) - 验证令牌预算是否充足
        3. 工具优化检查 (10%) - 验证是否使用最优工具组合

        参数:
            context: 评估上下文

        返回:
            检查结果列表
        """
        checks: list[ConfidenceCheck] = []

        # 检查1: 并行执行优化 (M19: 风险归因 - 执行效率)
        # 条件: 启用并行模式 + 独立操作数>=2 + 无依赖关系
        parallel_ok = (
            context.parallel_execution_mode
            and context.independent_operations >= 2
            and not context.has_dependencies
        )
        # 部分满足条件也给予部分分数
        parallel_score = 0.0
        if context.parallel_execution_mode:
            parallel_score += 0.4
        if context.independent_operations >= 2:
            parallel_score += 0.3
        if not context.has_dependencies:
            parallel_score += 0.3

        checks.append(
            ConfidenceCheck(
                name="parallel_execution",
                passed=parallel_ok,
                weight=self.WEIGHT_PARALLEL_EXECUTION if parallel_ok else 0.0,
                message=(
                    f"[PASS] 并行执行优化: {context.independent_operations}个独立操作"
                    if parallel_ok
                    else f"[WARN] 并行执行未优化: 模式={context.parallel_execution_mode}, "
                    f"独立操作={context.independent_operations}, 依赖={context.has_dependencies}"
                ),
                details={
                    "parallel_mode": context.parallel_execution_mode,
                    "independent_ops": context.independent_operations,
                    "has_dependencies": context.has_dependencies,
                    "partial_score": round(parallel_score, 2),
                    "audit_tag": "M19",  # 风险归因: 执行效率影响
                },
            )
        )

        # 检查2: 令牌效率 (M3: 审计 - 资源消耗追踪)
        # 根据任务复杂度判断令牌预算是否合理
        complexity_budgets = {
            "SIMPLE": 200,
            "MEDIUM": 1000,
            "COMPLEX": 2500,
        }
        expected_budget = complexity_budgets.get(context.task_complexity, 1000)

        token_ok = context.token_budget_ok and (
            context.estimated_tokens <= expected_budget * 1.2  # 允许20%浮动
        )

        checks.append(
            ConfidenceCheck(
                name="token_efficiency",
                passed=token_ok,
                weight=self.WEIGHT_TOKEN_EFFICIENCY if token_ok else 0.0,
                message=(
                    f"[PASS] 令牌效率良好: {context.estimated_tokens}/{expected_budget} "
                    f"({context.task_complexity})"
                    if token_ok
                    else f"[WARN] 令牌效率待优化: {context.estimated_tokens}/{expected_budget} "
                    f"({context.task_complexity})"
                ),
                details={
                    "estimated_tokens": context.estimated_tokens,
                    "expected_budget": expected_budget,
                    "task_complexity": context.task_complexity,
                    "budget_ok": context.token_budget_ok,
                    "audit_tag": "M3",  # 审计: 资源消耗追踪
                },
            )
        )

        # 检查3: 工具选择优化 (M19: 风险归因 - 工具效能)
        # 工具选择评分 >= 0.7 且使用最优工具
        tool_ok = context.uses_optimal_tools and context.tool_selection_score >= 0.7

        checks.append(
            ConfidenceCheck(
                name="tool_optimization",
                passed=tool_ok,
                weight=self.WEIGHT_TOOL_OPTIMIZATION if tool_ok else 0.0,
                message=(
                    f"[PASS] 工具选择优化: 评分={context.tool_selection_score:.0%}"
                    if tool_ok
                    else f"[WARN] 工具选择待优化: 最优工具={context.uses_optimal_tools}, "
                    f"评分={context.tool_selection_score:.0%}"
                ),
                details={
                    "uses_optimal_tools": context.uses_optimal_tools,
                    "tool_selection_score": context.tool_selection_score,
                    "threshold": 0.7,
                    "audit_tag": "M19",  # 风险归因: 工具效能影响
                },
            )
        )

        return checks

    def _assess_combined(self, context: ConfidenceContext) -> list[ConfidenceCheck]:
        """组合评估 (预执行 + 信号 + 扩展 + 高级).

        权重分配:
        - 预执行检查: 30%
        - 信号检查: 30%
        - 扩展检查: 20%
        - 高级检查: 20%
        """
        pre_exec_checks = self._assess_pre_execution(context)
        signal_checks = self._assess_signal(context)
        extended_checks = self._assess_extended(context)
        advanced_checks = self._assess_advanced(context)

        # 调整权重 (预执行30% + 信号30% + 扩展20% + 高级20%)
        for check in pre_exec_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.3

        for check in signal_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.3

        for check in extended_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.2

        for check in advanced_checks:
            check_dict = check.to_dict()
            check_dict["weight"] *= 0.2

        return pre_exec_checks + signal_checks + extended_checks + advanced_checks

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
        self._score_history.clear()

    def get_adaptive_thresholds(
        self, context: ConfidenceContext
    ) -> tuple[float, float]:
        """获取自适应阈值 (v4.3增强).

        根据市场状态动态调整置信度阈值:
        - 高波动市场: 提高阈值要求
        - 低流动性市场: 提高阈值要求
        - 正常市场: 使用默认阈值

        参数:
            context: 评估上下文

        返回:
            (高阈值, 中阈值) 元组
        """
        high_thresh = self._high_threshold
        medium_thresh = self._medium_threshold

        # 波动率调整 (高波动 +5%)
        if context.volatility > 0.3:
            adjustment = min(0.05, (context.volatility - 0.3) * 0.2)
            high_thresh = min(0.99, high_thresh + adjustment)
            medium_thresh = min(0.89, medium_thresh + adjustment)

        # 流动性调整 (低流动性 +3%)
        if context.liquidity_score < 0.6:
            adjustment = min(0.03, (0.6 - context.liquidity_score) * 0.1)
            high_thresh = min(0.99, high_thresh + adjustment)
            medium_thresh = min(0.89, medium_thresh + adjustment)

        # 异常市场状态调整 (+5%)
        if context.market_condition in {"VOLATILE", "CRISIS", "LIMIT_UP", "LIMIT_DOWN"}:
            high_thresh = min(0.99, high_thresh + 0.05)
            medium_thresh = min(0.89, medium_thresh + 0.05)

        return (high_thresh, medium_thresh)

    def get_trend_analysis(self) -> dict[str, Any]:
        """获取置信度趋势分析 (v4.3增强).

        分析历史置信度变化趋势，提供预警信息。

        返回:
            趋势分析结果字典
        """
        if len(self._score_history) < 3:
            return {
                "trend": "INSUFFICIENT_DATA",
                "message": "历史数据不足，无法分析趋势",
                "recent_avg": 0.0,
                "overall_avg": 0.0,
                "direction": "NEUTRAL",
                "alert": False,
            }

        overall_avg = sum(self._score_history) / len(self._score_history)

        # 近期平均 (最近5次)
        recent = self._score_history[-5:]
        recent_avg = sum(recent) / len(recent)

        # 趋势方向
        if recent_avg >= overall_avg + 0.05:
            direction = "UP"
            trend = "IMPROVING"
        elif recent_avg <= overall_avg - 0.05:
            direction = "DOWN"
            trend = "DECLINING"
        else:
            direction = "NEUTRAL"
            trend = "STABLE"

        # 预警检测
        alert = False
        alert_message = ""

        # 连续下降预警
        if len(self._score_history) >= 3:
            last_3 = self._score_history[-3:]
            if all(last_3[i] > last_3[i + 1] for i in range(len(last_3) - 1)):
                alert = True
                alert_message = "⚠️ 置信度连续下降"

        # 低置信度预警
        if recent_avg < 0.70:
            alert = True
            alert_message = "❌ 近期置信度持续偏低"

        return {
            "trend": trend,
            "message": f"趋势: {trend} | 方向: {direction}",
            "recent_avg": round(recent_avg, 4),
            "overall_avg": round(overall_avg, 4),
            "direction": direction,
            "alert": alert,
            "alert_message": alert_message,
            "history_count": len(self._score_history),
        }

    def _record_score(self, score: float) -> None:
        """记录置信度分数到历史."""
        self._score_history.append(score)
        if len(self._score_history) > self._max_history:
            self._score_history.pop(0)


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
