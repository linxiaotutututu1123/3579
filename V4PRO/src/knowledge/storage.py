"""
分层存储实现 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

分层存储方案:
- HOT (热数据): Redis - 最近7天
- WARM (温数据): SQLite - 7-90天
- COLD (冷数据): File - 90天以上

军规覆盖:
- M33: 知识沉淀机制
- M3: 审计日志完整
- M7: 场景回放支持
"""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Iterator, TypeVar

from src.knowledge.base import (
    KnowledgeAuditRecord,
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeStore,
    KnowledgeType,
    StorageTier,
    STORAGE_TIER_THRESHOLDS,
)


T = TypeVar("T", bound=KnowledgeEntry)


@dataclass
class TieredStorageConfig:
    """分层存储配置.

    Attributes:
        hot_max_items: 热存储最大条目数
        hot_ttl_seconds: 热数据过期时间 (秒)
        warm_db_path: 温存储数据库路径
        cold_dir_path: 冷存储目录路径
        auto_migrate: 是否自动迁移数据
        compress_cold: 是否压缩冷数据
        audit_enabled: 是否启用审计日志
        audit_path: 审计日志路径
    """

    hot_max_items: int = 10000
    hot_ttl_seconds: int = 7 * 24 * 3600  # 7天
    warm_db_path: str = "knowledge_warm.db"
    cold_dir_path: str = "knowledge_cold"
    auto_migrate: bool = True
    compress_cold: bool = True
    audit_enabled: bool = True
    audit_path: str = "knowledge_audit.jsonl"


class HotStorage(KnowledgeStore[T]):
    """热存储实现 (内存LRU缓存).

    使用内存中的LRU缓存模拟Redis行为。
    生产环境应替换为真实的Redis客户端。

    特性:
    - O(1) 读写性能
    - LRU淘汰策略
    - TTL过期机制
    """

    def __init__(
        self,
        name: str = "hot",
        max_items: int = 10000,
        ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        """初始化热存储.

        Args:
            name: 存储名称
            max_items: 最大条目数
            ttl_seconds: 条目过期时间
        """
        super().__init__(name)
        self.max_items = max_items
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[T, float]] = OrderedDict()
        self._lock = threading.RLock()

    def _evict_expired(self) -> None:
        """淘汰过期条目."""
        now = time.time()
        expired_keys = [
            key
            for key, (_, ts) in self._cache.items()
            if now - ts > self.ttl_seconds
        ]
        for key in expired_keys:
            del self._cache[key]

    def _evict_lru(self) -> None:
        """LRU淘汰."""
        while len(self._cache) >= self.max_items:
            self._cache.popitem(last=False)

    def put(self, entry: T) -> str:
        """存储知识条目.

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        with self._lock:
            self._evict_expired()
            self._evict_lru()
            self._cache[entry.id] = (entry, time.time())
            self._cache.move_to_end(entry.id)
            self._stats["total_entries"] = len(self._cache)
            self._stats["total_writes"] += 1
        return entry.id

    def get(self, entry_id: str) -> T | None:
        """获取知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目或 None
        """
        with self._lock:
            self._stats["total_reads"] += 1
            if entry_id in self._cache:
                entry, ts = self._cache[entry_id]
                if time.time() - ts <= self.ttl_seconds:
                    self._cache.move_to_end(entry_id)
                    self._cache[entry_id] = (entry, time.time())
                    entry.touch()
                    self._stats["cache_hits"] += 1
                    return entry
                else:
                    del self._cache[entry_id]
            self._stats["cache_misses"] += 1
            return None

    def delete(self, entry_id: str) -> bool:
        """删除知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        with self._lock:
            if entry_id in self._cache:
                del self._cache[entry_id]
                self._stats["total_entries"] = len(self._cache)
                return True
            return False

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
            tags: 标签过滤
            min_priority: 最低优先级
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            匹配的知识条目列表
        """
        with self._lock:
            self._evict_expired()
            results: list[T] = []

            for entry, _ in self._cache.values():
                if knowledge_type and entry.knowledge_type != knowledge_type:
                    continue
                if tags and not all(tag in entry.tags for tag in tags):
                    continue
                if min_priority and entry.priority.value < min_priority.value:
                    continue
                if start_time and entry.created_at < start_time:
                    continue
                if end_time and entry.created_at > end_time:
                    continue
                results.append(entry)

            # 按创建时间降序排序
            results.sort(key=lambda x: x.created_at, reverse=True)
            return results[offset : offset + limit]

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
        with self._lock:
            self._evict_expired()
            if not knowledge_type and not tags:
                return len(self._cache)

            count = 0
            for entry, _ in self._cache.values():
                if knowledge_type and entry.knowledge_type != knowledge_type:
                    continue
                if tags and not all(tag in entry.tags for tag in tags):
                    continue
                count += 1
            return count

    def clear(self) -> int:
        """清空所有知识条目.

        Returns:
            删除的条目数量
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats["total_entries"] = 0
            return count

    def get_all_entries(self) -> list[T]:
        """获取所有条目 (用于迁移).

        Returns:
            所有条目列表
        """
        with self._lock:
            self._evict_expired()
            return [entry for entry, _ in self._cache.values()]


