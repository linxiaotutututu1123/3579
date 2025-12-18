"""
动态VaR风险引擎 (军规级 v4.2).

V4PRO Platform Component - Phase 10 组合风控增强
V4 SPEC: §22 VaR风控增强

军规覆盖:
- M6: 熔断保护 - 极端风险预警
- M13: 涨跌停感知 - 涨跌停调整VaR
- M16: 保证金监控 - 流动性调整VaR

功能特性:
- EVT极值理论VaR (POT + GPD)
- 半参数VaR (核密度 + GPD)
- 涨跌停调整VaR
- 流动性调整VaR
- 动态更新机制

示例:
    >>> from src.risk.dynamic_var import DynamicVaREngine
    >>> engine = DynamicVaREngine()
    >>> result = engine.evt_var(returns, confidence=0.99)
    >>> limit_var = engine.limit_adjusted_var(returns, limit_pct=0.10)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

from src.risk.var_calculator import VaRCalculator, VaRResult


class VaRMethod(Enum):
    """VaR计算方法枚举."""

    HISTORICAL = "historical"  # 历史模拟法
    PARAMETRIC = "parametric"  # 参数法
    MONTE_CARLO = "monte_carlo"  # 蒙特卡洛
    EVT_GPD = "evt_gpd"  # 极值理论GPD
    SEMIPARAMETRIC = "semiparametric"  # 半参数法
    LIMIT_ADJUSTED = "limit_adjusted"  # 涨跌停调整
    LIQUIDITY_ADJUSTED = "liquidity_adjusted"  # 流动性调整


class RiskLevel(Enum):
    """风险等级枚举."""

    SAFE = "安全"  # VaR < 阈值 * 0.5
    NORMAL = "正常"  # VaR < 阈值 * 0.7
    WARNING = "预警"  # VaR < 阈值 * 0.9
    DANGER = "危险"  # VaR < 阈值
    CRITICAL = "临界"  # VaR >= 阈值


@dataclass
class GPDParameters:
    """广义帕累托分布参数.

    属性:
        xi: 形状参数 (尾部厚度)
        beta: 尺度参数
        threshold: 阈值
        exceedances: 超阈值样本数
    """

    xi: float
    beta: float
    threshold: float
    exceedances: int


@dataclass
class DynamicVaRResult:
    """动态VaR计算结果.

    属性:
        var: 风险价值
        confidence: 置信水平
        method: 计算方法
        expected_shortfall: 预期尾部损失
        risk_level: 风险等级
        timestamp: 计算时间戳
        metadata: 元数据
    """

    var: float
    confidence: float
    method: VaRMethod
    expected_shortfall: float = 0.0
    risk_level: RiskLevel = RiskLevel.NORMAL
    sample_size: int = 0
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后处理."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()  # noqa: DTZ005

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式."""
        return {
            "event_type": "VAR_CALCULATION",
            "var": round(self.var, 6),
            "confidence": self.confidence,
            "method": self.method.value,
            "expected_shortfall": round(self.expected_shortfall, 6),
            "risk_level": self.risk_level.value,
            "sample_size": self.sample_size,
            "timestamp": self.timestamp,
        }


@dataclass
class LiquidityMetrics:
    """流动性指标.

    属性:
        adv: 平均日成交量 (Average Daily Volume)
        bid_ask_spread: 买卖价差
        market_depth: 市场深度
        impact_coefficient: 冲击系数
    """

    adv: float = 0.0
    bid_ask_spread: float = 0.0
    market_depth: float = 0.0
    impact_coefficient: float = 0.1


