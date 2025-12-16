"""监控模块测试 (军规级 v4.0)."""

import pytest

from src.monitoring import HealthChecker, HealthStatus, MetricsCollector, MetricValue
from src.monitoring.health import HealthState
from src.monitoring.metrics import MetricType


class TestHealthChecker:
    """健康检查器测试."""

    def test_register_and_check(self) -> None:
        """测试注册和检查."""
        checker = HealthChecker()
        checker.register_check("broker", lambda: (True, "OK"))
        status = checker.check("broker")
        assert status.state == HealthState.HEALTHY

    def test_check_unregistered(self) -> None:
        """测试检查未注册组件."""
        checker = HealthChecker()
        status = checker.check("unknown")
        assert status.state == HealthState.UNKNOWN

    def test_check_exception(self) -> None:
        """测试检查异常."""
        checker = HealthChecker()
        checker.register_check("bad", lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        status = checker.check("bad")
        assert status.state == HealthState.UNHEALTHY

    def test_check_all(self) -> None:
        """测试检查所有."""
        checker = HealthChecker()
        checker.register_check("a", lambda: (True, "OK"))
        checker.register_check("b", lambda: (False, "Error"))
        results = checker.check_all()
        assert len(results) == 2

    def test_unregister(self) -> None:
        """测试注销."""
        checker = HealthChecker()
        checker.register_check("test", lambda: (True, "OK"))
        checker.unregister_check("test")
        assert "test" not in checker.components

    def test_get_status(self) -> None:
        """测试获取状态."""
        checker = HealthChecker()
        checker.register_check("x", lambda: (True, "OK"))
        checker.check("x")
        assert checker.get_status("x") is not None
        assert checker.get_status("y") is None

    def test_get_all_status(self) -> None:
        """测试获取所有状态."""
        checker = HealthChecker()
        checker.register_check("x", lambda: (True, "OK"))
        checker.check("x")
        assert "x" in checker.get_all_status()

    def test_is_system_healthy(self) -> None:
        """测试系统健康."""
        checker = HealthChecker()
        assert checker.is_system_healthy() is False
        checker.register_check("x", lambda: (True, "OK"))
        checker.check_all()
        assert checker.is_system_healthy() is True

    def test_get_summary(self) -> None:
        """测试获取摘要."""
        checker = HealthChecker()
        checker.register_check("x", lambda: (True, "OK"))
        checker.check_all()
        summary = checker.get_summary()
        assert summary["total_components"] == 1


class TestHealthStatus:
    """健康状态测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        status = HealthStatus("test", HealthState.HEALTHY, "OK", 1.0)
        d = status.to_dict()
        assert d["component"] == "test"
        assert d["state"] == "healthy"

    def test_is_healthy(self) -> None:
        """测试健康判断."""
        healthy = HealthStatus("a", HealthState.HEALTHY)
        unhealthy = HealthStatus("b", HealthState.UNHEALTHY)
        assert healthy.is_healthy is True
        assert unhealthy.is_healthy is False


class TestMetricsCollector:
    """指标收集器测试."""

    def test_increment(self) -> None:
        """测试计数器."""
        c = MetricsCollector()
        c.increment("orders")
        c.increment("orders", 5)
        assert c.get_counter("orders") == 6

    def test_increment_negative(self) -> None:
        """测试负数递增."""
        c = MetricsCollector()
        with pytest.raises(ValueError):
            c.increment("x", -1)

    def test_set_gauge(self) -> None:
        """测试仪表盘."""
        c = MetricsCollector()
        c.set("pos", 10)
        assert c.get_gauge("pos") == 10

    def test_observe(self) -> None:
        """测试直方图."""
        c = MetricsCollector()
        c.observe("latency", 5)
        c.observe("latency", 15)
        stats = c.get_histogram_stats("latency")
        assert stats["count"] == 2
        assert stats["avg"] == 10

    def test_histogram_empty(self) -> None:
        """测试空直方图."""
        c = MetricsCollector()
        stats = c.get_histogram_stats("unknown")
        assert stats["count"] == 0

    def test_get_all_metrics(self) -> None:
        """测试获取所有指标."""
        c = MetricsCollector()
        c.increment("c1")
        c.set("g1", 5)
        c.observe("h1", 10)
        metrics = c.get_all_metrics()
        assert len(metrics) >= 3

    def test_reset(self) -> None:
        """测试重置."""
        c = MetricsCollector()
        c.increment("x")
        c.reset()
        assert c.get_counter("x") == 0

    def test_export_prometheus(self) -> None:
        """测试Prometheus导出."""
        c = MetricsCollector()
        c.increment("orders", 10)
        c.set("pos", 5)
        c.observe("lat", 1)
        output = c.export_prometheus()
        assert "orders" in output
        assert "TYPE" in output

    def test_prefix(self) -> None:
        """测试前缀."""
        c = MetricsCollector(prefix="app_")
        c.increment("x")
        assert "app_x" in c._counters

    def test_labels(self) -> None:
        """测试标签."""
        c = MetricsCollector()
        c.increment("x", 1, labels={"a": "1"})
        c.set("y", 1, labels={"b": "2"})
        c.observe("z", 1, labels={"c": "3"})
        output = c.export_prometheus()
        assert "a=" in output


class TestMetricValue:
    """指标值测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        m = MetricValue("test", 1.0, MetricType.COUNTER)
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["type"] == "counter"
