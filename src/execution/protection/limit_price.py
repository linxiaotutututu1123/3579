"""
涨跌停保护模块 - LimitPriceGuard (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §18 涨跌停板规则
V4 Scenarios: CHINA.LIMIT.PRICE_CHECK, CHINA.LIMIT.ORDER_REJECT

军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板

功能特性:
- 根据昨结算价和涨跌停幅度计算涨跌停价格
- 检查订单价格是否在涨跌停范围内
- 支持不同品种的涨跌停幅度配置
- 提供涨跌停价格查询功能
- 检测当前价格是否处于涨跌停状态

涨跌停幅度参考 (2025年):
- 股指期货 (IF/IH/IC/IM): ±10%
- 国债期货 (T/TF/TS): ±2%
- 商品期货: 3%-8% (各品种不同)
- 贵金属 (au/ag): 6%-8%
- 有色金属: 4%-7%
- 黑色系: 4%-8%
- 农产品: 4%-5%
- 化工品: 4%-6%

示例:
    >>> guard = LimitPriceGuard()
    >>> result = guard.check_order_price(
    ...     order_price=4500.0,
    ...     last_settle=4200.0,
    ...     limit_pct=0.05,  # 5%涨跌停
    ...     symbol="rb2501",
    ... )
    >>> if result.passed:
    ...     print("订单价格在涨跌停范围内")
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LimitPriceCheckResult(Enum):
    """涨跌停检查结果枚举."""

    PASS = "PASS"  # 通过检查
    ABOVE_LIMIT_UP = "ABOVE_LIMIT_UP"  # 超过涨停价
    BELOW_LIMIT_DOWN = "BELOW_LIMIT_DOWN"  # 低于跌停价
    INVALID_PRICE = "INVALID_PRICE"  # 无效价格
    INVALID_SETTLE = "INVALID_SETTLE"  # 无效结算价
    AT_LIMIT_UP = "AT_LIMIT_UP"  # 处于涨停价
    AT_LIMIT_DOWN = "AT_LIMIT_DOWN"  # 处于跌停价


class LimitStatus(Enum):
    """涨跌停状态枚举."""

    NORMAL = "NORMAL"  # 正常交易
    AT_LIMIT_UP = "AT_LIMIT_UP"  # 涨停
    AT_LIMIT_DOWN = "AT_LIMIT_DOWN"  # 跌停
    NEAR_LIMIT_UP = "NEAR_LIMIT_UP"  # 接近涨停 (<1%距离)
    NEAR_LIMIT_DOWN = "NEAR_LIMIT_DOWN"  # 接近跌停 (<1%距离)


@dataclass(frozen=True)
class LimitPriceConfig:
    """涨跌停配置.

    属性:
        default_limit_pct: 默认涨跌停幅度 (如 0.05 表示 5%)
        near_limit_threshold: 接近涨跌停的阈值 (如 0.01 表示 1%)
        allow_limit_price_order: 是否允许以涨跌停价下单
        tick_size: 最小变动价位 (用于价格修正)
    """

    default_limit_pct: float = 0.05
    near_limit_threshold: float = 0.01
    allow_limit_price_order: bool = True
    tick_size: float = 1.0


# 中国期货市场各品种涨跌停幅度配置
# 来源: 各交易所规则 (2025年)
PRODUCT_LIMIT_PCT: dict[str, float] = {
    # 股指期货 (CFFEX) - ±10%
    "if": 0.10,
    "ih": 0.10,
    "ic": 0.10,
    "im": 0.10,
    # 国债期货 (CFFEX) - ±2%
    "t": 0.02,
    "tf": 0.02,
    "ts": 0.02,
    # 贵金属 (SHFE) - 6%
    "au": 0.06,
    "ag": 0.06,
    # 有色金属 (SHFE) - 5%
    "cu": 0.05,
    "al": 0.05,
    "zn": 0.05,
    "pb": 0.05,
    "ni": 0.05,
    "sn": 0.05,
    "ao": 0.05,  # 氧化铝
    # 黑色系 (SHFE/DCE) - 4%
    "rb": 0.04,
    "hc": 0.04,
    "ss": 0.04,  # 不锈钢
    "i": 0.04,  # 铁矿石
    "j": 0.04,  # 焦炭
    "jm": 0.04,  # 焦煤
    # 能源化工 (SHFE/DCE/CZCE/INE) - 5%
    "bu": 0.05,
    "ru": 0.05,
    "sp": 0.05,
    "nr": 0.05,
    "sc": 0.05,  # 原油
    "lu": 0.05,  # 低硫燃料油
    "fu": 0.05,  # 燃料油
    "l": 0.05,  # 塑料
    "v": 0.05,  # PVC
    "pp": 0.05,
    "eg": 0.05,  # 乙二醇
    "eb": 0.05,  # 苯乙烯
    "pg": 0.05,  # LPG
    "ma": 0.05,  # 甲醇 (郑商所大写)
    "ta": 0.05,  # PTA
    "sa": 0.05,  # 纯碱
    "ur": 0.05,  # 尿素
    "pf": 0.05,  # 涤纶短纤
    # 农产品 (DCE/CZCE) - 4%
    "c": 0.04,  # 玉米
    "cs": 0.04,  # 淀粉
    "a": 0.04,  # 豆一
    "b": 0.04,  # 豆二
    "m": 0.04,  # 豆粕
    "y": 0.04,  # 豆油
    "p": 0.04,  # 棕榈油
    "jd": 0.04,  # 鸡蛋
    "lh": 0.04,  # 生猪
    "rr": 0.04,  # 粳米
    "wh": 0.04,  # 强麦
    "ri": 0.04,  # 早稻
    "pm": 0.04,  # 普麦
    "cf": 0.04,  # 棉花
    "sr": 0.04,  # 白糖
    "oi": 0.04,  # 菜油
    "rm": 0.04,  # 菜粕
    "rs": 0.04,  # 菜籽
    "ap": 0.04,  # 苹果
    "cj": 0.04,  # 红枣
    "pk": 0.04,  # 花生
    # 新能源 (GFEX) - 5%
    "lc": 0.05,  # 碳酸锂
    "si": 0.05,  # 工业硅
}


@dataclass
class LimitPrices:
    """涨跌停价格.

    属性:
        limit_up: 涨停价
        limit_down: 跌停价
        last_settle: 昨结算价
        limit_pct: 涨跌停幅度
        tick_size: 最小变动价位
    """

    limit_up: float
    limit_down: float
    last_settle: float
    limit_pct: float
    tick_size: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "limit_up": self.limit_up,
            "limit_down": self.limit_down,
            "last_settle": self.last_settle,
            "limit_pct": self.limit_pct,
            "tick_size": self.tick_size,
        }


@dataclass
class LimitPriceCheckOutput:
    """涨跌停检查输出.

    属性:
        result: 检查结果枚举
        symbol: 合约代码
        order_price: 订单价格
        limit_up: 涨停价
        limit_down: 跌停价
        last_settle: 昨结算价
        limit_pct: 涨跌停幅度
        message: 详细信息
    """

    result: LimitPriceCheckResult
    symbol: str = ""
    order_price: float = 0.0
    limit_up: float = 0.0
    limit_down: float = 0.0
    last_settle: float = 0.0
    limit_pct: float = 0.0
    message: str = ""

    @property
    def passed(self) -> bool:
        """是否通过检查."""
        return self.result == LimitPriceCheckResult.PASS

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "result": self.result.value,
            "symbol": self.symbol,
            "order_price": self.order_price,
            "limit_up": self.limit_up,
            "limit_down": self.limit_down,
            "last_settle": self.last_settle,
            "limit_pct": self.limit_pct,
            "message": self.message,
            "passed": self.passed,
        }


class LimitPriceGuard:
    """涨跌停保护门控 (军规级 v4.0).

    军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板

    V4 Scenarios:
    - CHINA.LIMIT.PRICE_CHECK: 涨跌停价格检查
    - CHINA.LIMIT.ORDER_REJECT: 超限订单拒绝

    功能:
    - 根据昨结算价计算涨跌停价格
    - 检查订单价格是否在涨跌停范围内
    - 检测当前价格的涨跌停状态
    - 支持自定义品种涨跌停幅度

    示例:
        >>> guard = LimitPriceGuard()
        >>> result = guard.check_order_price(
        ...     order_price=4500.0,
        ...     last_settle=4200.0,
        ...     limit_pct=0.05,
        ...     symbol="rb2501",
        ... )
    """

    def __init__(
        self,
        config: LimitPriceConfig | None = None,
        product_limits: dict[str, float] | None = None,
    ) -> None:
        """初始化涨跌停保护门控.

        参数:
            config: 涨跌停配置
            product_limits: 品种涨跌停幅度覆盖配置
        """
        self._config = config or LimitPriceConfig()
        self._product_limits = product_limits or PRODUCT_LIMIT_PCT.copy()
        self._check_count = 0
        self._reject_count = 0
        self._limit_hit_count = 0

    @property
    def config(self) -> LimitPriceConfig:
        """配置."""
        return self._config

    @property
    def check_count(self) -> int:
        """检查次数."""
        return self._check_count

    @property
    def reject_count(self) -> int:
        """拒绝次数 (超出涨跌停范围)."""
        return self._reject_count

    @property
    def limit_hit_count(self) -> int:
        """涨跌停触发次数."""
        return self._limit_hit_count

    def get_limit_pct(self, symbol: str) -> float:
        """获取品种的涨跌停幅度.

        参数:
            symbol: 合约代码 (如 "rb2501")

        返回:
            涨跌停幅度 (如 0.05 表示 5%)
        """
        product = self._extract_product(symbol)
        return self._product_limits.get(product, self._config.default_limit_pct)

    def get_limit_prices(
        self,
        last_settle: float,
        limit_pct: float | None = None,
        symbol: str = "",
        tick_size: float | None = None,
    ) -> LimitPrices:
        """计算涨跌停价格.

        参数:
            last_settle: 昨结算价
            limit_pct: 涨跌停幅度 (None则根据品种查找)
            symbol: 合约代码 (用于查找品种涨跌停幅度)
            tick_size: 最小变动价位 (用于价格修正)

        返回:
            涨跌停价格对象
        """
        # 确定涨跌停幅度
        if limit_pct is None:
            limit_pct = self.get_limit_pct(symbol) if symbol else self._config.default_limit_pct

        # 确定tick_size
        actual_tick_size = tick_size if tick_size is not None else self._config.tick_size

        # 计算原始涨跌停价格
        raw_limit_up = last_settle * (1 + limit_pct)
        raw_limit_down = last_settle * (1 - limit_pct)

        # 按tick_size修正 (涨停向下取整，跌停向上取整)
        if actual_tick_size > 0:
            limit_up = self._round_down(raw_limit_up, actual_tick_size)
            limit_down = self._round_up(raw_limit_down, actual_tick_size)
        else:
            limit_up = raw_limit_up
            limit_down = raw_limit_down

        return LimitPrices(
            limit_up=limit_up,
            limit_down=limit_down,
            last_settle=last_settle,
            limit_pct=limit_pct,
            tick_size=actual_tick_size,
        )

    def check_order_price(
        self,
        order_price: float,
        last_settle: float,
        limit_pct: float | None = None,
        symbol: str = "",
        tick_size: float | None = None,
    ) -> LimitPriceCheckOutput:
        """检查订单价格是否在涨跌停范围内.

        军规 M13: 涨跌停感知 - 订单价格必须检查涨跌停板
        V4 Scenario: CHINA.LIMIT.PRICE_CHECK

        参数:
            order_price: 订单价格
            last_settle: 昨结算价
            limit_pct: 涨跌停幅度 (None则根据品种查找)
            symbol: 合约代码
            tick_size: 最小变动价位

        返回:
            检查输出
        """
        self._check_count += 1

        # 验证订单价格
        if order_price <= 0:
            self._reject_count += 1
            return LimitPriceCheckOutput(
                result=LimitPriceCheckResult.INVALID_PRICE,
                symbol=symbol,
                order_price=order_price,
                message=f"无效订单价格: {order_price}",
            )

        # 验证昨结算价
        if last_settle <= 0:
            self._reject_count += 1
            return LimitPriceCheckOutput(
                result=LimitPriceCheckResult.INVALID_SETTLE,
                symbol=symbol,
                order_price=order_price,
                last_settle=last_settle,
                message=f"无效昨结算价: {last_settle}",
            )

        # 获取涨跌停价格
        limits = self.get_limit_prices(last_settle, limit_pct, symbol, tick_size)

        # 检查是否超过涨停价
        # V4 Scenario: CHINA.LIMIT.ORDER_REJECT
        if order_price > limits.limit_up:
            self._reject_count += 1
            return LimitPriceCheckOutput(
                result=LimitPriceCheckResult.ABOVE_LIMIT_UP,
                symbol=symbol,
                order_price=order_price,
                limit_up=limits.limit_up,
                limit_down=limits.limit_down,
                last_settle=last_settle,
                limit_pct=limits.limit_pct,
                message=f"订单价格 {order_price} 超过涨停价 {limits.limit_up}",
            )

        # 检查是否低于跌停价
        # V4 Scenario: CHINA.LIMIT.ORDER_REJECT
        if order_price < limits.limit_down:
            self._reject_count += 1
            return LimitPriceCheckOutput(
                result=LimitPriceCheckResult.BELOW_LIMIT_DOWN,
                symbol=symbol,
                order_price=order_price,
                limit_up=limits.limit_up,
                limit_down=limits.limit_down,
                last_settle=last_settle,
                limit_pct=limits.limit_pct,
                message=f"订单价格 {order_price} 低于跌停价 {limits.limit_down}",
            )

        # 检查是否刚好等于涨停价
        if abs(order_price - limits.limit_up) < 0.0001:
            self._limit_hit_count += 1
            if not self._config.allow_limit_price_order:
                self._reject_count += 1
                return LimitPriceCheckOutput(
                    result=LimitPriceCheckResult.AT_LIMIT_UP,
                    symbol=symbol,
                    order_price=order_price,
                    limit_up=limits.limit_up,
                    limit_down=limits.limit_down,
                    last_settle=last_settle,
                    limit_pct=limits.limit_pct,
                    message=f"订单价格 {order_price} 等于涨停价, 不允许涨停价下单",
                )

        # 检查是否刚好等于跌停价
        if abs(order_price - limits.limit_down) < 0.0001:
            self._limit_hit_count += 1
            if not self._config.allow_limit_price_order:
                self._reject_count += 1
                return LimitPriceCheckOutput(
                    result=LimitPriceCheckResult.AT_LIMIT_DOWN,
                    symbol=symbol,
                    order_price=order_price,
                    limit_up=limits.limit_up,
                    limit_down=limits.limit_down,
                    last_settle=last_settle,
                    limit_pct=limits.limit_pct,
                    message=f"订单价格 {order_price} 等于跌停价, 不允许跌停价下单",
                )

        # 通过检查
        return LimitPriceCheckOutput(
            result=LimitPriceCheckResult.PASS,
            symbol=symbol,
            order_price=order_price,
            limit_up=limits.limit_up,
            limit_down=limits.limit_down,
            last_settle=last_settle,
            limit_pct=limits.limit_pct,
            message="涨跌停检查通过",
        )

    def get_limit_status(
        self,
        current_price: float,
        last_settle: float,
        limit_pct: float | None = None,
        symbol: str = "",
        tick_size: float | None = None,
    ) -> LimitStatus:
        """获取当前价格的涨跌停状态.

        参数:
            current_price: 当前价格
            last_settle: 昨结算价
            limit_pct: 涨跌停幅度
            symbol: 合约代码
            tick_size: 最小变动价位

        返回:
            涨跌停状态枚举
        """
        if current_price <= 0 or last_settle <= 0:
            return LimitStatus.NORMAL

        limits = self.get_limit_prices(last_settle, limit_pct, symbol, tick_size)

        # 涨停
        if abs(current_price - limits.limit_up) < 0.0001:
            return LimitStatus.AT_LIMIT_UP

        # 跌停
        if abs(current_price - limits.limit_down) < 0.0001:
            return LimitStatus.AT_LIMIT_DOWN

        # 接近涨停 (距离涨停价 < threshold)
        distance_to_up = (limits.limit_up - current_price) / last_settle
        if 0 < distance_to_up < self._config.near_limit_threshold:
            return LimitStatus.NEAR_LIMIT_UP

        # 接近跌停 (距离跌停价 < threshold)
        distance_to_down = (current_price - limits.limit_down) / last_settle
        if 0 < distance_to_down < self._config.near_limit_threshold:
            return LimitStatus.NEAR_LIMIT_DOWN

        return LimitStatus.NORMAL

    def is_at_limit(
        self,
        current_price: float,
        last_settle: float,
        limit_pct: float | None = None,
        symbol: str = "",
    ) -> bool:
        """检查当前价格是否处于涨跌停.

        参数:
            current_price: 当前价格
            last_settle: 昨结算价
            limit_pct: 涨跌停幅度
            symbol: 合约代码

        返回:
            是否处于涨跌停状态
        """
        status = self.get_limit_status(current_price, last_settle, limit_pct, symbol)
        return status in (LimitStatus.AT_LIMIT_UP, LimitStatus.AT_LIMIT_DOWN)

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "check_count": self._check_count,
            "reject_count": self._reject_count,
            "limit_hit_count": self._limit_hit_count,
            "pass_rate": (
                (self._check_count - self._reject_count) / self._check_count
                if self._check_count > 0
                else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """重置统计信息."""
        self._check_count = 0
        self._reject_count = 0
        self._limit_hit_count = 0

    def _extract_product(self, symbol: str) -> str:
        """从合约代码提取品种代码.

        参数:
            symbol: 合约代码 (如 "rb2501", "IF2501")

        返回:
            品种代码 (如 "rb", "if")
        """
        if not symbol:
            return ""

        # 提取字母部分 (品种代码)
        product = ""
        for char in symbol:
            if char.isalpha():
                product += char
            elif char.isdigit() and product:
                break

        return product.lower()

    def _round_down(self, price: float, tick_size: float) -> float:
        """向下取整到tick_size.

        参数:
            price: 原始价格
            tick_size: 最小变动价位

        返回:
            修正后的价格
        """
        if tick_size <= 0:
            return price
        return int(price / tick_size) * tick_size

    def _round_up(self, price: float, tick_size: float) -> float:
        """向上取整到tick_size.

        参数:
            price: 原始价格
            tick_size: 最小变动价位

        返回:
            修正后的价格
        """
        if tick_size <= 0:
            return price
        import math

        return math.ceil(price / tick_size) * tick_size


# 便捷函数

_default_guard: LimitPriceGuard | None = None


def get_default_guard() -> LimitPriceGuard:
    """获取默认涨跌停保护门控 (单例).

    返回:
        默认的LimitPriceGuard实例
    """
    global _default_guard
    if _default_guard is None:
        _default_guard = LimitPriceGuard()
    return _default_guard


def check_limit_price(
    order_price: float,
    last_settle: float,
    limit_pct: float | None = None,
    symbol: str = "",
) -> tuple[bool, str]:
    """检查订单价格是否在涨跌停范围内 (便捷函数).

    军规 M13: 涨跌停感知

    参数:
        order_price: 订单价格
        last_settle: 昨结算价
        limit_pct: 涨跌停幅度 (None则使用品种默认值)
        symbol: 合约代码

    返回:
        (是否通过, 消息)
    """
    guard = get_default_guard()
    result = guard.check_order_price(order_price, last_settle, limit_pct, symbol)
    return result.passed, result.message


def get_limit_prices(
    last_settle: float,
    limit_pct: float | None = None,
    symbol: str = "",
) -> tuple[float, float]:
    """获取涨跌停价格 (便捷函数).

    参数:
        last_settle: 昨结算价
        limit_pct: 涨跌停幅度 (None则使用品种默认值)
        symbol: 合约代码

    返回:
        (涨停价, 跌停价)
    """
    guard = get_default_guard()
    limits = guard.get_limit_prices(last_settle, limit_pct, symbol)
    return limits.limit_up, limits.limit_down
