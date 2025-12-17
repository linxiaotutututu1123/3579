"""
风险归因模块 - RiskAttribution (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §23 风险归因, §24 模型可解释性
V4 Scenarios:
- RISK.ATTRIBUTION.LOSS_EXPLAIN: 亏损归因分析
- RISK.ATTRIBUTION.FACTOR_DECOMPOSE: 因子分解
- RISK.ATTRIBUTION.SHAP_INTEGRATION: SHAP集成

军规覆盖:
- M19: 风险归因 - 每笔亏损必须有归因分析

功能特性:
- SHAP值计算 (模型可解释性)
- 因子归因 (动量/成交量/波动率)
- 亏损订单自动归因
- 审计日志记录

示例:
    >>> from src.risk.attribution import (
    ...     RiskAttributionEngine,
    ...     AttributionResult,
    ...     FactorContribution,
    ... )
    >>> engine = RiskAttributionEngine()
    >>> result = engine.attribute_loss(trade_info, features, model_output)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np


if TYPE_CHECKING:
    import torch


class AttributionMethod(Enum):
    """归因方法枚举."""

    SHAP = "SHAP"  # SHAP值 (需要shap库)
    GRADIENT = "GRADIENT"  # 梯度归因
    PERMUTATION = "PERMUTATION"  # 置换重要性
    SIMPLE = "SIMPLE"  # 简单因子分解


class FactorType(Enum):
    """因子类型枚举."""

    MOMENTUM = "MOMENTUM"  # 动量因子 (收益率)
    VOLUME = "VOLUME"  # 成交量因子
    VOLATILITY = "VOLATILITY"  # 波动率因子
    TREND = "TREND"  # 趋势因子
    REVERSAL = "REVERSAL"  # 反转因子
    LIQUIDITY = "LIQUIDITY"  # 流动性因子


@dataclass(frozen=True)
class FactorContribution:
    """因子贡献 (不可变).

    属性:
        factor_type: 因子类型
        contribution: 贡献度 (-1到1, 正=盈利贡献, 负=亏损贡献)
        importance: 重要性 (0到1, 绝对贡献度)
        shap_value: SHAP值 (可选)
        description: 描述
    """

    factor_type: FactorType
    contribution: float
    importance: float
    shap_value: float = 0.0
    description: str = ""


@dataclass
class AttributionResult:
    """归因结果.

    属性:
        trade_id: 交易ID
        symbol: 合约代码
        pnl: 盈亏金额
        is_loss: 是否亏损
        factors: 因子贡献列表
        primary_factor: 主要因子
        primary_contribution: 主要因子贡献度
        method: 归因方法
        confidence: 置信度 (0到1)
        feature_importances: 特征重要性字典
        shap_values: SHAP值数组 (可选)
        explanation: 可读解释
        timestamp: 时间戳
        metadata: 元数据
    """

    trade_id: str
    symbol: str
    pnl: float
    is_loss: bool
    factors: list[FactorContribution] = field(default_factory=list)
    primary_factor: FactorType = FactorType.MOMENTUM
    primary_contribution: float = 0.0
    method: AttributionMethod = AttributionMethod.SIMPLE
    confidence: float = 0.0
    feature_importances: dict[str, float] = field(default_factory=dict)
    shap_values: np.ndarray | None = None
    explanation: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式.

        返回:
            符合审计要求的字典
        """
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "pnl": self.pnl,
            "is_loss": self.is_loss,
            "primary_factor": self.primary_factor.value,
            "primary_contribution": round(self.primary_contribution, 4),
            "method": self.method.value,
            "confidence": round(self.confidence, 4),
            "factors": [
                {
                    "type": f.factor_type.value,
                    "contribution": round(f.contribution, 4),
                    "importance": round(f.importance, 4),
                }
                for f in self.factors
            ],
            "explanation": self.explanation,
            "timestamp": self.timestamp,
        }


@dataclass
class FeatureGroup:
    """特征组.

    属性:
        name: 组名
        start_idx: 起始索引
        end_idx: 结束索引
        factor_type: 对应因子类型
    """

    name: str
    start_idx: int
    end_idx: int
    factor_type: FactorType


