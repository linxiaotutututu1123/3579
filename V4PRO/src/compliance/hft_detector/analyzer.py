"""
HFT模式分析器模块 - HFT Pattern Analyzer (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.HFT_ANALYSIS: 高频交易模式分析
- CHINA.COMPLIANCE.BEHAVIOR_PROFILE: 交易行为画像
- CHINA.COMPLIANCE.RISK_ASSESSMENT: 风险评估

军规覆盖:
- M3: 审计日志完整 - 分析结果必须记录审计日志
- M17: 程序化合规 - 识别并标记HFT交易模式

功能特性:
- HFT模式识别 (做市、动量、套利、分层等)
- 账户行为画像生成
- 风险等级评估 (低/中/高/极高)
- 与detector/tracker集成共享数据

示例:
    >>> from src.compliance.hft_detector.analyzer import (
    ...     HFTPatternAnalyzer,
    ...     TradingPattern,
    ...     RiskLevel,
    ... )
    >>> analyzer = HFTPatternAnalyzer()
    >>> profile = analyzer.analyze_account("acc_001", order_flows)
    >>> print(f"风险等级: {profile.risk_level.value}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from src.compliance.hft_detector.detector import OrderFlow

logger = logging.getLogger(__name__)


# ============================================================
# 枚举定义
# ============================================================


class TradingPattern(Enum):
    """HFT交易模式枚举."""

    UNKNOWN = "UNKNOWN"              # 未知模式
    MARKET_MAKING = "MARKET_MAKING"  # 做市策略 - 双边挂单赚取价差
    MOMENTUM = "MOMENTUM"            # 动量策略 - 追踪价格趋势
    ARBITRAGE = "ARBITRAGE"          # 套利策略 - 跨市场/品种套利
    LAYERING = "LAYERING"            # 分层策略 - 多层挂单影响价格
    SPOOFING = "SPOOFING"            # 幌骗策略 - 虚假挂单误导市场
    SCALPING = "SCALPING"            # 剥头皮策略 - 极短期小利润
    NORMAL = "NORMAL"                # 正常交易


class RiskLevel(Enum):
    """风险等级枚举."""

    LOW = "LOW"            # 低风险 - 正常交易行为
    MEDIUM = "MEDIUM"      # 中风险 - 需关注
    HIGH = "HIGH"          # 高风险 - 需要审查
    CRITICAL = "CRITICAL"  # 极高风险 - 可能违规

    @property
    def severity(self) -> int:
        """获取严重程度数值 (0-3)."""
        severity_map = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return severity_map.get(self, 0)


# ============================================================
# 数据结构定义
# ============================================================


@dataclass(frozen=True)
class PatternIndicator:
    """模式指标 (不可变).

    属性:
        pattern: 交易模式
        confidence: 置信度 (0-1)
        evidence: 判定依据描述
    """

    pattern: TradingPattern
    confidence: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "pattern": self.pattern.value,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
        }


@dataclass
class BehaviorProfile:
    """账户行为画像.

    属性:
        account_id: 账户ID
        analysis_time: 分析时间 (ISO格式)
        primary_pattern: 主要交易模式
        pattern_indicators: 各模式指标列表
        risk_level: 风险等级
        order_frequency_avg: 平均订单频率 (笔/秒)
        cancel_ratio_avg: 平均撤单比例 (0-1)
        avg_holding_time_ms: 平均持仓时间 (毫秒)
        buy_sell_ratio: 买卖比例
        symbol_diversity: 品种多样性 (交易品种数)
        risk_factors: 风险因素列表
        recommendation: 建议措施
        military_rule: 关联军规
    """

    account_id: str
    analysis_time: str = ""
    primary_pattern: TradingPattern = TradingPattern.UNKNOWN
    pattern_indicators: list[PatternIndicator] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    order_frequency_avg: float = 0.0
    cancel_ratio_avg: float = 0.0
    avg_holding_time_ms: float = 0.0
    buy_sell_ratio: float = 1.0
    symbol_diversity: int = 0
    risk_factors: list[str] = field(default_factory=list)
    recommendation: str = ""
    military_rule: str = "M17"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "account_id": self.account_id,
            "analysis_time": self.analysis_time,
            "primary_pattern": self.primary_pattern.value,
            "pattern_indicators": [p.to_dict() for p in self.pattern_indicators],
            "risk_level": self.risk_level.value,
            "order_frequency_avg": round(self.order_frequency_avg, 2),
            "cancel_ratio_avg": round(self.cancel_ratio_avg, 4),
            "avg_holding_time_ms": round(self.avg_holding_time_ms, 2),
            "buy_sell_ratio": round(self.buy_sell_ratio, 2),
            "symbol_diversity": self.symbol_diversity,
            "risk_factors": self.risk_factors,
            "recommendation": self.recommendation,
            "military_rule": self.military_rule,
        }


@dataclass(frozen=True)
class AnalyzerConfig:
    """分析器配置 (不可变).

    属性:
        min_orders_for_analysis: 最小订单数要求
        high_freq_threshold: 高频阈值 (笔/秒)
        high_cancel_ratio: 高撤单比例阈值
        short_holding_ms: 短持仓时间阈值 (毫秒)
        layering_depth_threshold: 分层深度阈值
    """

    min_orders_for_analysis: int = 10
    high_freq_threshold: float = 100.0
    high_cancel_ratio: float = 0.4
    short_holding_ms: float = 1000.0
    layering_depth_threshold: int = 5


# ============================================================
# 主类实现
# ============================================================


class HFTPatternAnalyzer:
    """HFT模式分析器 (军规 M3/M17).

    功能:
    - HFT模式识别 (做市、动量、套利、分层等)
    - 账户行为画像生成
    - 风险等级评估 (低/中/高/极高)
    - 与detector/tracker集成共享数据

    示例:
        >>> analyzer = HFTPatternAnalyzer()
        >>> profile = analyzer.analyze_account("acc_001", order_flows)
        >>> if profile.risk_level == RiskLevel.CRITICAL:
        ...     print("极高风险账户，需立即审查")
    """

    VERSION = "4.0"

    def __init__(
        self,
        config: AnalyzerConfig | None = None,
        audit_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """初始化HFT模式分析器.

        参数:
            config: 分析器配置 (None使用默认配置)
            audit_callback: 审计回调函数 (可选)
        """
        self._config = config or AnalyzerConfig()
        self._audit_callback = audit_callback
        self._analysis_count: int = 0

    @property
    def config(self) -> AnalyzerConfig:
        """获取配置."""
        return self._config

    def analyze_account(
        self,
        account_id: str,
        order_flows: list[OrderFlow],
    ) -> BehaviorProfile:
        """分析账户交易行为.

        参数:
            account_id: 账户ID
            order_flows: 订单流列表

        返回:
            账户行为画像
        """
        self._analysis_count += 1
        analysis_time = datetime.now().isoformat()  # noqa: DTZ005

        if len(order_flows) < self._config.min_orders_for_analysis:
            return BehaviorProfile(
                account_id=account_id,
                analysis_time=analysis_time,
                primary_pattern=TradingPattern.UNKNOWN,
                risk_level=RiskLevel.LOW,
                recommendation="订单数量不足，无法进行有效分析",
            )

        # 计算基础指标
        metrics = self._calculate_metrics(order_flows)

        # 识别交易模式
        indicators = self._identify_patterns(order_flows, metrics)

        # 确定主要模式
        primary = self._determine_primary_pattern(indicators)

        # 评估风险等级
        risk_level, risk_factors = self._assess_risk(metrics, indicators)

        # 生成建议
        recommendation = self._generate_recommendation(risk_level, risk_factors)

        profile = BehaviorProfile(
            account_id=account_id,
            analysis_time=analysis_time,
            primary_pattern=primary,
            pattern_indicators=indicators,
            risk_level=risk_level,
            order_frequency_avg=metrics["order_frequency"],
            cancel_ratio_avg=metrics["cancel_ratio"],
            avg_holding_time_ms=metrics["avg_holding_time"],
            buy_sell_ratio=metrics["buy_sell_ratio"],
            symbol_diversity=metrics["symbol_count"],
            risk_factors=risk_factors,
            recommendation=recommendation,
        )

        # M3军规: 记录审计日志
        if self._audit_callback:
            self._audit_callback(profile.to_dict())

        return profile

    def _calculate_metrics(
        self,
        order_flows: list[OrderFlow],
    ) -> dict[str, Any]:
        """计算基础指标."""
        total = len(order_flows)
        cancels = sum(1 for o in order_flows if o.event_type == "cancel")
        buys = sum(1 for o in order_flows if o.direction == "buy")
        symbols = {o.symbol for o in order_flows if o.symbol}

        # 计算时间跨度
        timestamps = [o.timestamp for o in order_flows]
        time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1.0

        # 计算平均往返时间
        rtts = [o.round_trip_ms for o in order_flows if o.round_trip_ms > 0]
        avg_rtt = sum(rtts) / len(rtts) if rtts else 0.0

        return {
            "order_frequency": total / time_span if time_span > 0 else 0.0,
            "cancel_ratio": cancels / total if total > 0 else 0.0,
            "buy_sell_ratio": buys / (total - buys) if (total - buys) > 0 else 1.0,
            "symbol_count": len(symbols),
            "avg_holding_time": avg_rtt,
            "total_orders": total,
        }

    def _identify_patterns(
        self,
        order_flows: list[OrderFlow],
        metrics: dict[str, Any],
    ) -> list[PatternIndicator]:
        """识别交易模式."""
        indicators: list[PatternIndicator] = []

        # 做市模式检测: 双向交易且撤单比例适中
        if 0.4 <= metrics["buy_sell_ratio"] <= 0.6:
            conf = 0.7 if metrics["cancel_ratio"] < 0.3 else 0.5
            indicators.append(PatternIndicator(
                pattern=TradingPattern.MARKET_MAKING,
                confidence=conf,
                evidence="买卖比例接近1:1，符合做市特征",
            ))

        # 动量模式检测: 单边交易为主
        if metrics["buy_sell_ratio"] > 0.8 or metrics["buy_sell_ratio"] < 0.2:
            indicators.append(PatternIndicator(
                pattern=TradingPattern.MOMENTUM,
                confidence=0.6,
                evidence="单边交易占比超过80%，疑似动量策略",
            ))

        # 剥头皮模式检测: 高频率+短持仓
        if (metrics["order_frequency"] > self._config.high_freq_threshold
                and metrics["avg_holding_time"] < self._config.short_holding_ms):
            indicators.append(PatternIndicator(
                pattern=TradingPattern.SCALPING,
                confidence=0.8,
                evidence="高频交易且持仓时间极短，符合剥头皮特征",
            ))

        # 分层/幌骗模式检测: 高撤单比例
        if metrics["cancel_ratio"] > self._config.high_cancel_ratio:
            conf = 0.7 if metrics["cancel_ratio"] > 0.6 else 0.5
            indicators.append(PatternIndicator(
                pattern=TradingPattern.LAYERING,
                confidence=conf,
                evidence=f"撤单比例达{metrics['cancel_ratio']:.1%}，疑似分层策略",
            ))

        # 套利模式检测: 多品种交易
        if metrics["symbol_count"] >= 3:
            indicators.append(PatternIndicator(
                pattern=TradingPattern.ARBITRAGE,
                confidence=0.5,
                evidence=f"交易品种达{metrics['symbol_count']}个，可能存在套利行为",
            ))

        # 正常交易
        if not indicators:
            indicators.append(PatternIndicator(
                pattern=TradingPattern.NORMAL,
                confidence=0.9,
                evidence="未检测到明显HFT特征",
            ))

        return indicators

    def _determine_primary_pattern(
        self,
        indicators: list[PatternIndicator],
    ) -> TradingPattern:
        """确定主要交易模式."""
        if not indicators:
            return TradingPattern.UNKNOWN
        # 选择置信度最高的模式
        best = max(indicators, key=lambda x: x.confidence)
        return best.pattern

    def _assess_risk(
        self,
        metrics: dict[str, Any],
        indicators: list[PatternIndicator],
    ) -> tuple[RiskLevel, list[str]]:
        """评估风险等级."""
        factors: list[str] = []
        score = 0

        # 高频交易风险
        if metrics["order_frequency"] > self._config.high_freq_threshold:
            factors.append(f"订单频率过高: {metrics['order_frequency']:.1f}笔/秒")
            score += 2

        # 高撤单比例风险
        if metrics["cancel_ratio"] > self._config.high_cancel_ratio:
            factors.append(f"撤单比例过高: {metrics['cancel_ratio']:.1%}")
            score += 2

        # 分层/幌骗风险
        for ind in indicators:
            if ind.pattern in (TradingPattern.LAYERING, TradingPattern.SPOOFING):
                factors.append(f"检测到{ind.pattern.value}模式")
                score += 3

        # 确定风险等级
        if score >= 5:
            return RiskLevel.CRITICAL, factors
        if score >= 3:
            return RiskLevel.HIGH, factors
        if score >= 1:
            return RiskLevel.MEDIUM, factors
        return RiskLevel.LOW, factors

    def _generate_recommendation(
        self,
        risk_level: RiskLevel,
        risk_factors: list[str],
    ) -> str:
        """生成建议措施."""
        if risk_level == RiskLevel.LOW:
            return "交易行为正常，继续监控"
        if risk_level == RiskLevel.MEDIUM:
            return "建议关注交易频率，适当降低撤单比例"
        if risk_level == RiskLevel.HIGH:
            return "建议: 1) 降低交易频率; 2) 检查策略合规性; 3) 联系合规部门"
        return "警告: 立即停止交易，联系合规部门进行审查"

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        return {
            "analysis_count": self._analysis_count,
            "version": self.VERSION,
            "military_rule": "M3/M17",
        }


# ============================================================
# 便捷函数
# ============================================================


def create_analyzer(
    config: AnalyzerConfig | None = None,
    audit_callback: Callable[[dict[str, Any]], None] | None = None,
) -> HFTPatternAnalyzer:
    """创建HFT模式分析器."""
    return HFTPatternAnalyzer(config, audit_callback)


__all__ = [
    "TradingPattern",
    "RiskLevel",
    "PatternIndicator",
    "BehaviorProfile",
    "AnalyzerConfig",
    "HFTPatternAnalyzer",
    "create_analyzer",
]
