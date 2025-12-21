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
