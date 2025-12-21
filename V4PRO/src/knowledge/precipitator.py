"""
知识沉淀管理器 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

知识沉淀管理功能:
- 高价值知识识别
- 自动归档和清理
- 知识版本控制
- 知识关联追踪
- 定期维护任务

军规覆盖:
- M33: 知识沉淀机制 (核心)
- M3: 审计日志完整
- M7: 场景回放支持
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeType,
    StorageTier,
)
from src.knowledge.storage import TieredStorage


class PrecipitationLevel(Enum):
    """沉淀级别.

    - CRITICAL: 关键知识，永久保留
    - IMPORTANT: 重要知识，长期保留
    - STANDARD: 标准知识，按规则保留
    - TEMPORARY: 临时知识，可清理
    """

    CRITICAL = 4
    IMPORTANT = 3
    STANDARD = 2
    TEMPORARY = 1


class MaintenanceAction(Enum):
    """维护动作类型.

    - ARCHIVE: 归档
    - PROMOTE: 提升层级
    - DEMOTE: 降级层级
    - DELETE: 删除
    - CONSOLIDATE: 合并
    - VERSION: 版本化
    """

    ARCHIVE = auto()
    PROMOTE = auto()
    DEMOTE = auto()
    DELETE = auto()
    CONSOLIDATE = auto()
    VERSION = auto()


@dataclass
class PrecipitationRule:
    """沉淀规则.

    定义知识如何被沉淀和维护。

    Attributes:
        id: 规则ID
        name: 规则名称
        knowledge_types: 适用的知识类型
        min_access_count: 最低访问次数
        min_age_days: 最低年龄(天)
        max_age_days: 最大年龄(天)
        min_priority: 最低优先级
        action: 维护动作
        target_level: 目标沉淀级别
        enabled: 是否启用
    """

    id: str
    name: str
    knowledge_types: list[KnowledgeType]
    min_access_count: int = 0
    min_age_days: int = 0
    max_age_days: int = 365
    min_priority: KnowledgePriority = KnowledgePriority.LOW
    action: MaintenanceAction = MaintenanceAction.ARCHIVE
    target_level: PrecipitationLevel = PrecipitationLevel.STANDARD
    enabled: bool = True

    def matches(self, entry: KnowledgeEntry) -> bool:
        """检查条目是否匹配此规则.

        Args:
            entry: 知识条目

        Returns:
            是否匹配
        """
        if not self.enabled:
            return False

        if entry.knowledge_type not in self.knowledge_types:
            return False

        age_days = entry.age_seconds / (24 * 3600)
        if age_days < self.min_age_days or age_days > self.max_age_days:
            return False

        if entry.access_count < self.min_access_count:
            return False

        if entry.priority.value < self.min_priority.value:
            return False

        return True


@dataclass
class PrecipitationRecord:
    """沉淀记录.

    记录知识沉淀操作的详情。

    Attributes:
        id: 记录ID
        entry_id: 知识条目ID
        action: 执行的动作
        from_tier: 原始层级
        to_tier: 目标层级
        level: 沉淀级别
        rule_id: 触发规则ID
        timestamp: 时间戳
        details: 详情
    """

    id: str
    entry_id: str
    action: MaintenanceAction
    from_tier: StorageTier | None
    to_tier: StorageTier | None
    level: PrecipitationLevel
    rule_id: str = ""
    timestamp: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化时设置时间戳."""
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "id": self.id,
            "entry_id": self.entry_id,
            "action": self.action.name,
            "from_tier": self.from_tier.value if self.from_tier else None,
            "to_tier": self.to_tier.value if self.to_tier else None,
            "level": self.level.name,
            "rule_id": self.rule_id,
            "timestamp": self.timestamp,
            "details": self.details,
        }


@dataclass
class KnowledgeVersion:
    """知识版本.

    用于知识版本控制。

    Attributes:
        version_id: 版本ID
        entry_id: 知识条目ID
        version: 版本号
        content_hash: 内容哈希
        created_at: 创建时间
        author: 作者/来源
        changes: 变更说明
        snapshot: 内容快照
    """

    version_id: str
    entry_id: str
    version: int
    content_hash: str
    created_at: float
    author: str = ""
    changes: str = ""
    snapshot: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_entry(
        cls,
        entry: KnowledgeEntry,
        changes: str = "",
        author: str = "system",
    ) -> KnowledgeVersion:
        """从知识条目创建版本.

        Args:
            entry: 知识条目
            changes: 变更说明
            author: 作者

        Returns:
            KnowledgeVersion 实例
        """
        return cls(
            version_id=str(uuid.uuid4()),
            entry_id=entry.id,
            version=entry.version,
            content_hash=entry.content_hash,
            created_at=time.time(),
            author=author,
            changes=changes,
            snapshot=entry.to_dict(),
        )


