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


def load_settings() -> AppSettings:
    webhook = getenv("DINGTALK_WEBHOOK_URL", "").strip()
    secret = getenv("DINGTALK_SECRET", "").strip() or None
    baseline_time = getenv("BASELINE_TIME", "09:00:00").strip()

    dingtalk = None
    if webhook:
        dingtalk = DingTalkSettings(webhook_url=webhook, secret=secret)

    return AppSettings(baseline_time=baseline_time, dingtalk=dingtalk)