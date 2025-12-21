"""
成本估计模块.

V4PRO Platform Component - Phase 1/7
V2 SPEC: 第 6 章 成本模型

Exports:
    CostEstimator: 成本估计器
    CostBreakdown: 成本分解
    ChinaFeeCalculator: 中国期货手续费计算器 (Phase 7)
    FeeConfig: 手续费配置
    FeeResult: 手续费计算结果
    FeeType: 手续费类型枚举
    TradeDirection: 交易方向枚举
"""

from src.cost.china_fee_calculator import (
    ChinaFeeCalculator,
    FeeConfig,
    FeeResult,
    FeeType,
    TradeDirection,
    calculate_fee,
    estimate_cost,
    get_default_calculator,
)
from src.cost.estimator import CostBreakdown, CostEstimator


__all__ = [
    # Phase 7 新增: 中国期货手续费计算器
    "ChinaFeeCalculator",
    # 原有导出
    "CostBreakdown",
    "CostEstimator",
    "FeeConfig",
    "FeeResult",
    "FeeType",
    "TradeDirection",
    "calculate_fee",
    "estimate_cost",
    "get_default_calculator",
]
