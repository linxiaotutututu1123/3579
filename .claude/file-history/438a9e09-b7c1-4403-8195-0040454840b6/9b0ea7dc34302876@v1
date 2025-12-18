"""涨跌停保护模块 (军规级 v4.0).

本模块提供中国期货市场的涨跌停价格保护功能，包括：
- 涨跌停价格计算
- 订单价格检查
- 涨跌停状态判断

军规覆盖:
- M13: 涨跌停感知 - 订单价格必须检查涨跌停板

场景覆盖:
- CHINA.LIMIT.PRICE_CHECK: 涨跌停价格检查
- CHINA.LIMIT.ORDER_REJECT: 超限订单拒绝

示例:
    >>> from src.execution.protection.limit_price import LimitPriceGuard
    >>> guard = LimitPriceGuard()
    >>> result = guard.check_order_price("rb2501", 3600, 3500)
    >>> if not result.is_valid:
    ...     print(f"订单拒绝: {result.reason}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from src.market.exchange_config import Exchange, get_exchange_for_product


class LimitStatus(Enum):
    """涨跌停状态枚举.

    属性:
        NORMAL: 正常交易
        NEAR_UP_LIMIT: 接近涨停
        NEAR_DOWN_LIMIT: 接近跌停
        AT_UP_LIMIT: 涨停
        AT_DOWN_LIMIT: 跌停
        BEYOND_UP_LIMIT: 超过涨停价
        BEYOND_DOWN_LIMIT: 低于跌停价
    """

    NORMAL = "正常交易"
    NEAR_UP_LIMIT = "接近涨停"
    NEAR_DOWN_LIMIT = "接近跌停"
    AT_UP_LIMIT = "涨停"
    AT_DOWN_LIMIT = "跌停"
    BEYOND_UP_LIMIT = "超过涨停价"
    BEYOND_DOWN_LIMIT = "低于跌停价"


@dataclass(frozen=True)
class LimitPriceConfig:
    """涨跌停幅度配置.

    属性:
        product: 品种代码
        limit_pct: 涨跌停幅度（如0.10表示10%）
        exchange: 交易所
        description: 说明
    """

    product: str
    limit_pct: float
    exchange: Exchange | None = None
    description: str = ""


@dataclass
class PriceCheckResult:
    """价格检查结果.

    属性:
        is_valid: 价格是否有效
        status: 涨跌停状态
        reason: 无效原因
        order_price: 订单价格
        settle_price: 结算价（昨收）
        up_limit: 涨停价
        down_limit: 跌停价
        pct_from_up: 距涨停百分比
        pct_from_down: 距跌停百分比
    """

    is_valid: bool
    status: LimitStatus
    reason: str = ""
    order_price: float = 0.0
    settle_price: float = 0.0
    up_limit: float = 0.0
    down_limit: float = 0.0
    pct_from_up: float = 0.0
    pct_from_down: float = 0.0


# ============================================================================
# 涨跌停幅度配置（2025年）
# 注意：涨跌停幅度可能随时调整，需定期更新
# ============================================================================

# 默认涨跌停幅度配置
DEFAULT_LIMIT_CONFIGS: dict[str, LimitPriceConfig] = {
    # SHFE有色金属
    "cu": LimitPriceConfig("cu", 0.08, Exchange.SHFE, "铜"),
    "al": LimitPriceConfig("al", 0.08, Exchange.SHFE, "铝"),
    "zn": LimitPriceConfig("zn", 0.08, Exchange.SHFE, "锌"),
    "pb": LimitPriceConfig("pb", 0.08, Exchange.SHFE, "铅"),
    "ni": LimitPriceConfig("ni", 0.10, Exchange.SHFE, "镍"),
    "sn": LimitPriceConfig("sn", 0.08, Exchange.SHFE, "锡"),
    # SHFE贵金属
    "au": LimitPriceConfig("au", 0.09, Exchange.SHFE, "黄金"),
    "ag": LimitPriceConfig("ag", 0.10, Exchange.SHFE, "白银"),
    # SHFE黑色系
    "rb": LimitPriceConfig("rb", 0.08, Exchange.SHFE, "螺纹钢"),
    "hc": LimitPriceConfig("hc", 0.08, Exchange.SHFE, "热轧卷板"),
    "ss": LimitPriceConfig("ss", 0.08, Exchange.SHFE, "不锈钢"),
    # SHFE能化
    "bu": LimitPriceConfig("bu", 0.08, Exchange.SHFE, "沥青"),
    "ru": LimitPriceConfig("ru", 0.08, Exchange.SHFE, "天然橡胶"),
    "sp": LimitPriceConfig("sp", 0.06, Exchange.SHFE, "纸浆"),
    "fu": LimitPriceConfig("fu", 0.08, Exchange.SHFE, "燃料油"),
    # DCE农产品
    "c": LimitPriceConfig("c", 0.05, Exchange.DCE, "玉米"),
    "cs": LimitPriceConfig("cs", 0.05, Exchange.DCE, "玉米淀粉"),
    "a": LimitPriceConfig("a", 0.05, Exchange.DCE, "豆一"),
    "b": LimitPriceConfig("b", 0.05, Exchange.DCE, "豆二"),
    "m": LimitPriceConfig("m", 0.05, Exchange.DCE, "豆粕"),
    "y": LimitPriceConfig("y", 0.05, Exchange.DCE, "豆油"),
    "p": LimitPriceConfig("p", 0.06, Exchange.DCE, "棕榈油"),
    "jd": LimitPriceConfig("jd", 0.05, Exchange.DCE, "鸡蛋"),
    "lh": LimitPriceConfig("lh", 0.08, Exchange.DCE, "生猪"),
    # DCE黑色
    "i": LimitPriceConfig("i", 0.10, Exchange.DCE, "铁矿石"),
    "j": LimitPriceConfig("j", 0.08, Exchange.DCE, "焦炭"),
    "jm": LimitPriceConfig("jm", 0.08, Exchange.DCE, "焦煤"),
    # DCE化工
    "l": LimitPriceConfig("l", 0.05, Exchange.DCE, "塑料"),
    "v": LimitPriceConfig("v", 0.05, Exchange.DCE, "PVC"),
    "pp": LimitPriceConfig("pp", 0.05, Exchange.DCE, "聚丙烯"),
    "eg": LimitPriceConfig("eg", 0.06, Exchange.DCE, "乙二醇"),
    "eb": LimitPriceConfig("eb", 0.06, Exchange.DCE, "苯乙烯"),
    "pg": LimitPriceConfig("pg", 0.08, Exchange.DCE, "LPG"),
    # CZCE农产品
    "CF": LimitPriceConfig("CF", 0.05, Exchange.CZCE, "棉花"),
    "SR": LimitPriceConfig("SR", 0.05, Exchange.CZCE, "白糖"),
    "OI": LimitPriceConfig("OI", 0.05, Exchange.CZCE, "菜籽油"),
    "RM": LimitPriceConfig("RM", 0.05, Exchange.CZCE, "菜籽粕"),
    "AP": LimitPriceConfig("AP", 0.07, Exchange.CZCE, "苹果"),
    "CJ": LimitPriceConfig("CJ", 0.08, Exchange.CZCE, "红枣"),
    "PK": LimitPriceConfig("PK", 0.06, Exchange.CZCE, "花生"),
    # CZCE化工
    "MA": LimitPriceConfig("MA", 0.06, Exchange.CZCE, "甲醇"),
    "TA": LimitPriceConfig("TA", 0.05, Exchange.CZCE, "PTA"),
    "SA": LimitPriceConfig("SA", 0.07, Exchange.CZCE, "纯碱"),
    "UR": LimitPriceConfig("UR", 0.05, Exchange.CZCE, "尿素"),
    "FG": LimitPriceConfig("FG", 0.06, Exchange.CZCE, "玻璃"),
    "SM": LimitPriceConfig("SM", 0.07, Exchange.CZCE, "锰硅"),
    "SF": LimitPriceConfig("SF", 0.07, Exchange.CZCE, "硅铁"),
    # CFFEX股指期货
    "IF": LimitPriceConfig("IF", 0.10, Exchange.CFFEX, "沪深300股指期货"),
    "IH": LimitPriceConfig("IH", 0.10, Exchange.CFFEX, "上证50股指期货"),
    "IC": LimitPriceConfig("IC", 0.10, Exchange.CFFEX, "中证500股指期货"),
    "IM": LimitPriceConfig("IM", 0.10, Exchange.CFFEX, "中证1000股指期货"),
    # CFFEX国债期货
    "T": LimitPriceConfig("T", 0.02, Exchange.CFFEX, "10年期国债期货"),
    "TF": LimitPriceConfig("TF", 0.012, Exchange.CFFEX, "5年期国债期货"),
    "TS": LimitPriceConfig("TS", 0.005, Exchange.CFFEX, "2年期国债期货"),
    "TL": LimitPriceConfig("TL", 0.035, Exchange.CFFEX, "30年期国债期货"),
    # GFEX
    "lc": LimitPriceConfig("lc", 0.10, Exchange.GFEX, "碳酸锂"),
    "si": LimitPriceConfig("si", 0.08, Exchange.GFEX, "工业硅"),
    # INE
    "sc": LimitPriceConfig("sc", 0.10, Exchange.INE, "原油"),
    "lu": LimitPriceConfig("lu", 0.08, Exchange.INE, "低硫燃料油"),
    "bc": LimitPriceConfig("bc", 0.08, Exchange.INE, "国际铜"),
    "nr": LimitPriceConfig("nr", 0.08, Exchange.INE, "20号胶"),
}


@dataclass
class LimitPriceGuard:
    """涨跌停价格保护器.

    提供订单价格的涨跌停检查功能。

    属性:
        configs: 涨跌停幅度配置
        default_limit_pct: 默认涨跌停幅度
        near_limit_threshold: 接近涨跌停阈值（如0.02表示距涨跌停2%以内）
        allow_at_limit: 是否允许以涨跌停价格下单
        tick_size: 最小价格变动单位（用于价格取整）
    """

    configs: dict[str, LimitPriceConfig] = field(
        default_factory=lambda: DEFAULT_LIMIT_CONFIGS.copy()
    )
    default_limit_pct: float = 0.10  # 默认10%
    near_limit_threshold: float = 0.02  # 2%以内算接近涨跌停
    allow_at_limit: bool = True  # 允许以涨跌停价格下单
    tick_size: float = 1.0  # 默认1元

    # 类变量：安全阈值
    SAFETY_MARGIN: ClassVar[float] = 0.001  # 0.1%安全边际

    def get_limit_config(self, product: str) -> LimitPriceConfig | None:
        """获取品种的涨跌停配置.

        参数:
            product: 品种代码

        返回:
            涨跌停配置，未找到返回None
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

    def get_limit_pct(self, product: str) -> float:
        """获取品种的涨跌停幅度.

        参数:
            product: 品种代码

        返回:
            涨跌停幅度
        """
        config = self.get_limit_config(product)
        return config.limit_pct if config else self.default_limit_pct

    def calculate_limits(
        self,
        product: str,
        settle_price: float,
        tick_size: float | None = None,
    ) -> tuple[float, float]:
        """计算涨跌停价格.

        参数:
            product: 品种代码
            settle_price: 结算价（昨收）
            tick_size: 最小变动价位（可选）

        返回:
            (涨停价, 跌停价)
        """
        limit_pct = self.get_limit_pct(product)
        ts = tick_size if tick_size else self.tick_size

        # 计算原始涨跌停价
        up_limit_raw = settle_price * (1 + limit_pct)
        down_limit_raw = settle_price * (1 - limit_pct)

        # 按tick_size取整（涨停向下取整，跌停向上取整）
        up_limit = self._round_to_tick(up_limit_raw, ts, direction="down")
        down_limit = self._round_to_tick(down_limit_raw, ts, direction="up")

        return up_limit, down_limit

    def _round_to_tick(
        self,
        price: float,
        tick_size: float,
        direction: str = "nearest",
    ) -> float:
        """按最小变动价位取整.

        参数:
            price: 原始价格
            tick_size: 最小变动价位
            direction: 取整方向（"up", "down", "nearest"）

        返回:
            取整后价格
        """
        if direction == "up":
            import math
            return math.ceil(price / tick_size) * tick_size
        if direction == "down":
            import math
            return math.floor(price / tick_size) * tick_size
        return round(price / tick_size) * tick_size

    def check_order_price(
        self,
        instrument: str,
        order_price: float,
        settle_price: float,
        tick_size: float | None = None,
    ) -> PriceCheckResult:
        """检查订单价格是否在涨跌停范围内.

        参数:
            instrument: 合约代码（如 "rb2501"）
            order_price: 订单价格
            settle_price: 结算价（昨收）
            tick_size: 最小变动价位（可选）

        返回:
            价格检查结果
        """
        # 提取品种代码
        product = self._extract_product(instrument)

        # 计算涨跌停价
        up_limit, down_limit = self.calculate_limits(
            product, settle_price, tick_size
        )

        # 计算距离百分比
        pct_from_up = (up_limit - order_price) / settle_price if settle_price else 0
        pct_from_down = (order_price - down_limit) / settle_price if settle_price else 0

        # 判断状态
        status, is_valid, reason = self._determine_status(
            order_price, up_limit, down_limit, pct_from_up, pct_from_down
        )

        return PriceCheckResult(
            is_valid=is_valid,
            status=status,
            reason=reason,
            order_price=order_price,
            settle_price=settle_price,
            up_limit=up_limit,
            down_limit=down_limit,
            pct_from_up=pct_from_up,
            pct_from_down=pct_from_down,
        )

    def _determine_status(
        self,
        order_price: float,
        up_limit: float,
        down_limit: float,
        pct_from_up: float,
        pct_from_down: float,
    ) -> tuple[LimitStatus, bool, str]:
        """判断订单价格状态.

        返回:
            (状态, 是否有效, 原因)
        """
        # 超过涨停价
        if order_price > up_limit + self.SAFETY_MARGIN:
            return (
                LimitStatus.BEYOND_UP_LIMIT,
                False,
                f"订单价格{order_price:.2f}超过涨停价{up_limit:.2f}",
            )

        # 低于跌停价
        if order_price < down_limit - self.SAFETY_MARGIN:
            return (
                LimitStatus.BEYOND_DOWN_LIMIT,
                False,
                f"订单价格{order_price:.2f}低于跌停价{down_limit:.2f}",
            )

        # 涨停价
        if abs(order_price - up_limit) < self.SAFETY_MARGIN:
            if self.allow_at_limit:
                return LimitStatus.AT_UP_LIMIT, True, ""
            return (
                LimitStatus.AT_UP_LIMIT,
                False,
                f"订单价格{order_price:.2f}处于涨停价",
            )

        # 跌停价
        if abs(order_price - down_limit) < self.SAFETY_MARGIN:
            if self.allow_at_limit:
                return LimitStatus.AT_DOWN_LIMIT, True, ""
            return (
                LimitStatus.AT_DOWN_LIMIT,
                False,
                f"订单价格{order_price:.2f}处于跌停价",
            )

        # 接近涨停
        if pct_from_up < self.near_limit_threshold:
            return LimitStatus.NEAR_UP_LIMIT, True, ""

        # 接近跌停
        if pct_from_down < self.near_limit_threshold:
            return LimitStatus.NEAR_DOWN_LIMIT, True, ""

        # 正常
        return LimitStatus.NORMAL, True, ""

    def _extract_product(self, instrument: str) -> str:
        """从合约代码提取品种代码."""
        result = ""
        for char in instrument:
            if char.isalpha():
                result += char
            else:
                break
        return result if result else instrument

    def is_at_limit(
        self,
        product: str,
        current_price: float,
        settle_price: float,
    ) -> tuple[bool, LimitStatus]:
        """判断当前价格是否处于涨跌停.

        参数:
            product: 品种代码
            current_price: 当前价格
            settle_price: 结算价

        返回:
            (是否涨跌停, 涨跌停状态)
        """
        up_limit, down_limit = self.calculate_limits(product, settle_price)

        if abs(current_price - up_limit) < self.SAFETY_MARGIN:
            return True, LimitStatus.AT_UP_LIMIT
        if abs(current_price - down_limit) < self.SAFETY_MARGIN:
            return True, LimitStatus.AT_DOWN_LIMIT

        return False, LimitStatus.NORMAL


# ============================================================================
# 便捷函数
# ============================================================================
_default_guard: LimitPriceGuard | None = None


def get_default_guard() -> LimitPriceGuard:
    """获取默认涨跌停保护器.

    返回:
        默认保护器实例
    """
    global _default_guard
    if _default_guard is None:
        _default_guard = LimitPriceGuard()
    return _default_guard


def check_order_price(
    instrument: str,
    order_price: float,
    settle_price: float,
) -> PriceCheckResult:
    """检查订单价格（便捷函数）.

    参数:
        instrument: 合约代码
        order_price: 订单价格
        settle_price: 结算价

    返回:
        价格检查结果
    """
    return get_default_guard().check_order_price(
        instrument, order_price, settle_price
    )


def calculate_limits(
    product: str,
    settle_price: float,
) -> tuple[float, float]:
    """计算涨跌停价格（便捷函数）.

    参数:
        product: 品种代码
        settle_price: 结算价

    返回:
        (涨停价, 跌停价)
    """
    return get_default_guard().calculate_limits(product, settle_price)
