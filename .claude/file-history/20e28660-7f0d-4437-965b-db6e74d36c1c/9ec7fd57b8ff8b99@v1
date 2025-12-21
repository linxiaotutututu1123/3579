"""CTP配置测试 (军规级 v4.0).

覆盖场景:
- INFRA.CONFIG.LOAD: 配置加载成功
- INFRA.CONFIG.VALIDATE: 配置验证通过
- INFRA.CONFIG.ENV_ISOLATE: 环境隔离正确

军规覆盖:
- M8 配置隔离: 不同环境配置严格隔离
- M9 错误上报: 配置错误统一处理
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.brokers.ctp.config import (
    REQUIRED_CTP_ENV_VARS,
    CtpConfigMissingError,
    CtpConfigValidationError,
    CtpConnectionConfig,
    CtpFullConfig,
    CtpMarketConfig,
    CtpTradeConfig,
    TradeEnvironment,
    check_environment_isolation,
    get_current_environment,
    load_ctp_config,
    load_full_ctp_config,
)


# =============================================================================
# 场景: INFRA.CONFIG.LOAD - 配置加载成功
# =============================================================================


class TestCtpConfigLoad:
    """CTP配置加载测试 - 场景: INFRA.CONFIG.LOAD."""

    def test_load_paper_mode_default(self) -> None:
        """测试PAPER模式默认配置."""
        config = load_ctp_config(TradeEnvironment.PAPER)

        assert config.front_addr == "tcp://mock.ctp.local:10130"
        assert config.broker_id == "MOCK"
        assert config.user_id == "mock_user"
        assert config.password == "mock_password"

    def test_load_paper_mode_string(self) -> None:
        """测试PAPER模式字符串参数."""
        config = load_ctp_config("paper")

        assert config.broker_id == "MOCK"

    def test_load_sim_mode_from_env(self) -> None:
        """测试SIM模式从环境变量加载."""
        env = {
            "CTP_FRONT_ADDR": "tcp://simnow.ctp.local:10130",
            "CTP_BROKER_ID": "SIM_BROKER",
            "CTP_USER_ID": "sim_user",
            "CTP_PASSWORD": "sim_pass",
        }
        with patch.dict("os.environ", env):
            config = load_ctp_config(TradeEnvironment.SIM)

            assert config.front_addr == "tcp://simnow.ctp.local:10130"
            assert config.broker_id == "SIM_BROKER"

    def test_load_live_mode_missing_vars_raises(self) -> None:
        """测试LIVE模式缺失变量抛出异常."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CtpConfigMissingError) as exc_info:
                load_ctp_config(TradeEnvironment.LIVE)

            assert "缺失必需的环境变量" in str(exc_info.value)

    def test_load_live_mode_with_all_vars(self) -> None:
        """测试LIVE模式带所有变量."""
        env = {
            "CTP_FRONT_ADDR": "tcp://real.ctp.server:10130",
            "CTP_BROKER_ID": "REAL_BROKER",
            "CTP_USER_ID": "real_user",
            "CTP_PASSWORD": "real_pass",
        }
        with patch.dict("os.environ", env):
            config = load_ctp_config(TradeEnvironment.LIVE)

            assert config.front_addr == "tcp://real.ctp.server:10130"
            assert config.broker_id == "REAL_BROKER"

    def test_load_optional_vars(self) -> None:
        """测试加载可选变量."""
        env = {
            "CTP_FRONT_ADDR": "tcp://simnow.ctp.local:10130",
            "CTP_BROKER_ID": "SIM_BROKER",
            "CTP_USER_ID": "sim_user",
            "CTP_PASSWORD": "sim_pass",
            "CTP_APP_ID": "app_123",
            "CTP_AUTH_CODE": "auth_456",
            "CTP_PRODUCT_INFO": "V4PRO",
        }
        with patch.dict("os.environ", env):
            config = load_ctp_config(TradeEnvironment.SIM)

            assert config.app_id == "app_123"
            assert config.auth_code == "auth_456"
            assert config.product_info == "V4PRO"

    def test_load_require_complete_checks_all(self) -> None:
        """测试require_complete检查所有变量."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(CtpConfigMissingError):
                load_ctp_config(TradeEnvironment.PAPER, require_complete=True)


# =============================================================================
# 场景: INFRA.CONFIG.VALIDATE - 配置验证通过
# =============================================================================


class TestCtpConfigValidate:
    """CTP配置验证测试 - 场景: INFRA.CONFIG.VALIDATE."""

    def test_validate_valid_config(self) -> None:
        """测试验证有效配置."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )

        errors = config.validate()

        assert len(errors) == 0
        assert config.is_valid() is True

    def test_validate_empty_front_addr(self) -> None:
        """测试验证空前置地址."""
        config = CtpConnectionConfig(
            front_addr="",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )

        errors = config.validate()

        assert "front_addr不能为空" in errors
        assert config.is_valid() is False

    def test_validate_invalid_front_addr_prefix(self) -> None:
        """测试验证无效前置地址前缀."""
        config = CtpConnectionConfig(
            front_addr="http://invalid.addr:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )

        errors = config.validate()

        assert "front_addr必须以tcp://或ssl://开头" in errors

    def test_validate_ssl_front_addr(self) -> None:
        """测试验证SSL前置地址."""
        config = CtpConnectionConfig(
            front_addr="ssl://secure.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="test_pass",
        )

        errors = config.validate()

        assert len(errors) == 0

    def test_validate_empty_broker_id(self) -> None:
        """测试验证空经纪商ID."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="",
            user_id="test_user",
            password="test_pass",
        )

        errors = config.validate()

        assert "broker_id不能为空" in errors

    def test_validate_empty_user_id(self) -> None:
        """测试验证空用户ID."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="",
            password="test_pass",
        )

        errors = config.validate()

        assert "user_id不能为空" in errors

    def test_validate_empty_password(self) -> None:
        """测试验证空密码."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="",
        )

        errors = config.validate()

        assert "password不能为空" in errors

    def test_validate_multiple_errors(self) -> None:
        """测试验证多个错误."""
        config = CtpConnectionConfig(
            front_addr="",
            broker_id="",
            user_id="",
            password="",
        )

        errors = config.validate()

        assert len(errors) >= 4

    def test_load_validates_on_live(self) -> None:
        """测试LIVE模式加载时验证."""
        env = {
            "CTP_FRONT_ADDR": "invalid://bad.addr",  # 无效前缀
            "CTP_BROKER_ID": "BROKER",
            "CTP_USER_ID": "user",
            "CTP_PASSWORD": "pass",
        }
        with patch.dict("os.environ", env):
            with pytest.raises(CtpConfigValidationError) as exc_info:
                load_ctp_config(TradeEnvironment.LIVE)

            assert "验证失败" in str(exc_info.value)


# =============================================================================
# 场景: INFRA.CONFIG.ENV_ISOLATE - 环境隔离正确
# =============================================================================


class TestCtpEnvironmentIsolation:
    """CTP环境隔离测试 - 场景: INFRA.CONFIG.ENV_ISOLATE, 军规: M8."""

    def test_paper_mode_allows_any_config(self) -> None:
        """测试PAPER模式允许任何配置."""
        config = CtpConnectionConfig(
            front_addr="tcp://any.server:10130",
            broker_id="ANY",
            user_id="any_user",
            password="any_pass",
        )

        result = check_environment_isolation(TradeEnvironment.PAPER, config)

        assert result is True

    def test_sim_mode_detects_simnow(self) -> None:
        """测试SIM模式检测simnow关键字."""
        config = CtpConnectionConfig(
            front_addr="tcp://simnow.ctp.local:10130",
            broker_id="SIMNOW",
            user_id="sim_user",
            password="sim_pass",
        )

        result = check_environment_isolation(TradeEnvironment.SIM, config)

        assert result is True

    def test_sim_mode_detects_test(self) -> None:
        """测试SIM模式检测test关键字."""
        config = CtpConnectionConfig(
            front_addr="tcp://test.ctp.local:10130",
            broker_id="TEST",
            user_id="test_user",
            password="test_pass",
        )

        result = check_environment_isolation(TradeEnvironment.SIM, config)

        assert result is True

    def test_sim_mode_detects_demo(self) -> None:
        """测试SIM模式检测demo关键字."""
        config = CtpConnectionConfig(
            front_addr="tcp://demo.ctp.server:10130",
            broker_id="DEMO",
            user_id="demo_user",
            password="demo_pass",
        )

        result = check_environment_isolation(TradeEnvironment.SIM, config)

        assert result is True

    def test_live_mode_rejects_simnow(self) -> None:
        """测试LIVE模式拒绝simnow地址."""
        config = CtpConnectionConfig(
            front_addr="tcp://simnow.ctp.local:10130",
            broker_id="BROKER",
            user_id="user",
            password="pass",
        )

        result = check_environment_isolation(TradeEnvironment.LIVE, config)

        assert result is False

    def test_live_mode_rejects_test(self) -> None:
        """测试LIVE模式拒绝test地址."""
        config = CtpConnectionConfig(
            front_addr="tcp://test.ctp.local:10130",
            broker_id="BROKER",
            user_id="user",
            password="pass",
        )

        result = check_environment_isolation(TradeEnvironment.LIVE, config)

        assert result is False

    def test_live_mode_rejects_mock(self) -> None:
        """测试LIVE模式拒绝mock地址."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="BROKER",
            user_id="user",
            password="pass",
        )

        result = check_environment_isolation(TradeEnvironment.LIVE, config)

        assert result is False

    def test_live_mode_accepts_real_server(self) -> None:
        """测试LIVE模式接受真实服务器."""
        config = CtpConnectionConfig(
            front_addr="tcp://180.168.146.187:10130",
            broker_id="REAL_BROKER",
            user_id="real_user",
            password="real_pass",
        )

        result = check_environment_isolation(TradeEnvironment.LIVE, config)

        assert result is True


