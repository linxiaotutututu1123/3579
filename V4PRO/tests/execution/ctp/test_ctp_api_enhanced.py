"""CTP API增强测试 (军规级 v4.0).

覆盖场景:
- INFRA.CTP.CONNECT: CTP连接成功
- INFRA.CTP.AUTH: CTP认证成功
- INFRA.CTP.SUBSCRIBE: 行情订阅成功
- INFRA.CTP.RECONNECT: CTP重连成功

军规覆盖:
- M3 完整审计: 所有操作记录日志
- M6 熔断保护: 连接异常自动处理
- M8 配置隔离: 支持不同环境配置
- M9 错误上报: 异常统一处理上报
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from src.brokers.ctp.api import (
    ConnectionStatus,
    CtpApi,
    CtpAuthError,
    CtpSubscribeError,
    SubscriptionStatus,
    TickData,
    create_ctp_api,
)
from src.brokers.ctp.config import CtpConnectionConfig


# =============================================================================
# 场景: INFRA.CTP.CONNECT - CTP连接成功
# =============================================================================


class TestCtpConnect:
    """CTP连接测试 - 场景: INFRA.CTP.CONNECT."""

    def test_connect_success(self) -> None:
        """测试连接成功."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        result = api.connect()

        assert result is True
        assert api.is_connected is True
        assert api.status == ConnectionStatus.CONNECTED
        assert api._connected_at is not None

    def test_connect_already_connected(self) -> None:
        """测试重复连接跳过."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        # 第二次连接应该跳过
        result = api.connect()

        assert result is True
        assert api.is_connected is True

    def test_connect_status_transition(self) -> None:
        """测试连接状态转换."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        # 初始状态
        assert api.status == ConnectionStatus.DISCONNECTED

        # 连接后状态
        api.connect()
        assert api.status == ConnectionStatus.CONNECTED

    def test_connect_with_default_config(self) -> None:
        """测试使用默认配置连接."""
        # 使用PAPER模式的默认配置
        with patch.dict("os.environ", {"TRADE_MODE": "PAPER"}):
            api = create_ctp_api()
            result = api.connect()
            assert result is True

    def test_connect_records_timestamp(self) -> None:
        """测试连接记录时间戳 - 军规M3完整审计."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        before = datetime.now(UTC)
        api.connect()
        after = datetime.now(UTC)

        assert api._connected_at is not None
        assert before <= api._connected_at <= after


# =============================================================================
# 场景: INFRA.CTP.AUTH - CTP认证成功
# =============================================================================


class TestCtpAuth:
    """CTP认证测试 - 场景: INFRA.CTP.AUTH."""

    def test_authenticate_success(self) -> None:
        """测试认证成功."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        result = api.authenticate()

        assert result is True
        assert api.is_authenticated is True
        assert api.status == ConnectionStatus.AUTHENTICATED

    def test_authenticate_without_connect_raises(self) -> None:
        """测试未连接时认证抛出异常."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        with pytest.raises(CtpAuthError, match="未连接"):
            api.authenticate()

    def test_authenticate_already_authenticated(self) -> None:
        """测试重复认证跳过."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.authenticate()

        # 第二次认证应该跳过
        result = api.authenticate()

        assert result is True
        assert api.is_authenticated is True

    def test_authenticate_empty_broker_id_raises(self) -> None:
        """测试空broker_id认证失败."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        with pytest.raises(CtpAuthError, match="broker_id为空"):
            api.authenticate()

    def test_authenticate_empty_user_id_raises(self) -> None:
        """测试空user_id认证失败."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        with pytest.raises(CtpAuthError, match="user_id为空"):
            api.authenticate()

    def test_authenticate_records_timestamp(self) -> None:
        """测试认证记录时间戳 - 军规M3完整审计."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        before = datetime.now(UTC)
        api.authenticate()
        after = datetime.now(UTC)

        assert api._authenticated_at is not None
        assert before <= api._authenticated_at <= after

    def test_login_success(self) -> None:
        """测试登录成功."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.authenticate()

        result = api.login()

        assert result is True
        assert api.is_ready is True
        assert api.status == ConnectionStatus.LOGGED_IN

    def test_login_without_auth_raises(self) -> None:
        """测试未认证时登录抛出异常."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        with pytest.raises(CtpAuthError, match="未认证"):
            api.login()


# =============================================================================
# 场景: INFRA.CTP.SUBSCRIBE - 行情订阅成功
# =============================================================================


class TestCtpSubscribe:
    """CTP订阅测试 - 场景: INFRA.CTP.SUBSCRIBE."""

    def test_subscribe_success(self) -> None:
        """测试订阅成功."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        results = api.subscribe(["rb2501", "au2506"])

        assert results["rb2501"] is True
        assert results["au2506"] is True
        assert "rb2501" in api.subscribed_symbols
        assert "au2506" in api.subscribed_symbols

    def test_subscribe_without_connect_raises(self) -> None:
        """测试未连接时订阅抛出异常."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        with pytest.raises(CtpSubscribeError, match="未连接"):
            api.subscribe(["rb2501"])

    def test_subscribe_updates_state(self) -> None:
        """测试订阅更新状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.subscribe(["rb2501"])

        state = api.get_subscription_state("rb2501")

        assert state is not None
        assert state.status == SubscriptionStatus.SUBSCRIBED
        assert state.subscribed_at is not None

    def test_subscribe_multiple_symbols(self) -> None:
        """测试批量订阅."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        symbols = ["rb2501", "au2506", "cu2503", "al2502"]
        results = api.subscribe(symbols)

        assert all(results.values())
        assert len(api.subscribed_symbols) == 4

    def test_unsubscribe_success(self) -> None:
        """测试退订成功."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.subscribe(["rb2501"])

        results = api.unsubscribe(["rb2501"])

        assert results["rb2501"] is True
        state = api.get_subscription_state("rb2501")
        assert state is not None
        assert state.status == SubscriptionStatus.UNSUBSCRIBED

    def test_unsubscribe_not_subscribed(self) -> None:
        """测试退订未订阅的合约."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()

        results = api.unsubscribe(["rb2501"])

        assert results["rb2501"] is False


# =============================================================================
# 场景: INFRA.CTP.RECONNECT - CTP重连成功
# =============================================================================


class TestCtpReconnect:
    """CTP重连测试 - 军规M6熔断保护."""

    def test_reconnect_success(self) -> None:
        """测试重连成功."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.subscribe(["rb2501"])

        result = api.reconnect()

        assert result is True
        assert api.is_connected is True
        # 重连后订阅应该被清除
        assert len(api.subscribed_symbols) == 0

    def test_reconnect_clears_state(self) -> None:
        """测试重连清除状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.authenticate()
        api.subscribe(["rb2501", "au2506"])

        api.reconnect()

        # 认证状态应该被清除
        assert api.is_authenticated is False
        assert api._authenticated_at is None
        # 订阅应该被清除
        assert len(api._subscriptions) == 0

    def test_disconnect_clears_all(self) -> None:
        """测试断开连接清除所有状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.authenticate()
        api.subscribe(["rb2501"])

        api.disconnect()

        assert api.status == ConnectionStatus.DISCONNECTED
        assert api.is_connected is False
        assert api._connected_at is None
        assert api._authenticated_at is None
        assert len(api._subscriptions) == 0

    def test_disconnect_when_not_connected(self) -> None:
        """测试未连接时断开跳过."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        # 不应该抛出异常
        api.disconnect()

        assert api.status == ConnectionStatus.DISCONNECTED


# =============================================================================
# TickData数据类测试
# =============================================================================


class TestTickData:
    """TickData数据类测试."""

    def test_create_tick_data(self) -> None:
        """测试创建Tick数据."""
        tick = TickData(
            symbol="rb2501",
            exchange="SHFE",
            last_price=4000.0,
            volume=1000,
            open_interest=50000.0,
            bid_price1=3999.0,
            bid_volume1=100,
            ask_price1=4001.0,
            ask_volume1=150,
            upper_limit=4400.0,
            lower_limit=3600.0,
        )

        assert tick.symbol == "rb2501"
        assert tick.exchange == "SHFE"
        assert tick.last_price == 4000.0
        assert tick.timestamp is not None

    def test_tick_data_to_dict(self) -> None:
        """测试Tick数据转字典."""
        tick = TickData(
            symbol="rb2501",
            exchange="SHFE",
            last_price=4000.0,
            volume=1000,
            open_interest=50000.0,
            bid_price1=3999.0,
            bid_volume1=100,
            ask_price1=4001.0,
            ask_volume1=150,
            upper_limit=4400.0,
            lower_limit=3600.0,
        )

        d = tick.to_dict()

        assert d["symbol"] == "rb2501"
        assert d["exchange"] == "SHFE"
        assert d["last_price"] == 4000.0
        assert "timestamp" in d

    def test_on_tick_callback(self) -> None:
        """测试Tick回调."""
        received_ticks: list[TickData] = []

        def on_tick(tick: TickData) -> None:
            received_ticks.append(tick)

        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config, on_tick=on_tick)
        api.connect()
        api.subscribe(["rb2501"])

        tick = TickData(
            symbol="rb2501",
            exchange="SHFE",
            last_price=4000.0,
            volume=1000,
            open_interest=50000.0,
            bid_price1=3999.0,
            bid_volume1=100,
            ask_price1=4001.0,
            ask_volume1=150,
            upper_limit=4400.0,
            lower_limit=3600.0,
        )
        api.on_tick_received(tick)

        assert len(received_ticks) == 1
        assert received_ticks[0].symbol == "rb2501"

    def test_on_tick_updates_subscription_state(self) -> None:
        """测试Tick更新订阅状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.subscribe(["rb2501"])

        tick = TickData(
            symbol="rb2501",
            exchange="SHFE",
            last_price=4000.0,
            volume=1000,
            open_interest=50000.0,
            bid_price1=3999.0,
            bid_volume1=100,
            ask_price1=4001.0,
            ask_volume1=150,
            upper_limit=4400.0,
            lower_limit=3600.0,
        )
        api.on_tick_received(tick)

        state = api.get_subscription_state("rb2501")
        assert state is not None
        assert state.last_tick_at == tick.timestamp

    def test_on_tick_callback_exception_handled(self) -> None:
        """测试Tick回调异常处理 - 军规M9错误上报."""

        def bad_callback(tick: TickData) -> None:
            raise ValueError("Test error")

        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config, on_tick=bad_callback)
        api.connect()
        api.subscribe(["rb2501"])

        tick = TickData(
            symbol="rb2501",
            exchange="SHFE",
            last_price=4000.0,
            volume=1000,
            open_interest=50000.0,
            bid_price1=3999.0,
            bid_volume1=100,
            ask_price1=4001.0,
            ask_volume1=150,
            upper_limit=4400.0,
            lower_limit=3600.0,
        )

        # 不应该抛出异常
        api.on_tick_received(tick)


