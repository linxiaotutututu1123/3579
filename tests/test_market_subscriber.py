"""
V2 Scenario Tests: MKT.SUBSCRIBER.DIFF_UPDATE

Phase 0 Market Layer - Subscriber
军规级验收测试
"""

from __future__ import annotations

from src.market.subscriber import Subscriber


class TestMktSubscriberDiffUpdate:
    """V2 Scenario: MKT.SUBSCRIBER.DIFF_UPDATE - 订阅集差分更新."""

    RULE_ID = "MKT.SUBSCRIBER.DIFF_UPDATE"
    COMPONENT = "Subscriber"

    def test_diff_add_equals_new_minus_old(self) -> None:
        """add = new - old."""
        subscriber = Subscriber()

        # Initial subscription
        subscriber.update({"rb2501", "rb2505"})

        # Update with new set
        diff = subscriber.update({"rb2501", "rb2505", "hc2501", "hc2505"})

        # Assert - Evidence
        assert diff.add == {"hc2501", "hc2505"}, (
            f"[{self.RULE_ID}] add should be new-old, got {diff.add}"
        )

    def test_diff_remove_equals_old_minus_new(self) -> None:
        """remove = old - new."""
        subscriber = Subscriber()

        # Initial subscription
        subscriber.update({"rb2501", "rb2505", "hc2501"})

        # Update with smaller set
        diff = subscriber.update({"rb2501"})

        # Assert - Evidence
        assert diff.remove == {"rb2505", "hc2501"}, (
            f"[{self.RULE_ID}] remove should be old-new, got {diff.remove}"
        )

    def test_diff_both_add_and_remove(self) -> None:
        """同时有新增和移除."""
        subscriber = Subscriber()

        # Initial
        subscriber.update({"rb2501", "rb2505"})

        # Update: remove rb2505, add hc2501
        diff = subscriber.update({"rb2501", "hc2501"})

        # Assert - Evidence
        assert diff.add == {"hc2501"}, f"[{self.RULE_ID}] add should be {{hc2501}}"
        assert diff.remove == {"rb2505"}, f"[{self.RULE_ID}] remove should be {{rb2505}}"

    def test_diff_no_change(self) -> None:
        """无变化时add和remove都为空."""
        subscriber = Subscriber()

        subscriber.update({"rb2501", "rb2505"})
        diff = subscriber.update({"rb2501", "rb2505"})

        # Assert - Evidence
        assert diff.add == set(), f"[{self.RULE_ID}] add should be empty"
        assert diff.remove == set(), f"[{self.RULE_ID}] remove should be empty"

    def test_subscribe_callback_invoked(self) -> None:
        """订阅回调被调用."""
        added_symbols: set[str] = set()

        def on_subscribe(symbols: set[str]) -> None:
            added_symbols.update(symbols)

        subscriber = Subscriber(on_subscribe=on_subscribe)
        subscriber.update({"rb2501", "rb2505"})

        # Assert - Evidence
        assert added_symbols == {"rb2501", "rb2505"}, (
            f"[{self.RULE_ID}] on_subscribe callback should receive added symbols"
        )

    def test_unsubscribe_callback_invoked(self) -> None:
        """取消订阅回调被调用."""
        removed_symbols: set[str] = set()

        def on_unsubscribe(symbols: set[str]) -> None:
            removed_symbols.update(symbols)

        subscriber = Subscriber(on_unsubscribe=on_unsubscribe)
        subscriber.update({"rb2501", "rb2505"})
        subscriber.update({"rb2501"})

        # Assert - Evidence
        assert removed_symbols == {"rb2505"}, (
            f"[{self.RULE_ID}] on_unsubscribe callback should receive removed symbols"
        )

    def test_current_subscriptions_reflects_state(self) -> None:
        """current_subscriptions 反映当前状态."""
        subscriber = Subscriber()

        subscriber.update({"rb2501", "rb2505"})
        assert subscriber.current_subscriptions == {"rb2501", "rb2505"}

        subscriber.update({"rb2501", "hc2501"})
        assert subscriber.current_subscriptions == {"rb2501", "hc2501"}, (
            f"[{self.RULE_ID}] current_subscriptions should reflect latest state"
        )

    def test_incremental_subscribe(self) -> None:
        """增量订阅."""
        subscriber = Subscriber()

        subscriber.update({"rb2501"})
        diff = subscriber.subscribe({"rb2505", "hc2501"})

        assert diff.add == {"rb2505", "hc2501"}
        assert diff.remove == set()
        assert subscriber.current_subscriptions == {"rb2501", "rb2505", "hc2501"}

    def test_incremental_unsubscribe(self) -> None:
        """增量取消订阅."""
        subscriber = Subscriber()

        subscriber.update({"rb2501", "rb2505", "hc2501"})
        diff = subscriber.unsubscribe({"rb2505", "hc2501"})

        assert diff.add == set()
        assert diff.remove == {"rb2505", "hc2501"}
        assert subscriber.current_subscriptions == {"rb2501"}


