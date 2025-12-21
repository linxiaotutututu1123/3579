"""
模式存储 (军规级 v4.0).

V4PRO Platform Component - Phase 8 知识库设计
V4 SPEC: D4 知识库纳入升级计划

模式知识库功能:
- 市场模式识别
- 价格形态存储
- 交易信号模式
- 模式匹配检索

军规覆盖:
- M33: 知识沉淀机制
- M3: 审计日志完整
- M7: 场景回放支持
"""

from __future__ import annotations

import statistics
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from src.knowledge.base import (
    KnowledgeEntry,
    KnowledgePriority,
    KnowledgeStore,
    KnowledgeType,
)


class PatternType(Enum):
    """模式类型枚举.

    定义系统支持的市场模式类型:
    - PRICE: 价格形态
    - VOLUME: 成交量模式
    - VOLATILITY: 波动率模式
    - TREND: 趋势模式
    - REVERSAL: 反转模式
    - BREAKOUT: 突破模式
    - CONSOLIDATION: 整理模式
    - SIGNAL: 信号模式
    """

    PRICE = auto()  # 价格形态
    VOLUME = auto()  # 成交量模式
    VOLATILITY = auto()  # 波动率模式
    TREND = auto()  # 趋势模式
    REVERSAL = auto()  # 反转模式
    BREAKOUT = auto()  # 突破模式
    CONSOLIDATION = auto()  # 整理模式
    SIGNAL = auto()  # 信号模式


class MarketRegime(Enum):
    """市场状态枚举.

    定义市场的宏观状态:
    - TRENDING_UP: 上升趋势
    - TRENDING_DOWN: 下降趋势
    - RANGING: 震荡区间
    - VOLATILE: 高波动
    - CALM: 低波动
    - EXTREME: 极端行情
    """

    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    CALM = "calm"
    EXTREME = "extreme"


class PatternStrength(Enum):
    """模式强度.

    - STRONG: 强信号
    - MODERATE: 中等信号
    - WEAK: 弱信号
    """

    STRONG = 3
    MODERATE = 2
    WEAK = 1


@dataclass
class PatternSignature:
    """模式特征签名.

    用于模式匹配的特征向量。

    Attributes:
        price_change_pct: 价格变化百分比
        volume_ratio: 成交量比率
        volatility: 波动率
        momentum: 动量
        trend_strength: 趋势强度
        support_level: 支撑位
        resistance_level: 阻力位
        extra_features: 额外特征
    """

    price_change_pct: float = 0.0
    volume_ratio: float = 1.0
    volatility: float = 0.0
    momentum: float = 0.0
    trend_strength: float = 0.0
    support_level: float = 0.0
    resistance_level: float = 0.0
    extra_features: dict[str, float] = field(default_factory=dict)

    def to_vector(self) -> list[float]:
        """转换为特征向量.

        Returns:
            特征向量
        """
        base = [
            self.price_change_pct,
            self.volume_ratio,
            self.volatility,
            self.momentum,
            self.trend_strength,
        ]
        return base + list(self.extra_features.values())

    def compute_similarity(self, other: PatternSignature) -> float:
        """计算与另一个签名的相似度.

        使用余弦相似度。

        Args:
            other: 另一个模式签名

        Returns:
            相似度分数 (0-1)
        """
        v1 = self.to_vector()
        v2 = other.to_vector()

        # 对齐长度
        max_len = max(len(v1), len(v2))
        v1 += [0.0] * (max_len - len(v1))
        v2 += [0.0] * (max_len - len(v2))

        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


@dataclass
class PatternOccurrence:
    """模式出现记录.

    记录模式在历史中的出现情况。

    Attributes:
        timestamp: 出现时间戳
        symbol: 交易标的
        price: 出现时价格
        outcome: 后续结果 (涨跌幅)
        duration: 模式持续时间
        confidence: 识别置信度
    """

    timestamp: float
    symbol: str
    price: float
    outcome: float = 0.0
    duration: float = 0.0
    confidence: float = 0.8


