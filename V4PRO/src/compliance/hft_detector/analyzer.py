"""
HFT模式分析器模块 - HFT Pattern Analyzer (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
军规覆盖: M3(审计日志完整), M17(程序化合规)

功能: HFT模式识别、账户行为画像、风险等级评估
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


class TradingPattern(Enum):
    """HFT交易模式枚举."""
    UNKNOWN = "UNKNOWN"
    MARKET_MAKING = "MARKET_MAKING"  # 做市策略
    MOMENTUM = "MOMENTUM"            # 动量策略
    ARBITRAGE = "ARBITRAGE"          # 套利策略
    LAYERING = "LAYERING"            # 分层策略
    SPOOFING = "SPOOFING"            # 幌骗策略
    SCALPING = "SCALPING"            # 剥头皮策略
    NORMAL = "NORMAL"                # 正常交易


class RiskLevel(Enum):
    """风险等级枚举."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @property
    def severity(self) -> int:
        """获取严重程度数值 (0-3)."""
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}.get(self.value, 0)


@dataclass(frozen=True)
class PatternIndicator:
    """模式指标."""
    pattern: TradingPattern
    confidence: float
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return {"pattern": self.pattern.value, "confidence": round(self.confidence, 3), "evidence": self.evidence}


@dataclass
class BehaviorProfile:
    """账户行为画像."""
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
        return {
            "account_id": self.account_id, "analysis_time": self.analysis_time,
            "primary_pattern": self.primary_pattern.value,
            "pattern_indicators": [p.to_dict() for p in self.pattern_indicators],
            "risk_level": self.risk_level.value, "order_frequency_avg": round(self.order_frequency_avg, 2),
            "cancel_ratio_avg": round(self.cancel_ratio_avg, 4), "buy_sell_ratio": round(self.buy_sell_ratio, 2),
            "symbol_diversity": self.symbol_diversity, "risk_factors": self.risk_factors,
            "recommendation": self.recommendation, "military_rule": self.military_rule,
        }


@dataclass(frozen=True)
class AnalyzerConfig:
    """分析器配置."""
    min_orders_for_analysis: int = 10
    high_freq_threshold: float = 100.0
    high_cancel_ratio: float = 0.4
    short_holding_ms: float = 1000.0


