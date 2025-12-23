"""
多维收益归因模块 - SHAP归因分析器 (军规级 v4.0).

V4PRO Platform Component - Phase 10 多维收益归因
V4 SPEC: SS25 多维归因分析, SS26 SHAP可解释性
V4 Scenarios:
- RISK.ATTRIBUTION.SHAP: SHAP值归因分析
- RISK.ATTRIBUTION.TIME_SERIES: 时间序列归因
- RISK.ATTRIBUTION.STRATEGY: 策略收益分解

军规覆盖:
- M19: 风险归因 - 每笔亏损必须有归因分析

功能特性:
- SHAP值计算 (需要shap库)
- 多维因子归因 (市场/策略/时间)
- 时间序列分解 (日/周/月)
- 策略收益分解 (alpha/timing/selection)
- 审计日志记录

示例:
    >>> from src.risk.attribution.shap_attribution import (
    ...     SHAPAttributor,
    ...     AttributionResult,
    ...     MarketFactor,
    ...     StrategyFactor,
    ... )
    >>> attributor = SHAPAttributor()
    >>> result = attributor.attribute_returns(
    ...     returns=returns,
    ...     factor_data=factors,
    ...     model=model,
    ... )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np


if TYPE_CHECKING:
    import torch


# ============================================================
# 枚举定义
# ============================================================


class MarketFactor(Enum):
    """市场因子类型枚举."""

    BETA = "BETA"  # 市场Beta敞口
    MOMENTUM = "MOMENTUM"  # 动量因子
    VOLATILITY = "VOLATILITY"  # 波动率因子
    SIZE = "SIZE"  # 市值因子
    VALUE = "VALUE"  # 价值因子
    LIQUIDITY = "LIQUIDITY"  # 流动性因子


class StrategyFactor(Enum):
    """策略因子类型枚举."""

    ALPHA = "ALPHA"  # 超额收益 (选股能力)
    TIMING = "TIMING"  # 择时能力
    SELECTION = "SELECTION"  # 品种选择
    ALLOCATION = "ALLOCATION"  # 资产配置
    EXECUTION = "EXECUTION"  # 执行效率
    COST = "COST"  # 交易成本


class TimeDimension(Enum):
    """时间维度枚举."""

    DAILY = "DAILY"  # 日度归因
    WEEKLY = "WEEKLY"  # 周度归因
    MONTHLY = "MONTHLY"  # 月度归因
    QUARTERLY = "QUARTERLY"  # 季度归因
    YEARLY = "YEARLY"  # 年度归因


class AttributionMethod(Enum):
    """归因方法枚举."""

    SHAP = "SHAP"  # SHAP值归因 (需要shap库)
    BRINSON = "BRINSON"  # Brinson归因法
    FACTOR = "FACTOR"  # 因子归因法
    REGRESSION = "REGRESSION"  # 回归归因法
    SIMPLE = "SIMPLE"  # 简单分解法


# ============================================================
# 数据类定义
# ============================================================


@dataclass(frozen=True)
class FactorContribution:
    """单因子贡献 (不可变).

    属性:
        factor_name: 因子名称
        factor_type: 因子类型 (市场/策略)
        contribution: 收益贡献度 (百分比)
        shap_value: SHAP值 (原始值)
        importance: 重要性权重 (0-1)
        direction: 方向 (正/负贡献)
        description: 描述信息
    """

    factor_name: str
    factor_type: str
    contribution: float
    shap_value: float = 0.0
    importance: float = 0.0
    direction: str = "positive"
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "factor_name": self.factor_name,
            "factor_type": self.factor_type,
            "contribution": round(self.contribution, 6),
            "shap_value": round(self.shap_value, 6),
            "importance": round(self.importance, 4),
            "direction": self.direction,
            "description": self.description,
        }


@dataclass(frozen=True)
class TimeAttribution:
    """时间维度归因 (不可变).

    属性:
        period: 时间段标识
        dimension: 时间维度 (日/周/月)
        total_return: 该时段总收益
        factor_contributions: 各因子贡献
        residual: 残差 (未解释部分)
    """

    period: str
    dimension: TimeDimension
    total_return: float
    factor_contributions: tuple[FactorContribution, ...]
    residual: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "period": self.period,
            "dimension": self.dimension.value,
            "total_return": round(self.total_return, 6),
            "factor_contributions": [fc.to_dict() for fc in self.factor_contributions],
            "residual": round(self.residual, 6),
        }


@dataclass(frozen=True)
class StrategyBreakdown:
    """策略收益分解 (不可变).

    属性:
        strategy_id: 策略ID
        total_return: 总收益
        alpha_contribution: Alpha贡献
        timing_contribution: 择时贡献
        selection_contribution: 选品贡献
        allocation_contribution: 配置贡献
        execution_contribution: 执行贡献
        cost_contribution: 成本贡献 (负值)
    """

    strategy_id: str
    total_return: float
    alpha_contribution: float = 0.0
    timing_contribution: float = 0.0
    selection_contribution: float = 0.0
    allocation_contribution: float = 0.0
    execution_contribution: float = 0.0
    cost_contribution: float = 0.0

    @property
    def gross_return(self) -> float:
        """毛收益 (不含成本)."""
        return self.total_return - self.cost_contribution

    @property
    def skill_return(self) -> float:
        """技能收益 (Alpha + Timing + Selection)."""
        return self.alpha_contribution + self.timing_contribution + self.selection_contribution

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "strategy_id": self.strategy_id,
            "total_return": round(self.total_return, 6),
            "alpha_contribution": round(self.alpha_contribution, 6),
            "timing_contribution": round(self.timing_contribution, 6),
            "selection_contribution": round(self.selection_contribution, 6),
            "allocation_contribution": round(self.allocation_contribution, 6),
            "execution_contribution": round(self.execution_contribution, 6),
            "cost_contribution": round(self.cost_contribution, 6),
            "gross_return": round(self.gross_return, 6),
            "skill_return": round(self.skill_return, 6),
        }


@dataclass
class AttributionResult:
    """多维归因结果.

    属性:
        attribution_id: 归因ID
        timestamp: 时间戳
        method: 归因方法
        total_return: 总收益
        factor_contributions: 因子贡献列表
        time_attributions: 时间维度归因列表
        strategy_breakdown: 策略分解列表
        market_contribution: 市场贡献合计
        strategy_contribution: 策略贡献合计
        residual: 残差 (未解释部分)
        r_squared: 解释度 (0-1)
        shap_values: 原始SHAP值数组
        confidence: 置信度
        metadata: 元数据
    """

    attribution_id: str
    timestamp: str
    method: AttributionMethod
    total_return: float
    factor_contributions: list[FactorContribution] = field(default_factory=list)
    time_attributions: list[TimeAttribution] = field(default_factory=list)
    strategy_breakdown: list[StrategyBreakdown] = field(default_factory=list)
    market_contribution: float = 0.0
    strategy_contribution: float = 0.0
    residual: float = 0.0
    r_squared: float = 0.0
    shap_values: np.ndarray | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def explained_return(self) -> float:
        """已解释收益."""
        return self.total_return - self.residual

    @property
    def explanation_ratio(self) -> float:
        """解释比例."""
        if abs(self.total_return) < 1e-10:
            return 0.0
        return self.explained_return / self.total_return

    def get_top_factors(self, n: int = 5) -> list[FactorContribution]:
        """获取前N个重要因子.

        参数:
            n: 返回因子数量

        返回:
            按重要性排序的因子列表
        """
        sorted_factors = sorted(
            self.factor_contributions,
            key=lambda f: abs(f.contribution),
            reverse=True,
        )
        return sorted_factors[:n]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "attribution_id": self.attribution_id,
            "timestamp": self.timestamp,
            "method": self.method.value,
            "total_return": round(self.total_return, 6),
            "factor_contributions": [fc.to_dict() for fc in self.factor_contributions],
            "time_attributions": [ta.to_dict() for ta in self.time_attributions],
            "strategy_breakdown": [sb.to_dict() for sb in self.strategy_breakdown],
            "market_contribution": round(self.market_contribution, 6),
            "strategy_contribution": round(self.strategy_contribution, 6),
            "residual": round(self.residual, 6),
            "r_squared": round(self.r_squared, 4),
            "explained_return": round(self.explained_return, 6),
            "explanation_ratio": round(self.explanation_ratio, 4),
            "confidence": round(self.confidence, 4),
            "metadata": self.metadata,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式 (军规 M19).

        返回:
            符合审计要求的字典
        """
        return {
            "attribution_id": self.attribution_id,
            "timestamp": self.timestamp,
            "method": self.method.value,
            "total_return": round(self.total_return, 6),
            "market_contribution": round(self.market_contribution, 6),
            "strategy_contribution": round(self.strategy_contribution, 6),
            "residual": round(self.residual, 6),
            "r_squared": round(self.r_squared, 4),
            "confidence": round(self.confidence, 4),
            "top_factors": [
                {
                    "name": f.factor_name,
                    "contribution": round(f.contribution, 6),
                }
                for f in self.get_top_factors(3)
            ],
        }


