"""应用配置测试 (军规级 v4.0).

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

from src.app.config import (
    REQUIRED_PROD_ENV_VARS,
    AppConfig,
    ConfigMissingError,
    ConfigValidationError,
    DatabaseConfig,
    Environment,
    RedisConfig,
    TradingConfig,
    check_environment_isolation,
    get_config,
    get_current_environment,
    load_app_config,
    load_config_from_file,
    reset_config,
)


# =============================================================================
# 场景: INFRA.CONFIG.LOAD - 配置加载成功
# =============================================================================


class TestConfigLoad:
    """配置加载测试 - 场景: INFRA.CONFIG.LOAD."""

    def test_load_default_dev_mode(self) -> None:
        """测试加载默认DEV模式."""
        with patch.dict("os.environ", {}, clear=True):
            config = load_app_config()

            assert config.environment == Environment.DEV
            assert config.app_name == "V4PRO"

    def test_load_from_env_var(self) -> None:
        """测试从环境变量加载."""
        env = {
            "V4PRO_ENV": "TEST",
            "V4PRO_APP_NAME": "TestApp",
            "V4PRO_VERSION": "1.0.0",
        }
        with patch.dict("os.environ", env):
            config = load_app_config()

            assert config.environment == Environment.TEST
            assert config.app_name == "TestApp"
            assert config.version == "1.0.0"

    def test_load_database_config(self) -> None:
        """测试加载数据库配置."""
        env = {
            "DB_HOST": "db.example.com",
            "DB_PORT": "5433",
            "DB_NAME": "testdb",
            "DB_USER": "testuser",
            "DB_PASSWORD": "testpass",
            "DB_POOL_SIZE": "10",
        }
        with patch.dict("os.environ", env):
            config = load_app_config()

            assert config.database.host == "db.example.com"
            assert config.database.port == 5433
            assert config.database.name == "testdb"
            assert config.database.user == "testuser"
            assert config.database.password == "testpass"
            assert config.database.pool_size == 10

    def test_load_redis_config(self) -> None:
        """测试加载Redis配置."""
        env = {
            "REDIS_HOST": "redis.example.com",
            "REDIS_PORT": "6380",
            "REDIS_DB": "1",
            "REDIS_PASSWORD": "redispass",
        }
        with patch.dict("os.environ", env):
            config = load_app_config()

            assert config.redis.host == "redis.example.com"
            assert config.redis.port == 6380
            assert config.redis.db == 1
            assert config.redis.password == "redispass"

    def test_load_trading_config(self) -> None:
        """测试加载交易配置."""
        env = {
            "TRADING_MAX_POSITION": "5000000",
            "TRADING_MAX_ORDER_VOLUME": "50",
            "TRADING_MAX_DAILY_LOSS": "50000",
            "TRADING_MARGIN_WARNING": "0.6",
            "TRADING_MARGIN_DANGER": "0.8",
        }
        with patch.dict("os.environ", env):
            config = load_app_config()

            assert config.trading.max_position_value == 5000000.0
            assert config.trading.max_order_volume == 50
            assert config.trading.max_daily_loss == 50000.0
            assert config.trading.margin_warning_level == 0.6
            assert config.trading.margin_danger_level == 0.8

    def test_load_debug_mode(self) -> None:
        """测试加载调试模式."""
        with patch.dict("os.environ", {"V4PRO_DEBUG": "true"}):
            config = load_app_config()
            assert config.debug is True

        with patch.dict("os.environ", {"V4PRO_DEBUG": "false"}):
            config = load_app_config()
            assert config.debug is False

    def test_load_prod_missing_vars_raises(self) -> None:
        """测试PROD模式缺失变量抛出异常."""
        with patch.dict("os.environ", {"V4PRO_ENV": "PROD"}, clear=True):
            with pytest.raises(ConfigMissingError) as exc_info:
                load_app_config()

            assert "缺失必需的环境变量" in str(exc_info.value)

    def test_load_prod_with_all_vars(self) -> None:
        """测试PROD模式带所有变量."""
        env = {
            "V4PRO_ENV": "PROD",
            "DB_HOST": "prod.db.example.com",
            "DB_USER": "produser",
            "DB_PASSWORD": "prodpass",
            "DB_NAME": "proddb",
        }
        with patch.dict("os.environ", env):
            config = load_app_config()

            assert config.environment == Environment.PROD
            assert config.database.host == "prod.db.example.com"

    def test_load_with_string_environment(self) -> None:
        """测试使用字符串环境参数."""
        config = load_app_config(environment="dev")
        assert config.environment == Environment.DEV

        config = load_app_config(environment="TEST")
        assert config.environment == Environment.TEST

    def test_load_invalid_env_falls_back_to_dev(self) -> None:
        """测试无效环境回退到DEV."""
        with patch.dict("os.environ", {"V4PRO_ENV": "INVALID"}):
            config = load_app_config()
            assert config.environment == Environment.DEV


# =============================================================================
# 场景: INFRA.CONFIG.VALIDATE - 配置验证通过
# =============================================================================


class TestConfigValidate:
    """配置验证测试 - 场景: INFRA.CONFIG.VALIDATE."""

    def test_validate_valid_config(self) -> None:
        """测试验证有效配置."""
        config = AppConfig(
            environment=Environment.DEV,
            app_name="V4PRO",
            version="4.0.0",
            database=DatabaseConfig(host="localhost", name="v4pro"),
            trading=TradingConfig(),
        )

        errors = config.validate()

        assert len(errors) == 0
        assert config.is_valid() is True

    def test_validate_empty_app_name(self) -> None:
        """测试验证空应用名称."""
        config = AppConfig(app_name="")

        errors = config.validate()

        assert "app_name不能为空" in errors

    def test_validate_empty_version(self) -> None:
        """测试验证空版本号."""
        config = AppConfig(version="")

        errors = config.validate()

        assert "version不能为空" in errors

    def test_validate_prod_debug_not_allowed(self) -> None:
        """测试PROD环境不允许debug."""
        config = AppConfig(
            environment=Environment.PROD,
            debug=True,
        )

        errors = config.validate()

        assert "PROD环境不允许开启debug模式" in errors

    def test_validate_database_config(self) -> None:
        """测试验证数据库配置."""
        db_config = DatabaseConfig(host="", name="")

        errors = db_config.validate()

        assert "数据库host不能为空" in errors
        assert "数据库name不能为空" in errors

    def test_validate_trading_config(self) -> None:
        """测试验证交易配置."""
        trading_config = TradingConfig(
            max_position_value=-1,
            max_order_volume=0,
            max_daily_loss=-100,
            margin_warning_level=1.5,
            margin_danger_level=0.5,
        )

        errors = trading_config.validate()

        assert "max_position_value必须大于0" in errors
        assert "max_order_volume必须大于0" in errors
        assert "max_daily_loss必须大于0" in errors
        assert "margin_warning_level必须在0-1之间" in errors

    def test_validate_margin_levels_order(self) -> None:
        """测试验证保证金水平顺序."""
        trading_config = TradingConfig(
            margin_warning_level=0.9,
            margin_danger_level=0.8,
        )

        errors = trading_config.validate()

        assert "margin_warning_level必须小于margin_danger_level" in errors

    def test_load_validates_on_prod(self) -> None:
        """测试PROD模式加载时验证."""
        env = {
            "V4PRO_ENV": "PROD",
            "DB_HOST": "prod.db.example.com",
            "DB_USER": "user",
            "DB_PASSWORD": "pass",
            "DB_NAME": "",  # 空名称
            "V4PRO_DEBUG": "true",  # PROD不允许debug
        }
        with patch.dict("os.environ", env):
            with pytest.raises(ConfigValidationError) as exc_info:
                load_app_config()

            assert "验证失败" in str(exc_info.value)


# =============================================================================
# 场景: INFRA.CONFIG.ENV_ISOLATE - 环境隔离正确
# =============================================================================


class TestEnvironmentIsolation:
    """环境隔离测试 - 场景: INFRA.CONFIG.ENV_ISOLATE, 军规: M8."""

    def test_dev_mode_allows_any_config(self) -> None:
        """测试DEV模式允许任何配置."""
        config = AppConfig(
            environment=Environment.DEV,
            database=DatabaseConfig(host="any.server", name="anydb"),
        )

        result = check_environment_isolation(Environment.DEV, config)

        assert result is True

    def test_test_mode_allows_test_db(self) -> None:
        """测试TEST模式允许测试数据库."""
        config = AppConfig(
            environment=Environment.TEST,
            database=DatabaseConfig(host="db.example.com", name="test_v4pro"),
        )

        result = check_environment_isolation(Environment.TEST, config)

        assert result is True

    def test_test_mode_allows_localhost(self) -> None:
        """测试TEST模式允许localhost."""
        config = AppConfig(
            environment=Environment.TEST,
            database=DatabaseConfig(host="localhost", name="proddb"),
        )

        result = check_environment_isolation(Environment.TEST, config)

        assert result is True

    def test_test_mode_allows_127_0_0_1(self) -> None:
        """测试TEST模式允许127.0.0.1."""
        config = AppConfig(
            environment=Environment.TEST,
            database=DatabaseConfig(host="127.0.0.1", name="proddb"),
        )

        result = check_environment_isolation(Environment.TEST, config)

        assert result is True

    def test_test_mode_rejects_prod_db(self) -> None:
        """测试TEST模式拒绝生产数据库."""
        config = AppConfig(
            environment=Environment.TEST,
            database=DatabaseConfig(host="prod.db.example.com", name="production"),
        )

        result = check_environment_isolation(Environment.TEST, config)

        assert result is False

    def test_prod_mode_rejects_test_db(self) -> None:
        """测试PROD模式拒绝测试数据库."""
        config = AppConfig(
            environment=Environment.PROD,
            database=DatabaseConfig(host="prod.db.example.com", name="test_db"),
        )

        result = check_environment_isolation(Environment.PROD, config)

        assert result is False

    def test_prod_mode_rejects_dev_db(self) -> None:
        """测试PROD模式拒绝开发数据库."""
        config = AppConfig(
            environment=Environment.PROD,
            database=DatabaseConfig(host="prod.db.example.com", name="dev_v4pro"),
        )

        result = check_environment_isolation(Environment.PROD, config)

        assert result is False

    def test_prod_mode_rejects_localhost(self) -> None:
        """测试PROD模式拒绝localhost."""
        config = AppConfig(
            environment=Environment.PROD,
            database=DatabaseConfig(host="localhost", name="proddb"),
        )

        result = check_environment_isolation(Environment.PROD, config)

        assert result is False

    def test_prod_mode_rejects_debug(self) -> None:
        """测试PROD模式拒绝debug."""
        config = AppConfig(
            environment=Environment.PROD,
            debug=True,
            database=DatabaseConfig(host="prod.db.example.com", name="proddb"),
        )

        result = check_environment_isolation(Environment.PROD, config)

        assert result is False

    def test_prod_mode_accepts_valid_config(self) -> None:
        """测试PROD模式接受有效配置."""
        config = AppConfig(
            environment=Environment.PROD,
            debug=False,
            database=DatabaseConfig(host="prod.db.example.com", name="v4pro_production"),
        )

        result = check_environment_isolation(Environment.PROD, config)

        assert result is True


# =============================================================================
# DatabaseConfig数据类测试
# =============================================================================


class TestDatabaseConfig:
    """数据库配置数据类测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = DatabaseConfig()

        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "v4pro"
        assert config.user == ""
        assert config.password == ""
        assert config.pool_size == 5

    def test_to_dict_masks_password(self) -> None:
        """测试转字典掩码密码."""
        config = DatabaseConfig(
            host="db.example.com",
            user="testuser",
            password="secret",
        )

        d = config.to_dict(mask_password=True)

        assert d["password"] == "***"
        assert d["user"] == "testuser"

    def test_to_dict_shows_password(self) -> None:
        """测试转字典显示密码."""
        config = DatabaseConfig(password="secret")

        d = config.to_dict(mask_password=False)

        assert d["password"] == "secret"

    def test_to_dict_empty_password(self) -> None:
        """测试转字典空密码."""
        config = DatabaseConfig(password="")

        d = config.to_dict(mask_password=True)

        assert d["password"] == ""


