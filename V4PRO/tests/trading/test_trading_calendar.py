"""夜盘交易日历模块测试 (军规级 v4.0).

测试场景:
- CHINA.CALENDAR.NIGHT_SESSION: 夜盘时段正确
- CHINA.CALENDAR.TRADING_DAY: 交易日计算正确
- CHINA.CALENDAR.HOLIDAY: 节假日处理正确

军规覆盖:
- M15: 夜盘跨日处理
"""

from datetime import date, datetime

import pytest

from src.market.trading_calendar import (
    HOLIDAYS_2025,
    WORKDAYS_2025,
    ChinaTradingCalendar,
    TradingDayInfo,
    TradingPeriod,
    get_default_calendar,
    get_trading_day,
    is_trading_day,
    is_trading_time,
)


class TestTradingPeriodEnum:
    """交易时段枚举测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    def test_trading_period_values(self) -> None:
        """测试交易时段枚举值."""
        assert TradingPeriod.PRE_MARKET.value == "盘前"
        assert TradingPeriod.MORNING_1.value == "早盘第一节"
        assert TradingPeriod.NIGHT.value == "夜盘"
        assert TradingPeriod.CLOSED.value == "休市"


class TestTradingDayInfo:
    """交易日信息测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    def test_trading_day_info_creation(self) -> None:
        """测试交易日信息创建."""
        info = TradingDayInfo(
            trading_day=date(2025, 12, 16),
            is_trading_day=True,
            has_night_session=True,
            period=TradingPeriod.MORNING_1,
        )
        assert info.trading_day == date(2025, 12, 16)
        assert info.is_trading_day is True
        assert info.has_night_session is True


class TestHolidayData:
    """节假日数据测试."""

    RULE_ID = "CHINA.CALENDAR.HOLIDAY"

    def test_holidays_2025_exists(self) -> None:
        """测试2025年节假日数据存在."""
        assert len(HOLIDAYS_2025) > 0

    def test_spring_festival_2025(self) -> None:
        """测试2025年春节假期."""
        assert date(2025, 1, 28) in HOLIDAYS_2025
        assert HOLIDAYS_2025[date(2025, 1, 28)] == "春节"

    def test_national_day_2025(self) -> None:
        """测试2025年国庆节假期."""
        assert date(2025, 10, 1) in HOLIDAYS_2025
        assert HOLIDAYS_2025[date(2025, 10, 1)] == "国庆节"

    def test_workdays_2025_exists(self) -> None:
        """测试2025年调休工作日数据存在."""
        assert len(WORKDAYS_2025) > 0


class TestChinaTradingCalendar:
    """中国期货交易日历测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_is_holiday(self, calendar: ChinaTradingCalendar) -> None:
        """测试节假日判断."""
        assert calendar.is_holiday(date(2025, 1, 1)) is True
        assert calendar.is_holiday(date(2025, 10, 1)) is True
        assert calendar.is_holiday(date(2025, 12, 16)) is False

    def test_get_holiday_name(self, calendar: ChinaTradingCalendar) -> None:
        """测试获取节假日名称."""
        assert calendar.get_holiday_name(date(2025, 1, 1)) == "元旦"
        assert calendar.get_holiday_name(date(2025, 10, 1)) == "国庆节"
        assert calendar.get_holiday_name(date(2025, 12, 16)) is None

    def test_is_weekend(self, calendar: ChinaTradingCalendar) -> None:
        """测试周末判断."""
        # 2025-12-13 是周六
        assert calendar.is_weekend(date(2025, 12, 13)) is True
        # 2025-12-14 是周日
        assert calendar.is_weekend(date(2025, 12, 14)) is True
        # 2025-12-15 是周一
        assert calendar.is_weekend(date(2025, 12, 15)) is False

    def test_is_workday_override(self, calendar: ChinaTradingCalendar) -> None:
        """测试调休工作日判断."""
        assert calendar.is_workday_override(date(2025, 1, 26)) is True
        assert calendar.is_workday_override(date(2025, 12, 16)) is False

    def test_is_trading_day_normal(self, calendar: ChinaTradingCalendar) -> None:
        """测试普通工作日为交易日."""
        # 2025-12-16 是周二
        assert calendar.is_trading_day(date(2025, 12, 16)) is True
        # 2025-12-17 是周三
        assert calendar.is_trading_day(date(2025, 12, 17)) is True

    def test_is_trading_day_weekend(self, calendar: ChinaTradingCalendar) -> None:
        """测试周末不是交易日."""
        # 2025-12-13 是周六
        assert calendar.is_trading_day(date(2025, 12, 13)) is False
        # 2025-12-14 是周日
        assert calendar.is_trading_day(date(2025, 12, 14)) is False

    def test_is_trading_day_holiday(self, calendar: ChinaTradingCalendar) -> None:
        """测试节假日不是交易日."""
        assert calendar.is_trading_day(date(2025, 1, 1)) is False
        assert calendar.is_trading_day(date(2025, 10, 1)) is False

    def test_is_trading_day_workday_override(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试调休工作日是交易日."""
        # 2025-01-26 是周日但是调休工作日
        assert calendar.is_trading_day(date(2025, 1, 26)) is True