# =============================================================================
# CtpConnectionConfig数据类测试
# =============================================================================


class TestCtpConnectionConfig:
    """CTP连接配置数据类测试."""

    def test_to_dict_masks_password(self) -> None:
        """测试转字典掩码密码."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="secret_password",
            auth_code="secret_auth",
        )

        d = config.to_dict(mask_password=True)

        assert d["password"] == "***"
        assert d["auth_code"] == "***"
        assert d["user_id"] == "test_user"

    def test_to_dict_shows_password(self) -> None:
        """测试转字典显示密码."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="secret_password",
        )

        d = config.to_dict(mask_password=False)

        assert d["password"] == "secret_password"

    def test_to_dict_empty_password(self) -> None:
        """测试转字典空密码."""
        config = CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="test_user",
            password="",
        )

        d = config.to_dict(mask_password=True)

        assert d["password"] == ""


# =============================================================================
# CtpFullConfig测试
# =============================================================================


class TestCtpFullConfig:
    """CTP完整配置测试."""

    def test_full_config_paper_mode_valid(self) -> None:
        """测试PAPER模式完整配置有效."""
        full_config = CtpFullConfig(environment=TradeEnvironment.PAPER)

        errors = full_config.validate()

        assert len(errors) == 0
        assert full_config.is_valid() is True

    def test_full_config_live_mode_validates_connection(self) -> None:
        """测试LIVE模式验证连接配置."""
        full_config = CtpFullConfig(
            environment=TradeEnvironment.LIVE,
            connection=CtpConnectionConfig(),  # 空配置
        )

        errors = full_config.validate()

        assert len(errors) > 0
        assert full_config.is_valid() is False

    def test_load_full_config_paper(self) -> None:
        """测试加载PAPER模式完整配置."""
        with patch.dict("os.environ", {"TRADE_MODE": "PAPER"}):
            full_config = load_full_ctp_config(TradeEnvironment.PAPER)

            assert full_config.environment == TradeEnvironment.PAPER
            assert full_config.connection.broker_id == "MOCK"

    def test_load_full_config_with_market_config(self) -> None:
        """测试加载带行情配置."""
        env = {
            "CTP_FRONT_ADDR": "tcp://simnow.ctp.local:10130",
            "CTP_BROKER_ID": "SIM",
            "CTP_USER_ID": "user",
            "CTP_PASSWORD": "pass",
            "CTP_MD_FRONT_ADDR": "tcp://md.simnow.ctp.local:10130",
            "CTP_SUBSCRIBE_SYMBOLS": "rb2501,au2506,cu2503",
        }
        with patch.dict("os.environ", env):
            full_config = load_full_ctp_config(TradeEnvironment.SIM)

            assert full_config.market.md_front_addr == "tcp://md.simnow.ctp.local:10130"
            assert full_config.market.subscribe_symbols == ["rb2501", "au2506", "cu2503"]

    def test_load_full_config_with_trade_config(self) -> None:
        """测试加载带交易配置."""
        env = {
            "CTP_FRONT_ADDR": "tcp://simnow.ctp.local:10130",
            "CTP_BROKER_ID": "SIM",
            "CTP_USER_ID": "user",
            "CTP_PASSWORD": "pass",
            "CTP_TD_FRONT_ADDR": "tcp://td.simnow.ctp.local:10130",
            "CTP_ORDER_TIMEOUT": "60.0",
        }
        with patch.dict("os.environ", env):
            full_config = load_full_ctp_config(TradeEnvironment.SIM)

            assert full_config.trade.td_front_addr == "tcp://td.simnow.ctp.local:10130"
            assert full_config.trade.order_timeout == 60.0


