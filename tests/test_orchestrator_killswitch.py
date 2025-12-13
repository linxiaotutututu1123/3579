from __future__ import annotations

from src.execution.broker import Broker, OrderAck
from src.execution.flatten_executor import FlattenExecutor
from src.execution.flatten_plan import BookTop, FlattenSpec, PositionToClose
from src.execution.order_types import OrderIntent
from src.orchestrator import handle_risk_update
from src.risk.events import RiskEventType
from src.risk.manager import RiskManager
from src.risk.state import AccountSnapshot, RiskConfig


class CountingBroker(Broker):
    def __init__(self) -> None:
        self.calls: list[OrderIntent] = []

    def place_order(self, intent: OrderIntent) -> OrderAck:
        self.calls.append(intent)
        return OrderAck(order_id=f"oid-{len(self.calls)}")


def test_kill_switch_triggers_flatten_execution() -> None:
    # RiskManager setup
    def cancel_all() -> None:
        pass

    def flatten_all() -> None:
        pass

    rm = RiskManager(
        RiskConfig(dd_limit=-0.03, cooldown_seconds=10),
        cancel_all_cb=cancel_all,
        force_flatten_all_cb=flatten_all,
        now_cb=lambda: 0.0,
    )
    rm.on_day_start_0900(AccountSnapshot(equity=1_000_000.0, margin_used=0.0))
    rm.drain_events()  # ignore baseline event

    # Broker/Executor
    broker = CountingBroker()
    exe = FlattenExecutor(broker)

    positions = [
        PositionToClose(symbol="AO", net_qty=5, today_qty=2, yesterday_qty=3),
        PositionToClose(symbol="SA", net_qty=-4, today_qty=1, yesterday_qty=3),
    ]
    books = {
        "AO": BookTop(best_bid=100.0, best_ask=101.0, tick=1.0),
        "SA": BookTop(best_bid=200.0, best_ask=201.0, tick=1.0),
    }

    res = handle_risk_update(
        risk=rm,
        executor=exe,
        snap=AccountSnapshot(equity=969_000.0, margin_used=0.0),  # -3.1% triggers
        positions=positions,
        books=books,
        flatten_spec=FlattenSpec(stage2_requotes=0, stage3_max_cross_levels=0),
    )

    assert any(e.type == RiskEventType.KILL_SWITCH_FIRED for e in res.risk_events)
    assert len(broker.calls) > 0
    assert len(res.execution_records) == len(broker.calls)
