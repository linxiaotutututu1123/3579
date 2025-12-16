"""策略回退管理器测试 (军规级 v4.0)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.strategy.fallback import (
    DEFAULT_FALLBACK_CHAINS,
    FallbackConfig,
    FallbackEvent,
    FallbackManager,
    FallbackReason,
    FallbackResult,
)


@dataclass
class MockTargetPortfolio:
    """模拟目标组合."""
    positions: dict[str, float]


class MockStrategy:
    """模拟策略."""

    def __init__(self, name: str, should_fail: bool = False, delay: float = 0) -> None:
        self.name = name
        self.should_fail = should_fail
        self.delay = delay

    def on_tick(self, state: Any) -> MockTargetPortfolio:
        import time
        if self.delay > 0:
            time.sleep(self.delay)
        if self.should_fail:
            raise RuntimeError(f"{self.name} failed")
        return MockTargetPortfolio(positions={self.name: 1.0})


class TestFallbackReason:
    """回退原因测试."""

    def test_enum_values(self) -> None:
        """测试枚举值."""
        assert FallbackReason.EXCEPTION.value == "exception"
        assert FallbackReason.TIMEOUT.value == "timeout"
        assert FallbackReason.NOT_REGISTERED.value == "not_registered"
        assert FallbackReason.MANUAL.value == "manual"


class TestFallbackEvent:
    """回退事件测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        event = FallbackEvent(
            ts=1000.0,
            original_strategy="top_tier",
            fallback_strategy="simple_ai",
            reason=FallbackReason.EXCEPTION,
            error_message="Test error",
            latency_ms=50.0,
        )
        d = event.to_dict()
        assert d["event_type"] == "fallback"
        assert d["original_strategy"] == "top_tier"
        assert d["reason"] == "exception"


class TestFallbackConfig:
    """回退配置测试."""

    def test_defaults(self) -> None:
        """测试默认值."""
        config = FallbackConfig()
        assert config.timeout_s == 1.0
        assert config.max_chain_depth == 5
        assert config.enable_timeout is True
        assert config.enable_exception is True


class TestFallbackResult:
    """回退结果测试."""

    def test_success(self) -> None:
        """测试成功结果."""
        result = FallbackResult(
            portfolio=MockTargetPortfolio({}),
            strategy_used="top_tier",
            fallback_occurred=False,
        )
        assert result.success is True

    def test_failure(self) -> None:
        """测试失败结果."""
        result = FallbackResult(
            portfolio=None,
            strategy_used="top_tier",
            fallback_occurred=True,
        )
        assert result.success is False