class DynamicVaREngine:
    """动态VaR风险引擎 (军规 M6/M13/M16).

    功能:
    - EVT极值理论VaR
    - 半参数VaR
    - 涨跌停调整VaR
    - 流动性调整VaR
    - 动态风险等级

    示例:
        >>> engine = DynamicVaREngine()
        >>> result = engine.evt_var(returns, confidence=0.99)
    """

    # 默认参数
    DEFAULT_THRESHOLD_PCT: ClassVar[float] = 0.90  # GPD阈值百分位
    DEFAULT_VAR_LIMIT: ClassVar[float] = 0.10  # VaR告警阈值
    MIN_SAMPLES_EVT: ClassVar[int] = 30  # EVT最小样本数

    def __init__(
        self,
        default_confidence: float = 0.95,
        var_limit: float = 0.10,
        seed: int | None = None,
    ) -> None:
        """初始化动态VaR引擎.

        参数:
            default_confidence: 默认置信水平
            var_limit: VaR告警阈值
            seed: 随机种子
        """
        self._default_confidence = default_confidence
        self._var_limit = var_limit
        self._base_calculator = VaRCalculator(default_confidence, seed)

        # 回调函数
        self._on_risk_callbacks: list[Callable[[DynamicVaRResult], None]] = []

        # 统计
        self._calculation_count: int = 0
        self._warning_count: int = 0

    @property
    def calculation_count(self) -> int:
        """获取计算次数."""
        return self._calculation_count

    @property
    def warning_count(self) -> int:
        """获取告警次数."""
        return self._warning_count

    def evt_var(
        self,
        returns: list[float],
        confidence: float | None = None,
        threshold_pct: float = 0.90,
    ) -> DynamicVaRResult:
        """极值理论VaR (POT + GPD方法) (M6).

        使用超阈值模型(POT)和广义帕累托分布(GPD)计算极端风险。

        参数:
            returns: 收益率序列
            confidence: 置信水平
            threshold_pct: 阈值百分位 (0.90表示第90百分位)

        返回:
            动态VaR结果
        """
        self._calculation_count += 1
        confidence = confidence or self._default_confidence

        if len(returns) < self.MIN_SAMPLES_EVT:
            # 样本不足，回退到历史VaR
            base_result = self._base_calculator.historical_var(returns, confidence)
            return self._wrap_result(
                base_result, VaRMethod.HISTORICAL, {"fallback": "insufficient_samples"}
            )

        # 1. 确定阈值
        sorted_returns = sorted(returns)
        threshold_idx = int(len(sorted_returns) * (1 - threshold_pct))
        threshold_idx = max(1, min(threshold_idx, len(sorted_returns) - 1))
        threshold = sorted_returns[threshold_idx]

        # 2. 提取超阈值样本 (负收益超过阈值)
        exceedances = [threshold - r for r in returns if r < threshold]

        if len(exceedances) < 10:
            # 超阈值样本不足，回退
            base_result = self._base_calculator.historical_var(returns, confidence)
            return self._wrap_result(
                base_result,
                VaRMethod.HISTORICAL,
                {"fallback": "insufficient_exceedances"},
            )

        # 3. 估计GPD参数 (矩估计法)
        gpd_params = self._estimate_gpd_params(exceedances, threshold)

        # 4. 计算VaR
        n = len(returns)
        nu = len(exceedances)
        p = 1 - confidence

        if abs(gpd_params.xi) > 1e-10:
            # xi != 0
            var_value = -threshold + (gpd_params.beta / gpd_params.xi) * (
                pow((n / nu) * p, -gpd_params.xi) - 1
            )
        else:
            # xi ≈ 0 (指数分布)
            var_value = -threshold + gpd_params.beta * math.log((n / nu) * p)

        var_value = abs(var_value)

        # 5. 计算ES
        es = self._evt_expected_shortfall(var_value, gpd_params)

        # 6. 确定风险等级
        risk_level = self._calculate_risk_level(var_value)

        result = DynamicVaRResult(
            var=var_value,
            confidence=confidence,
            method=VaRMethod.EVT_GPD,
            expected_shortfall=es,
            risk_level=risk_level,
            sample_size=len(returns),
            metadata={
                "xi": round(gpd_params.xi, 6),
                "beta": round(gpd_params.beta, 6),
                "threshold": round(threshold, 6),
                "exceedances": nu,
            },
        )

        self._notify_risk(result)
        return result

    def semiparametric_var(
        self,
        returns: list[float],
        confidence: float | None = None,
        bandwidth: float | None = None,
    ) -> DynamicVaRResult:
        """半参数VaR (核密度 + GPD).

        中心部分使用核密度估计，尾部使用GPD。

        参数:
            returns: 收益率序列
            confidence: 置信水平
            bandwidth: 核密度带宽 (None=自动)

        返回:
            动态VaR结果
        """
        self._calculation_count += 1
        confidence = confidence or self._default_confidence

        if len(returns) < self.MIN_SAMPLES_EVT:
            base_result = self._base_calculator.historical_var(returns, confidence)
            return self._wrap_result(
                base_result, VaRMethod.HISTORICAL, {"fallback": "insufficient_samples"}
            )

        # 计算统计量
        n = len(returns)
        mean = sum(returns) / n
        variance = sum((r - mean) ** 2 for r in returns) / (n - 1) if n > 1 else 0
        std = math.sqrt(variance) if variance > 0 else 0.001

        # 自动带宽 (Silverman's rule)
        if bandwidth is None:
            bandwidth = 1.06 * std * pow(n, -0.2)

        # 核密度估计VaR (高斯核)
        target_p = 1 - confidence
        sorted_returns = sorted(returns)

        # 使用二分查找VaR
        var_value = self._kernel_density_quantile(
            sorted_returns, target_p, bandwidth, std
        )

        # 计算ES
        es_returns = [r for r in returns if r < -var_value]
        es = -sum(es_returns) / len(es_returns) if es_returns else var_value

        risk_level = self._calculate_risk_level(var_value)

        result = DynamicVaRResult(
            var=var_value,
            confidence=confidence,
            method=VaRMethod.SEMIPARAMETRIC,
            expected_shortfall=es,
            risk_level=risk_level,
            sample_size=n,
            metadata={"bandwidth": round(bandwidth, 6), "std": round(std, 6)},
        )

        self._notify_risk(result)
        return result

    def limit_adjusted_var(
        self,
        returns: list[float],
        limit_pct: float,
        confidence: float | None = None,
    ) -> DynamicVaRResult:
        """涨跌停调整VaR (M13).

        考虑涨跌停板截断效应对VaR的影响。

        参数:
            returns: 收益率序列
            limit_pct: 涨跌停幅度 (如0.10表示10%)
            confidence: 置信水平

        返回:
            动态VaR结果
        """
        self._calculation_count += 1
        confidence = confidence or self._default_confidence

        if len(returns) < 2:
            return DynamicVaRResult(
                var=0.0,
                confidence=confidence,
                method=VaRMethod.LIMIT_ADJUSTED,
                sample_size=len(returns),
            )

        # 截断收益率到涨跌停范围
        truncated_returns = [
            max(-limit_pct, min(limit_pct, r)) for r in returns
        ]

        # 计算截断后的VaR
        base_result = self._base_calculator.historical_var(truncated_returns, confidence)

        # 计算截断比例
        truncated_count = sum(
            1 for r in returns if abs(r) >= limit_pct
        )
        truncation_ratio = truncated_count / len(returns) if returns else 0

        # 如果截断比例高，VaR可能被低估，需要调整
        adjustment_factor = 1.0 + truncation_ratio * 0.5  # 简单线性调整
        adjusted_var = base_result.var * adjustment_factor

        # 如果收益超过涨跌停，VaR至少应等于涨跌停幅度
        if adjusted_var < limit_pct and truncation_ratio > 0.05:
            adjusted_var = limit_pct

        risk_level = self._calculate_risk_level(adjusted_var)

        result = DynamicVaRResult(
            var=adjusted_var,
            confidence=confidence,
            method=VaRMethod.LIMIT_ADJUSTED,
            expected_shortfall=base_result.expected_shortfall * adjustment_factor,
            risk_level=risk_level,
            sample_size=len(returns),
            metadata={
                "limit_pct": limit_pct,
                "truncation_ratio": round(truncation_ratio, 4),
                "adjustment_factor": round(adjustment_factor, 4),
                "raw_var": round(base_result.var, 6),
            },
        )

        self._notify_risk(result)
        return result

    def liquidity_adjusted_var(
        self,
        returns: list[float],
        position_value: float,
        liquidity: LiquidityMetrics,
        confidence: float | None = None,
        liquidation_days: int = 1,
    ) -> DynamicVaRResult:
        """流动性调整VaR (M16).

        考虑平仓成本和市场冲击对VaR的影响。

        参数:
            returns: 收益率序列
            position_value: 持仓价值
            liquidity: 流动性指标
            confidence: 置信水平
            liquidation_days: 预期平仓天数

        返回:
            动态VaR结果
        """
        self._calculation_count += 1
        confidence = confidence or self._default_confidence

        if len(returns) < 2:
            return DynamicVaRResult(
                var=0.0,
                confidence=confidence,
                method=VaRMethod.LIQUIDITY_ADJUSTED,
                sample_size=len(returns),
            )

        # 计算基础VaR
        base_result = self._base_calculator.historical_var(returns, confidence)

        # 计算流动性成本
        liquidity_cost = 0.0

        # 1. 买卖价差成本
        spread_cost = liquidity.bid_ask_spread * position_value

        # 2. 市场冲击成本 (简化的Almgren-Chriss模型)
        if liquidity.adv > 0:
            participation_rate = position_value / (liquidity.adv * liquidation_days)
            impact_cost = (
                liquidity.impact_coefficient
                * math.sqrt(participation_rate)
                * position_value
            )
        else:
            impact_cost = liquidity.impact_coefficient * position_value

        liquidity_cost = (spread_cost + impact_cost) / position_value if position_value > 0 else 0

        # 调整VaR
        # LVaR = VaR + 流动性成本
        adjusted_var = base_result.var + liquidity_cost

        # 多日平仓的时间调整
        if liquidation_days > 1:
            time_factor = math.sqrt(liquidation_days)
            adjusted_var *= time_factor

        risk_level = self._calculate_risk_level(adjusted_var)

        result = DynamicVaRResult(
            var=adjusted_var,
            confidence=confidence,
            method=VaRMethod.LIQUIDITY_ADJUSTED,
            expected_shortfall=base_result.expected_shortfall + liquidity_cost,
            risk_level=risk_level,
            sample_size=len(returns),
            metadata={
                "base_var": round(base_result.var, 6),
                "liquidity_cost": round(liquidity_cost, 6),
                "spread_cost_pct": round(spread_cost / position_value, 6) if position_value > 0 else 0,
                "impact_cost_pct": round(impact_cost / position_value, 6) if position_value > 0 else 0,
                "liquidation_days": liquidation_days,
            },
        )

        self._notify_risk(result)
        return result

    def calculate_var(
        self,
        returns: list[float],
        method: VaRMethod = VaRMethod.HISTORICAL,
        confidence: float | None = None,
        **kwargs: Any,
    ) -> DynamicVaRResult:
        """统一VaR计算接口.

        参数:
            returns: 收益率序列
            method: 计算方法
            confidence: 置信水平
            **kwargs: 方法特定参数

        返回:
            动态VaR结果
        """
        confidence = confidence or self._default_confidence

        if method == VaRMethod.HISTORICAL:
            result = self._base_calculator.historical_var(returns, confidence)
            return self._wrap_result(result, method)
        elif method == VaRMethod.PARAMETRIC:
            result = self._base_calculator.parametric_var(returns, confidence)
            return self._wrap_result(result, method)
        elif method == VaRMethod.MONTE_CARLO:
            result = self._base_calculator.monte_carlo_var(
                returns, confidence, kwargs.get("simulations", 10000)
            )
            return self._wrap_result(result, method)
        elif method == VaRMethod.EVT_GPD:
            return self.evt_var(returns, confidence, kwargs.get("threshold_pct", 0.90))
        elif method == VaRMethod.SEMIPARAMETRIC:
            return self.semiparametric_var(
                returns, confidence, kwargs.get("bandwidth")
            )
        elif method == VaRMethod.LIMIT_ADJUSTED:
            return self.limit_adjusted_var(
                returns, kwargs.get("limit_pct", 0.10), confidence
            )
        elif method == VaRMethod.LIQUIDITY_ADJUSTED:
            return self.liquidity_adjusted_var(
                returns,
                kwargs.get("position_value", 0),
                kwargs.get("liquidity", LiquidityMetrics()),
                confidence,
            )
        else:
            # 默认历史VaR
            result = self._base_calculator.historical_var(returns, confidence)
            return self._wrap_result(result, VaRMethod.HISTORICAL)

    def _estimate_gpd_params(
        self, exceedances: list[float], threshold: float
    ) -> GPDParameters:
        """估计GPD参数 (矩估计法).

        参数:
            exceedances: 超阈值样本
            threshold: 阈值

        返回:
            GPD参数
        """
        n = len(exceedances)
        if n < 2:
            return GPDParameters(xi=0, beta=1, threshold=threshold, exceedances=n)

        # 矩估计
        mean_exc = sum(exceedances) / n
        var_exc = sum((e - mean_exc) ** 2 for e in exceedances) / (n - 1) if n > 1 else 0

        if mean_exc <= 0:
            return GPDParameters(xi=0, beta=1, threshold=threshold, exceedances=n)

        # xi = 0.5 * (1 - mean^2 / var)
        # beta = 0.5 * mean * (1 + mean^2 / var)
        if var_exc > 0:
            ratio = mean_exc * mean_exc / var_exc
            xi = 0.5 * (1 - ratio)
            beta = 0.5 * mean_exc * (1 + ratio)
        else:
            xi = 0
            beta = mean_exc

        # 限制xi范围 (-0.5, 0.5) 保证稳定性
        xi = max(-0.5, min(0.5, xi))

        return GPDParameters(
            xi=xi, beta=max(0.001, beta), threshold=threshold, exceedances=n
        )

    def _evt_expected_shortfall(
        self, var: float, gpd: GPDParameters
    ) -> float:
        """计算EVT期望尾部损失.

        参数:
            var: VaR值
            gpd: GPD参数

        返回:
            ES值
        """
        if gpd.xi >= 1:
            return var * 2  # 无限期望，返回保守估计

        # ES = VaR / (1 - xi) + (beta - xi * threshold) / (1 - xi)
        es = var / (1 - gpd.xi) + (gpd.beta - gpd.xi * abs(gpd.threshold)) / (
            1 - gpd.xi
        )
        return max(var, es)

    def _kernel_density_quantile(
        self,
        sorted_returns: list[float],
        target_p: float,
        bandwidth: float,
        std: float,
    ) -> float:
        """核密度估计分位数.

        参数:
            sorted_returns: 排序后的收益率
            target_p: 目标概率
            bandwidth: 带宽
            std: 标准差

        返回:
            分位数（VaR）
        """
        n = len(sorted_returns)
        if n == 0:
            return 0.0

        # 搜索范围
        x_min = sorted_returns[0] - 3 * std
        x_max = sorted_returns[-1] + 3 * std

        # 二分查找
        for _ in range(50):  # 最多50次迭代
            x_mid = (x_min + x_max) / 2
            cdf = self._kernel_cdf(sorted_returns, x_mid, bandwidth)

            if abs(cdf - target_p) < 1e-6:
                break
            elif cdf < target_p:
                x_max = x_mid
            else:
                x_min = x_mid

        return -x_mid  # VaR是正值

    def _kernel_cdf(
        self, sorted_returns: list[float], x: float, bandwidth: float
    ) -> float:
        """核密度CDF.

        参数:
            sorted_returns: 排序后的收益率
            x: 目标点
            bandwidth: 带宽

        返回:
            CDF值
        """
        n = len(sorted_returns)
        if n == 0:
            return 0.5

        cdf_sum = 0.0
        for r in sorted_returns:
            z = (x - r) / bandwidth
            # 高斯核CDF
            cdf_sum += 0.5 * (1 + math.erf(z / math.sqrt(2)))

        return cdf_sum / n

    def _calculate_risk_level(self, var: float) -> RiskLevel:
        """计算风险等级.

        参数:
            var: VaR值

        返回:
            风险等级
        """
        if var >= self._var_limit:
            self._warning_count += 1
            return RiskLevel.CRITICAL
        elif var >= self._var_limit * 0.9:
            self._warning_count += 1
            return RiskLevel.DANGER
        elif var >= self._var_limit * 0.7:
            return RiskLevel.WARNING
        elif var >= self._var_limit * 0.5:
            return RiskLevel.NORMAL
        else:
            return RiskLevel.SAFE

    def _wrap_result(
        self,
        base_result: VaRResult,
        method: VaRMethod,
        extra_metadata: dict[str, Any] | None = None,
    ) -> DynamicVaRResult:
        """包装基础VaR结果.

        参数:
            base_result: 基础VaR结果
            method: 方法
            extra_metadata: 额外元数据

        返回:
            动态VaR结果
        """
        self._calculation_count += 1
        risk_level = self._calculate_risk_level(base_result.var)

        metadata = base_result.metadata or {}
        if extra_metadata:
            metadata.update(extra_metadata)

        result = DynamicVaRResult(
            var=base_result.var,
            confidence=base_result.confidence,
            method=method,
            expected_shortfall=base_result.expected_shortfall,
            risk_level=risk_level,
            sample_size=base_result.sample_size,
            metadata=metadata,
        )

        self._notify_risk(result)
        return result

    def register_callback(
        self, callback: Callable[[DynamicVaRResult], None]
    ) -> None:
        """注册风险回调."""
        self._on_risk_callbacks.append(callback)

    def _notify_risk(self, result: DynamicVaRResult) -> None:
        """通知风险结果."""
        for callback in self._on_risk_callbacks:
            try:
                callback(result)
            except Exception:  # noqa: BLE001
                pass  # 回调错误不影响主流程

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息."""
        return {
            "calculation_count": self._calculation_count,
            "warning_count": self._warning_count,
            "default_confidence": self._default_confidence,
            "var_limit": self._var_limit,
        }

    def reset(self) -> None:
        """重置统计."""
        self._calculation_count = 0
        self._warning_count = 0


# ============================================================
# 便捷函数
# ============================================================


def create_dynamic_var_engine(
    confidence: float = 0.95,
    var_limit: float = 0.10,
    seed: int | None = None,
) -> DynamicVaREngine:
    """创建动态VaR引擎.

    参数:
        confidence: 默认置信水平
        var_limit: VaR告警阈值
        seed: 随机种子

    返回:
        动态VaR引擎实例
    """
    return DynamicVaREngine(
        default_confidence=confidence,
        var_limit=var_limit,
        seed=seed,
    )


def quick_evt_var(
    returns: list[float],
    confidence: float = 0.99,
) -> float:
    """快速计算EVT VaR.

    参数:
        returns: 收益率序列
        confidence: 置信水平

    返回:
        VaR值
    """
    engine = DynamicVaREngine()
    result = engine.evt_var(returns, confidence)
    return result.var


def quick_limit_var(
    returns: list[float],
    limit_pct: float = 0.10,
    confidence: float = 0.95,
) -> float:
    """快速计算涨跌停调整VaR.

    参数:
        returns: 收益率序列
        limit_pct: 涨跌停幅度
        confidence: 置信水平

    返回:
        VaR值
    """
    engine = DynamicVaREngine()
    result = engine.limit_adjusted_var(returns, limit_pct, confidence)
    return result.var