# =============================================================================
# CtpMarketConfig测试
# =============================================================================


class TestCtpMarketConfig:
    """CTP行情配置测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = CtpMarketConfig()

        assert config.md_front_addr == ""
        assert config.subscribe_symbols == []
        assert config.auto_reconnect is True
        assert config.reconnect_interval == 5.0
        assert config.max_reconnect_attempts == 3


# =============================================================================
# CtpTradeConfig测试
# =============================================================================


class TestCtpTradeConfig:
    """CTP交易配置测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = CtpTradeConfig()

        assert config.td_front_addr == ""
        assert config.max_order_ref == 999999
        assert config.order_timeout == 30.0
        assert config.cancel_timeout == 10.0


# =============================================================================
# TradeEnvironment枚举测试
# =============================================================================


class TestTradeEnvironment:
    """交易环境枚举测试."""

    def test_paper_value(self) -> None:
        """测试PAPER值."""
        assert TradeEnvironment.PAPER.value == "PAPER"

    def test_sim_value(self) -> None:
        """测试SIM值."""
        assert TradeEnvironment.SIM.value == "SIM"

    def test_live_value(self) -> None:
        """测试LIVE值."""
        assert TradeEnvironment.LIVE.value == "LIVE"

    def test_from_string(self) -> None:
        """测试从字符串创建."""
        assert TradeEnvironment("PAPER") == TradeEnvironment.PAPER
        assert TradeEnvironment("SIM") == TradeEnvironment.SIM
        assert TradeEnvironment("LIVE") == TradeEnvironment.LIVE


