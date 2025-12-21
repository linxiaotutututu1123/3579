"""DL Data Layer - 数据处理模块.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计)

V4PRO Scenarios:
- DL.DATA.SEQ.BUILD - 序列构建
- DL.DATA.SEQ.NORMALIZE - 序列标准化
- DL.DATA.DATASET.CREATE - 数据集创建
- DL.DATA.LOADER.BATCH - 批量加载
"""

from __future__ import annotations

from src.strategy.dl.data.dataset import (
    FinancialDataset,
    FinancialSample,
    create_dataset,
)
from src.strategy.dl.data.sequence_handler import (
    NormalizationMethod,
    SequenceConfig,
    SequenceHandler,
    SequenceWindow,
)


__all__ = [
    # 序列处理
    "NormalizationMethod",
    "SequenceConfig",
    "SequenceHandler",
    "SequenceWindow",
    # 数据集
    "FinancialDataset",
    "FinancialSample",
    "create_dataset",
]
