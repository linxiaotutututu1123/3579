"""
知识库基类模块 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

核心架构:
- KnowledgeEntry: 知识条目基类
- KnowledgeStore: 知识存储抽象基类
- KnowledgeType: 知识类型枚举
- KnowledgePriority: 知识优先级

军规覆盖:
- M33: 知识沉淀机制
- M3: 审计日志完整
- M7: 场景回放支持
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Generic, TypeVar


class KnowledgeType(Enum):
    """知识类型枚举.

    定义系统支持的知识类型:
    - REFLEXION: 反思经验知识
    - PATTERN: 市场模式知识
    - DECISION: 决策历史知识
    - FAULT: 故障预防知识
    - STRATEGY: 策略优化知识
    - RISK: 风控增强知识
    """

    REFLEXION = auto()  # 反思记忆
    PATTERN = auto()  # 市场模式
    DECISION = auto()  # 决策日志
    FAULT = auto()  # 故障预防
    STRATEGY = auto()  # 策略优化
    RISK = auto()  # 风控增强


class KnowledgePriority(Enum):
    """知识优先级枚举.

    用于知识检索和融合时的权重计算:
    - CRITICAL: 关键知识 (权重 1.0)
    - HIGH: 高优先级 (权重 0.8)
    - MEDIUM: 中优先级 (权重 0.5)
    - LOW: 低优先级 (权重 0.2)
    """

    CRITICAL = 4  # 关键 (1.0)
    HIGH = 3  # 高 (0.8)
    MEDIUM = 2  # 中 (0.5)
    LOW = 1  # 低 (0.2)

    @property
    def weight(self) -> float:
        """获取优先级权重."""
        weights = {
            KnowledgePriority.CRITICAL: 1.0,
            KnowledgePriority.HIGH: 0.8,
            KnowledgePriority.MEDIUM: 0.5,
            KnowledgePriority.LOW: 0.2,
        }
        return weights[self]


class StorageTier(Enum):
    """存储层级枚举.

    分层存储方案:
    - HOT: 热数据 (Redis) - 最近7天
    - WARM: 温数据 (SQLite) - 7-90天
    - COLD: 冷数据 (File) - 90天以上
    """

    HOT = "hot"  # Redis, 7天内
    WARM = "warm"  # SQLite, 7-90天
    COLD = "cold"  # File, 90天+


# 热温冷数据阈值 (秒)
STORAGE_TIER_THRESHOLDS = {
    StorageTier.HOT: 7 * 24 * 3600,  # 7天
    StorageTier.WARM: 90 * 24 * 3600,  # 90天
    StorageTier.COLD: float("inf"),  # 永久
}


@dataclass
class KnowledgeEntry:
    """知识条目基类.

    所有知识条目的基础数据结构，包含:
    - 唯一标识
    - 类型和优先级
    - 创建和访问时间戳
    - 内容和元数据
    - 版本控制

    Attributes:
        id: 唯一标识符 (UUID)
        knowledge_type: 知识类型
        priority: 优先级
        created_at: 创建时间戳
        updated_at: 更新时间戳
        accessed_at: 最后访问时间戳
        access_count: 访问计数
        content: 知识内容
        metadata: 元数据
        tags: 标签列表
        version: 版本号
        content_hash: 内容哈希
        run_id: 关联的运行 ID (用于回放)
        source: 知识来源
    """

    id: str
    knowledge_type: KnowledgeType
    priority: KnowledgePriority
    created_at: float
    updated_at: float
    accessed_at: float
    access_count: int
    content: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    version: int = 1
    content_hash: str = ""
    run_id: str = ""
    source: str = ""

    def __post_init__(self) -> None:
        """初始化后计算内容哈希."""
        if not self.content_hash:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """计算内容哈希.

        Returns:
            16位十六进制哈希字符串
        """
        sorted_json = json.dumps(self.content, sort_keys=True, ensure_ascii=False)
        hash_bytes = hashlib.sha256(sorted_json.encode("utf-8")).digest()
        return hash_bytes[:8].hex()

    @property
    def age_seconds(self) -> float:
        """获取知识条目年龄 (秒)."""
        return time.time() - self.created_at

    @property
    def storage_tier(self) -> StorageTier:
        """根据年龄确定存储层级."""
        age = self.age_seconds
        if age < STORAGE_TIER_THRESHOLDS[StorageTier.HOT]:
            return StorageTier.HOT
        if age < STORAGE_TIER_THRESHOLDS[StorageTier.WARM]:
            return StorageTier.WARM
        return StorageTier.COLD

    def touch(self) -> None:
        """更新访问时间和计数."""
        self.accessed_at = time.time()
        self.access_count += 1

    def update_content(self, new_content: dict[str, Any]) -> None:
        """更新内容并增加版本号.

        Args:
            new_content: 新的内容字典
        """
        self.content = new_content
        self.updated_at = time.time()
        self.version += 1
        self.content_hash = self._compute_hash()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            包含所有字段的字典
        """
        data = asdict(self)
        data["knowledge_type"] = self.knowledge_type.name
        data["priority"] = self.priority.name
        data["storage_tier"] = self.storage_tier.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeEntry:
        """从字典创建实例.

        Args:
            data: 包含知识条目数据的字典

        Returns:
            KnowledgeEntry 实例
        """
        data = data.copy()
        if isinstance(data.get("knowledge_type"), str):
            data["knowledge_type"] = KnowledgeType[data["knowledge_type"]]
        if isinstance(data.get("priority"), str):
            data["priority"] = KnowledgePriority[data["priority"]]
        # 移除存储层级 (计算属性)
        data.pop("storage_tier", None)
        return cls(**data)

    @classmethod
    def create(
        cls,
        knowledge_type: KnowledgeType,
        content: dict[str, Any],
        priority: KnowledgePriority = KnowledgePriority.MEDIUM,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        run_id: str = "",
        source: str = "",
    ) -> KnowledgeEntry:
        """创建新的知识条目.

        Args:
            knowledge_type: 知识类型
            content: 知识内容
            priority: 优先级
            tags: 标签列表
            metadata: 元数据
            run_id: 关联的运行 ID
            source: 知识来源

        Returns:
            新的 KnowledgeEntry 实例
        """
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            knowledge_type=knowledge_type,
            priority=priority,
            created_at=now,
            updated_at=now,
            accessed_at=now,
            access_count=0,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
            run_id=run_id,
            source=source,
        )


