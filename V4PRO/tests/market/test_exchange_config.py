"""六大交易所配置模块测试 (军规级 v4.0).

测试场景:
- CHINA.EXCHANGE.CONFIG_LOAD: 配置加载正确
- CHINA.EXCHANGE.PRODUCT_MAP: 品种映射正确

军规覆盖:
- M15: 夜盘跨日处理
- M20: 跨所一致
"""

import pytest

from src.market.exchange_config import (
    DAY_SESSIONS,
    EXCHANGE_CONFIGS,
    Exchange,
    ExchangeConfig,
    NightSessionEnd,
    ProductExchangeMapper,
    TradingSession,
    get_all_exchanges,
    get_exchange_by_code,
    get_exchange_config,
    get_exchange_for_product,
    get_night_session_end,
    get_night_session_end_for_product,
    get_products_by_category,
    get_products_by_exchange,
    get_trading_sessions,
    has_night_session,
)


class TestExchangeEnum:
    """交易所枚举测试."""

    RULE_ID = "CHINA.EXCHANGE.CONFIG_LOAD"

    def test_exchange_count(self) -> None:
        """测试交易所数量为6个."""
        assert len(Exchange) == 6

    def test_exchange_values(self) -> None:
        """测试交易所中文名称."""
        assert Exchange.SHFE.value == "上海期货交易所"
        assert Exchange.DCE.value == "大连商品交易所"
        assert Exchange.CZCE.value == "郑州商品交易所"
        assert Exchange.CFFEX.value == "中国金融期货交易所"
        assert Exchange.GFEX.value == "广州期货交易所"
        assert Exchange.INE.value == "上海国际能源交易中心"


class TestNightSessionEnd:
    """夜盘结束时间枚举测试."""

    RULE_ID = "CHINA.EXCHANGE.CONFIG_LOAD"

    def test_night_session_values(self) -> None:
        """测试夜盘结束时间分类."""
        assert NightSessionEnd.T_23_00.value == "23:00"
        assert NightSessionEnd.T_01_00.value == "01:00"
        assert NightSessionEnd.T_02_30.value == "02:30"
        assert NightSessionEnd.NONE.value == "无夜盘"


class TestTradingSession:
    """交易时段测试."""

    RULE_ID = "CHINA.EXCHANGE.CONFIG_LOAD"

    def test_trading_session_creation(self) -> None:
        """测试交易时段创建."""
        session = TradingSession("09:00", "10:15", "早盘第一节")
        assert session.start == "09:00"
        assert session.end == "10:15"
        assert session.name == "早盘第一节"

    def test_trading_session_immutable(self) -> None:
        """测试交易时段不可变."""
        session = TradingSession("09:00", "10:15")
        with pytest.raises(AttributeError):
            session.start = "09:30"  # type: ignore[misc]

    def test_day_sessions_count(self) -> None:
        """测试日盘标准时段数量."""
        assert len(DAY_SESSIONS) == 3


class TestExchangeConfig:
    """交易所配置测试."""

    RULE_ID = "CHINA.EXCHANGE.CONFIG_LOAD"

    def test_all_exchanges_configured(self) -> None:
        """测试所有交易所都有配置."""
        for exchange in Exchange:
            assert exchange in EXCHANGE_CONFIGS

    def test_shfe_config(self) -> None:
        """测试上期所配置."""
        config = EXCHANGE_CONFIGS[Exchange.SHFE]
        assert config.code == "SHFE"
        assert config.name == "上海期货交易所"
        assert config.night_session_end == NightSessionEnd.T_02_30
        assert "cu" in config.products
        assert "rb" in config.products
        assert "au" in config.products

    def test_dce_config(self) -> None:
        """测试大商所配置."""
        config = EXCHANGE_CONFIGS[Exchange.DCE]
        assert config.code == "DCE"
        assert config.night_session_end == NightSessionEnd.T_23_00
        assert "i" in config.products
        assert "m" in config.products

    def test_czce_config(self) -> None:
        """测试郑商所配置."""
        config = EXCHANGE_CONFIGS[Exchange.CZCE]
        assert config.code == "CZCE"
        assert "MA" in config.products
        assert "CF" in config.products

    def test_cffex_no_night_session(self) -> None:
        """测试中金所无夜盘."""
        config = EXCHANGE_CONFIGS[Exchange.CFFEX]
        assert config.code == "CFFEX"
        assert config.night_session_end == NightSessionEnd.NONE
        assert "IF" in config.products
        assert "T" in config.products

    def test_gfex_config(self) -> None:
        """测试广期所配置."""
        config = EXCHANGE_CONFIGS[Exchange.GFEX]
        assert config.code == "GFEX"
        assert "lc" in config.products
        assert "si" in config.products

    def test_ine_config(self) -> None:
        """测试能源中心配置."""
        config = EXCHANGE_CONFIGS[Exchange.INE]
        assert config.code == "INE"
        assert config.night_session_end == NightSessionEnd.T_02_30
        assert "sc" in config.products


