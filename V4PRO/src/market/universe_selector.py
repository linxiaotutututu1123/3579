"""
UniverseSelector - 主力/次主力选择器

V3PRO+ Platform Component - Phase 0
V2 SPEC: 4.2
V2 Scenarios: UNIV.DOMINANT.BASIC, UNIV.SUBDOMINANT.PAIRING,
              UNIV.ROLL.COOLDOWN, UNIV.EXPIRY.GATE

军规级要求:
- 基于 OI + Volume 评分选择主力
- 次主力 != 主力
- 切换后冷却期内不再切换
- 临期合约被排除
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from src.market.instrument_cache import InstrumentCache, InstrumentInfo

# 配置常量（来自 V3PRO_UPGRADE_PLAN 第 18 章）
EXPIRY_BLOCK_DAYS: int = 5
MIN_SWITCH_EDGE: float = 0.1
ROLL_COOLDOWN_S: float = 300.0


@dataclass
class UniverseSnapshot:
    """主力快照.

    Attributes:
        dominant_by_product: 品种→主力合约映射
        subdominant_by_product: 品种→次主力合约映射
        subscribe_set: 需订阅的合约集合
        generated_at: 生成时间戳
    """

    dominant_by_product: dict[str, str] = field(default_factory=dict)
    subdominant_by_product: dict[str, str] = field(default_factory=dict)
    subscribe_set: set[str] = field(default_factory=set)
    generated_at: float = 0.0


class UniverseSelector:
    """主力/次主力选择器.

    V2 Scenarios:
    - UNIV.DOMINANT.BASIC: 能正确选择主力合约
    - UNIV.SUBDOMINANT.PAIRING: 能正确选择次主力合约
    - UNIV.ROLL.COOLDOWN: 主力切换有冷却期
    - UNIV.EXPIRY.GATE: 临期合约被排除

    军规级要求:
    - 基于 open_interest + volume 评分
    - 次主力 != 主力
    - 切换后 ROLL_COOLDOWN_S 内不再切换
    - days_to_expiry < EXPIRY_BLOCK_DAYS 的合约不成为主力
    """

    def __init__(
        self,
        instrument_cache: InstrumentCache,
        expiry_block_days: int = EXPIRY_BLOCK_DAYS,
        min_switch_edge: float = MIN_SWITCH_EDGE,
        roll_cooldown_s: float = ROLL_COOLDOWN_S,
    ) -> None:
        """初始化选择器.

        Args:
            instrument_cache: 合约缓存
            expiry_block_days: 临期排除天数
            min_switch_edge: 主力切换门槛（如 0.1 = 10%）
            roll_cooldown_s: 主力切换冷却（秒）
        """
        self._instrument_cache = instrument_cache
        self._expiry_block_days = expiry_block_days
        self._min_switch_edge = min_switch_edge
        self._roll_cooldown_s = roll_cooldown_s

        self._current: UniverseSnapshot | None = None
        self._last_roll_ts: dict[str, float] = {}  # product -> last roll timestamp

    @property
    def current(self) -> UniverseSnapshot | None:
        """当前快照."""
        return self._current

    def select(
        self,
        oi: dict[str, int],
        vol: dict[str, int],
        now_ts: float,
        trading_day: str | None = None,
    ) -> UniverseSnapshot:
        """选择主力/次主力.

        V2 Scenarios: UNIV.DOMINANT.BASIC, UNIV.SUBDOMINANT.PAIRING,
                      UNIV.ROLL.COOLDOWN, UNIV.EXPIRY.GATE

        Args:
            oi: symbol -> open_interest 映射
            vol: symbol -> volume 映射
            now_ts: 当前时间戳（Unix epoch）
            trading_day: 交易日（YYYYMMDD），用于计算临期

        Returns:
            主力快照
        """
        dominant: dict[str, str] = {}
        subdominant: dict[str, str] = {}
        subscribe_set: set[str] = set()

        # 按品种分组计算
        for product in self._instrument_cache.all_products():
            instruments = self._instrument_cache.get_by_product(product)
            if not instruments:
                continue

            # 过滤临期合约
            valid_instruments = self._filter_expiry(instruments, trading_day)
            if not valid_instruments:
                continue

            # 计算评分（OI * 0.6 + Volume * 0.4）
            scored = []
            for inst in valid_instruments:
                symbol = inst.symbol
                score = oi.get(symbol, 0) * 0.6 + vol.get(symbol, 0) * 0.4
                scored.append((symbol, score))

            # 按评分排序
            scored.sort(key=lambda x: x[1], reverse=True)

            if not scored:
                continue

            # 主力选择（考虑冷却期）
            candidate_dominant = scored[0][0]
            current_dominant = (
                self._current.dominant_by_product.get(product)
                if self._current
                else None
            )

            # 检查冷却期和切换门槛
            if current_dominant and current_dominant != candidate_dominant:
                if self._is_in_cooldown(product, now_ts):
                    # 冷却期内，保持原主力
                    candidate_dominant = current_dominant
                elif not self._meets_switch_edge(
                    current_dominant, candidate_dominant, oi, vol
                ):
                    # 未达到切换门槛，保持原主力
                    candidate_dominant = current_dominant
                else:
                    # 切换主力，更新冷却时间
                    self._last_roll_ts[product] = now_ts
            elif current_dominant is None:
                # 首次设置主力，初始化冷却时间戳（防止快速切换）
                self._last_roll_ts[product] = now_ts

            dominant[product] = candidate_dominant
            subscribe_set.add(candidate_dominant)

            # 次主力选择（必须 != 主力）
            for symbol, _ in scored:
                if symbol != candidate_dominant:
                    subdominant[product] = symbol
                    subscribe_set.add(symbol)
                    break

        snapshot = UniverseSnapshot(
            dominant_by_product=dominant,
            subdominant_by_product=subdominant,
            subscribe_set=subscribe_set,
            generated_at=now_ts,
        )
        self._current = snapshot
        return snapshot

    def _filter_expiry(
        self, instruments: list[InstrumentInfo], trading_day: str | None
    ) -> list[InstrumentInfo]:
        """过滤临期合约.

        V2 Scenario: UNIV.EXPIRY.GATE
        """
        if not trading_day:
            return instruments

        try:
            # Parse YYYYMMDD format directly to date (avoids DTZ007)
            today = date(
                int(trading_day[:4]), int(trading_day[4:6]), int(trading_day[6:8])
            )
        except (ValueError, IndexError):
            return instruments

        valid = []
        for inst in instruments:
            try:
                exp = inst.expire_date
                expiry = date(int(exp[:4]), int(exp[4:6]), int(exp[6:8]))
                days_to_expiry = (expiry - today).days
                if days_to_expiry >= self._expiry_block_days:
                    valid.append(inst)
            except (ValueError, IndexError):
                valid.append(inst)
        return valid

    def _is_in_cooldown(self, product: str, now_ts: float) -> bool:
        """检查是否在冷却期内.

        V2 Scenario: UNIV.ROLL.COOLDOWN
        """
        last_roll = self._last_roll_ts.get(product, 0.0)
        return (now_ts - last_roll) < self._roll_cooldown_s

    def _meets_switch_edge(
        self,
        current: str,
        candidate: str,
        oi: dict[str, int],
        vol: dict[str, int],
    ) -> bool:
        """检查是否达到切换门槛.

        V2 Scenario: UNIV.ROLL.COOLDOWN
        """
        current_score = oi.get(current, 0) * 0.6 + vol.get(current, 0) * 0.4
        candidate_score = oi.get(candidate, 0) * 0.6 + vol.get(candidate, 0) * 0.4

        if current_score == 0:
            return True

        edge = (candidate_score - current_score) / current_score
        return edge >= self._min_switch_edge
