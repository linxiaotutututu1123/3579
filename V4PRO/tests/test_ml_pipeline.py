"""
ML数据管道单元测试 (军规级 v4.0).

V4PRO Platform Component - Phase 6.1.1 ML数据管道测试
V4 SPEC: SS30 数据管道设计, SS31 特征工程流水线

军规覆盖:
- M3: 完整审计日志 - 验证所有操作记录审计轨迹
- M6: 熔断保护机制 - 验证连续失败触发熔断保护
- M7: 确定性处理 - 验证相同输入产生相同输出

测试场景覆盖:
- ML.PIPELINE.REALTIME: 实时流式数据处理
- ML.PIPELINE.BATCH: 批量数据处理
- ML.PIPELINE.BATCH.CHECKPOINT: 检查点恢复
- ML.PIPELINE.BATCH.DETERMINISTIC: 确定性处理
- ML.PIPELINE.CIRCUIT_BREAKER: 熔断保护机制
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Any

import pytest

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
from src.ml.pipeline.realtime import (
    AuditEventType,
    BufferedItem,
    CircuitBreakerState,
    CircuitState,
    LatencyTracker,
    RealtimePipeline,
    create_realtime_pipeline,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def batch_config() -> PipelineConfig:
    """创建批量管道配置."""
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
    """创建实时管道配置."""
    return PipelineConfig(
        mode=PipelineMode.REALTIME,
        sources=[DataSource.MARKET],
        buffer_size=1000,
        enable_audit=True,
        enable_knowledge=True,
    )


@pytest.fixture
def sample_data() -> list[dict[str, Any]]:
    """生成测试用数据."""
    random.seed(42)
    return [
        {
            "price": 5000.0 + random.uniform(-100, 100),
            "volume": random.randint(100, 1000),
            "timestamp": time.time() + i,
        }
        for i in range(50)
    ]


@pytest.fixture
def batch_pipeline(batch_config: PipelineConfig) -> BatchPipeline:
    """创建批量管道实例."""
    return BatchPipeline(batch_config)


@pytest.fixture
def realtime_pipeline(realtime_config: PipelineConfig) -> RealtimePipeline:
    """创建实时管道实例."""
    return RealtimePipeline(realtime_config)


# ============================================================================
# Enum Tests
# ============================================================================


@pytest.mark.unit
class TestPipelineMode:
    """PipelineMode枚举测试."""

    def test_realtime_mode_value(self) -> None:
        """测试实时模式枚举值."""
        assert PipelineMode.REALTIME.value == "REALTIME"

    def test_batch_mode_value(self) -> None:
        """测试批量模式枚举值."""
        assert PipelineMode.BATCH.value == "BATCH"

    def test_hybrid_mode_value(self) -> None:
        """测试混合模式枚举值."""
        assert PipelineMode.HYBRID.value == "HYBRID"

    def test_all_modes_exist(self) -> None:
        """测试所有模式存在."""
        modes = list(PipelineMode)
        assert len(modes) == 3
        assert PipelineMode.REALTIME in modes
        assert PipelineMode.BATCH in modes
        assert PipelineMode.HYBRID in modes


@pytest.mark.unit
class TestDataSource:
    """DataSource枚举测试."""

    def test_market_source_value(self) -> None:
        """测试市场数据源枚举值."""
        assert DataSource.MARKET.value == "MARKET"

    def test_fundamental_source_value(self) -> None:
        """测试基本面数据源枚举值."""
        assert DataSource.FUNDAMENTAL.value == "FUNDAMENTAL"

    def test_sentiment_source_value(self) -> None:
        """测试情绪数据源枚举值."""
        assert DataSource.SENTIMENT.value == "SENTIMENT"

    def test_alternative_source_value(self) -> None:
        """测试另类数据源枚举值."""
        assert DataSource.ALTERNATIVE.value == "ALTERNATIVE"

    def test_all_sources_exist(self) -> None:
        """测试所有数据源存在."""
        sources = list(DataSource)
        assert len(sources) == 4


@pytest.mark.unit
class TestProcessingStage:
    """ProcessingStage枚举测试."""

    def test_ingest_stage_value(self) -> None:
        """测试摄取阶段枚举值."""
        assert ProcessingStage.INGEST.value == "INGEST"

    def test_validate_stage_value(self) -> None:
        """测试验证阶段枚举值."""
        assert ProcessingStage.VALIDATE.value == "VALIDATE"

    def test_transform_stage_value(self) -> None:
        """测试转换阶段枚举值."""
        assert ProcessingStage.TRANSFORM.value == "TRANSFORM"

    def test_feature_stage_value(self) -> None:
        """测试特征阶段枚举值."""
        assert ProcessingStage.FEATURE.value == "FEATURE"

    def test_output_stage_value(self) -> None:
        """测试输出阶段枚举值."""
        assert ProcessingStage.OUTPUT.value == "OUTPUT"

    def test_all_stages_exist(self) -> None:
        """测试所有阶段存在."""
        stages = list(ProcessingStage)
        assert len(stages) == 5


@pytest.mark.unit
class TestCircuitState:
    """CircuitState枚举测试 (M6)."""

    def test_closed_state_value(self) -> None:
        """测试关闭状态枚举值."""
        assert CircuitState.CLOSED.value == "CLOSED"

    def test_open_state_value(self) -> None:
        """测试打开状态枚举值."""
        assert CircuitState.OPEN.value == "OPEN"

    def test_half_open_state_value(self) -> None:
        """测试半开状态枚举值."""
        assert CircuitState.HALF_OPEN.value == "HALF_OPEN"


@pytest.mark.unit
class TestAuditEventType:
    """AuditEventType枚举测试 (M3)."""

    def test_ingest_event_value(self) -> None:
        """测试摄取事件枚举值."""
        assert AuditEventType.INGEST.value == "INGEST"

    def test_process_event_value(self) -> None:
        """测试处理事件枚举值."""
        assert AuditEventType.PROCESS.value == "PROCESS"

    def test_circuit_open_event_value(self) -> None:
        """测试熔断打开事件枚举值."""
        assert AuditEventType.CIRCUIT_OPEN.value == "CIRCUIT_OPEN"

    def test_circuit_close_event_value(self) -> None:
        """测试熔断关闭事件枚举值."""
        assert AuditEventType.CIRCUIT_CLOSE.value == "CIRCUIT_CLOSE"

    def test_error_event_value(self) -> None:
        """测试错误事件枚举值."""
        assert AuditEventType.ERROR.value == "ERROR"


# ============================================================================
# Configuration Tests
# ============================================================================


@pytest.mark.unit
class TestPipelineConfig:
    """PipelineConfig配置测试."""

    def test_default_batch_size(self) -> None:
        """测试默认批量大小."""
        config = PipelineConfig(mode=PipelineMode.BATCH, sources=[DataSource.MARKET])
        assert config.batch_size == 1000

    def test_default_buffer_size(self) -> None:
        """测试默认缓冲区大小."""
        config = PipelineConfig(mode=PipelineMode.BATCH, sources=[DataSource.MARKET])
        assert config.buffer_size == 10000

    def test_default_audit_enabled(self) -> None:
        """测试默认启用审计 (M3)."""
        config = PipelineConfig(mode=PipelineMode.BATCH, sources=[DataSource.MARKET])
        assert config.enable_audit is True

    def test_default_knowledge_enabled(self) -> None:
        """测试默认启用知识沉淀 (M33)."""
        config = PipelineConfig(mode=PipelineMode.BATCH, sources=[DataSource.MARKET])
        assert config.enable_knowledge is True

    def test_default_deterministic_enabled(self) -> None:
        """测试默认启用确定性处理 (M7)."""
        config = PipelineConfig(mode=PipelineMode.BATCH, sources=[DataSource.MARKET])
        assert config.enable_deterministic is True

    def test_custom_batch_size(self) -> None:
        """测试自定义批量大小."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET],
            batch_size=500,
        )
        assert config.batch_size == 500

    def test_invalid_batch_size_raises(self) -> None:
        """测试无效批量大小抛出异常."""
        with pytest.raises(ValueError, match="batch_size必须为正数"):
            PipelineConfig(
                mode=PipelineMode.BATCH,
                sources=[DataSource.MARKET],
                batch_size=0,
            )

    def test_invalid_buffer_size_raises(self) -> None:
        """测试无效缓冲区大小抛出异常."""
        with pytest.raises(ValueError, match="buffer_size必须为正数"):
            PipelineConfig(
                mode=PipelineMode.BATCH,
                sources=[DataSource.MARKET],
                buffer_size=0,
            )

    def test_buffer_size_less_than_batch_size_raises(self) -> None:
        """测试缓冲区小于批量大小抛出异常."""
        with pytest.raises(ValueError, match="buffer_size.*必须大于等于batch_size"):
            PipelineConfig(
                mode=PipelineMode.BATCH,
                sources=[DataSource.MARKET],
                batch_size=1000,
                buffer_size=500,
            )

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET, DataSource.FUNDAMENTAL],
            batch_size=500,
        )
        d = config.to_dict()

        assert d["mode"] == "BATCH"
        assert d["sources"] == ["MARKET", "FUNDAMENTAL"]
        assert d["batch_size"] == 500

    def test_validate_with_sources(self) -> None:
        """测试验证有数据源."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET],
        )
        assert config.validate() is True

    def test_validate_without_sources(self) -> None:
        """测试验证无数据源."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[],
        )
        assert config.validate() is False

    def test_multiple_sources(self) -> None:
        """测试多数据源配置."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET, DataSource.FUNDAMENTAL, DataSource.SENTIMENT],
        )
        assert len(config.sources) == 3


@pytest.mark.unit
class TestCreatePipelineConfig:
    """create_pipeline_config便捷函数测试."""

    def test_default_creation(self) -> None:
        """测试默认创建."""
        config = create_pipeline_config()
        assert config.mode == PipelineMode.BATCH
        assert DataSource.MARKET in config.sources

    def test_realtime_mode(self) -> None:
        """测试实时模式创建."""
        config = create_pipeline_config(mode=PipelineMode.REALTIME)
        assert config.mode == PipelineMode.REALTIME

    def test_custom_sources(self) -> None:
        """测试自定义数据源."""
        config = create_pipeline_config(
            sources=[DataSource.FUNDAMENTAL, DataSource.ALTERNATIVE]
        )
        assert DataSource.FUNDAMENTAL in config.sources
        assert DataSource.ALTERNATIVE in config.sources


# ============================================================================
# PipelineMetrics Tests
# ============================================================================


@pytest.mark.unit
class TestPipelineMetrics:
    """PipelineMetrics指标测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        metrics = PipelineMetrics()
        assert metrics.records_processed == 0
        assert metrics.records_failed == 0
        assert metrics.latency_ms == 0.0
        assert metrics.throughput_per_sec == 0.0

    def test_success_rate_with_no_records(self) -> None:
        """测试无记录时成功率."""
        metrics = PipelineMetrics()
        assert metrics.success_rate == 0.0

    def test_success_rate_calculation(self) -> None:
        """测试成功率计算."""
        metrics = PipelineMetrics()
        metrics.records_processed = 80
        metrics.records_failed = 20
        assert metrics.success_rate == 0.8

    def test_total_records(self) -> None:
        """测试总记录数."""
        metrics = PipelineMetrics()
        metrics.records_processed = 100
        metrics.records_failed = 10
        assert metrics.total_records == 110

    def test_duration_ms_with_times(self) -> None:
        """测试处理时长计算."""
        metrics = PipelineMetrics()
        metrics.start_time = "2025-12-22T10:00:00"
        metrics.end_time = "2025-12-22T10:00:01"
        assert metrics.duration_ms == 1000.0

    def test_duration_ms_without_times(self) -> None:
        """测试无时间时处理时长."""
        metrics = PipelineMetrics()
        assert metrics.duration_ms == 0.0

    def test_record_stage_metric(self) -> None:
        """测试记录阶段指标."""
        metrics = PipelineMetrics()
        metrics.record_stage_metric(ProcessingStage.INGEST, "duration_ms", 50.0)

        assert ProcessingStage.INGEST in metrics.stage_metrics
        assert metrics.stage_metrics[ProcessingStage.INGEST]["duration_ms"] == 50.0

    def test_record_error(self) -> None:
        """测试记录错误."""
        metrics = PipelineMetrics()
        metrics.record_error("ValidationError")
        metrics.record_error("ValidationError")
        metrics.record_error("TimeoutError")

        assert metrics.error_counts["ValidationError"] == 2
        assert metrics.error_counts["TimeoutError"] == 1
        assert metrics.records_failed == 3

    def test_add_audit_entry(self) -> None:
        """测试添加审计日志条目 (M3)."""
        metrics = PipelineMetrics()
        metrics.add_audit_entry({"action": "test_action", "result": "success"})

        assert len(metrics.audit_log) == 1
        assert "timestamp" in metrics.audit_log[0]
        assert metrics.audit_log[0]["action"] == "test_action"

    def test_add_knowledge_entry(self) -> None:
        """测试添加知识条目 (M33)."""
        metrics = PipelineMetrics()
        metrics.add_knowledge_entry({"category": "test", "content": "test content"})

        assert len(metrics.knowledge_entries) == 1
        assert "timestamp" in metrics.knowledge_entries[0]

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        metrics = PipelineMetrics()
        metrics.records_processed = 100
        metrics.latency_ms = 5.5

        d = metrics.to_dict()
        assert d["records_processed"] == 100
        assert d["latency_ms"] == 5.5
        assert "success_rate" in d

    def test_to_audit_dict(self) -> None:
        """测试转换为审计字典 (M3)."""
        metrics = PipelineMetrics()
        metrics.records_processed = 100
        metrics.add_audit_entry({"action": "test"})

        d = metrics.to_audit_dict()
        assert "audit_log" in d
        assert len(d["audit_log"]) == 1

    def test_reset(self) -> None:
        """测试重置指标."""
        metrics = PipelineMetrics()
        metrics.records_processed = 100
        metrics.add_audit_entry({"action": "test"})

        metrics.reset()

        assert metrics.records_processed == 0
        assert len(metrics.audit_log) == 0


