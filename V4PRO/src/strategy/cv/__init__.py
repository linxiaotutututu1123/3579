"""交叉验证模块 (军规级 v4.2).

V4PRO Platform Component - Phase K B类模型层
V4 SPEC: §26 时间序列交叉验证

本模块包含金融时间序列专用的交叉验证方法:
- M7: 回放一致性 - 确定性分割
- M3: 完整审计 - 验证日志
- M19: 风险归因 - 性能追踪

功能特性:
    - 滚动窗口验证 (Walk-Forward)
    - 时间序列K折 (Purged K-Fold)
    - 组合净化交叉验证 (Combinatorial Purged CV)
    - 验证指标计算
"""

from src.strategy.cv.base import (
    CrossValidator,
    CVConfig,
    CVResult,
    CVSplit,
)
from src.strategy.cv.metrics import (
    CVMetrics,
    compute_cv_metrics,
    compute_max_drawdown,
    compute_sharpe_ratio,
)
from src.strategy.cv.purged_kfold import (
    PurgedKFoldConfig,
    PurgedKFoldCV,
)
from src.strategy.cv.walk_forward import (
    WalkForwardConfig,
    WalkForwardCV,
)


__all__ = [
    # 基础类
    "CVConfig",
    "CVResult",
    "CVSplit",
    "CrossValidator",
    # Walk-Forward
    "WalkForwardConfig",
    "WalkForwardCV",
    # Purged K-Fold
    "PurgedKFoldConfig",
    "PurgedKFoldCV",
    # 指标
    "CVMetrics",
    "compute_cv_metrics",
    "compute_sharpe_ratio",
    "compute_max_drawdown",
]
