Param(
  [Parameter(Position=0)]
  [string]$Root = "."
)

$ErrorActionPreference = "Stop"

function Ensure-Dir([string]$path) {
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null }
}

function Write-FileUtf8([string]$path, [string]$content) {
  $dir = Split-Path $path -Parent
  if ($dir -and $dir -ne "." -and -not (Test-Path $dir)) { Ensure-Dir $dir }

  # Force UTF8 (no BOM) for consistency
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($path, $content, $utf8NoBom)
}

Set-Location $Root

# Directories
Ensure-Dir ".github/workflows"
Ensure-Dir "scripts"
Ensure-Dir "src/risk"
Ensure-Dir "src/alerts"
Ensure-Dir "tests"

# Files
Write-FileUtf8 ".github/workflows/ci.yml" @"
name: ci

on:
  push:
    branches: ["**"]
  pull_request:
    branches: ["**"]

jobs:
  windows-check:
    runs-on: windows-latest
    timeout-minutes: 20
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Create venv
        shell: pwsh
        run: |
          python -m venv .venv
          .\.venv\Scripts\python.exe -m pip install -U pip

      - name: Install deps
        shell: pwsh
        run: |
          .\.venv\Scripts\pip.exe install -r requirements.txt -r requirements-dev.txt

      - name: Run quality gate
        shell: pwsh
        run: |
          .\.venv\Scripts\python.exe -m ruff format --check .
          .\.venv\Scripts\python.exe -m ruff check .
          .\.venv\Scripts\python.exe -m mypy .
          .\.venv\Scripts\python.exe -m pytest -q

      - name: Export context artifact (optional)
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path artifacts\context | Out-Null
          try { tree /F > artifacts\context\tree.txt } catch {}
          try { git rev-parse HEAD > artifacts\context\git_commit.txt } catch {}
          try { git status --porcelain=v1 > artifacts\context\git_status.txt } catch {}
          .\.venv\Scripts\python.exe scripts\export_context.py --out artifacts\context\context.md

      - name: Upload context artifact
        uses: actions/upload-artifact@v4
        with:
          name: context
          path: artifacts/context
          if-no-files-found: ignore
"@

Write-FileUtf8 "README.md" @"
# cn-futures-auto-trader (Windows + GitHub CI gate)

This repo is a **skeleton** for a CN futures fully-automated trading system.
It implements a strict, testable RiskPolicy backbone and uses **GitHub Actions** as the only
“automatic self-check” gate after each feature.

## Quality gate (GitHub only)
Workflow: `.github/workflows/ci.yml`

For every push/PR, CI runs:
- ruff format check
- ruff lint
- mypy
- pytest

### How you work with Claude (recommended)
For each small feature:
1. Ask Claude to modify only the files for that feature.
2. Commit + push.
3. Check GitHub Actions green.
4. Only then start the next feature.

## Locked spec
See: `SPEC_RISK.md`

## Run locally (optional)
You *can* run locally, but per your requirement CI is the gate.
- `./scripts/dev.ps1 init`
- `./scripts/dev.ps1 check`

(These mimic the CI steps.)
"@

Write-FileUtf8 "SPEC_RISK.md" @"
# RiskPolicy v1.1 (Final)

## Instruments
- AO (SHFE), SA (CZCE), LC (GFEX) + 2 auto-selected later

## Daily baseline
- E0 snapshot at **09:00:00** (day session)

## Kill switch (daily DD)
- Trigger: `DD(t) <= -3%` and `kill_switch_fired_today == false`
- Action: `CancelAll -> ForceFlattenAll -> COOLDOWN(90min)`
- After cooldown: `RECOVERY`
  - `recovery_risk_multiplier = 0.30`
  - `max_margin_recovery = 0.40`
- Second time `DD(t) <= -3%` in same trading day: `LOCKED` (no opening until next day)

## Force flatten (execution policy)
- Order type: **LIMIT only** (no FAK/FOK)
- Prefer closing today positions first (**CloseToday**); if rejected, fallback to **Close**
- Stage1: `t1=5s` near best (min impact)
- Stage2: `dt=2s`, `n=12` requotes, `step=1 tick`
- Stage3: aggressive but limited: cross `<= 12 levels` from best
- Alerts: DingTalk webhook
"@

Write-FileUtf8 "requirements.txt" @"
pydantic>=2.7
python-dotenv>=1.0
requests>=2.32
PyYAML>=6.0
"@

Write-FileUtf8 "requirements-dev.txt" @"
ruff>=0.7
mypy>=1.11
pytest>=8.2
types-requests>=2.32
"@

Write-FileUtf8 "pyproject.toml" @"
[project]
name = "cn-futures-auto-trader"
version = "0.1.0"
requires-python = ">=3.11"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "SIM"]
ignore = []

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
no_implicit_optional = true
strict_equality = true
pretty = true