# =============================================================================
# RedisConfig数据类测试
# =============================================================================


class TestRedisConfig:
    """Redis配置数据类测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = RedisConfig()

        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password == ""

    def test_to_dict_masks_password(self) -> None:
        """测试转字典掩码密码."""
        config = RedisConfig(password="secret")

        d = config.to_dict(mask_password=True)

        assert d["password"] == "***"

    def test_to_dict_shows_password(self) -> None:
        """测试转字典显示密码."""
        config = RedisConfig(password="secret")

        d = config.to_dict(mask_password=False)

        assert d["password"] == "secret"


# =============================================================================
# TradingConfig数据类测试
# =============================================================================


class TestTradingConfig:
    """交易配置数据类测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = TradingConfig()

        assert config.max_position_value == 10000000.0
        assert config.max_order_volume == 100
        assert config.max_daily_loss == 100000.0
        assert config.margin_warning_level == 0.7
        assert config.margin_danger_level == 0.85

    def test_to_dict(self) -> None:
        """测试转字典."""
        config = TradingConfig(
            max_position_value=5000000.0,
            max_order_volume=50,
        )

        d = config.to_dict()

        assert d["max_position_value"] == 5000000.0
        assert d["max_order_volume"] == 50


# =============================================================================
# AppConfig数据类测试
# =============================================================================


