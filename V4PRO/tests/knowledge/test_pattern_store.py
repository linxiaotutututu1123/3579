"""
模式存储测试.

测试 pattern_store.py 中的模式存储功能。
"""

from __future__ import annotations

import time

import pytest

from src.knowledge.pattern_store import (
    COMMON_PATTERNS,
    MarketRegime,
    Pattern,
    PatternOccurrence,
    PatternSignature,
    PatternStore,
    PatternStrength,
    PatternType,
)
from src.knowledge.base import KnowledgeType


class TestPatternSignature:
    """模式签名测试."""

    def test_to_vector(self) -> None:
        """测试转换为向量."""
        sig = PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            volatility=0.02,
            momentum=0.5,
            trend_strength=0.8,
        )

        vector = sig.to_vector()
        assert len(vector) == 5
        assert vector[0] == 0.03
        assert vector[1] == 1.5

    def test_compute_similarity_identical(self) -> None:
        """测试相同签名的相似度."""
        sig1 = PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            momentum=0.5,
        )
        sig2 = PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            momentum=0.5,
        )

        similarity = sig1.compute_similarity(sig2)
        assert similarity == pytest.approx(1.0, rel=0.01)

    def test_compute_similarity_different(self) -> None:
        """测试不同签名的相似度."""
        sig1 = PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            momentum=0.5,
        )
        sig2 = PatternSignature(
            price_change_pct=-0.05,
            volume_ratio=0.5,
            momentum=-0.5,
        )

        similarity = sig1.compute_similarity(sig2)
        assert similarity < 0.5

    def test_extra_features(self) -> None:
        """测试额外特征."""
        sig = PatternSignature(
            price_change_pct=0.01,
            extra_features={"rsi": 65, "macd": 0.5},
        )

        vector = sig.to_vector()
        assert len(vector) == 7  # 5 base + 2 extra


class TestPattern:
    """模式条目测试."""

    def test_create_pattern(self) -> None:
        """测试创建模式."""
        pattern = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="突破模式",
            description="价格突破阻力位",
            regime=MarketRegime.TRENDING_UP,
            strength=PatternStrength.STRONG,
        )

        assert pattern.id
        assert pattern.pattern_type == PatternType.BREAKOUT
        assert pattern.name == "突破模式"
        assert pattern.created_at > 0

    def test_add_occurrence(self, sample_pattern: Pattern) -> None:
        """测试添加出现记录."""
        initial_count = len(sample_pattern.occurrences)

        sample_pattern.add_occurrence(PatternOccurrence(
            timestamp=time.time(),
            symbol="IF2401",
            price=4100.0,
            outcome=0.015,
            confidence=0.85,
        ))

        assert len(sample_pattern.occurrences) == initial_count + 1

    def test_stats_update(self) -> None:
        """测试统计更新."""
        pattern = Pattern.create(
            pattern_type=PatternType.TREND,
            name="趋势模式",
            description="描述",
        )

        # 添加出现记录
        for i in range(5):
            pattern.add_occurrence(PatternOccurrence(
                timestamp=time.time() - i * 3600,
                symbol="IF2401",
                price=4000 + i * 10,
                outcome=0.01 if i < 3 else -0.005,  # 3赢2输
            ))

        assert pattern.success_rate == pytest.approx(0.6, rel=0.01)
        assert pattern.avg_return != 0

    def test_to_dict(self, sample_pattern: Pattern) -> None:
        """测试转换为字典."""
        data = sample_pattern.to_dict()

        assert data["id"] == sample_pattern.id
        assert data["pattern_type"] == "BREAKOUT"
        assert data["name"] == sample_pattern.name
        assert "signature" in data
        assert "occurrences" in data

    def test_from_dict(self, sample_pattern: Pattern) -> None:
        """测试从字典创建."""
        data = sample_pattern.to_dict()
        restored = Pattern.from_dict(data)

        assert restored.id == sample_pattern.id
        assert restored.pattern_type == sample_pattern.pattern_type
        assert restored.name == sample_pattern.name

    def test_to_knowledge_entry(self, sample_pattern: Pattern) -> None:
        """测试转换为知识条目."""
        entry = sample_pattern.to_knowledge_entry()

        assert entry.knowledge_type == KnowledgeType.PATTERN
        assert "BREAKOUT" in entry.tags
        assert "trending_up" in entry.tags