class WarmStorage(KnowledgeStore[T]):
    """温存储实现 (SQLite).

    使用SQLite存储7-90天的知识数据。

    特性:
    - 持久化存储
    - SQL查询能力
    - 事务支持
    """

    def __init__(
        self,
        name: str = "warm",
        db_path: str = "knowledge_warm.db",
    ) -> None:
        """初始化温存储.

        Args:
            name: 存储名称
            db_path: 数据库文件路径
        """
        super().__init__(name)
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """初始化数据库表."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_entries (
                    id TEXT PRIMARY KEY,
                    knowledge_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    accessed_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    version INTEGER DEFAULT 1,
                    content_hash TEXT,
                    run_id TEXT,
                    source TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_type
                ON knowledge_entries(knowledge_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON knowledge_entries(created_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority
                ON knowledge_entries(priority)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """获取数据库连接.

        Yields:
            数据库连接
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _entry_to_row(self, entry: T) -> tuple:
        """将条目转换为数据库行.

        Args:
            entry: 知识条目

        Returns:
            数据库行元组
        """
        return (
            entry.id,
            entry.knowledge_type.name,
            entry.priority.value,
            entry.created_at,
            entry.updated_at,
            entry.accessed_at,
            entry.access_count,
            json.dumps(entry.content, ensure_ascii=False),
            json.dumps(entry.metadata, ensure_ascii=False),
            json.dumps(entry.tags, ensure_ascii=False),
            entry.version,
            entry.content_hash,
            entry.run_id,
            entry.source,
        )

    def _row_to_entry(self, row: sqlite3.Row) -> KnowledgeEntry:
        """将数据库行转换为条目.

        Args:
            row: 数据库行

        Returns:
            知识条目
        """
        return KnowledgeEntry(
            id=row["id"],
            knowledge_type=KnowledgeType[row["knowledge_type"]],
            priority=KnowledgePriority(row["priority"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            accessed_at=row["accessed_at"],
            access_count=row["access_count"],
            content=json.loads(row["content"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            tags=json.loads(row["tags"]) if row["tags"] else [],
            version=row["version"],
            content_hash=row["content_hash"] or "",
            run_id=row["run_id"] or "",
            source=row["source"] or "",
        )

    def put(self, entry: T) -> str:
        """存储知识条目.

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO knowledge_entries
                    (id, knowledge_type, priority, created_at, updated_at,
                     accessed_at, access_count, content, metadata, tags,
                     version, content_hash, run_id, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._entry_to_row(entry),
                )
                conn.commit()
            self._stats["total_writes"] += 1
        return entry.id

    def get(self, entry_id: str) -> T | None:
        """获取知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目或 None
        """
        with self._lock:
            self._stats["total_reads"] += 1
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM knowledge_entries WHERE id = ?",
                    (entry_id,),
                )
                row = cursor.fetchone()
                if row:
                    entry = self._row_to_entry(row)
                    entry.touch()
                    # 更新访问信息
                    conn.execute(
                        """
                        UPDATE knowledge_entries
                        SET accessed_at = ?, access_count = ?
                        WHERE id = ?
                        """,
                        (entry.accessed_at, entry.access_count, entry_id),
                    )
                    conn.commit()
                    self._stats["cache_hits"] += 1
                    return entry  # type: ignore
                self._stats["cache_misses"] += 1
                return None

    def delete(self, entry_id: str) -> bool:
        """删除知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM knowledge_entries WHERE id = ?",
                    (entry_id,),
                )
                conn.commit()
                return cursor.rowcount > 0

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
            tags: 标签过滤
            min_priority: 最低优先级
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            匹配的知识条目列表
        """
        with self._lock:
            conditions: list[str] = []
            params: list[Any] = []

            if knowledge_type:
                conditions.append("knowledge_type = ?")
                params.append(knowledge_type.name)
            if min_priority:
                conditions.append("priority >= ?")
                params.append(min_priority.value)
            if start_time:
                conditions.append("created_at >= ?")
                params.append(start_time)
            if end_time:
                conditions.append("created_at <= ?")
                params.append(end_time)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"""
                SELECT * FROM knowledge_entries
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

            results: list[T] = []
            for row in rows:
                entry = self._row_to_entry(row)
                # 标签过滤 (JSON内部过滤)
                if tags and not all(tag in entry.tags for tag in tags):
                    continue
                results.append(entry)  # type: ignore

            return results

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
        with self._lock:
            conditions: list[str] = []
            params: list[Any] = []

            if knowledge_type:
                conditions.append("knowledge_type = ?")
                params.append(knowledge_type.name)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT COUNT(*) FROM knowledge_entries WHERE {where_clause}"

            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                count = cursor.fetchone()[0]

            # 如果有标签过滤，需要后处理
            if tags:
                entries = self.query(knowledge_type=knowledge_type, tags=tags, limit=100000)
                return len(entries)

            return count

    def clear(self) -> int:
        """清空所有知识条目.

        Returns:
            删除的条目数量
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM knowledge_entries")
                count = cursor.fetchone()[0]
                conn.execute("DELETE FROM knowledge_entries")
                conn.commit()
            return count

    def get_entries_older_than(self, age_seconds: float) -> list[T]:
        """获取超过指定年龄的条目 (用于迁移).

        Args:
            age_seconds: 年龄阈值 (秒)

        Returns:
            符合条件的条目列表
        """
        threshold = time.time() - age_seconds
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT * FROM knowledge_entries
                    WHERE created_at < ?
                    ORDER BY created_at
                    """,
                    (threshold,),
                )
                rows = cursor.fetchall()

            return [self._row_to_entry(row) for row in rows]  # type: ignore


class ColdStorage(KnowledgeStore[T]):
    """冷存储实现 (文件系统).

    使用文件系统存储90天以上的归档数据。

    特性:
    - GZIP压缩
    - 分目录组织
    - 批量读写
    """

    def __init__(
        self,
        name: str = "cold",
        storage_dir: str = "knowledge_cold",
        compress: bool = True,
    ) -> None:
        """初始化冷存储.

        Args:
            name: 存储名称
            storage_dir: 存储目录
            compress: 是否压缩
        """
        super().__init__(name)
        self.storage_dir = Path(storage_dir)
        self.compress = compress
        self._lock = threading.RLock()
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """确保存储目录存在."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_entry_path(self, entry_id: str) -> Path:
        """获取条目文件路径.

        Args:
            entry_id: 条目 ID

        Returns:
            文件路径
        """
        # 使用ID前缀分目录避免单目录文件过多
        prefix = entry_id[:2]
        subdir = self.storage_dir / prefix
        subdir.mkdir(exist_ok=True)
        suffix = ".json.gz" if self.compress else ".json"
        return subdir / f"{entry_id}{suffix}"

    def _write_entry(self, path: Path, entry: T) -> None:
        """写入条目到文件.

        Args:
            path: 文件路径
            entry: 知识条目
        """
        data = json.dumps(entry.to_dict(), ensure_ascii=False).encode("utf-8")
        if self.compress:
            with gzip.open(path, "wb") as f:
                f.write(data)
        else:
            path.write_bytes(data)

    def _read_entry(self, path: Path) -> T | None:
        """从文件读取条目.

        Args:
            path: 文件路径

        Returns:
            知识条目或 None
        """
        if not path.exists():
            return None

        try:
            if self.compress:
                with gzip.open(path, "rb") as f:
                    data = json.loads(f.read().decode("utf-8"))
            else:
                data = json.loads(path.read_text(encoding="utf-8"))
            return KnowledgeEntry.from_dict(data)  # type: ignore
        except (json.JSONDecodeError, gzip.BadGzipFile):
            return None

    def put(self, entry: T) -> str:
        """存储知识条目.

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        with self._lock:
            path = self._get_entry_path(entry.id)
            self._write_entry(path, entry)
            self._stats["total_writes"] += 1
        return entry.id

    def get(self, entry_id: str) -> T | None:
        """获取知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目或 None
        """
        with self._lock:
            self._stats["total_reads"] += 1
            path = self._get_entry_path(entry_id)
            entry = self._read_entry(path)
            if entry:
                entry.touch()
                self._write_entry(path, entry)
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1
            return entry

    def delete(self, entry_id: str) -> bool:
        """删除知识条目.

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        with self._lock:
            path = self._get_entry_path(entry_id)
            if path.exists():
                path.unlink()
                return True
            return False

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

        注意: 冷存储查询性能较低，建议使用具体ID查询。

        Args:
            knowledge_type: 知识类型过滤
            tags: 标签过滤
            min_priority: 最低优先级
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            匹配的知识条目列表
        """
        with self._lock:
            results: list[T] = []
            suffix = ".json.gz" if self.compress else ".json"

            for subdir in self.storage_dir.iterdir():
                if not subdir.is_dir():
                    continue
                for file_path in subdir.glob(f"*{suffix}"):
                    entry = self._read_entry(file_path)
                    if entry is None:
                        continue
                    if knowledge_type and entry.knowledge_type != knowledge_type:
                        continue
                    if tags and not all(tag in entry.tags for tag in tags):
                        continue
                    if min_priority and entry.priority.value < min_priority.value:
                        continue
                    if start_time and entry.created_at < start_time:
                        continue
                    if end_time and entry.created_at > end_time:
                        continue
                    results.append(entry)  # type: ignore

            results.sort(key=lambda x: x.created_at, reverse=True)
            return results[offset : offset + limit]

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
        if not knowledge_type and not tags:
            # 快速计数
            count = 0
            suffix = ".json.gz" if self.compress else ".json"
            for subdir in self.storage_dir.iterdir():
                if subdir.is_dir():
                    count += len(list(subdir.glob(f"*{suffix}")))
            return count

        return len(self.query(knowledge_type=knowledge_type, tags=tags, limit=100000))

    def clear(self) -> int:
        """清空所有知识条目.

        Returns:
            删除的条目数量
        """
        with self._lock:
            count = 0
            for subdir in self.storage_dir.iterdir():
                if subdir.is_dir():
                    for file_path in subdir.iterdir():
                        file_path.unlink()
                        count += 1
                    subdir.rmdir()
            return count


class TieredStorage(KnowledgeStore[T]):
    """分层存储管理器.

    统一管理热/温/冷三层存储，自动处理:
    - 数据迁移 (热->温->冷)
    - 跨层查询
    - 审计日志

    军规要求:
    - M33: 知识沉淀机制 - 自动归档
    - M3: 审计日志完整 - 所有操作记录
    - M7: 场景回放支持 - run_id追踪
    """

    def __init__(
        self,
        config: TieredStorageConfig | None = None,
        name: str = "tiered",
    ) -> None:
        """初始化分层存储.

        Args:
            config: 存储配置
            name: 存储名称
        """
        super().__init__(name)
        self.config = config or TieredStorageConfig()

        # 初始化三层存储
        self.hot = HotStorage[T](
            name="hot",
            max_items=self.config.hot_max_items,
            ttl_seconds=self.config.hot_ttl_seconds,
        )
        self.warm = WarmStorage[T](
            name="warm",
            db_path=self.config.warm_db_path,
        )
        self.cold = ColdStorage[T](
            name="cold",
            storage_dir=self.config.cold_dir_path,
            compress=self.config.compress_cold,
        )

        # 审计日志
        self._audit_records: list[KnowledgeAuditRecord] = []
        self._audit_lock = threading.Lock()

    def _log_audit(
        self,
        operation: str,
        entry_id: str,
        knowledge_type: str,
        run_id: str = "",
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str = "",
    ) -> None:
        """记录审计日志.

        Args:
            operation: 操作类型
            entry_id: 条目 ID
            knowledge_type: 知识类型
            run_id: 运行 ID
            details: 详情
            success: 是否成功
            error_message: 错误信息
        """
        if not self.config.audit_enabled:
            return

        record = KnowledgeAuditRecord.create(
            operation=operation,
            entry_id=entry_id,
            knowledge_type=knowledge_type,
            run_id=run_id,
            details=details,
            success=success,
            error_message=error_message,
        )

        with self._audit_lock:
            self._audit_records.append(record)
            # 定期刷新到文件
            if len(self._audit_records) >= 100:
                self._flush_audit_log()

    def _flush_audit_log(self) -> None:
        """刷新审计日志到文件."""
        if not self._audit_records:
            return

        with open(self.config.audit_path, "a", encoding="utf-8") as f:
            for record in self._audit_records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        self._audit_records.clear()

    def _determine_tier(self, entry: T) -> StorageTier:
        """确定条目应存储的层级.

        Args:
            entry: 知识条目

        Returns:
            存储层级
        """
        return entry.storage_tier

    def put(self, entry: T) -> str:
        """存储知识条目.

        根据条目年龄自动选择存储层级。

        Args:
            entry: 知识条目

        Returns:
            条目 ID
        """
        tier = self._determine_tier(entry)

        if tier == StorageTier.HOT:
            self.hot.put(entry)
        elif tier == StorageTier.WARM:
            self.warm.put(entry)
        else:
            self.cold.put(entry)

        self._log_audit(
            operation="put",
            entry_id=entry.id,
            knowledge_type=entry.knowledge_type.name,
            run_id=entry.run_id,
            details={"tier": tier.value},
        )
        self._stats["total_writes"] += 1

        return entry.id

    def get(self, entry_id: str) -> T | None:
        """获取知识条目.

        按热->温->冷顺序查找。

        Args:
            entry_id: 条目 ID

        Returns:
            知识条目或 None
        """
        self._stats["total_reads"] += 1

        # 热存储查找
        entry = self.hot.get(entry_id)
        if entry:
            self._stats["cache_hits"] += 1
            self._log_audit("get", entry_id, entry.knowledge_type.name, details={"tier": "hot"})
            return entry

        # 温存储查找
        entry = self.warm.get(entry_id)
        if entry:
            # 提升到热存储
            self.hot.put(entry)
            self._log_audit("get", entry_id, entry.knowledge_type.name, details={"tier": "warm", "promoted": True})
            return entry

        # 冷存储查找
        entry = self.cold.get(entry_id)
        if entry:
            # 提升到热存储
            self.hot.put(entry)
            self._log_audit("get", entry_id, entry.knowledge_type.name, details={"tier": "cold", "promoted": True})
            return entry

        self._stats["cache_misses"] += 1
        return None

    def delete(self, entry_id: str) -> bool:
        """删除知识条目.

        从所有层级删除。

        Args:
            entry_id: 条目 ID

        Returns:
            是否删除成功
        """
        deleted = False
        if self.hot.delete(entry_id):
            deleted = True
        if self.warm.delete(entry_id):
            deleted = True
        if self.cold.delete(entry_id):
            deleted = True

        self._log_audit("delete", entry_id, "", details={"deleted": deleted})
        return deleted

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

        跨层级查询并合并结果。

        Args:
            knowledge_type: 知识类型过滤
            tags: 标签过滤
            min_priority: 最低优先级
            start_time: 开始时间戳
            end_time: 结束时间戳
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            匹配的知识条目列表
        """
        # 从各层获取结果
        hot_results = self.hot.query(
            knowledge_type, tags, min_priority, start_time, end_time, limit * 2, 0
        )
        warm_results = self.warm.query(
            knowledge_type, tags, min_priority, start_time, end_time, limit * 2, 0
        )
        cold_results = self.cold.query(
            knowledge_type, tags, min_priority, start_time, end_time, limit, 0
        )

        # 合并去重 (以ID为键)
        seen: set[str] = set()
        results: list[T] = []
        for entry in hot_results + warm_results + cold_results:
            if entry.id not in seen:
                seen.add(entry.id)
                results.append(entry)

        # 按创建时间排序
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[offset : offset + limit]

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
            条目数量 (跨层级)
        """
        return (
            self.hot.count(knowledge_type, tags)
            + self.warm.count(knowledge_type, tags)
            + self.cold.count(knowledge_type, tags)
        )

    def clear(self) -> int:
        """清空所有知识条目.

        Returns:
            删除的条目数量
        """
        count = self.hot.clear() + self.warm.clear() + self.cold.clear()
        self._log_audit("clear", "", "", details={"count": count})
        return count

    def migrate(self) -> dict[str, int]:
        """执行数据迁移.

        将过期数据从高层迁移到低层:
        - 热 -> 温 (超过7天)
        - 温 -> 冷 (超过90天)

        Returns:
            迁移统计 {"hot_to_warm": n, "warm_to_cold": n}
        """
        stats = {"hot_to_warm": 0, "warm_to_cold": 0}

        # 热 -> 温
        hot_entries = self.hot.get_all_entries()
        for entry in hot_entries:
            if entry.age_seconds > STORAGE_TIER_THRESHOLDS[StorageTier.HOT]:
                self.warm.put(entry)
                self.hot.delete(entry.id)
                stats["hot_to_warm"] += 1

        # 温 -> 冷
        warm_old = self.warm.get_entries_older_than(
            STORAGE_TIER_THRESHOLDS[StorageTier.WARM]
        )
        for entry in warm_old:
            self.cold.put(entry)
            self.warm.delete(entry.id)
            stats["warm_to_cold"] += 1

        self._log_audit("migrate", "", "", details=stats)
        return stats

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            包含各层统计的字典
        """
        return {
            "overall": self._stats.copy(),
            "hot": self.hot.get_stats(),
            "warm": self.warm.get_stats(),
            "cold": self.cold.get_stats(),
        }

    def flush(self) -> None:
        """刷新所有缓冲数据."""
        self._flush_audit_log()

    def close(self) -> None:
        """关闭存储并清理资源."""
        self.flush()
