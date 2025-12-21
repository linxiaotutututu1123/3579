"""DL Factors Layer - 因子分析模块.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计), M19(风险归因)

V4PRO Scenarios:
- DL.FACTOR.IC.COMPUTE - IC计算
- DL.FACTOR.IC.DECAY - IC衰减分析
- DL.FACTOR.RANK - 因子排序
"""

from __future__ import annotations

from src.strategy.dl.factors.ic_calculator import (
    FactorMetrics,
    ICCalculator,
    ICConfig,
    ICResult,
)


__all__ = [
    "FactorMetrics",
    "ICCalculator",
    "ICConfig",
    "ICResult",
]