# 泛型类型变量
T = TypeVar("T", bound=KnowledgeEntry)


class KnowledgeStore(ABC, Generic[T]):
    """知识存储抽象基类.

    定义知识存储的标准接口，所有具体存储实现必须继承此类。

    支持的操作:
    - 存储/检索知识条目
    - 按类型/标签/时间范围查询
    - 批量操作
    - 统计信息

    军规要求:
    - M33: 所有操作必须支持知识沉淀
    - M3: 所有操作必须记录审计日志
    - M7: 支持场景回放
    """

    def __init__(self, name: str = "default") -> None:
        """初始化知识存储.

        Args:
            name: 存储名称
        """
        self.name = name
        self._stats = {
            "total_entries": 0,
            "total_reads": 0,
            "total_writes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    @abstractmethod
    def put(self, entry: T) -> str:
        """存储知识条目.

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, entry_id: str) -> T | None:
        """获取知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目或 None
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """删除知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        raise NotImplementedError

    @abstractmethod
    def query(
        self,
        knowledge_type: KnowledgeType | None = None,
        tags: list[str] | None = None,
        min_priority: KnowledgePriority | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """查询知识条目.

        Args:
            knowledge_type: 知识类型过滤
            tags: 标签过滤 (AND 逻辑)
            min_priority: 最低优先级
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            匹配的知识条目列表
        """
        raise NotImplementedError

    @abstractmethod
    def count(
        self,
        knowledge_type: KnowledgeType | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """统计知识条目数量.

        Args:
            knowledge_type: 知识类型过滤
            tags: 标签过滤

        Returns:
            条目数量
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> int:
        """清空所有知识条目.

        Returns:
            删除的条目数量
        """
        raise NotImplementedError

    def put_batch(self, entries: list[T]) -> list[str]:
        """批量存储知识条目.

        Args:
            entries: 知识条目列表

        Returns:
            条目 ID 列表
        """
        return [self.put(entry) for entry in entries]

    def get_batch(self, entry_ids: list[str]) -> list[T | None]:
        """批量获取知识条目.

        Args:
            entry_ids: 条目 ID 列表

        Returns:
            知识条目列表
        """
        return [self.get(entry_id) for entry_id in entry_ids]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计信息字典
        """
        return self._stats.copy()


@dataclass
class QueryContext:
    """查询上下文.

    用于构建复杂查询条件。

    Attributes:
        knowledge_types: 知识类型列表
        tags: 标签列表
        min_priority: 最低优先级
        start_time: 开始时间
        end_time: 结束时间
        content_filter: 内容过滤条件
        order_by: 排序字段
        ascending: 是否升序
        limit: 限制数量
        offset: 偏移量
    """

    knowledge_types: list[KnowledgeType] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    min_priority: KnowledgePriority | None = None
    start_time: float | None = None
    end_time: float | None = None
    content_filter: dict[str, Any] = field(default_factory=dict)
    order_by: str = "created_at"
    ascending: bool = False
    limit: int = 100
    offset: int = 0


@dataclass
class KnowledgeAuditRecord:
    """知识操作审计记录.

    记录所有知识库操作，用于:
    - M3 审计合规
    - M7 场景回放

    Attributes:
        id: 审计记录 ID
        ts: 时间戳
        operation: 操作类型 (put/get/delete/query)
        entry_id: 知识条目 ID
        knowledge_type: 知识类型
        run_id: 关联的运行 ID
        details: 操作详情
        success: 是否成功
        error_message: 错误信息
    """

    id: str
    ts: float
    operation: str
    entry_id: str
    knowledge_type: str
    run_id: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: str = ""

    @classmethod
    def create(
        cls,
        operation: str,
        entry_id: str,
        knowledge_type: str,
        run_id: str = "",
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str = "",
    ) -> KnowledgeAuditRecord:
        """创建审计记录.

        Args:
            operation: 操作类型
            entry_id: 条目 ID
            knowledge_type: 知识类型
            run_id: 运行 ID
            details: 详情
            success: 是否成功
            error_message: 错误信息

        Returns:
            审计记录实例
        """
        return cls(
            id=str(uuid.uuid4()),
            ts=time.time(),
            operation=operation,
            entry_id=entry_id,
            knowledge_type=knowledge_type,
            run_id=run_id,
            details=details or {},
            success=success,
            error_message=error_message,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return asdict(self)


def validate_knowledge_entry(entry: KnowledgeEntry) -> list[str]:
    """验证知识条目完整性.

    检查所有军规级必备字段。

    Args:
        entry: 知识条目

    Returns:
        错误列表（空列表表示验证通过）
    """
    errors: list[str] = []

    if not entry.id:
        errors.append("KNOWLEDGE.ENTRY.HAS_ID: id is missing")
    if not entry.content:
        errors.append("KNOWLEDGE.ENTRY.HAS_CONTENT: content is empty")
    if not entry.content_hash:
        errors.append("KNOWLEDGE.ENTRY.HAS_HASH: content_hash is missing")
    if entry.created_at <= 0:
        errors.append("KNOWLEDGE.ENTRY.HAS_TIMESTAMP: created_at is invalid")

    return errors
