"""
分层确认机制增强实现 - 熔断器集成.

V4PRO Platform Component - Execution Confirmation System Enhanced
军规覆盖: M5(成本先行), M6(熔断保护), M12(双重确认), M13(涨跌停感知), M15(夜盘规则), M17(程序化合规)

增强功能 (v1.1):
- 熔断状态感知: 熔断触发时拒绝新订单确认
- 硬确认超时触发熔断: 日盘超时自动触发熔断器
- 高频策略豁免: 基于策略类型和订单特征的豁免逻辑
- 恢复期确认升级: 熔断恢复期自动提升确认级别
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from src.execution.confirmation import (
    AlertCallback,
    AuditCallback,
    ConfirmationAuditEvent,
    ConfirmationAuditEventType,
    ConfirmationConfig,
    ConfirmationContext,
    ConfirmationDecision,
    ConfirmationLevel,
    ConfirmationResult,
    CostCheckCallback,
    HardConfirmation,
    LimitCheckCallback,
    RiskCheckCallback,
    SessionType,
    SoftConfirmation,
    StrategyType,
    UserConfirmCallback,
    determine_confirmation_level,
)


if TYPE_CHECKING:
    from src.guardian.circuit_breaker import CircuitBreaker


# =============================================================================
# Circuit Breaker Integration Types
# =============================================================================


class CircuitBreakerAwareResult(str, Enum):
    """熔断感知确认结果.

    扩展ConfirmationResult以支持熔断状态.

    Attributes:
        CIRCUIT_BREAKER_BLOCKED: 熔断状态下被阻止
        CIRCUIT_BREAKER_TRIGGERED: 确认超时触发熔断
        RECOVERY_PERIOD_UPGRADED: 恢复期确认级别升级
    """
    CIRCUIT_BREAKER_BLOCKED = "CIRCUIT_BREAKER_BLOCKED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"
    RECOVERY_PERIOD_UPGRADED = "RECOVERY_PERIOD_UPGRADED"


class ConfirmationAuditEventTypeExtended(str, Enum):
    """扩展的确认审计事件类型.

    新增熔断相关事件.
    """
    CIRCUIT_BREAKER_CHECK = "CONFIRMATION.CIRCUIT_BREAKER.CHECK"
    CIRCUIT_BREAKER_BLOCKED = "CONFIRMATION.CIRCUIT_BREAKER.BLOCKED"
    CIRCUIT_BREAKER_TRIGGER = "CONFIRMATION.CIRCUIT_BREAKER.TRIGGER"
    RECOVERY_PERIOD_UPGRADE = "CONFIRMATION.RECOVERY.UPGRADE"
    HIGH_FREQUENCY_EXEMPTION = "CONFIRMATION.HIGH_FREQUENCY.EXEMPTION"


@dataclass
class HighFrequencyExemptionConfig:
    """高频策略豁免配置.

    军规覆盖: M17(程序化合规)

    Attributes:
        enable_exemption: 是否启用高频豁免
        max_order_value_for_exemption: 豁免最大订单金额(默认10万)
        max_position_ratio: 豁免最大持仓比例(默认5%)
        allowed_symbols: 允许豁免的合约列表(空表示全部)
        min_strategy_score: 最低策略评分(0-100)
    """
    enable_exemption: bool = True
    max_order_value_for_exemption: float = 100_000  # 10万
    max_position_ratio: float = 0.05  # 5%
    allowed_symbols: list[str] = field(default_factory=list)
    min_strategy_score: int = 80


@dataclass
class RecoveryPeriodConfig:
    """恢复期配置.

    军规覆盖: M6(熔断保护)

    Attributes:
        upgrade_confirmation_level: 恢复期是否升级确认级别
        recovery_soft_to_hard: SOFT升级为HARD
        recovery_auto_to_soft: AUTO升级为SOFT
    """
    upgrade_confirmation_level: bool = True
    recovery_soft_to_hard: bool = True
    recovery_auto_to_soft: bool = True


@dataclass
class CircuitBreakerIntegrationConfig:
    """熔断器集成配置.

    军规覆盖: M6(熔断保护), M12(双重确认)

    Attributes:
        enable_circuit_breaker_check: 确认前检查熔断状态
        enable_timeout_circuit_break: 超时触发熔断
        block_on_circuit_break: 熔断时阻止新确认
        high_frequency_exemption: 高频策略豁免配置
        recovery_period: 恢复期配置
    """
    enable_circuit_breaker_check: bool = True
    enable_timeout_circuit_break: bool = True
    block_on_circuit_break: bool = True
    high_frequency_exemption: HighFrequencyExemptionConfig = field(
        default_factory=HighFrequencyExemptionConfig
    )
    recovery_period: RecoveryPeriodConfig = field(
        default_factory=RecoveryPeriodConfig
    )


# Type alias for circuit breaker callback
CircuitBreakerTriggerCallback = Callable[[str, dict[str, Any]], Awaitable[bool]]


# =============================================================================
# Enhanced Hard Confirmation with Circuit Breaker Integration
# =============================================================================


class HardConfirmationEnhanced(HardConfirmation):
    """增强版硬确认 - 集成熔断器.

    V4PRO Scenario: CONFIRMATION.LEVEL_HARD + CIRCUIT_BREAKER

    增强功能:
    - 硬确认超时自动触发熔断器
    - 与CircuitBreaker状态机联动

    军规覆盖: M6(熔断保护), M12(双重确认)
    """

    def __init__(
        self,
        config: ConfirmationConfig,
        circuit_breaker_config: CircuitBreakerIntegrationConfig | None = None,
        audit_callback: AuditCallback | None = None,
        alert_callback: AlertCallback | None = None,
        user_confirm_callback: UserConfirmCallback | None = None,
        soft_confirmation: SoftConfirmation | None = None,
        circuit_breaker_trigger_callback: CircuitBreakerTriggerCallback | None = None,
    ):
        """初始化增强版硬确认器.

        Args:
            config: 确认配置
            circuit_breaker_config: 熔断器集成配置
            audit_callback: 审计回调
            alert_callback: 告警发送回调
            user_confirm_callback: 用户确认回调
            soft_confirmation: 软确认器(用于降级)
            circuit_breaker_trigger_callback: 熔断触发回调
        """
        super().__init__(
            config=config,
            audit_callback=audit_callback,
            alert_callback=alert_callback,
            user_confirm_callback=user_confirm_callback,
            soft_confirmation=soft_confirmation,
        )
        self._cb_config = circuit_breaker_config or CircuitBreakerIntegrationConfig()
        self._circuit_breaker_trigger = circuit_breaker_trigger_callback

    async def _trigger_circuit_breaker(
        self,
        confirmation_id: str,
        context: ConfirmationContext,
        reason: str,
    ) -> bool:
        """触发熔断器.

        Args:
            confirmation_id: 确认ID
            context: 确认上下文
            reason: 触发原因

        Returns:
            是否成功触发熔断
        """
        if not self._cb_config.enable_timeout_circuit_break:
            return False

        if self._circuit_breaker_trigger:
            metadata = {
                "confirmation_id": confirmation_id,
                "context": context.to_dict(),
                "reason": reason,
                "trigger_source": "HARD_CONFIRM_TIMEOUT",
            }
            try:
                result = await self._circuit_breaker_trigger(reason, metadata)

                # 发送熔断触发审计事件
                self._emit_audit(ConfirmationAuditEvent(
                    event_type=ConfirmationAuditEventType.HARD_CONFIRM_CIRCUIT_BREAK,
                    confirmation_id=confirmation_id,
                    reason=f"熔断器触发: {reason}",
                    metadata={
                        "trigger_result": result,
                        "trigger_source": "HARD_CONFIRM_TIMEOUT",
                    },
                ))

                return result
            except Exception as e:
                # 熔断触发失败时记录但不阻塞
                self._emit_audit(ConfirmationAuditEvent(
                    event_type=ConfirmationAuditEventType.HARD_CONFIRM_CIRCUIT_BREAK,
                    confirmation_id=confirmation_id,
                    reason=f"熔断器触发失败: {e!s}",
                    metadata={"error": str(e)},
                ))
                return False
        return False

    async def confirm(
        self,
        confirmation_id: str,
        context: ConfirmationContext,
    ) -> ConfirmationDecision:
        """执行增强版硬确认流程.

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
            reason="增强版硬确认流程开始",
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

            # 实际触发熔断器
            await self._trigger_circuit_breaker(
                confirmation_id,
                context,
                f"硬确认超时触发熔断: 合约{context.order_intent.symbol}, 金额{context.order_value:.0f}",
            )

            return ConfirmationDecision(
                level=ConfirmationLevel.HARD_CONFIRM,
                result=ConfirmationResult.REJECTED,
                reasons=reasons,
                checks_passed=checks_passed,
                checks_failed=checks_failed,
                elapsed_seconds=elapsed,
            )


