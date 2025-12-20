"""交叉验证指标模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M19(风险归因)

V4PRO Scenarios:
- K46: CV.METRICS.SHARPE - 夏普比率验证
- K47: CV.METRICS.DRAWDOWN - 最大回撤验证
- K48: CV.METRICS.STABILITY - 稳定性验证
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class CVMetrics:
    """交叉验证指标集合."""

    # 基础指标
    mean_return: float = 0.0
    std_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0

    # 风险指标
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    var_95: float = 0.0  # 95% VaR
    cvar_95: float = 0.0  # 95% CVaR

    # 稳定性指标
    win_rate: float = 0.0
    profit_factor: float = 0.0
    stability_score: float = 0.0

    # 验证指标
    mean_test_score: float = 0.0
    std_test_score: float = 0.0
    cv_score: float = 0.0  # 变异系数

    # M3: 审计信息
    n_folds: int = 0
    fold_scores: list[float] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def compute_sharpe_ratio(
    returns: NDArray[np.float64],
    risk_free_rate: float = 0.0,
    annualization_factor: float = 252.0,
) -> float:
    """计算夏普比率 (K46).

    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率(年化)
        annualization_factor: 年化因子

    Returns:
        夏普比率
    """
    if len(returns) < 2:
        return 0.0

    # 日化无风险利率
    daily_rf = risk_free_rate / annualization_factor

    excess_returns = returns - daily_rf
    mean_excess = float(np.mean(excess_returns))
    std_excess = float(np.std(excess_returns, ddof=1))

    if std_excess < 1e-10:
        return 0.0

    # 年化夏普
    sharpe = (mean_excess / std_excess) * np.sqrt(annualization_factor)

    return float(sharpe)


def compute_sortino_ratio(
    returns: NDArray[np.float64],
    risk_free_rate: float = 0.0,
    annualization_factor: float = 252.0,
) -> float:
    """计算索提诺比率.

    只考虑下行风险.

    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率(年化)
        annualization_factor: 年化因子

    Returns:
        索提诺比率
    """
    if len(returns) < 2:
        return 0.0

    daily_rf = risk_free_rate / annualization_factor
    excess_returns = returns - daily_rf

    mean_excess = float(np.mean(excess_returns))

    # 下行标准差
    downside_returns = excess_returns[excess_returns < 0]
    if len(downside_returns) < 2:
        return 0.0

    downside_std = float(np.std(downside_returns, ddof=1))

    if downside_std < 1e-10:
        return 0.0

    sortino = (mean_excess / downside_std) * np.sqrt(annualization_factor)

    return float(sortino)


def compute_max_drawdown(
    returns: NDArray[np.float64],
) -> float:
    """计算最大回撤 (K47).

    Args:
        returns: 收益率序列

    Returns:
        最大回撤(正数)
    """
    if len(returns) < 2:
        return 0.0

    # 累计收益
    cumulative = np.cumprod(1 + returns)

    # 运行最大值
    running_max = np.maximum.accumulate(cumulative)

    # 回撤
    drawdowns = (running_max - cumulative) / running_max

    return float(np.max(drawdowns))


def compute_calmar_ratio(
    returns: NDArray[np.float64],
    annualization_factor: float = 252.0,
) -> float:
    """计算卡玛比率.

    年化收益 / 最大回撤

    Args:
        returns: 收益率序列
        annualization_factor: 年化因子

    Returns:
        卡玛比率
    """
    max_dd = compute_max_drawdown(returns)

    if max_dd < 1e-10:
        return 0.0

    # 年化收益
    total_return = float(np.prod(1 + returns) - 1)
    n_periods = len(returns)
    annual_return = (1 + total_return) ** (annualization_factor / n_periods) - 1

    return annual_return / max_dd


def compute_var(
    returns: NDArray[np.float64],
    confidence: float = 0.95,
) -> float:
    """计算VaR (Value at Risk).

    Args:
        returns: 收益率序列
        confidence: 置信度

    Returns:
        VaR值(正数表示损失)
    """
    if len(returns) < 10:
        return 0.0

    var = float(np.percentile(returns, (1 - confidence) * 100))
    return -var if var < 0 else 0.0


def compute_cvar(
    returns: NDArray[np.float64],
    confidence: float = 0.95,
) -> float:
    """计算CVaR (Conditional VaR).

    Args:
        returns: 收益率序列
        confidence: 置信度

    Returns:
        CVaR值(正数表示损失)
    """
    if len(returns) < 10:
        return 0.0

    var_threshold = np.percentile(returns, (1 - confidence) * 100)
    tail_returns = returns[returns <= var_threshold]

    if len(tail_returns) == 0:
        return 0.0

    cvar = float(np.mean(tail_returns))
    return -cvar if cvar < 0 else 0.0


def compute_stability_score(
    fold_scores: list[float],
) -> float:
    """计算稳定性分数 (K48).

    基于各折分数的一致性.

    Args:
        fold_scores: 各折分数列表

    Returns:
        稳定性分数 [0, 1]
    """
    if len(fold_scores) < 2:
        return 0.0

    scores = np.array(fold_scores)
    mean_score = float(np.mean(scores))
    std_score = float(np.std(scores, ddof=1))

    if abs(mean_score) < 1e-10:
        return 0.0

    # 变异系数的反向映射
    cv = std_score / abs(mean_score)

    # 映射到 [0, 1], CV越小越稳定
    stability = 1 / (1 + cv)

    return float(stability)


def compute_win_rate(
    returns: NDArray[np.float64],
) -> float:
    """计算胜率.

    Args:
        returns: 收益率序列

    Returns:
        胜率 [0, 1]
    """
    if len(returns) == 0:
        return 0.0

    wins = np.sum(returns > 0)
    return float(wins / len(returns))


def compute_profit_factor(
    returns: NDArray[np.float64],
) -> float:
    """计算盈亏比.

    总盈利 / 总亏损

    Args:
        returns: 收益率序列

    Returns:
        盈亏比
    """
    gains = returns[returns > 0]
    losses = returns[returns < 0]

    total_gains = float(np.sum(gains)) if len(gains) > 0 else 0.0
    total_losses = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0

    if total_losses < 1e-10:
        return float("inf") if total_gains > 0 else 0.0

    return total_gains / total_losses


def compute_cv_metrics(
    returns: NDArray[np.float64],
    fold_scores: list[float] | None = None,
    risk_free_rate: float = 0.0,
) -> CVMetrics:
    """计算完整CV指标集 (K46-K48).

    Args:
        returns: 收益率序列
        fold_scores: 各折分数(可选)
        risk_free_rate: 无风险利率

    Returns:
        CVMetrics对象
    """
    fold_scores = fold_scores or []

    metrics = CVMetrics(
        # 基础指标
        mean_return=float(np.mean(returns)) if len(returns) > 0 else 0.0,
        std_return=float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0,
        sharpe_ratio=compute_sharpe_ratio(returns, risk_free_rate),
        sortino_ratio=compute_sortino_ratio(returns, risk_free_rate),
        # 风险指标
        max_drawdown=compute_max_drawdown(returns),
        calmar_ratio=compute_calmar_ratio(returns),
        var_95=compute_var(returns, 0.95),
        cvar_95=compute_cvar(returns, 0.95),
        # 稳定性指标
        win_rate=compute_win_rate(returns),
        profit_factor=compute_profit_factor(returns),
        stability_score=compute_stability_score(fold_scores),
        # 验证指标
        mean_test_score=float(np.mean(fold_scores)) if fold_scores else 0.0,
        std_test_score=float(np.std(fold_scores, ddof=1)) if len(fold_scores) > 1 else 0.0,
        n_folds=len(fold_scores),
        fold_scores=fold_scores.copy() if fold_scores else [],
    )

    # 计算CV分数(变异系数)
    if metrics.mean_test_score != 0:
        metrics.cv_score = metrics.std_test_score / abs(metrics.mean_test_score)

    return metrics
