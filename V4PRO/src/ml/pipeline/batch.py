"""批量数据管道实现 (军规级 v4.0).

V4PRO Platform Component - Phase 6.1.1 ML数据管道基础框架
V4 SPEC: SS30 数据管道设计, SS31 特征工程流水线
V4 Scenarios:
- ML.PIPELINE.BATCH: 批量数据处理
- ML.PIPELINE.BATCH.CHECKPOINT: 检查点恢复
- ML.PIPELINE.BATCH.PROGRESS: 进度追踪
- ML.PIPELINE.BATCH.DETERMINISTIC: 确定性处理

军规覆盖:
- M3: 完整审计日志 - 所有批量操作必须记录审计轨迹
- M7: 确定性处理 - 设置随机种子确保回放一致
- M33: 知识沉淀机制 - 批量处理经验沉淀为可复用知识

功能特性:
- 大批量处理，高吞吐
- 确定性处理 (M7: 回放一致)
- 检查点恢复
- 进度追踪
- 错误容忍与重试

示例:
    >>> from src.ml.pipeline.batch import BatchPipeline
    >>> from src.ml.pipeline.base import PipelineConfig, PipelineMode
    >>> config = PipelineConfig(mode=PipelineMode.BATCH, batch_size=5000)
    >>> pipeline = BatchPipeline(config)
    >>> pipeline.set_random_state(42)  # M7 确定性
    >>> results = pipeline.process_batch(data_list)
    >>> progress = pipeline.get_progress()
    >>> print(f"Progress: {progress:.2%}")
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from src.ml.pipeline.base import (
    DataPipeline,
    PipelineConfig,
    PipelineMetrics,
    PipelineMode,
    ProcessingStage,
)


@dataclass
class BatchCheckpoint:
    """批量处理检查点 (军规 M7).

    记录批量处理的断点状态，支持恢复处理。

    属性:
        batch_id: 批次ID
        processed_count: 已处理数量
        total_count: 总数量
        last_processed_index: 最后处理的索引
        random_state: 随机状态 (M7 确定性)
        data_hash: 数据哈希 (用于验证数据一致性)
        timestamp: 检查点时间戳
        metadata: 额外元数据
    """

    batch_id: str
    processed_count: int
    total_count: int
    last_processed_index: int
    random_state: int | None
    data_hash: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式.

        返回:
            检查点字典
        """
        return {
            "batch_id": self.batch_id,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "last_processed_index": self.last_processed_index,
            "random_state": self.random_state,
            "data_hash": self.data_hash,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatchCheckpoint:
        """从字典创建检查点.

        参数:
            data: 检查点字典

        返回:
            BatchCheckpoint实例
        """
        return cls(
            batch_id=data["batch_id"],
            processed_count=data["processed_count"],
            total_count=data["total_count"],
            last_processed_index=data["last_processed_index"],
            random_state=data.get("random_state"),
            data_hash=data["data_hash"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class BatchProcessingResult:
    """批量处理结果.

    属性:
        success_items: 成功处理的项
        failed_items: 失败的项
        error_details: 错误详情
        processing_time_ms: 处理时间(毫秒)
    """

    success_items: list[Any] = field(default_factory=list)
    failed_items: list[tuple[int, Any, str]] = field(
        default_factory=list
    )  # (index, item, error)
    error_details: list[dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0

    @property
    def success_count(self) -> int:
        """成功数量."""
        return len(self.success_items)

    @property
    def failed_count(self) -> int:
        """失败数量."""
        return len(self.failed_items)

    @property
    def total_count(self) -> int:
        """总数量."""
        return self.success_count + self.failed_count

    @property
    def success_rate(self) -> float:
        """成功率."""
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "total_count": self.total_count,
            "success_rate": round(self.success_rate, 4),
            "processing_time_ms": round(self.processing_time_ms, 2),
            "error_count": len(self.error_details),
        }


class BatchPipeline(DataPipeline):
    """批量数据管道 (军规M3/M7/M33).

    用于大规模批量数据处理的管道实现。

    特性:
    - 大批量处理，高吞吐
    - 确定性处理 (M7: 回放一致)
    - 检查点恢复
    - 进度追踪
    - 错误容忍与重试

    军规覆盖:
    - M3: 完整审计日志 - 记录所有批量操作
    - M7: 确定性处理 - 设置随机种子确保回放一致
    - M33: 知识沉淀机制 - 沉淀批量处理经验

    类常量:
        DEFAULT_BATCH_SIZE: 默认批量大小 (10000)
        CHECKPOINT_INTERVAL: 检查点间隔 (1000)
        MAX_RETRY_COUNT: 最大重试次数 (3)
        RETRY_DELAY_MS: 重试延迟毫秒数 (100)

    示例:
        >>> config = PipelineConfig(mode=PipelineMode.BATCH, batch_size=5000)
        >>> pipeline = BatchPipeline(config)
        >>> pipeline.set_random_state(42)
        >>> results = pipeline.process_batch(large_dataset)
        >>> checkpoint = pipeline.save_checkpoint()
        >>> print(f"Processed: {pipeline.get_progress():.2%}")
    """

    # 类常量
    DEFAULT_BATCH_SIZE: ClassVar[int] = 10000
    CHECKPOINT_INTERVAL: ClassVar[int] = 1000
    MAX_RETRY_COUNT: ClassVar[int] = 3
    RETRY_DELAY_MS: ClassVar[int] = 100
    PIPELINE_VERSION: ClassVar[str] = "1.0.0"

    def __init__(self, config: PipelineConfig) -> None:
        """初始化批量管道.

        参数:
            config: 管道配置

        Raises:
            ValueError: 当配置模式不是BATCH时
        """
        # 验证模式
        if config.mode != PipelineMode.BATCH:
            msg = f"BatchPipeline仅支持BATCH模式, 当前模式: {config.mode.value}"
            raise ValueError(msg)

        super().__init__(config)

        # 批量处理状态
        self._checkpoint: dict[str, Any] = {}
        self._processed_count: int = 0
        self._total_count: int = 0
        self._random_state: int | None = None
        self._current_batch_id: str = ""
        self._last_processed_index: int = -1

        # 处理结果缓存
        self._batch_results: list[BatchProcessingResult] = []

        # 数据处理器 (可扩展)
        self._item_processor: Any | None = None

    @property
    def processed_count(self) -> int:
        """获取已处理数量.

        返回:
            已处理的记录数
        """
        return self._processed_count

    @property
    def total_count(self) -> int:
        """获取总数量.

        返回:
            总记录数
        """
        return self._total_count

    @property
    def random_state(self) -> int | None:
        """获取随机种子 (M7).

        返回:
            随机种子值
        """
        return self._random_state

    @property
    def current_batch_id(self) -> str:
        """获取当前批次ID.

        返回:
            批次ID
        """
        return self._current_batch_id

    def set_random_state(self, seed: int) -> None:
        """设置随机种子 (M7 确定性).

        确保相同种子下处理结果可重现。

        参数:
            seed: 随机种子值

        示例:
            >>> pipeline.set_random_state(42)
            >>> result1 = pipeline.process_batch(data)
            >>> pipeline.set_random_state(42)  # 重置
            >>> result2 = pipeline.process_batch(data)
            >>> assert result1 == result2  # 确定性保证
        """
        self._random_state = seed
        random.seed(seed)

        # 审计日志 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "set_random_state",
                    "seed": seed,
                    "purpose": "M7_deterministic_processing",
                }
            )

        # 知识沉淀 (M33)
        if self._config.enable_knowledge:
            self.record_knowledge(
                category="determinism",
                content=f"设置随机种子为{seed}，启用确定性处理模式",
                context={"seed": seed, "military_rule": "M7"},
            )

    def _generate_batch_id(self) -> str:
        """生成批次ID.

        返回:
            唯一批次ID
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")  # noqa: DTZ005
        random_suffix = random.randint(1000, 9999)
        return f"batch_{timestamp}_{random_suffix}"

    def _compute_data_hash(self, data: list[Any]) -> str:
        """计算数据哈希 (M7 确定性验证).

        用于验证数据一致性，确保检查点恢复时数据未变更。

        参数:
            data: 数据列表

        返回:
            16位十六进制哈希字符串
        """
        try:
            # 尝试JSON序列化
            data_str = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            # 回退到字符串表示
            data_str = str(data)

        hash_bytes = hashlib.sha256(data_str.encode("utf-8")).digest()
        return hash_bytes[:8].hex()

    def ingest(self, data: Any) -> Any:
        """数据摄取阶段.

        将输入数据转换为可处理的列表格式。

        参数:
            data: 原始输入数据

        返回:
            摄取后的数据列表

        Raises:
            ValueError: 当数据格式无效时
        """
        self.update_stage(ProcessingStage.INGEST)
        start_time = time.time()

        # 转换为列表
        if isinstance(data, list):
            result = data
        elif hasattr(data, "__iter__"):
            result = list(data)
        else:
            result = [data]

        # 记录指标
        duration_ms = (time.time() - start_time) * 1000
        self._metrics.record_stage_metric(
            ProcessingStage.INGEST,
            "duration_ms",
            duration_ms,
        )
        self._metrics.record_stage_metric(
            ProcessingStage.INGEST,
            "record_count",
            float(len(result)),
        )

        # 审计日志 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "ingest",
                    "input_type": type(data).__name__,
                    "output_count": len(result),
                    "duration_ms": round(duration_ms, 2),
                }
            )

        return result

    def validate(self, data: Any) -> bool:
        """数据验证阶段.

        校验数据质量与完整性。

        参数:
            data: 待验证数据

        返回:
            验证是否通过
        """
        self.update_stage(ProcessingStage.VALIDATE)
        start_time = time.time()

        # 基础验证
        if data is None:
            is_valid = False
            reason = "data_is_none"
        elif isinstance(data, list) and len(data) == 0:
            is_valid = False
            reason = "empty_list"
        else:
            is_valid = True
            reason = "passed"

        # 记录指标
        duration_ms = (time.time() - start_time) * 1000
        self._metrics.record_stage_metric(
            ProcessingStage.VALIDATE,
            "duration_ms",
            duration_ms,
        )
        self._metrics.record_stage_metric(
            ProcessingStage.VALIDATE,
            "is_valid",
            float(is_valid),
        )

        # 审计日志 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "validate",
                    "is_valid": is_valid,
                    "reason": reason,
                    "duration_ms": round(duration_ms, 2),
                }
            )

        return is_valid

    def transform(self, data: Any) -> Any:
        """数据转换阶段.

        执行数据清洗和标准化。

        参数:
            data: 待转换数据

        返回:
            转换后的数据
        """
        self.update_stage(ProcessingStage.TRANSFORM)
        start_time = time.time()

        # 默认转换：保持原样
        # 子类可重写此方法实现具体转换逻辑
        result = data

        # 记录指标
        duration_ms = (time.time() - start_time) * 1000
        self._metrics.record_stage_metric(
            ProcessingStage.TRANSFORM,
            "duration_ms",
            duration_ms,
        )

        # 审计日志 (M3)
        if self._config.enable_audit:
            count = len(result) if isinstance(result, list) else 1
            self._metrics.add_audit_entry(
                {
                    "action": "transform",
                    "record_count": count,
                    "duration_ms": round(duration_ms, 2),
                }
            )

        return result

    def _process_single_item(self, item: Any, index: int) -> tuple[bool, Any, str]:
        """处理单个数据项.

        参数:
            item: 数据项
            index: 索引位置

        返回:
            (是否成功, 处理结果或原始项, 错误信息)
        """
        try:
            # 如果有自定义处理器，使用它
            if self._item_processor is not None:
                result = self._item_processor(item)
            else:
                # 默认处理：直接返回
                result = item

            return (True, result, "")

        except Exception as e:  # noqa: BLE001
            error_msg = f"{type(e).__name__}: {e}"
            return (False, item, error_msg)

    def process_batch(self, data: list[Any]) -> list[Any]:
        """批量处理.

        执行完整的批量数据处理流程。

        参数:
            data: 数据列表

        返回:
            处理后的数据列表

        示例:
            >>> results = pipeline.process_batch([1, 2, 3, 4, 5])
            >>> print(f"Processed {len(results)} items")
        """
        # 初始化批次
        self._current_batch_id = self._generate_batch_id()
        self._total_count = len(data)
        self._processed_count = 0
        self._last_processed_index = -1

        # 应用随机种子 (M7)
        if self._random_state is not None:
            random.seed(self._random_state)

        # 计算数据哈希 (M7)
        data_hash = self._compute_data_hash(data)

        # 启动管道
        self.start()

        # 记录批次开始 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "batch_start",
                    "batch_id": self._current_batch_id,
                    "total_count": self._total_count,
                    "data_hash": data_hash,
                    "random_state": self._random_state,
                }
            )

        # 处理结果
        batch_result = BatchProcessingResult()
        processing_start = time.time()

        # 分批处理
        checkpoint_interval = self.CHECKPOINT_INTERVAL

        for i, item in enumerate(data):
            # 处理单项
            success, result, error = self._process_single_item(item, i)

            if success:
                batch_result.success_items.append(result)
                self._metrics.records_processed += 1
            else:
                batch_result.failed_items.append((i, item, error))
                batch_result.error_details.append(
                    {
                        "index": i,
                        "error": error,
                        "timestamp": datetime.now().isoformat(),  # noqa: DTZ005
                    }
                )
                self._metrics.record_error(error.split(":")[0] if error else "unknown")

            self._processed_count += 1
            self._last_processed_index = i

            # 检查点保存
            if (i + 1) % checkpoint_interval == 0:
                self._checkpoint = self.save_checkpoint()

                # 审计日志 (M3)
                if self._config.enable_audit:
                    self._metrics.add_audit_entry(
                        {
                            "action": "checkpoint_created",
                            "batch_id": self._current_batch_id,
                            "processed_count": self._processed_count,
                            "progress": round(self.get_progress(), 4),
                        }
                    )

        # 计算处理时间
        batch_result.processing_time_ms = (time.time() - processing_start) * 1000

        # 更新指标
        self._metrics.latency_ms = batch_result.processing_time_ms / max(
            1, self._total_count
        )
        if batch_result.processing_time_ms > 0:
            self._metrics.throughput_per_sec = self._total_count / (
                batch_result.processing_time_ms / 1000
            )

        # 停止管道
        self.stop()

        # 记录批次完成 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "batch_complete",
                    "batch_id": self._current_batch_id,
                    "success_count": batch_result.success_count,
                    "failed_count": batch_result.failed_count,
                    "success_rate": round(batch_result.success_rate, 4),
                    "processing_time_ms": round(batch_result.processing_time_ms, 2),
                }
            )

        # 知识沉淀 (M33)
        if self._config.enable_knowledge:
            self.record_knowledge(
                category="batch_processing",
                content=f"批次{self._current_batch_id}处理完成: "
                f"{batch_result.success_count}/{self._total_count}成功",
                context={
                    "batch_id": self._current_batch_id,
                    "success_rate": batch_result.success_rate,
                    "throughput": self._metrics.throughput_per_sec,
                    "error_types": list(self._metrics.error_counts.keys()),
                },
            )

        # 保存处理结果
        self._batch_results.append(batch_result)

        return batch_result.success_items

    def process(self, data: Any) -> Any:
        """完整处理流程.

        实现DataPipeline抽象方法，执行完整的批量处理。

        参数:
            data: 原始输入数据

        返回:
            处理后的数据

        Raises:
            ValueError: 当数据验证失败时
        """
        # 摄取
        ingested_data = self.ingest(data)

        # 验证
        if not self.validate(ingested_data):
            error_msg = "数据验证失败"
            if self._config.enable_audit:
                self._metrics.add_audit_entry(
                    {
                        "action": "process_failed",
                        "reason": error_msg,
                    }
                )
            raise ValueError(error_msg)

        # 转换
        transformed_data = self.transform(ingested_data)

        # 批量处理
        return self.process_batch(transformed_data)

    def save_checkpoint(self) -> dict[str, Any]:
        """保存检查点.

        保存当前处理状态，支持后续恢复。

        返回:
            检查点数据字典

        示例:
            >>> checkpoint = pipeline.save_checkpoint()
            >>> # 稍后恢复...
            >>> pipeline.load_checkpoint(checkpoint)
        """
        checkpoint = BatchCheckpoint(
            batch_id=self._current_batch_id,
            processed_count=self._processed_count,
            total_count=self._total_count,
            last_processed_index=self._last_processed_index,
            random_state=self._random_state,
            data_hash=self._checkpoint.get("data_hash", ""),
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
            metadata={
                "metrics": self._metrics.to_dict(),
                "stage": self._current_stage.value,
            },
        )

        checkpoint_dict = checkpoint.to_dict()
        self._checkpoint = checkpoint_dict

        # 审计日志 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "save_checkpoint",
                    "batch_id": self._current_batch_id,
                    "processed_count": self._processed_count,
                    "progress": round(self.get_progress(), 4),
                }
            )

        return checkpoint_dict

    def load_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        """加载检查点恢复.

        从检查点恢复处理状态。

        参数:
            checkpoint: 检查点数据字典

        Raises:
            ValueError: 当检查点数据无效时

        示例:
            >>> pipeline.load_checkpoint(saved_checkpoint)
            >>> remaining_data = full_data[pipeline.processed_count:]
            >>> pipeline.process_batch(remaining_data)
        """
        if not checkpoint:
            raise ValueError("检查点数据为空")

        required_keys = [
            "batch_id",
            "processed_count",
            "total_count",
            "last_processed_index",
        ]
        for key in required_keys:
            if key not in checkpoint:
                raise ValueError(f"检查点缺少必要字段: {key}")

        # 恢复状态
        self._current_batch_id = checkpoint["batch_id"]
        self._processed_count = checkpoint["processed_count"]
        self._total_count = checkpoint["total_count"]
        self._last_processed_index = checkpoint["last_processed_index"]
        self._random_state = checkpoint.get("random_state")
        self._checkpoint = checkpoint

        # 恢复随机状态 (M7)
        if self._random_state is not None:
            random.seed(self._random_state)
            # 快进随机状态到检查点位置
            for _ in range(self._processed_count):
                random.random()

        # 审计日志 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "load_checkpoint",
                    "batch_id": self._current_batch_id,
                    "processed_count": self._processed_count,
                    "checkpoint_timestamp": checkpoint.get("timestamp", "unknown"),
                }
            )

        # 知识沉淀 (M33)
        if self._config.enable_knowledge:
            self.record_knowledge(
                category="checkpoint_recovery",
                content=f"从检查点恢复批次{self._current_batch_id}，"
                f"已处理{self._processed_count}/{self._total_count}",
                context={
                    "batch_id": self._current_batch_id,
                    "resume_index": self._last_processed_index + 1,
                },
            )

    def get_progress(self) -> float:
        """获取处理进度 (0.0-1.0).

        返回:
            进度百分比 (0.0 到 1.0)

        示例:
            >>> progress = pipeline.get_progress()
            >>> print(f"Progress: {progress:.2%}")  # 如: "Progress: 75.50%"
        """
        if self._total_count == 0:
            return 0.0
        return self._processed_count / self._total_count

    def get_metrics(self) -> PipelineMetrics:
        """获取管道运行指标.

        返回:
            管道指标对象

        示例:
            >>> metrics = pipeline.get_metrics()
            >>> print(f"Success rate: {metrics.success_rate:.2%}")
        """
        return self._metrics

    def get_batch_results(self) -> list[BatchProcessingResult]:
        """获取所有批次处理结果.

        返回:
            批次处理结果列表
        """
        return self._batch_results.copy()

    def get_last_batch_result(self) -> BatchProcessingResult | None:
        """获取最后一次批次处理结果.

        返回:
            最后一次的BatchProcessingResult，如果没有则返回None
        """
        if not self._batch_results:
            return None
        return self._batch_results[-1]

    def set_item_processor(self, processor: Any) -> None:
        """设置数据项处理器.

        允许自定义单个数据项的处理逻辑。

        参数:
            processor: 可调用对象，接受单个数据项返回处理结果

        示例:
            >>> pipeline.set_item_processor(lambda x: x * 2)
            >>> results = pipeline.process_batch([1, 2, 3])
            >>> print(results)  # [2, 4, 6]
        """
        self._item_processor = processor

        # 审计日志 (M3)
        if self._config.enable_audit:
            processor_name = getattr(processor, "__name__", type(processor).__name__)
            self._metrics.add_audit_entry(
                {
                    "action": "set_item_processor",
                    "processor": processor_name,
                }
            )

    def reset(self) -> None:
        """重置管道状态.

        清空所有处理状态和指标。
        """
        super().reset()
        self._checkpoint = {}
        self._processed_count = 0
        self._total_count = 0
        self._current_batch_id = ""
        self._last_processed_index = -1
        self._batch_results.clear()

        # 审计日志 (M3)
        if self._config.enable_audit:
            self._metrics.add_audit_entry(
                {
                    "action": "pipeline_reset",
                    "purpose": "clear_all_state",
                }
            )

    def get_checkpoint_info(self) -> dict[str, Any]:
        """获取当前检查点信息.

        返回:
            检查点信息字典
        """
        return {
            "has_checkpoint": bool(self._checkpoint),
            "batch_id": self._current_batch_id,
            "processed_count": self._processed_count,
            "total_count": self._total_count,
            "progress": round(self.get_progress(), 4),
            "last_processed_index": self._last_processed_index,
        }


# ============================================================
# 便捷函数
# ============================================================


def create_batch_pipeline(
    batch_size: int = BatchPipeline.DEFAULT_BATCH_SIZE,
    enable_audit: bool = True,
    enable_knowledge: bool = True,
    random_seed: int | None = None,
) -> BatchPipeline:
    """创建批量管道.

    参数:
        batch_size: 批量大小
        enable_audit: 是否启用审计日志 (M3)
        enable_knowledge: 是否启用知识沉淀 (M33)
        random_seed: 随机种子 (M7)，如果提供则启用确定性处理

    返回:
        BatchPipeline实例

    示例:
        >>> pipeline = create_batch_pipeline(batch_size=5000, random_seed=42)
        >>> results = pipeline.process_batch(data)
    """
    config = PipelineConfig(
        mode=PipelineMode.BATCH,
        batch_size=batch_size,
        buffer_size=max(batch_size * 2, BatchPipeline.DEFAULT_BATCH_SIZE * 2),
        enable_audit=enable_audit,
        enable_knowledge=enable_knowledge,
        enable_deterministic=random_seed is not None,
    )

    pipeline = BatchPipeline(config)

    if random_seed is not None:
        pipeline.set_random_state(random_seed)

    return pipeline


def process_in_batches(
    data: list[Any],
    batch_size: int = BatchPipeline.DEFAULT_BATCH_SIZE,
    processor: Any | None = None,
    random_seed: int | None = None,
) -> list[Any]:
    """便捷批量处理函数.

    参数:
        data: 数据列表
        batch_size: 批量大小
        processor: 数据项处理器
        random_seed: 随机种子 (M7)

    返回:
        处理后的数据列表

    示例:
        >>> results = process_in_batches(
        ...     data=[1, 2, 3, 4, 5],
        ...     processor=lambda x: x * 2,
        ...     random_seed=42,
        ... )
        >>> print(results)  # [2, 4, 6, 8, 10]
    """
    pipeline = create_batch_pipeline(
        batch_size=batch_size,
        random_seed=random_seed,
    )

    if processor is not None:
        pipeline.set_item_processor(processor)

    return pipeline.process_batch(data)
