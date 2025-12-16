"""中国期货夜盘交易日历模块 (军规级 v4.0).

本模块提供中国期货市场的交易日历功能，包括：
- 夜盘交易日归属判断
- 交易时间判断
- 节假日处理
- 下一交易日计算

军规覆盖:
- M15: 夜盘跨日处理 - 夜盘交易日归属必须正确

场景覆盖:
- CHINA.CALENDAR.NIGHT_SESSION: 夜盘时段正确
- CHINA.CALENDAR.TRADING_DAY: 交易日计算正确
- CHINA.CALENDAR.HOLIDAY: 节假日处理正确

夜盘交易日归属规则:
- 周一夜盘 21:00 → 周二 02:30 归属于周二交易日
- 周五没有夜盘
- 节假日前一天没有夜盘
- 节假日后第一天从日盘开始

示例:
    >>> from src.market.trading_calendar import ChinaTradingCalendar
    >>> calendar = ChinaTradingCalendar()
    >>> # 周一晚上21:30属于周二交易日
    >>> trading_day = calendar.get_trading_day("2025-12-15 21:30:00")
    >>> print(trading_day)
    2025-12-16
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import ClassVar

from src.market.exchange_config import (
    Exchange,
    NightSessionEnd,
    get_exchange_for_product,
    get_night_session_end_for_product,
)


class TradingPeriod(Enum):
    """交易时段枚举.

    属性:
        PRE_MARKET: 盘前（09:00之前）
        MORNING_1: 早盘第一节（09:00-10:15）
        MORNING_BREAK: 早盘休息（10:15-10:30）
        MORNING_2: 早盘第二节（10:30-11:30）
        LUNCH_BREAK: 午休（11:30-13:30）
        AFTERNOON: 午盘（13:30-15:00）
        AFTER_MARKET: 盘后（15:00-21:00）
        NIGHT: 夜盘（21:00-次日02:30）
        CLOSED: 休市
    """

    PRE_MARKET = "盘前"
    MORNING_1 = "早盘第一节"
    MORNING_BREAK = "早盘休息"
    MORNING_2 = "早盘第二节"
    LUNCH_BREAK = "午休"
    AFTERNOON = "午盘"
    AFTER_MARKET = "盘后"
    NIGHT = "夜盘"
    CLOSED = "休市"


@dataclass
class TradingDayInfo:
    """交易日信息.

    属性:
        trading_day: 交易日日期
        is_trading_day: 是否为交易日
        has_night_session: 是否有夜盘
        period: 当前交易时段
        reason: 非交易日原因（如节假日名称）
    """

    trading_day: date
    is_trading_day: bool = True
    has_night_session: bool = True
    period: TradingPeriod = TradingPeriod.CLOSED
    reason: str = ""


# ============================================================================
# 2025年中国期货市场节假日（示例数据，实际使用时需要更新）
# ============================================================================
HOLIDAYS_2025: dict[date, str] = {
    # 元旦
    date(2025, 1, 1): "元旦",
    # 春节（1月28日-2月4日）
    date(2025, 1, 28): "春节",
    date(2025, 1, 29): "春节",
    date(2025, 1, 30): "春节",
    date(2025, 1, 31): "春节",
    date(2025, 2, 1): "春节",
    date(2025, 2, 2): "春节",
    date(2025, 2, 3): "春节",
    date(2025, 2, 4): "春节",
    # 清明节（4月4日-4月6日）
    date(2025, 4, 4): "清明节",
    date(2025, 4, 5): "清明节",
    date(2025, 4, 6): "清明节",
    # 劳动节（5月1日-5月5日）
    date(2025, 5, 1): "劳动节",
    date(2025, 5, 2): "劳动节",
    date(2025, 5, 3): "劳动节",
    date(2025, 5, 4): "劳动节",
    date(2025, 5, 5): "劳动节",
    # 端午节（5月31日-6月2日）
    date(2025, 5, 31): "端午节",
    date(2025, 6, 1): "端午节",
    date(2025, 6, 2): "端午节",
    # 中秋节（10月6日）
    date(2025, 10, 6): "中秋节",
    # 国庆节（10月1日-10月8日）
    date(2025, 10, 1): "国庆节",
    date(2025, 10, 2): "国庆节",
    date(2025, 10, 3): "国庆节",
    date(2025, 10, 4): "国庆节",
    date(2025, 10, 5): "国庆节",
    date(2025, 10, 7): "国庆节",
    date(2025, 10, 8): "国庆节",
}

# 2025年调休工作日（周末上班）
WORKDAYS_2025: set[date] = {
    date(2025, 1, 26),  # 春节调休
    date(2025, 2, 8),  # 春节调休
    date(2025, 4, 27),  # 劳动节调休
    date(2025, 9, 28),  # 国庆节调休
    date(2025, 10, 11),  # 国庆节调休
}


@dataclass
class ChinaTradingCalendar:
    """中国期货市场交易日历.

    提供交易日计算、夜盘归属判断等功能。

    属性:
        holidays: 节假日字典（日期->节假日名称）
        workdays: 调休工作日集合
        _cache: 交易日缓存

    示例:
        >>> calendar = ChinaTradingCalendar()
        >>> # 判断是否为交易日
        >>> calendar.is_trading_day(date(2025, 12, 16))
        True
        >>> # 获取交易日
        >>> calendar.get_trading_day("2025-12-15 21:30:00")
        date(2025, 12, 16)
    """

    holidays: dict[date, str] = field(default_factory=lambda: HOLIDAYS_2025.copy())
    workdays: set[date] = field(default_factory=lambda: WORKDAYS_2025.copy())
    _cache: dict[date, TradingDayInfo] = field(default_factory=dict)

    # 交易时段时间点
    NIGHT_SESSION_START: ClassVar[time] = time(21, 0)
    NIGHT_SESSION_END_23: ClassVar[time] = time(23, 0)
    NIGHT_SESSION_END_01: ClassVar[time] = time(1, 0)
    NIGHT_SESSION_END_02: ClassVar[time] = time(2, 30)
    DAY_SESSION_START: ClassVar[time] = time(9, 0)
    MORNING_BREAK_START: ClassVar[time] = time(10, 15)
    MORNING_BREAK_END: ClassVar[time] = time(10, 30)
    LUNCH_START: ClassVar[time] = time(11, 30)
    LUNCH_END: ClassVar[time] = time(13, 30)
    DAY_SESSION_END: ClassVar[time] = time(15, 0)

    def is_holiday(self, d: date) -> bool:
        """判断是否为节假日.

        参数:
            d: 日期

        返回:
            是否为节假日
        """
        return d in self.holidays

    def get_holiday_name(self, d: date) -> str | None:
        """获取节假日名称.

        参数:
            d: 日期

        返回:
            节假日名称，非节假日返回None
        """
        return self.holidays.get(d)

    def is_weekend(self, d: date) -> bool:
        """判断是否为周末.

        参数:
            d: 日期

        返回:
            是否为周末（周六或周日）
        """
        return d.weekday() >= 5

    def is_workday_override(self, d: date) -> bool:
        """判断是否为调休工作日.

        参数:
            d: 日期

        返回:
            是否为调休工作日
        """
        return d in self.workdays

    def is_trading_day(self, d: date) -> bool:
        """判断是否为交易日.

        参数:
            d: 日期

        返回:
            是否为交易日

        规则:
        1. 节假日不是交易日
        2. 周末不是交易日（除非是调休工作日）
        3. 调休工作日是交易日
        """
        # 节假日不是交易日
        if self.is_holiday(d):
            return False

        # 调休工作日是交易日
        if self.is_workday_override(d):
            return True

        # 周末不是交易日
        return not self.is_weekend(d)

    def has_night_session_on_day(self, d: date) -> bool:
        """判断某日是否有夜盘.

        参数:
            d: 日期

        返回:
            该日是否有夜盘

        规则:
        1. 非交易日没有夜盘
        2. 周五没有夜盘
        3. 节假日前一天没有夜盘
        4. 当天是节假日没有夜盘
        """
        # 非交易日没有夜盘
        if not self.is_trading_day(d):
            return False

        # 周五没有夜盘
        if d.weekday() == 4:  # Friday
            return False

        # 检查下一个自然日是否为交易日
        next_day = d + timedelta(days=1)

        # 如果下一天是节假日或周末（非调休工作日），则没有夜盘
        if self.is_holiday(next_day):
            return False

        # 周六周日（非调休）前一天没有夜盘
        if self.is_weekend(next_day) and not self.is_workday_override(next_day):
            return False

        return True

    def get_trading_day(
        self,
        dt: datetime | str,
        product: str | None = None,
    ) -> date:
        """根据时间戳获取所属交易日.

        参数:
            dt: 时间戳（datetime对象或ISO格式字符串）
            product: 品种代码（可选，用于判断夜盘结束时间）

        返回:
            所属交易日

        规则:
        - 夜盘21:00-次日02:30属于下一交易日
        - 日盘09:00-15:00属于当日
        - 其他时间属于当日（如果当日是交易日）
        """
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        current_date = dt.date()
        current_time = dt.time()

        # 判断是否在夜盘时段
        if self._is_in_night_session(current_time, product):
            # 夜盘时段：21:00-23:59属于下一交易日
            if current_time >= self.NIGHT_SESSION_START:
                return self._get_next_trading_day(current_date)
            # 夜盘时段：00:00-02:30属于当日（夜盘延续）
            return current_date

        # 日盘时段：属于当日
        return current_date

    def _is_in_night_session(
        self,
        t: time,
        product: str | None = None,
    ) -> bool:
        """判断时间是否在夜盘时段.

        参数:
            t: 时间
            product: 品种代码

        返回:
            是否在夜盘时段
        """
        # 获取夜盘结束时间
        if product:
            night_end = get_night_session_end_for_product(product)
        else:
            night_end = NightSessionEnd.T_02_30  # 默认最晚结束时间

        # 无夜盘品种
        if night_end == NightSessionEnd.NONE:
            return False

        # 21:00-23:59
        if t >= self.NIGHT_SESSION_START:
            return True

        # 00:00-夜盘结束时间
        if night_end == NightSessionEnd.T_23_00:
            return False  # 23:00结束，00:00后不算夜盘
        if night_end == NightSessionEnd.T_01_00:
            return t < self.NIGHT_SESSION_END_01
        if night_end == NightSessionEnd.T_02_30:
            return t < self.NIGHT_SESSION_END_02

        return False

    def _get_next_trading_day(self, d: date) -> date:
        """获取下一个交易日.

        参数:
            d: 当前日期

        返回:
            下一个交易日
        """
        next_day = d + timedelta(days=1)
        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)
            # 防止无限循环（最多查找30天）
            if (next_day - d).days > 30:
                # 理论上不会发生，但作为保护
                return next_day
        return next_day

    def get_next_trading_day(self, d: date) -> date:
        """获取下一个交易日（公开方法）.

        参数:
            d: 当前日期

        返回:
            下一个交易日
        """
        return self._get_next_trading_day(d)

    def get_previous_trading_day(self, d: date) -> date:
        """获取上一个交易日.

        参数:
            d: 当前日期

        返回:
            上一个交易日
        """
        prev_day = d - timedelta(days=1)
        while not self.is_trading_day(prev_day):
            prev_day -= timedelta(days=1)
            # 防止无限循环
            if (d - prev_day).days > 30:
                return prev_day
        return prev_day

    def is_trading_time(
        self,
        dt: datetime | str,
        product: str | None = None,
        exchange: Exchange | None = None,
    ) -> bool:
        """判断是否为交易时间.

        参数:
            dt: 时间戳
            product: 品种代码
            exchange: 交易所

        返回:
            是否为交易时间
        """
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        current_date = dt.date()
        current_time = dt.time()

        # 确定交易所
        if exchange is None and product:
            exchange = get_exchange_for_product(product)

        # 判断夜盘
        if self._is_in_night_session(current_time, product):
            # 夜盘时段需要检查前一日是否有夜盘
            if current_time >= self.NIGHT_SESSION_START:
                return self.has_night_session_on_day(current_date)
            # 凌晨时段需要检查前一日是否有夜盘
            prev_day = current_date - timedelta(days=1)
            return self.has_night_session_on_day(prev_day)

        # 日盘时段
        if not self.is_trading_day(current_date):
            return False

        # 检查是否在日盘时段内
        return self._is_in_day_session(current_time, exchange)

    def _is_in_day_session(
        self,
        t: time,
        exchange: Exchange | None = None,
    ) -> bool:
        """判断时间是否在日盘时段.

        参数:
            t: 时间
            exchange: 交易所

        返回:
            是否在日盘时段
        """
        # CFFEX股指期货特殊时段
        if exchange == Exchange.CFFEX:
            # 09:30-11:30, 13:00-15:00
            if time(9, 30) <= t < time(11, 30):
                return True
            if time(13, 0) <= t < time(15, 0):
                return True
            return False

        # 标准日盘时段
        # 09:00-10:15
        if self.DAY_SESSION_START <= t < self.MORNING_BREAK_START:
            return True
        # 10:30-11:30
        if self.MORNING_BREAK_END <= t < self.LUNCH_START:
            return True
        # 13:30-15:00
        if self.LUNCH_END <= t < self.DAY_SESSION_END:
            return True

        return False

    def get_trading_period(
        self,
        dt: datetime | str,
        product: str | None = None,
    ) -> TradingPeriod:
        """获取当前交易时段.

        参数:
            dt: 时间戳
            product: 品种代码

        返回:
            当前交易时段
        """
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        current_date = dt.date()
        current_time = dt.time()

        # 判断是否为交易日
        if not self.is_trading_day(current_date):
            # 检查是否在夜盘延续时段（凌晨）
            if current_time < time(3, 0):
                prev_day = current_date - timedelta(days=1)
                if self.has_night_session_on_day(prev_day):
                    if self._is_in_night_session(current_time, product):
                        return TradingPeriod.NIGHT
            return TradingPeriod.CLOSED

        # 夜盘时段
        if current_time >= self.NIGHT_SESSION_START:
            if self.has_night_session_on_day(current_date):
                return TradingPeriod.NIGHT
            return TradingPeriod.AFTER_MARKET

        # 凌晨夜盘延续
        if current_time < time(3, 0):
            prev_day = current_date - timedelta(days=1)
            if self.has_night_session_on_day(prev_day):
                if self._is_in_night_session(current_time, product):
                    return TradingPeriod.NIGHT

        # 盘前
        if current_time < self.DAY_SESSION_START:
            return TradingPeriod.PRE_MARKET

        # 早盘第一节
        if current_time < self.MORNING_BREAK_START:
            return TradingPeriod.MORNING_1

        # 早盘休息
        if current_time < self.MORNING_BREAK_END:
            return TradingPeriod.MORNING_BREAK

        # 早盘第二节
        if current_time < self.LUNCH_START:
            return TradingPeriod.MORNING_2

        # 午休
        if current_time < self.LUNCH_END:
            return TradingPeriod.LUNCH_BREAK

        # 午盘
        if current_time < self.DAY_SESSION_END:
            return TradingPeriod.AFTERNOON

        # 盘后
        return TradingPeriod.AFTER_MARKET

    def get_trading_days_between(
        self,
        start: date,
        end: date,
    ) -> list[date]:
        """获取两个日期之间的所有交易日.

        参数:
            start: 开始日期（包含）
            end: 结束日期（包含）

        返回:
            交易日列表
        """
        trading_days = []
        current = start
        while current <= end:
            if self.is_trading_day(current):
                trading_days.append(current)
            current += timedelta(days=1)
        return trading_days

    def count_trading_days(
        self,
        start: date,
        end: date,
    ) -> int:
        """计算两个日期之间的交易日数量.

        参数:
            start: 开始日期（包含）
            end: 结束日期（包含）

        返回:
            交易日数量
        """
        return len(self.get_trading_days_between(start, end))

    def add_trading_days(
        self,
        d: date,
        n: int,
    ) -> date:
        """在日期上增加n个交易日.

        参数:
            d: 起始日期
            n: 交易日数量（正数向后，负数向前）

        返回:
            目标日期
        """
        if n == 0:
            return d

        step = 1 if n > 0 else -1
        remaining = abs(n)
        current = d

        while remaining > 0:
            current += timedelta(days=step)
            if self.is_trading_day(current):
                remaining -= 1

        return current


# ============================================================================
# 便捷函数
# ============================================================================
_default_calendar: ChinaTradingCalendar | None = None


def get_default_calendar() -> ChinaTradingCalendar:
    """获取默认交易日历实例.

    返回:
        默认交易日历实例
    """
    global _default_calendar
    if _default_calendar is None:
        _default_calendar = ChinaTradingCalendar()
    return _default_calendar


def get_trading_day(dt: datetime | str, product: str | None = None) -> date:
    """获取时间戳所属交易日.

    参数:
        dt: 时间戳
        product: 品种代码

    返回:
        所属交易日
    """
    return get_default_calendar().get_trading_day(dt, product)


def is_trading_day(d: date) -> bool:
    """判断是否为交易日.

    参数:
        d: 日期

    返回:
        是否为交易日
    """
    return get_default_calendar().is_trading_day(d)


def is_trading_time(
    dt: datetime | str,
    product: str | None = None,
) -> bool:
    """判断是否为交易时间.

    参数:
        dt: 时间戳
        product: 品种代码

    返回:
        是否为交易时间
    """
    return get_default_calendar().is_trading_time(dt, product)
