"""
中国期货市场触发器 - ChinaTriggers (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §12 Phase 7, §18 涨跌停板规则, §19 保证金制度
V4 Scenarios:
- CHINA.TRIGGER.LIMIT_PRICE: 涨跌停触发器
- CHINA.TRIGGER.MARGIN_CALL: 保证金追缴触发
- CHINA.TRIGGER.DELIVERY: 交割月接近触发

军规覆盖:
- M6: 熔断保护 - 触发风控阈值必须立即停止
- M13: 涨跌停感知 - 订单价格必须检查涨跌停板
- M15: 夜盘跨日处理 - 交易日归属必须正确
- M16: 保证金实时监控 - 保证金使用率必须实时计算

功能特性:
- 涨跌停板触发检测与预警
- 保证金使用率五级预警触发
- 交割月临近自动平仓提醒
- 与现有TriggerManager无缝集成

示例:
    >>> from src.guardian.triggers_china import (
    ...     LimitPriceTrigger,
    ...     MarginTrigger,
    ...     DeliveryApproachingTrigger,
    ...     register_china_triggers,
    ... )
    >>> manager = TriggerManager()
    >>> register_china_triggers(manager)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any

from src.guardian.triggers import BaseTrigger, TriggerResult


class LimitPriceStatus(Enum):
    """涨跌停状态枚举."""

    NORMAL = "NORMAL"  # 正常交易
    NEAR_LIMIT_UP = "NEAR_LIMIT_UP"  # 接近涨停
    NEAR_LIMIT_DOWN = "NEAR_LIMIT_DOWN"  # 接近跌停
    AT_LIMIT_UP = "AT_LIMIT_UP"  # 涨停
    AT_LIMIT_DOWN = "AT_LIMIT_DOWN"  # 跌停


class MarginLevel(Enum):
    """保证金等级枚举."""

    SAFE = "SAFE"  # < 50%
    NORMAL = "NORMAL"  # 50% - 70%
    WARNING = "WARNING"  # 70% - 85%
    DANGER = "DANGER"  # 85% - 100%
    CRITICAL = "CRITICAL"  # >= 100%


@dataclass
class LimitPriceInfo:
    """涨跌停信息.

    属性:
        symbol: 合约代码
        current_price: 当前价格
        limit_up: 涨停价
        limit_down: 跌停价
        status: 涨跌停状态
        distance_to_limit_pct: 距离涨跌停的百分比
    """

    symbol: str
    current_price: float
    limit_up: float
    limit_down: float
    status: LimitPriceStatus
    distance_to_limit_pct: float


@dataclass
class MarginInfo:
    """保证金信息.

    属性:
        equity: 账户权益
        margin_used: 已用保证金
        margin_available: 可用保证金
        usage_ratio: 使用率
        level: 保证金等级
    """

    equity: float
    margin_used: float
    margin_available: float
    usage_ratio: float
    level: MarginLevel


@dataclass
class DeliveryInfo:
    """交割信息.

    属性:
        symbol: 合约代码
        delivery_date: 交割日期
        days_to_delivery: 距离交割天数
        position: 当前持仓
        should_close: 是否应该平仓
    """

    symbol: str
    delivery_date: date
    days_to_delivery: int
    position: int
    should_close: bool


class LimitPriceTrigger(BaseTrigger):
    """涨跌停触发器 (军规 M6, M13).

    V4 Scenario: CHINA.TRIGGER.LIMIT_PRICE

    检测合约价格是否接近或达到涨跌停板。

    属性:
        near_limit_threshold: 接近涨跌停阈值 (默认 1%)

    示例:
        >>> trigger = LimitPriceTrigger(near_limit_threshold=0.01)
        >>> result = trigger.check({
        ...     "limit_prices": {
        ...         "rb2501": {"current": 4200, "limit_up": 4410, "limit_down": 3990}
        ...     }
        ... })
    """

    def __init__(self, near_limit_threshold: float = 0.01) -> None:
        """初始化涨跌停触发器.

        参数:
            near_limit_threshold: 接近涨跌停阈值 (默认 0.01 即 1%)
        """
        self._near_limit_threshold = near_limit_threshold
        self._triggered_symbols: dict[str, LimitPriceInfo] = {}

    @property
    def name(self) -> str:
        """触发器名称."""
        return "limit_price_china"

    @property
    def triggered_symbols(self) -> dict[str, LimitPriceInfo]:
        """获取触发的合约信息."""
        return self._triggered_symbols.copy()

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查涨跌停状态.

        参数:
            state: 状态字典, 需包含:
                - limit_prices: dict[str, dict] 合约涨跌停信息
                  每个合约包含 {current, limit_up, limit_down}

        返回:
            检测结果
        """
        limit_prices = state.get("limit_prices", {})
        self._triggered_symbols.clear()

        triggered_list: list[dict[str, Any]] = []
        at_limit_symbols: list[str] = []
        near_limit_symbols: list[str] = []

        for symbol, prices in limit_prices.items():
            current = prices.get("current", 0)
            limit_up = prices.get("limit_up", 0)
            limit_down = prices.get("limit_down", 0)

            if current <= 0 or limit_up <= 0 or limit_down <= 0:
                continue

            # 计算涨跌停状态
            status, distance_pct = self._calculate_status(current, limit_up, limit_down)

            if status in (LimitPriceStatus.AT_LIMIT_UP, LimitPriceStatus.AT_LIMIT_DOWN):
                at_limit_symbols.append(symbol)
                info = LimitPriceInfo(
                    symbol=symbol,
                    current_price=current,
                    limit_up=limit_up,
                    limit_down=limit_down,
                    status=status,
                    distance_to_limit_pct=distance_pct,
                )
                self._triggered_symbols[symbol] = info
                triggered_list.append(
                    {
                        "symbol": symbol,
                        "status": status.value,
                        "current": current,
                        "limit_up": limit_up,
                        "limit_down": limit_down,
                        "distance_pct": distance_pct,
                    }
                )

            elif status in (
                LimitPriceStatus.NEAR_LIMIT_UP,
                LimitPriceStatus.NEAR_LIMIT_DOWN,
            ):
                near_limit_symbols.append(symbol)
                info = LimitPriceInfo(
                    symbol=symbol,
                    current_price=current,
                    limit_up=limit_up,
                    limit_down=limit_down,
                    status=status,
                    distance_to_limit_pct=distance_pct,
                )
                self._triggered_symbols[symbol] = info
                triggered_list.append(
                    {
                        "symbol": symbol,
                        "status": status.value,
                        "current": current,
                        "limit_up": limit_up,
                        "limit_down": limit_down,
                        "distance_pct": distance_pct,
                    }
                )

        triggered = len(triggered_list) > 0

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name="limit_price_alert",
            details={
                "triggered_symbols": triggered_list,
                "at_limit_count": len(at_limit_symbols),
                "near_limit_count": len(near_limit_symbols),
                "at_limit_symbols": at_limit_symbols,
                "near_limit_symbols": near_limit_symbols,
                "threshold": self._near_limit_threshold,
            },
        )

    def _calculate_status(
        self, current: float, limit_up: float, limit_down: float
    ) -> tuple[LimitPriceStatus, float]:
        """计算涨跌停状态.

        参数:
            current: 当前价格
            limit_up: 涨停价
            limit_down: 跌停价

        返回:
            (状态, 距离最近限价的百分比)
        """
        # 计算距离涨停和跌停的比例
        range_total = limit_up - limit_down
        if range_total <= 0:
            return LimitPriceStatus.NORMAL, 0.0

        distance_to_up = (limit_up - current) / range_total
        distance_to_down = (current - limit_down) / range_total

        # 判断是否触及涨跌停
        if current >= limit_up:
            return LimitPriceStatus.AT_LIMIT_UP, 0.0
        if current <= limit_down:
            return LimitPriceStatus.AT_LIMIT_DOWN, 0.0

        # 判断是否接近涨跌停
        if distance_to_up <= self._near_limit_threshold:
            return LimitPriceStatus.NEAR_LIMIT_UP, distance_to_up
        if distance_to_down <= self._near_limit_threshold:
            return LimitPriceStatus.NEAR_LIMIT_DOWN, distance_to_down

        return LimitPriceStatus.NORMAL, min(distance_to_up, distance_to_down)

    def reset(self) -> None:
        """重置触发器状态."""
        self._triggered_symbols.clear()