# =============================================================================
# Enhanced Confirmation Manager with Circuit Breaker Integration
# =============================================================================


class ConfirmationManagerEnhanced:
    """增强版确认管理器 - 集成熔断器.

    统一管理确认流程,自动选择确认级别并执行。
    增强功能:
    - 确认前检查熔断器状态
    - 恢复期自动升级确认级别
    - 高频策略豁免逻辑
    - 硬确认超时触发熔断

    军规覆盖: M5, M6, M12, M13, M15, M17
    """

    def __init__(
        self,
        config: ConfirmationConfig | None = None,
        circuit_breaker_config: CircuitBreakerIntegrationConfig | None = None,
        audit_callback: AuditCallback | None = None,
        alert_callback: AlertCallback | None = None,
        risk_check: RiskCheckCallback | None = None,
        cost_check: CostCheckCallback | None = None,
        limit_check: LimitCheckCallback | None = None,
        user_confirm_callback: UserConfirmCallback | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        circuit_breaker_trigger_callback: CircuitBreakerTriggerCallback | None = None,
    ):
        """初始化增强版确认管理器.

        Args:
            config: 确认配置
            circuit_breaker_config: 熔断器集成配置
            audit_callback: 审计回调
            alert_callback: 告警回调
            risk_check: 风控检查回调
            cost_check: 成本检查回调
            limit_check: 涨跌停检查回调
            user_confirm_callback: 用户确认回调
            circuit_breaker: 熔断器实例(可选)
            circuit_breaker_trigger_callback: 熔断触发回调
        """
        self.config = config or ConfirmationConfig()
        self._cb_config = circuit_breaker_config or CircuitBreakerIntegrationConfig()
        self._audit_callback = audit_callback
        self._circuit_breaker = circuit_breaker

        self._soft_confirmation = SoftConfirmation(
            config=self.config,
            audit_callback=audit_callback,
            risk_check=risk_check,
            cost_check=cost_check,
            limit_check=limit_check,
        )

        self._hard_confirmation = HardConfirmationEnhanced(
            config=self.config,
            circuit_breaker_config=circuit_breaker_config,
            audit_callback=audit_callback,
            alert_callback=alert_callback,
            user_confirm_callback=user_confirm_callback,
            soft_confirmation=self._soft_confirmation,
            circuit_breaker_trigger_callback=circuit_breaker_trigger_callback,
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

    def _check_circuit_breaker_state(self) -> tuple[bool, str]:
        """检查熔断器状态.

        Returns:
            (是否允许继续, 状态描述)
        """
        if not self._cb_config.enable_circuit_breaker_check:
            return True, "熔断检查已禁用"

        if self._circuit_breaker is None:
            return True, "未配置熔断器"

        try:
            # 动态导入避免循环依赖
            from src.guardian.circuit_breaker import CircuitBreakerState

            current_state = self._circuit_breaker.state

            if current_state == CircuitBreakerState.TRIGGERED:
                if self._cb_config.block_on_circuit_break:
                    return False, "熔断器已触发(TRIGGERED),阻止新确认"
                return True, "熔断器已触发(TRIGGERED),但未配置阻止"

            if current_state == CircuitBreakerState.RECOVERY:
                return True, "熔断器恢复期(RECOVERY),允许有限确认"

            # NORMAL
            return True, "熔断器正常(NORMAL)"

        except Exception as e:
            # 熔断器检查失败时不阻塞
            return True, f"熔断器检查异常: {e!s}"

    def _is_in_recovery_period(self) -> bool:
        """检查是否处于恢复期.

        Returns:
            是否处于恢复期
        """
        if self._circuit_breaker is None:
            return False

        try:
            from src.guardian.circuit_breaker import CircuitBreakerState
            return self._circuit_breaker.state == CircuitBreakerState.RECOVERY
        except Exception:
            return False

    def _check_high_frequency_exemption(
        self,
        context: ConfirmationContext,
    ) -> tuple[bool, str]:
        """检查高频策略豁免.

        Args:
            context: 确认上下文

        Returns:
            (是否豁免, 豁免原因)

        军规覆盖: M17(程序化合规)
        """
        hf_config = self._cb_config.high_frequency_exemption

        if not hf_config.enable_exemption:
            return False, "高频豁免已禁用"

        # 检查策略类型
        if context.strategy_type != StrategyType.HIGH_FREQUENCY:
            return False, "非高频策略"

        # 检查订单金额
        if context.order_value > hf_config.max_order_value_for_exemption:
            return False, f"订单金额{context.order_value:.0f}超过豁免上限{hf_config.max_order_value_for_exemption:.0f}"

        # 检查合约白名单(如果配置了)
        if hf_config.allowed_symbols:
            if context.order_intent.symbol not in hf_config.allowed_symbols:
                return False, f"合约{context.order_intent.symbol}不在豁免白名单中"

        return True, "符合高频策略豁免条件"

    def _upgrade_confirmation_level_for_recovery(
        self,
        level: ConfirmationLevel,
        reasons: list[str],
    ) -> tuple[ConfirmationLevel, list[str]]:
        """恢复期升级确认级别.

        Args:
            level: 原确认级别
            reasons: 原决策原因

        Returns:
            (升级后级别, 更新后原因)
        """
        recovery_config = self._cb_config.recovery_period

        if not recovery_config.upgrade_confirmation_level:
            return level, reasons

        if not self._is_in_recovery_period():
            return level, reasons

        new_level = level
        new_reasons = reasons.copy()

        if level == ConfirmationLevel.AUTO and recovery_config.recovery_auto_to_soft:
            new_level = ConfirmationLevel.SOFT_CONFIRM
            new_reasons.append("恢复期: AUTO升级为SOFT_CONFIRM")

        elif level == ConfirmationLevel.SOFT_CONFIRM and recovery_config.recovery_soft_to_hard:
            new_level = ConfirmationLevel.HARD_CONFIRM
            new_reasons.append("恢复期: SOFT_CONFIRM升级为HARD_CONFIRM")

        return new_level, new_reasons

    async def confirm(
        self,
        context: ConfirmationContext,
    ) -> ConfirmationDecision:
        """执行增强版确认流程.

        根据上下文自动选择确认级别并执行。
        增强功能:
        1. 熔断状态检查
        2. 高频策略豁免
        3. 恢复期级别升级

        Args:
            context: 确认上下文

        Returns:
            确认决策结果

        军规覆盖: M5, M6, M12, M13, M15, M17
        """
        confirmation_id = self._generate_confirmation_id()

        # 发送开始事件
        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_STARTED,
            confirmation_id=confirmation_id,
            context=context.to_dict(),
            reason="增强版确认流程开始",
        ))

        # 1. 检查熔断器状态
        cb_allowed, cb_reason = self._check_circuit_breaker_state()

        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_LEVEL_DETERMINED,
            confirmation_id=confirmation_id,
            reason=f"熔断状态检查: {cb_reason}",
            metadata={"circuit_breaker_allowed": cb_allowed},
        ))

        if not cb_allowed:
            # 熔断状态下检查高频豁免
            hf_exempt, hf_reason = self._check_high_frequency_exemption(context)

            if hf_exempt:
                self._emit_audit(ConfirmationAuditEvent(
                    event_type=ConfirmationAuditEventType.CONFIRMATION_LEVEL_DETERMINED,
                    confirmation_id=confirmation_id,
                    reason=f"高频策略豁免: {hf_reason}",
                    metadata={"high_frequency_exemption": True},
                ))
            else:
                # 熔断阻止
                decision = ConfirmationDecision(
                    level=ConfirmationLevel.HARD_CONFIRM,
                    result=ConfirmationResult.REJECTED,
                    reasons=[cb_reason, "熔断状态下拒绝新订单确认"],
                    checks_failed=["M6_CIRCUIT_BREAKER_BLOCK"],
                )

                self._emit_audit(ConfirmationAuditEvent(
                    event_type=ConfirmationAuditEventType.CONFIRMATION_COMPLETED,
                    confirmation_id=confirmation_id,
                    level=ConfirmationLevel.HARD_CONFIRM.value,
                    result=ConfirmationResult.REJECTED.value,
                    reason="熔断状态下拒绝确认",
                    metadata=decision.to_dict(),
                ))

                return decision

        # 2. 确定确认级别
        level, reasons = determine_confirmation_level(context, self.config)

        # 3. 恢复期级别升级
        level, reasons = self._upgrade_confirmation_level_for_recovery(level, reasons)

        self._emit_audit(ConfirmationAuditEvent(
            event_type=ConfirmationAuditEventType.CONFIRMATION_LEVEL_DETERMINED,
            confirmation_id=confirmation_id,
            level=level.value,
            reason=f"确认级别: {level.value}",
            metadata={"reasons": reasons},
        ))

        # 4. 执行对应级别的确认
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

    def set_circuit_breaker(self, circuit_breaker: CircuitBreaker) -> None:
        """设置熔断器实例.

        Args:
            circuit_breaker: 熔断器实例
        """
        self._circuit_breaker = circuit_breaker

    def get_circuit_breaker_state(self) -> str | None:
        """获取当前熔断器状态.

        Returns:
            熔断器状态字符串,未配置时返回None
        """
        if self._circuit_breaker is None:
            return None
        try:
            return self._circuit_breaker.current_state.value
        except Exception:
            return None