class TestProductExchangeMapper:
    """品种到交易所映射器测试."""

    RULE_ID = "CHINA.EXCHANGE.PRODUCT_MAP"

    def test_get_exchange_shfe_products(self) -> None:
        """测试上期所品种映射."""
        assert ProductExchangeMapper.get_exchange("cu") == Exchange.SHFE
        assert ProductExchangeMapper.get_exchange("rb") == Exchange.SHFE
        assert ProductExchangeMapper.get_exchange("au") == Exchange.SHFE
        assert ProductExchangeMapper.get_exchange("ag") == Exchange.SHFE

    def test_get_exchange_dce_products(self) -> None:
        """测试大商所品种映射."""
        assert ProductExchangeMapper.get_exchange("i") == Exchange.DCE
        assert ProductExchangeMapper.get_exchange("m") == Exchange.DCE
        assert ProductExchangeMapper.get_exchange("j") == Exchange.DCE

    def test_get_exchange_czce_products(self) -> None:
        """测试郑商所品种映射（大小写不敏感）."""
        assert ProductExchangeMapper.get_exchange("MA") == Exchange.CZCE
        assert ProductExchangeMapper.get_exchange("ma") == Exchange.CZCE
        assert ProductExchangeMapper.get_exchange("CF") == Exchange.CZCE
        assert ProductExchangeMapper.get_exchange("cf") == Exchange.CZCE

    def test_get_exchange_cffex_products(self) -> None:
        """测试中金所品种映射."""
        assert ProductExchangeMapper.get_exchange("IF") == Exchange.CFFEX
        assert ProductExchangeMapper.get_exchange("if") == Exchange.CFFEX
        assert ProductExchangeMapper.get_exchange("T") == Exchange.CFFEX

    def test_get_exchange_gfex_products(self) -> None:
        """测试广期所品种映射."""
        assert ProductExchangeMapper.get_exchange("lc") == Exchange.GFEX
        assert ProductExchangeMapper.get_exchange("si") == Exchange.GFEX

    def test_get_exchange_ine_products(self) -> None:
        """测试能源中心品种映射."""
        assert ProductExchangeMapper.get_exchange("sc") == Exchange.INE
        assert ProductExchangeMapper.get_exchange("lu") == Exchange.INE

    def test_get_exchange_unknown_product(self) -> None:
        """测试未知品种返回None."""
        assert ProductExchangeMapper.get_exchange("UNKNOWN") is None
        assert ProductExchangeMapper.get_exchange("xyz") is None

    def test_get_all_products(self) -> None:
        """测试获取所有品种."""
        products = ProductExchangeMapper.get_all_products()
        assert len(products) > 50
        assert "cu" in products
        assert "if" in products


class TestConvenienceFunctions:
    """便捷函数测试."""

    RULE_ID = "CHINA.EXCHANGE.CONFIG_LOAD"

    def test_get_exchange_for_product(self) -> None:
        """测试get_exchange_for_product函数."""
        assert get_exchange_for_product("rb") == Exchange.SHFE
        assert get_exchange_for_product("IF") == Exchange.CFFEX
        assert get_exchange_for_product("unknown") is None

    def test_get_exchange_config(self) -> None:
        """测试get_exchange_config函数."""
        config = get_exchange_config(Exchange.SHFE)
        assert isinstance(config, ExchangeConfig)
        assert config.code == "SHFE"

    def test_get_exchange_config_not_found(self) -> None:
        """测试get_exchange_config未找到时抛出异常."""
        # Exchange枚举保证了所有值都有配置，这里测试类型检查
        with pytest.raises(KeyError):
            get_exchange_config("INVALID")  # type: ignore[arg-type]

    def test_get_trading_sessions(self) -> None:
        """测试get_trading_sessions函数."""
        sessions = get_trading_sessions(Exchange.SHFE)
        assert len(sessions) == 3
        assert sessions[0].start == "09:00"

    def test_has_night_session(self) -> None:
        """测试has_night_session函数."""
        assert has_night_session(Exchange.SHFE) is True
        assert has_night_session(Exchange.DCE) is True
        assert has_night_session(Exchange.CFFEX) is False

    def test_get_night_session_end(self) -> None:
        """测试get_night_session_end函数."""
        assert get_night_session_end(Exchange.SHFE) == NightSessionEnd.T_02_30
        assert get_night_session_end(Exchange.DCE) == NightSessionEnd.T_23_00
        assert get_night_session_end(Exchange.CFFEX) == NightSessionEnd.NONE

    def test_get_products_by_exchange(self) -> None:
        """测试get_products_by_exchange函数."""
        products = get_products_by_exchange(Exchange.SHFE)
        assert "cu" in products
        assert "rb" in products

    def test_get_products_by_category(self) -> None:
        """测试get_products_by_category函数."""
        metals = get_products_by_category("金属")
        assert "SHFE" in metals
        assert "cu" in metals["SHFE"]

    def test_get_products_by_category_not_found(self) -> None:
        """测试get_products_by_category分类不存在."""
        with pytest.raises(KeyError):
            get_products_by_category("不存在的分类")

    def test_get_all_exchanges(self) -> None:
        """测试get_all_exchanges函数."""
        exchanges = get_all_exchanges()
        assert len(exchanges) == 6
        assert Exchange.SHFE in exchanges

    def test_get_exchange_by_code(self) -> None:
        """测试get_exchange_by_code函数."""
        assert get_exchange_by_code("SHFE") == Exchange.SHFE
        assert get_exchange_by_code("shfe") == Exchange.SHFE
        assert get_exchange_by_code("DCE") == Exchange.DCE
        assert get_exchange_by_code("INVALID") is None


