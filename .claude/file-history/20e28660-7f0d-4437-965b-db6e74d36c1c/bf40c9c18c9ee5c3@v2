"""应用配置模块 (军规级 v4.0).

提供应用级配置管理，包括:
- 配置数据类定义
- 环境变量加载
- 配置验证
- 环境隔离 (DEV/TEST/PROD)

军规覆盖:
- M8 配置隔离: 不同环境配置严格隔离
- M9 错误上报: 配置错误统一处理

场景覆盖:
- INFRA.CONFIG.LOAD: 配置加载成功
- INFRA.CONFIG.VALIDATE: 配置验证通过
- INFRA.CONFIG.ENV_ISOLATE: 环境隔离正确
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# =============================================================================
# 异常定义
# =============================================================================


class ConfigError(Exception):
    """配置异常基类."""


class ConfigLoadError(ConfigError):
    """配置加载异常."""


class ConfigValidationError(ConfigError):
    """配置验证异常."""


class ConfigMissingError(ConfigError):
    """配置缺失异常."""


# =============================================================================
# 枚举定义
# =============================================================================


class Environment(str, Enum):
    """运行环境枚举.

    DEV: 开发环境
    TEST: 测试环境
    PROD: 生产环境
    """

    DEV = "DEV"
    TEST = "TEST"
    PROD = "PROD"


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class DatabaseConfig:
    """数据库配置.

    属性:
        host: 数据库主机
        port: 数据库端口
        name: 数据库名称
        user: 用户名
        password: 密码
        pool_size: 连接池大小
    """

    host: str = "localhost"
    port: int = 5432
    name: str = "v4pro"
    user: str = ""
    password: str = ""
    pool_size: int = 5

    def validate(self) -> list[str]:
        """验证配置完整性.

        返回:
            错误信息列表
        """
        errors: list[str] = []

        if not self.host:
            errors.append("数据库host不能为空")
        if not self.name:
            errors.append("数据库name不能为空")

        return errors

    def to_dict(self, mask_password: bool = True) -> dict[str, Any]:
        """转换为字典.

        参数:
            mask_password: 是否掩码密码

        返回:
            配置字典
        """
        return {
            "host": self.host,
            "port": self.port,
            "name": self.name,
            "user": self.user,
            "password": "***" if mask_password and self.password else self.password,
            "pool_size": self.pool_size,
        }


@dataclass
class RedisConfig:
    """Redis配置.

    属性:
        host: Redis主机
        port: Redis端口
        db: 数据库编号
        password: 密码
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""

    def to_dict(self, mask_password: bool = True) -> dict[str, Any]:
        """转换为字典."""
        return {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "password": "***" if mask_password and self.password else self.password,
        }


@dataclass
class TradingConfig:
    """交易配置.

    属性:
        max_position_value: 最大持仓价值
        max_order_volume: 最大订单数量
        max_daily_loss: 最大日亏损
        margin_warning_level: 保证金预警水平
        margin_danger_level: 保证金危险水平
    """

    max_position_value: float = 10000000.0
    max_order_volume: int = 100
    max_daily_loss: float = 100000.0
    margin_warning_level: float = 0.7
    margin_danger_level: float = 0.85

    def validate(self) -> list[str]:
        """验证配置完整性.

        返回:
            错误信息列表
        """
        errors: list[str] = []

        if self.max_position_value <= 0:
            errors.append("max_position_value必须大于0")
        if self.max_order_volume <= 0:
            errors.append("max_order_volume必须大于0")
        if self.max_daily_loss <= 0:
            errors.append("max_daily_loss必须大于0")
        if not 0 < self.margin_warning_level < 1:
            errors.append("margin_warning_level必须在0-1之间")
        if not 0 < self.margin_danger_level <= 1:
            errors.append("margin_danger_level必须在0-1之间")
        if self.margin_warning_level >= self.margin_danger_level:
            errors.append("margin_warning_level必须小于margin_danger_level")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "max_position_value": self.max_position_value,
            "max_order_volume": self.max_order_volume,
            "max_daily_loss": self.max_daily_loss,
            "margin_warning_level": self.margin_warning_level,
            "margin_danger_level": self.margin_danger_level,
        }


