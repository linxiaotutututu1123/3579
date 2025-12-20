"""中国期货手续费计算器模块测试 (军规级 v4.0).

测试场景:
- CHINA.FEE.BY_VOLUME_CALC: 按手收费计算
- CHINA.FEE.BY_VALUE_CALC: 按金额收费计算
- CHINA.FEE.CLOSE_TODAY_CALC: 平今手续费计算

军规覆盖:
- M5: 成本先行
- M14: 平今平昨分离
"""

import pytest

from src.cost.china_fee_calculator import (
    ALL_FEE_CONFIGS,
    CFFEX_FEE_CONFIGS,
    ChinaFeeCalculator,
    FeeConfig,
    FeeResult,
    FeeType,
    TradeDirection,
    calculate_fee,
    estimate_cost,
    get_default_calculator,
)
from src.market.exchange_config import Exchange


class TestFeeTypeEnum:
    """手续费类型枚举测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    def test_fee_type_values(self) -> None:
        """测试手续费类型枚举值."""
        assert FeeType.FIXED.value == "按手"
        assert FeeType.RATIO.value == "按金额"
        assert FeeType.MIXED.value == "混合"


class TestTradeDirectionEnum:
    """交易方向枚举测试."""

    RULE_ID = "CHINA.FEE.CLOSE_TODAY_CALC"

    def test_trade_direction_values(self) -> None:
        """测试交易方向枚举值."""
        assert TradeDirection.OPEN.value == "开仓"
        assert TradeDirection.CLOSE.value == "平仓"
        assert TradeDirection.CLOSE_TODAY.value == "平今"


class TestFeeConfig:
    """手续费配置测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    def test_fee_config_ratio(self) -> None:
        """测试按金额收费配置."""
        config = FeeConfig(
            FeeType.RATIO,
            open_ratio=0.0001,
            close_ratio=0.0001,
            close_today_ratio=0.0002,
            multiplier=10,
        )
        assert config.fee_type == FeeType.RATIO
        assert config.open_ratio == 0.0001
        assert config.close_today_ratio == 0.0002

    def test_fee_config_fixed(self) -> None:
        """测试按手收费配置."""
        config = FeeConfig(
            FeeType.FIXED,
            open_fixed=3.0,
            close_fixed=3.0,
            close_today_fixed=0.0,
            multiplier=5,
        )
        assert config.fee_type == FeeType.FIXED
        assert config.open_fixed == 3.0
        assert config.close_today_fixed == 0.0

    def test_fee_config_immutable(self) -> None:
        """测试配置不可变."""
        config = FeeConfig(FeeType.RATIO)
        with pytest.raises(AttributeError):
            config.open_ratio = 0.0002  # type: ignore[misc]


class TestFeeResult:
    """手续费结果测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    def test_fee_result_creation(self) -> None:
        """测试手续费结果创建."""
        result = FeeResult(
            fee=35.0,
            fee_type=FeeType.RATIO,
            direction=TradeDirection.OPEN,
            volume=10,
            price=3500,
            value=350000,
            product="rb",
            exchange=Exchange.SHFE,
        )
        assert result.fee == 35.0
        assert result.product == "rb"
        assert result.exchange == Exchange.SHFE


class TestFeeConfigs:
    """费率配置数据测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    def test_all_configs_not_empty(self) -> None:
        """测试所有配置不为空."""
        assert len(ALL_FEE_CONFIGS) > 0

    def test_cffex_close_today_high(self) -> None:
        """测试中金所平今费率极高."""
        # IF平今费率是开仓的15倍
        if_config = CFFEX_FEE_CONFIGS["IF"]
        assert if_config.close_today_ratio == 0.000345
        assert if_config.open_ratio == 0.000023
        assert if_config.close_today_ratio / if_config.open_ratio == 15


