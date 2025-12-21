"""Information Coefficient计算器.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计), M19(风险归因)

V4PRO Scenarios:
- DL.FACTOR.IC.COMPUTE - IC计算(门禁: IC >= 0.05)
- DL.FACTOR.IC.DECAY - IC衰减分析
- DL.FACTOR.IC.RANK - 因子排名IC
"""

from __future__ import annotations

from collections.abc import Sequence as PySequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.stats import pearsonr, spearmanr


@dataclass
class ICConfig:
    """IC计算配置.

    Attributes:
        method: 计算方法('spearman'或'pearson')
        min_samples: 最小样本数
        decay_periods: IC衰减分析周期列表
        ic_threshold: IC门禁阈值
        significance_level: 显著性水平
    """

    method: str = "spearman"  # 'spearman' or 'pearson'
    min_samples: int = 30
    decay_periods: tuple[int, ...] = (1, 5, 10, 20)
    ic_threshold: float = 0.05  # 门禁: IC >= 0.05
    significance_level: float = 0.05


@dataclass
class ICResult:
    """IC计算结果.

    Attributes:
        ic: Information Coefficient值
        p_value: p值
        n_samples: 样本数
        is_significant: 是否显著
        passes_threshold: 是否通过门禁
    """

    ic: float
    p_value: float
    n_samples: int
    is_significant: bool
    passes_threshold: bool

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "ic": self.ic,
            "p_value": self.p_value,
            "n_samples": self.n_samples,
            "is_significant": self.is_significant,
            "passes_threshold": self.passes_threshold,
        }


@dataclass
class FactorMetrics:
    """因子评估指标.

    Attributes:
        ic_mean: IC均值
        ic_std: IC标准差
        icir: IC信息比率 (IC_mean / IC_std)
        ic_positive_ratio: IC为正的比例
        ic_decay: IC衰减曲线
        turnover: 因子换手率
    """

    ic_mean: float = 0.0
    ic_std: float = 0.0
    icir: float = 0.0
    ic_positive_ratio: float = 0.0
    ic_decay: dict[int, float] = field(default_factory=dict)
    turnover: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "ic_mean": self.ic_mean,
            "ic_std": self.ic_std,
            "icir": self.icir,
            "ic_positive_ratio": self.ic_positive_ratio,
            "ic_decay": self.ic_decay,
            "turnover": self.turnover,
        }

    def passes_gate(self, threshold: float = 0.05) -> bool:
        """检查是否通过门禁.

        Args:
            threshold: IC阈值

        Returns:
            是否通过
        """
        return self.ic_mean >= threshold