# ============================================================
# SHAP归因分析器
# ============================================================


class SHAPAttributor:
    """SHAP多维归因分析器 (军规 M19).

    提供基于SHAP的多维收益归因分析功能。

    功能:
    - 因子贡献度计算 (市场因子 + 策略因子)
    - 时间序列归因 (日/周/月)
    - 策略收益分解 (Alpha/Timing/Selection)
    - SHAP值可解释性分析

    军规覆盖:
    - M19: 风险归因 - 完整归因分析链

    示例:
        >>> attributor = SHAPAttributor(use_shap=True)
        >>> result = attributor.attribute_returns(
        ...     returns=portfolio_returns,
        ...     factor_data=factor_matrix,
        ...     strategy_returns={"strategy1": s1_returns},
        ... )
        >>> print(result.get_top_factors(3))
    """

    # 默认市场因子权重
    DEFAULT_MARKET_WEIGHTS: ClassVar[dict[MarketFactor, float]] = {
        MarketFactor.BETA: 0.30,
        MarketFactor.MOMENTUM: 0.20,
        MarketFactor.VOLATILITY: 0.20,
        MarketFactor.SIZE: 0.10,
        MarketFactor.VALUE: 0.10,
        MarketFactor.LIQUIDITY: 0.10,
    }

    # 默认策略因子权重
    DEFAULT_STRATEGY_WEIGHTS: ClassVar[dict[StrategyFactor, float]] = {
        StrategyFactor.ALPHA: 0.35,
        StrategyFactor.TIMING: 0.25,
        StrategyFactor.SELECTION: 0.20,
        StrategyFactor.ALLOCATION: 0.10,
        StrategyFactor.EXECUTION: 0.05,
        StrategyFactor.COST: 0.05,
    }

    def __init__(
        self,
        use_shap: bool = True,
        shap_samples: int = 100,
        default_method: AttributionMethod = AttributionMethod.SHAP,
    ) -> None:
        """初始化SHAP归因分析器.

        参数:
            use_shap: 是否使用SHAP库 (需要安装shap)
            shap_samples: SHAP采样数量
            default_method: 默认归因方法
        """
        self._use_shap = use_shap
        self._shap_samples = shap_samples
        self._default_method = default_method
        self._shap_available = self._check_shap_available()

        # 统计
        self._attribution_count: int = 0
        self._shap_calculation_count: int = 0

    def _check_shap_available(self) -> bool:
        """检查SHAP库是否可用."""
        try:
            import shap  # noqa: F401

            return True
        except ImportError:
            return False

    @property
    def use_shap(self) -> bool:
        """是否使用SHAP."""
        return self._use_shap and self._shap_available

    @property
    def attribution_count(self) -> int:
        """归因计算次数."""
        return self._attribution_count

    @property
    def shap_calculation_count(self) -> int:
        """SHAP计算次数."""
        return self._shap_calculation_count

    def attribute_returns(
        self,
        returns: np.ndarray,
        factor_data: np.ndarray | None = None,
        benchmark_returns: np.ndarray | None = None,
        strategy_returns: dict[str, np.ndarray] | None = None,
        model: torch.nn.Module | None = None,
        method: AttributionMethod | None = None,
        time_dimension: TimeDimension = TimeDimension.DAILY,
    ) -> AttributionResult:
        """执行多维收益归因分析.

        参数:
            returns: 组合收益率序列
            factor_data: 因子数据矩阵 (T x K)
            benchmark_returns: 基准收益率序列
            strategy_returns: 各策略收益率字典
            model: 预测模型 (用于SHAP)
            method: 归因方法
            time_dimension: 时间维度

        返回:
            AttributionResult 多维归因结果
        """
        self._attribution_count += 1
        method = method or self._default_method
        attribution_id = self._generate_attribution_id()
        timestamp = datetime.now().isoformat()  # noqa: DTZ005

        # 计算总收益
        total_return = float(np.sum(returns)) if len(returns) > 0 else 0.0

        # 因子贡献度计算
        factor_contributions = self._calculate_factor_contributions(
            returns=returns,
            factor_data=factor_data,
            benchmark_returns=benchmark_returns,
            model=model,
            method=method,
        )

        # 时间序列归因
        time_attributions = self._calculate_time_attributions(
            returns=returns,
            factor_contributions=factor_contributions,
            dimension=time_dimension,
        )

        # 策略收益分解
        strategy_breakdown = self._calculate_strategy_breakdown(
            returns=returns,
            strategy_returns=strategy_returns,
            benchmark_returns=benchmark_returns,
        )

        # 计算市场/策略贡献汇总
        market_contribution = sum(
            fc.contribution
            for fc in factor_contributions
            if fc.factor_type == "market"
        )
        strategy_contribution = sum(
            fc.contribution
            for fc in factor_contributions
            if fc.factor_type == "strategy"
        )

        # 计算残差
        explained = market_contribution + strategy_contribution
        residual = total_return - explained

        # 计算解释度 (R-squared)
        r_squared = self._calculate_r_squared(
            returns=returns,
            factor_data=factor_data,
        )

        # 置信度
        confidence = self._calculate_confidence(
            method=method,
            r_squared=r_squared,
            sample_size=len(returns),
        )

        return AttributionResult(
            attribution_id=attribution_id,
            timestamp=timestamp,
            method=method,
            total_return=total_return,
            factor_contributions=factor_contributions,
            time_attributions=time_attributions,
            strategy_breakdown=strategy_breakdown,
            market_contribution=market_contribution,
            strategy_contribution=strategy_contribution,
            residual=residual,
            r_squared=r_squared,
            confidence=confidence,
            metadata={
                "sample_size": len(returns),
                "factor_count": len(factor_contributions),
                "time_periods": len(time_attributions),
                "strategy_count": len(strategy_breakdown),
            },
        )

    def _calculate_factor_contributions(
        self,
        returns: np.ndarray,
        factor_data: np.ndarray | None,
        benchmark_returns: np.ndarray | None,
        model: torch.nn.Module | None,
        method: AttributionMethod,
    ) -> list[FactorContribution]:
        """计算因子贡献度.

        参数:
            returns: 收益率序列
            factor_data: 因子数据
            benchmark_returns: 基准收益
            model: 预测模型
            method: 归因方法

        返回:
            因子贡献列表
        """
        contributions: list[FactorContribution] = []

        if method == AttributionMethod.SHAP and self.use_shap and model is not None:
            contributions = self._shap_factor_attribution(
                returns=returns,
                factor_data=factor_data,
                model=model,
            )
        elif method == AttributionMethod.REGRESSION and factor_data is not None:
            contributions = self._regression_factor_attribution(
                returns=returns,
                factor_data=factor_data,
            )
        else:
            contributions = self._simple_factor_attribution(
                returns=returns,
                benchmark_returns=benchmark_returns,
            )

        return contributions

    def _shap_factor_attribution(
        self,
        returns: np.ndarray,
        factor_data: np.ndarray | None,
        model: torch.nn.Module,
    ) -> list[FactorContribution]:
        """基于SHAP的因子归因.

        参数:
            returns: 收益率序列
            factor_data: 因子数据
            model: 预测模型

        返回:
            因子贡献列表
        """
        contributions: list[FactorContribution] = []

        if factor_data is None or len(factor_data) == 0:
            return self._simple_factor_attribution(returns, None)

        try:
            import shap
            import torch

            self._shap_calculation_count += 1

            # 创建模型包装器
            def model_wrapper(x: np.ndarray) -> np.ndarray:
                with torch.no_grad():
                    tensor = torch.from_numpy(x).float()
                    output = model(tensor)
                    result: np.ndarray = output.numpy()
                    return result

            # 准备数据
            background = factor_data[:min(50, len(factor_data))]
            test_data = factor_data

            # 创建SHAP解释器
            explainer = shap.KernelExplainer(model_wrapper, background)
            shap_values = explainer.shap_values(test_data, nsamples=self._shap_samples)

            if isinstance(shap_values, list):
                shap_values = shap_values[0]

            # 聚合SHAP值
            mean_shap = np.mean(np.abs(shap_values), axis=0)
            total_shap = np.sum(mean_shap)

            # 因子名称映射
            factor_names = self._get_factor_names(factor_data.shape[1])

            for i, (name, shap_val) in enumerate(zip(factor_names, mean_shap, strict=False)):
                importance = shap_val / total_shap if total_shap > 0 else 0.0
                direction_val = np.mean(shap_values[:, i])
                direction = "positive" if direction_val >= 0 else "negative"

                # 估算贡献度
                contribution = float(np.sum(returns)) * importance * np.sign(direction_val)

                factor_type = "market" if i < 3 else "strategy"

                contributions.append(
                    FactorContribution(
                        factor_name=name,
                        factor_type=factor_type,
                        contribution=contribution,
                        shap_value=float(shap_val),
                        importance=importance,
                        direction=direction,
                        description=self._get_factor_description(name, contribution),
                    )
                )

        except ImportError:
            return self._simple_factor_attribution(returns, None)
        except Exception:
            return self._simple_factor_attribution(returns, None)

        return contributions

    def _regression_factor_attribution(
        self,
        returns: np.ndarray,
        factor_data: np.ndarray,
    ) -> list[FactorContribution]:
        """基于回归的因子归因.

        参数:
            returns: 收益率序列
            factor_data: 因子数据

        返回:
            因子贡献列表
        """
        contributions: list[FactorContribution] = []

        if len(returns) < 10 or factor_data.shape[0] != len(returns):
            return self._simple_factor_attribution(returns, None)

        try:
            # 简单OLS回归
            X = factor_data
            y = returns

            # 添加截距项
            X_with_intercept = np.column_stack([np.ones(len(X)), X])

            # 最小二乘解
            coeffs, residuals, _, _ = np.linalg.lstsq(X_with_intercept, y, rcond=None)

            # 提取系数 (第一个是截距)
            intercept = coeffs[0]
            betas = coeffs[1:]

            # 计算因子贡献
            factor_means = np.mean(factor_data, axis=0)
            factor_contributions_raw = betas * factor_means

            total_contribution = np.sum(np.abs(factor_contributions_raw))
            factor_names = self._get_factor_names(factor_data.shape[1])

            for i, (name, beta, contrib) in enumerate(
                zip(factor_names, betas, factor_contributions_raw, strict=False)
            ):
                importance = abs(contrib) / total_contribution if total_contribution > 0 else 0.0
                direction = "positive" if contrib >= 0 else "negative"
                factor_type = "market" if i < 3 else "strategy"

                contributions.append(
                    FactorContribution(
                        factor_name=name,
                        factor_type=factor_type,
                        contribution=float(contrib),
                        shap_value=float(beta),
                        importance=importance,
                        direction=direction,
                        description=self._get_factor_description(name, contrib),
                    )
                )

            # 添加Alpha (截距)
            contributions.append(
                FactorContribution(
                    factor_name="alpha",
                    factor_type="strategy",
                    contribution=float(intercept),
                    shap_value=0.0,
                    importance=0.0,
                    direction="positive" if intercept >= 0 else "negative",
                    description=f"Alpha贡献: {intercept:.4f}",
                )
            )

        except Exception:
            return self._simple_factor_attribution(returns, None)

        return contributions

    def _simple_factor_attribution(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray | None,
    ) -> list[FactorContribution]:
        """简单因子归因.

        参数:
            returns: 收益率序列
            benchmark_returns: 基准收益

        返回:
            因子贡献列表
        """
        contributions: list[FactorContribution] = []
        total_return = float(np.sum(returns)) if len(returns) > 0 else 0.0

        # 市场因子贡献 (基于基准)
        if benchmark_returns is not None and len(benchmark_returns) > 0:
            market_return = float(np.sum(benchmark_returns))
            beta = self._estimate_beta(returns, benchmark_returns)
            market_contribution = market_return * beta

            contributions.append(
                FactorContribution(
                    factor_name="beta",
                    factor_type="market",
                    contribution=market_contribution,
                    shap_value=beta,
                    importance=abs(market_contribution / total_return) if total_return != 0 else 0.0,
                    direction="positive" if market_contribution >= 0 else "negative",
                    description=f"市场Beta敞口贡献: {market_contribution:.4f}",
                )
            )

            # Alpha贡献
            alpha_contribution = total_return - market_contribution
            contributions.append(
                FactorContribution(
                    factor_name="alpha",
                    factor_type="strategy",
                    contribution=alpha_contribution,
                    shap_value=0.0,
                    importance=abs(alpha_contribution / total_return) if total_return != 0 else 0.0,
                    direction="positive" if alpha_contribution >= 0 else "negative",
                    description=f"超额收益Alpha贡献: {alpha_contribution:.4f}",
                )
            )
        else:
            # 没有基准时，使用简单分解
            momentum_contrib = self._estimate_momentum_contribution(returns)
            volatility_contrib = self._estimate_volatility_contribution(returns)
            residual_contrib = total_return - momentum_contrib - volatility_contrib

            contributions.extend([
                FactorContribution(
                    factor_name="momentum",
                    factor_type="market",
                    contribution=momentum_contrib,
                    shap_value=0.0,
                    importance=abs(momentum_contrib / total_return) if total_return != 0 else 0.0,
                    direction="positive" if momentum_contrib >= 0 else "negative",
                    description=f"动量因子贡献: {momentum_contrib:.4f}",
                ),
                FactorContribution(
                    factor_name="volatility",
                    factor_type="market",
                    contribution=volatility_contrib,
                    shap_value=0.0,
                    importance=abs(volatility_contrib / total_return) if total_return != 0 else 0.0,
                    direction="positive" if volatility_contrib >= 0 else "negative",
                    description=f"波动率因子贡献: {volatility_contrib:.4f}",
                ),
                FactorContribution(
                    factor_name="alpha",
                    factor_type="strategy",
                    contribution=residual_contrib,
                    shap_value=0.0,
                    importance=abs(residual_contrib / total_return) if total_return != 0 else 0.0,
                    direction="positive" if residual_contrib >= 0 else "negative",
                    description=f"Alpha贡献: {residual_contrib:.4f}",
                ),
            ])

        return contributions

    def _calculate_time_attributions(
        self,
        returns: np.ndarray,
        factor_contributions: list[FactorContribution],
        dimension: TimeDimension,
    ) -> list[TimeAttribution]:
        """计算时间序列归因.

        参数:
            returns: 收益率序列
            factor_contributions: 因子贡献
            dimension: 时间维度

        返回:
            时间归因列表
        """
        time_attributions: list[TimeAttribution] = []

        if len(returns) == 0:
            return time_attributions

        # 根据时间维度分组
        period_size = self._get_period_size(dimension, len(returns))
        num_periods = (len(returns) + period_size - 1) // period_size

        for i in range(num_periods):
            start_idx = i * period_size
            end_idx = min((i + 1) * period_size, len(returns))
            period_returns = returns[start_idx:end_idx]
            period_total = float(np.sum(period_returns))

            # 按比例分配因子贡献到该时段
            period_factor_contributions: list[FactorContribution] = []
            period_ratio = len(period_returns) / len(returns)

            for fc in factor_contributions:
                period_contrib = fc.contribution * period_ratio
                period_factor_contributions.append(
                    FactorContribution(
                        factor_name=fc.factor_name,
                        factor_type=fc.factor_type,
                        contribution=period_contrib,
                        shap_value=fc.shap_value * period_ratio,
                        importance=fc.importance,
                        direction=fc.direction,
                        description=fc.description,
                    )
                )

            # 计算残差
            explained = sum(pfc.contribution for pfc in period_factor_contributions)
            residual = period_total - explained

            time_attributions.append(
                TimeAttribution(
                    period=f"{dimension.value}_{i + 1}",
                    dimension=dimension,
                    total_return=period_total,
                    factor_contributions=tuple(period_factor_contributions),
                    residual=residual,
                )
            )

        return time_attributions

    def _calculate_strategy_breakdown(
        self,
        returns: np.ndarray,
        strategy_returns: dict[str, np.ndarray] | None,
        benchmark_returns: np.ndarray | None,
    ) -> list[StrategyBreakdown]:
        """计算策略收益分解.

        参数:
            returns: 组合收益率
            strategy_returns: 各策略收益率
            benchmark_returns: 基准收益率

        返回:
            策略分解列表
        """
        breakdown_list: list[StrategyBreakdown] = []

        if strategy_returns is None or len(strategy_returns) == 0:
            # 没有策略收益时，将整体组合作为单一策略
            total_return = float(np.sum(returns)) if len(returns) > 0 else 0.0

            if benchmark_returns is not None and len(benchmark_returns) > 0:
                benchmark_total = float(np.sum(benchmark_returns))
                alpha = total_return - benchmark_total
            else:
                alpha = total_return * 0.3  # 简单估算
                benchmark_total = total_return - alpha

            breakdown_list.append(
                StrategyBreakdown(
                    strategy_id="portfolio",
                    total_return=total_return,
                    alpha_contribution=alpha,
                    timing_contribution=total_return * 0.2,
                    selection_contribution=total_return * 0.2,
                    allocation_contribution=total_return * 0.2,
                    execution_contribution=total_return * 0.05,
                    cost_contribution=total_return * -0.05,
                )
            )
        else:
            for strategy_id, s_returns in strategy_returns.items():
                s_total = float(np.sum(s_returns)) if len(s_returns) > 0 else 0.0

                # 分解各组成部分
                if benchmark_returns is not None and len(benchmark_returns) == len(s_returns):
                    beta = self._estimate_beta(s_returns, benchmark_returns)
                    benchmark_contrib = float(np.sum(benchmark_returns)) * beta
                    alpha = s_total - benchmark_contrib
                else:
                    alpha = s_total * 0.3

                # 简化的分解 (可以使用更复杂的方法)
                timing = s_total * 0.2
                selection = s_total * 0.2
                allocation = s_total * 0.15
                execution = s_total * 0.05
                cost = s_total * -0.05

                breakdown_list.append(
                    StrategyBreakdown(
                        strategy_id=strategy_id,
                        total_return=s_total,
                        alpha_contribution=alpha,
                        timing_contribution=timing,
                        selection_contribution=selection,
                        allocation_contribution=allocation,
                        execution_contribution=execution,
                        cost_contribution=cost,
                    )
                )

        return breakdown_list

    def _estimate_beta(
        self,
        returns: np.ndarray,
        benchmark_returns: np.ndarray,
    ) -> float:
        """估算Beta值.

        参数:
            returns: 资产收益率
            benchmark_returns: 基准收益率

        返回:
            Beta值
        """
        if len(returns) < 2 or len(benchmark_returns) < 2:
            return 1.0

        min_len = min(len(returns), len(benchmark_returns))
        r = returns[:min_len]
        b = benchmark_returns[:min_len]

        cov = np.cov(r, b)[0, 1]
        var_b = np.var(b)

        if var_b < 1e-10:
            return 1.0

        return float(cov / var_b)

    def _estimate_momentum_contribution(self, returns: np.ndarray) -> float:
        """估算动量因子贡献.

        参数:
            returns: 收益率序列

        返回:
            动量贡献
        """
        if len(returns) < 5:
            return 0.0

        # 简单动量: 过去收益的延续性
        past_returns = returns[:-1]
        current_returns = returns[1:]

        if len(past_returns) == 0:
            return 0.0

        # 动量贡献 = 收益自相关性 * 总收益
        autocorr = np.corrcoef(past_returns, current_returns)[0, 1]
        if np.isnan(autocorr):
            autocorr = 0.0

        return float(np.sum(returns) * abs(autocorr) * 0.3)

    def _estimate_volatility_contribution(self, returns: np.ndarray) -> float:
        """估算波动率因子贡献.

        参数:
            returns: 收益率序列

        返回:
            波动率贡献
        """
        if len(returns) < 2:
            return 0.0

        volatility = float(np.std(returns))
        mean_return = float(np.mean(returns))

        # 波动率贡献 (高波动通常带来负贡献)
        if mean_return < 0:
            return -volatility * 0.1 * len(returns)
        return volatility * 0.05 * len(returns)

    def _calculate_r_squared(
        self,
        returns: np.ndarray,
        factor_data: np.ndarray | None,
    ) -> float:
        """计算解释度 (R-squared).

        参数:
            returns: 收益率序列
            factor_data: 因子数据

        返回:
            R-squared值
        """
        if factor_data is None or len(returns) < 10:
            return 0.5  # 默认值

        if factor_data.shape[0] != len(returns):
            return 0.5

        try:
            # 简单OLS回归
            X = factor_data
            y = returns

            X_with_intercept = np.column_stack([np.ones(len(X)), X])
            coeffs, residuals, _, _ = np.linalg.lstsq(X_with_intercept, y, rcond=None)

            # 计算预测值
            y_pred = X_with_intercept @ coeffs

            # 计算R-squared
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)

            if ss_tot < 1e-10:
                return 0.0

            r_squared = 1 - ss_res / ss_tot
            return max(0.0, min(1.0, float(r_squared)))

        except Exception:
            return 0.5

    def _calculate_confidence(
        self,
        method: AttributionMethod,
        r_squared: float,
        sample_size: int,
    ) -> float:
        """计算置信度.

        参数:
            method: 归因方法
            r_squared: 解释度
            sample_size: 样本量

        返回:
            置信度 (0-1)
        """
        # 基础置信度 (基于方法)
        method_confidence = {
            AttributionMethod.SHAP: 0.95,
            AttributionMethod.BRINSON: 0.90,
            AttributionMethod.REGRESSION: 0.85,
            AttributionMethod.FACTOR: 0.80,
            AttributionMethod.SIMPLE: 0.70,
        }
        base_confidence = method_confidence.get(method, 0.70)

        # 样本量调整
        sample_factor = min(1.0, sample_size / 100)

        # R-squared调整
        r2_factor = 0.5 + 0.5 * r_squared

        return base_confidence * sample_factor * r2_factor

    def _get_period_size(self, dimension: TimeDimension, total_length: int) -> int:
        """获取时间周期大小.

        参数:
            dimension: 时间维度
            total_length: 总长度

        返回:
            周期大小
        """
        period_sizes = {
            TimeDimension.DAILY: 1,
            TimeDimension.WEEKLY: 5,
            TimeDimension.MONTHLY: 22,
            TimeDimension.QUARTERLY: 66,
            TimeDimension.YEARLY: 252,
        }
        size = period_sizes.get(dimension, 1)
        return min(size, total_length)

    def _get_factor_names(self, num_factors: int) -> list[str]:
        """获取因子名称列表.

        参数:
            num_factors: 因子数量

        返回:
            因子名称列表
        """
        default_names = [
            "beta", "momentum", "volatility",
            "size", "value", "liquidity",
            "alpha", "timing", "selection",
        ]
        if num_factors <= len(default_names):
            return default_names[:num_factors]
        return default_names + [f"factor_{i}" for i in range(len(default_names), num_factors)]

    def _get_factor_description(self, factor_name: str, contribution: float) -> str:
        """生成因子描述.

        参数:
            factor_name: 因子名称
            contribution: 贡献度

        返回:
            描述字符串
        """
        direction = "正向" if contribution >= 0 else "负向"
        strength = (
            "强"
            if abs(contribution) > 0.1
            else "中"
            if abs(contribution) > 0.01
            else "弱"
        )

        descriptions = {
            "beta": f"市场Beta敞口{direction}贡献({strength})",
            "momentum": f"动量因子{direction}贡献({strength})",
            "volatility": f"波动率因子{direction}贡献({strength})",
            "size": f"市值因子{direction}贡献({strength})",
            "value": f"价值因子{direction}贡献({strength})",
            "liquidity": f"流动性因子{direction}贡献({strength})",
            "alpha": f"超额收益Alpha{direction}贡献({strength})",
            "timing": f"择时能力{direction}贡献({strength})",
            "selection": f"品种选择{direction}贡献({strength})",
        }

        return descriptions.get(factor_name, f"{factor_name}因子{direction}贡献")

    def _generate_attribution_id(self) -> str:
        """生成归因ID.

        返回:
            唯一归因ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")  # noqa: DTZ005
        return f"ATTR_{timestamp}_{self._attribution_count}"

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        return {
            "attribution_count": self._attribution_count,
            "shap_calculation_count": self._shap_calculation_count,
            "shap_available": self._shap_available,
            "use_shap": self._use_shap,
            "default_method": self._default_method.value,
            "shap_samples": self._shap_samples,
        }

    def reset_statistics(self) -> None:
        """重置统计信息."""
        self._attribution_count = 0
        self._shap_calculation_count = 0


# ============================================================
# 便捷函数
# ============================================================


def create_shap_attributor(
    use_shap: bool = True,
    shap_samples: int = 100,
    default_method: AttributionMethod = AttributionMethod.SHAP,
) -> SHAPAttributor:
    """创建SHAP归因分析器.

    参数:
        use_shap: 是否使用SHAP
        shap_samples: SHAP采样数量
        default_method: 默认归因方法

    返回:
        SHAPAttributor实例
    """
    return SHAPAttributor(
        use_shap=use_shap,
        shap_samples=shap_samples,
        default_method=default_method,
    )


def attribute_portfolio_returns(
    returns: np.ndarray,
    factor_data: np.ndarray | None = None,
    benchmark_returns: np.ndarray | None = None,
    time_dimension: TimeDimension = TimeDimension.DAILY,
) -> AttributionResult:
    """归因组合收益 (便捷函数).

    参数:
        returns: 组合收益率
        factor_data: 因子数据
        benchmark_returns: 基准收益率
        time_dimension: 时间维度

    返回:
        归因结果
    """
    attributor = SHAPAttributor(use_shap=False)
    return attributor.attribute_returns(
        returns=returns,
        factor_data=factor_data,
        benchmark_returns=benchmark_returns,
        time_dimension=time_dimension,
    )


def get_factor_summary(result: AttributionResult) -> dict[str, float]:
    """获取因子摘要.

    参数:
        result: 归因结果

    返回:
        因子贡献摘要
    """
    return {fc.factor_name: fc.contribution for fc in result.factor_contributions}


def get_time_summary(result: AttributionResult) -> dict[str, float]:
    """获取时间归因摘要.

    参数:
        result: 归因结果

    返回:
        时间归因摘要
    """
    return {ta.period: ta.total_return for ta in result.time_attributions}


def get_strategy_summary(result: AttributionResult) -> dict[str, dict[str, float]]:
    """获取策略分解摘要.

    参数:
        result: 归因结果

    返回:
        策略分解摘要
    """
    return {
        sb.strategy_id: {
            "total": sb.total_return,
            "alpha": sb.alpha_contribution,
            "timing": sb.timing_contribution,
            "selection": sb.selection_contribution,
            "skill": sb.skill_return,
        }
        for sb in result.strategy_breakdown
    }
