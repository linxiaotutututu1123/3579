"""Deep Learning Strategy Module - 深度学习策略模块 (军规级 v4.2).

V4PRO Platform Component - Phase 6 B类模型层
V4 SPEC: D6 Phase 6 B类模型开发计划

模块职责:
- 数据层: 序列处理、数据集构建、数据加载
- 模型层: LSTM增强、注意力机制
- 训练层: 训练器、早停、检查点
- 因子层: IC计算、因子评估

Required Scenarios:
- DL.DATA.SEQ.BUILD - 序列构建确定性
- DL.DATA.SEQ.NORMALIZE - 序列标准化
- DL.DATA.DATASET.CREATE - 数据集创建
- DL.MODEL.LSTM.FORWARD - LSTM前向传播
- DL.MODEL.LSTM.ATTENTION - 带注意力的LSTM
- DL.TRAIN.LOOP - 训练循环确定性
- DL.TRAIN.EARLY_STOP - 早停机制
- DL.TRAIN.CHECKPOINT - 检查点保存
- DL.FACTOR.IC.COMPUTE - IC计算(门禁: IC >= 0.05)
- DL.FACTOR.IC.DECAY - IC衰减分析

军规覆盖:
- M7: 确定性处理(回放一致)
- M3: 完整审计日志
- M19: 风险归因追踪
- M26: 测试规范遵守

质量门禁:
- 单元测试覆盖率 >= 95%
- 27场景全部通过
- 模型IC值 >= 0.05
"""

from __future__ import annotations

# 数据层
from src.strategy.dl.data import (
    FinancialDataset,
    FinancialSample,
    NormalizationMethod,
    SequenceConfig,
    SequenceHandler,
    SequenceWindow,
    create_dataset,
)

# 因子层
from src.strategy.dl.factors import (
    FactorMetrics,
    ICCalculator,
    ICConfig,
    ICResult,
)

# 原有组件
from src.strategy.dl.features import build_features, get_feature_dim
from src.strategy.dl.model import TinyMLP

# 模型层
from src.strategy.dl.models import (
    EnhancedLSTM,
    LSTMConfig,
)
from src.strategy.dl.policy import infer_score

# 训练层
from src.strategy.dl.training import (
    EarlyStopping,
    TradingModelTrainer,
    TrainerConfig,
    TrainerMetrics,
)
from src.strategy.dl.weights import (
    clear_model_cache,
    load_model_and_hash,
)


__all__ = [
    # 数据层
    "FinancialDataset",
    "FinancialSample",
    "NormalizationMethod",
    "SequenceConfig",
    "SequenceHandler",
    "SequenceWindow",
    "create_dataset",
    # 模型层
    "EnhancedLSTM",
    "LSTMConfig",
    "TinyMLP",
    # 训练层
    "EarlyStopping",
    "TrainerConfig",
    "TrainerMetrics",
    "TradingModelTrainer",
    # 因子层
    "FactorMetrics",
    "ICCalculator",
    "ICConfig",
    "ICResult",
    # 原有组件
    "build_features",
    "clear_model_cache",
    "get_feature_dim",
    "infer_score",
    "load_model_and_hash",
]
