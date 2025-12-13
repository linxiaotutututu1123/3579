from __future__ import annotations

import hmac
import time
import urllib.parse
from base64 import b64encode
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class DingTalkConfig:
    webhook_url: str
    secret: str | None = None
    timeout_seconds: float = 3.0


def _sign(secret: str, timestamp_ms: int) -> str:
    string_to_sign = f"{timestamp_ms}\n{secret}"
    h = hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod="sha256").digest()
    return urllib.parse.quote_plus(b64encode(h).decode("utf-8"))


def send_markdown(cfg: DingTalkConfig, title: str, markdown_text: str) -> None:
    url = cfg.webhook_url
    if cfg.secret:
        ts = int(time.time() * 1000)
        sign = _sign(cfg.secret, ts)
        connector = "&" if "?" in url else "?"
        url = f"{url}{connector}timestamp={ts}&sign={sign}"

    payload = {"msgtype": "markdown", "markdown": {"title": title, "text": markdown_text}}
    r = requests.post(url, json=payload, timeout=cfg.timeout_seconds)
    r.raise_for_status()