# ============================================================================
# LatencyTracker Tests
# ============================================================================


@pytest.mark.unit
class TestLatencyTracker:
    """LatencyTracker延迟追踪器测试."""

    def test_add_sample(self) -> None:
        """测试添加延迟样本."""
        tracker = LatencyTracker()
        tracker.add_sample(5.0)
        tracker.add_sample(10.0)
        tracker.add_sample(15.0)

        assert len(tracker.samples) == 3

    def test_p99_calculation(self) -> None:
        """测试P99延迟计算."""
        tracker = LatencyTracker()
        for i in range(100):
            tracker.add_sample(float(i))

        p99 = tracker.p99
        assert 98.0 <= p99 <= 99.0

    def test_avg_calculation(self) -> None:
        """测试平均延迟计算."""
        tracker = LatencyTracker()
        tracker.add_sample(10.0)
        tracker.add_sample(20.0)
        tracker.add_sample(30.0)

        assert tracker.avg == 20.0

    def test_max_calculation(self) -> None:
        """测试最大延迟计算."""
        tracker = LatencyTracker()
        tracker.add_sample(10.0)
        tracker.add_sample(50.0)
        tracker.add_sample(30.0)

        assert tracker.max == 50.0

    def test_min_calculation(self) -> None:
        """测试最小延迟计算."""
        tracker = LatencyTracker()
        tracker.add_sample(10.0)
        tracker.add_sample(5.0)
        tracker.add_sample(30.0)

        assert tracker.min == 5.0

    def test_is_violation_false(self) -> None:
        """测试无延迟违规."""
        tracker = LatencyTracker(p99_threshold_ms=10.0)
        for _ in range(100):
            tracker.add_sample(5.0)

        assert tracker.is_violation() is False

    def test_is_violation_true(self) -> None:
        """测试有延迟违规."""
        tracker = LatencyTracker(p99_threshold_ms=10.0)
        for _ in range(100):
            tracker.add_sample(15.0)

        assert tracker.is_violation() is True

    def test_reset(self) -> None:
        """测试重置追踪器."""
        tracker = LatencyTracker()
        tracker.add_sample(10.0)
        tracker.reset()

        assert len(tracker.samples) == 0

    def test_max_samples_limit(self) -> None:
        """测试最大样本数限制."""
        tracker = LatencyTracker(max_samples=10)
        for i in range(20):
            tracker.add_sample(float(i))

        assert len(tracker.samples) == 10

    def test_empty_tracker(self) -> None:
        """测试空追踪器."""
        tracker = LatencyTracker()
        assert tracker.p99 == 0.0
        assert tracker.avg == 0.0
        assert tracker.max == 0.0
        assert tracker.min == 0.0