class TestAppConfig:
    """应用配置数据类测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = AppConfig()

        assert config.environment == Environment.DEV
        assert config.app_name == "V4PRO"
        assert config.version == "4.0.0"
        assert config.debug is False

    def test_to_dict(self) -> None:
        """测试转字典."""
        config = AppConfig(
            environment=Environment.TEST,
            app_name="TestApp",
            version="1.0.0",
            debug=True,
        )

        d = config.to_dict()

        assert d["environment"] == "TEST"
        assert d["app_name"] == "TestApp"
        assert d["version"] == "1.0.0"
        assert d["debug"] is True

    def test_to_dict_masks_secrets(self) -> None:
        """测试转字典掩码敏感信息."""
        config = AppConfig(
            database=DatabaseConfig(password="dbsecret"),
            redis=RedisConfig(password="redissecret"),
        )

        d = config.to_dict(mask_secrets=True)

        assert d["database"]["password"] == "***"
        assert d["redis"]["password"] == "***"


# =============================================================================
# Environment枚举测试
# =============================================================================


class TestEnvironment:
    """环境枚举测试."""

    def test_dev_value(self) -> None:
        """测试DEV值."""
        assert Environment.DEV.value == "DEV"

    def test_test_value(self) -> None:
        """测试TEST值."""
        assert Environment.TEST.value == "TEST"

    def test_prod_value(self) -> None:
        """测试PROD值."""
        assert Environment.PROD.value == "PROD"

    def test_from_string(self) -> None:
        """测试从字符串创建."""
        assert Environment("DEV") == Environment.DEV
        assert Environment("TEST") == Environment.TEST
        assert Environment("PROD") == Environment.PROD


# =============================================================================
# get_current_environment测试
# =============================================================================


class TestGetCurrentEnvironment:
    """获取当前环境测试."""

    def test_default_dev(self) -> None:
        """测试默认DEV环境."""
        with patch.dict("os.environ", {}, clear=True):
            env = get_current_environment()
            assert env == Environment.DEV

    def test_from_env_var(self) -> None:
        """测试从环境变量获取."""
        with patch.dict("os.environ", {"V4PRO_ENV": "PROD"}):
            env = get_current_environment()
            assert env == Environment.PROD

    def test_invalid_falls_back_to_dev(self) -> None:
        """测试无效值回退到DEV."""
        with patch.dict("os.environ", {"V4PRO_ENV": "INVALID"}):
            env = get_current_environment()
            assert env == Environment.DEV

    def test_case_insensitive(self) -> None:
        """测试大小写不敏感."""
        with patch.dict("os.environ", {"V4PRO_ENV": "prod"}):
            env = get_current_environment()
            assert env == Environment.PROD


# =============================================================================
# 单例配置测试
# =============================================================================


class TestSingletonConfig:
    """单例配置测试."""

    def test_get_config_returns_same_instance(self) -> None:
        """测试get_config返回相同实例."""
        reset_config()

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config_clears_instance(self) -> None:
        """测试reset_config清除实例."""
        config1 = get_config()
        reset_config()
        config2 = get_config()

        # 应该是不同的实例
        assert config1 is not config2


# =============================================================================
# 常量测试
# =============================================================================


class TestConstants:
    """常量测试."""

    def test_required_prod_env_vars(self) -> None:
        """测试必需的PROD环境变量."""
        assert "DB_HOST" in REQUIRED_PROD_ENV_VARS
        assert "DB_USER" in REQUIRED_PROD_ENV_VARS
        assert "DB_PASSWORD" in REQUIRED_PROD_ENV_VARS


# =============================================================================
# load_config_from_file测试
# =============================================================================


class TestLoadConfigFromFile:
    """从文件加载配置测试."""

    def test_load_from_yaml_file(self, tmp_path: object) -> None:
        """测试从YAML文件加载."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.yaml"
            config_file.write_text(
                """
environment: TEST
app_name: FileApp
version: 2.0.0
debug: true
database:
  host: file.db.example.com
  port: 5433
  name: filedb
  user: fileuser
  password: filepass
  pool_size: 20
redis:
  host: file.redis.example.com
  port: 6380
  db: 2
trading:
  max_position_value: 8000000
  max_order_volume: 80
"""
            )

            config = load_config_from_file(config_file)

            assert config.environment == Environment.TEST
            assert config.app_name == "FileApp"
            assert config.version == "2.0.0"
            assert config.debug is True
            assert config.database.host == "file.db.example.com"
            assert config.database.port == 5433
            assert config.redis.host == "file.redis.example.com"
            assert config.trading.max_position_value == 8000000

    def test_load_from_nonexistent_file_raises(self) -> None:
        """测试加载不存在的文件抛出异常."""
        from src.app.config import ConfigLoadError

        with pytest.raises(ConfigLoadError, match="配置文件不存在"):
            load_config_from_file("/nonexistent/path/config.yaml")

    def test_load_from_empty_file_raises(self) -> None:
        """测试加载空文件抛出异常."""
        import tempfile
        from pathlib import Path

        from src.app.config import ConfigLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "empty.yaml"
            config_file.write_text("")

            with pytest.raises(ConfigLoadError, match="配置文件为空"):
                load_config_from_file(config_file)

    def test_load_from_invalid_yaml_raises(self) -> None:
        """测试加载无效YAML抛出异常."""
        import tempfile
        from pathlib import Path

        from src.app.config import ConfigLoadError

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "invalid.yaml"
            config_file.write_text("invalid: yaml: content: [")

            with pytest.raises(ConfigLoadError, match="配置文件解析失败"):
                load_config_from_file(config_file)

    def test_load_with_defaults(self) -> None:
        """测试加载使用默认值."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "minimal.yaml"
            config_file.write_text("app_name: MinimalApp\n")

            config = load_config_from_file(config_file)

            assert config.app_name == "MinimalApp"
            assert config.environment == Environment.DEV  # 默认值
            assert config.database.host == "localhost"  # 默认值
