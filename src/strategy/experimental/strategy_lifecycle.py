"""策略生命周期管理器 (军规级 v4.2).

V4PRO Platform Component - Phase 8 智能策略升级
V4 SPEC: §24 实验性策略门禁 - 闭环管理

军规覆盖:
- M18: 实验性门禁 - 未成熟策略禁止实盘启用
- M12: 双重确认 - 大额调整需人工审批
- M19: 风险归因 - 策略表现追踪

功能特性:
- 策略生命周期状态管理
- 成熟度与资金分配联动
- 自动晋升/降级机制
- 表现监控与告警
- 审计日志记录

示例:
    >>> from src.strategy.experimental import StrategyLifecycleManager
    >>> manager = StrategyLifecycleManager()
    >>> manager.register_strategy("ppo_v1", "PPO强化学习策略", "rl")
    >>> allocation = manager.calculate_allocation("ppo_v1", maturity_pct=0.85)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar


if TYPE_CHECKING:
    from collections.abc import Callable


class LifecycleStage(Enum):
    """策略生命周期阶段."""

    INCUBATION = "孵化期"  # 0-40% 成熟度，0%资金
    DEVELOPMENT = "发展期"  # 40-60% 成熟度，0%资金
    VALIDATION = "验证期"  # 60-80% 成熟度，5%资金试运行
    PRODUCTION = "生产期"  # 80-100% 成熟度，正式分配
    DEGRADED = "降级期"  # 表现下滑，减少资金
    SUSPENDED = "暂停期"  # 表现严重下滑，暂停
    RETIRED = "退役期"  # 策略退役


class AllocationTier(Enum):
    """资金分配等级."""

    ZERO = "零分配"  # 0%
    TRIAL = "试运行"  # 5%
    MINIMAL = "最小分配"  # 10%
    NORMAL = "正常分配"  # 20%
    ENHANCED = "增强分配"  # 30%
    MAXIMUM = "最大分配"  # 40%


@dataclass(frozen=True)
class AllocationConfig:
    """资金分配配置.

    属性:
        tier: 分配等级
        max_capital_pct: 最大资金占比
        max_position_pct: 最大持仓占比
        max_single_trade_pct: 单笔最大占比
        leverage_limit: 杠杆限制
    """

    tier: AllocationTier
    max_capital_pct: float
    max_position_pct: float
    max_single_trade_pct: float
    leverage_limit: float


# 分配等级配置表
ALLOCATION_CONFIGS: dict[AllocationTier, AllocationConfig] = {
    AllocationTier.ZERO: AllocationConfig(
        tier=AllocationTier.ZERO,
        max_capital_pct=0.0,
        max_position_pct=0.0,
        max_single_trade_pct=0.0,
        leverage_limit=0.0,
    ),
    AllocationTier.TRIAL: AllocationConfig(
        tier=AllocationTier.TRIAL,
        max_capital_pct=0.05,
        max_position_pct=0.02,
        max_single_trade_pct=0.01,
        leverage_limit=1.0,
    ),
    AllocationTier.MINIMAL: AllocationConfig(
        tier=AllocationTier.MINIMAL,
        max_capital_pct=0.10,
        max_position_pct=0.05,
        max_single_trade_pct=0.02,
        leverage_limit=1.5,
    ),
    AllocationTier.NORMAL: AllocationConfig(
        tier=AllocationTier.NORMAL,
        max_capital_pct=0.20,
        max_position_pct=0.10,
        max_single_trade_pct=0.03,
        leverage_limit=2.0,
    ),
    AllocationTier.ENHANCED: AllocationConfig(
        tier=AllocationTier.ENHANCED,
        max_capital_pct=0.30,
        max_position_pct=0.15,
        max_single_trade_pct=0.05,
        leverage_limit=2.5,
    ),
    AllocationTier.MAXIMUM: AllocationConfig(
        tier=AllocationTier.MAXIMUM,
        max_capital_pct=0.40,
        max_position_pct=0.20,
        max_single_trade_pct=0.08,
        leverage_limit=3.0,
    ),
}


@dataclass
class StrategyPerformance:
    """策略表现数据.

    属性:
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 胜率
        profit_factor: 盈亏比
        daily_pnl: 日盈亏列表
        trade_count: 交易次数
        last_updated: 最后更新时间
    """

    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    daily_pnl: list[float] = field(default_factory=list)
    trade_count: int = 0
    last_updated: datetime | None = None


@dataclass
class StrategyState:
    """策略状态.

    属性:
        strategy_id: 策略ID
        strategy_name: 策略名称
        strategy_type: 策略类型
        stage: 生命周期阶段
        allocation_tier: 资金分配等级
        maturity_pct: 成熟度百分比
        performance: 表现数据
        promotion_count: 晋升次数
        demotion_count: 降级次数
        registered_at: 注册时间
        last_stage_change: 最后阶段变更时间
        notes: 备注
        metadata: 元数据
    """

    strategy_id: str
    strategy_name: str
    strategy_type: str
    stage: LifecycleStage = LifecycleStage.INCUBATION
    allocation_tier: AllocationTier = AllocationTier.ZERO
    maturity_pct: float = 0.0
    performance: StrategyPerformance = field(default_factory=StrategyPerformance)
    promotion_count: int = 0
    demotion_count: int = 0
    registered_at: datetime = field(default_factory=datetime.now)
    last_stage_change: datetime | None = None
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式."""
        return {
            "event_type": "STRATEGY_STATE",
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type,
            "stage": self.stage.value,
            "allocation_tier": self.allocation_tier.value,
            "maturity_pct": round(self.maturity_pct, 4),
            "sharpe_ratio": round(self.performance.sharpe_ratio, 4),
            "max_drawdown": round(self.performance.max_drawdown, 4),
            "promotion_count": self.promotion_count,
            "demotion_count": self.demotion_count,
            "timestamp": datetime.now().isoformat(),  # noqa: DTZ005
        }


