"""置信度API接口模块 (军规级 v4.4).

V4PRO Platform Component - 置信度评估API
军规覆盖: M3(完整审计), M19(风险归因)

V4PRO Scenarios:
- K56: CONFIDENCE.API.ASSESS - API评估接口
- K57: CONFIDENCE.API.STATS - 统计查询接口
- K58: CONFIDENCE.API.TREND - 趋势查询接口

提供无框架依赖的API层，易于集成FastAPI/Flask等Web框架。

示例:
    >>> from src.risk.confidence_api import ConfidenceAPI, ConfidenceAPIRequest
    >>> api = ConfidenceAPI()
    >>> request = ConfidenceAPIRequest(
    ...     task_type="STRATEGY_EXECUTION",
    ...     task_name="test_strategy",
    ...     context_data={"duplicate_check_complete": True}
    ... )
    >>> response = api.assess(request)
    >>> print(f"Score: {response.score:.0%}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceContext,
    ConfidenceResult,
    TaskType,
)


logger = logging.getLogger(__name__)


# =============================================================================
# API 请求/响应数据类
# =============================================================================


@dataclass
class ConfidenceAPIRequest:
    """置信度评估API请求.

    属性:
        task_type: 任务类型 (字符串)
        task_name: 任务名称
        context_data: 上下文数据字典
        request_id: 请求ID (可选)
    """

    task_type: str
    task_name: str = ""
    context_data: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self) -> None:
        """初始化后处理."""
        if not self.request_id:
            self.request_id = f"req_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"  # noqa: DTZ005

    def to_context(self) -> ConfidenceContext:
        """转换为 ConfidenceContext.

        返回:
            置信度评估上下文

        异常:
            ValueError: 无效的任务类型
        """
        # 解析任务类型
        try:
            task_type = TaskType(self.task_type)
        except ValueError:
            raise ValueError(f"无效的任务类型: {self.task_type}") from None

        # 构建上下文
        return ConfidenceContext(
            task_type=task_type,
            task_name=self.task_name,
            symbol=self.context_data.get("symbol", ""),
            strategy_id=self.context_data.get("strategy_id", ""),
            # 预执行检查项
            duplicate_check_complete=self.context_data.get(
                "duplicate_check_complete", False
            ),
            architecture_verified=self.context_data.get("architecture_verified", False),
            has_official_docs=self.context_data.get("has_official_docs", False),
            has_oss_reference=self.context_data.get("has_oss_reference", False),
            root_cause_identified=self.context_data.get("root_cause_identified", False),
            # 信号检查项
            signal_strength=self.context_data.get("signal_strength", 0.0),
            signal_consistency=self.context_data.get("signal_consistency", 0.0),
            market_condition=self.context_data.get("market_condition", "NORMAL"),
            risk_within_limits=self.context_data.get("risk_within_limits", True),
            # 扩展检查项
            volatility=self.context_data.get("volatility", 0.0),
            liquidity_score=self.context_data.get("liquidity_score", 1.0),
            historical_win_rate=self.context_data.get("historical_win_rate", 0.5),
            position_concentration=self.context_data.get("position_concentration", 0.0),
            # 高级检查项
            backtest_sample_size=self.context_data.get("backtest_sample_size", 0),
            backtest_sharpe=self.context_data.get("backtest_sharpe", 0.0),
            external_signal_valid=self.context_data.get("external_signal_valid", False),
            external_signal_correlation=self.context_data.get(
                "external_signal_correlation", 0.0
            ),
            regime_alignment=self.context_data.get("regime_alignment", False),
            current_regime=self.context_data.get("current_regime", "UNKNOWN"),
            strategy_regime=self.context_data.get("strategy_regime", "UNKNOWN"),
            cross_asset_correlation=self.context_data.get(
                "cross_asset_correlation", 0.0
            ),
            # 元数据
            metadata=self.context_data.get("metadata", {}),
        )

    def to_json(self) -> str:
        """转换为JSON字符串."""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> ConfidenceAPIRequest:
        """从JSON字符串创建请求.

        参数:
            json_str: JSON字符串

        返回:
            API请求对象
        """
        data = json.loads(json_str)
        return cls(
            task_type=data.get("task_type", ""),
            task_name=data.get("task_name", ""),
            context_data=data.get("context_data", {}),
            request_id=data.get("request_id", ""),
        )


@dataclass(frozen=True)
class ConfidenceAPIResponse:
    """置信度评估API响应.

    属性:
        score: 置信度分数 (0.0-1.0)
        level: 置信度等级
        can_proceed: 是否可以继续
        checks: 检查结果列表
        recommendation: 建议操作
        timestamp: 时间戳
        request_id: 关联的请求ID
        success: 是否成功
        error: 错误信息 (如果有)
    """

    score: float
    level: str
    can_proceed: bool
    checks: tuple[dict[str, Any], ...]
    recommendation: str
    timestamp: str
    request_id: str = ""
    success: bool = True
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "score": round(self.score, 4),
            "level": self.level,
            "can_proceed": self.can_proceed,
            "checks": list(self.checks),
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "success": self.success,
            "error": self.error,
        }

    def to_json(self) -> str:
        """转换为JSON字符串."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_result(
        cls,
        result: ConfidenceResult,
        request_id: str = "",
    ) -> ConfidenceAPIResponse:
        """从 ConfidenceResult 创建响应.

        参数:
            result: 置信度评估结果
            request_id: 关联的请求ID

        返回:
            API响应对象
        """
        return cls(
            score=result.score,
            level=result.level.value,
            can_proceed=result.can_proceed,
            checks=tuple(c.to_dict() for c in result.checks),
            recommendation=result.recommendation,
            timestamp=result.timestamp,
            request_id=request_id,
            success=True,
            error="",
        )

    @classmethod
    def error_response(
        cls,
        error: str,
        request_id: str = "",
    ) -> ConfidenceAPIResponse:
        """创建错误响应.

        参数:
            error: 错误信息
            request_id: 关联的请求ID

        返回:
            错误响应对象
        """
        return cls(
            score=0.0,
            level="ERROR",
            can_proceed=False,
            checks=(),
            recommendation="",
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
            request_id=request_id,
            success=False,
            error=error,
        )