class MarginTrigger(BaseTrigger):
    """保证金触发器 (军规 M6, M16).

    V4 Scenario: CHINA.TRIGGER.MARGIN_CALL

    检测保证金使用率是否达到预警或危险水平。

    属性:
        warning_threshold: 预警阈值 (默认 70%)
        danger_threshold: 危险阈值 (默认 85%)
        critical_threshold: 临界阈值 (默认 100%)

    示例:
        >>> trigger = MarginTrigger()
        >>> result = trigger.check({
        ...     "equity": 100000.0,
        ...     "margin_used": 80000.0,
        ... })
    """

    # 保证金等级阈值
    SAFE_THRESHOLD = 0.5
    NORMAL_THRESHOLD = 0.7
    WARNING_THRESHOLD = 0.85
    DANGER_THRESHOLD = 1.0

    def __init__(
        self,
        warning_threshold: float = 0.7,
        danger_threshold: float = 0.85,
        critical_threshold: float = 1.0,
    ) -> None:
        """初始化保证金触发器.

        参数:
            warning_threshold: 预警阈值 (默认 0.7 即 70%)
            danger_threshold: 危险阈值 (默认 0.85 即 85%)
            critical_threshold: 临界阈值 (默认 1.0 即 100%)
        """
        self._warning_threshold = warning_threshold
        self._danger_threshold = danger_threshold
        self._critical_threshold = critical_threshold
        self._last_level: MarginLevel = MarginLevel.SAFE
        self._last_info: MarginInfo | None = None

    @property
    def name(self) -> str:
        """触发器名称."""
        return "margin_china"

    @property
    def last_level(self) -> MarginLevel:
        """获取最后的保证金等级."""
        return self._last_level

    @property
    def last_info(self) -> MarginInfo | None:
        """获取最后的保证金信息."""
        return self._last_info

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查保证金使用率.

        参数:
            state: 状态字典, 需包含:
                - equity: float 账户权益
                - margin_used: float 已用保证金

        返回:
            检测结果
        """
        equity = state.get("equity", 0.0)
        margin_used = state.get("margin_used", 0.0)

        # 计算使用率
        usage_ratio = (
            margin_used / equity if equity > 0 else (1.0 if margin_used > 0 else 0.0)
        )

        margin_available = max(0.0, equity - margin_used)

        # 计算等级
        level = self._calculate_level(usage_ratio)

        # 保存信息
        self._last_info = MarginInfo(
            equity=equity,
            margin_used=margin_used,
            margin_available=margin_available,
            usage_ratio=usage_ratio,
            level=level,
        )

        # 判断是否触发 (WARNING及以上触发)
        triggered = level in (
            MarginLevel.WARNING,
            MarginLevel.DANGER,
            MarginLevel.CRITICAL,
        )

        # 生成事件名称
        event_name = self._get_event_name(level)

        # 检查等级是否变化
        level_changed = level != self._last_level
        self._last_level = level

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name=event_name,
            details={
                "equity": equity,
                "margin_used": margin_used,
                "margin_available": margin_available,
                "usage_ratio": usage_ratio,
                "usage_ratio_pct": f"{usage_ratio:.1%}",
                "level": level.value,
                "level_changed": level_changed,
                "action_required": self._get_action(level),
            },
        )

    def _calculate_level(self, usage_ratio: float) -> MarginLevel:
        """计算保证金等级.

        参数:
            usage_ratio: 使用率

        返回:
            保证金等级
        """
        if usage_ratio < self.SAFE_THRESHOLD:
            return MarginLevel.SAFE
        if usage_ratio < self.NORMAL_THRESHOLD:
            return MarginLevel.NORMAL
        if usage_ratio < self.WARNING_THRESHOLD:
            return MarginLevel.WARNING
        if usage_ratio < self.DANGER_THRESHOLD:
            return MarginLevel.DANGER
        return MarginLevel.CRITICAL

    def _get_event_name(self, level: MarginLevel) -> str:
        """获取事件名称.

        参数:
            level: 保证金等级

        返回:
            事件名称
        """
        return {
            MarginLevel.SAFE: "margin_safe",
            MarginLevel.NORMAL: "margin_normal",
            MarginLevel.WARNING: "margin_warning",
            MarginLevel.DANGER: "margin_danger",
            MarginLevel.CRITICAL: "margin_critical",
        }[level]

    def _get_action(self, level: MarginLevel) -> str:
        """获取建议行动.

        参数:
            level: 保证金等级

        返回:
            建议行动
        """
        return {
            MarginLevel.SAFE: "正常交易",
            MarginLevel.NORMAL: "注意仓位控制",
            MarginLevel.WARNING: "建议减仓, 避免新开仓",
            MarginLevel.DANGER: "立即减仓, 禁止开仓",
            MarginLevel.CRITICAL: "触发强平, 紧急平仓",
        }[level]

    def reset(self) -> None:
        """重置触发器状态."""
        self._last_level = MarginLevel.SAFE
        self._last_info = None


class DeliveryApproachingTrigger(BaseTrigger):
    """交割临近触发器 (军规 M6, M15).

    V4 Scenario: CHINA.TRIGGER.DELIVERY

    检测持仓合约是否接近交割月, 提醒移仓换月。

    属性:
        warning_days: 预警天数 (默认 5 个交易日)
        critical_days: 紧急天数 (默认 2 个交易日)

    示例:
        >>> trigger = DeliveryApproachingTrigger(warning_days=5)
        >>> result = trigger.check({
        ...     "positions": [
        ...         {"symbol": "rb2501", "delivery_date": date(2025, 1, 15), "qty": 10}
        ...     ],
        ...     "current_date": date(2025, 1, 10),
        ... })
    """

    def __init__(
        self,
        warning_days: int = 5,
        critical_days: int = 2,
    ) -> None:
        """初始化交割临近触发器.

        参数:
            warning_days: 预警天数 (默认 5 个交易日)
            critical_days: 紧急天数 (默认 2 个交易日)
        """
        self._warning_days = warning_days
        self._critical_days = critical_days
        self._approaching_positions: list[DeliveryInfo] = []

    @property
    def name(self) -> str:
        """触发器名称."""
        return "delivery_approaching_china"

    @property
    def approaching_positions(self) -> list[DeliveryInfo]:
        """获取接近交割的持仓列表."""
        return self._approaching_positions.copy()

    def check(self, state: dict[str, Any]) -> TriggerResult:
        """检查交割临近状态.

        参数:
            state: 状态字典, 需包含:
                - positions: list[dict] 持仓列表
                  每个持仓包含 {symbol, delivery_date, qty}
                - current_date: date 当前日期 (可选)

        返回:
            检测结果
        """
        positions = state.get("positions", [])
        current_date = state.get("current_date")

        if current_date is None:
            current_date = date.today()  # noqa: DTZ011
        elif isinstance(current_date, datetime):
            current_date = current_date.date()

        self._approaching_positions.clear()

        warning_positions: list[dict[str, Any]] = []
        critical_positions: list[dict[str, Any]] = []

        for pos in positions:
            symbol = pos.get("symbol", "")
            qty = pos.get("qty", 0)
            delivery_date = pos.get("delivery_date")

            # 跳过无持仓的合约
            if qty == 0:
                continue

            # 处理交割日期
            if delivery_date is None:
                continue
            if isinstance(delivery_date, str):
                try:
                    delivery_date = datetime.strptime(  # noqa: DTZ007
                        delivery_date, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    continue
            elif isinstance(delivery_date, datetime):
                delivery_date = delivery_date.date()

            # 计算剩余天数
            days_to_delivery = (delivery_date - current_date).days

            # 跳过已过期的
            if days_to_delivery < 0:
                continue

            # 判断是否需要预警
            should_close = days_to_delivery <= self._critical_days

            if days_to_delivery <= self._warning_days:
                info = DeliveryInfo(
                    symbol=symbol,
                    delivery_date=delivery_date,
                    days_to_delivery=days_to_delivery,
                    position=qty,
                    should_close=should_close,
                )
                self._approaching_positions.append(info)

                pos_dict = {
                    "symbol": symbol,
                    "delivery_date": delivery_date.isoformat(),
                    "days_to_delivery": days_to_delivery,
                    "position": qty,
                    "should_close": should_close,
                }

                if should_close:
                    critical_positions.append(pos_dict)
                else:
                    warning_positions.append(pos_dict)

        triggered = len(self._approaching_positions) > 0

        # 确定事件名称
        if len(critical_positions) > 0:
            event_name = "delivery_critical"
        elif len(warning_positions) > 0:
            event_name = "delivery_warning"
        else:
            event_name = "delivery_normal"

        return TriggerResult(
            triggered=triggered,
            trigger_name=self.name,
            event_name=event_name,
            details={
                "warning_positions": warning_positions,
                "critical_positions": critical_positions,
                "warning_count": len(warning_positions),
                "critical_count": len(critical_positions),
                "warning_days_threshold": self._warning_days,
                "critical_days_threshold": self._critical_days,
            },
        )

    def reset(self) -> None:
        """重置触发器状态."""
        self._approaching_positions.clear()


# ============================================================
# 便捷函数
# ============================================================


def create_default_china_triggers() -> list[BaseTrigger]:
    """创建默认的中国期货触发器列表.

    返回:
        触发器列表
    """
    return [
        LimitPriceTrigger(near_limit_threshold=0.01),
        MarginTrigger(
            warning_threshold=0.7,
            danger_threshold=0.85,
            critical_threshold=1.0,
        ),
        DeliveryApproachingTrigger(warning_days=5, critical_days=2),
    ]


def register_china_triggers(manager: Any) -> list[str]:
    """注册中国期货触发器到管理器.

    参数:
        manager: TriggerManager 实例

    返回:
        已注册的触发器名称列表
    """
    triggers = create_default_china_triggers()
    names = []
    for trigger in triggers:
        manager.add_trigger(trigger)
        names.append(trigger.name)
    return names
