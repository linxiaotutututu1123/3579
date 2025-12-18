"""实验性策略模块 (军规级 v3.0).

本模块包含学术前沿策略，需要经过充分训练验证后才能启用。

功能特性:
    - 训练成熟度评估算法
    - 最低训练时间限制（3个月）
    - 80%成熟度启用门槛
    - 实时进度监控

军规要求:
    - 未达到80%成熟度禁止启用
    - 最低训练90天
    - 所有训练记录必须审计

示例:
    from src.strategy.experimental import (
        MaturityEvaluator,
        TrainingGate,
        TrainingMonitor,
    )

    # 创建成熟度评估器
    evaluator = MaturityEvaluator()

    # 检查是否可启用
    gate = TrainingGate(evaluator)
    if gate.can_activate():
        strategy.activate()
"""

from src.strategy.experimental.maturity_evaluator import (
    MaturityEvaluator,
    MaturityLevel,
    MaturityReport,
    MaturityScore,
)
from src.strategy.experimental.training_gate import (
    ActivationDecision,
    TrainingGate,
    TrainingGateConfig,
)
from src.strategy.experimental.training_monitor import (
    TrainingMonitor,
    TrainingProgress,
    TrainingSession,
    TrainingStatus,
)


__all__ = [
    "ActivationDecision",
    "MaturityEvaluator",
    "MaturityLevel",
    "MaturityReport",
    "MaturityScore",
    "TrainingGate",
    "TrainingGateConfig",
    "TrainingMonitor",
    "TrainingProgress",
    "TrainingSession",
    "TrainingStatus",
]
