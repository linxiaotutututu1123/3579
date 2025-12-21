"""
分层确认机制实现.

V4PRO Platform Component - Execution Confirmation System
军规覆盖: M5(成本先行), M6(熔断保护), M12(双重确认), M13(涨跌停感知)

V4PRO Scenarios:
- CONFIRMATION.LEVEL_AUTO: 全自动确认(无需人工)
- CONFIRMATION.LEVEL_SOFT: 软确认(系统二次校验)
- CONFIRMATION.LEVEL_HARD: 硬确认(人工介入)

设计原则:
- 解决M12与全自动矛盾: 分层确认机制
- 夜盘时段(21:00-02:30)无人值守: 降级处理
- 高频套利(秒级决策): AUTO级别
- 极端行情: 快速响应与确认并存
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.execution.order_types import OrderIntent


class ConfirmationLevel(str, Enum):
    """确认级别枚举.

    V4PRO Scenario: CONFIRMATION.LEVEL_*
    军规覆盖: M12(双重确认)

    Attributes:
        AUTO: 全自动确认, 无需人工介入
        SOFT_CONFIRM: 软确认, 系统自动二次校验
        HARD_CONFIRM: 硬确认, 需要人工介入
    """

    AUTO = "全自动"
    SOFT_CONFIRM = "软确认"
    HARD_CONFIRM = "硬确认"


class ConfirmationResult(str, Enum):
    """确认结果枚举.

    Attributes:
        APPROVED: 确认通过
        REJECTED: 确认拒绝
        TIMEOUT: 确认超时
        DEGRADED: 降级处理
    """

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    TIMEOUT = "TIMEOUT"
    DEGRADED = "DEGRADED"


class SessionType(str, Enum):
    """交易时段类型.

    军规覆盖: M15(夜盘规则)

    Attributes:
        DAY_SESSION: 日盘 (09:00-15:00)
        NIGHT_SESSION: 夜盘 (21:00-02:30)
        VOLATILE_PERIOD: 波动时段 (开盘/收盘前后)
    """

    DAY_SESSION = "DAY_SESSION"
    NIGHT_SESSION = "NIGHT_SESSION"
    VOLATILE_PERIOD = "VOLATILE_PERIOD"


class StrategyType(str, Enum):
    """策略类型.

    Attributes:
        HIGH_FREQUENCY: 高频策略
        PRODUCTION: 生产策略
        EXPERIMENTAL: 实验策略
    """

    HIGH_FREQUENCY = "HIGH_FREQUENCY"
    PRODUCTION = "PRODUCTION"
    EXPERIMENTAL = "EXPERIMENTAL"


@dataclass(frozen=True)
class OrderValueThresholds:
    """订单金额阈值配置.

    军规覆盖: M12(大额订单双重确认)

    Attributes:
        auto_max: 全自动最大金额 (<50万)
        soft_confirm_max: 软确认最大金额 (50万-200万)
    """

    auto_max: float = 500_000  # <50万: 全自动
    soft_confirm_max: float = 2_000_000  # 50万-200万: 软确认
    # >200万: 硬确认 (隐含)


@dataclass(frozen=True)
class MarketConditionThresholds:
    """市场条件阈值配置.

    军规覆盖: M6(熔断保护), M13(涨跌停感知)

    Attributes:
        volatility_pct: 波动率阈值 (>5%触发确认)
        price_gap_pct: 跳空阈值 (>3%触发确认)
        limit_hit_count: 连续涨跌停次数阈值 (>=2触发确认)
    """

    volatility_pct: float = 0.05  # 波动率>5%触发确认
    price_gap_pct: float = 0.03  # 跳空>3%触发确认
    limit_hit_count: int = 2  # 连续涨跌停>=2次触发确认


@dataclass
class MarketCondition:
    """当前市场条件.

    用于确认级别判断的市场状态快照。

    Attributes:
        current_volatility_pct: 当前波动率 (0.0-1.0)
        price_gap_pct: 当前跳空幅度 (0.0-1.0)
        limit_hit_count: 连续涨跌停次数
        is_limit_up: 是否涨停
        is_limit_down: 是否跌停
    """

    current_volatility_pct: float = 0.0
    price_gap_pct: float = 0.0
    limit_hit_count: int = 0
    is_limit_up: bool = False
    is_limit_down: bool = False


@dataclass
class ConfirmationConfig:
    """确认机制配置.

    军规覆盖: M5, M6, M12, M13

    Attributes:
        order_thresholds: 订单金额阈值
        market_thresholds: 市场条件阈值
        soft_confirm_timeout_seconds: 软确认超时(秒)
        hard_confirm_timeout_seconds: 硬确认超时(秒)
        enable_night_session_degradation: 夜盘超时是否降级
    """

    order_thresholds: OrderValueThresholds = field(
        default_factory=OrderValueThresholds
    )
    market_thresholds: MarketConditionThresholds = field(
        default_factory=MarketConditionThresholds
    )
    soft_confirm_timeout_seconds: float = 5.0
    hard_confirm_timeout_seconds: float = 30.0
    enable_night_session_degradation: bool = True


# Session rules mapping
SESSION_RULES: dict[SessionType, ConfirmationLevel] = {
    SessionType.DAY_SESSION: ConfirmationLevel.AUTO,
    SessionType.NIGHT_SESSION: ConfirmationLevel.SOFT_CONFIRM,
    SessionType.VOLATILE_PERIOD: ConfirmationLevel.HARD_CONFIRM,
}

# Strategy rules mapping
STRATEGY_RULES: dict[StrategyType, ConfirmationLevel] = {
    StrategyType.HIGH_FREQUENCY: ConfirmationLevel.AUTO,
    StrategyType.PRODUCTION: ConfirmationLevel.SOFT_CONFIRM,
    StrategyType.EXPERIMENTAL: ConfirmationLevel.HARD_CONFIRM,
}


@dataclass
class ConfirmationContext:
    """确认上下文.

    包含确认决策所需的全部信息。

    Attributes:
        order_intent: 订单意图
        order_value: 订单估算金额
        market_condition: 市场条件
        session_type: 交易时段
        strategy_type: 策略类型
        timestamp: 时间戳
    """

    order_intent: OrderIntent
    order_value: float
    market_condition: MarketCondition
    session_type: SessionType
    strategy_type: StrategyType
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典(用于审计日志)."""
        return {
            "order_intent": {
                "symbol": self.order_intent.symbol,
                "side": self.order_intent.side.value,
                "offset": self.order_intent.offset.value,
                "price": self.order_intent.price,
                "qty": self.order_intent.qty,
                "reason": self.order_intent.reason,
            },
            "order_value": self.order_value,
            "market_condition": {
                "volatility_pct": self.market_condition.current_volatility_pct,
                "price_gap_pct": self.market_condition.price_gap_pct,
                "limit_hit_count": self.market_condition.limit_hit_count,
                "is_limit_up": self.market_condition.is_limit_up,
                "is_limit_down": self.market_condition.is_limit_down,
            },
            "session_type": self.session_type.value,
            "strategy_type": self.strategy_type.value,
            "timestamp": self.timestamp,
        }