class KnowledgePrecipitator:
    """知识沉淀管理器.

    实现军规M33的核心知识沉淀机制。

    功能特性:
    - 高价值知识识别和保护
    - 自动分层归档
    - 定期清理过期知识
    - 版本控制和回滚
    - 知识关联追踪
    - 沉淀统计和报告

    军规要求:
    - M33: 知识沉淀机制 (核心实现)
    - M3: 审计日志完整 - 所有操作记录
    - M7: 场景回放支持 - 版本快照
    """

    def __init__(
        self,
        storage: TieredStorage,
        archive_dir: str = "knowledge_archive",
        auto_maintenance: bool = True,
        maintenance_interval: int = 3600,  # 1小时
    ) -> None:
        """初始化知识沉淀管理器.

        Args:
            storage: 分层存储
            archive_dir: 归档目录
            auto_maintenance: 是否自动维护
            maintenance_interval: 维护间隔(秒)
        """
        self.storage = storage
        self.archive_dir = Path(archive_dir)
        self.auto_maintenance = auto_maintenance
        self.maintenance_interval = maintenance_interval

        self._rules: list[PrecipitationRule] = []
        self._versions: dict[str, list[KnowledgeVersion]] = {}
        self._records: list[PrecipitationRecord] = []
        self._lock = threading.RLock()

        self._stats = {
            "total_precipitations": 0,
            "archived_count": 0,
            "deleted_count": 0,
            "promoted_count": 0,
            "demoted_count": 0,
            "versions_created": 0,
        }

        # 确保归档目录存在
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # 注册默认规则
        self._register_default_rules()

        # 启动自动维护
        if auto_maintenance:
            self._start_maintenance_thread()

    def _register_default_rules(self) -> None:
        """注册默认沉淀规则."""
        # 规则1: 高频访问知识提升为重要
        self.register_rule(
            PrecipitationRule(
                id="high_access_promote",
                name="高频访问知识提升",
                knowledge_types=list(KnowledgeType),
                min_access_count=100,
                min_age_days=7,
                action=MaintenanceAction.PROMOTE,
                target_level=PrecipitationLevel.IMPORTANT,
            )
        )

        # 规则2: 失败经验永久保留
        self.register_rule(
            PrecipitationRule(
                id="failure_preserve",
                name="失败经验永久保留",
                knowledge_types=[KnowledgeType.REFLEXION],
                min_priority=KnowledgePriority.HIGH,
                action=MaintenanceAction.ARCHIVE,
                target_level=PrecipitationLevel.CRITICAL,
            )
        )

        # 规则3: 长期未访问知识降级
        self.register_rule(
            PrecipitationRule(
                id="stale_demote",
                name="长期未访问知识降级",
                knowledge_types=list(KnowledgeType),
                min_age_days=90,
                max_age_days=365,
                action=MaintenanceAction.DEMOTE,
                target_level=PrecipitationLevel.TEMPORARY,
            )
        )

        # 规则4: 过期临时知识清理
        self.register_rule(
            PrecipitationRule(
                id="expired_cleanup",
                name="过期临时知识清理",
                knowledge_types=[KnowledgeType.DECISION],
                min_age_days=365,
                min_priority=KnowledgePriority.LOW,
                action=MaintenanceAction.DELETE,
                target_level=PrecipitationLevel.TEMPORARY,
            )
        )

    def _start_maintenance_thread(self) -> None:
        """启动自动维护线程."""
        def maintenance_loop() -> None:
            while True:
                time.sleep(self.maintenance_interval)
                try:
                    self.run_maintenance()
                except Exception:
                    pass  # 维护失败不影响主流程

        thread = threading.Thread(target=maintenance_loop, daemon=True)
        thread.start()

    def register_rule(self, rule: PrecipitationRule) -> None:
        """注册沉淀规则.

        Args:
            rule: 沉淀规则
        """
        with self._lock:
            self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """移除沉淀规则.

        Args:
            rule_id: 规则ID

        Returns:
            是否成功
        """
        with self._lock:
            for rule in self._rules:
                if rule.id == rule_id:
                    self._rules.remove(rule)
                    return True
            return False

    def evaluate_entry(
        self,
        entry: KnowledgeEntry,
    ) -> tuple[PrecipitationLevel, list[PrecipitationRule]]:
        """评估知识条目的沉淀级别.

        Args:
            entry: 知识条目

        Returns:
            (沉淀级别, 匹配的规则列表)
        """
        matched_rules: list[PrecipitationRule] = []
        max_level = PrecipitationLevel.TEMPORARY

        with self._lock:
            for rule in self._rules:
                if rule.matches(entry):
                    matched_rules.append(rule)
                    if rule.target_level.value > max_level.value:
                        max_level = rule.target_level

        return max_level, matched_rules

    def precipitate(
        self,
        entry: KnowledgeEntry,
        force_level: PrecipitationLevel | None = None,
    ) -> PrecipitationRecord:
        """执行知识沉淀.

        Args:
            entry: 知识条目
            force_level: 强制设置的沉淀级别

        Returns:
            沉淀记录
        """
        with self._lock:
            # 评估沉淀级别
            level, rules = self.evaluate_entry(entry)
            if force_level:
                level = force_level

            # 确定动作
            action = self._determine_action(entry, level, rules)

            # 记录原始层级
            from_tier = entry.storage_tier

            # 执行动作
            to_tier = self._execute_action(entry, action, level)

            # 创建记录
            record = PrecipitationRecord(
                id=str(uuid.uuid4()),
                entry_id=entry.id,
                action=action,
                from_tier=from_tier,
                to_tier=to_tier,
                level=level,
                rule_id=rules[0].id if rules else "",
                details={
                    "knowledge_type": entry.knowledge_type.name,
                    "priority": entry.priority.name,
                    "access_count": entry.access_count,
                    "age_days": entry.age_seconds / (24 * 3600),
                },
            )

            self._records.append(record)
            self._update_stats(action)
            self._stats["total_precipitations"] += 1

            return record

    def _determine_action(
        self,
        entry: KnowledgeEntry,
        level: PrecipitationLevel,
        rules: list[PrecipitationRule],
    ) -> MaintenanceAction:
        """确定维护动作.

        Args:
            entry: 知识条目
            level: 沉淀级别
            rules: 匹配的规则

        Returns:
            维护动作
        """
        # 如果有匹配规则，使用规则的动作
        if rules:
            return rules[0].action

        # 根据级别确定默认动作
        if level == PrecipitationLevel.CRITICAL:
            return MaintenanceAction.ARCHIVE
        if level == PrecipitationLevel.IMPORTANT:
            return MaintenanceAction.PROMOTE
        if level == PrecipitationLevel.TEMPORARY:
            return MaintenanceAction.DEMOTE
        return MaintenanceAction.ARCHIVE

    def _execute_action(
        self,
        entry: KnowledgeEntry,
        action: MaintenanceAction,
        level: PrecipitationLevel,
    ) -> StorageTier | None:
        """执行维护动作.

        Args:
            entry: 知识条目
            action: 维护动作
            level: 沉淀级别

        Returns:
            目标存储层级
        """
        to_tier = None

        if action == MaintenanceAction.ARCHIVE:
            # 归档到冷存储
            self.storage.cold.put(entry)
            to_tier = StorageTier.COLD

        elif action == MaintenanceAction.PROMOTE:
            # 提升到热存储
            self.storage.hot.put(entry)
            to_tier = StorageTier.HOT

        elif action == MaintenanceAction.DEMOTE:
            # 降级到冷存储
            if entry.storage_tier == StorageTier.HOT:
                self.storage.warm.put(entry)
                self.storage.hot.delete(entry.id)
                to_tier = StorageTier.WARM
            elif entry.storage_tier == StorageTier.WARM:
                self.storage.cold.put(entry)
                self.storage.warm.delete(entry.id)
                to_tier = StorageTier.COLD

        elif action == MaintenanceAction.DELETE:
            # 删除前创建版本快照
            self.create_version(entry, "Deleted by maintenance")
            self.storage.delete(entry.id)

        elif action == MaintenanceAction.VERSION:
            # 创建版本
            self.create_version(entry, "Version checkpoint")

        return to_tier

    def _update_stats(self, action: MaintenanceAction) -> None:
        """更新统计信息.

        Args:
            action: 执行的动作
        """
        if action == MaintenanceAction.ARCHIVE:
            self._stats["archived_count"] += 1
        elif action == MaintenanceAction.DELETE:
            self._stats["deleted_count"] += 1
        elif action == MaintenanceAction.PROMOTE:
            self._stats["promoted_count"] += 1
        elif action == MaintenanceAction.DEMOTE:
            self._stats["demoted_count"] += 1

    def create_version(
        self,
        entry: KnowledgeEntry,
        changes: str = "",
        author: str = "system",
    ) -> KnowledgeVersion:
        """创建知识版本.

        Args:
            entry: 知识条目
            changes: 变更说明
            author: 作者

        Returns:
            KnowledgeVersion 实例
        """
        with self._lock:
            version = KnowledgeVersion.from_entry(entry, changes, author)

            if entry.id not in self._versions:
                self._versions[entry.id] = []
            self._versions[entry.id].append(version)

            # 持久化版本
            self._save_version(version)

            self._stats["versions_created"] += 1
            return version

    def _save_version(self, version: KnowledgeVersion) -> None:
        """持久化版本到归档目录.

        Args:
            version: 知识版本
        """
        version_dir = self.archive_dir / "versions" / version.entry_id[:2]
        version_dir.mkdir(parents=True, exist_ok=True)

        version_file = version_dir / f"{version.entry_id}_{version.version}.json"
        with open(version_file, "w", encoding="utf-8") as f:
            json.dump({
                "version_id": version.version_id,
                "entry_id": version.entry_id,
                "version": version.version,
                "content_hash": version.content_hash,
                "created_at": version.created_at,
                "author": version.author,
                "changes": version.changes,
                "snapshot": version.snapshot,
            }, f, ensure_ascii=False, indent=2)

    def get_versions(self, entry_id: str) -> list[KnowledgeVersion]:
        """获取知识条目的所有版本.

        Args:
            entry_id: 知识条目ID

        Returns:
            版本列表
        """
        with self._lock:
            return self._versions.get(entry_id, []).copy()

    def rollback(
        self,
        entry_id: str,
        target_version: int,
    ) -> KnowledgeEntry | None:
        """回滚到指定版本.

        Args:
            entry_id: 知识条目ID
            target_version: 目标版本号

        Returns:
            回滚后的知识条目或 None
        """
        with self._lock:
            versions = self._versions.get(entry_id, [])
            for version in versions:
                if version.version == target_version:
                    # 从快照恢复
                    entry = KnowledgeEntry.from_dict(version.snapshot)
                    # 存储恢复的条目
                    self.storage.put(entry)
                    return entry
            return None

    def run_maintenance(self) -> dict[str, int]:
        """执行定期维护任务.

        Returns:
            维护统计
        """
        maintenance_stats = {
            "processed": 0,
            "archived": 0,
            "promoted": 0,
            "demoted": 0,
            "deleted": 0,
        }

        with self._lock:
            # 获取所有条目
            all_entries = self.storage.query(limit=10000)

            for entry in all_entries:
                level, rules = self.evaluate_entry(entry)

                # 只处理匹配规则的条目
                if rules:
                    record = self.precipitate(entry)
                    maintenance_stats["processed"] += 1

                    if record.action == MaintenanceAction.ARCHIVE:
                        maintenance_stats["archived"] += 1
                    elif record.action == MaintenanceAction.PROMOTE:
                        maintenance_stats["promoted"] += 1
                    elif record.action == MaintenanceAction.DEMOTE:
                        maintenance_stats["demoted"] += 1
                    elif record.action == MaintenanceAction.DELETE:
                        maintenance_stats["deleted"] += 1

            # 执行存储迁移
            migration_stats = self.storage.migrate()

            return {
                **maintenance_stats,
                "migrated_hot_to_warm": migration_stats.get("hot_to_warm", 0),
                "migrated_warm_to_cold": migration_stats.get("warm_to_cold", 0),
            }

    def get_precipitation_report(
        self,
        days: int = 7,
    ) -> dict[str, Any]:
        """获取沉淀报告.

        Args:
            days: 统计天数

        Returns:
            沉淀报告
        """
        cutoff = time.time() - days * 24 * 3600

        with self._lock:
            recent_records = [r for r in self._records if r.timestamp >= cutoff]

            # 按动作统计
            by_action: dict[str, int] = {}
            for record in recent_records:
                action_name = record.action.name
                by_action[action_name] = by_action.get(action_name, 0) + 1

            # 按知识类型统计
            by_type: dict[str, int] = {}
            for record in recent_records:
                kt = record.details.get("knowledge_type", "UNKNOWN")
                by_type[kt] = by_type.get(kt, 0) + 1

            return {
                "period_days": days,
                "total_precipitations": len(recent_records),
                "by_action": by_action,
                "by_knowledge_type": by_type,
                "active_rules": len(self._rules),
                "total_versions": sum(len(v) for v in self._versions.values()),
                "overall_stats": self._stats.copy(),
            }

    def identify_high_value_knowledge(
        self,
        limit: int = 20,
    ) -> list[tuple[KnowledgeEntry, float]]:
        """识别高价值知识.

        基于访问频率、优先级、年龄等因素评估知识价值。

        Args:
            limit: 返回数量限制

        Returns:
            (知识条目, 价值分数) 列表
        """
        all_entries = self.storage.query(limit=1000)

        scored: list[tuple[KnowledgeEntry, float]] = []
        for entry in all_entries:
            score = self._compute_value_score(entry)
            scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _compute_value_score(self, entry: KnowledgeEntry) -> float:
        """计算知识价值分数.

        Args:
            entry: 知识条目

        Returns:
            价值分数 (0-1)
        """
        score = 0.0

        # 优先级权重 (0-0.3)
        priority_weight = entry.priority.weight * 0.3
        score += priority_weight

        # 访问频率权重 (0-0.3)
        access_weight = min(entry.access_count / 100, 1.0) * 0.3
        score += access_weight

        # 新鲜度权重 (0-0.2)
        age_days = entry.age_seconds / (24 * 3600)
        freshness_weight = max(0, 1 - age_days / 365) * 0.2
        score += freshness_weight

        # 知识类型权重 (0-0.2)
        type_weights = {
            KnowledgeType.REFLEXION: 0.2,  # 经验最有价值
            KnowledgeType.RISK: 0.2,
            KnowledgeType.FAULT: 0.15,
            KnowledgeType.PATTERN: 0.15,
            KnowledgeType.STRATEGY: 0.1,
            KnowledgeType.DECISION: 0.1,
        }
        score += type_weights.get(entry.knowledge_type, 0.1)

        return min(score, 1.0)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据字典
        """
        with self._lock:
            return {
                **self._stats,
                "active_rules": len(self._rules),
                "total_versions": sum(len(v) for v in self._versions.values()),
                "total_records": len(self._records),
                "storage_stats": self.storage.get_stats(),
            }

    def export_knowledge_base(
        self,
        output_path: str,
        include_versions: bool = True,
    ) -> dict[str, int]:
        """导出知识库.

        Args:
            output_path: 输出路径
            include_versions: 是否包含版本历史

        Returns:
            导出统计
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        stats = {
            "entries_exported": 0,
            "versions_exported": 0,
        }

        # 导出所有条目
        all_entries = self.storage.query(limit=100000)
        entries_file = output_dir / "knowledge_entries.jsonl"
        with open(entries_file, "w", encoding="utf-8") as f:
            for entry in all_entries:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
                stats["entries_exported"] += 1

        # 导出版本历史
        if include_versions:
            versions_file = output_dir / "knowledge_versions.jsonl"
            with open(versions_file, "w", encoding="utf-8") as f:
                for entry_id, versions in self._versions.items():
                    for version in versions:
                        f.write(json.dumps({
                            "version_id": version.version_id,
                            "entry_id": version.entry_id,
                            "version": version.version,
                            "content_hash": version.content_hash,
                            "created_at": version.created_at,
                            "author": version.author,
                            "changes": version.changes,
                        }, ensure_ascii=False) + "\n")
                        stats["versions_exported"] += 1

        # 导出沉淀记录
        records_file = output_dir / "precipitation_records.jsonl"
        with open(records_file, "w", encoding="utf-8") as f:
            for record in self._records:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

        return stats