class TestNightSessionProducts:
    """夜盘品种配置测试."""

    RULE_ID = "CHINA.EXCHANGE.CONFIG_LOAD"

    def test_get_night_session_end_for_product_t_23_00(self) -> None:
        """测试23:00结束的品种."""
        # DCE农产品
        assert get_night_session_end_for_product("m") == NightSessionEnd.T_23_00
        assert get_night_session_end_for_product("i") == NightSessionEnd.T_23_00
        # CZCE
        assert get_night_session_end_for_product("MA") == NightSessionEnd.T_23_00

    def test_get_night_session_end_for_product_t_01_00(self) -> None:
        """测试01:00结束的品种."""
        assert get_night_session_end_for_product("rb") == NightSessionEnd.T_01_00
        assert get_night_session_end_for_product("hc") == NightSessionEnd.T_01_00

    def test_get_night_session_end_for_product_t_02_30(self) -> None:
        """测试02:30结束的品种."""
        assert get_night_session_end_for_product("cu") == NightSessionEnd.T_02_30
        assert get_night_session_end_for_product("au") == NightSessionEnd.T_02_30
        assert get_night_session_end_for_product("sc") == NightSessionEnd.T_02_30

    def test_get_night_session_end_for_product_none(self) -> None:
        """测试无夜盘的品种."""
        assert get_night_session_end_for_product("IF") == NightSessionEnd.NONE
        assert get_night_session_end_for_product("T") == NightSessionEnd.NONE

    def test_get_night_session_end_for_product_unknown(self) -> None:
        """测试未知品种默认无夜盘."""
        assert get_night_session_end_for_product("UNKNOWN") == NightSessionEnd.NONE


class TestMilitaryRuleM15:
    """军规M15: 夜盘跨日处理测试."""

    RULE_ID = "M15.NIGHT_SESSION"

    def test_night_session_config_complete(self) -> None:
        """测试夜盘配置完整性."""
        # 有夜盘的交易所必须有夜盘开始时间
        for exchange in [
            Exchange.SHFE,
            Exchange.DCE,
            Exchange.CZCE,
            Exchange.GFEX,
            Exchange.INE,
        ]:
            config = get_exchange_config(exchange)
            assert config.night_session_start == "21:00"
            assert config.night_session_end != NightSessionEnd.NONE

        # CFFEX无夜盘
        cffex_config = get_exchange_config(Exchange.CFFEX)
        assert cffex_config.night_session_end == NightSessionEnd.NONE


class TestMilitaryRuleM20:
    """军规M20: 跨所一致测试."""

    RULE_ID = "M20.CROSS_EXCHANGE"

    def test_all_exchanges_have_settlement_time(self) -> None:
        """测试所有交易所都有结算时间."""
        for exchange in Exchange:
            config = get_exchange_config(exchange)
            assert config.settlement_time is not None
            assert config.settlement_time != ""

    def test_all_exchanges_have_products(self) -> None:
        """测试所有交易所都有品种列表."""
        for exchange in Exchange:
            config = get_exchange_config(exchange)
            assert len(config.products) > 0

    def test_all_exchanges_have_trading_sessions(self) -> None:
        """测试所有交易所都有交易时段."""
        for exchange in Exchange:
            config = get_exchange_config(exchange)
            assert len(config.trading_sessions) > 0