class TestChinaFeeCalculator:
    """中国期货手续费计算器测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_get_config_lowercase(self, calculator: ChinaFeeCalculator) -> None:
        """测试小写品种代码获取配置."""
        config = calculator.get_config("rb")
        assert config is not None
        assert config.fee_type == FeeType.RATIO

    def test_get_config_uppercase(self, calculator: ChinaFeeCalculator) -> None:
        """测试大写品种代码获取配置."""
        config = calculator.get_config("IF")
        assert config is not None
        assert config.fee_type == FeeType.RATIO

    def test_get_config_not_found(self, calculator: ChinaFeeCalculator) -> None:
        """测试未知品种返回None."""
        config = calculator.get_config("UNKNOWN")
        assert config is None


class TestByVolumeCalc:
    """按手收费计算测试."""

    RULE_ID = "CHINA.FEE.BY_VOLUME_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_calc_fixed_fee_open(self, calculator: ChinaFeeCalculator) -> None:
        """测试按手收费开仓."""
        # 铝 (al) 按手收费 3元/手
        result = calculator.calculate("al2501", 20000, 10, "open")
        assert result.fee == 30.0  # 10手 × 3元
        assert result.fee_type == FeeType.FIXED

    def test_calc_fixed_fee_close(self, calculator: ChinaFeeCalculator) -> None:
        """测试按手收费平仓."""
        result = calculator.calculate("al2501", 20000, 10, "close")
        assert result.fee == 30.0  # 10手 × 3元

    def test_calc_fixed_fee_close_today_zero(
        self, calculator: ChinaFeeCalculator
    ) -> None:
        """测试按手收费平今免费."""
        # 铝平今免费
        result = calculator.calculate("al2501", 20000, 10, "close_today")
        assert result.fee == 0.0


class TestByValueCalc:
    """按金额收费计算测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_calc_ratio_fee_rb(self, calculator: ChinaFeeCalculator) -> None:
        """测试螺纹钢按金额收费."""
        # rb 费率 0.0001，乘数 10
        # 3500 × 10 × 10 × 0.0001 = 35
        result = calculator.calculate("rb2501", 3500, 10, "open")
        assert result.fee == 35.0
        assert result.fee_type == FeeType.RATIO

    def test_calc_ratio_fee_au(self, calculator: ChinaFeeCalculator) -> None:
        """测试黄金按金额收费."""
        # au 费率 0.00002，乘数 1000
        # 450 × 10 × 1000 × 0.00002 = 90
        result = calculator.calculate("au2512", 450, 10, "open")
        assert result.fee == 90.0

    def test_calc_ratio_fee_i(self, calculator: ChinaFeeCalculator) -> None:
        """测试铁矿石按金额收费."""
        # i 费率 0.0001，乘数 100
        # 900 × 10 × 100 × 0.0001 = 90
        result = calculator.calculate("i2501", 900, 10, "open")
        assert result.fee == 90.0


class TestCloseTodayCalc:
    """平今手续费计算测试."""

    RULE_ID = "CHINA.FEE.CLOSE_TODAY_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_cffex_close_today_high(self, calculator: ChinaFeeCalculator) -> None:
        """测试中金所平今费率极高."""
        # IF 平今费率 0.000345，乘数 300
        # 4000 × 1 × 300 × 0.000345 = 414
        result = calculator.calculate("IF2501", 4000, 1, "close_today")
        assert result.fee == 414.0
        assert result.fee_type == FeeType.RATIO

    def test_cffex_open_vs_close_today(self, calculator: ChinaFeeCalculator) -> None:
        """测试中金所开仓与平今费率差异."""
        open_result = calculator.calculate("IF2501", 4000, 1, "open")
        close_today_result = calculator.calculate("IF2501", 4000, 1, "close_today")
        # 平今是开仓的15倍
        assert close_today_result.fee == open_result.fee * 15

    def test_ma_close_today_higher(self, calculator: ChinaFeeCalculator) -> None:
        """测试甲醇平今费率更高."""
        # MA 开仓2元，平今6元
        open_result = calculator.calculate("MA2501", 2500, 10, "open")
        close_today_result = calculator.calculate("MA2501", 2500, 10, "close_today")
        assert open_result.fee == 20.0
        assert close_today_result.fee == 60.0

    def test_close_vs_close_today(self, calculator: ChinaFeeCalculator) -> None:
        """测试平仓与平今费率差异."""
        # rb 平仓和平今费率相同
        close_result = calculator.calculate("rb2501", 3500, 10, "close")
        close_today_result = calculator.calculate("rb2501", 3500, 10, "close_today")
        assert close_result.fee == close_today_result.fee


