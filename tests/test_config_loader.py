"""
配置验证模块测试 (军规级 v4.1).

测试覆盖:
- M21: 配置验证 - 所有配置必须通过 pydantic 验证

场景覆盖:
- CONFIG.LOAD.EXCHANGE: 加载交易所配置
- CONFIG.VALIDATE.PYDANTIC: Pydantic 验证
- CONFIG.VALIDATE.ALL: 验证所有配置
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.config.exchange_config_loader import (
    ConfigValidator,
    ExchangeConfigModel,
    ExchangeInfoModel,
    ProductModel,
    TradingSessionModel,
    TradingSessionsModel,
    get_all_products_from_configs,
    load_all_exchanges,
    load_exchange_config,
    validate_exchange_config,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def config_dir() -> Path:
    """获取配置目录."""
    return Path(__file__).parent.parent / "config" / "exchanges"


@pytest.fixture
def sample_exchange_data() -> dict:
    """创建示例交易所数据."""
    return {
        "exchange": {
            "code": "SHFE",
            "name": "上海期货交易所",
            "name_en": "Shanghai Futures Exchange",
            "timezone": "Asia/Shanghai",
        },
        "trading_sessions": {
            "day": [
                {"start": "09:00", "end": "10:15"},
                {"start": "10:30", "end": "11:30"},
            ],
            "night": [
                {"start": "21:00", "end": "02:30"},
            ],
        },
        "night_session_end": {
            "01:00": ["cu", "al"],
            "02:30": ["au", "ag"],
        },
        "products": {
            "metals": [
                {
                    "symbol": "cu",
                    "name": "铜",
                    "multiplier": 5,
                    "tick_size": 10,
                    "margin_ratio": 0.08,
                },
            ],
        },
    }


# ============================================================
# TradingSessionModel 测试
# ============================================================


class TestTradingSessionModel:
    """交易时段模型测试."""

    def test_valid_session(self) -> None:
        """测试有效时段."""
        session = TradingSessionModel(start="09:00", end="10:15")
        assert session.start == "09:00"
        assert session.end == "10:15"

    def test_invalid_time_format(self) -> None:
        """测试无效时间格式."""
        with pytest.raises(ValueError):
            TradingSessionModel(start="invalid", end="10:15")  # 无效格式

    def test_invalid_time_range(self) -> None:
        """测试无效时间范围."""
        with pytest.raises(ValueError):
            TradingSessionModel(start="25:00", end="10:15")


# ============================================================
# ProductModel 测试
# ============================================================


class TestProductModel:
    """品种模型测试."""

    def test_valid_product(self) -> None:
        """测试有效品种."""
        product = ProductModel(
            symbol="cu",
            name="铜",
            multiplier=5,
            tick_size=10,
            margin_ratio=0.08,
        )
        assert product.symbol == "cu"
        assert product.multiplier == 5

    def test_empty_symbol(self) -> None:
        """测试空品种代码."""
        with pytest.raises(ValueError):
            ProductModel(
                symbol="",
                name="铜",
                multiplier=5,
                tick_size=10,
            )

    def test_invalid_multiplier(self) -> None:
        """测试无效乘数."""
        with pytest.raises(ValueError):
            ProductModel(
                symbol="cu",
                name="铜",
                multiplier=0,  # 必须大于0
                tick_size=10,
            )

    def test_invalid_margin_ratio(self) -> None:
        """测试无效保证金比率."""
        with pytest.raises(ValueError):
            ProductModel(
                symbol="cu",
                name="铜",
                multiplier=5,
                tick_size=10,
                margin_ratio=1.5,  # 必须<=1
            )


# ============================================================
# ExchangeInfoModel 测试
# ============================================================


class TestExchangeInfoModel:
    """交易所信息模型测试."""

    def test_valid_exchange(self) -> None:
        """测试有效交易所."""
        info = ExchangeInfoModel(
            code="SHFE",
            name="上海期货交易所",
        )
        assert info.code == "SHFE"

    def test_invalid_exchange_code(self) -> None:
        """测试无效交易所代码."""
        with pytest.raises(ValueError):
            ExchangeInfoModel(
                code="INVALID",
                name="无效交易所",
            )

    def test_all_valid_codes(self) -> None:
        """测试所有有效代码."""
        valid_codes = ["SHFE", "DCE", "CZCE", "CFFEX", "GFEX", "INE"]
        for code in valid_codes:
            info = ExchangeInfoModel(code=code, name=f"{code}交易所")
            assert info.code == code


# ============================================================
# ExchangeConfigModel 测试
# ============================================================


class TestExchangeConfigModel:
    """交易所配置模型测试."""

    def test_valid_config(self, sample_exchange_data: dict) -> None:
        """测试有效配置."""
        config = ExchangeConfigModel(**sample_exchange_data)
        assert config.exchange.code == "SHFE"
        assert len(config.trading_sessions.day) == 2
        assert len(config.trading_sessions.night) == 1

    def test_get_all_products(self, sample_exchange_data: dict) -> None:
        """测试获取所有品种."""
        config = ExchangeConfigModel(**sample_exchange_data)
        products = config.get_all_products()
        assert len(products) == 1
        assert products[0].symbol == "cu"

    def test_get_product(self, sample_exchange_data: dict) -> None:
        """测试获取指定品种."""
        config = ExchangeConfigModel(**sample_exchange_data)
        product = config.get_product("cu")
        assert product is not None
        assert product.name == "铜"

        # 测试不存在的品种
        assert config.get_product("xxx") is None

    def test_has_night_session(self, sample_exchange_data: dict) -> None:
        """测试夜盘检测."""
        config = ExchangeConfigModel(**sample_exchange_data)
        assert config.has_night_session() is True

    def test_get_night_end_time(self, sample_exchange_data: dict) -> None:
        """测试获取夜盘收盘时间."""
        config = ExchangeConfigModel(**sample_exchange_data)
        assert config.get_night_end_time("cu") == "01:00"
        assert config.get_night_end_time("au") == "02:30"
        assert config.get_night_end_time("xxx") is None


# ============================================================
# 配置加载测试
# ============================================================


class TestConfigLoading:
    """配置加载测试."""

    def test_load_shfe_config(self, config_dir: Path) -> None:
        """测试加载SHFE配置."""
        if not (config_dir / "shfe.yml").exists():
            pytest.skip("SHFE配置文件不存在")

        config = load_exchange_config("SHFE", config_dir)
        assert config.exchange.code == "SHFE"
        assert config.has_night_session() is True

    def test_load_cffex_config(self, config_dir: Path) -> None:
        """测试加载CFFEX配置 (无夜盘)."""
        if not (config_dir / "cffex.yml").exists():
            pytest.skip("CFFEX配置文件不存在")

        config = load_exchange_config("CFFEX", config_dir)
        assert config.exchange.code == "CFFEX"
        assert config.has_night_session() is False

    def test_load_nonexistent_config(self, config_dir: Path) -> None:
        """测试加载不存在的配置."""
        with pytest.raises(FileNotFoundError):
            load_exchange_config("INVALID", config_dir)

    def test_load_all_exchanges(self, config_dir: Path) -> None:
        """测试加载所有交易所配置."""
        if not config_dir.exists():
            pytest.skip("配置目录不存在")

        configs = load_all_exchanges(config_dir)
        assert len(configs) > 0


# ============================================================
# 配置验证测试
# ============================================================


class TestValidation:
    """配置验证测试."""

    def test_validate_valid_config(self, sample_exchange_data: dict) -> None:
        """测试验证有效配置."""
        valid, error = validate_exchange_config(sample_exchange_data)
        assert valid is True
        assert error == ""

    def test_validate_invalid_config(self) -> None:
        """测试验证无效配置."""
        invalid_data = {
            "exchange": {
                "code": "INVALID",  # 无效代码
                "name": "测试",
            },
            "trading_sessions": {"day": [], "night": []},
            "products": {},
        }
        valid, error = validate_exchange_config(invalid_data)
        assert valid is False
        assert "无效的交易所代码" in error


# ============================================================
# ConfigValidator 测试
# ============================================================


class TestConfigValidator:
    """配置验证器测试."""

    def test_validator_init(self) -> None:
        """测试验证器初始化."""
        validator = ConfigValidator()
        assert len(validator.errors) == 0
        assert len(validator.warnings) == 0

    def test_validate_all(self, config_dir: Path) -> None:
        """测试验证所有配置."""
        if not config_dir.exists():
            pytest.skip("配置目录不存在")

        validator = ConfigValidator(config_dir)
        result = validator.validate_all()
        # 如果有配置文件,应该通过验证
        if list(config_dir.glob("*.yml")):
            assert result is True

    def test_get_report(self, config_dir: Path) -> None:
        """测试获取验证报告."""
        if not config_dir.exists():
            pytest.skip("配置目录不存在")

        validator = ConfigValidator(config_dir)
        validator.validate_all()
        report = validator.get_report()

        assert "valid" in report
        assert "exchange_count" in report
        assert "total_products" in report
        assert "errors" in report
        assert "warnings" in report


# ============================================================
# 品种映射测试
# ============================================================


class TestProductMapping:
    """品种映射测试."""

    def test_get_all_products_from_configs(self, config_dir: Path) -> None:
        """测试从配置获取所有品种."""
        if not config_dir.exists():
            pytest.skip("配置目录不存在")

        configs = load_all_exchanges(config_dir)
        if not configs:
            pytest.skip("未找到配置文件")

        products = get_all_products_from_configs(configs)
        assert len(products) > 0

        # 检查格式
        for symbol, (exchange_code, product) in products.items():
            assert isinstance(symbol, str)
            assert isinstance(exchange_code, str)
            assert isinstance(product, ProductModel)


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_empty_products(self) -> None:
        """测试空品种列表."""
        data = {
            "exchange": {
                "code": "SHFE",
                "name": "上海期货交易所",
            },
            "trading_sessions": {"day": [], "night": []},
            "products": {},
        }
        config = ExchangeConfigModel(**data)
        assert len(config.get_all_products()) == 0

    def test_empty_night_session_end(self) -> None:
        """测试空夜盘收盘时间."""
        data = {
            "exchange": {
                "code": "CFFEX",
                "name": "中国金融期货交易所",
            },
            "trading_sessions": {"day": [], "night": []},
            "night_session_end": {},
            "products": {},
        }
        config = ExchangeConfigModel(**data)
        assert config.get_night_end_time("IF") is None

    def test_case_insensitive_product_lookup(self) -> None:
        """测试品种查找大小写不敏感."""
        data = {
            "exchange": {
                "code": "SHFE",
                "name": "上海期货交易所",
            },
            "trading_sessions": {"day": [], "night": []},
            "products": {
                "metals": [
                    {
                        "symbol": "CU",
                        "name": "铜",
                        "multiplier": 5,
                        "tick_size": 10,
                    }
                ]
            },
        }
        config = ExchangeConfigModel(**data)
        assert config.get_product("cu") is not None
        assert config.get_product("CU") is not None
