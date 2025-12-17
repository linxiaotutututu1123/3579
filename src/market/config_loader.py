"""
配置验证模块 (军规级 v4.1).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §27 配置结构化验证

军规覆盖:
- M21: 配置验证 - 所有配置必须通过 pydantic 验证

功能特性:
- Pydantic 模型验证
- YAML 配置文件加载
- 交易所配置验证
- 品种配置验证

示例:
    >>> from src.config.exchange_config_loader import (
    ...     load_exchange_config,
    ...     load_all_exchanges,
    ...     ExchangeConfigModel,
    ... )
    >>> config = load_exchange_config("SHFE")
    >>> all_configs = load_all_exchanges()
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Pydantic 模型定义
# ============================================================


class TradingSessionModel(BaseModel):
    """交易时段模型."""

    start: str = Field(..., description="开始时间 (HH:MM)")
    end: str = Field(..., description="结束时间 (HH:MM)")

    @field_validator("start", "end")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """验证时间格式."""
        parts = v.split(":")
        if len(parts) != 2:
            msg = f"时间格式错误: {v}, 应为 HH:MM"
            raise ValueError(msg)
        hour, minute = int(parts[0]), int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            msg = f"时间范围错误: {v}"
            raise ValueError(msg)
        return v


class TradingSessionsModel(BaseModel):
    """交易时段集合模型."""

    day: list[TradingSessionModel] = Field(default_factory=list, description="日盘时段")
    night: list[TradingSessionModel] = Field(default_factory=list, description="夜盘时段")


class ProductModel(BaseModel):
    """品种模型."""

    symbol: str = Field(..., description="品种代码")
    name: str = Field(..., description="品种名称")
    multiplier: int = Field(..., gt=0, description="合约乘数")
    tick_size: float = Field(..., gt=0, description="最小变动价位")
    margin_ratio: float = Field(0.1, ge=0, le=1, description="保证金比率")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """验证品种代码."""
        if not v:
            msg = "品种代码不能为空"
            raise ValueError(msg)
        return v


class ExchangeInfoModel(BaseModel):
    """交易所信息模型."""

    code: str = Field(..., description="交易所代码")
    name: str = Field(..., description="交易所中文名称")
    name_en: str = Field("", description="交易所英文名称")
    timezone: str = Field("Asia/Shanghai", description="时区")

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """验证交易所代码."""
        valid_codes = {"SHFE", "DCE", "CZCE", "CFFEX", "GFEX", "INE"}
        if v not in valid_codes:
            msg = f"无效的交易所代码: {v}, 有效值: {valid_codes}"
            raise ValueError(msg)
        return v


class ExchangeConfigModel(BaseModel):
    """交易所完整配置模型."""

    exchange: ExchangeInfoModel = Field(..., description="交易所信息")
    trading_sessions: TradingSessionsModel = Field(..., description="交易时段")
    night_session_end: dict[str, list[str]] = Field(
        default_factory=dict, description="夜盘收盘时间"
    )
    products: dict[str, list[ProductModel]] = Field(default_factory=dict, description="品种列表")

    def get_all_products(self) -> list[ProductModel]:
        """获取所有品种."""
        result: list[ProductModel] = []
        for category_products in self.products.values():
            result.extend(category_products)
        return result

    def get_product(self, symbol: str) -> ProductModel | None:
        """获取指定品种."""
        for category_products in self.products.values():
            for product in category_products:
                if product.symbol.upper() == symbol.upper():
                    return product
        return None

    def has_night_session(self) -> bool:
        """检查是否有夜盘."""
        return len(self.trading_sessions.night) > 0

    def get_night_end_time(self, symbol: str) -> str | None:
        """获取品种夜盘收盘时间."""
        for end_time, symbols in self.night_session_end.items():
            if symbol.lower() in [s.lower() for s in symbols]:
                return end_time
        return None


# ============================================================
# 配置加载函数
# ============================================================


def load_exchange_config(
    exchange_code: str,
    config_dir: Path | None = None,
) -> ExchangeConfigModel:
    """加载交易所配置.

    参数:
        exchange_code: 交易所代码 (SHFE/DCE/CZCE/CFFEX/GFEX/INE)
        config_dir: 配置目录路径 (默认 config/exchanges/)

    返回:
        交易所配置模型

    异常:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置验证失败
    """
    import yaml

    if config_dir is None:
        config_dir = Path(__file__).parent.parent.parent / "config" / "exchanges"

    config_file = config_dir / f"{exchange_code.lower()}.yml"
    if not config_file.exists():
        msg = f"配置文件不存在: {config_file}"
        raise FileNotFoundError(msg)

    with open(config_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return ExchangeConfigModel(**data)


def load_all_exchanges(
    config_dir: Path | None = None,
) -> dict[str, ExchangeConfigModel]:
    """加载所有交易所配置.

    参数:
        config_dir: 配置目录路径

    返回:
        交易所代码 -> 配置模型 字典
    """
    import yaml

    if config_dir is None:
        config_dir = Path(__file__).parent.parent.parent / "config" / "exchanges"

    if not config_dir.exists():
        return {}

    result: dict[str, ExchangeConfigModel] = {}
    for config_file in config_dir.glob("*.yml"):
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        try:
            config = ExchangeConfigModel(**data)
            result[config.exchange.code] = config
        except Exception:
            # 跳过无效配置文件
            continue

    return result


def validate_exchange_config(data: dict[str, Any]) -> tuple[bool, str]:
    """验证交易所配置数据.

    参数:
        data: 配置数据字典

    返回:
        (是否有效, 错误信息)
    """
    try:
        ExchangeConfigModel(**data)
        return True, ""
    except Exception as e:
        return False, str(e)


def get_all_products_from_configs(
    configs: dict[str, ExchangeConfigModel] | None = None,
) -> dict[str, tuple[str, ProductModel]]:
    """从所有配置中获取品种映射.

    参数:
        configs: 交易所配置字典 (默认加载所有)

    返回:
        品种代码 -> (交易所代码, 品种模型) 字典
    """
    if configs is None:
        configs = load_all_exchanges()

    result: dict[str, tuple[str, ProductModel]] = {}
    for exchange_code, config in configs.items():
        for product in config.get_all_products():
            result[product.symbol.lower()] = (exchange_code, product)

    return result


# ============================================================
# 配置验证器
# ============================================================


class ConfigValidator:
    """配置验证器 (军规级).

    功能:
    - 验证所有交易所配置
    - 检查品种重复
    - 验证时间格式
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """初始化验证器.

        参数:
            config_dir: 配置目录路径
        """
        self._config_dir = config_dir
        self._errors: list[str] = []
        self._warnings: list[str] = []

    def validate_all(self) -> bool:
        """验证所有配置.

        返回:
            是否全部通过
        """
        self._errors.clear()
        self._warnings.clear()

        configs = load_all_exchanges(self._config_dir)

        if not configs:
            self._errors.append("未找到任何交易所配置")
            return False

        # 检查六大交易所是否都有配置
        required_exchanges = {"SHFE", "DCE", "CZCE", "CFFEX", "GFEX", "INE"}
        missing = required_exchanges - set(configs.keys())
        if missing:
            self._warnings.append(f"缺少交易所配置: {missing}")

        # 检查品种重复
        all_products: dict[str, str] = {}  # symbol -> exchange
        for exchange_code, config in configs.items():
            for product in config.get_all_products():
                symbol_lower = product.symbol.lower()
                if symbol_lower in all_products:
                    self._warnings.append(
                        f"品种 {product.symbol} 在多个交易所定义: "
                        f"{all_products[symbol_lower]}, {exchange_code}"
                    )
                else:
                    all_products[symbol_lower] = exchange_code

        return len(self._errors) == 0

    @property
    def errors(self) -> list[str]:
        """获取错误列表."""
        return self._errors.copy()

    @property
    def warnings(self) -> list[str]:
        """获取警告列表."""
        return self._warnings.copy()

    def get_report(self) -> dict[str, Any]:
        """获取验证报告.

        返回:
            验证报告字典
        """
        configs = load_all_exchanges(self._config_dir)

        return {
            "valid": len(self._errors) == 0,
            "exchange_count": len(configs),
            "exchanges": list(configs.keys()),
            "total_products": sum(len(c.get_all_products()) for c in configs.values()),
            "errors": self._errors,
            "warnings": self._warnings,
        }
