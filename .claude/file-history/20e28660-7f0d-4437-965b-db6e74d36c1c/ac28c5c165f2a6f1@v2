"""VaR计算器测试 (军规级 v4.0)."""


from src.risk.var_calculator import VaRCalculator, VaRResult


class TestVaRResult:
    """VaR结果测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        result = VaRResult(var=0.05, confidence=0.95, method="historical")
        d = result.to_dict()
        assert d["var"] == 0.05
        assert d["confidence"] == 0.95
        assert d["method"] == "historical"


class TestVaRCalculator:
    """VaR计算器测试."""

    def test_historical_var(self) -> None:
        """测试历史VaR."""
        calc = VaRCalculator()
        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
        result = calc.historical_var(returns, confidence=0.95)
        assert result.var > 0
        assert result.method == "historical"
        assert result.sample_size == 10

    def test_historical_var_empty(self) -> None:
        """测试空数据历史VaR."""
        calc = VaRCalculator()
        result = calc.historical_var([])
        assert result.var == 0.0

    def test_historical_var_single(self) -> None:
        """测试单数据历史VaR."""
        calc = VaRCalculator()
        result = calc.historical_var([0.01])
        assert result.var == 0.0

    def test_parametric_var(self) -> None:
        """测试参数VaR."""
        calc = VaRCalculator()
        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
        result = calc.parametric_var(returns, confidence=0.95)
        assert result.method == "parametric"
        assert "mean" in result.metadata
        assert "std" in result.metadata

    def test_parametric_var_empty(self) -> None:
        """测试空数据参数VaR."""
        calc = VaRCalculator()
        result = calc.parametric_var([])
        assert result.var == 0.0

    def test_monte_carlo_var(self) -> None:
        """测试蒙特卡洛VaR."""
        calc = VaRCalculator()
        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
        result = calc.monte_carlo_var(returns, confidence=0.95, simulations=100)
        assert result.method == "monte_carlo"
        assert result.metadata["simulations"] == 100

    def test_monte_carlo_var_empty(self) -> None:
        """测试空数据蒙特卡洛VaR."""
        calc = VaRCalculator()
        result = calc.monte_carlo_var([])
        assert result.var == 0.0

    def test_expected_shortfall(self) -> None:
        """测试预期尾部损失."""
        calc = VaRCalculator()
        returns = [-0.10, -0.05, -0.03, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07]
        es = calc.expected_shortfall(returns, confidence=0.95)
        assert es >= 0

    def test_default_confidence(self) -> None:
        """测试默认置信度."""
        calc = VaRCalculator(default_confidence=0.99)
        returns = [-0.05, -0.03, 0.01, 0.02, 0.03]
        result = calc.historical_var(returns)
        assert result.confidence == 0.99

    def test_norm_ppf_edge_cases(self) -> None:
        """测试正态分布逆CDF边界."""
        calc = VaRCalculator()
        assert calc._norm_ppf(0.0) == float("-inf")
        assert calc._norm_ppf(1.0) == float("inf")
        assert calc._norm_ppf(0.5) == 0.0

    def test_norm_ppf_low_p(self) -> None:
        """测试低概率正态逆CDF."""
        calc = VaRCalculator()
        z = calc._norm_ppf(0.01)
        assert z < -2

    def test_norm_ppf_high_p(self) -> None:
        """测试高概率正态逆CDF."""
        calc = VaRCalculator()
        z = calc._norm_ppf(0.99)
        assert z > 2

    def test_norm_pdf(self) -> None:
        """测试正态分布PDF."""
        calc = VaRCalculator()
        assert calc._norm_pdf(0) > 0.39
        assert calc._norm_pdf(0) < 0.40

    def test_calculate_expected_shortfall_edge(self) -> None:
        """测试预期尾部损失边界."""
        calc = VaRCalculator()
        assert calc._calculate_expected_shortfall([], 0) == 0.0
        assert calc._calculate_expected_shortfall([-0.1, -0.05, 0.0], 0) == 0.1


class TestVaRCalculatorIntegration:
    """VaR计算器集成测试."""

    def test_all_methods_consistent(self) -> None:
        """测试所有方法一致性."""
        calc = VaRCalculator()
        returns = [
            -0.08, -0.06, -0.04, -0.02, 0.00,
            0.02, 0.04, 0.06, 0.08, 0.10,
        ] * 10

        hist = calc.historical_var(returns)
        param = calc.parametric_var(returns)
        mc = calc.monte_carlo_var(returns, simulations=1000)

        # 所有方法应该返回正的VaR
        assert hist.var >= 0
        assert param.var >= 0
        assert mc.var >= 0
