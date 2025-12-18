"""CTP配置管理模块 (军规级 v4.0).

提供CTP连接配置的管理，包括:
- 配置数据类定义
- 环境变量加载
- 配置验证
- 环境隔离 (PAPER/LIVE)

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
from typing import Any


logger = logging.getLogger(__name__)


# =============================================================================
# 异常定义
# =============================================================================


class CtpConfigError(Exception):
    """CTP配置异常."""


class CtpConfigValidationError(CtpConfigError):
    """CTP配置验证异常."""


class CtpConfigMissingError(CtpConfigError):
    """CTP配置缺失异常."""


# =============================================================================
# 枚举定义
# =============================================================================


class TradeEnvironment(str, Enum):
    """交易环境枚举.

    PAPER: 模拟环境，不需要真实CTP配置
    SIM: 仿真环境，使用仿真前置
    LIVE: 实盘环境，使用实盘前置
    """

    PAPER = "PAPER"
    SIM = "SIM"
    LIVE = "LIVE"


# =============================================================================
# 配置数据类
# =============================================================================


@dataclass
class CtpConnectionConfig:
    """CTP连接配置.

    属性:
        front_addr: 前置地址 (如 tcp://180.168.146.187:10130)
        broker_id: 经纪商代码
        user_id: 用户ID
        password: 密码
        app_id: 应用ID (穿透式监管)
        auth_code: 认证码 (穿透式监管)
        product_info: 产品信息
        user_product_info: 用户产品信息
    """

    front_addr: str = ""
    broker_id: str = ""
    user_id: str = ""
    password: str = ""
    app_id: str = ""
    auth_code: str = ""
    product_info: str = ""
    user_product_info: str = ""

    def validate(self) -> list[str]:
        """验证配置完整性.

        返回:
            错误信息列表，空列表表示验证通过
        """
        errors: list[str] = []

        if not self.front_addr:
            errors.append("front_addr不能为空")
        elif not self.front_addr.startswith(("tcp://", "ssl://")):
            errors.append("front_addr必须以tcp://或ssl://开头")

        if not self.broker_id:
            errors.append("broker_id不能为空")

        if not self.user_id:
            errors.append("user_id不能为空")

        if not self.password:
            errors.append("password不能为空")

        return errors

    def is_valid(self) -> bool:
        """检查配置是否有效."""
        return len(self.validate()) == 0

    def to_dict(self, mask_password: bool = True) -> dict[str, Any]:
        """转换为字典.

        参数:
            mask_password: 是否掩码密码

        返回:
            配置字典
        """
        return {
            "front_addr": self.front_addr,
            "broker_id": self.broker_id,
            "user_id": self.user_id,
            "password": "***" if mask_password and self.password else self.password,
            "app_id": self.app_id,
            "auth_code": "***" if mask_password and self.auth_code else self.auth_code,
            "product_info": self.product_info,
            "user_product_info": self.user_product_info,
        }


@dataclass
class CtpMarketConfig:
    """CTP行情配置.

    属性:
        md_front_addr: 行情前置地址
        subscribe_symbols: 订阅的合约列表
        auto_reconnect: 是否自动重连
        reconnect_interval: 重连间隔 (秒)
        max_reconnect_attempts: 最大重连次数
    """

    md_front_addr: str = ""
    subscribe_symbols: list[str] = field(default_factory=list)
    auto_reconnect: bool = True
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 3


@dataclass
class CtpTradeConfig:
    """CTP交易配置.

    属性:
        td_front_addr: 交易前置地址
        max_order_ref: 最大订单引用号
        order_timeout: 订单超时时间 (秒)
        cancel_timeout: 撤单超时时间 (秒)
    """

    td_front_addr: str = ""
    max_order_ref: int = 999999
    order_timeout: float = 30.0
    cancel_timeout: float = 10.0


@dataclass
class CtpFullConfig:
    """CTP完整配置.

    属性:
        environment: 交易环境
        connection: 连接配置
        market: 行情配置
        trade: 交易配置
    """

    environment: TradeEnvironment = TradeEnvironment.PAPER
    connection: CtpConnectionConfig = field(default_factory=CtpConnectionConfig)
    market: CtpMarketConfig = field(default_factory=CtpMarketConfig)
    trade: CtpTradeConfig = field(default_factory=CtpTradeConfig)

    def validate(self) -> list[str]:
        """验证完整配置.

        返回:
            错误信息列表
        """
        errors: list[str] = []

        # PAPER模式不需要验证连接配置
        if self.environment == TradeEnvironment.PAPER:
            return errors

        # SIM/LIVE模式需要完整连接配置
        connection_errors = self.connection.validate()
        errors.extend(connection_errors)

        return errors

    def is_valid(self) -> bool:
        """检查配置是否有效."""
        return len(self.validate()) == 0


# =============================================================================
# 环境变量常量
# =============================================================================

# 必需的环境变量 (LIVE模式)
REQUIRED_CTP_ENV_VARS = (
    "CTP_FRONT_ADDR",
    "CTP_BROKER_ID",
    "CTP_USER_ID",
    "CTP_PASSWORD",
)

# 可选的环境变量
OPTIONAL_CTP_ENV_VARS = (
    "CTP_APP_ID",
    "CTP_AUTH_CODE",
    "CTP_PRODUCT_INFO",
    "CTP_USER_PRODUCT_INFO",
    "CTP_MD_FRONT_ADDR",
    "CTP_TD_FRONT_ADDR",
)

# 环境变量前缀
ENV_PREFIX = "CTP_"


# =============================================================================
# 配置加载函数
# =============================================================================


def load_ctp_config(
    environment: TradeEnvironment | str = TradeEnvironment.PAPER,
    require_complete: bool = False,
) -> CtpConnectionConfig:
    """从环境变量加载CTP配置.

    参数:
        environment: 交易环境
        require_complete: 是否要求配置完整

    返回:
        CTP连接配置

    异常:
        CtpConfigMissingError: LIVE模式下配置缺失
        CtpConfigValidationError: 配置验证失败
    """
    # 规范化环境参数
    if isinstance(environment, str):
        environment = TradeEnvironment(environment.upper())

    # PAPER模式：返回空配置或模拟配置
    if environment == TradeEnvironment.PAPER and not require_complete:
        logger.info("PAPER模式: 使用模拟CTP配置")
        return CtpConnectionConfig(
            front_addr="tcp://mock.ctp.local:10130",
            broker_id="MOCK",
            user_id="mock_user",
            password="mock_password",
        )

    # SIM/LIVE模式：从环境变量加载
    missing_vars = []
    for var in REQUIRED_CTP_ENV_VARS:
        if not os.environ.get(var):
            missing_vars.append(var)

    if missing_vars and (environment == TradeEnvironment.LIVE or require_complete):
        raise CtpConfigMissingError(
            f"缺失必需的环境变量: {', '.join(missing_vars)}。"
            f"请在{environment.value}模式下设置这些环境变量。"
        )

    # 加载配置
    config = CtpConnectionConfig(
        front_addr=os.environ.get("CTP_FRONT_ADDR", ""),
        broker_id=os.environ.get("CTP_BROKER_ID", ""),
        user_id=os.environ.get("CTP_USER_ID", ""),
        password=os.environ.get("CTP_PASSWORD", ""),
        app_id=os.environ.get("CTP_APP_ID", ""),
        auth_code=os.environ.get("CTP_AUTH_CODE", ""),
        product_info=os.environ.get("CTP_PRODUCT_INFO", ""),
        user_product_info=os.environ.get("CTP_USER_PRODUCT_INFO", ""),
    )

    # 验证配置
    if require_complete or environment == TradeEnvironment.LIVE:
        errors = config.validate()
        if errors:
            raise CtpConfigValidationError(f"CTP配置验证失败: {'; '.join(errors)}")

    logger.info(
        "CTP配置加载完成: environment=%s, broker_id=%s, user_id=%s",
        environment.value,
        config.broker_id or "(empty)",
        config.user_id or "(empty)",
    )

    return config


def load_full_ctp_config(
    environment: TradeEnvironment | str = TradeEnvironment.PAPER,
) -> CtpFullConfig:
    """加载完整CTP配置.

    参数:
        environment: 交易环境

    返回:
        完整CTP配置
    """
    # 规范化环境参数
    if isinstance(environment, str):
        environment = TradeEnvironment(environment.upper())

    # 加载连接配置
    connection_config = load_ctp_config(
        environment=environment,
        require_complete=(environment == TradeEnvironment.LIVE),
    )

    # 加载行情配置
    market_config = CtpMarketConfig(
        md_front_addr=os.environ.get("CTP_MD_FRONT_ADDR", connection_config.front_addr),
        subscribe_symbols=_parse_symbol_list(os.environ.get("CTP_SUBSCRIBE_SYMBOLS", "")),
        auto_reconnect=os.environ.get("CTP_AUTO_RECONNECT", "true").lower() == "true",
        reconnect_interval=float(os.environ.get("CTP_RECONNECT_INTERVAL", "5.0")),
        max_reconnect_attempts=int(os.environ.get("CTP_MAX_RECONNECT_ATTEMPTS", "3")),
    )

    # 加载交易配置
    trade_config = CtpTradeConfig(
        td_front_addr=os.environ.get("CTP_TD_FRONT_ADDR", connection_config.front_addr),
        max_order_ref=int(os.environ.get("CTP_MAX_ORDER_REF", "999999")),
        order_timeout=float(os.environ.get("CTP_ORDER_TIMEOUT", "30.0")),
        cancel_timeout=float(os.environ.get("CTP_CANCEL_TIMEOUT", "10.0")),
    )

    return CtpFullConfig(
        environment=environment,
        connection=connection_config,
        market=market_config,
        trade=trade_config,
    )


def _parse_symbol_list(symbols_str: str) -> list[str]:
    """解析合约列表字符串.

    参数:
        symbols_str: 逗号分隔的合约列表

    返回:
        合约代码列表
    """
    if not symbols_str:
        return []
    return [s.strip() for s in symbols_str.split(",") if s.strip()]


# =============================================================================
# 环境隔离检查
# =============================================================================


def check_environment_isolation(
    expected_env: TradeEnvironment,
    config: CtpConnectionConfig,
) -> bool:
    """检查环境隔离是否正确.

    确保配置与预期环境匹配，防止误操作。

    参数:
        expected_env: 预期环境
        config: CTP配置

    返回:
        环境隔离是否正确

    军规: M8 配置隔离
    """
    # PAPER模式: 允许任何配置
    if expected_env == TradeEnvironment.PAPER:
        return True

    # SIM模式: 检查是否使用仿真前置
    if expected_env == TradeEnvironment.SIM:
        sim_keywords = ["simnow", "sim", "test", "demo"]
        front_addr_lower = config.front_addr.lower()
        return any(kw in front_addr_lower for kw in sim_keywords)

    # LIVE模式: 不能使用仿真前置
    if expected_env == TradeEnvironment.LIVE:
        sim_keywords = ["simnow", "sim", "test", "demo", "mock"]
        front_addr_lower = config.front_addr.lower()
        if any(kw in front_addr_lower for kw in sim_keywords):
            logger.error(
                "LIVE模式检测到仿真前置地址: %s，拒绝加载",
                config.front_addr,
            )
            return False
        return True

    return True


def get_current_environment() -> TradeEnvironment:
    """获取当前交易环境.

    从环境变量TRADE_MODE读取。

    返回:
        当前交易环境
    """
    mode = os.environ.get("TRADE_MODE", "PAPER").upper()
    try:
        return TradeEnvironment(mode)
    except ValueError:
        logger.warning("无效的TRADE_MODE: %s，默认使用PAPER", mode)
        return TradeEnvironment.PAPER