@dataclass
class Pattern:
    """模式条目.

    市场模式的核心数据结构。

    Attributes:
        id: 模式ID
        pattern_type: 模式类型
        name: 模式名称
        description: 模式描述
        regime: 市场状态
        strength: 模式强度
        signature: 模式特征签名
        occurrences: 历史出现记录
        success_rate: 成功率
        avg_return: 平均收益
        std_return: 收益标准差
        created_at: 创建时间
        updated_at: 更新时间
        tags: 标签列表
    """

    id: str
    pattern_type: PatternType
    name: str
    description: str
    regime: MarketRegime
    strength: PatternStrength
    signature: PatternSignature
    occurrences: list[PatternOccurrence] = field(default_factory=list)
    success_rate: float = 0.0
    avg_return: float = 0.0
    std_return: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """初始化时设置时间戳和计算统计."""
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = self.created_at
        self._update_stats()

    def _update_stats(self) -> None:
        """更新统计信息."""
        if not self.occurrences:
            return

        outcomes = [occ.outcome for occ in self.occurrences]
        self.avg_return = statistics.mean(outcomes) if outcomes else 0.0
        self.std_return = statistics.stdev(outcomes) if len(outcomes) > 1 else 0.0
        self.success_rate = sum(1 for o in outcomes if o > 0) / len(outcomes) if outcomes else 0.0

    def add_occurrence(self, occurrence: PatternOccurrence) -> None:
        """添加模式出现记录.

        Args:
            occurrence: 出现记录
        """
        self.occurrences.append(occurrence)
        self.updated_at = time.time()
        self._update_stats()

    @classmethod
    def create(
        cls,
        pattern_type: PatternType,
        name: str,
        description: str,
        regime: MarketRegime = MarketRegime.RANGING,
        strength: PatternStrength = PatternStrength.MODERATE,
        signature: PatternSignature | None = None,
        tags: list[str] | None = None,
    ) -> Pattern:
        """创建新的模式条目.

        Args:
            pattern_type: 模式类型
            name: 名称
            description: 描述
            regime: 市场状态
            strength: 模式强度
            signature: 特征签名
            tags: 标签

        Returns:
            Pattern 实例
        """
        return cls(
            id=str(uuid.uuid4()),
            pattern_type=pattern_type,
            name=name,
            description=description,
            regime=regime,
            strength=strength,
            signature=signature or PatternSignature(),
            tags=tags or [],
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典.

        Returns:
            字典表示
        """
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.name,
            "name": self.name,
            "description": self.description,
            "regime": self.regime.value,
            "strength": self.strength.value,
            "signature": {
                "price_change_pct": self.signature.price_change_pct,
                "volume_ratio": self.signature.volume_ratio,
                "volatility": self.signature.volatility,
                "momentum": self.signature.momentum,
                "trend_strength": self.signature.trend_strength,
                "support_level": self.signature.support_level,
                "resistance_level": self.signature.resistance_level,
                "extra_features": self.signature.extra_features,
            },
            "occurrences": [
                {
                    "timestamp": occ.timestamp,
                    "symbol": occ.symbol,
                    "price": occ.price,
                    "outcome": occ.outcome,
                    "duration": occ.duration,
                    "confidence": occ.confidence,
                }
                for occ in self.occurrences
            ],
            "success_rate": self.success_rate,
            "avg_return": self.avg_return,
            "std_return": self.std_return,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pattern:
        """从字典创建实例.

        Args:
            data: 字典数据

        Returns:
            Pattern 实例
        """
        sig_data = data.get("signature", {})
        occurrences_data = data.get("occurrences", [])

        pattern = cls(
            id=data["id"],
            pattern_type=PatternType[data["pattern_type"]],
            name=data["name"],
            description=data["description"],
            regime=MarketRegime(data["regime"]),
            strength=PatternStrength(data["strength"]),
            signature=PatternSignature(
                price_change_pct=sig_data.get("price_change_pct", 0.0),
                volume_ratio=sig_data.get("volume_ratio", 1.0),
                volatility=sig_data.get("volatility", 0.0),
                momentum=sig_data.get("momentum", 0.0),
                trend_strength=sig_data.get("trend_strength", 0.0),
                support_level=sig_data.get("support_level", 0.0),
                resistance_level=sig_data.get("resistance_level", 0.0),
                extra_features=sig_data.get("extra_features", {}),
            ),
            occurrences=[
                PatternOccurrence(
                    timestamp=occ["timestamp"],
                    symbol=occ["symbol"],
                    price=occ["price"],
                    outcome=occ.get("outcome", 0.0),
                    duration=occ.get("duration", 0.0),
                    confidence=occ.get("confidence", 0.8),
                )
                for occ in occurrences_data
            ],
            success_rate=data.get("success_rate", 0.0),
            avg_return=data.get("avg_return", 0.0),
            std_return=data.get("std_return", 0.0),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            tags=data.get("tags", []),
        )
        return pattern

    def to_knowledge_entry(self) -> KnowledgeEntry:
        """转换为通用知识条目.

        Returns:
            KnowledgeEntry 实例
        """
        # 根据模式强度确定优先级
        priority_map = {
            PatternStrength.STRONG: KnowledgePriority.HIGH,
            PatternStrength.MODERATE: KnowledgePriority.MEDIUM,
            PatternStrength.WEAK: KnowledgePriority.LOW,
        }

        return KnowledgeEntry.create(
            knowledge_type=KnowledgeType.PATTERN,
            content=self.to_dict(),
            priority=priority_map.get(self.strength, KnowledgePriority.MEDIUM),
            tags=self.tags + [self.pattern_type.name, self.regime.value],
            source="pattern_store",
        )


class PatternStore:
    """模式知识库.

    专门用于存储和检索市场模式的知识库。

    功能特性:
    - 模式注册和管理
    - 模式匹配检索
    - 统计分析
    - 模式验证

    军规要求:
    - M33: 知识沉淀 - 自动记录模式
    - M3: 审计完整 - 所有操作记录
    - M7: 回放支持 - 支持历史回放
    """

    def __init__(
        self,
        storage: KnowledgeStore[KnowledgeEntry],
        name: str = "pattern_store",
    ) -> None:
        """初始化模式存储.

        Args:
            storage: 底层知识存储
            name: 库名称
        """
        self.storage = storage
        self.name = name
        self._stats = {
            "total_patterns": 0,
            "total_occurrences": 0,
            "match_count": 0,
        }

    def register(self, pattern: Pattern) -> str:
        """注册模式.

        Args:
            pattern: 模式条目

        Returns:
            模式 ID
        """
        entry = pattern.to_knowledge_entry()
        entry_id = self.storage.put(entry)

        self._stats["total_patterns"] += 1
        self._stats["total_occurrences"] += len(pattern.occurrences)

        return entry_id

    def get(self, pattern_id: str) -> Pattern | None:
        """获取模式.

        Args:
            pattern_id: 模式 ID

        Returns:
            模式条目或 None
        """
        entry = self.storage.get(pattern_id)
        if entry:
            return Pattern.from_dict(entry.content)
        return None

    def update(self, pattern: Pattern) -> str:
        """更新模式.

        Args:
            pattern: 模式条目

        Returns:
            模式 ID
        """
        pattern.updated_at = time.time()
        entry = pattern.to_knowledge_entry()
        entry.id = pattern.id
        return self.storage.put(entry)

    def add_occurrence(
        self,
        pattern_id: str,
        occurrence: PatternOccurrence,
    ) -> bool:
        """为模式添加出现记录.

        Args:
            pattern_id: 模式 ID
            occurrence: 出现记录

        Returns:
            是否成功
        """
        pattern = self.get(pattern_id)
        if pattern:
            pattern.add_occurrence(occurrence)
            self.update(pattern)
            self._stats["total_occurrences"] += 1
            return True
        return False

    def search(
        self,
        pattern_type: PatternType | None = None,
        regime: MarketRegime | None = None,
        min_strength: PatternStrength | None = None,
        min_success_rate: float = 0.0,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[Pattern]:
        """搜索模式.

        Args:
            pattern_type: 模式类型过滤
            regime: 市场状态过滤
            min_strength: 最低强度
            min_success_rate: 最低成功率
            symbol: 标的过滤
            limit: 返回数量限制

        Returns:
            匹配的模式列表
        """
        # 构建标签过滤
        tags: list[str] = []
        if pattern_type:
            tags.append(pattern_type.name)
        if regime:
            tags.append(regime.value)

        # 查询知识库
        entries = self.storage.query(
            knowledge_type=KnowledgeType.PATTERN,
            tags=tags if tags else None,
            limit=limit * 2,
        )

        # 转换并过滤
        results: list[Pattern] = []
        for entry in entries:
            pattern = Pattern.from_dict(entry.content)

            if min_strength and pattern.strength.value < min_strength.value:
                continue
            if min_success_rate > 0 and pattern.success_rate < min_success_rate:
                continue
            if symbol:
                # 检查是否有该标的的出现记录
                has_symbol = any(occ.symbol == symbol for occ in pattern.occurrences)
                if not has_symbol:
                    continue

            results.append(pattern)
            if len(results) >= limit:
                break

        return results

    def match(
        self,
        signature: PatternSignature,
        min_similarity: float = 0.7,
        limit: int = 10,
    ) -> list[tuple[Pattern, float]]:
        """匹配相似模式.

        基于特征签名查找相似模式。

        Args:
            signature: 当前特征签名
            min_similarity: 最低相似度阈值
            limit: 返回数量限制

        Returns:
            匹配的模式列表及其相似度分数
        """
        # 获取所有模式
        all_patterns = self.search(limit=1000)

        # 计算相似度
        scored: list[tuple[Pattern, float]] = []
        for pattern in all_patterns:
            similarity = signature.compute_similarity(pattern.signature)
            if similarity >= min_similarity:
                scored.append((pattern, similarity))

        # 按相似度排序
        scored.sort(key=lambda x: x[1], reverse=True)
        self._stats["match_count"] += 1

        return scored[:limit]

    def get_by_regime(
        self,
        regime: MarketRegime,
        min_success_rate: float = 0.5,
        limit: int = 20,
    ) -> list[Pattern]:
        """获取特定市场状态下的有效模式.

        Args:
            regime: 市场状态
            min_success_rate: 最低成功率
            limit: 返回数量限制

        Returns:
            匹配的模式列表
        """
        return self.search(
            regime=regime,
            min_success_rate=min_success_rate,
            limit=limit,
        )

    def get_top_patterns(
        self,
        by: str = "success_rate",
        limit: int = 10,
    ) -> list[Pattern]:
        """获取排名靠前的模式.

        Args:
            by: 排序依据 (success_rate, avg_return, occurrences)
            limit: 返回数量限制

        Returns:
            排名靠前的模式列表
        """
        all_patterns = self.search(limit=1000)

        if by == "success_rate":
            all_patterns.sort(key=lambda p: p.success_rate, reverse=True)
        elif by == "avg_return":
            all_patterns.sort(key=lambda p: p.avg_return, reverse=True)
        elif by == "occurrences":
            all_patterns.sort(key=lambda p: len(p.occurrences), reverse=True)

        return all_patterns[:limit]

    def validate_pattern(
        self,
        pattern_id: str,
        min_occurrences: int = 10,
        min_success_rate: float = 0.5,
    ) -> dict[str, Any]:
        """验证模式有效性.

        Args:
            pattern_id: 模式 ID
            min_occurrences: 最少出现次数
            min_success_rate: 最低成功率

        Returns:
            验证结果
        """
        pattern = self.get(pattern_id)
        if not pattern:
            return {"valid": False, "reason": "pattern_not_found"}

        issues: list[str] = []

        if len(pattern.occurrences) < min_occurrences:
            issues.append(f"insufficient_occurrences: {len(pattern.occurrences)} < {min_occurrences}")

        if pattern.success_rate < min_success_rate:
            issues.append(f"low_success_rate: {pattern.success_rate:.2%} < {min_success_rate:.2%}")

        return {
            "valid": len(issues) == 0,
            "pattern_id": pattern_id,
            "occurrences": len(pattern.occurrences),
            "success_rate": pattern.success_rate,
            "avg_return": pattern.avg_return,
            "issues": issues,
        }

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        Returns:
            统计数据字典
        """
        return {
            **self._stats,
            "storage_stats": self.storage.get_stats(),
        }


# 预定义的常见模式模板
COMMON_PATTERNS = {
    "double_bottom": Pattern.create(
        pattern_type=PatternType.REVERSAL,
        name="双底反转",
        description="价格形成W形态后向上突破",
        regime=MarketRegime.TRENDING_DOWN,
        strength=PatternStrength.STRONG,
        signature=PatternSignature(
            price_change_pct=-0.05,
            momentum=0.3,
            trend_strength=-0.5,
        ),
        tags=["reversal", "bullish"],
    ),
    "head_shoulders": Pattern.create(
        pattern_type=PatternType.REVERSAL,
        name="头肩顶",
        description="价格形成头肩形态后向下突破",
        regime=MarketRegime.TRENDING_UP,
        strength=PatternStrength.STRONG,
        signature=PatternSignature(
            price_change_pct=0.08,
            momentum=-0.2,
            trend_strength=0.6,
        ),
        tags=["reversal", "bearish"],
    ),
    "breakout_high": Pattern.create(
        pattern_type=PatternType.BREAKOUT,
        name="突破前高",
        description="价格突破前期高点",
        regime=MarketRegime.TRENDING_UP,
        strength=PatternStrength.MODERATE,
        signature=PatternSignature(
            price_change_pct=0.03,
            volume_ratio=1.5,
            momentum=0.5,
        ),
        tags=["breakout", "bullish"],
    ),
    "volume_spike": Pattern.create(
        pattern_type=PatternType.VOLUME,
        name="放量异动",
        description="成交量突然放大",
        regime=MarketRegime.VOLATILE,
        strength=PatternStrength.MODERATE,
        signature=PatternSignature(
            volume_ratio=3.0,
            volatility=0.05,
        ),
        tags=["volume", "alert"],
    ),
}