class TestFallbackManager:
    """回退管理器测试."""

    def test_register_strategy(self) -> None:
        """测试注册策略."""
        manager = FallbackManager()
        strategy = MockStrategy("test")
        manager.register("test", strategy)
        assert "test" in manager.get_registered_strategies()

    def test_unregister_strategy(self) -> None:
        """测试注销策略."""
        manager = FallbackManager()
        strategy = MockStrategy("test")
        manager.register("test", strategy)
        assert manager.unregister("test") is True
        assert manager.unregister("unknown") is False

    def test_get_chain(self) -> None:
        """测试获取回退链."""
        manager = FallbackManager()
        chain = manager.get_chain("top_tier")
        assert "simple_ai" in chain

    def test_set_chain(self) -> None:
        """测试设置回退链."""
        manager = FallbackManager()
        manager.set_chain("custom", ["a", "b"])
        assert manager.get_chain("custom") == ["a", "b"]

    def test_execute_success(self) -> None:
        """测试成功执行."""
        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)
        manager.register("test", MockStrategy("test"))

        result = manager.execute("test", {})
        assert result.success
        assert result.strategy_used == "test"
        assert result.fallback_occurred is False

    def test_execute_fallback_on_exception(self) -> None:
        """测试异常回退."""
        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)
        manager.register("primary", MockStrategy("primary", should_fail=True))
        manager.register("fallback", MockStrategy("fallback"))
        manager.set_chain("primary", ["fallback"])

        result = manager.execute("primary", {})
        assert result.success
        assert result.strategy_used == "fallback"
        assert result.fallback_occurred is True

    def test_execute_not_registered(self) -> None:
        """测试未注册策略."""
        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)
        manager.register("simple_ai", MockStrategy("simple_ai"))

        result = manager.execute("unknown", {})
        # 应该回退到simple_ai
        assert result.fallback_occurred

    def test_execute_timeout(self) -> None:
        """测试超时回退."""
        config = FallbackConfig(timeout_s=0.01, enable_timeout=True)
        manager = FallbackManager(config)
        manager.register("slow", MockStrategy("slow", delay=1.0))
        manager.register("simple_ai", MockStrategy("simple_ai"))
        manager.set_chain("slow", ["simple_ai"])

        result = manager.execute("slow", {})
        assert result.strategy_used == "simple_ai"
        manager.close()

    def test_add_event_handler(self) -> None:
        """测试添加事件处理器."""
        events: list[FallbackEvent] = []

        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)
        manager.add_event_handler(lambda e: events.append(e))
        manager.register("fail", MockStrategy("fail", should_fail=True))
        manager.register("simple_ai", MockStrategy("simple_ai"))
        manager.set_chain("fail", ["simple_ai"])

        manager.execute("fail", {})
        assert len(events) > 0

    def test_get_fallback_counts(self) -> None:
        """测试获取回退计数."""
        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)
        manager.register("fail", MockStrategy("fail", should_fail=True))
        manager.register("simple_ai", MockStrategy("simple_ai"))
        manager.set_chain("fail", ["simple_ai"])

        manager.execute("fail", {})
        counts = manager.get_fallback_counts()
        assert "fail" in counts

    def test_reset_counts(self) -> None:
        """测试重置计数."""
        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)
        manager._fallback_counts["test"] = 5
        manager.reset_counts()
        assert len(manager.get_fallback_counts()) == 0

    def test_is_chain_valid(self) -> None:
        """测试链有效性."""
        manager = FallbackManager()
        manager.register("a", MockStrategy("a"))
        manager.register("b", MockStrategy("b"))
        manager.set_chain("a", ["b"])

        assert manager.is_chain_valid("a") is True
        manager.set_chain("a", ["c"])
        assert manager.is_chain_valid("a") is False

    def test_context_manager(self) -> None:
        """测试上下文管理器."""
        with FallbackManager() as manager:
            manager.register("test", MockStrategy("test"))
        # 应该正常关闭

    def test_default_chains(self) -> None:
        """测试默认回退链."""
        assert "top_tier" in DEFAULT_FALLBACK_CHAINS
        assert "simple_ai" in DEFAULT_FALLBACK_CHAINS["top_tier"]


class TestFallbackManagerEdgeCases:
    """回退管理器边界情况测试."""

    def test_max_chain_depth(self) -> None:
        """测试最大链深度."""
        config = FallbackConfig(max_chain_depth=2, enable_timeout=False)
        manager = FallbackManager(config)
        manager.register("a", MockStrategy("a", should_fail=True))
        manager.register("b", MockStrategy("b", should_fail=True))
        manager.register("c", MockStrategy("c"))
        manager.set_chain("a", ["b", "c"])

        result = manager.execute("a", {})
        # 只能尝试前2个策略
        assert result is not None

    def test_event_handler_exception(self) -> None:
        """测试事件处理器异常."""
        config = FallbackConfig(enable_timeout=False)
        manager = FallbackManager(config)

        def bad_handler(e: FallbackEvent) -> None:
            raise RuntimeError("Handler error")

        manager.add_event_handler(bad_handler)
        manager.register("fail", MockStrategy("fail", should_fail=True))
        manager.register("simple_ai", MockStrategy("simple_ai"))
        manager.set_chain("fail", ["simple_ai"])

        # 不应该因为处理器异常而失败
        result = manager.execute("fail", {})
        assert result.success