# =============================================================================
# 状态信息测试
# =============================================================================


class TestCtpApiStatusInfo:
    """CTP API状态信息测试."""

    def test_get_status_info(self) -> None:
        """测试获取状态信息."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)
        api.connect()
        api.authenticate()
        api.subscribe(["rb2501", "au2506"])

        info = api.get_status_info()

        assert info["status"] == "authenticated"
        assert info["is_connected"] is True
        assert info["is_authenticated"] is True
        assert info["front_addr"] == "tcp://mock.ctp.local:10130"
        assert info["broker_id"] == "MOCK"
        assert len(info["subscribed_symbols"]) == 2

    def test_repr(self) -> None:
        """测试字符串表示."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        repr_str = repr(api)

        assert "CtpApi" in repr_str
        assert "disconnected" in repr_str
        assert "MOCK" in repr_str


# =============================================================================
# 便捷函数测试
# =============================================================================


class TestCreateCtpApi:
    """create_ctp_api便捷函数测试."""

    def test_create_with_all_params(self) -> None:
        """测试带所有参数创建."""
        api = create_ctp_api(
            front_addr="tcp://test.ctp.local:10130",
            broker_id="TEST",
            user_id="user123",
            password="pass123",
        )

        assert api.config.front_addr == "tcp://test.ctp.local:10130"
        assert api.config.broker_id == "TEST"
        assert api.config.user_id == "user123"

    def test_create_with_callback(self) -> None:
        """测试带回调创建."""
        ticks: list[TickData] = []

        api = create_ctp_api(
            front_addr="tcp://test.ctp.local:10130",
            broker_id="TEST",
            user_id="user123",
            password="pass123",
            on_tick=lambda t: ticks.append(t),
        )

        assert api._on_tick is not None

    def test_create_from_env(self) -> None:
        """测试从环境变量创建."""
        with patch.dict("os.environ", {"TRADE_MODE": "PAPER"}):
            api = create_ctp_api()
            # PAPER模式使用模拟配置
            assert api.config.broker_id == "MOCK"