class TestNightSessionRules:
    """夜盘规则测试."""

    RULE_ID = "CHINA.CALENDAR.NIGHT_SESSION"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_has_night_session_normal_day(self, calendar: ChinaTradingCalendar) -> None:
        """测试普通交易日有夜盘."""
        # 2025-12-15 是周一
        assert calendar.has_night_session_on_day(date(2025, 12, 15)) is True
        # 2025-12-16 是周二
        assert calendar.has_night_session_on_day(date(2025, 12, 16)) is True

    def test_has_night_session_friday(self, calendar: ChinaTradingCalendar) -> None:
        """测试周五没有夜盘."""
        # 2025-12-19 是周五
        assert calendar.has_night_session_on_day(date(2025, 12, 19)) is False

    def test_has_night_session_before_holiday(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试节假日前一天没有夜盘."""
        # 2024-12-31 是周二，下一天2025-01-01是元旦假期
        # 所以2024-12-31没有夜盘
        assert calendar.has_night_session_on_day(date(2024, 12, 31)) is False

    def test_has_night_session_non_trading_day(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试非交易日没有夜盘."""
        # 2025-12-13 是周六
        assert calendar.has_night_session_on_day(date(2025, 12, 13)) is False
        # 2025-01-01 是元旦
        assert calendar.has_night_session_on_day(date(2025, 1, 1)) is False


class TestTradingDayCalculation:
    """交易日计算测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_get_trading_day_day_session(self, calendar: ChinaTradingCalendar) -> None:
        """测试日盘时段归属当日."""
        # 2025-12-16 10:00 属于 2025-12-16
        dt = datetime(2025, 12, 16, 10, 0)
        assert calendar.get_trading_day(dt) == date(2025, 12, 16)

    def test_get_trading_day_night_session_before_midnight(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试夜盘21:00-23:59归属下一交易日."""
        # 2025-12-15 21:30 属于 2025-12-16
        dt = datetime(2025, 12, 15, 21, 30)
        assert calendar.get_trading_day(dt) == date(2025, 12, 16)

    def test_get_trading_day_night_session_after_midnight(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试夜盘00:00-02:30归属当日."""
        # 2025-12-16 01:30 属于 2025-12-16（夜盘延续）
        dt = datetime(2025, 12, 16, 1, 30)
        assert calendar.get_trading_day(dt) == date(2025, 12, 16)

    def test_get_trading_day_string_input(self, calendar: ChinaTradingCalendar) -> None:
        """测试字符串输入."""
        trading_day = calendar.get_trading_day("2025-12-16T10:00:00")
        assert trading_day == date(2025, 12, 16)

    def test_get_next_trading_day(self, calendar: ChinaTradingCalendar) -> None:
        """测试获取下一交易日."""
        # 2025-12-19 是周五，下一交易日是 2025-12-22 周一
        next_day = calendar.get_next_trading_day(date(2025, 12, 19))
        assert next_day == date(2025, 12, 22)

    def test_get_previous_trading_day(self, calendar: ChinaTradingCalendar) -> None:
        """测试获取上一交易日."""
        # 2025-12-22 是周一，上一交易日是 2025-12-19 周五
        prev_day = calendar.get_previous_trading_day(date(2025, 12, 22))
        assert prev_day == date(2025, 12, 19)


class TestTradingTimeCheck:
    """交易时间判断测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_is_trading_time_morning_1(self, calendar: ChinaTradingCalendar) -> None:
        """测试早盘第一节是交易时间."""
        dt = datetime(2025, 12, 16, 9, 30)
        assert calendar.is_trading_time(dt) is True

    def test_is_trading_time_morning_break(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试早盘休息不是交易时间."""
        dt = datetime(2025, 12, 16, 10, 20)
        assert calendar.is_trading_time(dt) is False

    def test_is_trading_time_morning_2(self, calendar: ChinaTradingCalendar) -> None:
        """测试早盘第二节是交易时间."""
        dt = datetime(2025, 12, 16, 11, 0)
        assert calendar.is_trading_time(dt) is True

    def test_is_trading_time_lunch_break(self, calendar: ChinaTradingCalendar) -> None:
        """测试午休不是交易时间."""
        dt = datetime(2025, 12, 16, 12, 0)
        assert calendar.is_trading_time(dt) is False

    def test_is_trading_time_afternoon(self, calendar: ChinaTradingCalendar) -> None:
        """测试午盘是交易时间."""
        dt = datetime(2025, 12, 16, 14, 0)
        assert calendar.is_trading_time(dt) is True

    def test_is_trading_time_night_session(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试夜盘是交易时间（如果当日有夜盘）."""
        # 2025-12-15 是周一，有夜盘
        dt = datetime(2025, 12, 15, 21, 30)
        assert calendar.is_trading_time(dt) is True

    def test_is_trading_time_night_session_friday(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试周五夜盘不是交易时间."""
        # 2025-12-19 是周五，没有夜盘
        dt = datetime(2025, 12, 19, 21, 30)
        assert calendar.is_trading_time(dt) is False


class TestTradingPeriodDetection:
    """交易时段检测测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_get_trading_period_pre_market(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试盘前时段."""
        dt = datetime(2025, 12, 16, 8, 30)
        assert calendar.get_trading_period(dt) == TradingPeriod.PRE_MARKET

    def test_get_trading_period_morning_1(self, calendar: ChinaTradingCalendar) -> None:
        """测试早盘第一节."""
        dt = datetime(2025, 12, 16, 9, 30)
        assert calendar.get_trading_period(dt) == TradingPeriod.MORNING_1

    def test_get_trading_period_morning_break(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试早盘休息."""
        dt = datetime(2025, 12, 16, 10, 20)
        assert calendar.get_trading_period(dt) == TradingPeriod.MORNING_BREAK

    def test_get_trading_period_morning_2(self, calendar: ChinaTradingCalendar) -> None:
        """测试早盘第二节."""
        dt = datetime(2025, 12, 16, 11, 0)
        assert calendar.get_trading_period(dt) == TradingPeriod.MORNING_2

    def test_get_trading_period_lunch_break(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试午休."""
        dt = datetime(2025, 12, 16, 12, 0)
        assert calendar.get_trading_period(dt) == TradingPeriod.LUNCH_BREAK

    def test_get_trading_period_afternoon(self, calendar: ChinaTradingCalendar) -> None:
        """测试午盘."""
        dt = datetime(2025, 12, 16, 14, 0)
        assert calendar.get_trading_period(dt) == TradingPeriod.AFTERNOON

    def test_get_trading_period_after_market(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试盘后."""
        dt = datetime(2025, 12, 16, 16, 0)
        assert calendar.get_trading_period(dt) == TradingPeriod.AFTER_MARKET

    def test_get_trading_period_night(self, calendar: ChinaTradingCalendar) -> None:
        """测试夜盘."""
        # 2025-12-15 是周一，有夜盘
        dt = datetime(2025, 12, 15, 21, 30)
        assert calendar.get_trading_period(dt) == TradingPeriod.NIGHT

    def test_get_trading_period_closed(self, calendar: ChinaTradingCalendar) -> None:
        """测试休市."""
        # 2025-12-13 是周六
        dt = datetime(2025, 12, 13, 10, 0)
        assert calendar.get_trading_period(dt) == TradingPeriod.CLOSED


class TestTradingDaysRange:
    """交易日范围计算测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_get_trading_days_between(self, calendar: ChinaTradingCalendar) -> None:
        """测试获取日期范围内的交易日."""
        # 2025-12-15 周一 到 2025-12-19 周五
        start = date(2025, 12, 15)
        end = date(2025, 12, 19)
        trading_days = calendar.get_trading_days_between(start, end)
        assert len(trading_days) == 5
        assert trading_days[0] == date(2025, 12, 15)
        assert trading_days[-1] == date(2025, 12, 19)

    def test_count_trading_days(self, calendar: ChinaTradingCalendar) -> None:
        """测试计算交易日数量."""
        start = date(2025, 12, 15)
        end = date(2025, 12, 19)
        count = calendar.count_trading_days(start, end)
        assert count == 5

    def test_add_trading_days_forward(self, calendar: ChinaTradingCalendar) -> None:
        """测试向后增加交易日."""
        # 2025-12-15 周一 + 5个交易日 = 2025-12-22 周一（跳过周末）
        result = calendar.add_trading_days(date(2025, 12, 15), 5)
        assert result == date(2025, 12, 22)

    def test_add_trading_days_backward(self, calendar: ChinaTradingCalendar) -> None:
        """测试向前减少交易日."""
        # 2025-12-22 周一 - 5个交易日 = 2025-12-15 周一
        result = calendar.add_trading_days(date(2025, 12, 22), -5)
        assert result == date(2025, 12, 15)

    def test_add_trading_days_zero(self, calendar: ChinaTradingCalendar) -> None:
        """测试增加0个交易日."""
        result = calendar.add_trading_days(date(2025, 12, 16), 0)
        assert result == date(2025, 12, 16)


class TestConvenienceFunctions:
    """便捷函数测试."""

    RULE_ID = "CHINA.CALENDAR.TRADING_DAY"

    def test_get_default_calendar(self) -> None:
        """测试获取默认日历."""
        calendar1 = get_default_calendar()
        calendar2 = get_default_calendar()
        assert calendar1 is calendar2  # 单例

    def test_get_trading_day_function(self) -> None:
        """测试get_trading_day便捷函数."""
        dt = datetime(2025, 12, 16, 10, 0)
        trading_day = get_trading_day(dt)
        assert trading_day == date(2025, 12, 16)

    def test_is_trading_day_function(self) -> None:
        """测试is_trading_day便捷函数."""
        assert is_trading_day(date(2025, 12, 16)) is True
        assert is_trading_day(date(2025, 12, 13)) is False

    def test_is_trading_time_function(self) -> None:
        """测试is_trading_time便捷函数."""
        dt = datetime(2025, 12, 16, 10, 0)
        assert is_trading_time(dt) is True


class TestMilitaryRuleM15:
    """军规M15: 夜盘跨日处理测试."""

    RULE_ID = "M15.NIGHT_SESSION"

    @pytest.fixture
    def calendar(self) -> ChinaTradingCalendar:
        """创建测试用日历实例."""
        return ChinaTradingCalendar()

    def test_night_session_belongs_to_next_trading_day(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试夜盘归属下一交易日."""
        # 周一晚上21:30属于周二
        dt = datetime(2025, 12, 15, 21, 30)  # 周一晚上
        trading_day = calendar.get_trading_day(dt)
        assert trading_day == date(2025, 12, 16)  # 周二

    def test_early_morning_belongs_to_same_trading_day(
        self, calendar: ChinaTradingCalendar
    ) -> None:
        """测试凌晨夜盘归属同一交易日."""
        # 周二凌晨01:30属于周二
        dt = datetime(2025, 12, 16, 1, 30)
        trading_day = calendar.get_trading_day(dt)
        assert trading_day == date(2025, 12, 16)

    def test_friday_night_no_trading(self, calendar: ChinaTradingCalendar) -> None:
        """测试周五晚上没有夜盘."""
        # 周五晚上21:30不是交易时间
        dt = datetime(2025, 12, 19, 21, 30)  # 周五晚上
        assert calendar.is_trading_time(dt) is False

    def test_holiday_eve_no_night_session(self, calendar: ChinaTradingCalendar) -> None:
        """测试节假日前一天没有夜盘."""
        # 2024-12-31 是周二，下一天2025-01-01是元旦假期
        # 所以2024-12-31没有夜盘
        assert calendar.has_night_session_on_day(date(2024, 12, 31)) is False