@dataclass
class ConfirmationDecision:
    """确认决策结果.

    Attributes:
        level: 确认级别
        result: 确认结果
        reasons: 决策原因列表
        checks_passed: 通过的检查项
        checks_failed: 失败的检查项
        timestamp: 决策时间戳
        elapsed_seconds: 确认耗时(秒)
    """

    level: ConfirmationLevel
    result: ConfirmationResult
    reasons: list[str] = field(default_factory=list)
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    elapsed_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典(用于审计日志)."""
        return {
            "level": self.level.value,
            "result": self.result.value,
            "reasons": self.reasons,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "timestamp": self.timestamp,
            "elapsed_seconds": self.elapsed_seconds,
        }


class ConfirmationAuditEventType(str, Enum):
    """确认审计事件类型.

    军规覆盖: M3(完整审计)
    """

    CONFIRMATION_STARTED = "CONFIRMATION.STARTED"
    CONFIRMATION_LEVEL_DETERMINED = "CONFIRMATION.LEVEL_DETERMINED"
    SOFT_CONFIRM_STARTED = "CONFIRMATION.SOFT.STARTED"
    SOFT_CONFIRM_RISK_CHECK = "CONFIRMATION.SOFT.RISK_CHECK"
    SOFT_CONFIRM_COST_CHECK = "CONFIRMATION.SOFT.COST_CHECK"
    SOFT_CONFIRM_LIMIT_CHECK = "CONFIRMATION.SOFT.LIMIT_CHECK"
    SOFT_CONFIRM_COMPLETED = "CONFIRMATION.SOFT.COMPLETED"
    SOFT_CONFIRM_TIMEOUT = "CONFIRMATION.SOFT.TIMEOUT"
    HARD_CONFIRM_STARTED = "CONFIRMATION.HARD.STARTED"
    HARD_CONFIRM_ALERT_SENT = "CONFIRMATION.HARD.ALERT_SENT"
    HARD_CONFIRM_USER_RESPONSE = "CONFIRMATION.HARD.USER_RESPONSE"
    HARD_CONFIRM_TIMEOUT = "CONFIRMATION.HARD.TIMEOUT"
    HARD_CONFIRM_DEGRADED = "CONFIRMATION.HARD.DEGRADED"
    HARD_CONFIRM_CIRCUIT_BREAK = "CONFIRMATION.HARD.CIRCUIT_BREAK"
    CONFIRMATION_COMPLETED = "CONFIRMATION.COMPLETED"


@dataclass
class ConfirmationAuditEvent:
    """确认审计事件.

    军规覆盖: M3(完整审计)

    Attributes:
        event_type: 事件类型
        confirmation_id: 确认ID
        ts: 时间戳(毫秒)
        level: 确认级别
        result: 确认结果
        context: 上下文信息
        reason: 事件说明
        metadata: 扩展元数据
    """

    event_type: ConfirmationAuditEventType
    confirmation_id: str
    ts: int = field(default_factory=lambda: int(time.time() * 1000))
    level: str = ""
    result: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典(用于JSONL序列化)."""
        return {
            "event_type": self.event_type.value,
            "confirmation_id": self.confirmation_id,
            "ts": self.ts,
            "level": self.level,
            "result": self.result,
            "context": self.context,
            "reason": self.reason,
            "metadata": self.metadata,
        }


