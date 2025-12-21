"""置信度监控模块 (军规级 v4.4).

V4PRO Platform Component - 置信度监控与告警系统
军规覆盖: M3(完整审计), M9(错误上报), M19(风险归因)

V4PRO Scenarios:
- K53: CONFIDENCE.MONITOR - 置信度监控
- K54: CONFIDENCE.ALERT - 置信度告警
- K55: CONFIDENCE.HEALTH - 健康状态集成

集成 HealthChecker 和 DingTalk 告警系统。

示例:
    >>> from src.risk.confidence import ConfidenceAssessor
    >>> from src.risk.confidence_monitor import ConfidenceMonitor, ConfidenceMonitorConfig
    >>> assessor = ConfidenceAssessor()
    >>> monitor = ConfidenceMonitor(assessor, ConfidenceMonitorConfig())
    >>> # 注册到健康检查器
    >>> from src.monitoring.health import HealthChecker
    >>> health_checker = HealthChecker()
    >>> monitor.register_with_health_checker(health_checker)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.alerts.dingtalk import DingTalkConfig, send_markdown
from src.monitoring.health import HealthChecker, HealthState, HealthStatus
from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceLevel,
    ConfidenceResult,
)


if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# =============================================================================
# 配置数据类
# =============================================================================


@dataclass
class ConfidenceMonitorConfig:
    """置信度监控配置.

    属性:
        low_confidence_threshold: 低置信度阈值 (触发告警)
        alert_on_decline: 是否在置信度下降时告警
        decline_window: 下降趋势检测窗口大小
        alert_cooldown_seconds: 告警冷却时间 (防止告警风暴)
        dingtalk_config: 钉钉告警配置 (可选)
        enable_health_check: 是否启用健康检查集成
        health_check_interval_s: 健康检查间隔 (秒)
    """

    low_confidence_threshold: float = 0.70
    alert_on_decline: bool = True
    decline_window: int = 5
    alert_cooldown_seconds: float = 300.0  # 5分钟冷却
    dingtalk_config: DingTalkConfig | None = None
    enable_health_check: bool = True
    health_check_interval_s: float = 60.0

    def validate(self) -> list[str]:
        """验证配置完整性.

        返回:
            错误信息列表
        """
        errors: list[str] = []

        if not 0 < self.low_confidence_threshold < 1:
            errors.append("low_confidence_threshold必须在0-1之间")
        if self.decline_window < 2:
            errors.append("decline_window必须至少为2")
        if self.alert_cooldown_seconds < 0:
            errors.append("alert_cooldown_seconds不能为负")
        if self.health_check_interval_s <= 0:
            errors.append("health_check_interval_s必须大于0")

        return errors


# =============================================================================
# 告警记录
# =============================================================================


@dataclass
class AlertRecord:
    """告警记录.

    属性:
        alert_type: 告警类型
        confidence_score: 置信度分数
        message: 告警消息
        timestamp: 时间戳
        sent_successfully: 是否发送成功
        metadata: 附加元数据
    """

    alert_type: str
    confidence_score: float
    message: str
    timestamp: str = ""
    sent_successfully: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后处理."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()  # noqa: DTZ005

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "alert_type": self.alert_type,
            "confidence_score": self.confidence_score,
            "message": self.message,
            "timestamp": self.timestamp,
            "sent_successfully": self.sent_successfully,
            "metadata": self.metadata,
        }


# =============================================================================
# 置信度监控器
# =============================================================================


class ConfidenceMonitor:
    """置信度监控器 (军规 M3/M9/M19).

    监控置信度评估结果，集成健康检查和告警系统。

    功能:
    - 置信度实时监控
    - 低置信度告警
    - 下降趋势检测
    - 健康状态集成
    - 钉钉通知

    示例:
        >>> assessor = ConfidenceAssessor()
        >>> config = ConfidenceMonitorConfig(
        ...     low_confidence_threshold=0.70,
        ...     dingtalk_config=DingTalkConfig(webhook_url="https://...")
        ... )
        >>> monitor = ConfidenceMonitor(assessor, config)
        >>> result = assessor.assess(context)
        >>> alert_sent = monitor.check_and_alert(result)
    """

    # 告警类型常量
    ALERT_LOW_CONFIDENCE = "LOW_CONFIDENCE"
    ALERT_DECLINING_TREND = "DECLINING_TREND"
    ALERT_CONSECUTIVE_LOW = "CONSECUTIVE_LOW"

    def __init__(
        self,
        assessor: ConfidenceAssessor,
        config: ConfidenceMonitorConfig | None = None,
    ) -> None:
        """初始化置信度监控器.

        参数:
            assessor: 置信度评估器实例
            config: 监控配置
        """
        self._assessor = assessor
        self._config = config or ConfidenceMonitorConfig()
        self._last_alert_time: float = 0.0
        self._alert_history: list[AlertRecord] = []
        self._max_alert_history = 100
        self._recent_results: list[ConfidenceResult] = []
        self._max_recent_results = 20
        self._consecutive_low_count = 0

        # 验证配置
        errors = self._config.validate()
        if errors:
            logger.warning("监控配置验证警告: %s", "; ".join(errors))

    @property
    def assessor(self) -> ConfidenceAssessor:
        """获取评估器实例."""
        return self._assessor

    @property
    def config(self) -> ConfidenceMonitorConfig:
        """获取监控配置."""
        return self._config

    def check_and_alert(self, result: ConfidenceResult) -> bool:
        """检查置信度结果并发送告警.

        参数:
            result: 置信度评估结果

        返回:
            是否发送了告警

        场景: K53, K54
        """
        # 记录结果
        self._record_result(result)

        alert_sent = False

        # 检查低置信度
        if result.score < self._config.low_confidence_threshold:
            self._consecutive_low_count += 1
            if self._should_send_alert():
                alert_sent = self._send_low_confidence_alert(result)
        else:
            self._consecutive_low_count = 0

        # 检查下降趋势
        if self._config.alert_on_decline and self._detect_declining_trend():
            if self._should_send_alert():
                alert_sent = self._send_declining_alert() or alert_sent

        # 检查连续低置信度
        if self._consecutive_low_count >= 3 and self._should_send_alert():
            alert_sent = self._send_consecutive_low_alert() or alert_sent

        return alert_sent

    def register_with_health_checker(self, checker: HealthChecker) -> None:
        """注册到健康检查器.

        参数:
            checker: 健康检查器实例

        场景: K55
        """
        if not self._config.enable_health_check:
            logger.info("健康检查集成已禁用")
            return

        def confidence_health_check() -> tuple[bool, str]:
            """置信度健康检查函数."""
            trend = self._assessor.get_trend_analysis()

            # 检查是否有数据
            if trend["trend"] == "INSUFFICIENT_DATA":
                return True, "数据不足，无法评估"

            # 检查是否有告警
            if trend.get("alert", False):
                return False, trend.get("alert_message", "置信度异常")

            # 检查近期平均
            recent_avg = trend.get("recent_avg", 0.0)
            if recent_avg < self._config.low_confidence_threshold:
                return False, f"近期置信度偏低: {recent_avg:.0%}"

            return True, f"置信度正常: {recent_avg:.0%}"

        checker.register_check("confidence", confidence_health_check)
        logger.info("置信度健康检查已注册")

    def unregister_from_health_checker(self, checker: HealthChecker) -> None:
        """从健康检查器注销.

        参数:
            checker: 健康检查器实例
        """
        checker.unregister_check("confidence")
        logger.info("置信度健康检查已注销")

    def get_health_status(self) -> HealthStatus:
        """获取健康状态.

        返回:
            健康状态对象
        """
        trend = self._assessor.get_trend_analysis()

        # 判断健康状态
        if trend["trend"] == "INSUFFICIENT_DATA":
            state = HealthState.UNKNOWN
            message = "数据不足"
        elif trend.get("alert", False):
            state = HealthState.UNHEALTHY
            message = trend.get("alert_message", "置信度异常")
        elif trend.get("recent_avg", 0.0) < self._config.low_confidence_threshold:
            state = HealthState.DEGRADED
            message = f"置信度偏低: {trend.get('recent_avg', 0.0):.0%}"
        else:
            state = HealthState.HEALTHY
            message = f"置信度正常: {trend.get('recent_avg', 0.0):.0%}"

        return HealthStatus(
            component="confidence",
            state=state,
            message=message,
            metadata={
                "trend": trend["trend"],
                "recent_avg": trend.get("recent_avg", 0.0),
                "overall_avg": trend.get("overall_avg", 0.0),
                "direction": trend.get("direction", "NEUTRAL"),
                "consecutive_low_count": self._consecutive_low_count,
            },
        )

    def get_alert_history(self) -> list[AlertRecord]:
        """获取告警历史.

        返回:
            告警记录列表
        """
        return list(self._alert_history)

    def get_statistics(self) -> dict[str, Any]:
        """获取监控统计信息.

        返回:
            统计信息字典
        """
        assessor_stats = self._assessor.get_statistics()
        trend = self._assessor.get_trend_analysis()

        total_alerts = len(self._alert_history)
        successful_alerts = sum(1 for a in self._alert_history if a.sent_successfully)

        return {
            "assessor_stats": assessor_stats,
            "trend_analysis": trend,
            "alert_stats": {
                "total_alerts": total_alerts,
                "successful_alerts": successful_alerts,
                "failed_alerts": total_alerts - successful_alerts,
                "consecutive_low_count": self._consecutive_low_count,
            },
            "config": {
                "low_confidence_threshold": self._config.low_confidence_threshold,
                "alert_on_decline": self._config.alert_on_decline,
                "decline_window": self._config.decline_window,
                "dingtalk_enabled": self._config.dingtalk_config is not None,
            },
        }

    def reset(self) -> None:
        """重置监控状态."""
        self._last_alert_time = 0.0
        self._alert_history.clear()
        self._recent_results.clear()
        self._consecutive_low_count = 0
        self._assessor.reset_statistics()
        logger.info("置信度监控器已重置")

    # =========================================================================
    # 私有方法
    # =========================================================================

    def _record_result(self, result: ConfidenceResult) -> None:
        """记录评估结果."""
        self._recent_results.append(result)
        if len(self._recent_results) > self._max_recent_results:
            self._recent_results.pop(0)

    def _should_send_alert(self) -> bool:
        """检查是否应该发送告警 (冷却检查)."""
        current_time = time.time()
        if current_time - self._last_alert_time < self._config.alert_cooldown_seconds:
            return False
        return True

    def _detect_declining_trend(self) -> bool:
        """检测下降趋势."""
        if len(self._recent_results) < self._config.decline_window:
            return False

        window = self._recent_results[-self._config.decline_window :]
        scores = [r.score for r in window]

        # 检查是否连续下降
        for i in range(len(scores) - 1):
            if scores[i] <= scores[i + 1]:
                return False

        return True

    def _send_low_confidence_alert(self, result: ConfidenceResult) -> bool:
        """发送低置信度告警."""
        message = (
            f"[置信度告警] 低置信度检测\n\n"
            f"- 分数: {result.score:.0%}\n"
            f"- 等级: {result.level.value}\n"
            f"- 建议: {result.recommendation}\n"
            f"- 时间: {result.timestamp}"
        )

        return self._send_alert(
            alert_type=self.ALERT_LOW_CONFIDENCE,
            score=result.score,
            message=message,
            metadata={"level": result.level.value},
        )

    def _send_declining_alert(self) -> bool:
        """发送下降趋势告警."""
        window = self._recent_results[-self._config.decline_window :]
        scores = [r.score for r in window]

        message = (
            f"[置信度告警] 下降趋势检测\n\n"
            f"- 趋势窗口: {self._config.decline_window}\n"
            f"- 分数序列: {', '.join(f'{s:.0%}' for s in scores)}\n"
            f"- 当前分数: {scores[-1]:.0%}"
        )

        return self._send_alert(
            alert_type=self.ALERT_DECLINING_TREND,
            score=scores[-1],
            message=message,
            metadata={"scores": scores},
        )

    def _send_consecutive_low_alert(self) -> bool:
        """发送连续低置信度告警."""
        recent_scores = [r.score for r in self._recent_results[-3:]]

        message = (
            f"[置信度告警] 连续低置信度\n\n"
            f"- 连续次数: {self._consecutive_low_count}\n"
            f"- 近期分数: {', '.join(f'{s:.0%}' for s in recent_scores)}\n"
            f"- 阈值: {self._config.low_confidence_threshold:.0%}"
        )

        return self._send_alert(
            alert_type=self.ALERT_CONSECUTIVE_LOW,
            score=recent_scores[-1] if recent_scores else 0.0,
            message=message,
            metadata={"consecutive_count": self._consecutive_low_count},
        )

    def _send_alert(
        self,
        alert_type: str,
        score: float,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """发送告警.

        参数:
            alert_type: 告警类型
            score: 置信度分数
            message: 告警消息
            metadata: 附加元数据

        返回:
            是否发送成功
        """
        record = AlertRecord(
            alert_type=alert_type,
            confidence_score=score,
            message=message,
            metadata=metadata or {},
        )

        # 记录告警
        self._alert_history.append(record)
        if len(self._alert_history) > self._max_alert_history:
            self._alert_history.pop(0)

        # 更新最后告警时间
        self._last_alert_time = time.time()

        # 发送钉钉通知
        if self._config.dingtalk_config:
            try:
                title = f"V4PRO 置信度告警 - {alert_type}"
                send_markdown(self._config.dingtalk_config, title, message)
                record.sent_successfully = True
                logger.info("钉钉告警发送成功: %s", alert_type)
            except Exception as e:
                logger.error("钉钉告警发送失败: %s", e)
                record.sent_successfully = False
        else:
            # 无钉钉配置，仅记录日志
            logger.warning("置信度告警 [%s]: %s", alert_type, message)
            record.sent_successfully = True  # 日志记录视为成功

        return record.sent_successfully


# =============================================================================
# 便捷函数
# =============================================================================


def create_confidence_monitor(
    assessor: ConfidenceAssessor | None = None,
    dingtalk_webhook: str | None = None,
    dingtalk_secret: str | None = None,
    low_threshold: float = 0.70,
) -> ConfidenceMonitor:
    """创建置信度监控器.

    参数:
        assessor: 置信度评估器 (可选，默认创建新实例)
        dingtalk_webhook: 钉钉 webhook URL (可选)
        dingtalk_secret: 钉钉密钥 (可选)
        low_threshold: 低置信度阈值

    返回:
        置信度监控器实例
    """
    if assessor is None:
        assessor = ConfidenceAssessor()

    dingtalk_config = None
    if dingtalk_webhook:
        dingtalk_config = DingTalkConfig(
            webhook_url=dingtalk_webhook,
            secret=dingtalk_secret,
        )

    config = ConfidenceMonitorConfig(
        low_confidence_threshold=low_threshold,
        dingtalk_config=dingtalk_config,
    )

    return ConfidenceMonitor(assessor, config)


def quick_monitor_check(
    result: ConfidenceResult,
    threshold: float = 0.70,
) -> dict[str, Any]:
    """快速监控检查.

    参数:
        result: 置信度评估结果
        threshold: 低置信度阈值

    返回:
        监控检查结果字典
    """
    is_low = result.score < threshold
    is_critical = result.level == ConfidenceLevel.LOW

    return {
        "score": result.score,
        "level": result.level.value,
        "is_low": is_low,
        "is_critical": is_critical,
        "needs_attention": is_low or is_critical,
        "recommendation": result.recommendation,
        "timestamp": result.timestamp,
    }