class TestExtractProduct:
    """品种代码提取测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_extract_product_lower(self, calculator: ChinaFeeCalculator) -> None:
        """测试小写合约代码."""
        assert calculator._extract_product("rb2501") == "rb"

    def test_extract_product_upper(self, calculator: ChinaFeeCalculator) -> None:
        """测试大写合约代码."""
        assert calculator._extract_product("IF2501") == "IF"

    def test_extract_product_mixed(self, calculator: ChinaFeeCalculator) -> None:
        """测试混合大小写合约代码."""
        assert calculator._extract_product("MA2501") == "MA"

    def test_extract_product_no_number(self, calculator: ChinaFeeCalculator) -> None:
        """测试无数字的合约代码."""
        assert calculator._extract_product("rb") == "rb"


class TestParseDirection:
    """方向解析测试."""

    RULE_ID = "CHINA.FEE.CLOSE_TODAY_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_parse_direction_open(self, calculator: ChinaFeeCalculator) -> None:
        """测试解析开仓."""
        assert calculator._parse_direction("open") == TradeDirection.OPEN
        assert calculator._parse_direction("开仓") == TradeDirection.OPEN
        assert calculator._parse_direction("buy") == TradeDirection.OPEN

    def test_parse_direction_close(self, calculator: ChinaFeeCalculator) -> None:
        """测试解析平仓."""
        assert calculator._parse_direction("close") == TradeDirection.CLOSE
        assert calculator._parse_direction("平仓") == TradeDirection.CLOSE

    def test_parse_direction_close_today(
        self, calculator: ChinaFeeCalculator
    ) -> None:
        """测试解析平今."""
        assert calculator._parse_direction("close_today") == TradeDirection.CLOSE_TODAY
        assert calculator._parse_direction("平今") == TradeDirection.CLOSE_TODAY
        assert calculator._parse_direction("closetoday") == TradeDirection.CLOSE_TODAY


class TestRoundTrip:
    """往返交易成本测试."""

    RULE_ID = "CHINA.FEE.CLOSE_TODAY_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_round_trip_intraday(self, calculator: ChinaFeeCalculator) -> None:
        """测试日内往返交易成本."""
        # rb 开仓35 + 平今35 = 70
        cost = calculator.estimate_round_trip("rb2501", 3500, 10, is_intraday=True)
        assert cost == 70.0

    def test_round_trip_overnight(self, calculator: ChinaFeeCalculator) -> None:
        """测试隔夜往返交易成本."""
        # rb 开仓35 + 平仓35 = 70
        cost = calculator.estimate_round_trip("rb2501", 3500, 10, is_intraday=False)
        assert cost == 70.0

    def test_round_trip_cffex_intraday_expensive(
        self, calculator: ChinaFeeCalculator
    ) -> None:
        """测试中金所日内交易成本极高."""
        # IF 开仓27.6 + 平今414 = 441.6
        intraday_cost = calculator.estimate_round_trip(
            "IF2501", 4000, 1, is_intraday=True
        )
        overnight_cost = calculator.estimate_round_trip(
            "IF2501", 4000, 1, is_intraday=False
        )
        # 日内成本远高于隔夜
        assert intraday_cost > overnight_cost * 5


class TestFeeRateInfo:
    """费率信息测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_get_fee_rate_info_known(self, calculator: ChinaFeeCalculator) -> None:
        """测试获取已知品种费率信息."""
        info = calculator.get_fee_rate_info("rb")
        assert info["product"] == "rb"
        assert info["fee_type"] == "按金额"
        assert info["multiplier"] == 10

    def test_get_fee_rate_info_unknown(self, calculator: ChinaFeeCalculator) -> None:
        """测试获取未知品种费率信息."""
        info = calculator.get_fee_rate_info("UNKNOWN")
        assert info["fee_type"] == "默认"
        assert info["open_rate"] == 0.0001


class TestConvenienceFunctions:
    """便捷函数测试."""

    RULE_ID = "CHINA.FEE.BY_VALUE_CALC"

    def test_get_default_calculator(self) -> None:
        """测试获取默认计算器."""
        calc1 = get_default_calculator()
        calc2 = get_default_calculator()
        assert calc1 is calc2  # 单例

    def test_calculate_fee_function(self) -> None:
        """测试calculate_fee便捷函数."""
        fee = calculate_fee("rb2501", 3500, 10, "open")
        assert fee == 35.0

    def test_estimate_cost_function(self) -> None:
        """测试estimate_cost便捷函数."""
        cost = estimate_cost("rb2501", 3500, 10, is_intraday=True)
        assert cost == 70.0


class TestMilitaryRuleM5:
    """军规M5: 成本先行测试."""

    RULE_ID = "M5.COST_FIRST"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_fee_calculation_accurate(self, calculator: ChinaFeeCalculator) -> None:
        """测试手续费计算精确性."""
        # 验证多个品种的计算准确性
        result_rb = calculator.calculate("rb2501", 3500, 10, "open")
        result_if = calculator.calculate("IF2501", 4000, 1, "open")
        result_al = calculator.calculate("al2501", 20000, 10, "open")

        # 结果应该是精确到分
        assert result_rb.fee == 35.0
        assert result_if.fee == 27.6
        assert result_al.fee == 30.0


class TestMilitaryRuleM14:
    """军规M14: 平今平昨分离测试."""

    RULE_ID = "M14.CLOSE_TODAY_SEPARATION"

    @pytest.fixture
    def calculator(self) -> ChinaFeeCalculator:
        """创建测试用计算器实例."""
        return ChinaFeeCalculator()

    def test_close_today_different_from_close(
        self, calculator: ChinaFeeCalculator
    ) -> None:
        """测试平今与平昨费率区分."""
        # CFFEX平今费率是平昨的15倍
        close_result = calculator.calculate("IF2501", 4000, 1, "close")
        close_today_result = calculator.calculate("IF2501", 4000, 1, "close_today")

        assert close_today_result.direction == TradeDirection.CLOSE_TODAY
        assert close_result.direction == TradeDirection.CLOSE
        assert close_today_result.fee != close_result.fee

    def test_direction_correctly_recorded(
        self, calculator: ChinaFeeCalculator
    ) -> None:
        """测试交易方向正确记录."""
        open_result = calculator.calculate("rb2501", 3500, 10, "open")
        close_result = calculator.calculate("rb2501", 3500, 10, "close")
        close_today_result = calculator.calculate("rb2501", 3500, 10, "close_today")

        assert open_result.direction == TradeDirection.OPEN
        assert close_result.direction == TradeDirection.CLOSE
        assert close_today_result.direction == TradeDirection.CLOSE_TODAY
