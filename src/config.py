from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class DingTalkSettings:
    webhook_url: str
    secret: str | None


@dataclass(frozen=True)
class AppSettings:
    baseline_time: str = "09:00:00"
    dingtalk: DingTalkSettings | None = None
    trade_mode: str = "PAPER"
    strategy_name: str = "top_tier"
    strategy_symbols: tuple[str, ...] = ("AO", "SA", "LC")


def load_settings() -> AppSettings:
    webhook = getenv("DINGTALK_WEBHOOK_URL", "").strip()
    secret = getenv("DINGTALK_SECRET", "").strip() or None
    baseline_time = getenv("BASELINE_TIME", "09:00:00").strip()
    trade_mode = getenv("TRADE_MODE", "PAPER").strip().upper()
    strategy_name = getenv("STRATEGY_NAME", "top_tier").strip()
    strategy_symbols_str = getenv("STRATEGY_SYMBOLS", "AO,SA,LC").strip()
    strategy_symbols = tuple(s.strip() for s in strategy_symbols_str.split(",") if s.strip())

    dingtalk = None
    if webhook:
        dingtalk = DingTalkSettings(webhook_url=webhook, secret=secret)

    return AppSettings(
        baseline_time=baseline_time,
        dingtalk=dingtalk,
        trade_mode=trade_mode,
        strategy_name=strategy_name,
        strategy_symbols=strategy_symbols,
    )