# =============================================================================
# Factory Functions
# =============================================================================


def create_enhanced_confirmation_manager(
    config: ConfirmationConfig | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    enable_circuit_breaker_integration: bool = True,
    audit_callback: AuditCallback | None = None,
    alert_callback: AlertCallback | None = None,
    user_confirm_callback: UserConfirmCallback | None = None,
) -> ConfirmationManagerEnhanced:
    """创建增强版确认管理器.

    工厂函数,简化创建过程。

    Args:
        config: 确认配置
        circuit_breaker: 熔断器实例
        enable_circuit_breaker_integration: 是否启用熔断器集成
        audit_callback: 审计回调
        alert_callback: 告警回调
        user_confirm_callback: 用户确认回调

    Returns:
        增强版确认管理器实例
    """
    cb_config = CircuitBreakerIntegrationConfig(
        enable_circuit_breaker_check=enable_circuit_breaker_integration,
        enable_timeout_circuit_break=enable_circuit_breaker_integration,
        block_on_circuit_break=enable_circuit_breaker_integration,
    )

    async def default_circuit_breaker_trigger(
        reason: str,
        metadata: dict[str, Any],
    ) -> bool:
        """默认熔断触发回调.

        当配置了熔断器时,调用其trigger方法。
        """
        if circuit_breaker is not None:
            try:
                from src.guardian.circuit_breaker import CircuitBreakerEvent
                circuit_breaker.trigger(
                    CircuitBreakerEvent.MANUAL_TRIGGER,
                    reason=reason,
                )
                return True
            except Exception:
                return False
        return False

    return ConfirmationManagerEnhanced(
        config=config,
        circuit_breaker_config=cb_config,
        audit_callback=audit_callback,
        alert_callback=alert_callback,
        user_confirm_callback=user_confirm_callback,
        circuit_breaker=circuit_breaker,
        circuit_breaker_trigger_callback=default_circuit_breaker_trigger if enable_circuit_breaker_integration else None,
    )