[tool.pytest.ini_options]
testpaths = ["tests"]
"@

Write-FileUtf8 ".env.example" @"
DINGTALK_WEBHOOK_URL=
DINGTALK_SECRET=
BASELINE_TIME=09:00:00
"@

Write-FileUtf8 "scripts/dev.ps1" @"
Param(
  [Parameter(Position=0)]
  [ValidateSet("init","check","fix","test","type","lint","fmt","context","clean")]
  [string]`$Task = "check"
)

`$ErrorActionPreference = "Stop"

`$VenvPath = ".venv"
`$Py = Join-Path `$VenvPath "Scripts\python.exe"
`$Pip = Join-Path `$VenvPath "Scripts\pip.exe"

function Ensure-Venv {
  if (-not (Test-Path `$VenvPath)) {
    python -m venv `$VenvPath
  }
}

function Install-Deps {
  & `$Py -m pip install -U pip
  & `$Pip install -r requirements.txt -r requirements-dev.txt
}

function Ensure-Artifacts {
  New-Item -ItemType Directory -Force -Path "artifacts\context" | Out-Null
}

switch (`$Task) {
  "init" {
    Ensure-Venv
    Install-Deps
  }
  "fmt" {
    Ensure-Venv
    & `$Py -m ruff format .
  }
  "lint" {
    Ensure-Venv
    & `$Py -m ruff check .
  }
  "type" {
    Ensure-Venv
    & `$Py -m mypy .
  }
  "test" {
    Ensure-Venv
    & `$Py -m pytest -q
  }
  "fix" {
    Ensure-Venv
    & `$Py -m ruff format .
    & `$Py -m ruff check . --fix
  }
  "context" {
    Ensure-Venv
    Ensure-Artifacts
    try { tree /F > artifacts\context\tree.txt } catch {}
    try {
      git rev-parse HEAD > artifacts\context\git_commit.txt
      git status --porcelain=v1 > artifacts\context\git_status.txt
    } catch {}
    & `$Py scripts\export_context.py --out artifacts\context\context.md
  }
  "check" {
    Ensure-Venv
    powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 context
    & `$Py -m ruff format --check .
    & `$Py -m ruff check .
    & `$Py -m mypy .
    & `$Py -m pytest -q
  }
  "clean" {
    Remove-Item -Recurse -Force artifacts -ErrorAction SilentlyContinue
  }
}
"@

Write-FileUtf8 "scripts/export_context.py" @"
from __future__ import annotations

import argparse
from pathlib import Path

INCLUDE_FILES = [
    "README.md",
    "SPEC_RISK.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "src/risk/manager.py",
    "src/risk/state.py",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output markdown path")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Project Context (for Claude)\n")
    lines.append("## Quality gate\n")
    lines.append(
        "- GitHub Actions runs: ruff format --check, ruff check, mypy, pytest\n"
        "- Keep CI green after each feature\n"
    )
    lines.append("\n## Locked risk spec\n")
    lines.append("- See SPEC_RISK.md\n")

    lines.append("\n## Included files\n")
    for f in INCLUDE_FILES:
        if Path(f).exists():
            lines.append(f"- {f}")

    out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
"@

Write-FileUtf8 "src/__init__.py" @"
__all__ = []
"@

Write-FileUtf8 "src/config.py" @"
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
"@

Write-FileUtf8 "src/main.py" @"
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from src.config import load_settings


def main() -> None:
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    settings = load_settings()
    print("cn-futures-auto-trader: boot OK (skeleton)")
    print(f"baseline_time={settings.baseline_time}")
    print(f"dingtalk_enabled={settings.dingtalk is not None}")


if __name__ == "__main__":
    main()
"@

Write-FileUtf8 "src/risk/__init__.py" @"
__all__ = ["state", "manager"]
"@

Write-FileUtf8 "src/risk/state.py" @"
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskMode(str, Enum):
    NORMAL = "NORMAL"
    COOLDOWN = "COOLDOWN"
    RECOVERY = "RECOVERY"
    LOCKED = "LOCKED"


@dataclass(frozen=True)
class RiskConfig:
    dd_limit: float = -0.03
    cooldown_seconds: int = 90 * 60
    recovery_risk_multiplier: float = 0.30
    max_margin_normal: float = 0.70
    max_margin_recovery: float = 0.40


@dataclass(frozen=True)
class AccountSnapshot:
    equity: float
    margin_used: float

    @property
    def margin_ratio(self) -> float:
        if self.equity <= 0:
            return 1.0
        return self.margin_used / self.equity


@dataclass
class RiskState:
    mode: RiskMode = RiskMode.NORMAL
    kill_switch_fired_today: bool = False
    e0: float | None = None
    cooldown_end_ts: float | None = None

    def dd(self, equity_now: float) -> float:
        if self.e0 is None or self.e0 == 0:
            return 0.0
        return (equity_now - self.e0) / self.e0
"@

Write-FileUtf8 "src/risk/manager.py" @"
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from src.risk.state import AccountSnapshot, RiskConfig, RiskMode, RiskState


@dataclass(frozen=True)
class Decision:
    allow_open: bool
    reason: str = ""


CancelAllCb = Callable[[], None]
ForceFlattenAllCb = Callable[[], None]


class RiskManager:
    def __init__(
        self,
        cfg: RiskConfig,
        *,
        cancel_all_cb: CancelAllCb,
        force_flatten_all_cb: ForceFlattenAllCb,
        now_cb=time.time,
    ) -> None:
        self.cfg = cfg
        self.state = RiskState()
        self._cancel_all = cancel_all_cb
        self._force_flatten_all = force_flatten_all_cb
        self._now = now_cb

    def on_day_start_0900(self, snap: AccountSnapshot) -> None:
        self.state.e0 = snap.equity
        self.state.mode = RiskMode.NORMAL
        self.state.kill_switch_fired_today = False
        self.state.cooldown_end_ts = None

    def update(self, snap: AccountSnapshot) -> None:
        if self.state.e0 is None:
            return

        now_ts = self._now()

        if self.state.mode == RiskMode.COOLDOWN and self.state.cooldown_end_ts is not None:
            if now_ts >= self.state.cooldown_end_ts:
                self.state.mode = RiskMode.RECOVERY

        dd = self.state.dd(snap.equity)

        if dd <= self.cfg.dd_limit:
            if not self.state.kill_switch_fired_today:
                self._fire_kill_switch()
            else:
                self.state.mode = RiskMode.LOCKED

    def _fire_kill_switch(self) -> None:
        self.state.kill_switch_fired_today = True
        self.state.mode = RiskMode.COOLDOWN
        self.state.cooldown_end_ts = self._now() + self.cfg.cooldown_seconds
        self._cancel_all()
        self._force_flatten_all()

    def can_open(self, snap: AccountSnapshot) -> Decision:
        if self.state.mode in (RiskMode.COOLDOWN, RiskMode.LOCKED):
            return Decision(False, f"blocked_by_mode:{self.state.mode.value}")

        max_margin = (
            self.cfg.max_margin_normal
            if self.state.mode == RiskMode.NORMAL
            else self.cfg.max_margin_recovery
        )
        if snap.margin_ratio > max_margin:
            return Decision(False, "blocked_by_margin_ratio")

        return Decision(True, "ok")
"@

Write-FileUtf8 "src/alerts/__init__.py" @"
__all__ = ["dingtalk"]
"@

Write-FileUtf8 "src/alerts/dingtalk.py" @"
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
"@

Write-FileUtf8 "tests/test_risk_state_machine.py" @"
from __future__ import annotations

from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig, RiskMode


def test_kill_switch_then_cooldown_then_recovery() -> None:
    calls = {"cancel": 0, "flatten": 0}
    now = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    cfg = RiskConfig(dd_limit=-0.03, cooldown_seconds=90 * 60)
    rm = RiskManager(cfg, cancel_all_cb=cancel_all, force_flatten_all_cb=flatten_all, now_cb=now_cb)

    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.NORMAL

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.COOLDOWN
    assert rm.state.kill_switch_fired_today is True
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1

    now["t"] = 60 * 60
    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.COOLDOWN

    now["t"] = 90 * 60 + 1
    rm.update(AccountSnapshot(equity=980_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.RECOVERY


def test_second_breach_locks_for_day() -> None:
    calls = {"cancel": 0, "flatten": 0}
    now = {"t": 0.0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    def now_cb() -> float:
        return now["t"]

    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=1),
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=now_cb,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.COOLDOWN
    assert calls["cancel"] == 1

    now["t"] = 2
    rm.update(AccountSnapshot(equity=980_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.RECOVERY

    rm.update(AccountSnapshot(equity=969_000.0, margin_used=0.0))
    assert rm.state.mode == RiskMode.LOCKED
    assert calls["cancel"] == 1
    assert calls["flatten"] == 1


def test_margin_gate_blocks_open_in_recovery() -> None:
    calls = {"cancel": 0, "flatten": 0}

    def cancel_all() -> None:
        calls["cancel"] += 1

    def flatten_all() -> None:
        calls["flatten"] += 1

    rm = RiskManager(
        RiskConfig(max_margin_recovery=0.40),
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))

    rm.state.mode = RiskMode.RECOVERY
    d = rm.can_open(AccountSnapshot(equity=1_000_000.0, margin_used=450_000.0))
    assert d.allow_open is False
    assert d.reason == "blocked_by_margin_ratio"
"@

Write-Host "OK. Files generated. Next:"
Write-Host "  git add ."
Write-Host "  git commit -m 'chore: bootstrap skeleton + ci'"
Write-Host "  git push"