"""实验性策略模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 智能策略升级
V4 SPEC: §24 实验性策略门禁

本模块包含学术前沿策略，需要经过充分训练验证后才能启用。

功能特性:
    - 训练成熟度评估算法
    - 最低训练时间限制（3个月）
    - 80%成熟度启用门槛
    - 实时进度监控
    - 策略生命周期管理 (v4.2新增)
    - 资金分配联动 (v4.2新增)
    - 自动晋升/降级 (v4.2新增)

军规覆盖:
    - M18: 实验性门禁 - 未成熟策略禁止实盘启用
    - M12: 双重确认 - 大额调整需人工审批
    - M19: 风险归因 - 策略表现追踪

示例:
    from src.strategy.experimental import (
        MaturityEvaluator,
        TrainingGate,
        TrainingMonitor,
        StrategyLifecycleManager,
    )

    # 创建生命周期管理器
    manager = StrategyLifecycleManager()
    manager.register_strategy("ppo_v1", "PPO策略", "rl")

    # 更新成熟度
    manager.update_maturity("ppo_v1", 0.85)

    # 获取资金分配
    allocation = manager.get_allocation("ppo_v1")
"""

from src.strategy.experimental.maturity_evaluator import (
    MaturityEvaluator,
    MaturityLevel,
    MaturityReport,
    MaturityScore,
)
from src.strategy.experimental.strategy_lifecycle import (
    ALLOCATION_CONFIGS,
    AllocationConfig,
    AllocationResult,
    AllocationTier,
    LifecycleStage,
    StrategyLifecycleManager,
    StrategyPerformance,
    StrategyState,
    TransitionEvent,
    create_lifecycle_manager,
    get_allocation_for_maturity,
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
    # 成熟度评估
    "MaturityEvaluator",
    "MaturityLevel",
    "MaturityReport",
    "MaturityScore",
    # 训练门禁
    "ActivationDecision",
    "TrainingGate",
    "TrainingGateConfig",
    # 训练监控
    "TrainingMonitor",
    "TrainingProgress",
    "TrainingSession",
    "TrainingStatus",
    # 生命周期管理 (v4.2)
    "ALLOCATION_CONFIGS",
    "AllocationConfig",
    "AllocationResult",
    "AllocationTier",
    "LifecycleStage",
    "StrategyLifecycleManager",
    "StrategyPerformance",
    "StrategyState",
    "TransitionEvent",
    "create_lifecycle_manager",
    "get_allocation_for_maturity",
]