@dataclass
class AppConfig:
    """应用配置.

    属性:
        environment: 运行环境
        app_name: 应用名称
        version: 版本号
        debug: 是否调试模式
        database: 数据库配置
        redis: Redis配置
        trading: 交易配置
    """

    environment: Environment = Environment.DEV
    app_name: str = "V4PRO"
    version: str = "4.0.0"
    debug: bool = False
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)

    def validate(self) -> list[str]:
        """验证完整配置.

        返回:
            错误信息列表

        场景: INFRA.CONFIG.VALIDATE
        """
        errors: list[str] = []

        # 验证基本配置
        if not self.app_name:
            errors.append("app_name不能为空")
        if not self.version:
            errors.append("version不能为空")

        # PROD环境特殊验证
        if self.environment == Environment.PROD:
            if self.debug:
                errors.append("PROD环境不允许开启debug模式")

        # 验证子配置
        errors.extend(self.database.validate())
        errors.extend(self.trading.validate())

        return errors

    def is_valid(self) -> bool:
        """检查配置是否有效."""
        return len(self.validate()) == 0

    def to_dict(self, mask_secrets: bool = True) -> dict[str, Any]:
        """转换为字典.

        参数:
            mask_secrets: 是否掩码敏感信息

        返回:
            配置字典
        """
        return {
            "environment": self.environment.value,
            "app_name": self.app_name,
            "version": self.version,
            "debug": self.debug,
            "database": self.database.to_dict(mask_secrets),
            "redis": self.redis.to_dict(mask_secrets),
            "trading": self.trading.to_dict(),
        }


# =============================================================================
# 环境变量常量
# =============================================================================

# 必需的环境变量 (PROD模式)
REQUIRED_PROD_ENV_VARS = (
    "DB_HOST",
    "DB_USER",
    "DB_PASSWORD",
)

# 环境变量前缀
ENV_PREFIX = "V4PRO_"


# =============================================================================
# 配置加载函数
# =============================================================================


def load_app_config(
    environment: Environment | str | None = None,
    require_complete: bool = False,
) -> AppConfig:
    """从环境变量加载应用配置.

    参数:
        environment: 运行环境，为None则从环境变量读取
        require_complete: 是否要求配置完整

    返回:
        应用配置

    异常:
        ConfigMissingError: PROD模式下配置缺失
        ConfigValidationError: 配置验证失败

    场景: INFRA.CONFIG.LOAD
    """
    # 确定环境
    if environment is None:
        env_str = os.environ.get("V4PRO_ENV", "DEV").upper()
        try:
            environment = Environment(env_str)
        except ValueError:
            logger.warning("无效的V4PRO_ENV: %s, 默认使用DEV", env_str)
            environment = Environment.DEV
    elif isinstance(environment, str):
        environment = Environment(environment.upper())

    # PROD模式下检查必需变量
    if environment == Environment.PROD or require_complete:
        missing_vars = []
        for var in REQUIRED_PROD_ENV_VARS:
            if not os.environ.get(var):
                missing_vars.append(var)

        if missing_vars:
            raise ConfigMissingError(
                f"缺失必需的环境变量: {', '.join(missing_vars)}。"
                f"请在{environment.value}模式下设置这些环境变量。"
            )

    # 加载数据库配置
    db_config = DatabaseConfig(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        name=os.environ.get("DB_NAME", "v4pro"),
        user=os.environ.get("DB_USER", ""),
        password=os.environ.get("DB_PASSWORD", ""),
        pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
    )

    # 加载Redis配置
    redis_config = RedisConfig(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6379")),
        db=int(os.environ.get("REDIS_DB", "0")),
        password=os.environ.get("REDIS_PASSWORD", ""),
    )

    # 加载交易配置
    trading_config = TradingConfig(
        max_position_value=float(os.environ.get("TRADING_MAX_POSITION", "10000000")),
        max_order_volume=int(os.environ.get("TRADING_MAX_ORDER_VOLUME", "100")),
        max_daily_loss=float(os.environ.get("TRADING_MAX_DAILY_LOSS", "100000")),
        margin_warning_level=float(os.environ.get("TRADING_MARGIN_WARNING", "0.7")),
        margin_danger_level=float(os.environ.get("TRADING_MARGIN_DANGER", "0.85")),
    )

    # 创建应用配置
    config = AppConfig(
        environment=environment,
        app_name=os.environ.get("V4PRO_APP_NAME", "V4PRO"),
        version=os.environ.get("V4PRO_VERSION", "4.0.0"),
        debug=os.environ.get("V4PRO_DEBUG", "false").lower() == "true",
        database=db_config,
        redis=redis_config,
        trading=trading_config,
    )

    # 验证配置
    if require_complete or environment == Environment.PROD:
        errors = config.validate()
        if errors:
            raise ConfigValidationError(f"配置验证失败: {'; '.join(errors)}")

    logger.info(
        "应用配置加载完成: environment=%s, app_name=%s",
        config.environment.value,
        config.app_name,
    )

    return config