# ============================================================================
# CircuitBreakerState Tests
# ============================================================================


@pytest.mark.unit
class TestCircuitBreakerState:
    """CircuitBreakerState熔断器状态测试 (M6)."""

    def test_default_state(self) -> None:
        """测试默认状态."""
        state = CircuitBreakerState()
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0

    def test_reset(self) -> None:
        """测试重置状态."""
        state = CircuitBreakerState()
        state.state = CircuitState.OPEN
        state.failure_count = 10
        state.open_time = time.time()

        state.reset()

        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0
        assert state.open_time == 0.0


# ============================================================================
# BufferedItem Tests
# ============================================================================


@pytest.mark.unit
class TestBufferedItem:
    """BufferedItem缓冲区数据项测试."""

    def test_creation(self) -> None:
        """测试创建缓冲区项."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test-001",
            sequence_id=1,
        )

        assert item.data == {"price": 100.0}
        assert item.correlation_id == "test-001"
        assert item.sequence_id == 1

    def test_metadata(self) -> None:
        """测试元数据."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test-001",
            sequence_id=1,
            metadata={"source": "test"},
        )

        assert item.metadata["source"] == "test"


# ============================================================================
# BatchCheckpoint Tests
# ============================================================================


@pytest.mark.unit
class TestBatchCheckpoint:
    """BatchCheckpoint检查点测试 (M7)."""

    def test_creation(self) -> None:
        """测试创建检查点."""
        checkpoint = BatchCheckpoint(
            batch_id="batch_001",
            processed_count=50,
            total_count=100,
            last_processed_index=49,
            random_state=42,
            data_hash="abc123",
            timestamp=datetime.now().isoformat(),
        )

        assert checkpoint.batch_id == "batch_001"
        assert checkpoint.processed_count == 50
        assert checkpoint.random_state == 42

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        checkpoint = BatchCheckpoint(
            batch_id="batch_001",
            processed_count=50,
            total_count=100,
            last_processed_index=49,
            random_state=42,
            data_hash="abc123",
            timestamp="2025-12-22T10:00:00",
        )

        d = checkpoint.to_dict()
        assert d["batch_id"] == "batch_001"
        assert d["random_state"] == 42

    def test_from_dict(self) -> None:
        """测试从字典创建."""
        data = {
            "batch_id": "batch_001",
            "processed_count": 50,
            "total_count": 100,
            "last_processed_index": 49,
            "random_state": 42,
            "data_hash": "abc123",
            "timestamp": "2025-12-22T10:00:00",
        }

        checkpoint = BatchCheckpoint.from_dict(data)
        assert checkpoint.batch_id == "batch_001"
        assert checkpoint.random_state == 42