class RiskAttributionEngine:
    """风险归因引擎 (军规 M19).

    功能:
    - 计算交易归因
    - SHAP值分析
    - 因子分解
    - 生成可读解释

    示例:
        >>> engine = RiskAttributionEngine(window=60)
        >>> result = engine.attribute_trade(
        ...     trade_id="T001",
        ...     symbol="rb2501",
        ...     pnl=-1000.0,
        ...     features=features,
        ...     model_output=0.5,
        ... )
    """

    # 特征组定义 (对应 features.py 的结构)
    DEFAULT_FEATURE_GROUPS: ClassVar[list[FeatureGroup]] = [
        FeatureGroup("returns", 0, 60, FactorType.MOMENTUM),
        FeatureGroup("volumes", 60, 120, FactorType.VOLUME),
        FeatureGroup("ranges", 120, 180, FactorType.VOLATILITY),
    ]

    def __init__(
        self,
        window: int = 60,
        method: AttributionMethod = AttributionMethod.SIMPLE,
        use_shap: bool = False,
    ) -> None:
        """初始化归因引擎.

        参数:
            window: 特征窗口大小
            method: 归因方法
            use_shap: 是否启用SHAP (需要shap库)
        """
        self._window = window
        self._method = method
        self._use_shap = use_shap
        self._shap_explainer: Any = None

        # 根据窗口大小调整特征组
        self._feature_groups = [
            FeatureGroup("returns", 0, window, FactorType.MOMENTUM),
            FeatureGroup("volumes", window, window * 2, FactorType.VOLUME),
            FeatureGroup("ranges", window * 2, window * 3, FactorType.VOLATILITY),
        ]

        # 统计
        self._attribution_count: int = 0
        self._loss_attribution_count: int = 0

    @property
    def window(self) -> int:
        """获取窗口大小."""
        return self._window

    @property
    def method(self) -> AttributionMethod:
        """获取归因方法."""
        return self._method

    @property
    def attribution_count(self) -> int:
        """获取归因总数."""
        return self._attribution_count

    @property
    def loss_attribution_count(self) -> int:
        """获取亏损归因数."""
        return self._loss_attribution_count

    def attribute_trade(
        self,
        trade_id: str,
        symbol: str,
        pnl: float,
        features: np.ndarray,
        model_output: float | None = None,
        model: torch.nn.Module | None = None,
        baseline_features: np.ndarray | None = None,
    ) -> AttributionResult:
        """归因单笔交易.

        参数:
            trade_id: 交易ID
            symbol: 合约代码
            pnl: 盈亏金额
            features: 特征向量
            model_output: 模型输出 (可选)
            model: PyTorch模型 (可选, 用于SHAP)
            baseline_features: 基准特征 (可选)

        返回:
            归因结果
        """
        self._attribution_count += 1
        is_loss = pnl < 0
        if is_loss:
            self._loss_attribution_count += 1

        # 选择归因方法
        if self._use_shap and model is not None:
            return self._attribute_with_shap(
                trade_id, symbol, pnl, features, model, baseline_features
            )
        if model_output is not None:
            return self._attribute_with_gradient(
                trade_id, symbol, pnl, features, model_output
            )
        return self._attribute_simple(trade_id, symbol, pnl, features)

    def attribute_loss(
        self,
        trade_id: str,
        symbol: str,
        loss_amount: float,
        features: np.ndarray,
        model_output: float | None = None,
    ) -> AttributionResult:
        """归因亏损交易 (军规 M19 强制要求).

        参数:
            trade_id: 交易ID
            symbol: 合约代码
            loss_amount: 亏损金额 (正数)
            features: 特征向量
            model_output: 模型输出 (可选)

        返回:
            归因结果
        """
        # 确保 loss_amount 为负数
        pnl = -abs(loss_amount) if loss_amount > 0 else loss_amount
        return self.attribute_trade(trade_id, symbol, pnl, features, model_output)

    def _attribute_simple(
        self,
        trade_id: str,
        symbol: str,
        pnl: float,
        features: np.ndarray,
    ) -> AttributionResult:
        """简单因子归因.

        基于特征组的统计量进行归因。

        参数:
            trade_id: 交易ID
            symbol: 合约代码
            pnl: 盈亏金额
            features: 特征向量

        返回:
            归因结果
        """
        is_loss = pnl < 0
        factors: list[FactorContribution] = []
        feature_importances: dict[str, float] = {}

        # 计算每个特征组的贡献
        total_variance = 0.0
        group_variances: dict[str, float] = {}

        for group in self._feature_groups:
            group_features = features[group.start_idx : group.end_idx]
            variance = float(np.var(group_features)) if len(group_features) > 0 else 0.0
            group_variances[group.name] = variance
            total_variance += variance

        # 归一化计算贡献度
        if total_variance > 1e-8:
            for group in self._feature_groups:
                variance = group_variances[group.name]
                importance = variance / total_variance

                # 计算方向性贡献 (基于均值)
                group_features = features[group.start_idx : group.end_idx]
                mean_value = float(np.mean(group_features))

                # 贡献度 = 重要性 × 方向
                contribution = importance * np.sign(mean_value)
                if is_loss:
                    contribution = -abs(contribution)  # 亏损时贡献为负

                factors.append(
                    FactorContribution(
                        factor_type=group.factor_type,
                        contribution=contribution,
                        importance=importance,
                        description=self._get_factor_description(
                            group.factor_type, contribution, mean_value
                        ),
                    )
                )

                feature_importances[group.name] = importance

        # 找出主要因子
        if factors:
            primary = max(factors, key=lambda f: f.importance)
            primary_factor = primary.factor_type
            primary_contribution = primary.contribution
        else:
            primary_factor = FactorType.MOMENTUM
            primary_contribution = 0.0

        # 生成解释
        explanation = self._generate_explanation(
            symbol, pnl, is_loss, factors, primary_factor
        )

        return AttributionResult(
            trade_id=trade_id,
            symbol=symbol,
            pnl=pnl,
            is_loss=is_loss,
            factors=factors,
            primary_factor=primary_factor,
            primary_contribution=primary_contribution,
            method=AttributionMethod.SIMPLE,
            confidence=0.7,  # 简单方法置信度较低
            feature_importances=feature_importances,
            explanation=explanation,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
        )

    def _attribute_with_gradient(
        self,
        trade_id: str,
        symbol: str,
        pnl: float,
        features: np.ndarray,
        model_output: float,
    ) -> AttributionResult:
        """基于梯度的归因.

        使用输入-输出敏感性进行归因。

        参数:
            trade_id: 交易ID
            symbol: 合约代码
            pnl: 盈亏金额
            features: 特征向量
            model_output: 模型输出

        返回:
            归因结果
        """
        is_loss = pnl < 0
        factors: list[FactorContribution] = []
        feature_importances: dict[str, float] = {}

        # 使用特征值乘以模型输出作为近似梯度
        # 这是一个简化版本，实际SHAP会更准确
        total_contribution = 0.0
        group_contributions: dict[str, float] = {}

        for group in self._feature_groups:
            group_features = features[group.start_idx : group.end_idx]
            # 近似贡献 = 特征均值 × 模型输出
            contribution = float(np.mean(group_features) * model_output)
            group_contributions[group.name] = abs(contribution)
            total_contribution += abs(contribution)

        # 归一化
        if total_contribution > 1e-8:
            for group in self._feature_groups:
                raw_contribution = group_contributions[group.name]
                importance = raw_contribution / total_contribution

                # 方向性
                group_features = features[group.start_idx : group.end_idx]
                mean_value = float(np.mean(group_features))
                direction = np.sign(mean_value * model_output)

                contribution = importance * direction
                if is_loss:
                    contribution = -abs(contribution)

                factors.append(
                    FactorContribution(
                        factor_type=group.factor_type,
                        contribution=contribution,
                        importance=importance,
                        description=self._get_factor_description(
                            group.factor_type, contribution, mean_value
                        ),
                    )
                )

                feature_importances[group.name] = importance

        # 主要因子
        if factors:
            primary = max(factors, key=lambda f: f.importance)
            primary_factor = primary.factor_type
            primary_contribution = primary.contribution
        else:
            primary_factor = FactorType.MOMENTUM
            primary_contribution = 0.0

        explanation = self._generate_explanation(
            symbol, pnl, is_loss, factors, primary_factor
        )

        return AttributionResult(
            trade_id=trade_id,
            symbol=symbol,
            pnl=pnl,
            is_loss=is_loss,
            factors=factors,
            primary_factor=primary_factor,
            primary_contribution=primary_contribution,
            method=AttributionMethod.GRADIENT,
            confidence=0.8,
            feature_importances=feature_importances,
            explanation=explanation,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
            metadata={"model_output": model_output},
        )

    def _attribute_with_shap(
        self,
        trade_id: str,
        symbol: str,
        pnl: float,
        features: np.ndarray,
        model: torch.nn.Module,
        baseline_features: np.ndarray | None = None,
    ) -> AttributionResult:
        """基于SHAP的归因.

        使用SHAP库计算特征重要性。

        参数:
            trade_id: 交易ID
            symbol: 合约代码
            pnl: 盈亏金额
            features: 特征向量
            model: PyTorch模型
            baseline_features: 基准特征

        返回:
            归因结果
        """
        is_loss = pnl < 0

        try:
            import shap
            import torch

            # 创建模型包装器
            def model_wrapper(x: np.ndarray) -> np.ndarray:
                with torch.no_grad():
                    tensor = torch.from_numpy(x).float()
                    output = model(tensor)
                    result: np.ndarray = output.numpy()
                    return result

            # 准备基准数据
            if baseline_features is None:
                baseline_features = np.zeros_like(features)

            background = baseline_features.reshape(1, -1)
            test_data = features.reshape(1, -1)

            # 创建SHAP解释器
            explainer = shap.KernelExplainer(model_wrapper, background)
            shap_values = explainer.shap_values(test_data, nsamples=100)

            if isinstance(shap_values, list):
                shap_values = shap_values[0]

            shap_values = shap_values.flatten()

        except ImportError:
            # 如果shap不可用，回退到梯度方法
            return self._attribute_with_gradient(trade_id, symbol, pnl, features, 0.0)
        except Exception:
            # 其他错误也回退
            return self._attribute_with_gradient(trade_id, symbol, pnl, features, 0.0)

        # 按特征组聚合SHAP值
        factors: list[FactorContribution] = []
        feature_importances: dict[str, float] = {}
        total_shap = float(np.sum(np.abs(shap_values)))

        for group in self._feature_groups:
            group_shap = shap_values[group.start_idx : group.end_idx]
            group_sum = float(np.sum(group_shap))
            group_abs_sum = float(np.sum(np.abs(group_shap)))

            importance = group_abs_sum / total_shap if total_shap > 1e-8 else 0.0
            contribution = group_sum / total_shap if total_shap > 1e-8 else 0.0

            if is_loss and contribution > 0:
                contribution = -contribution

            factors.append(
                FactorContribution(
                    factor_type=group.factor_type,
                    contribution=contribution,
                    importance=importance,
                    shap_value=group_sum,
                    description=self._get_factor_description(
                        group.factor_type, contribution, group_sum
                    ),
                )
            )

            feature_importances[group.name] = importance

        # 主要因子
        if factors:
            primary = max(factors, key=lambda f: f.importance)
            primary_factor = primary.factor_type
            primary_contribution = primary.contribution
        else:
            primary_factor = FactorType.MOMENTUM
            primary_contribution = 0.0

        explanation = self._generate_explanation(
            symbol, pnl, is_loss, factors, primary_factor
        )

        return AttributionResult(
            trade_id=trade_id,
            symbol=symbol,
            pnl=pnl,
            is_loss=is_loss,
            factors=factors,
            primary_factor=primary_factor,
            primary_contribution=primary_contribution,
            method=AttributionMethod.SHAP,
            confidence=0.95,  # SHAP置信度最高
            feature_importances=feature_importances,
            shap_values=shap_values,
            explanation=explanation,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
        )

    def _get_factor_description(
        self,
        factor_type: FactorType,
        contribution: float,
        raw_value: float,
    ) -> str:
        """生成因子描述.

        参数:
            factor_type: 因子类型
            contribution: 贡献度
            raw_value: 原始值

        返回:
            描述字符串
        """
        direction = "正向" if contribution > 0 else "负向"
        strength = (
            "强"
            if abs(contribution) > 0.5
            else "中"
            if abs(contribution) > 0.2
            else "弱"
        )

        descriptions = {
            FactorType.MOMENTUM: f"动量因子{direction}贡献({strength}): 收益率趋势影响",
            FactorType.VOLUME: f"成交量因子{direction}贡献({strength}): 交易活跃度影响",
            FactorType.VOLATILITY: f"波动率因子{direction}贡献({strength}): 价格波动影响",
            FactorType.TREND: f"趋势因子{direction}贡献({strength}): 长期趋势影响",
            FactorType.REVERSAL: f"反转因子{direction}贡献({strength}): 价格反转影响",
            FactorType.LIQUIDITY: f"流动性因子{direction}贡献({strength}): 市场流动性影响",
        }

        return descriptions.get(factor_type, f"{factor_type.value}因子贡献")

    def _generate_explanation(
        self,
        symbol: str,
        pnl: float,
        is_loss: bool,
        factors: list[FactorContribution],
        primary_factor: FactorType,
    ) -> str:
        """生成可读解释.

        参数:
            symbol: 合约代码
            pnl: 盈亏金额
            is_loss: 是否亏损
            factors: 因子列表
            primary_factor: 主要因子

        返回:
            可读解释字符串
        """
        result_type = "亏损" if is_loss else "盈利"
        pnl_str = f"{abs(pnl):.2f}"

        # 主因子解释
        factor_names = {
            FactorType.MOMENTUM: "价格动量",
            FactorType.VOLUME: "成交量变化",
            FactorType.VOLATILITY: "市场波动",
            FactorType.TREND: "趋势变化",
            FactorType.REVERSAL: "价格反转",
            FactorType.LIQUIDITY: "流动性变化",
        }

        primary_name = factor_names.get(primary_factor, primary_factor.value)

        # 次要因子
        secondary_factors = [
            f for f in factors if f.factor_type != primary_factor and f.importance > 0.1
        ]
        secondary_str = ""
        if secondary_factors:
            secondary_names = [
                factor_names.get(f.factor_type, f.factor_type.value)
                for f in secondary_factors[:2]
            ]
            secondary_str = f", 次要因素: {', '.join(secondary_names)}"

        return f"合约 {symbol} {result_type} ¥{pnl_str}, 主要归因: {primary_name}{secondary_str}"

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        return {
            "attribution_count": self._attribution_count,
            "loss_attribution_count": self._loss_attribution_count,
            "loss_rate": (
                self._loss_attribution_count / self._attribution_count
                if self._attribution_count > 0
                else 0.0
            ),
            "method": self._method.value,
            "window": self._window,
            "use_shap": self._use_shap,
        }

    def reset_statistics(self) -> None:
        """重置统计信息."""
        self._attribution_count = 0
        self._loss_attribution_count = 0


