"""夜盘交易策略模块 (军规级 v4.0).

本模块提供夜盘交易策略的实现，包括：
- 夜盘基础设施: 配置类、时段管理器
- 夜盘跳空闪电战策略
- 夜盘策略基类

军规覆盖:
- M1: 单一信号源 - 每个策略实例生成唯一信号
- M15: 夜盘跨日处理 - 夜盘时段特殊处理

示例:
    >>> from src.strategy.night_session import NightGapFlashStrategy
    >>> strategy = NightGapFlashStrategy(gap_threshold=0.01)
    >>> signal = strategy.generate_signal(market_data)
"""

from __future__ import annotations

from src.strategy.night_session.base import (
    InternationalMarket,
    NightSessionConfig,
    NightSessionManager,
    SessionType,
    TimeRange,
)
from src.strategy.night_session.gap_flash import (
    GapDirection,
    GapInfo,
    MarketContext,
    NightGapFlashStrategy,
    NightSessionStrategy,
    StrategySignal,
)

__all__ = [
    # base.py
    "InternationalMarket",
    "NightSessionConfig",
    "NightSessionManager",
    "SessionType",
    "TimeRange",
    # gap_flash.py
    "GapDirection",
    "GapInfo",
    "MarketContext",
    "NightGapFlashStrategy",
    "NightSessionStrategy",
    "StrategySignal",
]
