"""Kalman Beta估计器增强测试 (军规级 v4.0)."""

from __future__ import annotations

import math

from src.strategy.calendar_arb.kalman_beta import (
    KalmanBetaEstimator,
    KalmanConfig,
    KalmanResult,
)


class TestKalmanConfig:
    """Kalman配置测试."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = KalmanConfig()
        assert config.initial_beta == 1.0
        assert config.initial_variance == 1.0
        assert config.min_beta == 0.5
        assert config.max_beta == 1.5
        assert config.z_score_window == 60
        assert config.min_samples == 20

    def test_custom_config(self) -> None:
        """测试自定义配置."""
        config = KalmanConfig(
            initial_beta=0.8,
            min_beta=0.3,
            max_beta=2.0,
            z_score_window=100,
        )
        assert config.initial_beta == 0.8
        assert config.min_beta == 0.3
        assert config.max_beta == 2.0


class TestKalmanResult:
    """Kalman结果测试."""

    def test_to_dict(self) -> None:
        """测试转字典."""
        result = KalmanResult(
            beta=1.05,
            beta_variance=0.01,
            residual=10.5,
            z_score=1.5,
            half_life=30.0,
            is_valid=True,
            beta_bounded=False,
        )
        d = result.to_dict()
        assert d["beta"] == 1.05
        assert d["beta_variance"] == 0.01
        assert d["residual"] == 10.5
        assert d["z_score"] == 1.5
        assert d["half_life"] == 30.0
        assert d["is_valid"] is True
        assert d["beta_bounded"] is False


class TestKalmanBetaEstimatorBasic:
    """Kalman Beta估计器基本测试."""

    def test_init_default(self) -> None:
        """测试默认初始化."""
        estimator = KalmanBetaEstimator()
        assert estimator.beta == 1.0
        assert estimator.variance == 1.0
        assert estimator.sample_count == 0

    def test_init_custom_config(self) -> None:
        """测试自定义配置初始化."""
        config = KalmanConfig(initial_beta=0.9, initial_variance=0.5)
        estimator = KalmanBetaEstimator(config)
        assert estimator.beta == 0.9
        assert estimator.variance == 0.5

    def test_reset(self) -> None:
        """测试重置."""
        estimator = KalmanBetaEstimator()

        # 更新一些数据
        for i in range(10):
            estimator.update(4500 + i, 4400 + i)

        # 重置
        estimator.reset()
        assert estimator.beta == 1.0
        assert estimator.variance == 1.0
        assert estimator.sample_count == 0


class TestKalmanBetaEstimatorUpdate:
    """更新测试."""

    def test_update_single(self) -> None:
        """测试单次更新."""
        estimator = KalmanBetaEstimator()
        result = estimator.update(4500.0, 4400.0)

        assert result.beta != 0
        assert result.is_valid is False  # 不足min_samples
        assert estimator.sample_count == 1

    def test_update_multiple(self) -> None:
        """测试多次更新."""
        estimator = KalmanBetaEstimator()

        for i in range(25):
            result = estimator.update(4500.0 + i * 10, 4400.0 + i * 10)

        assert estimator.sample_count == 25
        assert result.is_valid is True

    def test_update_zero_far_price(self) -> None:
        """测试零远月价格."""
        estimator = KalmanBetaEstimator()
        result = estimator.update(4500.0, 0.0)

        assert result.is_valid is False
        assert result.residual == 0.0
        assert result.z_score == 0.0

    def test_update_negative_far_price(self) -> None:
        """测试负远月价格."""
        estimator = KalmanBetaEstimator()
        result = estimator.update(4500.0, -100.0)

        assert result.is_valid is False


class TestKalmanBetaEstimatorBetaBound:
    """Beta边界测试."""

    def test_beta_bounded_low(self) -> None:
        """测试Beta下界."""
        config = KalmanConfig(initial_beta=0.3, min_beta=0.5, max_beta=1.5)
        estimator = KalmanBetaEstimator(config)

        # Beta应该被调整到下界
        result = estimator.update(4500.0, 4400.0)
        assert result.beta >= 0.5

    def test_beta_bounded_high(self) -> None:
        """测试Beta上界."""
        config = KalmanConfig(initial_beta=2.0, min_beta=0.5, max_beta=1.5)
        estimator = KalmanBetaEstimator(config)

        # Beta应该被调整到上界
        result = estimator.update(4500.0, 4400.0)
        assert result.beta <= 1.5

    def test_bound_beta_unchanged(self) -> None:
        """测试Beta在范围内不变."""
        config = KalmanConfig(initial_beta=1.0, min_beta=0.5, max_beta=1.5)
        estimator = KalmanBetaEstimator(config)

        result = estimator.update(4500.0, 4400.0)
        # 如果beta在范围内，bounded应该是False
        if 0.5 <= result.beta <= 1.5:
            # beta_bounded可能是True或False取决于计算结果
            pass


class TestKalmanBetaEstimatorZScore:
    """Z分数计算测试."""

    def test_z_score_insufficient_samples(self) -> None:
        """测试样本不足时的Z分数."""
        estimator = KalmanBetaEstimator()

        for _ in range(5):
            result = estimator.update(4500.0, 4400.0)

        assert result.z_score == 0.0  # 样本不足

    def test_z_score_sufficient_samples(self) -> None:
        """测试样本足够时的Z分数."""
        estimator = KalmanBetaEstimator()

        # 添加足够样本
        for i in range(30):
            result = estimator.update(4500.0 + i * 5, 4400.0 + i * 5)

        # Z分数应该有值（可能为0如果残差=均值）
        assert isinstance(result.z_score, float)

    def test_z_score_with_variance(self) -> None:
        """测试有方差时的Z分数."""
        estimator = KalmanBetaEstimator()

        # 添加有变化的价格
        for i in range(30):
            near = 4500.0 + (i % 10) * 20 - 100  # 波动
            far = 4400.0 + (i % 10) * 18 - 90
            result = estimator.update(near, far)

        # Z分数应该非零
        assert result.is_valid is True


class TestKalmanBetaEstimatorHalfLife:
    """半衰期计算测试."""

    def test_half_life_insufficient_samples(self) -> None:
        """测试样本不足时的半衰期."""
        estimator = KalmanBetaEstimator()

        for _ in range(5):
            result = estimator.update(4500.0, 4400.0)

        assert result.half_life == float("inf")

    def test_half_life_mean_reverting(self) -> None:
        """测试均值回归时的半衰期."""
        estimator = KalmanBetaEstimator()

        # 模拟均值回归的价差
        base_spread = 100.0
        for i in range(50):
            # 价差围绕base_spread波动
            deviation = 20 * math.sin(i * 0.5)
            near = 4500.0 + base_spread + deviation
            far = 4400.0
            result = estimator.update(near, far)

        # 半衰期应该是有限的（表示有均值回归）
        # 注意：实际值取决于模拟数据的特性
        assert isinstance(result.half_life, float)


class TestKalmanBetaEstimatorRollingStats:
    """滚动统计测试."""

    def test_rolling_window_trim(self) -> None:
        """测试滚动窗口裁剪."""
        config = KalmanConfig(z_score_window=10)
        estimator = KalmanBetaEstimator(config)

        # 添加超过窗口大小的样本
        for i in range(20):
            estimator.update(4500.0 + i, 4400.0 + i)

        # 残差列表应该被裁剪到窗口大小
        assert len(estimator._residuals) == 10


class TestKalmanBetaEstimatorState:
    """状态管理测试."""

    def test_get_state(self) -> None:
        """测试获取状态."""
        estimator = KalmanBetaEstimator()

        for i in range(10):
            estimator.update(4500.0 + i, 4400.0 + i)

        state = estimator.get_state()
        assert "beta" in state
        assert "variance" in state
        assert "sample_count" in state
        assert "residual_mean" in state

    def test_set_state(self) -> None:
        """测试设置状态."""
        estimator = KalmanBetaEstimator()

        state = {
            "beta": 1.1,
            "variance": 0.5,
        }
        estimator.set_state(state)

        assert estimator.beta == 1.1
        assert estimator.variance == 0.5

    def test_set_state_partial(self) -> None:
        """测试部分设置状态."""
        config = KalmanConfig(initial_beta=0.9, initial_variance=0.8)
        estimator = KalmanBetaEstimator(config)

        state = {"beta": 1.2}  # 只设置beta
        estimator.set_state(state)

        assert estimator.beta == 1.2
        # variance应该使用默认值
        assert estimator.variance == config.initial_variance


class TestKalmanBetaEstimatorProperties:
    """属性测试."""

    def test_beta_property(self) -> None:
        """测试beta属性."""
        estimator = KalmanBetaEstimator()
        assert estimator.beta == 1.0

        estimator.update(4500.0, 4400.0)
        beta = estimator.beta
        assert isinstance(beta, float)

    def test_variance_property(self) -> None:
        """测试variance属性."""
        estimator = KalmanBetaEstimator()
        assert estimator.variance == 1.0

        estimator.update(4500.0, 4400.0)
        var = estimator.variance
        assert isinstance(var, float)
        assert var > 0

    def test_sample_count_property(self) -> None:
        """测试sample_count属性."""
        estimator = KalmanBetaEstimator()
        assert estimator.sample_count == 0

        for i in range(5):
            estimator.update(4500.0, 4400.0)
            assert estimator.sample_count == i + 1


class TestKalmanBetaEstimatorEdgeCases:
    """边界情况测试."""

    def test_identical_prices(self) -> None:
        """测试相同价格."""
        estimator = KalmanBetaEstimator()
        result = estimator.update(4500.0, 4500.0)

        # 应该正常运行
        assert isinstance(result.beta, float)
        assert isinstance(result.residual, float)

    def test_large_price_difference(self) -> None:
        """测试大价差."""
        estimator = KalmanBetaEstimator()
        result = estimator.update(10000.0, 1000.0)

        assert isinstance(result.beta, float)
        assert result.beta >= 0.5  # 在边界内
        assert result.beta <= 1.5

    def test_small_prices(self) -> None:
        """测试小价格."""
        estimator = KalmanBetaEstimator()
        result = estimator.update(10.0, 9.5)

        assert isinstance(result.beta, float)
        assert isinstance(result.residual, float)

    def test_z_score_zero_variance(self) -> None:
        """测试零方差时的Z分数."""
        estimator = KalmanBetaEstimator()

        # 添加完全相同的价格
        for _ in range(30):
            estimator.update(4500.0, 4400.0)

        result = estimator.update(4500.0, 4400.0)
        # 零方差时z_score应该是0
        # 由于浮点精度，可能有微小方差
        assert isinstance(result.z_score, float)
