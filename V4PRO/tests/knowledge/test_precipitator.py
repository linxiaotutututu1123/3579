"""
知识沉淀管理器测试 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

测试场景:
- M33.PRECIPITATOR.RULE_MATCHING: 规则匹配功能
- M33.PRECIPITATOR.LEVEL_EVALUATION: 沉淀级别评估
- M33.PRECIPITATOR.VERSION_CONTROL: 版本控制功能
- M33.PRECIPITATOR.MAINTENANCE: 维护任务执行
- M33.PRECIPITATOR.ARCHIVE: 归档功能
- M33.PRECIPITATOR.HIGH_VALUE: 高价值知识识别
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeType,
    StorageTier,
)
from src.knowledge.precipitator import (
    KnowledgePrecipitator,
    KnowledgeVersion,
    MaintenanceAction,
    PrecipitationLevel,
    PrecipitationRecord,
    PrecipitationRule,
)
from src.knowledge.storage import TieredStorage


class TestPrecipitationRule:
    """沉淀规则测试类."""

    def test_m33_precipitator_rule_matching_by_type(
        self,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.RULE_MATCHING: 规则按类型匹配."""
        rule = PrecipitationRule(
            id="test_rule",
            name="Test Rule",
            knowledge_types=[KnowledgeType.REFLEXION],
            action=MaintenanceAction.ARCHIVE,
            target_level=PrecipitationLevel.IMPORTANT,
        )

        assert rule.matches(sample_entry) is True

        # 修改类型后不匹配
        sample_entry.knowledge_type = KnowledgeType.PATTERN
        assert rule.matches(sample_entry) is False

    def test_m33_precipitator_rule_matching_by_priority(
        self,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.RULE_MATCHING: 规则按优先级匹配."""
        rule = PrecipitationRule(
            id="high_priority_rule",
            name="High Priority Rule",
            knowledge_types=[KnowledgeType.REFLEXION],
            min_priority=KnowledgePriority.HIGH,
            action=MaintenanceAction.PROMOTE,
            target_level=PrecipitationLevel.CRITICAL,
        )

        # 中等优先级不匹配高优先级规则
        assert rule.matches(sample_entry) is False

        # 设置为高优先级后匹配
        sample_entry.priority = KnowledgePriority.HIGH
        assert rule.matches(sample_entry) is True

    def test_m33_precipitator_rule_matching_by_access_count(
        self,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.RULE_MATCHING: 规则按访问次数匹配."""
        rule = PrecipitationRule(
            id="frequent_access_rule",
            name="Frequent Access Rule",
            knowledge_types=[KnowledgeType.REFLEXION],
            min_access_count=10,
            action=MaintenanceAction.PROMOTE,
            target_level=PrecipitationLevel.IMPORTANT,
        )

        # 初始访问次数为0，不匹配
        assert rule.matches(sample_entry) is False

        # 增加访问次数后匹配
        for _ in range(10):
            sample_entry.touch()
        assert rule.matches(sample_entry) is True

    def test_m33_precipitator_rule_disabled(
        self,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.RULE_MATCHING: 禁用规则不匹配."""
        rule = PrecipitationRule(
            id="disabled_rule",
            name="Disabled Rule",
            knowledge_types=[KnowledgeType.REFLEXION],
            action=MaintenanceAction.DELETE,
            target_level=PrecipitationLevel.TEMPORARY,
            enabled=False,
        )

        assert rule.matches(sample_entry) is False


class TestKnowledgePrecipitator:
    """知识沉淀管理器测试类."""

    def test_m33_precipitator_level_evaluation(
        self,
        precipitator: KnowledgePrecipitator,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.LEVEL_EVALUATION: 沉淀级别评估."""
        level, rules = precipitator.evaluate_entry(sample_entry)

        # 默认规则下，普通条目应该有某个级别
        assert level in list(PrecipitationLevel)
        assert isinstance(rules, list)

    def test_m33_precipitator_custom_rule_registration(
        self,
        precipitator: KnowledgePrecipitator,
    ) -> None:
        """M33.PRECIPITATOR.RULE_REGISTRATION: 自定义规则注册."""
        initial_rule_count = len(precipitator._rules)

        custom_rule = PrecipitationRule(
            id="custom_test_rule",
            name="Custom Test Rule",
            knowledge_types=[KnowledgeType.DECISION],
            min_access_count=5,
            action=MaintenanceAction.ARCHIVE,
            target_level=PrecipitationLevel.STANDARD,
        )

        precipitator.register_rule(custom_rule)
        assert len(precipitator._rules) == initial_rule_count + 1

        # 移除规则
        result = precipitator.remove_rule("custom_test_rule")
        assert result is True
        assert len(precipitator._rules) == initial_rule_count

    def test_m33_precipitator_version_creation(
        self,
        precipitator: KnowledgePrecipitator,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.VERSION_CONTROL: 版本创建."""
        version = precipitator.create_version(
            entry=sample_entry,
            changes="Initial version for testing",
            author="test_suite",
        )

        assert isinstance(version, KnowledgeVersion)
        assert version.entry_id == sample_entry.id
        assert version.version == sample_entry.version
        assert version.content_hash == sample_entry.content_hash
        assert version.author == "test_suite"
        assert version.changes == "Initial version for testing"

    def test_m33_precipitator_version_history(
        self,
        precipitator: KnowledgePrecipitator,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.VERSION_CONTROL: 版本历史."""
        # 创建多个版本
        precipitator.create_version(sample_entry, "Version 1")

        # 修改内容
        sample_entry.content["updated"] = True
        sample_entry._update_metadata()

        precipitator.create_version(sample_entry, "Version 2")

        # 获取版本历史
        versions = precipitator.get_versions(sample_entry.id)
        assert len(versions) == 2

    def test_m33_precipitator_precipitate_entry(
        self,
        precipitator: KnowledgePrecipitator,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.PRECIPITATE: 执行沉淀."""
        # 先存储条目
        precipitator.storage.put(sample_entry)

        # 执行沉淀
        record = precipitator.precipitate(sample_entry)

        assert isinstance(record, PrecipitationRecord)
        assert record.entry_id == sample_entry.id
        assert record.action in list(MaintenanceAction)
        assert record.level in list(PrecipitationLevel)

    def test_m33_precipitator_force_level(
        self,
        precipitator: KnowledgePrecipitator,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.PRECIPITATE: 强制沉淀级别."""
        precipitator.storage.put(sample_entry)

        record = precipitator.precipitate(
            sample_entry,
            force_level=PrecipitationLevel.CRITICAL,
        )

        assert record.level == PrecipitationLevel.CRITICAL

    def test_m33_precipitator_maintenance_run(
        self,
        precipitator: KnowledgePrecipitator,
        tiered_storage: TieredStorage,
    ) -> None:
        """M33.PRECIPITATOR.MAINTENANCE: 维护任务执行."""
        # 创建一些测试条目
        for i in range(5):
            entry = KnowledgeEntry.create(
                knowledge_type=KnowledgeType.DECISION,
                content={"test": i},
                priority=KnowledgePriority.LOW,
                source="test",
            )
            tiered_storage.put(entry)

        # 运行维护
        stats = precipitator.run_maintenance()

        assert "processed" in stats
        assert "archived" in stats
        assert "promoted" in stats
        assert "demoted" in stats
        assert "deleted" in stats

    def test_m33_precipitator_high_value_identification(
        self,
        precipitator: KnowledgePrecipitator,
        tiered_storage: TieredStorage,
    ) -> None:
        """M33.PRECIPITATOR.HIGH_VALUE: 高价值知识识别."""
        # 创建不同优先级的条目
        high_value_entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.REFLEXION,
            content={"important": True},
            priority=KnowledgePriority.CRITICAL,
            source="test",
        )
        # 模拟多次访问
        for _ in range(20):
            high_value_entry.touch()
        tiered_storage.put(high_value_entry)

        low_value_entry = KnowledgeEntry.create(
            knowledge_type=KnowledgeType.DECISION,
            content={"trivial": True},
            priority=KnowledgePriority.LOW,
            source="test",
        )
        tiered_storage.put(low_value_entry)

        # 识别高价值知识
        high_value = precipitator.identify_high_value_knowledge(limit=10)

        assert len(high_value) > 0
        # 高价值条目应该排在前面
        entries = [e for e, _ in high_value]
        if len(entries) >= 2:
            scores = [s for _, s in high_value]
            assert scores[0] >= scores[1]

    def test_m33_precipitator_report_generation(
        self,
        precipitator: KnowledgePrecipitator,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.PRECIPITATOR.REPORT: 沉淀报告生成."""
        # 执行一些沉淀操作
        precipitator.storage.put(sample_entry)
        precipitator.precipitate(sample_entry)

        # 获取报告
        report = precipitator.get_precipitation_report(days=7)

        assert "period_days" in report
        assert "total_precipitations" in report
        assert "by_action" in report
        assert "by_knowledge_type" in report
        assert "active_rules" in report
        assert "overall_stats" in report

    def test_m33_precipitator_stats(
        self,
        precipitator: KnowledgePrecipitator,
    ) -> None:
        """M33.PRECIPITATOR.STATS: 统计信息."""
        stats = precipitator.get_stats()

        assert "total_precipitations" in stats
        assert "archived_count" in stats
        assert "deleted_count" in stats
        assert "promoted_count" in stats
        assert "demoted_count" in stats
        assert "versions_created" in stats
        assert "active_rules" in stats


class TestKnowledgeVersion:
    """知识版本测试类."""

    def test_m33_version_from_entry(
        self,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.VERSION.FROM_ENTRY: 从条目创建版本."""
        version = KnowledgeVersion.from_entry(
            entry=sample_entry,
            changes="Test change",
            author="tester",
        )

        assert version.entry_id == sample_entry.id
        assert version.version == sample_entry.version
        assert version.content_hash == sample_entry.content_hash
        assert version.author == "tester"
        assert version.changes == "Test change"
        assert "knowledge_type" in version.snapshot

    def test_m33_version_snapshot_integrity(
        self,
        sample_entry: KnowledgeEntry,
    ) -> None:
        """M33.VERSION.SNAPSHOT: 快照完整性."""
        version = KnowledgeVersion.from_entry(sample_entry, "Snapshot test")

        # 快照应包含原始内容
        assert version.snapshot["id"] == sample_entry.id
        assert version.snapshot["content"] == sample_entry.content
        assert version.snapshot["priority"] == sample_entry.priority.name


class TestPrecipitationRecord:
    """沉淀记录测试类."""

    def test_m33_record_creation(self) -> None:
        """M33.RECORD.CREATE: 记录创建."""
        record = PrecipitationRecord(
            id="test-record-001",
            entry_id="entry-001",
            action=MaintenanceAction.ARCHIVE,
            from_tier=StorageTier.HOT,
            to_tier=StorageTier.COLD,
            level=PrecipitationLevel.IMPORTANT,
            rule_id="test_rule",
        )

        assert record.id == "test-record-001"
        assert record.action == MaintenanceAction.ARCHIVE
        assert record.from_tier == StorageTier.HOT
        assert record.to_tier == StorageTier.COLD
        assert record.timestamp > 0

    def test_m33_record_to_dict(self) -> None:
        """M33.RECORD.TO_DICT: 记录序列化."""
        record = PrecipitationRecord(
            id="test-record-002",
            entry_id="entry-002",
            action=MaintenanceAction.PROMOTE,
            from_tier=StorageTier.WARM,
            to_tier=StorageTier.HOT,
            level=PrecipitationLevel.CRITICAL,
            details={"reason": "high_access"},
        )

        data = record.to_dict()

        assert data["id"] == "test-record-002"
        assert data["action"] == "PROMOTE"
        assert data["from_tier"] == "warm"
        assert data["to_tier"] == "hot"
        assert data["level"] == "CRITICAL"
        assert data["details"]["reason"] == "high_access"