class TestSubscriberExtended:
    """Subscriber 扩展测试 - 100% 覆盖率补充."""

    def test_register_callback_new_symbol(self) -> None:
        """注册新合约的回调."""
        subscriber = Subscriber()
        received: list[tuple[str, dict]] = []

        def callback(symbol: str, data: dict) -> None:
            received.append((symbol, data))

        subscriber.register_callback("rb2501", callback)
        subscriber.dispatch("rb2501", {"price": 4000})

        assert len(received) == 1
        assert received[0] == ("rb2501", {"price": 4000})

    def test_register_multiple_callbacks(self) -> None:
        """同一合约注册多个回调."""
        subscriber = Subscriber()
        received1: list[str] = []
        received2: list[str] = []

        subscriber.register_callback("rb2501", lambda s, _d: received1.append(s))
        subscriber.register_callback("rb2501", lambda s, _d: received2.append(s))

        subscriber.dispatch("rb2501", {})

        assert len(received1) == 1
        assert len(received2) == 1

    def test_dispatch_no_callbacks(self) -> None:
        """分发到无回调的合约."""
        subscriber = Subscriber()
        # Should not raise
        subscriber.dispatch("rb2501", {"price": 4000})

    def test_clear_with_unsubscribe_callback(self) -> None:
        """清空时调用取消订阅回调."""
        removed: set[str] = set()

        def on_unsubscribe(symbols: set[str]) -> None:
            removed.update(symbols)

        subscriber = Subscriber(on_unsubscribe=on_unsubscribe)
        subscriber.update({"rb2501", "rb2505"})
        subscriber.clear()

        assert removed == {"rb2501", "rb2505"}
        assert len(subscriber) == 0

    def test_clear_without_callback(self) -> None:
        """清空时无回调."""
        subscriber = Subscriber()
        subscriber.update({"rb2501", "rb2505"})
        subscriber.clear()

        assert len(subscriber) == 0

    def test_clear_empty(self) -> None:
        """清空空订阅."""
        removed: set[str] = set()

        def on_unsubscribe(symbols: set[str]) -> None:
            removed.update(symbols)

        subscriber = Subscriber(on_unsubscribe=on_unsubscribe)
        subscriber.clear()

        # Should not call callback when empty
        assert removed == set()

    def test_len(self) -> None:
        """返回订阅数量."""
        subscriber = Subscriber()
        assert len(subscriber) == 0

        subscriber.update({"rb2501"})
        assert len(subscriber) == 1

        subscriber.update({"rb2501", "rb2505", "hc2501"})
        assert len(subscriber) == 3

    def test_unsubscribe_clears_callbacks(self) -> None:
        """取消订阅时清除回调（需要提供 on_unsubscribe）."""
        received: list[str] = []

        def on_unsub(symbols: set[str]) -> None:
            pass  # Required to trigger callback cleanup

        subscriber = Subscriber(on_unsubscribe=on_unsub)
        subscriber.register_callback("rb2501", lambda s, _d: received.append(s))
        subscriber.update({"rb2501"})

        # Unsubscribe should clear callback (only when on_unsubscribe is set)
        subscriber.update(set())
        subscriber.dispatch("rb2501", {})

        assert len(received) == 0, "Callback should be cleared after unsubscribe"