class TestPatternStore:
    """模式存储测试."""

    def test_register_pattern(
        self,
        pattern_store: PatternStore,
        sample_pattern: Pattern,
    ) -> None:
        """测试注册模式."""
        pattern_id = pattern_store.register(sample_pattern)
        assert pattern_id

        retrieved = pattern_store.get(pattern_id)
        assert retrieved is not None
        assert retrieved.name == sample_pattern.name

    def test_update_pattern(
        self,
        pattern_store: PatternStore,
        sample_pattern: Pattern,
    ) -> None:
        """测试更新模式."""
        pattern_store.register(sample_pattern)

        sample_pattern.name = "更新后的名称"
        pattern_store.update(sample_pattern)

        retrieved = pattern_store.get(sample_pattern.id)
        assert retrieved is not None
        assert retrieved.name == "更新后的名称"

    def test_add_occurrence(self, pattern_store: PatternStore) -> None:
        """测试添加出现记录."""
        pattern = Pattern.create(
            pattern_type=PatternType.REVERSAL,
            name="反转模式",
            description="描述",
        )
        pattern_id = pattern_store.register(pattern)

        occurrence = PatternOccurrence(
            timestamp=time.time(),
            symbol="IF2401",
            price=4000.0,
            outcome=0.02,
        )

        success = pattern_store.add_occurrence(pattern_id, occurrence)
        assert success

        retrieved = pattern_store.get(pattern_id)
        assert retrieved is not None
        assert len(retrieved.occurrences) == 1

    def test_search_by_type(self, pattern_store: PatternStore) -> None:
        """测试按类型搜索."""
        pattern1 = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="突破1",
            description="描述",
        )
        pattern2 = Pattern.create(
            pattern_type=PatternType.REVERSAL,
            name="反转1",
            description="描述",
        )

        pattern_store.register(pattern1)
        pattern_store.register(pattern2)

        results = pattern_store.search(pattern_type=PatternType.BREAKOUT)
        assert len(results) >= 1
        assert all(p.pattern_type == PatternType.BREAKOUT for p in results)

    def test_search_by_regime(self, pattern_store: PatternStore) -> None:
        """测试按市场状态搜索."""
        pattern = Pattern.create(
            pattern_type=PatternType.TREND,
            name="上升趋势",
            description="描述",
            regime=MarketRegime.TRENDING_UP,
        )
        pattern_store.register(pattern)

        results = pattern_store.search(regime=MarketRegime.TRENDING_UP)
        assert len(results) >= 1

    def test_search_by_strength(self, pattern_store: PatternStore) -> None:
        """测试按强度搜索."""
        pattern1 = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="强信号",
            description="描述",
            strength=PatternStrength.STRONG,
        )
        pattern2 = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="弱信号",
            description="描述",
            strength=PatternStrength.WEAK,
        )

        pattern_store.register(pattern1)
        pattern_store.register(pattern2)

        results = pattern_store.search(min_strength=PatternStrength.MODERATE)
        assert all(p.strength.value >= PatternStrength.MODERATE.value for p in results)

    def test_search_by_success_rate(self, pattern_store: PatternStore) -> None:
        """测试按成功率搜索."""
        pattern = Pattern.create(
            pattern_type=PatternType.TREND,
            name="高成功率模式",
            description="描述",
        )
        # 添加高成功率的出现记录
        for i in range(10):
            pattern.add_occurrence(PatternOccurrence(
                timestamp=time.time() - i * 3600,
                symbol="IF2401",
                price=4000,
                outcome=0.01 if i < 8 else -0.005,  # 80%成功率
            ))

        pattern_store.register(pattern)

        results = pattern_store.search(min_success_rate=0.7)
        assert len(results) >= 1

    def test_match_by_signature(
        self,
        pattern_store: PatternStore,
        sample_pattern: Pattern,
    ) -> None:
        """测试按签名匹配."""
        pattern_store.register(sample_pattern)

        # 创建相似的签名
        similar_sig = PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            momentum=0.5,
        )

        matches = pattern_store.match(similar_sig, min_similarity=0.5)
        assert len(matches) >= 1

        # 验证返回的是元组 (pattern, score)
        for pattern, score in matches:
            assert score >= 0.5
            assert isinstance(pattern, Pattern)

    def test_get_by_regime(self, pattern_store: PatternStore) -> None:
        """测试获取特定状态下的模式."""
        pattern = Pattern.create(
            pattern_type=PatternType.VOLATILITY,
            name="高波动模式",
            description="描述",
            regime=MarketRegime.VOLATILE,
        )
        # 添加出现记录使成功率>0.5
        for _ in range(5):
            pattern.add_occurrence(PatternOccurrence(
                timestamp=time.time(),
                symbol="IF2401",
                price=4000,
                outcome=0.01,
            ))

        pattern_store.register(pattern)

        results = pattern_store.get_by_regime(
            regime=MarketRegime.VOLATILE,
            min_success_rate=0.5,
        )
        assert len(results) >= 1

    def test_get_top_patterns(self, pattern_store: PatternStore) -> None:
        """测试获取排名靠前的模式."""
        for i in range(5):
            pattern = Pattern.create(
                pattern_type=PatternType.TREND,
                name=f"模式{i}",
                description="描述",
            )
            # 不同的成功率
            for j in range(10):
                pattern.add_occurrence(PatternOccurrence(
                    timestamp=time.time(),
                    symbol="IF2401",
                    price=4000,
                    outcome=0.01 if j < (5 + i) else -0.01,
                ))
            pattern_store.register(pattern)

        top = pattern_store.get_top_patterns(by="success_rate", limit=3)
        assert len(top) == 3
        # 验证按成功率降序
        for i in range(len(top) - 1):
            assert top[i].success_rate >= top[i + 1].success_rate

    def test_validate_pattern(self, pattern_store: PatternStore) -> None:
        """测试验证模式."""
        pattern = Pattern.create(
            pattern_type=PatternType.BREAKOUT,
            name="测试模式",
            description="描述",
        )
        # 添加少量出现记录
        for i in range(5):
            pattern.add_occurrence(PatternOccurrence(
                timestamp=time.time(),
                symbol="IF2401",
                price=4000,
                outcome=0.01 if i < 2 else -0.01,  # 40%成功率
            ))

        pattern_id = pattern_store.register(pattern)

        result = pattern_store.validate_pattern(
            pattern_id,
            min_occurrences=10,
            min_success_rate=0.5,
        )

        assert not result["valid"]
        assert len(result["issues"]) == 2  # 出现次数不足 + 成功率低

    def test_get_stats(self, pattern_store: PatternStore, sample_pattern: Pattern) -> None:
        """测试统计信息."""
        pattern_store.register(sample_pattern)

        stats = pattern_store.get_stats()
        assert stats["total_patterns"] >= 1


class TestCommonPatterns:
    """预定义模式测试."""

    def test_common_patterns_defined(self) -> None:
        """验证常见模式已定义."""
        assert "double_bottom" in COMMON_PATTERNS
        assert "head_shoulders" in COMMON_PATTERNS
        assert "breakout_high" in COMMON_PATTERNS
        assert "volume_spike" in COMMON_PATTERNS

    def test_double_bottom(self) -> None:
        """测试双底模式."""
        pattern = COMMON_PATTERNS["double_bottom"]
        assert pattern.pattern_type == PatternType.REVERSAL
        assert pattern.regime == MarketRegime.TRENDING_DOWN
        assert pattern.strength == PatternStrength.STRONG

    def test_head_shoulders(self) -> None:
        """测试头肩顶模式."""
        pattern = COMMON_PATTERNS["head_shoulders"]
        assert pattern.pattern_type == PatternType.REVERSAL
        assert "bearish" in pattern.tags
