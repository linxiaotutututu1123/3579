"""DL Training Layer - 训练层模块.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计), M26(测试规范)

V4PRO Scenarios:
- DL.TRAIN.LOOP - 训练循环
- DL.TRAIN.EARLY_STOP - 早停机制
- DL.TRAIN.CHECKPOINT - 检查点保存
"""

from __future__ import annotations

from src.strategy.dl.training.trainer import (
    EarlyStopping,
    TradingModelTrainer,
    TrainerConfig,
    TrainerMetrics,
)


__all__ = [
    "EarlyStopping",
    "TrainerConfig",
    "TrainerMetrics",
    "TradingModelTrainer",
]
