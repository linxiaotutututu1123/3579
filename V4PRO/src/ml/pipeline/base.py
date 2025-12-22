"""
ML数据管道基础框架 - 抽象基类与核心组件 (军规级 v4.0).

V4PRO Platform Component - Phase 6.1.1 ML数据管道基础框架
V4 SPEC: SS30 数据管道设计, SS31 特征工程流水线
V4 Scenarios:
- ML.PIPELINE.REALTIME: 实时流式数据处理
- ML.PIPELINE.BATCH: 批量数据处理
- ML.PIPELINE.HYBRID: 混合模式处理
- ML.PIPELINE.INGEST: 数据摄取阶段
- ML.PIPELINE.VALIDATE: 数据验证阶段
- ML.PIPELINE.TRANSFORM: 数据转换阶段
- ML.PIPELINE.FEATURE: 特征工程阶段

军规覆盖:
- M3: 完整审计日志 - 所有管道操作必须记录审计日志
- M7: 确定性处理 - 相同输入必须产生相同输出
- M33: 知识沉淀机制 - 处理经验必须沉淀为可复用知识

功能特性:
- 管道模式定义 (实时/批量/混合)
- 数据源类型抽象 (市场/基本面/情绪/另类)
- 处理阶段划分 (摄取/验证/转换/特征/输出)
- 管道配置与指标
- 抽象基类约束

示例:
    >>> from src.ml.pipeline.base import (
    ...     DataPipeline,
    ...     PipelineConfig,
    ...     PipelineMetrics,
    ...     PipelineMode,
    ...     DataSource,
    ...     ProcessingStage,
    ... )
    >>> config = PipelineConfig(
    ...     mode=PipelineMode.BATCH,
    ...     sources=[DataSource.MARKET, DataSource.FUNDAMENTAL],
    ...     batch_size=500,
    ... )
    >>> print(config.mode)
    PipelineMode.BATCH
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar


if TYPE_CHECKING:
    from collections.abc import Callable


# ============================================================
# 枚举定义
# ============================================================


class PipelineMode(Enum):
    """管道运行模式枚举.

    定义数据管道的三种运行模式，用于控制数据处理策略。

    属性:
        REALTIME: 实时流式处理 - 低延迟，逐条处理
        BATCH: 批量处理 - 高吞吐，批次处理
        HYBRID: 混合模式 - 结合实时与批量的优势
    """

    REALTIME = "REALTIME"  # 实时流式处理
    BATCH = "BATCH"  # 批量处理
    HYBRID = "HYBRID"  # 混合模式


class DataSource(Enum):
    """数据源类型枚举.

    定义ML管道支持的数据源类型，用于数据摄取阶段。

    属性:
        MARKET: 市场数据 - 行情、成交、订单簿
        FUNDAMENTAL: 基本面数据 - 财报、估值、宏观
        SENTIMENT: 情绪数据 - 新闻、舆情、社交媒体
        ALTERNATIVE: 另类数据 - 卫星、天气、物流
    """

    MARKET = "MARKET"  # 市场数据
    FUNDAMENTAL = "FUNDAMENTAL"  # 基本面数据
    SENTIMENT = "SENTIMENT"  # 情绪数据
    ALTERNATIVE = "ALTERNATIVE"  # 另类数据


class ProcessingStage(Enum):
    """处理阶段枚举.

    定义数据管道的处理阶段，用于追踪数据处理进度。

    属性:
        INGEST: 数据摄取 - 从源系统获取原始数据
        VALIDATE: 数据验证 - 校验数据质量与完整性
        TRANSFORM: 数据转换 - 清洗、标准化、对齐
        FEATURE: 特征工程 - 特征提取与构建
        OUTPUT: 输出阶段 - 特征存储与分发
    """

    INGEST = "INGEST"  # 数据摄取
    VALIDATE = "VALIDATE"  # 数据验证
    TRANSFORM = "TRANSFORM"  # 数据转换
    FEATURE = "FEATURE"  # 特征工程
    OUTPUT = "OUTPUT"  # 输出阶段


# ============================================================
# 数据类定义
# ============================================================


@dataclass
class PipelineConfig:
    """管道配置数据类.

    定义数据管道的运行时配置参数。

    属性:
        mode: 管道运行模式 (实时/批量/混合)
        sources: 数据源列表
        batch_size: 批量处理大小 (默认1000)
        buffer_size: 缓冲区大小 (默认10000)
        enable_audit: 是否启用审计日志 (M3军规)
        enable_knowledge: 是否启用知识沉淀 (M33军规)
        enable_deterministic: 是否启用确定性处理 (M7军规)
        max_retries: 最大重试次数
        retry_delay_ms: 重试延迟毫秒数
        timeout_ms: 处理超时毫秒数
        metadata: 额外元数据

    示例:
        >>> config = PipelineConfig(
        ...     mode=PipelineMode.BATCH,
        ...     sources=[DataSource.MARKET],
        ...     batch_size=500,
        ...     enable_audit=True,
        ... )
        >>> print(config.batch_size)
        500
    """

    # 核心配置
    mode: PipelineMode
    sources: list[DataSource] = field(default_factory=list)

    # 批量处理配置
    batch_size: int = 1000
    buffer_size: int = 10000

    # 军规配置
    enable_audit: bool = True  # M3: 审计日志
    enable_knowledge: bool = True  # M33: 知识沉淀
    enable_deterministic: bool = True  # M7: 确定性处理

    # 容错配置
    max_retries: int = 3
    retry_delay_ms: int = 100
    timeout_ms: int = 30000

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """后初始化验证."""
        if self.batch_size <= 0:
            msg = f"batch_size必须为正数, 当前值: {self.batch_size}"
            raise ValueError(msg)
        if self.buffer_size <= 0:
            msg = f"buffer_size必须为正数, 当前值: {self.buffer_size}"
            raise ValueError(msg)
        if self.buffer_size < self.batch_size:
            msg = f"buffer_size({self.buffer_size})必须大于等于batch_size({self.batch_size})"
            raise ValueError(msg)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式.

        返回:
            配置字典
        """
        return {
            "mode": self.mode.value,
            "sources": [s.value for s in self.sources],
            "batch_size": self.batch_size,
            "buffer_size": self.buffer_size,
            "enable_audit": self.enable_audit,
            "enable_knowledge": self.enable_knowledge,
            "enable_deterministic": self.enable_deterministic,
            "max_retries": self.max_retries,
            "retry_delay_ms": self.retry_delay_ms,
            "timeout_ms": self.timeout_ms,
            "metadata": self.metadata,
        }

    def validate(self) -> bool:
        """验证配置有效性.

        返回:
            配置是否有效
        """
        if not self.sources:
            return False
        if self.mode not in PipelineMode:
            return False
        return True