# =============================================================================
# get_current_environment测试
# =============================================================================


class TestGetCurrentEnvironment:
    """获取当前环境测试."""

    def test_default_paper(self) -> None:
        """测试默认PAPER环境."""
        with patch.dict("os.environ", {}, clear=True):
            env = get_current_environment()
            assert env == TradeEnvironment.PAPER

    def test_from_env_var(self) -> None:
        """测试从环境变量获取."""
        with patch.dict("os.environ", {"TRADE_MODE": "LIVE"}):
            env = get_current_environment()
            assert env == TradeEnvironment.LIVE

    def test_invalid_falls_back_to_paper(self) -> None:
        """测试无效值回退到PAPER."""
        with patch.dict("os.environ", {"TRADE_MODE": "INVALID"}):
            env = get_current_environment()
            assert env == TradeEnvironment.PAPER

    def test_case_insensitive(self) -> None:
        """测试大小写不敏感."""
        with patch.dict("os.environ", {"TRADE_MODE": "live"}):
            env = get_current_environment()
            assert env == TradeEnvironment.LIVE


# =============================================================================
# 常量测试
# =============================================================================


class TestConstants:
    """常量测试."""

    def test_required_env_vars(self) -> None:
        """测试必需环境变量."""
        assert "CTP_FRONT_ADDR" in REQUIRED_CTP_ENV_VARS
        assert "CTP_BROKER_ID" in REQUIRED_CTP_ENV_VARS
        assert "CTP_USER_ID" in REQUIRED_CTP_ENV_VARS
        assert "CTP_PASSWORD" in REQUIRED_CTP_ENV_VARS