class HFTPatternAnalyzer:
    """HFT模式分析器 (军规 M3/M17)."""

    VERSION = "4.0"

    def __init__(self, config: AnalyzerConfig | None = None,
                 audit_callback: Callable[[dict[str, Any]], None] | None = None) -> None:
        self._config = config or AnalyzerConfig()
        self._audit_callback = audit_callback
        self._analysis_count: int = 0

    @property
    def config(self) -> AnalyzerConfig:
        return self._config

    def analyze_account(self, account_id: str, order_flows: list[OrderFlow]) -> BehaviorProfile:
        """分析账户交易行为，返回行为画像."""
        self._analysis_count += 1
        analysis_time = datetime.now().isoformat()  # noqa: DTZ005

        if len(order_flows) < self._config.min_orders_for_analysis:
            return BehaviorProfile(account_id=account_id, analysis_time=analysis_time,
                                   recommendation="订单数量不足，无法进行有效分析")

        metrics = self._calculate_metrics(order_flows)
        indicators = self._identify_patterns(metrics)
        primary = max(indicators, key=lambda x: x.confidence).pattern if indicators else TradingPattern.UNKNOWN
        risk_level, risk_factors = self._assess_risk(metrics, indicators)

        profile = BehaviorProfile(
            account_id=account_id, analysis_time=analysis_time, primary_pattern=primary,
            pattern_indicators=indicators, risk_level=risk_level,
            order_frequency_avg=metrics["order_frequency"], cancel_ratio_avg=metrics["cancel_ratio"],
            avg_holding_time_ms=metrics["avg_holding_time"], buy_sell_ratio=metrics["buy_sell_ratio"],
            symbol_diversity=metrics["symbol_count"], risk_factors=risk_factors,
            recommendation=self._generate_recommendation(risk_level),
        )

        if self._audit_callback:
            self._audit_callback(profile.to_dict())
        return profile

    def _calculate_metrics(self, order_flows: list[OrderFlow]) -> dict[str, Any]:
        """计算基础指标."""
        total = len(order_flows)
        cancels = sum(1 for o in order_flows if o.event_type == "cancel")
        buys = sum(1 for o in order_flows if o.direction == "buy")
        symbols = {o.symbol for o in order_flows if o.symbol}
        timestamps = [o.timestamp for o in order_flows]
        time_span = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 1.0
        rtts = [o.round_trip_ms for o in order_flows if o.round_trip_ms > 0]

        return {
            "order_frequency": total / time_span if time_span > 0 else 0.0,
            "cancel_ratio": cancels / total if total > 0 else 0.0,
            "buy_sell_ratio": buys / (total - buys) if (total - buys) > 0 else 1.0,
            "symbol_count": len(symbols),
            "avg_holding_time": sum(rtts) / len(rtts) if rtts else 0.0,
        }

    def _identify_patterns(self, metrics: dict[str, Any]) -> list[PatternIndicator]:
        """识别交易模式."""
        indicators: list[PatternIndicator] = []

        # 做市模式: 双向交易
        if 0.4 <= metrics["buy_sell_ratio"] <= 0.6:
            indicators.append(PatternIndicator(TradingPattern.MARKET_MAKING, 0.7 if metrics["cancel_ratio"] < 0.3 else 0.5,
                                               "买卖比例接近1:1，符合做市特征"))

        # 动量模式: 单边交易
        if metrics["buy_sell_ratio"] > 0.8 or metrics["buy_sell_ratio"] < 0.2:
            indicators.append(PatternIndicator(TradingPattern.MOMENTUM, 0.6, "单边交易占比超过80%，疑似动量策略"))

        # 剥头皮模式: 高频+短持仓
        if metrics["order_frequency"] > self._config.high_freq_threshold and metrics["avg_holding_time"] < self._config.short_holding_ms:
            indicators.append(PatternIndicator(TradingPattern.SCALPING, 0.8, "高频交易且持仓时间极短"))

        # 分层模式: 高撤单比例
        if metrics["cancel_ratio"] > self._config.high_cancel_ratio:
            indicators.append(PatternIndicator(TradingPattern.LAYERING, 0.7 if metrics["cancel_ratio"] > 0.6 else 0.5,
                                               f"撤单比例达{metrics['cancel_ratio']:.1%}，疑似分层策略"))

        # 套利模式: 多品种
        if metrics["symbol_count"] >= 3:
            indicators.append(PatternIndicator(TradingPattern.ARBITRAGE, 0.5, f"交易品种达{metrics['symbol_count']}个"))

        if not indicators:
            indicators.append(PatternIndicator(TradingPattern.NORMAL, 0.9, "未检测到明显HFT特征"))

        return indicators

    def _assess_risk(self, metrics: dict[str, Any], indicators: list[PatternIndicator]) -> tuple[RiskLevel, list[str]]:
        """评估风险等级."""
        factors, score = [], 0

        if metrics["order_frequency"] > self._config.high_freq_threshold:
            factors.append(f"订单频率过高: {metrics['order_frequency']:.1f}笔/秒")
            score += 2
        if metrics["cancel_ratio"] > self._config.high_cancel_ratio:
            factors.append(f"撤单比例过高: {metrics['cancel_ratio']:.1%}")
            score += 2
        for ind in indicators:
            if ind.pattern in (TradingPattern.LAYERING, TradingPattern.SPOOFING):
                factors.append(f"检测到{ind.pattern.value}模式")
                score += 3

        if score >= 5:
            return RiskLevel.CRITICAL, factors
        if score >= 3:
            return RiskLevel.HIGH, factors
        if score >= 1:
            return RiskLevel.MEDIUM, factors
        return RiskLevel.LOW, factors

    def _generate_recommendation(self, risk_level: RiskLevel) -> str:
        """生成建议措施."""
        recs = {
            RiskLevel.LOW: "交易行为正常，继续监控",
            RiskLevel.MEDIUM: "建议关注交易频率，适当降低撤单比例",
            RiskLevel.HIGH: "建议: 1) 降低交易频率; 2) 检查策略合规性; 3) 联系合规部门",
            RiskLevel.CRITICAL: "警告: 立即停止交易，联系合规部门进行审查",
        }
        return recs.get(risk_level, "")

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        return {"analysis_count": self._analysis_count, "version": self.VERSION, "military_rule": "M3/M17"}


def create_analyzer(config: AnalyzerConfig | None = None,
                    audit_callback: Callable[[dict[str, Any]], None] | None = None) -> HFTPatternAnalyzer:
    """创建HFT模式分析器."""
    return HFTPatternAnalyzer(config, audit_callback)


__all__ = ["TradingPattern", "RiskLevel", "PatternIndicator", "BehaviorProfile", "AnalyzerConfig",
           "HFTPatternAnalyzer", "create_analyzer"]