# =============================================================================
# 属性测试
# =============================================================================


class TestCtpApiProperties:
    """CTP API属性测试."""

    def test_is_connected_states(self) -> None:
        """测试is_connected在不同状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        # 初始未连接
        assert api.is_connected is False

        # 连接后
        api.connect()
        assert api.is_connected is True

        # 认证后仍然连接
        api.authenticate()
        assert api.is_connected is True

        # 断开后
        api.disconnect()
        assert api.is_connected is False

    def test_is_authenticated_states(self) -> None:
        """测试is_authenticated在不同状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        # 初始未认证
        assert api.is_authenticated is False

        # 连接后未认证
        api.connect()
        assert api.is_authenticated is False

        # 认证后
        api.authenticate()
        assert api.is_authenticated is True

    def test_is_ready_states(self) -> None:
        """测试is_ready在不同状态."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        # 初始未就绪
        assert api.is_ready is False

        # 连接后未就绪
        api.connect()
        assert api.is_ready is False

        # 认证后未就绪
        api.authenticate()
        assert api.is_ready is False

        # 登录后就绪
        api.login()
        assert api.is_ready is True

    def test_config_property(self) -> None:
        """测试config属性."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )
        api = CtpApi(config)

        assert api.config is config
        assert api.config.broker_id == "MOCK"