def load_config_from_file(filepath: str | Path) -> AppConfig:
    """从YAML文件加载配置.

    参数:
        filepath: 配置文件路径

    返回:
        应用配置

    异常:
        ConfigLoadError: 文件加载失败
    """
    import yaml

    filepath = Path(filepath)

    if not filepath.exists():
        raise ConfigLoadError(f"配置文件不存在: {filepath}")

    try:
        with open(filepath, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigLoadError(f"配置文件解析失败: {e}") from e

    if not data:
        raise ConfigLoadError("配置文件为空")

    # 解析环境
    env_str = data.get("environment", "DEV").upper()
    try:
        environment = Environment(env_str)
    except ValueError:
        environment = Environment.DEV

    # 解析数据库配置
    db_data = data.get("database", {})
    db_config = DatabaseConfig(
        host=db_data.get("host", "localhost"),
        port=db_data.get("port", 5432),
        name=db_data.get("name", "v4pro"),
        user=db_data.get("user", ""),
        password=db_data.get("password", ""),
        pool_size=db_data.get("pool_size", 5),
    )

    # 解析Redis配置
    redis_data = data.get("redis", {})
    redis_config = RedisConfig(
        host=redis_data.get("host", "localhost"),
        port=redis_data.get("port", 6379),
        db=redis_data.get("db", 0),
        password=redis_data.get("password", ""),
    )

    # 解析交易配置
    trading_data = data.get("trading", {})
    trading_config = TradingConfig(
        max_position_value=trading_data.get("max_position_value", 10000000.0),
        max_order_volume=trading_data.get("max_order_volume", 100),
        max_daily_loss=trading_data.get("max_daily_loss", 100000.0),
        margin_warning_level=trading_data.get("margin_warning_level", 0.7),
        margin_danger_level=trading_data.get("margin_danger_level", 0.85),
    )

    return AppConfig(
        environment=environment,
        app_name=data.get("app_name", "V4PRO"),
        version=data.get("version", "4.0.0"),
        debug=data.get("debug", False),
        database=db_config,
        redis=redis_config,
        trading=trading_config,
    )


# =============================================================================
# 环境隔离检查
# =============================================================================


def check_environment_isolation(
    expected_env: Environment,
    config: AppConfig,
) -> bool:
    """检查环境隔离是否正确.

    确保配置与预期环境匹配，防止误操作。

    参数:
        expected_env: 预期环境
        config: 应用配置

    返回:
        环境隔离是否正确

    场景: INFRA.CONFIG.ENV_ISOLATE
    军规: M8 配置隔离
    """
    # DEV环境: 允许任何配置
    if expected_env == Environment.DEV:
        return True

    # TEST环境: 检查是否使用测试数据库
    if expected_env == Environment.TEST:
        test_keywords = ["test", "dev", "staging", "sandbox"]
        db_name_lower = config.database.name.lower()
        if any(kw in db_name_lower for kw in test_keywords):
            return True
        # 允许localhost
        if config.database.host in ("localhost", "127.0.0.1"):
            return True
        logger.warning(
            "TEST模式检测到非测试数据库: %s",
            config.database.name,
        )
        return False

    # PROD环境: 不能使用测试/开发配置
    if expected_env == Environment.PROD:
        dev_keywords = ["test", "dev", "staging", "sandbox", "local"]
        db_name_lower = config.database.name.lower()
        db_host_lower = config.database.host.lower()

        if any(kw in db_name_lower for kw in dev_keywords):
            logger.error(
                "PROD模式检测到开发/测试数据库名: %s",
                config.database.name,
            )
            return False

        if db_host_lower in ("localhost", "127.0.0.1"):
            logger.error(
                "PROD模式检测到本地数据库: %s",
                config.database.host,
            )
            return False

        # 不允许debug模式
        if config.debug:
            logger.error("PROD模式不允许开启debug")
            return False

        return True

    return True


def get_current_environment() -> Environment:
    """获取当前运行环境.

    从环境变量V4PRO_ENV读取。

    返回:
        当前运行环境
    """
    env_str = os.environ.get("V4PRO_ENV", "DEV").upper()
    try:
        return Environment(env_str)
    except ValueError:
        logger.warning("无效的V4PRO_ENV: %s, 默认使用DEV", env_str)
        return Environment.DEV


# =============================================================================
# 单例配置实例
# =============================================================================


_config_instance: AppConfig | None = None


def get_config() -> AppConfig:
    """获取全局配置实例.

    返回:
        应用配置
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = load_app_config()
    return _config_instance


def reset_config() -> None:
    """重置全局配置实例.

    主要用于测试。
    """
    global _config_instance
    _config_instance = None