@dataclass
class PipelineMetrics:
    """管道指标数据类.

    记录数据管道的运行时指标。

    属性:
        records_processed: 已处理记录数
        records_failed: 失败记录数
        latency_ms: 平均延迟毫秒数
        throughput_per_sec: 每秒吞吐量
        stage_metrics: 各阶段指标
        error_counts: 错误类型计数
        start_time: 开始时间
        end_time: 结束时间
        audit_log: 审计日志列表 (M3)
        knowledge_entries: 知识条目列表 (M33)

    示例:
        >>> metrics = PipelineMetrics()
        >>> metrics.records_processed = 1000
        >>> metrics.latency_ms = 5.5
        >>> print(metrics.success_rate)
        1.0
    """

    # 核心指标
    records_processed: int = 0
    records_failed: int = 0
    latency_ms: float = 0.0
    throughput_per_sec: float = 0.0

    # 阶段指标
    stage_metrics: dict[ProcessingStage, dict[str, float]] = field(default_factory=dict)

    # 错误统计
    error_counts: dict[str, int] = field(default_factory=dict)

    # 时间记录
    start_time: str = ""
    end_time: str = ""

    # 军规相关
    audit_log: list[dict[str, Any]] = field(default_factory=list)  # M3
    knowledge_entries: list[dict[str, Any]] = field(default_factory=list)  # M33

    @property
    def success_rate(self) -> float:
        """计算成功率.

        返回:
            成功率 (0.0-1.0)
        """
        total = self.records_processed + self.records_failed
        if total == 0:
            return 0.0
        return self.records_processed / total

    @property
    def total_records(self) -> int:
        """获取总记录数.

        返回:
            总记录数
        """
        return self.records_processed + self.records_failed

    @property
    def duration_ms(self) -> float:
        """计算处理时长.

        返回:
            处理时长毫秒数
        """
        if not self.start_time or not self.end_time:
            return 0.0
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds() * 1000
        except (ValueError, TypeError):
            return 0.0

    def record_stage_metric(
        self,
        stage: ProcessingStage,
        metric_name: str,
        value: float,
    ) -> None:
        """记录阶段指标.

        参数:
            stage: 处理阶段
            metric_name: 指标名称
            value: 指标值
        """
        if stage not in self.stage_metrics:
            self.stage_metrics[stage] = {}
        self.stage_metrics[stage][metric_name] = value

    def record_error(self, error_type: str) -> None:
        """记录错误.

        参数:
            error_type: 错误类型
        """
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        self.records_failed += 1

    def add_audit_entry(self, entry: dict[str, Any]) -> None:
        """添加审计日志条目 (M3).

        参数:
            entry: 审计日志条目
        """
        entry["timestamp"] = datetime.now().isoformat()  # noqa: DTZ005
        self.audit_log.append(entry)

    def add_knowledge_entry(self, entry: dict[str, Any]) -> None:
        """添加知识条目 (M33).

        参数:
            entry: 知识条目
        """
        entry["timestamp"] = datetime.now().isoformat()  # noqa: DTZ005
        self.knowledge_entries.append(entry)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式.

        返回:
            指标字典
        """
        return {
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "success_rate": round(self.success_rate, 4),
            "latency_ms": round(self.latency_ms, 2),
            "throughput_per_sec": round(self.throughput_per_sec, 2),
            "duration_ms": round(self.duration_ms, 2),
            "stage_metrics": {
                stage.value: metrics
                for stage, metrics in self.stage_metrics.items()
            },
            "error_counts": self.error_counts,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "audit_log_count": len(self.audit_log),
            "knowledge_entries_count": len(self.knowledge_entries),
        }

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式 (军规 M3).

        返回:
            符合审计要求的字典
        """
        return {
            "records_processed": self.records_processed,
            "records_failed": self.records_failed,
            "success_rate": round(self.success_rate, 4),
            "latency_ms": round(self.latency_ms, 2),
            "throughput_per_sec": round(self.throughput_per_sec, 2),
            "error_counts": self.error_counts,
            "audit_log": self.audit_log,
        }

    def reset(self) -> None:
        """重置所有指标."""
        self.records_processed = 0
        self.records_failed = 0
        self.latency_ms = 0.0
        self.throughput_per_sec = 0.0
        self.stage_metrics.clear()
        self.error_counts.clear()
        self.start_time = ""
        self.end_time = ""
        self.audit_log.clear()
        self.knowledge_entries.clear()


