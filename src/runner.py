from __future__ import annotations

from dataclasses import dataclass

from src.config import AppSettings, load_settings
from src.execution.broker import Broker
from src.execution.flatten_executor import FlattenExecutor
from src.risk.manager import RiskManager
from src.risk.state import RiskConfig


@dataclass(frozen=True)
class Components:
    settings: AppSettings
    risk: RiskManager
    flatten: FlattenExecutor


def init_components(*, broker: Broker, risk_cfg: RiskConfig | None = None) -> Components:
    """
    App composition root.
    - Loads settings/env
    - Wires RiskManager + Executor
    - Returns components (no side effects like network calls)
    """
    settings = load_settings()

    cfg = risk_cfg or RiskConfig()

    # callbacks are still stubs here; later Step we will wire to Broker/OMS cancel/flatten actions
    def cancel_all() -> None:
        # placeholder: integrate with OMS later
        return

    def force_flatten_all() -> None:
        # placeholder: integrate with flatten runner later
        return

    risk = RiskManager(cfg, cancel_all_cb=cancel_all, force_flatten_all_cb=force_flatten_all)
    flatten = FlattenExecutor(broker)

    return Components(settings=settings, risk=risk, flatten=flatten)