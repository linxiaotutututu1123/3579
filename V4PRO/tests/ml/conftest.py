"""
ML数据管道测试配置.

提供测试夹具和通用工具。
"""

from __future__ import annotations

from typing import Generator

import pytest

from src.ml.pipeline.base import (
    DataPipeline,
    DataSource,
    PipelineConfig,
    PipelineMetrics,
    PipelineMode,
    ProcessingStage,
)
from src.ml.pipeline.batch import BatchCheckpoint, BatchPipeline, BatchProcessingResult
from src.ml.pipeline.realtime import (
    BufferedItem,
    CircuitBreakerState,
    CircuitState,
    LatencyTracker,
    RealtimePipeline,
)


# ============================================================================
# 基础配置夹具
# ============================================================================


@pytest.fixture
def batch_config() -> PipelineConfig:
    """批量管道配置fixture."""
    return PipelineConfig(
        mode=PipelineMode.BATCH,
        sources=[DataSource.MARKET, DataSource.FUNDAMENTAL],
        batch_size=100,
        buffer_size=1000,
        enable_audit=True,
        enable_knowledge=True,
        enable_deterministic=True,
    )


@pytest.fixture
def realtime_config() -> PipelineConfig:
    """实时管道配置fixture."""
    return PipelineConfig(
        mode=PipelineMode.REALTIME,
        sources=[DataSource.MARKET],
        batch_size=1,
        buffer_size=500,
        enable_audit=True,
        enable_knowledge=True,
    )


@pytest.fixture
def minimal_config() -> PipelineConfig:
    """最小配置fixture."""
    return PipelineConfig(
        mode=PipelineMode.BATCH,
        sources=[DataSource.MARKET],
        batch_size=10,
        buffer_size=100,
        enable_audit=False,
        enable_knowledge=False,
    )


# ============================================================================
# 管道实例夹具
# ============================================================================


@pytest.fixture
def batch_pipeline(batch_config: PipelineConfig) -> BatchPipeline:
    """批量管道实例fixture."""
    return BatchPipeline(batch_config)


@pytest.fixture
def realtime_pipeline(realtime_config: PipelineConfig) -> RealtimePipeline:
    """实时管道实例fixture."""
    return RealtimePipeline(realtime_config)


@pytest.fixture
def deterministic_pipeline(batch_config: PipelineConfig) -> BatchPipeline:
    """确定性批量管道fixture."""
    pipeline = BatchPipeline(batch_config)
    pipeline.set_random_state(42)
    return pipeline


# ============================================================================
# 数据夹具
# ============================================================================


@pytest.fixture
def sample_data() -> list[dict]:
    """示例数据fixture."""
    return [
        {"price": 100.0, "volume": 1000, "symbol": "IF2401"},
        {"price": 101.0, "volume": 1500, "symbol": "IF2401"},
        {"price": 99.5, "volume": 800, "symbol": "IF2401"},
        {"price": 102.0, "volume": 2000, "symbol": "IF2401"},
        {"price": 100.5, "volume": 1200, "symbol": "IF2401"},
    ]


@pytest.fixture
def large_sample_data() -> list[dict]:
    """大量示例数据fixture."""
    return [
        {"price": 100.0 + i * 0.1, "volume": 1000 + i * 10, "index": i}
        for i in range(100)
    ]


# ============================================================================
# 工具类夹具
# ============================================================================


@pytest.fixture
def latency_tracker() -> LatencyTracker:
    """延迟追踪器fixture."""
    return LatencyTracker(max_samples=100, p99_threshold_ms=10.0)


@pytest.fixture
def circuit_breaker_state() -> CircuitBreakerState:
    """熔断器状态fixture."""
    return CircuitBreakerState()


@pytest.fixture
def pipeline_metrics() -> PipelineMetrics:
    """管道指标fixture."""
    return PipelineMetrics()


# ============================================================================
# 辅助函数
# ============================================================================


def create_buffered_item(data: dict, seq_id: int = 1) -> BufferedItem:
    """创建缓冲区数据项."""
    import time

    return BufferedItem(
        data=data,
        timestamp=time.time(),
        correlation_id=f"test-{seq_id}",
        sequence_id=seq_id,
        metadata={"test": True},
    )


def create_checkpoint(
    batch_id: str = "test-batch",
    processed: int = 50,
    total: int = 100,
) -> dict:
    """创建测试检查点."""
    from datetime import datetime

    return BatchCheckpoint(
        batch_id=batch_id,
        processed_count=processed,
        total_count=total,
        last_processed_index=processed - 1,
        random_state=42,
        data_hash="abcd1234",
        timestamp=datetime.now().isoformat(),
        metadata={"test": True},
    ).to_dict()