class ICCalculator:
    """IC计算器 (军规级).

    用于计算因子或模型预测的Information Coefficient。

    军规覆盖:
    - M7: 确定性计算
    - M3: 完整审计日志
    - M19: 风险归因追踪

    门禁要求:
    - IC均值 >= 0.05

    Example:
        >>> config = ICConfig(method='spearman')
        >>> calculator = ICCalculator(config)
        >>> result = calculator.compute(predictions, returns)
        >>> assert result.passes_threshold, "IC未通过门禁"
    """

    def __init__(self, config: ICConfig | None = None) -> None:
        """初始化IC计算器.

        Args:
            config: IC配置
        """
        self.config = config or ICConfig()

        # M3: 审计日志
        self._computation_log: list[dict[str, Any]] = []

    def compute(
        self,
        predictions: PySequence[float] | NDArray[np.floating],
        returns: PySequence[float] | NDArray[np.floating],
    ) -> ICResult:
        """计算IC (DL.FACTOR.IC.COMPUTE).

        Args:
            predictions: 模型预测值/因子值
            returns: 实际收益率

        Returns:
            IC计算结果
        """
        preds = np.asarray(predictions, dtype=np.float64)
        rets = np.asarray(returns, dtype=np.float64)

        # 验证数据
        n_samples = len(preds)
        if n_samples != len(rets):
            raise ValueError("predictions and returns must have same length")

        if n_samples < self.config.min_samples:
            return ICResult(
                ic=0.0,
                p_value=1.0,
                n_samples=n_samples,
                is_significant=False,
                passes_threshold=False,
            )

        # 移除NaN
        valid_mask = ~(np.isnan(preds) | np.isnan(rets))
        preds = preds[valid_mask]
        rets = rets[valid_mask]
        n_valid = len(preds)

        if n_valid < self.config.min_samples:
            return ICResult(
                ic=0.0,
                p_value=1.0,
                n_samples=n_valid,
                is_significant=False,
                passes_threshold=False,
            )

        # 计算相关系数
        if self.config.method == "spearman":
            ic, p_value = spearmanr(preds, rets)
        else:
            ic, p_value = pearsonr(preds, rets)

        # 处理NaN
        if np.isnan(ic):
            ic = 0.0
            p_value = 1.0

        is_significant = p_value < self.config.significance_level
        passes_threshold = ic >= self.config.ic_threshold

        result = ICResult(
            ic=float(ic),
            p_value=float(p_value),
            n_samples=n_valid,
            is_significant=is_significant,
            passes_threshold=passes_threshold,
        )

        # M3: 记录日志
        self._log_computation(result)

        return result

    def compute_rolling(
        self,
        predictions: PySequence[float] | NDArray[np.floating],
        returns: PySequence[float] | NDArray[np.floating],
        window: int = 20,
    ) -> list[ICResult]:
        """计算滚动IC.

        Args:
            predictions: 预测值序列
            returns: 收益率序列
            window: 滚动窗口大小

        Returns:
            滚动IC结果列表
        """
        preds = np.asarray(predictions, dtype=np.float64)
        rets = np.asarray(returns, dtype=np.float64)

        n = len(preds)
        results: list[ICResult] = []

        for i in range(window, n + 1):
            window_preds = preds[i - window : i]
            window_rets = rets[i - window : i]
            result = self.compute(window_preds, window_rets)
            results.append(result)

        return results

    def compute_decay(
        self,
        predictions: PySequence[float] | NDArray[np.floating],
        returns_matrix: NDArray[np.floating],
    ) -> dict[int, float]:
        """计算IC衰减 (DL.FACTOR.IC.DECAY).

        分析因子/预测在不同持有期的IC。

        Args:
            predictions: 预测值(t时刻)
            returns_matrix: 收益率矩阵, shape=(n_samples, max_period)
                           每列是不同持有期的收益

        Returns:
            持有期到IC的映射
        """
        preds = np.asarray(predictions, dtype=np.float64)

        decay: dict[int, float] = {}

        for period in self.config.decay_periods:
            if period <= returns_matrix.shape[1]:
                # 计算period期收益
                period_returns = returns_matrix[:, period - 1]
                result = self.compute(preds, period_returns)
                decay[period] = result.ic

        return decay

    def compute_rank_ic(
        self,
        predictions: PySequence[float] | NDArray[np.floating],
        returns: PySequence[float] | NDArray[np.floating],
    ) -> ICResult:
        """计算Rank IC (DL.FACTOR.IC.RANK).

        基于排名的IC计算,对异常值更稳健。

        Args:
            predictions: 预测值
            returns: 收益率

        Returns:
            Rank IC结果
        """
        preds = np.asarray(predictions, dtype=np.float64)
        rets = np.asarray(returns, dtype=np.float64)

        # 转换为排名
        from scipy.stats import rankdata

        pred_ranks = rankdata(preds, method="average")
        ret_ranks = rankdata(rets, method="average")

        # 使用Pearson计算排名相关
        return self.compute(pred_ranks, ret_ranks)

    def compute_factor_metrics(
        self,
        predictions_series: list[PySequence[float]],
        returns_series: list[PySequence[float]],
    ) -> FactorMetrics:
        """计算完整因子评估指标.

        Args:
            predictions_series: 多期预测值列表
            returns_series: 多期收益率列表

        Returns:
            因子评估指标
        """
        if len(predictions_series) != len(returns_series):
            raise ValueError("predictions and returns series must have same length")

        # 计算每期IC
        ic_values: list[float] = []
        for preds, rets in zip(predictions_series, returns_series, strict=True):
            result = self.compute(preds, rets)
            ic_values.append(result.ic)

        ic_array = np.array(ic_values)

        # IC统计
        ic_mean = float(np.mean(ic_array))
        ic_std = float(np.std(ic_array)) if len(ic_array) > 1 else 0.0
        icir = ic_mean / ic_std if ic_std > 0 else 0.0
        ic_positive_ratio = float(np.mean(ic_array > 0))

        # 计算换手率(使用预测值的变化)
        turnover = self._compute_turnover(predictions_series)

        return FactorMetrics(
            ic_mean=ic_mean,
            ic_std=ic_std,
            icir=icir,
            ic_positive_ratio=ic_positive_ratio,
            turnover=turnover,
        )

    def _compute_turnover(
        self,
        predictions_series: list[PySequence[float]],
    ) -> float:
        """计算因子换手率.

        Args:
            predictions_series: 多期预测值

        Returns:
            平均换手率
        """
        if len(predictions_series) < 2:
            return 0.0

        turnovers: list[float] = []

        for i in range(1, len(predictions_series)):
            prev = np.asarray(predictions_series[i - 1])
            curr = np.asarray(predictions_series[i])

            # 计算排名变化
            from scipy.stats import rankdata

            prev_rank = rankdata(prev, method="average")
            curr_rank = rankdata(curr, method="average")

            # 换手率 = 排名变化的平均值 / 样本数
            rank_change = np.abs(curr_rank - prev_rank)
            turnover = float(np.mean(rank_change)) / len(prev)
            turnovers.append(turnover)

        return float(np.mean(turnovers))

    def _log_computation(self, result: ICResult) -> None:
        """记录计算日志 (M3).

        Args:
            result: IC计算结果
        """
        import time

        log_entry = {
            "timestamp": time.time(),
            "ic": result.ic,
            "p_value": result.p_value,
            "n_samples": result.n_samples,
            "is_significant": result.is_significant,
            "passes_threshold": result.passes_threshold,
            "method": self.config.method,
        }
        self._computation_log.append(log_entry)

    def get_computation_log(self) -> list[dict[str, Any]]:
        """获取计算日志 (M3).

        Returns:
            计算日志列表
        """
        return self._computation_log.copy()

    def validate_model(
        self,
        predictions: PySequence[float],
        returns: PySequence[float],
    ) -> tuple[bool, str]:
        """验证模型是否通过IC门禁.

        Args:
            predictions: 预测值
            returns: 收益率

        Returns:
            (是否通过, 消息)
        """
        result = self.compute(predictions, returns)

        if result.passes_threshold:
            return True, f"IC = {result.ic:.4f} >= {self.config.ic_threshold} (PASS)"
        else:
            return False, f"IC = {result.ic:.4f} < {self.config.ic_threshold} (FAIL)"

    def reset(self) -> None:
        """重置计算器状态."""
        self._computation_log.clear()


def compute_ic(
    predictions: PySequence[float],
    returns: PySequence[float],
    method: str = "spearman",
) -> float:
    """计算IC的便捷函数.

    Args:
        predictions: 预测值
        returns: 收益率
        method: 计算方法

    Returns:
        IC值
    """
    config = ICConfig(method=method)
    calculator = ICCalculator(config)
    result = calculator.compute(predictions, returns)
    return result.ic


def validate_ic_gate(
    predictions: PySequence[float],
    returns: PySequence[float],
    threshold: float = 0.05,
) -> bool:
    """验证IC门禁的便捷函数.

    Args:
        predictions: 预测值
        returns: 收益率
        threshold: IC阈值

    Returns:
        是否通过门禁
    """
    config = ICConfig(ic_threshold=threshold)
    calculator = ICCalculator(config)
    result = calculator.compute(predictions, returns)
    return result.passes_threshold