# ============================================================
# 抽象基类定义
# ============================================================


class DataPipeline(ABC):
    """数据管道抽象基类 (军规 M3/M7/M33).

    定义数据管道的核心接口，所有具体管道实现必须继承此类。

    军规覆盖:
    - M3: 完整审计日志 - 所有操作记录审计轨迹
    - M7: 确定性处理 - 保证相同输入产生相同输出
    - M33: 知识沉淀机制 - 处理经验转化为可复用知识

    核心方法:
    - ingest: 数据摄取
    - validate: 数据验证
    - transform: 数据转换
    - process: 完整处理流程
    - get_metrics: 获取运行指标

    类变量:
        PIPELINE_VERSION: 管道版本
        SUPPORTED_MODES: 支持的运行模式
        DEFAULT_BATCH_SIZE: 默认批量大小
        DEFAULT_BUFFER_SIZE: 默认缓冲区大小

    示例:
        >>> class MarketDataPipeline(DataPipeline):
        ...     def ingest(self, data: Any) -> Any:
        ...         return data
        ...     def validate(self, data: Any) -> bool:
        ...         return data is not None
        ...     def transform(self, data: Any) -> Any:
        ...         return data
        ...     def process(self, data: Any) -> Any:
        ...         ingested = self.ingest(data)
        ...         if self.validate(ingested):
        ...             return self.transform(ingested)
        ...         return None
        ...     def get_metrics(self) -> PipelineMetrics:
        ...         return PipelineMetrics()
    """

    # 类常量
    PIPELINE_VERSION: ClassVar[str] = "1.0.0"
    SUPPORTED_MODES: ClassVar[tuple[PipelineMode, ...]] = (
        PipelineMode.REALTIME,
        PipelineMode.BATCH,
        PipelineMode.HYBRID,
    )
    DEFAULT_BATCH_SIZE: ClassVar[int] = 1000
    DEFAULT_BUFFER_SIZE: ClassVar[int] = 10000

    # 阶段顺序
    STAGE_ORDER: ClassVar[tuple[ProcessingStage, ...]] = (
        ProcessingStage.INGEST,
        ProcessingStage.VALIDATE,
        ProcessingStage.TRANSFORM,
        ProcessingStage.FEATURE,
        ProcessingStage.OUTPUT,
    )

    def __init__(self, config: PipelineConfig | None = None) -> None:
        """初始化数据管道.

        参数:
            config: 管道配置，如果为None则使用默认配置
        """
        self._config = config or PipelineConfig(
            mode=PipelineMode.BATCH,
            sources=[DataSource.MARKET],
        )
        self._metrics = PipelineMetrics()
        self._current_stage = ProcessingStage.INGEST
        self._is_running = False
        self._processing_count = 0

    @property
    def config(self) -> PipelineConfig:
        """获取管道配置.

        返回:
            管道配置对象
        """
        return self._config

    @property
    def current_stage(self) -> ProcessingStage:
        """获取当前处理阶段.

        返回:
            当前处理阶段
        """
        return self._current_stage

    @property
    def is_running(self) -> bool:
        """获取运行状态.

        返回:
            是否正在运行
        """
        return self._is_running

    @property
    def processing_count(self) -> int:
        """获取处理次数.

        返回:
            处理次数
        """
        return self._processing_count

    @abstractmethod
    def ingest(self, data: Any) -> Any:
        """数据摄取阶段.

        从源系统获取原始数据并进行初步处理。

        参数:
            data: 原始输入数据

        返回:
            摄取后的数据

        Raises:
            ValueError: 当数据格式无效时
            RuntimeError: 当摄取过程失败时

        示例:
            >>> ingested = pipeline.ingest(raw_data)
        """
        ...

    @abstractmethod
    def validate(self, data: Any) -> bool:
        """数据验证阶段.

        校验数据质量、完整性和一致性。

        参数:
            data: 待验证数据

        返回:
            验证是否通过

        示例:
            >>> is_valid = pipeline.validate(data)
            >>> if not is_valid:
            ...     raise ValueError("数据验证失败")
        """
        ...

    @abstractmethod
    def transform(self, data: Any) -> Any:
        """数据转换阶段.

        执行数据清洗、标准化和对齐操作。

        参数:
            data: 待转换数据

        返回:
            转换后的数据

        Raises:
            ValueError: 当转换失败时

        示例:
            >>> transformed = pipeline.transform(validated_data)
        """
        ...

    @abstractmethod
    def process(self, data: Any) -> Any:
        """完整处理流程.

        执行从摄取到输出的完整数据处理流程。

        参数:
            data: 原始输入数据

        返回:
            处理后的数据

        Raises:
            ValueError: 当处理过程中数据无效时
            RuntimeError: 当处理过程失败时

        示例:
            >>> result = pipeline.process(raw_data)
        """
        ...

    @abstractmethod
    def get_metrics(self) -> PipelineMetrics:
        """获取管道运行指标.

        返回:
            管道指标对象

        示例:
            >>> metrics = pipeline.get_metrics()
            >>> print(metrics.success_rate)
        """
        ...

    def start(self) -> None:
        """启动管道.

        记录启动时间并设置运行状态。
        """
        self._is_running = True
        self._metrics.start_time = datetime.now().isoformat()  # noqa: DTZ005
        self._current_stage = ProcessingStage.INGEST

        if self._config.enable_audit:
            self._metrics.add_audit_entry({
                "action": "pipeline_start",
                "mode": self._config.mode.value,
                "sources": [s.value for s in self._config.sources],
            })

    def stop(self) -> None:
        """停止管道.

        记录结束时间并更新运行状态。
        """
        self._is_running = False
        self._metrics.end_time = datetime.now().isoformat()  # noqa: DTZ005

        if self._config.enable_audit:
            self._metrics.add_audit_entry({
                "action": "pipeline_stop",
                "records_processed": self._metrics.records_processed,
                "records_failed": self._metrics.records_failed,
                "success_rate": self._metrics.success_rate,
            })

    def reset(self) -> None:
        """重置管道状态.

        清空指标并重置阶段状态。
        """
        self._metrics.reset()
        self._current_stage = ProcessingStage.INGEST
        self._is_running = False
        self._processing_count = 0

    def update_stage(self, stage: ProcessingStage) -> None:
        """更新当前处理阶段.

        参数:
            stage: 新的处理阶段

        Raises:
            ValueError: 当阶段跳跃无效时
        """
        current_idx = self.STAGE_ORDER.index(self._current_stage)
        new_idx = self.STAGE_ORDER.index(stage)

        # 允许向前推进或回到起点
        if new_idx < current_idx and stage != ProcessingStage.INGEST:
            msg = f"不允许从{self._current_stage.value}回退到{stage.value}"
            raise ValueError(msg)

        self._current_stage = stage

        if self._config.enable_audit:
            self._metrics.add_audit_entry({
                "action": "stage_update",
                "from_stage": self.STAGE_ORDER[current_idx].value,
                "to_stage": stage.value,
            })

    def record_knowledge(
        self,
        category: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        """记录知识条目 (M33).

        将处理经验沉淀为可复用知识。

        参数:
            category: 知识类别
            content: 知识内容
            context: 上下文信息
        """
        if not self._config.enable_knowledge:
            return

        self._metrics.add_knowledge_entry({
            "category": category,
            "content": content,
            "context": context or {},
            "stage": self._current_stage.value,
            "processing_count": self._processing_count,
        })

    def get_audit_log(self) -> list[dict[str, Any]]:
        """获取审计日志 (M3).

        返回:
            审计日志列表
        """
        return self._metrics.audit_log.copy()

    def get_knowledge_entries(self) -> list[dict[str, Any]]:
        """获取知识条目 (M33).

        返回:
            知识条目列表
        """
        return self._metrics.knowledge_entries.copy()


# ============================================================
# 便捷函数
# ============================================================


def create_pipeline_config(
    mode: PipelineMode = PipelineMode.BATCH,
    sources: list[DataSource] | None = None,
    batch_size: int = 1000,
    buffer_size: int = 10000,
    enable_audit: bool = True,
    enable_knowledge: bool = True,
) -> PipelineConfig:
    """创建管道配置.

    参数:
        mode: 管道运行模式
        sources: 数据源列表
        batch_size: 批量处理大小
        buffer_size: 缓冲区大小
        enable_audit: 是否启用审计日志 (M3)
        enable_knowledge: 是否启用知识沉淀 (M33)

    返回:
        PipelineConfig实例

    示例:
        >>> config = create_pipeline_config(
        ...     mode=PipelineMode.REALTIME,
        ...     sources=[DataSource.MARKET],
        ... )
    """
    return PipelineConfig(
        mode=mode,
        sources=sources or [DataSource.MARKET],
        batch_size=batch_size,
        buffer_size=buffer_size,
        enable_audit=enable_audit,
        enable_knowledge=enable_knowledge,
    )


def get_stage_name(stage: ProcessingStage) -> str:
    """获取阶段显示名称.

    参数:
        stage: 处理阶段

    返回:
        阶段显示名称
    """
    stage_names = {
        ProcessingStage.INGEST: "数据摄取",
        ProcessingStage.VALIDATE: "数据验证",
        ProcessingStage.TRANSFORM: "数据转换",
        ProcessingStage.FEATURE: "特征工程",
        ProcessingStage.OUTPUT: "输出阶段",
    }
    return stage_names.get(stage, stage.value)


def get_mode_description(mode: PipelineMode) -> str:
    """获取模式描述.

    参数:
        mode: 管道模式

    返回:
        模式描述字符串
    """
    mode_descriptions = {
        PipelineMode.REALTIME: "实时流式处理 - 低延迟，逐条处理",
        PipelineMode.BATCH: "批量处理 - 高吞吐，批次处理",
        PipelineMode.HYBRID: "混合模式 - 结合实时与批量优势",
    }
    return mode_descriptions.get(mode, mode.value)


def get_source_description(source: DataSource) -> str:
    """获取数据源描述.

    参数:
        source: 数据源类型

    返回:
        数据源描述字符串
    """
    source_descriptions = {
        DataSource.MARKET: "市场数据 - 行情、成交、订单簿",
        DataSource.FUNDAMENTAL: "基本面数据 - 财报、估值、宏观",
        DataSource.SENTIMENT: "情绪数据 - 新闻、舆情、社交媒体",
        DataSource.ALTERNATIVE: "另类数据 - 卫星、天气、物流",
    }
    return source_descriptions.get(source, source.value)