@dataclass(frozen=True)
class StatisticsResponse:
    """统计信息响应.

    属性:
        total_assessments: 总评估次数
        high_count: 高置信度次数
        medium_count: 中等置信度次数
        low_count: 低置信度次数
        high_rate: 高置信度比例
        medium_rate: 中等置信度比例
        low_rate: 低置信度比例
        timestamp: 查询时间戳
    """

    total_assessments: int
    high_count: int
    medium_count: int
    low_count: int
    high_rate: float
    medium_rate: float
    low_rate: float
    timestamp: str = ""

    def __post_init__(self) -> None:
        """初始化后处理."""
        if not self.timestamp:
            # frozen=True 时需要使用 object.__setattr__
            object.__setattr__(
                self, "timestamp", datetime.now().isoformat()  # noqa: DTZ005
            )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "total_assessments": self.total_assessments,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "high_rate": round(self.high_rate, 4),
            "medium_rate": round(self.medium_rate, 4),
            "low_rate": round(self.low_rate, 4),
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """转换为JSON字符串."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass(frozen=True)
class TrendResponse:
    """趋势分析响应.

    属性:
        trend: 趋势状态 (IMPROVING/STABLE/DECLINING/INSUFFICIENT_DATA)
        direction: 方向 (UP/DOWN/NEUTRAL)
        recent_avg: 近期平均
        overall_avg: 总体平均
        alert: 是否触发告警
        alert_message: 告警消息
        history_count: 历史记录数
        timestamp: 查询时间戳
    """

    trend: str
    direction: str
    recent_avg: float
    overall_avg: float
    alert: bool
    alert_message: str
    history_count: int
    timestamp: str = ""

    def __post_init__(self) -> None:
        """初始化后处理."""
        if not self.timestamp:
            object.__setattr__(
                self, "timestamp", datetime.now().isoformat()  # noqa: DTZ005
            )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "trend": self.trend,
            "direction": self.direction,
            "recent_avg": round(self.recent_avg, 4),
            "overall_avg": round(self.overall_avg, 4),
            "alert": self.alert,
            "alert_message": self.alert_message,
            "history_count": self.history_count,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """转换为JSON字符串."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


# =============================================================================
# API 服务类
# =============================================================================