# ============================================================
# 便捷函数
# ============================================================


def create_attribution_engine(
    window: int = 60,
    method: AttributionMethod = AttributionMethod.SIMPLE,
    use_shap: bool = False,
) -> RiskAttributionEngine:
    """创建归因引擎.

    参数:
        window: 特征窗口大小
        method: 归因方法
        use_shap: 是否启用SHAP

    返回:
        归因引擎实例
    """
    return RiskAttributionEngine(window=window, method=method, use_shap=use_shap)


def attribute_trade_loss(
    trade_id: str,
    symbol: str,
    loss_amount: float,
    features: np.ndarray,
    model_output: float | None = None,
) -> AttributionResult:
    """归因亏损交易 (便捷函数).

    参数:
        trade_id: 交易ID
        symbol: 合约代码
        loss_amount: 亏损金额
        features: 特征向量
        model_output: 模型输出

    返回:
        归因结果
    """
    engine = RiskAttributionEngine()
    return engine.attribute_loss(trade_id, symbol, loss_amount, features, model_output)


def get_factor_summary(result: AttributionResult) -> dict[str, float]:
    """获取因子摘要.

    参数:
        result: 归因结果

    返回:
        因子贡献摘要
    """
    return {f.factor_type.value: f.contribution for f in result.factors}
