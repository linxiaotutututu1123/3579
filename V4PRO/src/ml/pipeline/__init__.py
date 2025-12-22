"""
ML数据管道模块.

V4PRO Platform Component - Phase 6.1.1 ML数据管道基础框架

组件:
- DataPipeline: 数据管道抽象基类
- BatchPipeline: 批量数据管道 (M3/M7/M33)
- PipelineConfig: 管道配置
- PipelineMetrics: 管道指标
"""

from __future__ import annotations

from src.ml.pipeline.base import (
    DataPipeline,
    DataSource,
    PipelineConfig,
    PipelineMetrics,
    PipelineMode,
    ProcessingStage,
    create_pipeline_config,
    get_mode_description,
    get_source_description,
    get_stage_name,
)
from src.ml.pipeline.batch import (
    BatchCheckpoint,
    BatchPipeline,
    BatchProcessingResult,
    create_batch_pipeline,
    process_in_batches,
)

__all__ = [
    # 基础类
    "DataPipeline",
    "DataSource",
    "PipelineConfig",
    "PipelineMetrics",
    "PipelineMode",
    "ProcessingStage",
    # 批量管道
    "BatchPipeline",
    "BatchCheckpoint",
    "BatchProcessingResult",
    # 便捷函数
    "create_pipeline_config",
    "create_batch_pipeline",
    "process_in_batches",
    "get_mode_description",
    "get_source_description",
    "get_stage_name",
]