class ConfidenceAPI:
    """置信度评估API服务.

    提供无框架依赖的API层，支持:
    - 置信度评估
    - 统计查询
    - 趋势分析
    - 批量评估

    示例:
        >>> api = ConfidenceAPI()
        >>> request = ConfidenceAPIRequest(
        ...     task_type="STRATEGY_EXECUTION",
        ...     context_data={"duplicate_check_complete": True}
        ... )
        >>> response = api.assess(request)
        >>> print(response.to_json())
    """

    def __init__(
        self,
        assessor: ConfidenceAssessor | None = None,
        *,
        high_threshold: float = 0.90,
        medium_threshold: float = 0.70,
        adaptive_mode: bool = False,
    ) -> None:
        """初始化API服务.

        参数:
            assessor: 置信度评估器 (可选)
            high_threshold: 高置信度阈值
            medium_threshold: 中等置信度阈值
            adaptive_mode: 是否启用自适应模式
        """
        if assessor is None:
            assessor = ConfidenceAssessor(
                high_threshold=high_threshold,
                medium_threshold=medium_threshold,
                adaptive_mode=adaptive_mode,
            )
        self._assessor = assessor

    @property
    def assessor(self) -> ConfidenceAssessor:
        """获取评估器实例."""
        return self._assessor

    def assess(self, request: ConfidenceAPIRequest) -> ConfidenceAPIResponse:
        """评估置信度.

        参数:
            request: API请求

        返回:
            API响应

        场景: K56
        """
        try:
            context = request.to_context()
            result = self._assessor.assess(context)
            return ConfidenceAPIResponse.from_result(result, request.request_id)
        except ValueError as e:
            logger.error("评估请求参数错误: %s", e)
            return ConfidenceAPIResponse.error_response(str(e), request.request_id)
        except Exception as e:
            logger.exception("评估过程发生异常")
            return ConfidenceAPIResponse.error_response(
                f"评估失败: {e}", request.request_id
            )

    def assess_batch(
        self, requests: list[ConfidenceAPIRequest]
    ) -> list[ConfidenceAPIResponse]:
        """批量评估置信度.

        参数:
            requests: 请求列表

        返回:
            响应列表
        """
        return [self.assess(req) for req in requests]

    def get_statistics(self) -> StatisticsResponse:
        """获取统计信息.

        返回:
            统计响应

        场景: K57
        """
        stats = self._assessor.get_statistics()
        return StatisticsResponse(
            total_assessments=stats["total_assessments"],
            high_count=stats["high_confidence_count"],
            medium_count=stats["medium_confidence_count"],
            low_count=stats["low_confidence_count"],
            high_rate=stats["high_rate"],
            medium_rate=stats["medium_rate"],
            low_rate=stats["low_rate"],
        )

    def get_trend(self) -> TrendResponse:
        """获取趋势分析.

        返回:
            趋势响应

        场景: K58
        """
        trend = self._assessor.get_trend_analysis()
        return TrendResponse(
            trend=trend["trend"],
            direction=trend.get("direction", "NEUTRAL"),
            recent_avg=trend.get("recent_avg", 0.0),
            overall_avg=trend.get("overall_avg", 0.0),
            alert=trend.get("alert", False),
            alert_message=trend.get("alert_message", ""),
            history_count=trend.get("history_count", 0),
        )

    def reset(self) -> None:
        """重置统计信息."""
        self._assessor.reset_statistics()
        logger.info("API统计已重置")

    def health_check(self) -> dict[str, Any]:
        """健康检查.

        返回:
            健康状态字典
        """
        trend = self.get_trend()
        stats = self.get_statistics()

        is_healthy = not trend.alert
        if stats.total_assessments > 0:
            is_healthy = is_healthy and trend.recent_avg >= 0.5

        return {
            "healthy": is_healthy,
            "total_assessments": stats.total_assessments,
            "trend": trend.trend,
            "recent_avg": trend.recent_avg,
            "alert": trend.alert,
            "timestamp": datetime.now().isoformat(),  # noqa: DTZ005
        }


# =============================================================================
# 便捷函数
# =============================================================================


def create_api(
    *,
    high_threshold: float = 0.90,
    medium_threshold: float = 0.70,
    adaptive_mode: bool = False,
) -> ConfidenceAPI:
    """创建API服务实例.

    参数:
        high_threshold: 高置信度阈值
        medium_threshold: 中等置信度阈值
        adaptive_mode: 是否启用自适应模式

    返回:
        API服务实例
    """
    return ConfidenceAPI(
        high_threshold=high_threshold,
        medium_threshold=medium_threshold,
        adaptive_mode=adaptive_mode,
    )


def quick_assess(
    task_type: str,
    **context_data: Any,
) -> ConfidenceAPIResponse:
    """快速评估.

    参数:
        task_type: 任务类型
        **context_data: 上下文数据

    返回:
        API响应
    """
    api = ConfidenceAPI()
    request = ConfidenceAPIRequest(
        task_type=task_type,
        context_data=context_data,
    )
    return api.assess(request)


def assess_from_json(json_str: str) -> str:
    """从JSON评估并返回JSON.

    参数:
        json_str: JSON请求字符串

    返回:
        JSON响应字符串
    """
    api = ConfidenceAPI()
    request = ConfidenceAPIRequest.from_json(json_str)
    response = api.assess(request)
    return response.to_json()