@dataclass
class TransitionEvent:
    """状态转换事件.

    属性:
        strategy_id: 策略ID
        from_stage: 原阶段
        to_stage: 新阶段
        from_tier: 原分配等级
        to_tier: 新分配等级
        reason: 原因
        triggered_by: 触发方式 (auto/manual)
        approved_by: 审批人 (如需)
        timestamp: 时间戳
    """

    strategy_id: str
    from_stage: LifecycleStage
    to_stage: LifecycleStage
    from_tier: AllocationTier
    to_tier: AllocationTier
    reason: str
    triggered_by: str = "auto"
    approved_by: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式."""
        return {
            "event_type": "STRATEGY_TRANSITION",
            "strategy_id": self.strategy_id,
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "from_tier": self.from_tier.value,
            "to_tier": self.to_tier.value,
            "reason": self.reason,
            "triggered_by": self.triggered_by,
            "approved_by": self.approved_by,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AllocationResult:
    """资金分配结果.

    属性:
        strategy_id: 策略ID
        allowed: 是否允许分配
        config: 分配配置
        actual_capital_pct: 实际资金占比
        reason: 原因
        requires_approval: 是否需要审批
    """

    strategy_id: str
    allowed: bool
    config: AllocationConfig
    actual_capital_pct: float
    reason: str
    requires_approval: bool = False


class StrategyLifecycleManager:
    """策略生命周期管理器 (军规 M18/M12/M19).

    实现策略从孵化到退役的全生命周期管理，
    包括资金分配、自动晋升/降级、表现监控。

    功能:
    - 策略注册与状态管理
    - 成熟度与资金分配联动
    - 自动晋升/降级机制
    - 表现监控与告警
    - 审计日志记录

    示例:
        >>> manager = StrategyLifecycleManager()
        >>> manager.register_strategy("ppo_v1", "PPO策略", "rl")
        >>> manager.update_maturity("ppo_v1", 0.85)
        >>> allocation = manager.get_allocation("ppo_v1")
    """

    # 晋升/降级阈值
    PROMOTION_MATURITY_THRESHOLD: ClassVar[float] = 0.80  # 晋升门槛
    DEMOTION_SHARPE_THRESHOLD: ClassVar[float] = 0.5  # 降级门槛 (夏普)
    DEMOTION_DRAWDOWN_THRESHOLD: ClassVar[float] = 0.15  # 降级门槛 (回撤)
    SUSPENSION_DRAWDOWN_THRESHOLD: ClassVar[float] = 0.25  # 暂停门槛 (回撤)

    # 军规: 大额调整需审批
    MANUAL_APPROVAL_TIER_CHANGE: ClassVar[int] = 2  # 跨越2级以上需审批

    def __init__(
        self,
        auto_transition: bool = True,
        require_approval_for_production: bool = True,
    ) -> None:
        """初始化生命周期管理器.

        参数:
            auto_transition: 是否启用自动转换
            require_approval_for_production: 进入生产期是否需要审批
        """
        self._auto_transition = auto_transition
        self._require_approval_for_production = require_approval_for_production

        # 策略状态存储
        self._strategies: dict[str, StrategyState] = {}

        # 待审批转换
        self._pending_transitions: dict[str, TransitionEvent] = {}

        # 转换历史
        self._transition_history: list[TransitionEvent] = []

        # 回调函数
        self._on_transition_callbacks: list[Callable[[TransitionEvent], None]] = []
        self._on_alert_callbacks: list[Callable[[str, str], None]] = []

        # 统计
        self._promotion_count: int = 0
        self._demotion_count: int = 0

    # ============================================================
    # 策略注册
    # ============================================================

    def register_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        strategy_type: str,
        initial_stage: LifecycleStage = LifecycleStage.INCUBATION,
        metadata: dict[str, Any] | None = None,
    ) -> StrategyState:
        """注册新策略.

        参数:
            strategy_id: 策略ID
            strategy_name: 策略名称
            strategy_type: 策略类型 (如 "rl", "dl", "statistical")
            initial_stage: 初始阶段
            metadata: 元数据

        返回:
            策略状态
        """
        if strategy_id in self._strategies:
            return self._strategies[strategy_id]

        state = StrategyState(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
            stage=initial_stage,
            allocation_tier=self._stage_to_tier(initial_stage),
            metadata=metadata or {},
        )

        self._strategies[strategy_id] = state
        return state

    def unregister_strategy(self, strategy_id: str) -> bool:
        """注销策略.

        参数:
            strategy_id: 策略ID

        返回:
            是否成功
        """
        if strategy_id in self._strategies:
            # 先转换到退役期
            state = self._strategies[strategy_id]
            if state.stage != LifecycleStage.RETIRED:
                self._execute_transition(
                    strategy_id,
                    LifecycleStage.RETIRED,
                    AllocationTier.ZERO,
                    "策略注销",
                    "manual",
                )
            del self._strategies[strategy_id]
            return True
        return False

    def get_strategy(self, strategy_id: str) -> StrategyState | None:
        """获取策略状态.

        参数:
            strategy_id: 策略ID

        返回:
            策略状态，不存在则返回None
        """
        return self._strategies.get(strategy_id)

    def get_all_strategies(self) -> list[StrategyState]:
        """获取所有策略."""
        return list(self._strategies.values())

    # ============================================================
    # 成熟度更新与自动转换
    # ============================================================

    def update_maturity(
        self,
        strategy_id: str,
        maturity_pct: float,
        auto_transition: bool | None = None,
    ) -> TransitionEvent | None:
        """更新策略成熟度.

        参数:
            strategy_id: 策略ID
            maturity_pct: 成熟度百分比 (0-1)
            auto_transition: 是否自动转换 (None=使用默认)

        返回:
            转换事件 (如有转换)
        """
        state = self._strategies.get(strategy_id)
        if state is None:
            return None

        state.maturity_pct = max(0.0, min(1.0, maturity_pct))

        # 检查是否需要自动转换
        should_auto = (
            auto_transition if auto_transition is not None else self._auto_transition
        )
        if should_auto:
            return self._check_and_transition(strategy_id, "maturity_update")

        return None

    def update_performance(
        self,
        strategy_id: str,
        sharpe_ratio: float | None = None,
        max_drawdown: float | None = None,
        win_rate: float | None = None,
        profit_factor: float | None = None,
        daily_pnl: list[float] | None = None,
        trade_count: int | None = None,
    ) -> TransitionEvent | None:
        """更新策略表现.

        参数:
            strategy_id: 策略ID
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率
            profit_factor: 盈亏比
            daily_pnl: 日盈亏列表
            trade_count: 交易次数

        返回:
            转换事件 (如有转换)
        """
        state = self._strategies.get(strategy_id)
        if state is None:
            return None

        perf = state.performance
        if sharpe_ratio is not None:
            perf.sharpe_ratio = sharpe_ratio
        if max_drawdown is not None:
            perf.max_drawdown = max_drawdown
        if win_rate is not None:
            perf.win_rate = win_rate
        if profit_factor is not None:
            perf.profit_factor = profit_factor
        if daily_pnl is not None:
            perf.daily_pnl = daily_pnl
        if trade_count is not None:
            perf.trade_count = trade_count
        perf.last_updated = datetime.now()  # noqa: DTZ005

        # 检查是否需要降级
        if self._auto_transition:
            return self._check_and_transition(strategy_id, "performance_update")

        return None

    def _check_and_transition(
        self,
        strategy_id: str,
        trigger_reason: str,
    ) -> TransitionEvent | None:
        """检查并执行自动转换.

        参数:
            strategy_id: 策略ID
            trigger_reason: 触发原因

        返回:
            转换事件 (如有转换)
        """
        state = self._strategies.get(strategy_id)
        if state is None:
            return None

        current_stage = state.stage
        new_stage = current_stage
        reason = ""

        # 1. 检查晋升条件
        if state.maturity_pct >= self.PROMOTION_MATURITY_THRESHOLD:
            if current_stage == LifecycleStage.INCUBATION:
                new_stage = LifecycleStage.DEVELOPMENT
                reason = f"成熟度达到 {state.maturity_pct:.1%}，从孵化期晋升到发展期"
            elif current_stage == LifecycleStage.DEVELOPMENT:
                new_stage = LifecycleStage.VALIDATION
                reason = f"成熟度达到 {state.maturity_pct:.1%}，进入验证期"
            elif current_stage == LifecycleStage.VALIDATION:
                # 进入生产期需要额外检查
                if self._can_enter_production(state):
                    new_stage = LifecycleStage.PRODUCTION
                    reason = f"成熟度 {state.maturity_pct:.1%}，表现优异，晋升到生产期"

        # 2. 检查降级条件 (仅生产期/验证期策略)
        if current_stage in [LifecycleStage.PRODUCTION, LifecycleStage.VALIDATION]:
            perf = state.performance
            if perf.max_drawdown >= self.SUSPENSION_DRAWDOWN_THRESHOLD:
                new_stage = LifecycleStage.SUSPENDED
                reason = f"最大回撤 {perf.max_drawdown:.1%} 超过暂停阈值，策略暂停"
            elif (
                perf.max_drawdown >= self.DEMOTION_DRAWDOWN_THRESHOLD
                or perf.sharpe_ratio < self.DEMOTION_SHARPE_THRESHOLD
            ):
                new_stage = LifecycleStage.DEGRADED
                reason = f"表现下滑 (夏普={perf.sharpe_ratio:.2f}, 回撤={perf.max_drawdown:.1%})，降级处理"

        # 3. 检查恢复条件 (降级期策略)
        if current_stage == LifecycleStage.DEGRADED:
            perf = state.performance
            if (
                perf.sharpe_ratio >= 1.0
                and perf.max_drawdown < self.DEMOTION_DRAWDOWN_THRESHOLD
            ):
                new_stage = LifecycleStage.VALIDATION
                reason = f"表现恢复 (夏普={perf.sharpe_ratio:.2f})，恢复到验证期"

        # 4. 执行转换
        if new_stage != current_stage:
            new_tier = self._stage_to_tier(new_stage)

            # 检查是否需要审批
            tier_diff = abs(
                list(AllocationTier).index(new_tier)
                - list(AllocationTier).index(state.allocation_tier)
            )
            needs_approval = tier_diff >= self.MANUAL_APPROVAL_TIER_CHANGE or (
                new_stage == LifecycleStage.PRODUCTION
                and self._require_approval_for_production
            )

            if needs_approval:
                # 创建待审批转换
                event = TransitionEvent(
                    strategy_id=strategy_id,
                    from_stage=current_stage,
                    to_stage=new_stage,
                    from_tier=state.allocation_tier,
                    to_tier=new_tier,
                    reason=reason,
                    triggered_by="auto_pending",
                )
                self._pending_transitions[strategy_id] = event
                self._notify_alert(
                    strategy_id,
                    f"策略 {state.strategy_name} 需要审批: {reason}",
                )
                return event

            # 直接执行转换
            return self._execute_transition(
                strategy_id, new_stage, new_tier, reason, "auto"
            )

        return None

    def _can_enter_production(self, state: StrategyState) -> bool:
        """检查是否可以进入生产期.

        参数:
            state: 策略状态

        返回:
            是否可以
        """
        perf = state.performance
        return (
            state.maturity_pct >= self.PROMOTION_MATURITY_THRESHOLD
            and perf.sharpe_ratio >= 1.0
            and perf.max_drawdown < self.DEMOTION_DRAWDOWN_THRESHOLD
            and perf.win_rate >= 0.45
        )

    def _execute_transition(
        self,
        strategy_id: str,
        new_stage: LifecycleStage,
        new_tier: AllocationTier,
        reason: str,
        triggered_by: str,
        approved_by: str | None = None,
    ) -> TransitionEvent:
        """执行状态转换.

        参数:
            strategy_id: 策略ID
            new_stage: 新阶段
            new_tier: 新分配等级
            reason: 原因
            triggered_by: 触发方式
            approved_by: 审批人

        返回:
            转换事件
        """
        state = self._strategies[strategy_id]

        event = TransitionEvent(
            strategy_id=strategy_id,
            from_stage=state.stage,
            to_stage=new_stage,
            from_tier=state.allocation_tier,
            to_tier=new_tier,
            reason=reason,
            triggered_by=triggered_by,
            approved_by=approved_by,
        )

        # 更新状态
        old_stage = state.stage
        state.stage = new_stage
        state.allocation_tier = new_tier
        state.last_stage_change = datetime.now()  # noqa: DTZ005

        # 更新统计
        if self._is_promotion(old_stage, new_stage):
            state.promotion_count += 1
            self._promotion_count += 1
        elif self._is_demotion(old_stage, new_stage):
            state.demotion_count += 1
            self._demotion_count += 1

        # 记录历史
        self._transition_history.append(event)

        # 通知回调
        self._notify_transition(event)

        # 移除待审批
        if strategy_id in self._pending_transitions:
            del self._pending_transitions[strategy_id]

        return event

    def _is_promotion(
        self, from_stage: LifecycleStage, to_stage: LifecycleStage
    ) -> bool:
        """检查是否为晋升."""
        stages = list(LifecycleStage)
        return stages.index(to_stage) > stages.index(from_stage) and to_stage not in [
            LifecycleStage.DEGRADED,
            LifecycleStage.SUSPENDED,
            LifecycleStage.RETIRED,
        ]

    def _is_demotion(
        self, from_stage: LifecycleStage, to_stage: LifecycleStage
    ) -> bool:
        """检查是否为降级."""
        return to_stage in [LifecycleStage.DEGRADED, LifecycleStage.SUSPENDED]

    def _stage_to_tier(self, stage: LifecycleStage) -> AllocationTier:
        """阶段到分配等级的映射."""
        mapping = {
            LifecycleStage.INCUBATION: AllocationTier.ZERO,
            LifecycleStage.DEVELOPMENT: AllocationTier.ZERO,
            LifecycleStage.VALIDATION: AllocationTier.TRIAL,
            LifecycleStage.PRODUCTION: AllocationTier.NORMAL,
            LifecycleStage.DEGRADED: AllocationTier.MINIMAL,
            LifecycleStage.SUSPENDED: AllocationTier.ZERO,
            LifecycleStage.RETIRED: AllocationTier.ZERO,
        }
        return mapping.get(stage, AllocationTier.ZERO)

    # ============================================================
    # 资金分配
    # ============================================================

    def get_allocation(self, strategy_id: str) -> AllocationResult:
        """获取策略资金分配.

        参数:
            strategy_id: 策略ID

        返回:
            分配结果
        """
        state = self._strategies.get(strategy_id)
        if state is None:
            return AllocationResult(
                strategy_id=strategy_id,
                allowed=False,
                config=ALLOCATION_CONFIGS[AllocationTier.ZERO],
                actual_capital_pct=0.0,
                reason="策略未注册",
            )

        config = ALLOCATION_CONFIGS[state.allocation_tier]

        # 根据成熟度微调分配
        if state.stage == LifecycleStage.PRODUCTION:
            # 生产期策略根据成熟度在 NORMAL 到 MAXIMUM 之间调整
            if state.maturity_pct >= 0.95 and state.performance.sharpe_ratio >= 2.0:
                config = ALLOCATION_CONFIGS[AllocationTier.MAXIMUM]
            elif state.maturity_pct >= 0.90 and state.performance.sharpe_ratio >= 1.5:
                config = ALLOCATION_CONFIGS[AllocationTier.ENHANCED]

        return AllocationResult(
            strategy_id=strategy_id,
            allowed=config.max_capital_pct > 0,
            config=config,
            actual_capital_pct=config.max_capital_pct,
            reason=f"阶段: {state.stage.value}, 等级: {state.allocation_tier.value}",
        )

    def calculate_allocation(
        self,
        strategy_id: str,
        maturity_pct: float,
        sharpe_ratio: float = 0.0,
    ) -> AllocationResult:
        """计算策略资金分配 (基于成熟度).

        参数:
            strategy_id: 策略ID
            maturity_pct: 成熟度百分比
            sharpe_ratio: 夏普比率

        返回:
            分配结果
        """
        # 更新成熟度
        self.update_maturity(strategy_id, maturity_pct)
        if sharpe_ratio > 0:
            self.update_performance(strategy_id, sharpe_ratio=sharpe_ratio)

        return self.get_allocation(strategy_id)

    # ============================================================
    # 人工审批
    # ============================================================

    def approve_transition(
        self,
        strategy_id: str,
        approver: str,
    ) -> TransitionEvent | None:
        """审批待处理转换.

        参数:
            strategy_id: 策略ID
            approver: 审批人

        返回:
            转换事件
        """
        pending = self._pending_transitions.get(strategy_id)
        if pending is None:
            return None

        return self._execute_transition(
            strategy_id,
            pending.to_stage,
            pending.to_tier,
            pending.reason,
            "manual_approved",
            approver,
        )

    def reject_transition(
        self,
        strategy_id: str,
        rejector: str,
        reason: str,
    ) -> bool:
        """拒绝待处理转换.

        参数:
            strategy_id: 策略ID
            rejector: 拒绝人
            reason: 拒绝原因

        返回:
            是否成功
        """
        if strategy_id in self._pending_transitions:
            del self._pending_transitions[strategy_id]
            state = self._strategies.get(strategy_id)
            if state:
                state.notes.append(f"转换被 {rejector} 拒绝: {reason}")
            return True
        return False

    def get_pending_transitions(self) -> list[TransitionEvent]:
        """获取所有待审批转换."""
        return list(self._pending_transitions.values())

    # ============================================================
    # 回调与通知
    # ============================================================

    def register_transition_callback(
        self,
        callback: Callable[[TransitionEvent], None],
    ) -> None:
        """注册转换回调."""
        self._on_transition_callbacks.append(callback)

    def register_alert_callback(
        self,
        callback: Callable[[str, str], None],
    ) -> None:
        """注册告警回调."""
        self._on_alert_callbacks.append(callback)

    def _notify_transition(self, event: TransitionEvent) -> None:
        """通知转换."""
        for callback in self._on_transition_callbacks:
            try:
                callback(event)
            except Exception:
                pass  # 回调错误不影响主流程

    def _notify_alert(self, strategy_id: str, message: str) -> None:
        """发送告警."""
        for callback in self._on_alert_callbacks:
            try:
                callback(strategy_id, message)
            except Exception:
                pass

    # ============================================================
    # 统计与查询
    # ============================================================

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        stage_counts: dict[str, int] = {}
        tier_counts: dict[str, int] = {}

        for state in self._strategies.values():
            stage_counts[state.stage.value] = stage_counts.get(state.stage.value, 0) + 1
            tier_counts[state.allocation_tier.value] = (
                tier_counts.get(state.allocation_tier.value, 0) + 1
            )

        return {
            "total_strategies": len(self._strategies),
            "stage_distribution": stage_counts,
            "tier_distribution": tier_counts,
            "total_promotions": self._promotion_count,
            "total_demotions": self._demotion_count,
            "pending_approvals": len(self._pending_transitions),
            "transition_history_count": len(self._transition_history),
        }

    def get_strategies_by_stage(self, stage: LifecycleStage) -> list[StrategyState]:
        """按阶段获取策略."""
        return [s for s in self._strategies.values() if s.stage == stage]

    def get_strategies_by_tier(self, tier: AllocationTier) -> list[StrategyState]:
        """按分配等级获取策略."""
        return [s for s in self._strategies.values() if s.allocation_tier == tier]

    def get_transition_history(
        self,
        strategy_id: str | None = None,
        limit: int = 100,
    ) -> list[TransitionEvent]:
        """获取转换历史.

        参数:
            strategy_id: 策略ID (None=全部)
            limit: 限制数量

        返回:
            转换事件列表
        """
        if strategy_id:
            history = [
                e for e in self._transition_history if e.strategy_id == strategy_id
            ]
        else:
            history = self._transition_history

        return history[-limit:]

    def reset(self) -> None:
        """重置管理器."""
        self._strategies.clear()
        self._pending_transitions.clear()
        self._transition_history.clear()
        self._promotion_count = 0
        self._demotion_count = 0


# ============================================================
# 便捷函数
# ============================================================


def create_lifecycle_manager(
    auto_transition: bool = True,
    require_approval: bool = True,
) -> StrategyLifecycleManager:
    """创建生命周期管理器.

    参数:
        auto_transition: 是否启用自动转换
        require_approval: 进入生产期是否需要审批

    返回:
        生命周期管理器实例
    """
    return StrategyLifecycleManager(
        auto_transition=auto_transition,
        require_approval_for_production=require_approval,
    )


def get_allocation_for_maturity(maturity_pct: float) -> AllocationConfig:
    """根据成熟度获取分配配置.

    参数:
        maturity_pct: 成熟度百分比

    返回:
        分配配置
    """
    if maturity_pct < 0.40 or maturity_pct < 0.60:
        return ALLOCATION_CONFIGS[AllocationTier.ZERO]
    if maturity_pct < 0.80:
        return ALLOCATION_CONFIGS[AllocationTier.TRIAL]
    if maturity_pct < 0.90:
        return ALLOCATION_CONFIGS[AllocationTier.NORMAL]
    if maturity_pct < 0.95:
        return ALLOCATION_CONFIGS[AllocationTier.ENHANCED]
    return ALLOCATION_CONFIGS[AllocationTier.MAXIMUM]