# ============================================================================
# BatchProcessingResult Tests
# ============================================================================


@pytest.mark.unit
class TestBatchProcessingResult:
    """BatchProcessingResult批量处理结果测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        result = BatchProcessingResult()
        assert result.success_count == 0
        assert result.failed_count == 0

    def test_success_count(self) -> None:
        """测试成功数量."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3, 4, 5]
        assert result.success_count == 5

    def test_failed_count(self) -> None:
        """测试失败数量."""
        result = BatchProcessingResult()
        result.failed_items = [(0, "item", "error")]
        assert result.failed_count == 1

    def test_total_count(self) -> None:
        """测试总数量."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3]
        result.failed_items = [(0, "item", "error")]
        assert result.total_count == 4

    def test_success_rate(self) -> None:
        """测试成功率."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3, 4]
        result.failed_items = [(0, "item", "error")]
        assert result.success_rate == 0.8

    def test_success_rate_empty(self) -> None:
        """测试空结果成功率."""
        result = BatchProcessingResult()
        assert result.success_rate == 0.0

    def test_to_dict(self) -> None:
        """测试转换为字典."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3]
        result.processing_time_ms = 100.5

        d = result.to_dict()
        assert d["success_count"] == 3
        assert d["processing_time_ms"] == 100.5


# ============================================================================
# RealtimePipeline Tests
# ============================================================================


@pytest.mark.unit
class TestRealtimePipeline:
    """RealtimePipeline实时管道测试."""

    def test_creation(self, realtime_config: PipelineConfig) -> None:
        """测试创建实时管道."""
        pipeline = RealtimePipeline(realtime_config)
        assert pipeline.config.mode == PipelineMode.REALTIME
        assert pipeline.circuit_state == CircuitState.CLOSED

    def test_wrong_mode_raises(self, batch_config: PipelineConfig) -> None:
        """测试错误模式抛出异常."""
        with pytest.raises(ValueError, match="RealtimePipeline仅支持REALTIME模式"):
            RealtimePipeline(batch_config)

    def test_ingest_data(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试数据摄取."""
        realtime_pipeline.start()
        item = realtime_pipeline.ingest({"price": 100.0})

        assert isinstance(item, BufferedItem)
        assert item.data == {"price": 100.0}
        assert item.sequence_id == 1

    def test_ingest_increments_sequence(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """测试摄取递增序列号."""
        realtime_pipeline.start()

        item1 = realtime_pipeline.ingest({"price": 100.0})
        item2 = realtime_pipeline.ingest({"price": 101.0})

        assert item1.sequence_id == 1
        assert item2.sequence_id == 2

    def test_validate_none_data(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试验证空数据."""
        assert realtime_pipeline.validate(None) is False

    def test_validate_valid_data(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试验证有效数据."""
        assert realtime_pipeline.validate({"price": 100.0}) is True

    def test_validate_buffered_item(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试验证BufferedItem."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test-001",
            sequence_id=1,
        )
        assert realtime_pipeline.validate(item) is True

    def test_validate_buffered_item_none_data(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """测试验证空数据的BufferedItem."""
        item = BufferedItem(
            data=None,
            timestamp=time.time(),
            correlation_id="test-001",
            sequence_id=1,
        )
        assert realtime_pipeline.validate(item) is False

    def test_transform_adds_metadata(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """测试转换添加元数据."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test-001",
            sequence_id=1,
            metadata={},
        )

        result = realtime_pipeline.transform(item)
        assert "transform_time" in result.metadata

    def test_buffer_size(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试缓冲区大小."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})
        realtime_pipeline.ingest({"price": 101.0})

        assert realtime_pipeline.get_buffer_size() == 2

    def test_buffer_capacity(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试缓冲区容量."""
        assert realtime_pipeline.get_buffer_capacity() == 1000

    def test_clear_buffer(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试清空缓冲区."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})
        realtime_pipeline.ingest({"price": 101.0})

        count = realtime_pipeline.clear_buffer()
        assert count == 2
        assert realtime_pipeline.get_buffer_size() == 0

    def test_get_status(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试获取状态."""
        realtime_pipeline.start()
        status = realtime_pipeline.get_status()

        assert status["running"] is True
        assert status["mode"] == "REALTIME"
        assert "buffer" in status
        assert "circuit_breaker" in status
        assert "latency" in status

    def test_get_latency_stats(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试获取延迟统计."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})

        stats = realtime_pipeline.get_latency_stats()
        assert "p99_ms" in stats
        assert "avg_ms" in stats
        assert "is_compliant" in stats

    def test_reset(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试重置管道."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})

        realtime_pipeline.reset()

        assert realtime_pipeline.get_buffer_size() == 0
        assert realtime_pipeline.circuit_state == CircuitState.CLOSED
        assert realtime_pipeline.processed_count == 0


@pytest.mark.unit
class TestRealtimePipelineCircuitBreaker:
    """RealtimePipeline熔断器测试 (M6)."""

    def test_circuit_initially_closed(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """测试熔断器初始关闭."""
        assert realtime_pipeline.circuit_state == CircuitState.CLOSED
        assert realtime_pipeline.is_circuit_open is False

    def test_reset_circuit_breaker(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """测试手动重置熔断器."""
        realtime_pipeline.reset_circuit_breaker()
        assert realtime_pipeline.circuit_state == CircuitState.CLOSED

    def test_circuit_open_callback(self) -> None:
        """测试熔断打开回调."""
        callback_called = []

        def on_circuit_open() -> None:
            callback_called.append(True)

        config = PipelineConfig(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.MARKET],
        )
        pipeline = RealtimePipeline(config, on_circuit_open=on_circuit_open)
        pipeline.start()

        # 手动触发熔断
        for _ in range(RealtimePipeline.CIRCUIT_BREAKER_THRESHOLD + 1):
            pipeline._record_failure("test_failure")

        assert len(callback_called) > 0

    def test_circuit_close_callback(self) -> None:
        """测试熔断关闭回调."""
        callback_called = []

        def on_circuit_close() -> None:
            callback_called.append(True)

        config = PipelineConfig(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.MARKET],
        )
        pipeline = RealtimePipeline(config, on_circuit_close=on_circuit_close)
        pipeline.start()

        # 触发熔断后恢复
        for _ in range(RealtimePipeline.CIRCUIT_BREAKER_THRESHOLD + 1):
            pipeline._record_failure("test_failure")

        # 手动设置半开状态并记录成功
        pipeline._circuit_state.state = CircuitState.HALF_OPEN
        pipeline._record_success()

        assert len(callback_called) > 0

    def test_ingest_blocked_when_circuit_open(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """测试熔断打开时摄取被阻塞."""
        realtime_pipeline.start()

        # 手动打开熔断器
        realtime_pipeline._circuit_state.state = CircuitState.OPEN
        realtime_pipeline._circuit_state.open_time = time.time()

        with pytest.raises(RuntimeError, match="熔断器已打开"):
            realtime_pipeline.ingest({"price": 100.0})


@pytest.mark.unit
class TestRealtimePipelineAudit:
    """RealtimePipeline审计日志测试 (M3)."""

    def test_audit_log_on_ingest(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试摄取时记录审计日志."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})

        audit_log = realtime_pipeline.get_audit_log()
        assert len(audit_log) > 0

        # 检查是否有INGEST事件
        ingest_events = [
            e for e in audit_log if e.get("event_type") == AuditEventType.INGEST.value
        ]
        assert len(ingest_events) > 0

    def test_audit_log_on_start(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试启动时记录审计日志."""
        realtime_pipeline.start()

        audit_log = realtime_pipeline.get_audit_log()
        start_events = [
            e
            for e in audit_log
            if e.get("event_type") == AuditEventType.PROCESS.value
            and e.get("action") == "pipeline_start"
        ]
        assert len(start_events) > 0

    def test_audit_log_on_stop(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试停止时记录审计日志."""
        realtime_pipeline.start()
        realtime_pipeline.stop()

        audit_log = realtime_pipeline.get_audit_log()
        stop_events = [
            e
            for e in audit_log
            if e.get("event_type") == AuditEventType.PROCESS.value
            and e.get("action") == "pipeline_stop"
        ]
        assert len(stop_events) > 0

    def test_clear_audit_log(self, realtime_pipeline: RealtimePipeline) -> None:
        """测试清空审计日志."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})

        realtime_pipeline.clear_audit_log()
        assert len(realtime_pipeline.get_audit_log()) == 0

    def test_audit_disabled(self) -> None:
        """测试禁用审计."""
        config = PipelineConfig(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.MARKET],
            enable_audit=False,
        )
        pipeline = RealtimePipeline(config)
        pipeline.start()
        pipeline.ingest({"price": 100.0})

        # 审计日志应该为空
        assert len(pipeline.get_audit_log()) == 0


# ============================================================================
# BatchPipeline Tests
# ============================================================================


@pytest.mark.unit
class TestBatchPipeline:
    """BatchPipeline批量管道测试."""

    def test_creation(self, batch_config: PipelineConfig) -> None:
        """测试创建批量管道."""
        pipeline = BatchPipeline(batch_config)
        assert pipeline.config.mode == PipelineMode.BATCH

    def test_wrong_mode_raises(self, realtime_config: PipelineConfig) -> None:
        """测试错误模式抛出异常."""
        with pytest.raises(ValueError, match="BatchPipeline仅支持BATCH模式"):
            BatchPipeline(realtime_config)

    def test_ingest_list(self, batch_pipeline: BatchPipeline) -> None:
        """测试摄取列表数据."""
        data = [1, 2, 3, 4, 5]
        result = batch_pipeline.ingest(data)
        assert result == data

    def test_ingest_iterator(self, batch_pipeline: BatchPipeline) -> None:
        """测试摄取迭代器数据."""
        data = iter([1, 2, 3])
        result = batch_pipeline.ingest(data)
        assert result == [1, 2, 3]

    def test_ingest_single_item(self, batch_pipeline: BatchPipeline) -> None:
        """测试摄取单个数据项."""
        result = batch_pipeline.ingest(42)
        assert result == [42]

    def test_validate_none(self, batch_pipeline: BatchPipeline) -> None:
        """测试验证空数据."""
        assert batch_pipeline.validate(None) is False

    def test_validate_empty_list(self, batch_pipeline: BatchPipeline) -> None:
        """测试验证空列表."""
        assert batch_pipeline.validate([]) is False

    def test_validate_valid_list(self, batch_pipeline: BatchPipeline) -> None:
        """测试验证有效列表."""
        assert batch_pipeline.validate([1, 2, 3]) is True

    def test_transform_preserves_data(self, batch_pipeline: BatchPipeline) -> None:
        """测试转换保持数据不变."""
        data = [1, 2, 3]
        result = batch_pipeline.transform(data)
        assert result == data

    def test_process_batch(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试批量处理."""
        results = batch_pipeline.process_batch(sample_data)
        assert len(results) == len(sample_data)

    def test_process_batch_with_processor(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试带处理器的批量处理."""
        batch_pipeline.set_item_processor(lambda x: x * 2)
        results = batch_pipeline.process_batch([1, 2, 3, 4, 5])
        assert results == [2, 4, 6, 8, 10]

    def test_get_progress(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试获取进度."""
        batch_pipeline.process_batch(sample_data)
        progress = batch_pipeline.get_progress()
        assert progress == 1.0

    def test_get_progress_empty(self, batch_pipeline: BatchPipeline) -> None:
        """测试空数据进度."""
        assert batch_pipeline.get_progress() == 0.0

    def test_get_batch_results(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试获取批次结果."""
        batch_pipeline.process_batch(sample_data)
        results = batch_pipeline.get_batch_results()
        assert len(results) == 1

    def test_get_last_batch_result(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试获取最后批次结果."""
        batch_pipeline.process_batch(sample_data)
        result = batch_pipeline.get_last_batch_result()

        assert result is not None
        assert result.success_count == len(sample_data)

    def test_get_last_batch_result_empty(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试空时获取最后批次结果."""
        assert batch_pipeline.get_last_batch_result() is None

    def test_reset(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试重置管道."""
        batch_pipeline.process_batch(sample_data)
        batch_pipeline.reset()

        assert batch_pipeline.processed_count == 0
        assert batch_pipeline.total_count == 0
        assert batch_pipeline.get_progress() == 0.0

    def test_process_validates_data(self, batch_pipeline: BatchPipeline) -> None:
        """测试完整处理验证数据."""
        with pytest.raises(ValueError, match="数据验证失败"):
            batch_pipeline.process([])


@pytest.mark.unit
class TestBatchPipelineCheckpoint:
    """BatchPipeline检查点测试 (M7)."""

    def test_save_checkpoint(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试保存检查点."""
        batch_pipeline.process_batch(sample_data)
        checkpoint = batch_pipeline.save_checkpoint()

        assert "batch_id" in checkpoint
        assert "processed_count" in checkpoint
        assert checkpoint["processed_count"] == len(sample_data)

    def test_load_checkpoint(self, batch_pipeline: BatchPipeline) -> None:
        """测试加载检查点."""
        checkpoint = {
            "batch_id": "test_batch",
            "processed_count": 50,
            "total_count": 100,
            "last_processed_index": 49,
            "random_state": 42,
            "data_hash": "abc123",
            "timestamp": datetime.now().isoformat(),
        }

        batch_pipeline.load_checkpoint(checkpoint)

        assert batch_pipeline.current_batch_id == "test_batch"
        assert batch_pipeline.processed_count == 50
        assert batch_pipeline.random_state == 42

    def test_load_checkpoint_empty_raises(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试加载空检查点抛出异常."""
        with pytest.raises(ValueError, match="检查点数据为空"):
            batch_pipeline.load_checkpoint({})

    def test_load_checkpoint_missing_field_raises(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试加载缺少字段的检查点抛出异常."""
        with pytest.raises(ValueError, match="检查点缺少必要字段"):
            batch_pipeline.load_checkpoint({"batch_id": "test"})

    def test_get_checkpoint_info(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试获取检查点信息."""
        batch_pipeline.process_batch(sample_data)
        info = batch_pipeline.get_checkpoint_info()

        assert info["has_checkpoint"] is True
        assert info["progress"] == 1.0


@pytest.mark.unit
class TestBatchPipelineDeterministic:
    """BatchPipeline确定性处理测试 (M7)."""

    def test_set_random_state(self, batch_pipeline: BatchPipeline) -> None:
        """测试设置随机种子."""
        batch_pipeline.set_random_state(42)
        assert batch_pipeline.random_state == 42

    def test_deterministic_processing(self) -> None:
        """测试确定性处理 (M7)."""
        data = list(range(100))

        # 第一次处理
        pipeline1 = create_batch_pipeline(random_seed=42)
        pipeline1.set_item_processor(lambda x: x + random.random())
        results1 = pipeline1.process_batch(data.copy())

        # 第二次处理 (相同种子)
        pipeline2 = create_batch_pipeline(random_seed=42)
        pipeline2.set_item_processor(lambda x: x + random.random())
        results2 = pipeline2.process_batch(data.copy())

        # 验证结果相同 (M7)
        assert results1 == results2

    def test_data_hash_consistency(self, batch_pipeline: BatchPipeline) -> None:
        """测试数据哈希一致性 (M7)."""
        data = [{"a": 1}, {"b": 2}]

        hash1 = batch_pipeline._compute_data_hash(data)
        hash2 = batch_pipeline._compute_data_hash(data)

        assert hash1 == hash2


@pytest.mark.unit
class TestBatchPipelineAudit:
    """BatchPipeline审计日志测试 (M3)."""

    def test_audit_on_batch_start(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试批次开始时记录审计日志."""
        batch_pipeline.process_batch(sample_data)

        metrics = batch_pipeline.get_metrics()
        start_entries = [
            e for e in metrics.audit_log if e.get("action") == "batch_start"
        ]
        assert len(start_entries) > 0

    def test_audit_on_batch_complete(
        self, batch_pipeline: BatchPipeline, sample_data: list[dict[str, Any]]
    ) -> None:
        """测试批次完成时记录审计日志."""
        batch_pipeline.process_batch(sample_data)

        metrics = batch_pipeline.get_metrics()
        complete_entries = [
            e for e in metrics.audit_log if e.get("action") == "batch_complete"
        ]
        assert len(complete_entries) > 0

    def test_audit_on_set_random_state(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试设置随机种子时记录审计日志."""
        batch_pipeline.set_random_state(42)

        metrics = batch_pipeline.get_metrics()
        seed_entries = [
            e for e in metrics.audit_log if e.get("action") == "set_random_state"
        ]
        assert len(seed_entries) > 0
        assert seed_entries[0]["seed"] == 42
        assert seed_entries[0]["purpose"] == "M7_deterministic_processing"


# ============================================================================
# Factory Function Tests
# ============================================================================


@pytest.mark.unit
class TestCreateRealtimePipeline:
    """create_realtime_pipeline便捷函数测试."""

    def test_default_creation(self) -> None:
        """测试默认创建."""
        pipeline = create_realtime_pipeline()
        assert isinstance(pipeline, RealtimePipeline)
        assert pipeline.config.mode == PipelineMode.REALTIME

    def test_custom_buffer_size(self) -> None:
        """测试自定义缓冲区大小."""
        pipeline = create_realtime_pipeline(buffer_size=5000)
        assert pipeline.get_buffer_capacity() == 5000

    def test_with_callbacks(self) -> None:
        """测试带回调函数."""
        open_called = []
        close_called = []

        pipeline = create_realtime_pipeline(
            on_circuit_open=lambda: open_called.append(True),
            on_circuit_close=lambda: close_called.append(True),
        )

        assert pipeline is not None


@pytest.mark.unit
class TestCreateBatchPipeline:
    """create_batch_pipeline便捷函数测试."""

    def test_default_creation(self) -> None:
        """测试默认创建."""
        pipeline = create_batch_pipeline()
        assert isinstance(pipeline, BatchPipeline)
        assert pipeline.config.mode == PipelineMode.BATCH

    def test_custom_batch_size(self) -> None:
        """测试自定义批量大小."""
        pipeline = create_batch_pipeline(batch_size=5000)
        assert pipeline.config.batch_size == 5000

    def test_with_random_seed(self) -> None:
        """测试带随机种子."""
        pipeline = create_batch_pipeline(random_seed=42)
        assert pipeline.random_state == 42


@pytest.mark.unit
class TestProcessInBatches:
    """process_in_batches便捷函数测试."""

    def test_basic_processing(self) -> None:
        """测试基本处理."""
        data = [1, 2, 3, 4, 5]
        results = process_in_batches(data)
        assert results == data

    def test_with_processor(self) -> None:
        """测试带处理器."""
        data = [1, 2, 3, 4, 5]
        results = process_in_batches(data, processor=lambda x: x * 2)
        assert results == [2, 4, 6, 8, 10]

    def test_with_random_seed(self) -> None:
        """测试带随机种子 (M7)."""
        data = list(range(10))

        results1 = process_in_batches(
            data.copy(),
            processor=lambda x: x + random.random(),
            random_seed=42,
        )
        results2 = process_in_batches(
            data.copy(),
            processor=lambda x: x + random.random(),
            random_seed=42,
        )

        assert results1 == results2


# ============================================================================
# Helper Function Tests
# ============================================================================


@pytest.mark.unit
class TestHelperFunctions:
    """辅助函数测试."""

    def test_get_stage_name(self) -> None:
        """测试获取阶段名称."""
        assert get_stage_name(ProcessingStage.INGEST) == "数据摄取"
        assert get_stage_name(ProcessingStage.VALIDATE) == "数据验证"
        assert get_stage_name(ProcessingStage.TRANSFORM) == "数据转换"
        assert get_stage_name(ProcessingStage.FEATURE) == "特征工程"
        assert get_stage_name(ProcessingStage.OUTPUT) == "输出阶段"

    def test_get_mode_description(self) -> None:
        """测试获取模式描述."""
        realtime_desc = get_mode_description(PipelineMode.REALTIME)
        batch_desc = get_mode_description(PipelineMode.BATCH)
        hybrid_desc = get_mode_description(PipelineMode.HYBRID)

        assert "实时" in realtime_desc
        assert "批量" in batch_desc
        assert "混合" in hybrid_desc

    def test_get_source_description(self) -> None:
        """测试获取数据源描述."""
        market_desc = get_source_description(DataSource.MARKET)
        fundamental_desc = get_source_description(DataSource.FUNDAMENTAL)
        sentiment_desc = get_source_description(DataSource.SENTIMENT)
        alternative_desc = get_source_description(DataSource.ALTERNATIVE)

        assert "市场" in market_desc
        assert "基本面" in fundamental_desc
        assert "情绪" in sentiment_desc
        assert "另类" in alternative_desc


# ============================================================================
# DataPipeline Base Class Tests
# ============================================================================


@pytest.mark.unit
class TestDataPipelineBase:
    """DataPipeline基类测试."""

    def test_class_constants(self) -> None:
        """测试类常量."""
        assert DataPipeline.PIPELINE_VERSION == "1.0.0"
        assert DataPipeline.DEFAULT_BATCH_SIZE == 1000
        assert DataPipeline.DEFAULT_BUFFER_SIZE == 10000

    def test_supported_modes(self) -> None:
        """测试支持的模式."""
        assert PipelineMode.REALTIME in DataPipeline.SUPPORTED_MODES
        assert PipelineMode.BATCH in DataPipeline.SUPPORTED_MODES
        assert PipelineMode.HYBRID in DataPipeline.SUPPORTED_MODES

    def test_stage_order(self) -> None:
        """测试阶段顺序."""
        expected_order = (
            ProcessingStage.INGEST,
            ProcessingStage.VALIDATE,
            ProcessingStage.TRANSFORM,
            ProcessingStage.FEATURE,
            ProcessingStage.OUTPUT,
        )
        assert DataPipeline.STAGE_ORDER == expected_order

    def test_update_stage_forward(self, batch_pipeline: BatchPipeline) -> None:
        """测试向前更新阶段."""
        batch_pipeline.update_stage(ProcessingStage.INGEST)
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        assert batch_pipeline.current_stage == ProcessingStage.VALIDATE

    def test_update_stage_backward_raises(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试向后更新阶段抛出异常."""
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        with pytest.raises(ValueError, match="不允许.*回退"):
            batch_pipeline.update_stage(ProcessingStage.INGEST)

    def test_update_stage_to_ingest_allowed(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """测试回到INGEST阶段允许."""
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        batch_pipeline.update_stage(ProcessingStage.INGEST)
        assert batch_pipeline.current_stage == ProcessingStage.INGEST

    def test_record_knowledge(self, batch_pipeline: BatchPipeline) -> None:
        """测试记录知识条目 (M33)."""
        batch_pipeline.record_knowledge(
            category="test",
            content="test content",
            context={"key": "value"},
        )

        entries = batch_pipeline.get_knowledge_entries()
        assert len(entries) == 1
        assert entries[0]["category"] == "test"

    def test_get_audit_log(self, batch_pipeline: BatchPipeline) -> None:
        """测试获取审计日志 (M3)."""
        batch_pipeline.start()
        batch_pipeline.stop()

        audit_log = batch_pipeline.get_audit_log()
        assert len(audit_log) > 0


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestPipelineIntegration:
    """管道集成测试."""

    def test_realtime_full_workflow(self) -> None:
        """测试实时管道完整工作流."""
        pipeline = create_realtime_pipeline(buffer_size=100)

        # 启动管道
        pipeline.start()
        assert pipeline.is_running is True

        # 摄取数据
        for i in range(10):
            pipeline.ingest({"price": 100.0 + i, "volume": 100 + i})

        # 验证缓冲区
        assert pipeline.get_buffer_size() == 10

        # 获取指标
        metrics = pipeline.get_metrics()
        assert metrics.records_processed >= 10

        # 停止管道
        pipeline.stop()
        assert pipeline.is_running is False

        # 验证审计日志 (M3)
        audit_log = pipeline.get_audit_log()
        assert len(audit_log) > 0

    def test_batch_full_workflow(self) -> None:
        """测试批量管道完整工作流."""
        pipeline = create_batch_pipeline(batch_size=10, random_seed=42)

        # 设置处理器
        pipeline.set_item_processor(lambda x: x * 2)

        # 处理数据
        data = list(range(25))
        results = pipeline.process_batch(data)

        # 验证结果
        assert len(results) == 25
        assert results == [x * 2 for x in data]

        # 验证进度
        assert pipeline.get_progress() == 1.0

        # 验证检查点
        checkpoint = pipeline.save_checkpoint()
        assert checkpoint["processed_count"] == 25

        # 验证审计日志 (M3)
        metrics = pipeline.get_metrics()
        assert len(metrics.audit_log) > 0

    def test_batch_checkpoint_recovery(self) -> None:
        """测试批量管道检查点恢复 (M7)."""
        # 第一阶段处理
        pipeline1 = create_batch_pipeline(random_seed=42)
        data = list(range(100))
        pipeline1.process_batch(data[:50])
        checkpoint = pipeline1.save_checkpoint()

        # 恢复处理
        pipeline2 = create_batch_pipeline(random_seed=42)
        pipeline2.load_checkpoint(checkpoint)

        assert pipeline2.processed_count == 50
        assert pipeline2.random_state == 42

    def test_metrics_consistency(self) -> None:
        """测试指标一致性."""
        pipeline = create_batch_pipeline()

        data = list(range(100))
        pipeline.process_batch(data)

        metrics = pipeline.get_metrics()

        # 验证指标一致性
        assert metrics.records_processed == 100
        assert metrics.records_failed == 0
        assert metrics.success_rate == 1.0

        # 验证批次结果
        result = pipeline.get_last_batch_result()
        assert result is not None
        assert result.success_count == 100


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
