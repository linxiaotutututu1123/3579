"""训练启用门禁 (军规级 v3.0).

军规要求:
    1. 总成熟度 >= 80% 才能启用
    2. 任意维度 >= 60%
    3. 训练时间 >= 90天
    4. 人工确认才能最终启用

本模块负责控制实验性策略的启用权限。

示例:
    gate = TrainingGate(evaluator)
    decision = gate.check_activation(history)

    if decision.allowed:
        print("可以启用！")
    else:
        print(f"不能启用: {decision.reasons}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import ClassVar

from src.strategy.experimental.maturity_evaluator import (
    MaturityEvaluator,
    MaturityReport,
    TrainingHistory,
)


class ActivationStatus(Enum):
    """启用状态."""

    TRAINING = "training"            # 训练中
    PENDING_REVIEW = "pending"       # 待审核
    APPROVED = "approved"            # 已批准
    REJECTED = "rejected"            # 已拒绝
    ACTIVATED = "activated"          # 已启用
    SUSPENDED = "suspended"          # 已暂停


@dataclass
class ActivationDecision:
    """启用决策.

    属性:
        allowed: 是否允许启用
        status: 当前状态
        maturity_pct: 成熟度百分比
        training_days: 训练天数
        remaining_days: 剩余天数（如果未达标）
        reasons: 原因列表
        report: 完整评估报告
        requires_manual_approval: 是否需要人工审批
        timestamp: 决策时间
    """

    allowed: bool
    status: ActivationStatus
    maturity_pct: float
    training_days: int
    remaining_days: int
    reasons: list[str]
    report: MaturityReport | None
    requires_manual_approval: bool
    timestamp: datetime = field(default_factory=datetime.now)  # noqa: DTZ005

    def to_display(self) -> str:
        """生成显示文本.

        返回:
            人类可读的状态文本
        """
        lines = [
            "=" * 60,
            "        策略训练状态报告",
            "=" * 60,
            "",
            f"  状态: {self._status_emoji()} {self.status.value.upper()}",
            f"  成熟度: {self._progress_bar(self.maturity_pct)} {self.maturity_pct:.1%}",
            f"  训练天数: {self.training_days} / 90 天",
            "",
        ]

        if self.remaining_days > 0:
            lines.append(f"  ⏳ 还需训练: {self.remaining_days} 天")
            lines.append("")

        if self.allowed:
            lines.append("  ✅ 策略已达到启用标准！")
            if self.requires_manual_approval:
                lines.append("  ⚠️  需要人工审批后才能正式启用")
        else:
            lines.append("  ❌ 策略尚未达到启用标准")
            lines.append("")
            lines.append("  阻止原因:")
            for reason in self.reasons:
                lines.append(f"    • {reason}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _status_emoji(self) -> str:
        """状态emoji."""
        return {
            ActivationStatus.TRAINING: "🔄",
            ActivationStatus.PENDING_REVIEW: "⏸️",
            ActivationStatus.APPROVED: "✅",
            ActivationStatus.REJECTED: "❌",
            ActivationStatus.ACTIVATED: "🚀",
            ActivationStatus.SUSPENDED: "⏹️",
        }.get(self.status, "❓")

    def _progress_bar(self, pct: float, width: int = 20) -> str:
        """进度条."""
        filled = int(pct * width)
        empty = width - filled
        bar = "█" * filled + "░" * empty
        return f"[{bar}]"


@dataclass
class TrainingGateConfig:
    """训练门禁配置.

    属性:
        activation_threshold: 启用门槛（默认80%）
        dimension_threshold: 单维度门槛（默认60%）
        min_training_days: 最低训练天数（默认90天）
        require_manual_approval: 是否需要人工审批
        cool_down_days: 启用后的冷却期（天）
    """

    activation_threshold: float = 0.80
    dimension_threshold: float = 0.60
    min_training_days: int = 90
    require_manual_approval: bool = True
    cool_down_days: int = 7


class TrainingGate:
    """训练启用门禁.

    控制实验性策略的启用权限。

    门禁规则:
        1. 总成熟度 >= 80%
        2. 每个评估维度 >= 60%
        3. 训练时间 >= 90天
        4. 需要人工审批（可配置）
    """

    # 军规：禁止绕过门禁
    BYPASS_FORBIDDEN: ClassVar[bool] = True

    def __init__(
        self,
        evaluator: MaturityEvaluator,
        config: TrainingGateConfig | None = None,
    ) -> None:
        """初始化训练门禁.

        参数:
            evaluator: 成熟度评估器
            config: 门禁配置
        """
        self._evaluator = evaluator
        self._config = config or TrainingGateConfig()
        self._approval_records: dict[str, datetime] = {}  # 人工审批记录
        self._activation_log: list[dict] = []

    def check_activation(self, history: TrainingHistory) -> ActivationDecision:
        """检查是否可以启用.

        参数:
            history: 训练历史

        返回:
            启用决策
        """
        # 1. 执行成熟度评估
        report = self._evaluator.evaluate(history)

        # 2. 收集阻止原因
        reasons: list[str] = list(report.blocking_reasons)

        # 3. 计算剩余天数
        remaining_days = max(0, self._config.min_training_days - history.training_days)

        # 4. 检查是否有人工审批
        has_approval = history.strategy_id in self._approval_records

        # 5. 确定状态
        if report.can_activate:
            if self._config.require_manual_approval and not has_approval:
                status = ActivationStatus.PENDING_REVIEW
                allowed = False
                reasons.append("需要人工审批")
            else:
                status = ActivationStatus.APPROVED
                allowed = True
        else:
            status = ActivationStatus.TRAINING
            allowed = False

        decision = ActivationDecision(
            allowed=allowed,
            status=status,
            maturity_pct=report.total_score,
            training_days=history.training_days,
            remaining_days=remaining_days,
            reasons=reasons,
            report=report,
            requires_manual_approval=self._config.require_manual_approval and not has_approval,
        )

        # 6. 记录日志
        self._log_check(history.strategy_id, decision)

        return decision

    def manual_approve(self, strategy_id: str, approver: str) -> bool:
        """人工审批.

        参数:
            strategy_id: 策略ID
            approver: 审批人

        返回:
            是否成功
        """
        self._approval_records[strategy_id] = datetime.now()
        self._log_approval(strategy_id, approver)
        return True

    def manual_reject(self, strategy_id: str, rejector: str, reason: str) -> bool:
        """人工拒绝.

        参数:
            strategy_id: 策略ID
            rejector: 拒绝人
            reason: 拒绝原因

        返回:
            是否成功
        """
        if strategy_id in self._approval_records:
            del self._approval_records[strategy_id]
        self._log_rejection(strategy_id, rejector, reason)
        return True

    def revoke_approval(self, strategy_id: str, revoker: str, reason: str) -> bool:
        """撤销审批.

        参数:
            strategy_id: 策略ID
            revoker: 撤销人
            reason: 撤销原因

        返回:
            是否成功
        """
        if strategy_id in self._approval_records:
            del self._approval_records[strategy_id]
            self._log_revocation(strategy_id, revoker, reason)
            return True
        return False

    def is_approved(self, strategy_id: str) -> bool:
        """检查是否已审批.

        参数:
            strategy_id: 策略ID

        返回:
            是否已审批
        """
        return strategy_id in self._approval_records

    def get_approval_time(self, strategy_id: str) -> datetime | None:
        """获取审批时间.

        参数:
            strategy_id: 策略ID

        返回:
            审批时间，如果未审批则返回None
        """
        return self._approval_records.get(strategy_id)

    def _log_check(self, strategy_id: str, decision: ActivationDecision) -> None:
        """记录检查日志.

        参数:
            strategy_id: 策略ID
            decision: 决策
        """
        self._activation_log.append({
            "type": "check",
            "strategy_id": strategy_id,
            "timestamp": datetime.now().isoformat(),
            "allowed": decision.allowed,
            "maturity_pct": decision.maturity_pct,
            "status": decision.status.value,
        })

    def _log_approval(self, strategy_id: str, approver: str) -> None:
        """记录审批日志.

        参数:
            strategy_id: 策略ID
            approver: 审批人
        """
        self._activation_log.append({
            "type": "approval",
            "strategy_id": strategy_id,
            "timestamp": datetime.now().isoformat(),
            "approver": approver,
        })

    def _log_rejection(self, strategy_id: str, rejector: str, reason: str) -> None:
        """记录拒绝日志.

        参数:
            strategy_id: 策略ID
            rejector: 拒绝人
            reason: 原因
        """
        self._activation_log.append({
            "type": "rejection",
            "strategy_id": strategy_id,
            "timestamp": datetime.now().isoformat(),
            "rejector": rejector,
            "reason": reason,
        })

    def _log_revocation(self, strategy_id: str, revoker: str, reason: str) -> None:
        """记录撤销日志.

        参数:
            strategy_id: 策略ID
            revoker: 撤销人
            reason: 原因
        """
        self._activation_log.append({
            "type": "revocation",
            "strategy_id": strategy_id,
            "timestamp": datetime.now().isoformat(),
            "revoker": revoker,
            "reason": reason,
        })

    @property
    def activation_log(self) -> list[dict]:
        """获取启用日志."""
        return list(self._activation_log)

    @property
    def config(self) -> TrainingGateConfig:
        """获取配置."""
        return self._config
