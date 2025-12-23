"""成本先行机制模块.

V4PRO Platform Component - Phase 8
V2 SPEC: 成本先行机制

军规覆盖:
- M5: 成本先行 - 交易执行前必须完成成本预估
- M3: 审计日志 - 所有成本计算结果必须可追溯

本模块提供:
- CostFirstCalculator: 交易成本预估计算器
- CostValidator: 成本验证器
- CostEstimate: 成本估算结果
- CostValidationResult: 成本验证结果
- MarketDepth: 市场深度数据
- CostThresholds: 成本阈值配置

示例:
    >>> from src.execution.cost_first import (
    ...     CostFirstCalculator,
    ...     CostValidator,
    ...     MarketDepth,
    ... )
    >>> calc = CostFirstCalculator()
    >>> estimate = calc.estimate_total_cost(
    ...     instrument="rb2501",
    ...     price=3500.0,
    ...     volume=10,
    ...     direction="buy"
    ... )
    >>> validator = CostValidator(calculator=calc)
    >>> result = validator.validate(
    ...     instrument="rb2501",
    ...     price=3500.0,
    ...     volume=10,
    ...     direction="buy",
    ...     expected_profit=200.0,
    ...     expected_loss=100.0
    ... )
    >>> if result.passed:
    ...     print("成本验证通过，可以执行交易")
"""

from __future__ import annotations

from src.execution.cost_first.cost_calculator import (
    CostAlertLevel,
    CostAuditEvent,
    CostCheckResult,
    CostEstimate,
    CostFirstCalculator,
    CostThresholds,
    CostValidationResult,
    CostValidator,
    MarketDepth,
    create_cost_audit_event,
)

__all__ = [
    # 核心类
    "CostFirstCalculator",
    "CostValidator",
    # 数据类
    "CostEstimate",
    "CostValidationResult",
    "MarketDepth",
    "CostThresholds",
    "CostAuditEvent",
    # 枚举
    "CostCheckResult",
    "CostAlertLevel",
    # 工厂函数
    "create_cost_audit_event",
]
