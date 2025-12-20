"""中国期货市场手续费计算器模块 (军规级 v4.0).

本模块提供中国期货市场的精确手续费计算功能，支持：
- 按手收费（固定金额/手）
- 按金额收费（成交金额×费率）
- 混合收费模式
- 平今手续费（CFFEX平今费率极高）
- 平昨手续费
- 交易所差异化费率

军规覆盖:
- M5: 成本先行 - 精确计算交易成本
- M14: 平今平昨分离 - 区分平今/平昨手续费

场景覆盖:
- CHINA.FEE.BY_VOLUME_CALC: 按手收费计算
- CHINA.FEE.BY_VALUE_CALC: 按金额收费计算
- CHINA.FEE.CLOSE_TODAY_CALC: 平今手续费计算

示例:
    >>> from src.cost.china_fee_calculator import ChinaFeeCalculator
    >>> calc = ChinaFeeCalculator()
    >>> # 螺纹钢按手收费
    >>> fee = calc.calculate("rb2501", 3500, 10, "open")
    >>> print(fee)
    FeeResult(fee=35.0, fee_type=FeeType.FIXED, ...)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from src.market.exchange_config import Exchange, get_exchange_for_product


class FeeType(Enum):
    """手续费类型枚举.

    属性:
        FIXED: 按手收费（固定金额/手）
        RATIO: 按金额收费（成交金额×费率）
        MIXED: 混合收费（按手+按金额）
    """

    FIXED = "按手"
    RATIO = "按金额"
    MIXED = "混合"


class TradeDirection(Enum):
    """交易方向枚举.

    属性:
        OPEN: 开仓
        CLOSE: 平仓（平昨）
        CLOSE_TODAY: 平今
    """

    OPEN = "开仓"
    CLOSE = "平仓"
    CLOSE_TODAY = "平今"


@dataclass(frozen=True)
class FeeConfig:
    """手续费配置.

    属性:
        fee_type: 手续费类型
        open_ratio: 开仓费率（按金额）
        close_ratio: 平仓费率（按金额）
        close_today_ratio: 平今费率（按金额）
        open_fixed: 开仓固定费（按手）
        close_fixed: 平仓固定费（按手）
        close_today_fixed: 平今固定费（按手）
        multiplier: 合约乘数
    """

    fee_type: FeeType
    open_ratio: float = 0.0
    close_ratio: float = 0.0
    close_today_ratio: float = 0.0
    open_fixed: float = 0.0
    close_fixed: float = 0.0
    close_today_fixed: float = 0.0
    multiplier: int = 1


@dataclass
class FeeResult:
    """手续费计算结果.

    属性:
        fee: 手续费金额
        fee_type: 手续费类型
        direction: 交易方向
        volume: 交易手数
        price: 成交价格
        value: 成交金额
        product: 品种代码
        exchange: 交易所
    """

    fee: float
    fee_type: FeeType
    direction: TradeDirection
    volume: int
    price: float
    value: float
    product: str
    exchange: Exchange | None = None


# ============================================================================
# 中国期货市场手续费配置（2025年主要品种）
# 注意：实际费率可能随时调整，需定期更新
# ============================================================================

# 上期所品种费率配置
SHFE_FEE_CONFIGS: dict[str, FeeConfig] = {
    # 有色金属 - 按金额收费
    "cu": FeeConfig(FeeType.RATIO, 0.00005, 0.00005, 0.00005, multiplier=5),
    "al": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=5
    ),
    "zn": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=5
    ),
    "pb": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=5
    ),
    "ni": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=1
    ),
    "sn": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=1
    ),
    # 贵金属 - 按金额收费
    "au": FeeConfig(FeeType.RATIO, 0.00002, 0.00002, 0.00002, multiplier=1000),
    "ag": FeeConfig(FeeType.RATIO, 0.00005, 0.00005, 0.00005, multiplier=15),
    # 黑色系 - 按手收费
    "rb": FeeConfig(FeeType.RATIO, 0.0001, 0.0001, 0.0001, multiplier=10),
    "hc": FeeConfig(FeeType.RATIO, 0.0001, 0.0001, 0.0001, multiplier=10),
    "ss": FeeConfig(
        FeeType.FIXED, open_fixed=2.0, close_fixed=2.0, close_today_fixed=0.0, multiplier=5
    ),
    # 能源化工
    "bu": FeeConfig(FeeType.RATIO, 0.0001, 0.0001, 0.0001, multiplier=10),
    "ru": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=10
    ),
    "sp": FeeConfig(
        FeeType.FIXED, open_fixed=0.5, close_fixed=0.5, close_today_fixed=0.0, multiplier=10
    ),
    "fu": FeeConfig(FeeType.RATIO, 0.00005, 0.00005, 0.00005, multiplier=10),
}

# 大商所品种费率配置
DCE_FEE_CONFIGS: dict[str, FeeConfig] = {
    # 农产品
    "c": FeeConfig(
        FeeType.FIXED, open_fixed=1.2, close_fixed=1.2, close_today_fixed=1.2, multiplier=10
    ),
    "cs": FeeConfig(
        FeeType.FIXED, open_fixed=1.5, close_fixed=1.5, close_today_fixed=1.5, multiplier=10
    ),
    "a": FeeConfig(
        FeeType.FIXED, open_fixed=2.0, close_fixed=2.0, close_today_fixed=2.0, multiplier=10
    ),
    "b": FeeConfig(
        FeeType.FIXED, open_fixed=1.0, close_fixed=1.0, close_today_fixed=1.0, multiplier=10
    ),
    "m": FeeConfig(
        FeeType.FIXED, open_fixed=1.5, close_fixed=1.5, close_today_fixed=1.5, multiplier=10
    ),
    "y": FeeConfig(
        FeeType.FIXED, open_fixed=2.5, close_fixed=2.5, close_today_fixed=2.5, multiplier=10
    ),
    "p": FeeConfig(
        FeeType.FIXED, open_fixed=2.5, close_fixed=2.5, close_today_fixed=2.5, multiplier=10
    ),
    "jd": FeeConfig(FeeType.RATIO, 0.00015, 0.00015, 0.00015, multiplier=10),
    "lh": FeeConfig(FeeType.RATIO, 0.0002, 0.0002, 0.0002, multiplier=16),
    # 黑色系
    "i": FeeConfig(FeeType.RATIO, 0.0001, 0.0001, 0.0001, multiplier=100),
    "j": FeeConfig(FeeType.RATIO, 0.0001, 0.0001, 0.00014, multiplier=100),
    "jm": FeeConfig(FeeType.RATIO, 0.0001, 0.0001, 0.00014, multiplier=60),
    # 化工
    "l": FeeConfig(
        FeeType.FIXED, open_fixed=1.0, close_fixed=1.0, close_today_fixed=1.0, multiplier=5
    ),
    "v": FeeConfig(
        FeeType.FIXED, open_fixed=1.0, close_fixed=1.0, close_today_fixed=1.0, multiplier=5
    ),
    "pp": FeeConfig(
        FeeType.FIXED, open_fixed=1.0, close_fixed=1.0, close_today_fixed=1.0, multiplier=5
    ),
    "eg": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=10
    ),
    "eb": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=5
    ),
    "pg": FeeConfig(
        FeeType.FIXED, open_fixed=6.0, close_fixed=6.0, close_today_fixed=6.0, multiplier=20
    ),
}

# 郑商所品种费率配置
CZCE_FEE_CONFIGS: dict[str, FeeConfig] = {
    # 农产品
    "CF": FeeConfig(
        FeeType.FIXED, open_fixed=4.3, close_fixed=4.3, close_today_fixed=0.0, multiplier=5
    ),
    "SR": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=10
    ),
    "OI": FeeConfig(
        FeeType.FIXED, open_fixed=2.0, close_fixed=2.0, close_today_fixed=0.0, multiplier=10
    ),
    "RM": FeeConfig(
        FeeType.FIXED, open_fixed=1.5, close_fixed=1.5, close_today_fixed=1.5, multiplier=10
    ),
    "AP": FeeConfig(
        FeeType.FIXED, open_fixed=5.0, close_fixed=5.0, close_today_fixed=20.0, multiplier=10
    ),
    "CJ": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=5
    ),
    "PK": FeeConfig(
        FeeType.FIXED, open_fixed=4.0, close_fixed=4.0, close_today_fixed=4.0, multiplier=5
    ),
    # 化工
    "MA": FeeConfig(
        FeeType.FIXED, open_fixed=2.0, close_fixed=2.0, close_today_fixed=6.0, multiplier=10
    ),
    "TA": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=5
    ),
    "SA": FeeConfig(
        FeeType.FIXED, open_fixed=3.5, close_fixed=3.5, close_today_fixed=3.5, multiplier=20
    ),
    "UR": FeeConfig(
        FeeType.FIXED, open_fixed=5.0, close_fixed=5.0, close_today_fixed=5.0, multiplier=20
    ),
    "FG": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=6.0, multiplier=20
    ),
    # 其他
    "SM": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=5
    ),
    "SF": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=5
    ),
}

# 中金所品种费率配置（平今费率极高！）
CFFEX_FEE_CONFIGS: dict[str, FeeConfig] = {
    # 股指期货 - 按金额收费，平今费率是开仓的15倍！
    "IF": FeeConfig(FeeType.RATIO, 0.000023, 0.000023, 0.000345, multiplier=300),
    "IH": FeeConfig(FeeType.RATIO, 0.000023, 0.000023, 0.000345, multiplier=300),
    "IC": FeeConfig(FeeType.RATIO, 0.000023, 0.000023, 0.000345, multiplier=200),
    "IM": FeeConfig(FeeType.RATIO, 0.000023, 0.000023, 0.000345, multiplier=200),
    # 国债期货 - 按手收费
    "T": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=10000
    ),
    "TF": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=10000
    ),
    "TS": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=20000
    ),
    "TL": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=10000
    ),
}

# 广期所品种费率配置
GFEX_FEE_CONFIGS: dict[str, FeeConfig] = {
    "lc": FeeConfig(FeeType.RATIO, 0.00004, 0.00004, 0.00008, multiplier=1),
    "si": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=3.0, multiplier=5
    ),
}

# 能源中心品种费率配置
INE_FEE_CONFIGS: dict[str, FeeConfig] = {
    "sc": FeeConfig(
        FeeType.FIXED, open_fixed=20.0, close_fixed=20.0, close_today_fixed=0.0, multiplier=1000
    ),
    "lu": FeeConfig(
        FeeType.FIXED, open_fixed=1.0, close_fixed=1.0, close_today_fixed=0.0, multiplier=10
    ),
    "bc": FeeConfig(FeeType.RATIO, 0.00005, 0.00005, 0.00005, multiplier=5),
    "nr": FeeConfig(
        FeeType.FIXED, open_fixed=3.0, close_fixed=3.0, close_today_fixed=0.0, multiplier=10
    ),
}


# 合并所有费率配置
ALL_FEE_CONFIGS: dict[str, FeeConfig] = {
    **SHFE_FEE_CONFIGS,
    **DCE_FEE_CONFIGS,
    **CZCE_FEE_CONFIGS,
    **CFFEX_FEE_CONFIGS,
    **GFEX_FEE_CONFIGS,
    **INE_FEE_CONFIGS,
}


@dataclass
class ChinaFeeCalculator:
    """中国期货市场手续费计算器.

    提供精确的手续费计算功能。

    属性:
        configs: 费率配置字典
        default_ratio: 默认按金额费率
        default_fixed: 默认按手费用

    示例:
        >>> calc = ChinaFeeCalculator()
        >>> result = calc.calculate("rb2501", 3500, 10, "open")
        >>> print(f"手续费: {result.fee:.2f}")
    """

    configs: dict[str, FeeConfig] = field(default_factory=lambda: ALL_FEE_CONFIGS.copy())
    default_ratio: float = 0.0001  # 默认万分之一
    default_fixed: float = 10.0  # 默认10元/手

    # 默认合约乘数
    DEFAULT_MULTIPLIER: ClassVar[int] = 10

    def get_config(self, product: str) -> FeeConfig | None:
        """获取品种的费率配置.

        参数:
            product: 品种代码（如 "rb", "IF"）

        返回:
            费率配置，未找到返回None
        """
        # 先尝试原始代码
        if product in self.configs:
            return self.configs[product]
        # 尝试小写
        if product.lower() in self.configs:
            return self.configs[product.lower()]
        # 尝试大写
        if product.upper() in self.configs:
            return self.configs[product.upper()]
        return None

    def calculate(
        self,
        instrument: str,
        price: float,
        volume: int,
        direction: str | TradeDirection,
        multiplier: int | None = None,
    ) -> FeeResult:
        """计算手续费.

        参数:
            instrument: 合约代码（如 "rb2501", "IF2501"）
            price: 成交价格
            volume: 成交手数
            direction: 交易方向（"open"/"close"/"close_today" 或 TradeDirection枚举）
            multiplier: 合约乘数（可选，默认从配置获取）

        返回:
            手续费计算结果

        示例:
            >>> calc.calculate("rb2501", 3500, 10, "open")
            >>> calc.calculate("IF2501", 4000, 2, TradeDirection.CLOSE_TODAY)
        """
        # 解析品种代码
        product = self._extract_product(instrument)

        # 转换方向
        if isinstance(direction, str):
            direction = self._parse_direction(direction)

        # 获取费率配置
        config = self.get_config(product)

        # 获取合约乘数
        if multiplier is None:
            multiplier = config.multiplier if config else self.DEFAULT_MULTIPLIER

        # 计算成交金额
        value = price * volume * multiplier

        # 计算手续费
        if config is None:
            # 使用默认费率
            fee = self._calc_default(price, volume, multiplier, direction)
            fee_type = FeeType.RATIO
        elif config.fee_type == FeeType.RATIO:
            fee = self._calc_by_ratio(config, value, direction)
            fee_type = FeeType.RATIO
        elif config.fee_type == FeeType.FIXED:
            fee = self._calc_by_fixed(config, volume, direction)
            fee_type = FeeType.FIXED
        else:  # MIXED
            fee = self._calc_by_ratio(config, value, direction) + self._calc_by_fixed(
                config, volume, direction
            )
            fee_type = FeeType.MIXED

        # 获取交易所
        exchange = get_exchange_for_product(product)

        return FeeResult(
            fee=round(fee, 2),
            fee_type=fee_type,
            direction=direction,
            volume=volume,
            price=price,
            value=value,
            product=product,
            exchange=exchange,
        )

    def _extract_product(self, instrument: str) -> str:
        """从合约代码提取品种代码.

        参数:
            instrument: 合约代码（如 "rb2501", "IF2501"）

        返回:
            品种代码（如 "rb", "IF"）
        """
        # 移除数字后缀
        result = ""
        for char in instrument:
            if char.isalpha():
                result += char
            else:
                break
        return result if result else instrument

    def _parse_direction(self, direction: str) -> TradeDirection:
        """解析交易方向字符串.

        参数:
            direction: 交易方向字符串

        返回:
            TradeDirection枚举
        """
        direction_lower = direction.lower()
        if direction_lower in ("open", "开仓", "buy", "sell"):
            return TradeDirection.OPEN
        if direction_lower in ("close_today", "平今", "closetoday"):
            return TradeDirection.CLOSE_TODAY
        return TradeDirection.CLOSE

    def _calc_default(
        self,
        price: float,
        volume: int,
        multiplier: int,
        direction: TradeDirection,
    ) -> float:
        """使用默认费率计算手续费.

        参数:
            price: 成交价格
            volume: 成交手数
            multiplier: 合约乘数
            direction: 交易方向

        返回:
            手续费金额
        """
        value = price * volume * multiplier
        ratio = self.default_ratio
        # 平今加收（默认3倍）
        if direction == TradeDirection.CLOSE_TODAY:
            ratio *= 3
        return value * ratio

    def _calc_by_ratio(
        self,
        config: FeeConfig,
        value: float,
        direction: TradeDirection,
    ) -> float:
        """按金额计算手续费.

        参数:
            config: 费率配置
            value: 成交金额
            direction: 交易方向

        返回:
            手续费金额
        """
        if direction == TradeDirection.OPEN:
            return value * config.open_ratio
        if direction == TradeDirection.CLOSE_TODAY:
            return value * config.close_today_ratio
        return value * config.close_ratio

    def _calc_by_fixed(
        self,
        config: FeeConfig,
        volume: int,
        direction: TradeDirection,
    ) -> float:
        """按手计算手续费.

        参数:
            config: 费率配置
            volume: 成交手数
            direction: 交易方向

        返回:
            手续费金额
        """
        if direction == TradeDirection.OPEN:
            return volume * config.open_fixed
        if direction == TradeDirection.CLOSE_TODAY:
            return volume * config.close_today_fixed
        return volume * config.close_fixed

    def estimate_round_trip(
        self,
        instrument: str,
        price: float,
        volume: int,
        multiplier: int | None = None,
        is_intraday: bool = True,
    ) -> float:
        """估算往返交易手续费（开仓+平仓）.

        参数:
            instrument: 合约代码
            price: 成交价格
            volume: 成交手数
            multiplier: 合约乘数
            is_intraday: 是否为日内交易（True=平今，False=平昨）

        返回:
            往返手续费总额
        """
        open_result = self.calculate(instrument, price, volume, "open", multiplier)
        close_direction = "close_today" if is_intraday else "close"
        close_result = self.calculate(instrument, price, volume, close_direction, multiplier)
        return open_result.fee + close_result.fee

    def get_fee_rate_info(self, product: str) -> dict[str, object]:
        """获取品种的费率信息摘要.

        参数:
            product: 品种代码

        返回:
            费率信息字典
        """
        config = self.get_config(product)
        if config is None:
            return {
                "product": product,
                "fee_type": "默认",
                "open_rate": self.default_ratio,
                "close_rate": self.default_ratio,
                "close_today_rate": self.default_ratio * 3,
                "multiplier": self.DEFAULT_MULTIPLIER,
            }

        return {
            "product": product,
            "fee_type": config.fee_type.value,
            "open_rate": config.open_ratio if config.open_ratio else config.open_fixed,
            "close_rate": (config.close_ratio if config.close_ratio else config.close_fixed),
            "close_today_rate": (
                config.close_today_ratio if config.close_today_ratio else config.close_today_fixed
            ),
            "multiplier": config.multiplier,
        }


# ============================================================================
# 便捷函数
# ============================================================================
_default_calculator: ChinaFeeCalculator | None = None


def get_default_calculator() -> ChinaFeeCalculator:
    """获取默认手续费计算器实例.

    返回:
        默认计算器实例
    """
    global _default_calculator
    if _default_calculator is None:
        _default_calculator = ChinaFeeCalculator()
    return _default_calculator


def calculate_fee(
    instrument: str,
    price: float,
    volume: int,
    direction: str = "open",
    multiplier: int | None = None,
) -> float:
    """计算手续费（便捷函数）.

    参数:
        instrument: 合约代码
        price: 成交价格
        volume: 成交手数
        direction: 交易方向
        multiplier: 合约乘数

    返回:
        手续费金额
    """
    result = get_default_calculator().calculate(instrument, price, volume, direction, multiplier)
    return result.fee


def estimate_cost(
    instrument: str,
    price: float,
    volume: int,
    is_intraday: bool = True,
) -> float:
    """估算往返交易成本（便捷函数）.

    参数:
        instrument: 合约代码
        price: 成交价格
        volume: 成交手数
        is_intraday: 是否为日内交易

    返回:
        往返手续费总额
    """
    return get_default_calculator().estimate_round_trip(
        instrument, price, volume, is_intraday=is_intraday
    )
