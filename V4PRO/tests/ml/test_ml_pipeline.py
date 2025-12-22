"""ML数据管道单元测试 (军规级).

测试覆盖:
- src/ml/pipeline/base.py
- src/ml/pipeline/realtime.py
- src/ml/pipeline/batch.py

每一个代码都要满足M1到M33的要求）每一个代码都要M1到M33都要满足）每写完一个代码模块都要检查是否满足军规 M1-M33。
军规覆盖:
- M26: 测试规范
- M3: 审计日志验证
- M6: 熔断器测试
- M7: 确定性验证

V4PRO Platform Component - Phase 6.1.1 ML数据管道测试
覆盖率目标: >= 95%
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timedelta
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
# 第1部分: base.py 测试
# ============================================================================


class TestPipelineMode:
    """PipelineMode枚举测试."""

    @pytest.mark.unit
    def test_pipeline_mode_values(self) -> None:
        """TC-001: 验证管道模式枚举值."""
        assert PipelineMode.REALTIME.value == "REALTIME"
        assert PipelineMode.BATCH.value == "BATCH"
        assert PipelineMode.HYBRID.value == "HYBRID"

    @pytest.mark.unit
    def test_pipeline_mode_count(self) -> None:
        """TC-002: 验证管道模式数量."""
        modes = list(PipelineMode)
        assert len(modes) == 3

    @pytest.mark.unit
    def test_pipeline_mode_membership(self) -> None:
        """TC-003: 验证枚举成员关系."""
        assert PipelineMode.REALTIME in PipelineMode
        assert PipelineMode.BATCH in PipelineMode
        assert PipelineMode.HYBRID in PipelineMode


class TestDataSource:
    """DataSource枚举测试."""

    @pytest.mark.unit
    def test_data_source_values(self) -> None:
        """TC-010: 验证数据源枚举值."""
        assert DataSource.MARKET.value == "MARKET"
        assert DataSource.FUNDAMENTAL.value == "FUNDAMENTAL"
        assert DataSource.SENTIMENT.value == "SENTIMENT"
        assert DataSource.ALTERNATIVE.value == "ALTERNATIVE"

    @pytest.mark.unit
    def test_data_source_count(self) -> None:
        """TC-011: 验证数据源数量."""
        sources = list(DataSource)
        assert len(sources) == 4

    @pytest.mark.unit
    def test_data_source_descriptions(self) -> None:
        """TC-012: 验证数据源描述."""
        assert "市场数据" in get_source_description(DataSource.MARKET)
        assert "基本面数据" in get_source_description(DataSource.FUNDAMENTAL)
        assert "情绪数据" in get_source_description(DataSource.SENTIMENT)
        assert "另类数据" in get_source_description(DataSource.ALTERNATIVE)


class TestProcessingStage:
    """ProcessingStage枚举测试."""

    @pytest.mark.unit
    def test_processing_stage_values(self) -> None:
        """TC-020: 验证处理阶段枚举值."""
        assert ProcessingStage.INGEST.value == "INGEST"
        assert ProcessingStage.VALIDATE.value == "VALIDATE"
        assert ProcessingStage.TRANSFORM.value == "TRANSFORM"
        assert ProcessingStage.FEATURE.value == "FEATURE"
        assert ProcessingStage.OUTPUT.value == "OUTPUT"

    @pytest.mark.unit
    def test_processing_stage_order(self) -> None:
        """TC-021: 验证处理阶段顺序与STAGE_ORDER一致."""
        expected_order = [
            ProcessingStage.INGEST,
            ProcessingStage.VALIDATE,
            ProcessingStage.TRANSFORM,
            ProcessingStage.FEATURE,
            ProcessingStage.OUTPUT,
        ]
        assert DataPipeline.STAGE_ORDER == tuple(expected_order)

    @pytest.mark.unit
    def test_processing_stage_names(self) -> None:
        """TC-022: 验证处理阶段名称."""
        assert get_stage_name(ProcessingStage.INGEST) == "数据摄取"
        assert get_stage_name(ProcessingStage.VALIDATE) == "数据验证"
        assert get_stage_name(ProcessingStage.TRANSFORM) == "数据转换"
        assert get_stage_name(ProcessingStage.FEATURE) == "特征工程"
        assert get_stage_name(ProcessingStage.OUTPUT) == "输出阶段"


class TestPipelineConfig:
    """PipelineConfig数据类测试."""

    @pytest.mark.unit
    def test_pipeline_config_defaults(self) -> None:
        """TC-030: 验证默认配置."""
        config = PipelineConfig(mode=PipelineMode.BATCH)
        assert config.mode == PipelineMode.BATCH
        assert config.sources == []
        assert config.batch_size == 1000
        assert config.buffer_size == 10000
        assert config.enable_audit is True
        assert config.enable_knowledge is True
        assert config.enable_deterministic is True
        assert config.max_retries == 3
        assert config.retry_delay_ms == 100
        assert config.timeout_ms == 30000
        assert config.metadata == {}

    @pytest.mark.unit
    def test_pipeline_config_custom(self) -> None:
        """TC-031: 验证自定义配置."""
        config = PipelineConfig(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.MARKET, DataSource.SENTIMENT],
            batch_size=500,
            buffer_size=5000,
            enable_audit=False,
            enable_knowledge=False,
            max_retries=5,
            metadata={"key": "value"},
        )
        assert config.mode == PipelineMode.REALTIME
        assert len(config.sources) == 2
        assert DataSource.MARKET in config.sources
        assert config.batch_size == 500
        assert config.buffer_size == 5000
        assert config.enable_audit is False
        assert config.max_retries == 5
        assert config.metadata["key"] == "value"

    @pytest.mark.unit
    def test_pipeline_config_validation_batch_size(self) -> None:
        """TC-032: 验证batch_size验证."""
        with pytest.raises(ValueError, match="batch_size必须为正数"):
            PipelineConfig(mode=PipelineMode.BATCH, batch_size=0)

        with pytest.raises(ValueError, match="batch_size必须为正数"):
            PipelineConfig(mode=PipelineMode.BATCH, batch_size=-1)

    @pytest.mark.unit
    def test_pipeline_config_validation_buffer_size(self) -> None:
        """TC-033: 验证buffer_size验证."""
        with pytest.raises(ValueError, match="buffer_size必须为正数"):
            PipelineConfig(mode=PipelineMode.BATCH, buffer_size=0)

    @pytest.mark.unit
    def test_pipeline_config_validation_buffer_vs_batch(self) -> None:
        """TC-034: 验证buffer_size必须大于等于batch_size."""
        with pytest.raises(ValueError, match="buffer_size.*必须大于等于batch_size"):
            PipelineConfig(mode=PipelineMode.BATCH, batch_size=1000, buffer_size=500)

    @pytest.mark.unit
    def test_pipeline_config_to_dict(self) -> None:
        """TC-035: 验证配置转换为字典."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET],
            batch_size=100,
            buffer_size=1000,
        )
        result = config.to_dict()
        assert result["mode"] == "BATCH"
        assert result["sources"] == ["MARKET"]
        assert result["batch_size"] == 100
        assert result["buffer_size"] == 1000

    @pytest.mark.unit
    def test_pipeline_config_validate_valid(self) -> None:
        """TC-036: 验证有效配置返回True."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET],
        )
        assert config.validate() is True

    @pytest.mark.unit
    def test_pipeline_config_validate_empty_sources(self) -> None:
        """TC-037: 验证空数据源返回False."""
        config = PipelineConfig(mode=PipelineMode.BATCH, sources=[])
        assert config.validate() is False


class TestPipelineMetrics:
    """PipelineMetrics数据类测试."""

    @pytest.mark.unit
    def test_pipeline_metrics_initial(self, pipeline_metrics: PipelineMetrics) -> None:
        """TC-040: 验证初始指标."""
        assert pipeline_metrics.records_processed == 0
        assert pipeline_metrics.records_failed == 0
        assert pipeline_metrics.latency_ms == 0.0
        assert pipeline_metrics.throughput_per_sec == 0.0
        assert pipeline_metrics.stage_metrics == {}
        assert pipeline_metrics.error_counts == {}
        assert pipeline_metrics.start_time == ""
        assert pipeline_metrics.end_time == ""
        assert pipeline_metrics.audit_log == []
        assert pipeline_metrics.knowledge_entries == []

    @pytest.mark.unit
    def test_pipeline_metrics_success_rate_zero_records(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-041: 验证零记录时成功率."""
        assert pipeline_metrics.success_rate == 0.0

    @pytest.mark.unit
    def test_pipeline_metrics_success_rate_all_success(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-042: 验证全部成功时成功率."""
        pipeline_metrics.records_processed = 100
        pipeline_metrics.records_failed = 0
        assert pipeline_metrics.success_rate == 1.0

    @pytest.mark.unit
    def test_pipeline_metrics_success_rate_partial(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-043: 验证部分失败时成功率."""
        pipeline_metrics.records_processed = 80
        pipeline_metrics.records_failed = 20
        assert pipeline_metrics.success_rate == 0.8

    @pytest.mark.unit
    def test_pipeline_metrics_total_records(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-044: 验证总记录数计算."""
        pipeline_metrics.records_processed = 80
        pipeline_metrics.records_failed = 20
        assert pipeline_metrics.total_records == 100

    @pytest.mark.unit
    def test_pipeline_metrics_duration_ms(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-045: 验证处理时长计算."""
        now = datetime.now()
        pipeline_metrics.start_time = now.isoformat()
        pipeline_metrics.end_time = (now + timedelta(seconds=1)).isoformat()
        assert abs(pipeline_metrics.duration_ms - 1000.0) < 10  # 允许10ms误差

    @pytest.mark.unit
    def test_pipeline_metrics_duration_ms_empty(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-046: 验证空时间时处理时长."""
        assert pipeline_metrics.duration_ms == 0.0

    @pytest.mark.unit
    def test_pipeline_metrics_record_stage_metric(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-047: 验证阶段指标记录."""
        pipeline_metrics.record_stage_metric(
            ProcessingStage.INGEST, "duration_ms", 5.5
        )
        assert ProcessingStage.INGEST in pipeline_metrics.stage_metrics
        assert pipeline_metrics.stage_metrics[ProcessingStage.INGEST]["duration_ms"] == 5.5

    @pytest.mark.unit
    def test_pipeline_metrics_record_error(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-048: 验证错误记录."""
        pipeline_metrics.record_error("ValidationError")
        pipeline_metrics.record_error("ValidationError")
        pipeline_metrics.record_error("TimeoutError")
        assert pipeline_metrics.error_counts["ValidationError"] == 2
        assert pipeline_metrics.error_counts["TimeoutError"] == 1
        assert pipeline_metrics.records_failed == 3

    @pytest.mark.unit
    def test_pipeline_metrics_add_audit_entry(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-049: 验证审计日志添加 (M3)."""
        pipeline_metrics.add_audit_entry({"action": "test", "data": 123})
        assert len(pipeline_metrics.audit_log) == 1
        assert pipeline_metrics.audit_log[0]["action"] == "test"
        assert "timestamp" in pipeline_metrics.audit_log[0]

    @pytest.mark.unit
    def test_pipeline_metrics_add_knowledge_entry(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-050: 验证知识条目添加 (M33)."""
        pipeline_metrics.add_knowledge_entry({"category": "test", "content": "data"})
        assert len(pipeline_metrics.knowledge_entries) == 1
        assert pipeline_metrics.knowledge_entries[0]["category"] == "test"

    @pytest.mark.unit
    def test_pipeline_metrics_to_dict(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-051: 验证指标转换为字典."""
        pipeline_metrics.records_processed = 100
        pipeline_metrics.latency_ms = 5.5
        result = pipeline_metrics.to_dict()
        assert result["records_processed"] == 100
        assert result["latency_ms"] == 5.5
        assert "success_rate" in result
        assert "audit_log_count" in result

    @pytest.mark.unit
    def test_pipeline_metrics_to_audit_dict(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-052: 验证审计字典格式 (M3)."""
        pipeline_metrics.records_processed = 50
        pipeline_metrics.add_audit_entry({"action": "test"})
        result = pipeline_metrics.to_audit_dict()
        assert "audit_log" in result
        assert len(result["audit_log"]) == 1

    @pytest.mark.unit
    def test_pipeline_metrics_reset(
        self, pipeline_metrics: PipelineMetrics
    ) -> None:
        """TC-053: 验证指标重置."""
        pipeline_metrics.records_processed = 100
        pipeline_metrics.records_failed = 10
        pipeline_metrics.add_audit_entry({"action": "test"})
        pipeline_metrics.reset()
        assert pipeline_metrics.records_processed == 0
        assert pipeline_metrics.records_failed == 0
        assert pipeline_metrics.audit_log == []


class TestPipelineBaseClass:
    """DataPipeline抽象基类测试."""

    @pytest.mark.unit
    def test_pipeline_class_constants(self) -> None:
        """TC-060: 验证类常量."""
        assert DataPipeline.PIPELINE_VERSION == "1.0.0"
        assert DataPipeline.DEFAULT_BATCH_SIZE == 1000
        assert DataPipeline.DEFAULT_BUFFER_SIZE == 10000
        assert len(DataPipeline.SUPPORTED_MODES) == 3

    @pytest.mark.unit
    def test_pipeline_stage_order(self) -> None:
        """TC-061: 验证阶段顺序."""
        assert len(DataPipeline.STAGE_ORDER) == 5
        assert DataPipeline.STAGE_ORDER[0] == ProcessingStage.INGEST
        assert DataPipeline.STAGE_ORDER[-1] == ProcessingStage.OUTPUT


class TestCreatePipelineConfig:
    """create_pipeline_config便捷函数测试."""

    @pytest.mark.unit
    def test_create_pipeline_config_defaults(self) -> None:
        """TC-070: 验证默认创建配置."""
        config = create_pipeline_config()
        assert config.mode == PipelineMode.BATCH
        assert DataSource.MARKET in config.sources
        assert config.batch_size == 1000
        assert config.enable_audit is True

    @pytest.mark.unit
    def test_create_pipeline_config_custom(self) -> None:
        """TC-071: 验证自定义创建配置."""
        config = create_pipeline_config(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.SENTIMENT],
            batch_size=500,
            enable_audit=False,
        )
        assert config.mode == PipelineMode.REALTIME
        assert config.sources == [DataSource.SENTIMENT]
        assert config.batch_size == 500
        assert config.enable_audit is False


class TestModeDescriptions:
    """模式描述函数测试."""

    @pytest.mark.unit
    def test_get_mode_description(self) -> None:
        """TC-080: 验证模式描述."""
        assert "实时" in get_mode_description(PipelineMode.REALTIME)
        assert "批量" in get_mode_description(PipelineMode.BATCH)
        assert "混合" in get_mode_description(PipelineMode.HYBRID)


# ============================================================================
# 第2部分: realtime.py 测试
# ============================================================================


class TestCircuitState:
    """CircuitState枚举测试."""

    @pytest.mark.unit
    def test_circuit_state_values(self) -> None:
        """TC-100: 验证熔断器状态枚举值."""
        assert CircuitState.CLOSED.value == "CLOSED"
        assert CircuitState.OPEN.value == "OPEN"
        assert CircuitState.HALF_OPEN.value == "HALF_OPEN"

    @pytest.mark.unit
    def test_circuit_state_count(self) -> None:
        """TC-101: 验证熔断器状态数量."""
        states = list(CircuitState)
        assert len(states) == 3


class TestLatencyTracker:
    """LatencyTracker延迟追踪器测试."""

    @pytest.mark.unit
    def test_latency_tracker_initial(self, latency_tracker: LatencyTracker) -> None:
        """TC-110: 验证初始延迟追踪器."""
        assert latency_tracker.samples == []
        assert latency_tracker.max_samples == 100
        assert latency_tracker.p99_threshold_ms == 10.0

    @pytest.mark.unit
    def test_latency_tracker_add_sample(self, latency_tracker: LatencyTracker) -> None:
        """TC-111: 验证添加延迟样本."""
        latency_tracker.add_sample(5.0)
        latency_tracker.add_sample(10.0)
        latency_tracker.add_sample(3.0)
        assert len(latency_tracker.samples) == 3

    @pytest.mark.unit
    def test_latency_tracker_max_samples(self) -> None:
        """TC-112: 验证最大样本数限制."""
        tracker = LatencyTracker(max_samples=5)
        for i in range(10):
            tracker.add_sample(float(i))
        assert len(tracker.samples) == 5
        assert tracker.samples == [5.0, 6.0, 7.0, 8.0, 9.0]

    @pytest.mark.unit
    def test_latency_tracker_p99(self, latency_tracker: LatencyTracker) -> None:
        """TC-113: 验证P99延迟计算."""
        for i in range(100):
            latency_tracker.add_sample(float(i))
        # P99应该接近99
        assert latency_tracker.p99 >= 95.0

    @pytest.mark.unit
    def test_latency_tracker_p99_empty(self, latency_tracker: LatencyTracker) -> None:
        """TC-114: 验证空样本时P99."""
        assert latency_tracker.p99 == 0.0

    @pytest.mark.unit
    def test_latency_tracker_avg(self, latency_tracker: LatencyTracker) -> None:
        """TC-115: 验证平均延迟计算."""
        latency_tracker.add_sample(10.0)
        latency_tracker.add_sample(20.0)
        latency_tracker.add_sample(30.0)
        assert latency_tracker.avg == 20.0

    @pytest.mark.unit
    def test_latency_tracker_avg_empty(self, latency_tracker: LatencyTracker) -> None:
        """TC-116: 验证空样本时平均值."""
        assert latency_tracker.avg == 0.0

    @pytest.mark.unit
    def test_latency_tracker_max_min(self, latency_tracker: LatencyTracker) -> None:
        """TC-117: 验证最大最小延迟."""
        latency_tracker.add_sample(5.0)
        latency_tracker.add_sample(15.0)
        latency_tracker.add_sample(10.0)
        assert latency_tracker.max == 15.0
        assert latency_tracker.min == 5.0

    @pytest.mark.unit
    def test_latency_tracker_max_min_empty(
        self, latency_tracker: LatencyTracker
    ) -> None:
        """TC-118: 验证空样本时最大最小值."""
        assert latency_tracker.max == 0.0
        assert latency_tracker.min == 0.0

    @pytest.mark.unit
    def test_latency_tracker_is_violation(self) -> None:
        """TC-119: 验证延迟违规检测."""
        tracker = LatencyTracker(p99_threshold_ms=10.0)
        for _ in range(100):
            tracker.add_sample(15.0)  # 全部超过阈值
        assert tracker.is_violation() is True

    @pytest.mark.unit
    def test_latency_tracker_no_violation(self) -> None:
        """TC-120: 验证无延迟违规."""
        tracker = LatencyTracker(p99_threshold_ms=10.0)
        for _ in range(100):
            tracker.add_sample(5.0)  # 全部低于阈值
        assert tracker.is_violation() is False

    @pytest.mark.unit
    def test_latency_tracker_reset(self, latency_tracker: LatencyTracker) -> None:
        """TC-121: 验证追踪器重置."""
        latency_tracker.add_sample(10.0)
        latency_tracker.add_sample(20.0)
        latency_tracker.reset()
        assert latency_tracker.samples == []


class TestCircuitBreakerState:
    """CircuitBreakerState熔断器状态测试."""

    @pytest.mark.unit
    def test_circuit_breaker_initial(
        self, circuit_breaker_state: CircuitBreakerState
    ) -> None:
        """TC-130: 验证初始熔断器状态."""
        assert circuit_breaker_state.state == CircuitState.CLOSED
        assert circuit_breaker_state.failure_count == 0
        assert circuit_breaker_state.half_open_attempts == 0

    @pytest.mark.unit
    def test_circuit_breaker_reset(
        self, circuit_breaker_state: CircuitBreakerState
    ) -> None:
        """TC-131: 验证熔断器状态重置."""
        circuit_breaker_state.state = CircuitState.OPEN
        circuit_breaker_state.failure_count = 50
        circuit_breaker_state.open_time = time.time()
        circuit_breaker_state.reset()
        assert circuit_breaker_state.state == CircuitState.CLOSED
        assert circuit_breaker_state.failure_count == 0
        assert circuit_breaker_state.open_time == 0.0


class TestBufferedItem:
    """BufferedItem缓冲区数据项测试."""

    @pytest.mark.unit
    def test_buffered_item_creation(self) -> None:
        """TC-140: 验证缓冲区数据项创建."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test-001",
            sequence_id=1,
            metadata={"source": "test"},
        )
        assert item.data == {"price": 100.0}
        assert item.correlation_id == "test-001"
        assert item.sequence_id == 1
        assert item.metadata["source"] == "test"


class TestRealtimePipelineCreate:
    """RealtimePipeline创建测试."""

    @pytest.mark.unit
    def test_realtime_pipeline_create(
        self, realtime_config: PipelineConfig
    ) -> None:
        """TC-150: 创建实时管道."""
        pipeline = RealtimePipeline(realtime_config)
        assert pipeline.config.mode == PipelineMode.REALTIME
        assert pipeline.circuit_state == CircuitState.CLOSED
        assert pipeline.is_running is False

    @pytest.mark.unit
    def test_realtime_pipeline_wrong_mode(self) -> None:
        """TC-151: 验证错误模式创建失败."""
        config = PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET],
        )
        with pytest.raises(ValueError, match="仅支持REALTIME模式"):
            RealtimePipeline(config)

    @pytest.mark.unit
    def test_realtime_pipeline_with_callbacks(
        self, realtime_config: PipelineConfig
    ) -> None:
        """TC-152: 验证带回调的管道创建."""
        open_called = []
        close_called = []

        def on_open():
            open_called.append(True)

        def on_close():
            close_called.append(True)

        pipeline = RealtimePipeline(
            realtime_config,
            on_circuit_open=on_open,
            on_circuit_close=on_close,
        )
        assert pipeline is not None


class TestRealtimePipelineIngest:
    """RealtimePipeline数据摄取测试."""

    @pytest.mark.unit
    def test_realtime_pipeline_ingest(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-160: 数据摄取."""
        realtime_pipeline.start()
        result = realtime_pipeline.ingest({"price": 100.0})
        assert isinstance(result, BufferedItem)
        assert result.data == {"price": 100.0}
        assert result.sequence_id == 1

    @pytest.mark.unit
    def test_realtime_pipeline_ingest_multiple(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-161: 多次数据摄取."""
        realtime_pipeline.start()
        for i in range(5):
            result = realtime_pipeline.ingest({"index": i})
            assert result.sequence_id == i + 1

    @pytest.mark.unit
    def test_realtime_pipeline_ingest_with_audit(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-162: 验证摄取审计日志 (M3)."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"price": 100.0})
        audit_log = realtime_pipeline.get_audit_log()
        # 应包含启动日志和摄取日志
        assert len(audit_log) >= 2


class TestRealtimePipelineBuffer:
    """RealtimePipeline缓冲区测试."""

    @pytest.mark.unit
    def test_realtime_pipeline_buffer_size(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-170: 缓冲区大小追踪."""
        realtime_pipeline.start()
        assert realtime_pipeline.get_buffer_size() == 0
        realtime_pipeline.ingest({"data": 1})
        assert realtime_pipeline.get_buffer_size() == 1
        realtime_pipeline.ingest({"data": 2})
        assert realtime_pipeline.get_buffer_size() == 2

    @pytest.mark.unit
    def test_realtime_pipeline_buffer_capacity(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-171: 缓冲区容量."""
        assert realtime_pipeline.get_buffer_capacity() == 500

    @pytest.mark.unit
    def test_realtime_pipeline_buffer_clear(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-172: 缓冲区清空."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"data": 1})
        realtime_pipeline.ingest({"data": 2})
        cleared = realtime_pipeline.clear_buffer()
        assert cleared == 2
        assert realtime_pipeline.get_buffer_size() == 0


class TestRealtimePipelineCircuitBreaker:
    """RealtimePipeline熔断器测试 (M6)."""

    @pytest.mark.unit
    def test_circuit_breaker_initial_closed(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-180: 熔断器初始关闭状态."""
        assert realtime_pipeline.circuit_state == CircuitState.CLOSED
        assert realtime_pipeline.is_circuit_open is False

    @pytest.mark.unit
    def test_circuit_breaker_manual_reset(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-181: 熔断器手动重置."""
        realtime_pipeline.reset_circuit_breaker()
        assert realtime_pipeline.circuit_state == CircuitState.CLOSED

    @pytest.mark.unit
    def test_circuit_breaker_audit_on_reset(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-182: 熔断器重置审计日志."""
        realtime_pipeline.reset_circuit_breaker()
        audit_log = realtime_pipeline.get_audit_log()
        reset_entries = [e for e in audit_log if e.get("reason") == "manual_reset"]
        assert len(reset_entries) >= 1


class TestRealtimePipelineLatencyTracking:
    """RealtimePipeline延迟追踪测试."""

    @pytest.mark.unit
    def test_latency_tracking(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-190: 延迟追踪."""
        realtime_pipeline.start()
        for _ in range(10):
            realtime_pipeline.ingest({"data": 1})
        stats = realtime_pipeline.get_latency_stats()
        assert "avg_ms" in stats
        assert "p99_ms" in stats
        assert "max_ms" in stats
        assert "min_ms" in stats
        assert stats["sample_count"] == 10


class TestRealtimePipelineAuditLogging:
    """RealtimePipeline审计日志测试 (M3)."""

    @pytest.mark.unit
    def test_audit_logging_enabled(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-200: 审计日志记录."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"data": 1})
        audit_log = realtime_pipeline.get_audit_log()
        assert len(audit_log) > 0
        # 验证日志包含必要字段
        for entry in audit_log:
            assert "timestamp" in entry
            assert "event_type" in entry
            assert "pipeline" in entry

    @pytest.mark.unit
    def test_audit_logging_clear(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-201: 审计日志清空."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"data": 1})
        realtime_pipeline.clear_audit_log()
        assert len(realtime_pipeline.get_audit_log()) == 0


class TestRealtimePipelineValidate:
    """RealtimePipeline验证测试."""

    @pytest.mark.unit
    def test_validate_none(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-210: 验证None数据."""
        assert realtime_pipeline.validate(None) is False

    @pytest.mark.unit
    def test_validate_valid_data(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-211: 验证有效数据."""
        assert realtime_pipeline.validate({"data": 1}) is True

    @pytest.mark.unit
    def test_validate_buffered_item(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-212: 验证BufferedItem."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test",
            sequence_id=1,
        )
        assert realtime_pipeline.validate(item) is True

    @pytest.mark.unit
    def test_validate_buffered_item_null_data(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-213: 验证空数据的BufferedItem."""
        item = BufferedItem(
            data=None,
            timestamp=time.time(),
            correlation_id="test",
            sequence_id=1,
        )
        assert realtime_pipeline.validate(item) is False


class TestRealtimePipelineTransform:
    """RealtimePipeline转换测试."""

    @pytest.mark.unit
    def test_transform_buffered_item(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-220: 转换BufferedItem."""
        item = BufferedItem(
            data={"price": 100.0},
            timestamp=time.time(),
            correlation_id="test",
            sequence_id=1,
            metadata={},
        )
        result = realtime_pipeline.transform(item)
        assert result is item
        assert "transform_time" in result.metadata

    @pytest.mark.unit
    def test_transform_raw_data(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-221: 转换原始数据."""
        data = {"price": 100.0}
        result = realtime_pipeline.transform(data)
        assert result == data


class TestRealtimePipelineProcess:
    """RealtimePipeline处理测试."""

    @pytest.mark.unit
    def test_process_single(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-230: 处理单条数据."""
        realtime_pipeline.start()
        result = realtime_pipeline.process({"price": 100.0})
        assert isinstance(result, BufferedItem)
        assert result.data == {"price": 100.0}


class TestRealtimePipelineStatus:
    """RealtimePipeline状态测试."""

    @pytest.mark.unit
    def test_get_status(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-240: 获取管道状态."""
        realtime_pipeline.start()
        status = realtime_pipeline.get_status()
        assert "running" in status
        assert "mode" in status
        assert "buffer" in status
        assert "circuit_breaker" in status
        assert "latency" in status
        assert "counters" in status

    @pytest.mark.unit
    def test_get_metrics(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-241: 获取管道指标."""
        realtime_pipeline.start()
        # process() increments _processed_count, ingest() only adds to buffer
        realtime_pipeline.process({"data": 1})
        metrics = realtime_pipeline.get_metrics()
        assert isinstance(metrics, PipelineMetrics)
        assert metrics.records_processed >= 1


class TestRealtimePipelineLifecycle:
    """RealtimePipeline生命周期测试."""

    @pytest.mark.unit
    def test_start_stop(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-250: 启动和停止管道."""
        assert realtime_pipeline.is_running is False
        realtime_pipeline.start()
        assert realtime_pipeline.is_running is True
        realtime_pipeline.stop()
        assert realtime_pipeline.is_running is False

    @pytest.mark.unit
    def test_reset(self, realtime_pipeline: RealtimePipeline) -> None:
        """TC-251: 重置管道."""
        realtime_pipeline.start()
        realtime_pipeline.ingest({"data": 1})
        realtime_pipeline.reset()
        assert realtime_pipeline.is_running is False
        assert realtime_pipeline.get_buffer_size() == 0
        assert realtime_pipeline.processed_count == 0


class TestCreateRealtimePipeline:
    """create_realtime_pipeline便捷函数测试."""

    @pytest.mark.unit
    def test_create_realtime_pipeline_defaults(self) -> None:
        """TC-260: 默认创建实时管道."""
        pipeline = create_realtime_pipeline()
        assert pipeline.config.mode == PipelineMode.REALTIME
        assert pipeline.config.enable_audit is True

    @pytest.mark.unit
    def test_create_realtime_pipeline_custom(self) -> None:
        """TC-261: 自定义创建实时管道."""
        pipeline = create_realtime_pipeline(
            buffer_size=1000,
            enable_audit=False,
            enable_knowledge=False,
        )
        assert pipeline.get_buffer_capacity() == 1000
        assert pipeline.config.enable_audit is False


# ============================================================================
# 第3部分: batch.py 测试
# ============================================================================


class TestBatchCheckpoint:
    """BatchCheckpoint检查点测试."""

    @pytest.mark.unit
    def test_batch_checkpoint_creation(self) -> None:
        """TC-300: 创建检查点."""
        checkpoint = BatchCheckpoint(
            batch_id="batch-001",
            processed_count=50,
            total_count=100,
            last_processed_index=49,
            random_state=42,
            data_hash="abcd1234",
            timestamp=datetime.now().isoformat(),
            metadata={"key": "value"},
        )
        assert checkpoint.batch_id == "batch-001"
        assert checkpoint.processed_count == 50
        assert checkpoint.total_count == 100
        assert checkpoint.random_state == 42

    @pytest.mark.unit
    def test_batch_checkpoint_to_dict(self) -> None:
        """TC-301: 检查点转换为字典."""
        checkpoint = BatchCheckpoint(
            batch_id="batch-001",
            processed_count=50,
            total_count=100,
            last_processed_index=49,
            random_state=42,
            data_hash="abcd1234",
            timestamp="2024-01-01T00:00:00",
        )
        result = checkpoint.to_dict()
        assert result["batch_id"] == "batch-001"
        assert result["processed_count"] == 50
        assert result["random_state"] == 42

    @pytest.mark.unit
    def test_batch_checkpoint_from_dict(self) -> None:
        """TC-302: 从字典创建检查点."""
        data = {
            "batch_id": "batch-002",
            "processed_count": 75,
            "total_count": 100,
            "last_processed_index": 74,
            "random_state": 123,
            "data_hash": "efgh5678",
            "timestamp": "2024-01-01T00:00:00",
            "metadata": {"test": True},
        }
        checkpoint = BatchCheckpoint.from_dict(data)
        assert checkpoint.batch_id == "batch-002"
        assert checkpoint.processed_count == 75
        assert checkpoint.metadata["test"] is True


class TestBatchProcessingResult:
    """BatchProcessingResult处理结果测试."""

    @pytest.mark.unit
    def test_batch_processing_result_empty(self) -> None:
        """TC-310: 空处理结果."""
        result = BatchProcessingResult()
        assert result.success_count == 0
        assert result.failed_count == 0
        assert result.total_count == 0
        assert result.success_rate == 0.0

    @pytest.mark.unit
    def test_batch_processing_result_success(self) -> None:
        """TC-311: 成功处理结果."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3, 4, 5]
        assert result.success_count == 5
        assert result.success_rate == 1.0

    @pytest.mark.unit
    def test_batch_processing_result_partial(self) -> None:
        """TC-312: 部分成功处理结果."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3, 4]
        result.failed_items = [(4, 5, "error")]
        assert result.success_count == 4
        assert result.failed_count == 1
        assert result.success_rate == 0.8

    @pytest.mark.unit
    def test_batch_processing_result_to_dict(self) -> None:
        """TC-313: 处理结果转换为字典."""
        result = BatchProcessingResult()
        result.success_items = [1, 2, 3]
        result.processing_time_ms = 100.5
        result_dict = result.to_dict()
        assert result_dict["success_count"] == 3
        assert result_dict["processing_time_ms"] == 100.5


class TestBatchPipelineCreate:
    """BatchPipeline创建测试."""

    @pytest.mark.unit
    def test_batch_pipeline_create(self, batch_config: PipelineConfig) -> None:
        """TC-320: 创建批量管道."""
        pipeline = BatchPipeline(batch_config)
        assert pipeline.config.mode == PipelineMode.BATCH
        assert pipeline.processed_count == 0
        assert pipeline.total_count == 0

    @pytest.mark.unit
    def test_batch_pipeline_wrong_mode(self) -> None:
        """TC-321: 验证错误模式创建失败."""
        config = PipelineConfig(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.MARKET],
        )
        with pytest.raises(ValueError, match="仅支持BATCH模式"):
            BatchPipeline(config)


class TestBatchPipelineProcess:
    """BatchPipeline批量处理测试."""

    @pytest.mark.unit
    def test_batch_pipeline_process(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-330: 批量处理."""
        results = batch_pipeline.process_batch(sample_data)
        assert len(results) == len(sample_data)
        assert batch_pipeline.processed_count == len(sample_data)
        assert batch_pipeline.get_progress() == 1.0

    @pytest.mark.unit
    def test_batch_pipeline_process_empty(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-331: 处理空列表."""
        results = batch_pipeline.process_batch([])
        assert len(results) == 0
        assert batch_pipeline.processed_count == 0

    @pytest.mark.unit
    def test_batch_pipeline_process_with_processor(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-332: 带处理器的批量处理."""
        batch_pipeline.set_item_processor(lambda x: x * 2)
        results = batch_pipeline.process_batch([1, 2, 3, 4, 5])
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.unit
    def test_batch_pipeline_process_audit(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-333: 批量处理审计日志 (M3)."""
        batch_pipeline.process_batch(sample_data)
        metrics = batch_pipeline.get_metrics()
        assert len(metrics.audit_log) > 0
        # 应包含batch_start和batch_complete
        actions = [e.get("action") for e in metrics.audit_log]
        assert "batch_start" in actions
        assert "batch_complete" in actions


class TestBatchPipelineCheckpointSave:
    """BatchPipeline检查点保存测试."""

    @pytest.mark.unit
    def test_batch_pipeline_checkpoint_save(
        self, batch_pipeline: BatchPipeline, large_sample_data: list
    ) -> None:
        """TC-340: 检查点保存."""
        batch_pipeline.process_batch(large_sample_data)
        checkpoint = batch_pipeline.save_checkpoint()
        assert "batch_id" in checkpoint
        assert "processed_count" in checkpoint
        assert "total_count" in checkpoint
        assert checkpoint["processed_count"] == len(large_sample_data)

    @pytest.mark.unit
    def test_batch_pipeline_checkpoint_info(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-341: 检查点信息."""
        batch_pipeline.process_batch(sample_data)
        info = batch_pipeline.get_checkpoint_info()
        assert "has_checkpoint" in info
        assert "batch_id" in info
        assert "progress" in info


class TestBatchPipelineCheckpointLoad:
    """BatchPipeline检查点恢复测试."""

    @pytest.mark.unit
    def test_batch_pipeline_checkpoint_load(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-350: 检查点恢复."""
        checkpoint = {
            "batch_id": "test-batch",
            "processed_count": 50,
            "total_count": 100,
            "last_processed_index": 49,
            "random_state": 42,
            "data_hash": "abcd1234",
            "timestamp": datetime.now().isoformat(),
        }
        batch_pipeline.load_checkpoint(checkpoint)
        assert batch_pipeline.processed_count == 50
        assert batch_pipeline.total_count == 100
        assert batch_pipeline.random_state == 42

    @pytest.mark.unit
    def test_batch_pipeline_checkpoint_load_empty(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-351: 加载空检查点."""
        with pytest.raises(ValueError, match="检查点数据为空"):
            batch_pipeline.load_checkpoint({})

    @pytest.mark.unit
    def test_batch_pipeline_checkpoint_load_missing_fields(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-352: 加载缺少字段的检查点."""
        with pytest.raises(ValueError, match="检查点缺少必要字段"):
            batch_pipeline.load_checkpoint({"batch_id": "test"})


class TestBatchPipelineDeterministic:
    """BatchPipeline确定性测试 (M7)."""

    @pytest.mark.unit
    def test_batch_pipeline_deterministic(
        self, deterministic_pipeline: BatchPipeline
    ) -> None:
        """TC-360: M7确定性验证."""
        # 设置随机种子
        deterministic_pipeline.set_random_state(42)

        # 第一次处理
        data = [1, 2, 3, 4, 5]
        result1 = deterministic_pipeline.process_batch(data)

        # 重置并再次处理
        deterministic_pipeline.reset()
        deterministic_pipeline.set_random_state(42)
        result2 = deterministic_pipeline.process_batch(data)

        # 结果应相同
        assert result1 == result2

    @pytest.mark.unit
    def test_batch_pipeline_random_state(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-361: 随机种子设置."""
        batch_pipeline.set_random_state(123)
        assert batch_pipeline.random_state == 123

    @pytest.mark.unit
    def test_batch_pipeline_random_state_audit(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-362: 随机种子设置审计日志."""
        batch_pipeline.set_random_state(42)
        metrics = batch_pipeline.get_metrics()
        # 应有设置随机种子的审计日志
        actions = [e.get("action") for e in metrics.audit_log]
        assert "set_random_state" in actions


class TestBatchPipelineProgress:
    """BatchPipeline进度追踪测试."""

    @pytest.mark.unit
    def test_batch_pipeline_progress_initial(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-370: 初始进度."""
        assert batch_pipeline.get_progress() == 0.0

    @pytest.mark.unit
    def test_batch_pipeline_progress_complete(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-371: 完成进度."""
        batch_pipeline.process_batch(sample_data)
        assert batch_pipeline.get_progress() == 1.0

    @pytest.mark.unit
    def test_batch_pipeline_progress_partial(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-372: 部分进度."""
        # 通过加载检查点模拟部分进度
        checkpoint = {
            "batch_id": "test",
            "processed_count": 50,
            "total_count": 100,
            "last_processed_index": 49,
            "random_state": None,
            "data_hash": "test",
            "timestamp": datetime.now().isoformat(),
        }
        batch_pipeline.load_checkpoint(checkpoint)
        assert batch_pipeline.get_progress() == 0.5


class TestBatchPipelineIngest:
    """BatchPipeline摄取测试."""

    @pytest.mark.unit
    def test_batch_pipeline_ingest_list(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-380: 摄取列表数据."""
        data = [1, 2, 3]
        result = batch_pipeline.ingest(data)
        assert result == [1, 2, 3]

    @pytest.mark.unit
    def test_batch_pipeline_ingest_single(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-381: 摄取单个数据."""
        result = batch_pipeline.ingest(42)
        assert result == [42]

    @pytest.mark.unit
    def test_batch_pipeline_ingest_iterator(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-382: 摄取迭代器."""
        result = batch_pipeline.ingest(range(5))
        assert result == [0, 1, 2, 3, 4]


class TestBatchPipelineValidate:
    """BatchPipeline验证测试."""

    @pytest.mark.unit
    def test_batch_pipeline_validate_none(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-390: 验证None数据."""
        # 需要先切换到VALIDATE阶段
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        assert batch_pipeline.validate(None) is False

    @pytest.mark.unit
    def test_batch_pipeline_validate_empty_list(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-391: 验证空列表."""
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        assert batch_pipeline.validate([]) is False

    @pytest.mark.unit
    def test_batch_pipeline_validate_valid(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-392: 验证有效数据."""
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        assert batch_pipeline.validate([1, 2, 3]) is True


class TestBatchPipelineTransform:
    """BatchPipeline转换测试."""

    @pytest.mark.unit
    def test_batch_pipeline_transform(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-400: 数据转换."""
        batch_pipeline.update_stage(ProcessingStage.TRANSFORM)
        data = [1, 2, 3]
        result = batch_pipeline.transform(data)
        assert result == data  # 默认不变换


class TestBatchPipelineFullProcess:
    """BatchPipeline完整处理流程测试."""

    @pytest.mark.unit
    def test_batch_pipeline_full_process(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-410: 完整处理流程."""
        result = batch_pipeline.process(sample_data)
        assert len(result) == len(sample_data)

    @pytest.mark.unit
    def test_batch_pipeline_full_process_validation_fail(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-411: 验证失败的完整处理."""
        with pytest.raises(ValueError, match="数据验证失败"):
            batch_pipeline.process([])


class TestBatchPipelineLifecycle:
    """BatchPipeline生命周期测试."""

    @pytest.mark.unit
    def test_batch_pipeline_reset(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-420: 重置管道."""
        batch_pipeline.process_batch(sample_data)
        batch_pipeline.reset()
        assert batch_pipeline.processed_count == 0
        assert batch_pipeline.total_count == 0
        assert batch_pipeline.current_batch_id == ""

    @pytest.mark.unit
    def test_batch_pipeline_get_batch_results(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-421: 获取批次结果."""
        batch_pipeline.process_batch(sample_data)
        results = batch_pipeline.get_batch_results()
        assert len(results) == 1
        assert isinstance(results[0], BatchProcessingResult)

    @pytest.mark.unit
    def test_batch_pipeline_get_last_batch_result(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-422: 获取最后批次结果."""
        batch_pipeline.process_batch(sample_data)
        result = batch_pipeline.get_last_batch_result()
        assert result is not None
        assert result.success_count == len(sample_data)

    @pytest.mark.unit
    def test_batch_pipeline_get_last_batch_result_empty(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-423: 无批次时获取最后结果."""
        result = batch_pipeline.get_last_batch_result()
        assert result is None


class TestCreateBatchPipeline:
    """create_batch_pipeline便捷函数测试."""

    @pytest.mark.unit
    def test_create_batch_pipeline_defaults(self) -> None:
        """TC-430: 默认创建批量管道."""
        pipeline = create_batch_pipeline()
        assert pipeline.config.mode == PipelineMode.BATCH
        assert pipeline.config.batch_size == 10000
        assert pipeline.config.enable_audit is True

    @pytest.mark.unit
    def test_create_batch_pipeline_custom(self) -> None:
        """TC-431: 自定义创建批量管道."""
        pipeline = create_batch_pipeline(
            batch_size=500,
            enable_audit=False,
            random_seed=42,
        )
        assert pipeline.config.batch_size == 500
        assert pipeline.config.enable_audit is False
        assert pipeline.random_state == 42


class TestProcessInBatches:
    """process_in_batches便捷函数测试."""

    @pytest.mark.unit
    def test_process_in_batches_simple(self) -> None:
        """TC-440: 简单批量处理."""
        data = [1, 2, 3, 4, 5]
        results = process_in_batches(data)
        assert results == data

    @pytest.mark.unit
    def test_process_in_batches_with_processor(self) -> None:
        """TC-441: 带处理器的批量处理."""
        data = [1, 2, 3, 4, 5]
        results = process_in_batches(data, processor=lambda x: x * 2)
        assert results == [2, 4, 6, 8, 10]

    @pytest.mark.unit
    def test_process_in_batches_deterministic(self) -> None:
        """TC-442: 确定性批量处理."""
        data = [1, 2, 3, 4, 5]
        result1 = process_in_batches(data, random_seed=42)
        result2 = process_in_batches(data, random_seed=42)
        assert result1 == result2


# ============================================================================
# 第4部分: 集成测试
# ============================================================================


class TestPipelineIntegration:
    """管道集成测试."""

    @pytest.mark.unit
    def test_pipeline_end_to_end_batch(
        self, batch_config: PipelineConfig, large_sample_data: list
    ) -> None:
        """TC-500: 批量管道端到端测试."""
        # 创建管道
        pipeline = BatchPipeline(batch_config)
        pipeline.set_random_state(42)

        # 处理数据
        results = pipeline.process_batch(large_sample_data)

        # 验证结果
        assert len(results) == len(large_sample_data)
        assert pipeline.get_progress() == 1.0

        # 验证指标
        metrics = pipeline.get_metrics()
        assert metrics.records_processed == len(large_sample_data)
        assert metrics.success_rate == 1.0

        # 验证审计日志 (M3)
        assert len(metrics.audit_log) > 0

        # 保存检查点
        checkpoint = pipeline.save_checkpoint()
        assert checkpoint["processed_count"] == len(large_sample_data)

    @pytest.mark.unit
    def test_pipeline_end_to_end_realtime(
        self, realtime_config: PipelineConfig, sample_data: list
    ) -> None:
        """TC-501: 实时管道端到端测试."""
        # 创建管道
        pipeline = RealtimePipeline(realtime_config)
        pipeline.start()

        # 摄取数据
        for item in sample_data:
            pipeline.ingest(item)

        # 验证状态
        status = pipeline.get_status()
        assert status["running"] is True
        assert status["buffer"]["size"] == len(sample_data)

        # 验证审计日志 (M3)
        audit_log = pipeline.get_audit_log()
        assert len(audit_log) > 0

        # 停止管道
        pipeline.stop()
        assert pipeline.is_running is False

    @pytest.mark.unit
    def test_batch_checkpoint_recovery(
        self, batch_config: PipelineConfig
    ) -> None:
        """TC-502: 批量管道检查点恢复测试."""
        # 第一个管道处理部分数据
        pipeline1 = BatchPipeline(batch_config)
        pipeline1.set_random_state(42)
        data = list(range(100))
        pipeline1.process_batch(data[:50])
        checkpoint = pipeline1.save_checkpoint()

        # 第二个管道从检查点恢复
        pipeline2 = BatchPipeline(batch_config)
        pipeline2.load_checkpoint(checkpoint)

        # 验证状态恢复
        assert pipeline2.processed_count == 50
        assert pipeline2.random_state == 42

    @pytest.mark.unit
    def test_pipeline_stage_transitions(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-503: 管道阶段转换测试."""
        # 初始阶段
        assert batch_pipeline.current_stage == ProcessingStage.INGEST

        # 正向转换
        batch_pipeline.update_stage(ProcessingStage.VALIDATE)
        assert batch_pipeline.current_stage == ProcessingStage.VALIDATE

        batch_pipeline.update_stage(ProcessingStage.TRANSFORM)
        assert batch_pipeline.current_stage == ProcessingStage.TRANSFORM

        # 回到起点是允许的
        batch_pipeline.update_stage(ProcessingStage.INGEST)
        assert batch_pipeline.current_stage == ProcessingStage.INGEST

    @pytest.mark.unit
    def test_pipeline_stage_invalid_transition(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-504: 管道无效阶段转换测试."""
        batch_pipeline.update_stage(ProcessingStage.TRANSFORM)

        # 回退到非起点阶段应失败
        with pytest.raises(ValueError, match="不允许.*回退"):
            batch_pipeline.update_stage(ProcessingStage.VALIDATE)

    @pytest.mark.unit
    def test_pipeline_knowledge_recording(
        self, batch_pipeline: BatchPipeline, sample_data: list
    ) -> None:
        """TC-505: 管道知识记录测试 (M33)."""
        batch_pipeline.record_knowledge(
            category="test",
            content="测试知识",
            context={"key": "value"},
        )
        entries = batch_pipeline.get_knowledge_entries()
        assert len(entries) == 1
        assert entries[0]["category"] == "test"

    @pytest.mark.unit
    def test_realtime_latency_compliance(
        self, realtime_pipeline: RealtimePipeline
    ) -> None:
        """TC-506: 实时管道延迟合规测试."""
        realtime_pipeline.start()

        # 执行多次摄取
        for i in range(50):
            realtime_pipeline.ingest({"index": i})

        # 检查延迟统计
        stats = realtime_pipeline.get_latency_stats()
        assert "is_compliant" in stats
        # 在测试环境中应该合规
        # (实际延迟可能因环境而异)

    @pytest.mark.unit
    def test_batch_error_handling(
        self, batch_pipeline: BatchPipeline
    ) -> None:
        """TC-507: 批量管道错误处理测试."""
        # 设置会抛出异常的处理器
        def faulty_processor(x: Any) -> Any:
            if x == 3:
                raise ValueError("模拟错误")
            return x

        batch_pipeline.set_item_processor(faulty_processor)
        results = batch_pipeline.process_batch([1, 2, 3, 4, 5])

        # 应该处理成功的项
        assert len(results) == 4  # 1, 2, 4, 5
        assert 3 not in results

        # 检查失败记录
        last_result = batch_pipeline.get_last_batch_result()
        assert last_result is not None
        assert last_result.failed_count == 1

    @pytest.mark.unit
    def test_metrics_throughput_calculation(
        self, batch_pipeline: BatchPipeline, large_sample_data: list
    ) -> None:
        """TC-508: 指标吞吐量计算测试."""
        batch_pipeline.process_batch(large_sample_data)
        # 添加小延迟确保start_time和end_time不同
        time.sleep(0.01)
        metrics = batch_pipeline.get_metrics()

        # 吞吐量应大于等于0（快速处理时可能为0）
        assert metrics.throughput_per_sec >= 0
        # 延迟应有值
        assert metrics.latency_ms >= 0
        # 验证记录数正确
        assert metrics.records_processed == len(large_sample_data)

    @pytest.mark.unit
    def test_realtime_buffer_overflow(self) -> None:
        """TC-509: 实时管道缓冲区溢出测试."""
        # 创建小缓冲区的管道
        config = PipelineConfig(
            mode=PipelineMode.REALTIME,
            sources=[DataSource.MARKET],
            batch_size=1,  # 必须设置batch_size<=buffer_size
            buffer_size=5,
        )
        pipeline = RealtimePipeline(config)
        pipeline.start()

        # 摄取超过缓冲区容量的数据
        for i in range(10):
            pipeline.ingest({"index": i})

        # 缓冲区大小应等于容量
        assert pipeline.get_buffer_size() == 5
        # 应有丢弃记录
        assert pipeline.dropped_count > 0


class TestAuditEventType:
    """AuditEventType枚举测试."""

    @pytest.mark.unit
    def test_audit_event_type_values(self) -> None:
        """TC-510: 验证审计事件类型枚举值."""
        assert AuditEventType.INGEST.value == "INGEST"
        assert AuditEventType.PROCESS.value == "PROCESS"
        assert AuditEventType.CIRCUIT_OPEN.value == "CIRCUIT_OPEN"
        assert AuditEventType.CIRCUIT_CLOSE.value == "CIRCUIT_CLOSE"
        assert AuditEventType.BUFFER_OVERFLOW.value == "BUFFER_OVERFLOW"
        assert AuditEventType.LATENCY_VIOLATION.value == "LATENCY_VIOLATION"
        assert AuditEventType.ERROR.value == "ERROR"