# Type aliases for callbacks
AlertCallback = Callable[[str, str, dict[str, Any]], Awaitable[None]]
AuditCallback = Callable[[ConfirmationAuditEvent], None]
RiskCheckCallback = Callable[[ConfirmationContext], Awaitable[bool]]
CostCheckCallback = Callable[[ConfirmationContext], Awaitable[bool]]
LimitCheckCallback = Callable[[ConfirmationContext], Awaitable[bool]]
UserConfirmCallback = Callable[[str, ConfirmationContext], Awaitable[bool]]


def get_current_session_type() -> SessionType:
    """获取当前交易时段类型.

    Returns:
        当前时段类型

    军规覆盖: M15(夜盘规则)
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute

    # 夜盘: 21:00-23:59, 00:00-02:30
    if time_val >= 2100 or time_val <= 230:
        return SessionType.NIGHT_SESSION

    # 日盘波动时段: 开盘前后15分钟, 收盘前后15分钟
    # 开盘: 09:00, 收盘: 15:00
    if (845 <= time_val <= 915) or (1445 <= time_val <= 1515):
        return SessionType.VOLATILE_PERIOD

    # 日盘正常时段
    if 900 <= time_val <= 1500:
        return SessionType.DAY_SESSION

    # 非交易时段按日盘处理
    return SessionType.DAY_SESSION


def determine_confirmation_level(
    context: ConfirmationContext,
    config: ConfirmationConfig,
) -> tuple[ConfirmationLevel, list[str]]:
    """确定确认级别.

    根据订单金额、市场条件、时段规则、策略规则综合判断。
    取各维度中最高级别作为最终确认级别。

    Args:
        context: 确认上下文
        config: 确认配置

    Returns:
        (确认级别, 决策原因列表)

    军规覆盖: M5, M6, M12, M13
    """
    levels: list[tuple[ConfirmationLevel, str]] = []

    # 1. 订单金额阈值判断 (M12)
    order_value = context.order_value
    thresholds = config.order_thresholds
    if order_value < thresholds.auto_max:
        levels.append((ConfirmationLevel.AUTO, f"订单金额{order_value:.0f}<{thresholds.auto_max:.0f}: AUTO"))
    elif order_value < thresholds.soft_confirm_max:
        levels.append((ConfirmationLevel.SOFT_CONFIRM, f"订单金额{order_value:.0f}在[{thresholds.auto_max:.0f},{thresholds.soft_confirm_max:.0f}): SOFT"))
    else:
        levels.append((ConfirmationLevel.HARD_CONFIRM, f"订单金额{order_value:.0f}>={thresholds.soft_confirm_max:.0f}: HARD"))

    # 2. 市场条件阈值判断 (M6, M13)
    market = context.market_condition
    market_thresholds = config.market_thresholds

    if market.current_volatility_pct > market_thresholds.volatility_pct:
        levels.append((ConfirmationLevel.SOFT_CONFIRM, f"波动率{market.current_volatility_pct:.2%}>{market_thresholds.volatility_pct:.2%}: SOFT"))

    if market.price_gap_pct > market_thresholds.price_gap_pct:
        levels.append((ConfirmationLevel.SOFT_CONFIRM, f"跳空{market.price_gap_pct:.2%}>{market_thresholds.price_gap_pct:.2%}: SOFT"))

    if market.limit_hit_count >= market_thresholds.limit_hit_count:
        levels.append((ConfirmationLevel.HARD_CONFIRM, f"连续涨跌停{market.limit_hit_count}>={market_thresholds.limit_hit_count}: HARD"))

    if market.is_limit_up or market.is_limit_down:
        levels.append((ConfirmationLevel.SOFT_CONFIRM, f"当前{'涨停' if market.is_limit_up else '跌停'}: SOFT"))

    # 3. 时段规则判断
    session_level = SESSION_RULES.get(context.session_type, ConfirmationLevel.AUTO)
    if session_level != ConfirmationLevel.AUTO:
        levels.append((session_level, f"时段{context.session_type.value}: {session_level.value}"))

    # 4. 策略规则判断
    strategy_level = STRATEGY_RULES.get(context.strategy_type, ConfirmationLevel.SOFT_CONFIRM)
    levels.append((strategy_level, f"策略{context.strategy_type.value}: {strategy_level.value}"))

    # 取最高级别
    level_priority = {
        ConfirmationLevel.AUTO: 0,
        ConfirmationLevel.SOFT_CONFIRM: 1,
        ConfirmationLevel.HARD_CONFIRM: 2,
    }

    max_level = ConfirmationLevel.AUTO
    reasons = []
    for level, reason in levels:
        reasons.append(reason)
        if level_priority[level] > level_priority[max_level]:
            max_level = level

    return max_level, reasons


class BaseConfirmation(ABC):
    """确认基类.

    定义确认流程的抽象接口。
    """

    def __init__(
        self,
        config: ConfirmationConfig,
        audit_callback: AuditCallback | None = None,
    ):
        """初始化确认器.

        Args:
            config: 确认配置
            audit_callback: 审计回调函数
        """
        self.config = config
        self._audit_callback = audit_callback

    def _emit_audit(self, event: ConfirmationAuditEvent) -> None:
        """发送审计事件.

        Args:
            event: 审计事件
        """
        if self._audit_callback:
            self._audit_callback(event)

    @abstractmethod
    async def confirm(
        self,
        confirmation_id: str,
        context: ConfirmationContext,
    ) -> ConfirmationDecision:
        """执行确认流程.

        Args:
            confirmation_id: 确认ID
            context: 确认上下文

        Returns:
            确认决策结果
        """


class SoftConfirmation(BaseConfirmation):
    """软确认实现.

    V4PRO Scenario: CONFIRMATION.LEVEL_SOFT

    执行系统二次校验:
    - 风控重检
    - 成本重算
    - 涨跌停重检
    - 5秒超时自动通过

    军规覆盖: M5(成本先行), M6(风控), M12(双重确认), M13(涨跌停)
    """

    def __init__(
        self,
        config: ConfirmationConfig,
        audit_callback: AuditCallback | None = None,
        risk_check: RiskCheckCallback | None = None,
        cost_check: CostCheckCallback | None = None,
        limit_check: LimitCheckCallback | None = None,
    ):
        """初始化软确认器.

        Args:
            config: 确认配置
            audit_callback: 审计回调
            risk_check: 风控检查回调
            cost_check: 成本检查回调
            limit_check: 涨跌停检查回调
        """
        super().__init__(config, audit_callback)
        self._risk_check = risk_check
        self._cost_check = cost_check
        self._limit_check = limit_check

    async def _default_risk_check(self, context: ConfirmationContext) -> bool:
        """默认风控检查(总是通过)."""
        return True

    async def _default_cost_check(self, context: ConfirmationContext) -> bool:
        """默认成本检查(总是通过)."""
        return True

    async def _default_limit_check(self, context: ConfirmationContext) -> bool:
        """默认涨跌停检查.

        检查当前是否涨跌停，如果是则拒绝。
        """
        market = context.market_condition
        # 涨停时不能买入,跌停时不能卖出
        from src.execution.order_types import Side
        if market.is_limit_up and context.order_intent.side == Side.BUY:
            return False
        if market.is_limit_down and context.order_intent.side == Side.SELL:
            return False
        return True

    async def confirm(
        self,
        confirmation_id: str,
        context: ConfirmationContext,
    ) -> ConfirmationDecision:
        """执行软确认流程.

        Args:
            confirmation_id: 确认ID
            context: 确认上下文

        Returns:
            确认决策结果

        军规覆盖: M5, M6, M12, M13
        """
        start_time = time.time()
        checks_passed = []
        checks_failed = []
        reasons = []

        # 发送开始事件
        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.SOFT_CONFIRM_STARTED,
            confirmation_id=confirmation_id,
            level=ConfirmationLevel.SOFT_CONFIRM.value,
            context=context.to_dict(),
            reason="软确认流程开始",
        ))

        timeout = self.config.soft_confirm_timeout_seconds

        try:
            # 1. 风控重检 (M6)
            risk_check = self._risk_check or self._default_risk_check
            try:
                risk_passed = await asyncio.wait_for(
                    risk_check(context),
                    timeout=timeout / 3,
                )
            except TimeoutError:
                risk_passed = True  # 超时自动通过
                reasons.append("风控检查超时,自动通过")

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.SOFT_CONFIRM_RISK_CHECK,
                confirmation_id=confirmation_id,
                result="PASS" if risk_passed else "FAIL",
                reason=f"风控检查: {'通过' if risk_passed else '失败'}",
            ))

            if risk_passed:
                checks_passed.append("M6_RISK_CHECK")
            else:
                checks_failed.append("M6_RISK_CHECK")
                reasons.append("风控检查失败")

            # 2. 成本重算 (M5)
            cost_check = self._cost_check or self._default_cost_check
            try:
                cost_passed = await asyncio.wait_for(
                    cost_check(context),
                    timeout=timeout / 3,
                )
            except TimeoutError:
                cost_passed = True  # 超时自动通过
                reasons.append("成本检查超时,自动通过")

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.SOFT_CONFIRM_COST_CHECK,
                confirmation_id=confirmation_id,
                result="PASS" if cost_passed else "FAIL",
                reason=f"成本检查: {'通过' if cost_passed else '失败'}",
            ))

            if cost_passed:
                checks_passed.append("M5_COST_CHECK")
            else:
                checks_failed.append("M5_COST_CHECK")
                reasons.append("成本检查失败")

            # 3. 涨跌停重检 (M13)
            limit_check = self._limit_check or self._default_limit_check
            try:
                limit_passed = await asyncio.wait_for(
                    limit_check(context),
                    timeout=timeout / 3,
                )
            except TimeoutError:
                limit_passed = True  # 超时自动通过
                reasons.append("涨跌停检查超时,自动通过")

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.SOFT_CONFIRM_LIMIT_CHECK,
                confirmation_id=confirmation_id,
                result="PASS" if limit_passed else "FAIL",
                reason=f"涨跌停检查: {'通过' if limit_passed else '失败'}",
            ))

            if limit_passed:
                checks_passed.append("M13_LIMIT_CHECK")
            else:
                checks_failed.append("M13_LIMIT_CHECK")
                reasons.append("涨跌停检查失败")

            # 综合判断
            all_passed = risk_passed and cost_passed and limit_passed
            elapsed = time.time() - start_time

            result = ConfirmationResult.APPROVED if all_passed else ConfirmationResult.REJECTED

            decision = ConfirmationDecision(
                level=ConfirmationLevel.SOFT_CONFIRM,
                result=result,
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                elapsed_seconds=elapsed,
            )

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.SOFT_CONFIRM_COMPLETED,
                confirmation_id=confirmation_id,
                level=ConfirmationLevel.SOFT_CONFIRM.value,
                result=result.value,
                reason=f"软确认完成: {result.value}",
                metadata=decision.to_dict(),
            ))

            return decision

        except TimeoutError:
            # 整体超时 - 自动通过
            elapsed = time.time() - start_time
            reasons.append(f"软确认超时({timeout}s),自动通过")

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.SOFT_CONFIRM_TIMEOUT,
                confirmation_id=confirmation_id,
                level=ConfirmationLevel.SOFT_CONFIRM.value,
                result=ConfirmationResult.TIMEOUT.value,
                reason=f"软确认超时({timeout}s),自动通过",
            ))

            return ConfirmationDecision(
                level=ConfirmationLevel.SOFT_CONFIRM,
                result=ConfirmationResult.APPROVED,  # 超时自动通过
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                elapsed_seconds=elapsed,
            )


class HardConfirmation(BaseConfirmation):
    """硬确认实现.

    V4PRO Scenario: CONFIRMATION.LEVEL_HARD

    需要人工介入确认:
    - 发送告警通知
    - 30秒超时处理
      - 日盘: 触发熔断
      - 夜盘: 降级为软确认

    军规覆盖: M6(熔断保护), M12(双重确认)
    """

    def __init__(
        self,
        config: ConfirmationConfig,
        audit_callback: AuditCallback | None = None,
        alert_callback: AlertCallback | None = None,
        user_confirm_callback: UserConfirmCallback | None = None,
        soft_confirmation: SoftConfirmation | None = None,
    ):
        """初始化硬确认器.

        Args:
            config: 确认配置
            audit_callback: 审计回调
            alert_callback: 告警发送回调
            user_confirm_callback: 用户确认回调
            soft_confirmation: 软确认器(用于降级)
        """
        super().__init__(config, audit_callback)
        self._alert_callback = alert_callback
        self._user_confirm_callback = user_confirm_callback
        self._soft_confirmation = soft_confirmation or SoftConfirmation(config, audit_callback)

    async def _default_alert(
        self,
        title: str,
        message: str,
        metadata: dict[str, Any],
    ) -> None:
        """默认告警(空实现)."""

    async def _default_user_confirm(
        self,
        confirmation_id: str,
        context: ConfirmationContext,
    ) -> bool:
        """默认用户确认(总是超时)."""
        # 模拟等待用户响应
        await asyncio.sleep(self.config.hard_confirm_timeout_seconds + 1)
        return False

    async def confirm(
        self,
        confirmation_id: str,
        context: ConfirmationContext,
    ) -> ConfirmationDecision:
        """执行硬确认流程.

        Args:
            confirmation_id: 确认ID
            context: 确认上下文

        Returns:
            确认决策结果

        军规覆盖: M6, M12
        """
        start_time = time.time()
        reasons = []
        checks_passed = []
        checks_failed = []

        # 发送开始事件
        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.HARD_CONFIRM_STARTED,
            confirmation_id=confirmation_id,
            level=ConfirmationLevel.HARD_CONFIRM.value,
            context=context.to_dict(),
            reason="硬确认流程开始",
        ))

        # 发送告警通知
        alert_callback = self._alert_callback or self._default_alert
        alert_title = f"[V4PRO] 大额订单确认 - {context.order_intent.symbol}"
        alert_message = (
            f"订单金额: {context.order_value:.0f}\n"
            f"合约: {context.order_intent.symbol}\n"
            f"方向: {context.order_intent.side.value}\n"
            f"数量: {context.order_intent.qty}\n"
            f"价格: {context.order_intent.price}\n"
            f"时段: {context.session_type.value}\n"
            f"请在30秒内确认"
        )

        await alert_callback(alert_title, alert_message, context.to_dict())

        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.HARD_CONFIRM_ALERT_SENT,
            confirmation_id=confirmation_id,
            reason="告警通知已发送",
            metadata={"title": alert_title},
        ))

        # 等待用户确认
        timeout = self.config.hard_confirm_timeout_seconds
        user_confirm = self._user_confirm_callback or self._default_user_confirm

        try:
            user_approved = await asyncio.wait_for(
                user_confirm(confirmation_id, context),
                timeout=timeout,
            )

            elapsed = time.time() - start_time

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.HARD_CONFIRM_USER_RESPONSE,
                confirmation_id=confirmation_id,
                result="APPROVED" if user_approved else "REJECTED",
                reason=f"用户响应: {'批准' if user_approved else '拒绝'}",
            ))

            if user_approved:
                checks_passed.append("M12_USER_CONFIRM")
                reasons.append("用户确认通过")
                result = ConfirmationResult.APPROVED
            else:
                checks_failed.append("M12_USER_CONFIRM")
                reasons.append("用户拒绝确认")
                result = ConfirmationResult.REJECTED

            decision = ConfirmationDecision(
                level=ConfirmationLevel.HARD_CONFIRM,
                result=result,
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                elapsed_seconds=elapsed,
            )

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.CONFIRMATION_COMPLETED,
                confirmation_id=confirmation_id,
                level=ConfirmationLevel.HARD_CONFIRM.value,
                result=result.value,
                reason=f"硬确认完成: {result.value}",
                metadata=decision.to_dict(),
            ))

            return decision

        except TimeoutError:
            # 超时处理
            elapsed = time.time() - start_time

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.HARD_CONFIRM_TIMEOUT,
                confirmation_id=confirmation_id,
                reason=f"硬确认超时({timeout}s)",
            ))

            # 根据时段决定处理方式
            is_night_session = context.session_type == SessionType.NIGHT_SESSION

            if is_night_session and self.config.enable_night_session_degradation:
                # 夜盘降级为软确认
                reasons.append(f"硬确认超时({timeout}s),夜盘降级为软确认")

                self._emit_audit(ConfirmationAuditEvent(
                    event_type=ConfirmationAuditEventType.HARD_CONFIRM_DEGRADED,
                    confirmation_id=confirmation_id,
                    reason="夜盘超时,降级为软确认",
                ))

                # 执行软确认
                soft_decision = await self._soft_confirmation.confirm(
                    confirmation_id, context
                )

                return ConfirmationDecision(
                    level=ConfirmationLevel.HARD_CONFIRM,
                    result=ConfirmationResult.DEGRADED,
                    reasons=reasons + soft_decision.reasons,
                    checks_passed=soft_decision.checks_passed,
                    checks_failed=soft_decision.checks_failed,
                    elapsed_seconds=elapsed + soft_decision.elapsed_seconds,
                )

            # 日盘触发熔断
            reasons.append(f"硬确认超时({timeout}s),日盘触发熔断")
            checks_failed.append("M6_CIRCUIT_BREAKER")

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.HARD_CONFIRM_CIRCUIT_BREAK,
                confirmation_id=confirmation_id,
                reason="日盘超时,触发熔断",
            ))

            return ConfirmationDecision(
                level=ConfirmationLevel.HARD_CONFIRM,
                result=ConfirmationResult.REJECTED,
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                elapsed_seconds=elapsed,
            )


class ConfirmationManager:
    """确认管理器.

    统一管理确认流程,自动选择确认级别并执行。

    军规覆盖: M5, M6, M12, M13
    """

    def __init__(
        self,
        config: ConfirmationConfig | None = None,
        audit_callback: AuditCallback | None = None,
        alert_callback: AlertCallback | None = None,
        risk_check: RiskCheckCallback | None = None,
        cost_check: CostCheckCallback | None = None,
        limit_check: LimitCheckCallback | None = None,
        user_confirm_callback: UserConfirmCallback | None = None,
    ):
        """初始化确认管理器.

        Args:
            config: 确认配置
            audit_callback: 审计回调
            alert_callback: 告警回调
            risk_check: 风控检查回调
            cost_check: 成本检查回调
            limit_check: 涨跌停检查回调
            user_confirm_callback: 用户确认回调
        """
        self.config = config or ConfirmationConfig()
        self._audit_callback = audit_callback

        self._soft_confirmation = SoftConfirmation(
            config=self.config,
            audit_callback=audit_callback,
            risk_check=risk_check,
            cost_check=cost_check,
            limit_check=limit_check,
        )

        self._hard_confirmation = HardConfirmation(
            config=self.config,
            audit_callback=audit_callback,
            alert_callback=alert_callback,
            user_confirm_callback=user_confirm_callback,
            soft_confirmation=self._soft_confirmation,
        )

        self._confirmation_counter = 0

    def _generate_confirmation_id(self) -> str:
        """生成确认ID."""
        self._confirmation_counter += 1
        ts = int(time.time() * 1000)
        return f"CONF-{ts}-{self._confirmation_counter:06d}"

    def _emit_audit(self, event: ConfirmationAuditEvent) -> None:
        """发送审计事件."""
        if self._audit_callback:
            self._audit_callback(event)

    async def confirm(
        self,
        context: ConfirmationContext,
    ) -> ConfirmationDecision:
        """执行确认流程.

        根据上下文自动选择确认级别并执行。

        Args:
            context: 确认上下文

        Returns:
            确认决策结果

        军规覆盖: M5, M6, M12, M13
        """
        confirmation_id = self._generate_confirmation_id()

        # 发送开始事件
        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_STARTED,
            confirmation_id=confirmation_id,
            context=context.to_dict(),
            reason="确认流程开始",
        ))

        # 确定确认级别
        level, reasons = determine_confirmation_level(context, self.config)

        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_LEVEL_DETERMINED,
            confirmation_id=confirmation_id,
            level=level.value,
            reason=f"确认级别: {level.value}",
            metadata={"reasons": reasons},
        ))

        # 执行对应级别的确认
        if level == ConfirmationLevel.AUTO:
            # 全自动直接通过
            decision = ConfirmationDecision(
                level=level,
                result=ConfirmationResult.APPROVED,
                reasons=reasons + ["AUTO级别,自动通过"],
            )

            self._emit_audit(ConfirmationAuditEvent(
                event_type=ConfirmationAuditEventType.CONFIRMATION_COMPLETED,
                confirmation_id=confirmation_id,
                level=level.value,
                result=ConfirmationResult.APPROVED.value,
                reason="AUTO级别,自动通过",
                metadata=decision.to_dict(),
            ))

            return decision

        if level == ConfirmationLevel.SOFT_CONFIRM:
            return await self._soft_confirmation.confirm(confirmation_id, context)

        # HARD_CONFIRM
        return await self._hard_confirmation.confirm(confirmation_id, context)
