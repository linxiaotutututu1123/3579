"""
风险归因模块测试 (军规级 v4.0).

测试覆盖:
- M19: 风险归因 - 每笔亏损必须有归因分析

场景覆盖:
- RISK.ATTRIBUTION.LOSS_EXPLAIN: 亏损归因分析
- RISK.ATTRIBUTION.FACTOR_DECOMPOSE: 因子分解
- RISK.ATTRIBUTION.SHAP_INTEGRATION: SHAP集成
"""

from __future__ import annotations

import numpy as np
import pytest

from src.risk.attribution import (
    AttributionMethod,
    AttributionResult,
    FactorContribution,
    FactorType,
    RiskAttributionEngine,
    attribute_trade_loss,
    create_attribution_engine,
    get_factor_summary,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def engine() -> RiskAttributionEngine:
    """创建默认归因引擎."""
    return RiskAttributionEngine(window=60)


@pytest.fixture
def sample_features() -> np.ndarray:
    """创建示例特征向量 (180维: 60 returns + 60 volumes + 60 ranges)."""
    np.random.seed(42)
    returns = np.random.randn(60) * 0.01  # 收益率
    volumes = np.random.randn(60) * 0.5  # 成交量
    ranges = np.random.randn(60) * 0.02  # 波动幅度
    return np.concatenate([returns, volumes, ranges]).astype(np.float32)


@pytest.fixture
def loss_features() -> np.ndarray:
    """创建亏损场景特征 (动量负向)."""
    np.random.seed(123)
    # 负动量
    returns = np.random.randn(60) * 0.01 - 0.02
    # 高成交量
    volumes = np.random.randn(60) * 0.5 + 1.0
    # 高波动
    ranges = np.random.randn(60) * 0.02 + 0.05
    return np.concatenate([returns, volumes, ranges]).astype(np.float32)


@pytest.fixture
def profit_features() -> np.ndarray:
    """创建盈利场景特征 (动量正向)."""
    np.random.seed(456)
    # 正动量
    returns = np.random.randn(60) * 0.01 + 0.02
    # 正常成交量
    volumes = np.random.randn(60) * 0.3
    # 低波动
    ranges = np.random.randn(60) * 0.01
    return np.concatenate([returns, volumes, ranges]).astype(np.float32)


# ============================================================
# 基础功能测试
# ============================================================


class TestRiskAttributionEngine:
    """归因引擎测试."""

    def test_init_default(self) -> None:
        """测试默认初始化."""
        engine = RiskAttributionEngine()
        assert engine.window == 60
        assert engine.method == AttributionMethod.SIMPLE
        assert engine.attribution_count == 0
        assert engine.loss_attribution_count == 0

    def test_init_custom_window(self) -> None:
        """测试自定义窗口."""
        engine = RiskAttributionEngine(window=30)
        assert engine.window == 30

    def test_init_custom_method(self) -> None:
        """测试自定义方法."""
        engine = RiskAttributionEngine(method=AttributionMethod.GRADIENT)
        assert engine.method == AttributionMethod.GRADIENT

    def test_attribute_trade_increments_count(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试归因计数递增."""
        assert engine.attribution_count == 0

        engine.attribute_trade("T001", "rb2501", 100.0, sample_features)
        assert engine.attribution_count == 1
        assert engine.loss_attribution_count == 0

        engine.attribute_trade("T002", "rb2501", -50.0, sample_features)
        assert engine.attribution_count == 2
        assert engine.loss_attribution_count == 1

    def test_attribute_trade_returns_result(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试归因返回结果."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)

        assert isinstance(result, AttributionResult)
        assert result.trade_id == "T001"
        assert result.symbol == "rb2501"
        assert result.pnl == -100.0
        assert result.is_loss is True

    def test_get_statistics(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试统计信息."""
        engine.attribute_trade("T001", "rb2501", 100.0, sample_features)
        engine.attribute_trade("T002", "rb2501", -50.0, sample_features)

        stats = engine.get_statistics()
        assert stats["attribution_count"] == 2
        assert stats["loss_attribution_count"] == 1
        assert stats["loss_rate"] == 0.5
        assert stats["method"] == "SIMPLE"
        assert stats["window"] == 60

    def test_reset_statistics(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试重置统计."""
        engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        assert engine.attribution_count == 1

        engine.reset_statistics()
        assert engine.attribution_count == 0
        assert engine.loss_attribution_count == 0


# ============================================================
# 亏损归因测试 (M19 军规核心)
# ============================================================


class TestLossAttribution:
    """亏损归因测试 (M19)."""

    def test_loss_attribution_basic(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试基础亏损归因."""
        result = engine.attribute_loss("T001", "rb2501", 1000.0, loss_features)

        assert result.is_loss is True
        assert result.pnl < 0
        assert len(result.factors) > 0
        assert result.primary_factor is not None
        assert result.explanation != ""

    def test_loss_attribution_has_factors(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试亏损归因包含因子."""
        result = engine.attribute_loss("T001", "rb2501", 500.0, loss_features)

        # 应该有三个因子: MOMENTUM, VOLUME, VOLATILITY
        factor_types = {f.factor_type for f in result.factors}
        assert FactorType.MOMENTUM in factor_types
        assert FactorType.VOLUME in factor_types
        assert FactorType.VOLATILITY in factor_types

    def test_loss_attribution_factor_importance_sum(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试因子重要性之和约等于1."""
        result = engine.attribute_loss("T001", "rb2501", 500.0, loss_features)

        total_importance = sum(f.importance for f in result.factors)
        assert abs(total_importance - 1.0) < 0.01  # 允许小误差

    def test_loss_attribution_negative_contributions(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试亏损时贡献为负."""
        result = engine.attribute_loss("T001", "rb2501", 500.0, loss_features)

        # 亏损时主要贡献应为负
        negative_count = sum(1 for f in result.factors if f.contribution < 0)
        assert negative_count > 0

    def test_loss_attribution_audit_dict(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试审计字典格式."""
        result = engine.attribute_loss("T001", "rb2501", 500.0, loss_features)
        audit_dict = result.to_audit_dict()

        # 验证必需字段
        assert "trade_id" in audit_dict
        assert "symbol" in audit_dict
        assert "pnl" in audit_dict
        assert "is_loss" in audit_dict
        assert "primary_factor" in audit_dict
        assert "factors" in audit_dict
        assert "explanation" in audit_dict
        assert "timestamp" in audit_dict

        # 验证字段类型
        assert isinstance(audit_dict["factors"], list)
        assert isinstance(audit_dict["is_loss"], bool)
        assert audit_dict["is_loss"] is True

    def test_loss_amount_positive_converted(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试正数亏损金额被转换为负数."""
        result = engine.attribute_loss("T001", "rb2501", 500.0, loss_features)
        assert result.pnl == -500.0

        result2 = engine.attribute_loss("T002", "rb2501", -500.0, loss_features)
        assert result2.pnl == -500.0


# ============================================================
# 因子分解测试
# ============================================================


class TestFactorDecomposition:
    """因子分解测试."""

    def test_three_factor_groups(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试三因子分组."""
        result = engine.attribute_trade("T001", "rb2501", 100.0, sample_features)

        assert len(result.factors) == 3
        factor_types = [f.factor_type for f in result.factors]
        assert FactorType.MOMENTUM in factor_types
        assert FactorType.VOLUME in factor_types
        assert FactorType.VOLATILITY in factor_types

    def test_factor_contribution_range(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试因子贡献范围."""
        result = engine.attribute_trade("T001", "rb2501", 100.0, sample_features)

        for factor in result.factors:
            assert -1.0 <= factor.contribution <= 1.0
            assert 0.0 <= factor.importance <= 1.0

    def test_primary_factor_identification(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试主因子识别."""
        result = engine.attribute_trade("T001", "rb2501", 100.0, sample_features)

        # 主因子应该是重要性最高的
        max_importance = max(f.importance for f in result.factors)
        primary = next(
            f for f in result.factors if f.factor_type == result.primary_factor
        )
        assert primary.importance == max_importance

    def test_feature_importances_dict(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试特征重要性字典."""
        result = engine.attribute_trade("T001", "rb2501", 100.0, sample_features)

        assert "returns" in result.feature_importances
        assert "volumes" in result.feature_importances
        assert "ranges" in result.feature_importances

        # 验证值范围
        for value in result.feature_importances.values():
            assert 0.0 <= value <= 1.0


# ============================================================
# 盈利 vs 亏损对比测试
# ============================================================


class TestProfitVsLoss:
    """盈利与亏损对比测试."""

    def test_profit_is_not_loss(
        self, engine: RiskAttributionEngine, profit_features: np.ndarray
    ) -> None:
        """测试盈利判定."""
        result = engine.attribute_trade("T001", "rb2501", 500.0, profit_features)
        assert result.is_loss is False

    def test_loss_is_loss(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试亏损判定."""
        result = engine.attribute_trade("T001", "rb2501", -500.0, loss_features)
        assert result.is_loss is True

    def test_zero_pnl_not_loss(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试零盈亏不是亏损."""
        result = engine.attribute_trade("T001", "rb2501", 0.0, sample_features)
        assert result.is_loss is False


# ============================================================
# 梯度归因测试
# ============================================================


class TestGradientAttribution:
    """梯度归因测试."""

    def test_gradient_method_with_model_output(
        self, sample_features: np.ndarray
    ) -> None:
        """测试带模型输出的梯度归因."""
        engine = RiskAttributionEngine(method=AttributionMethod.GRADIENT)
        result = engine.attribute_trade(
            "T001", "rb2501", -100.0, sample_features, model_output=0.5
        )

        assert result.method == AttributionMethod.GRADIENT
        assert result.confidence == 0.8
        assert "model_output" in result.metadata

    def test_gradient_falls_back_without_model_output(
        self, sample_features: np.ndarray
    ) -> None:
        """测试无模型输出时回退到简单方法."""
        engine = RiskAttributionEngine(method=AttributionMethod.GRADIENT)
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)

        # 没有 model_output 时应使用简单方法
        assert result.method == AttributionMethod.SIMPLE


# ============================================================
# 解释生成测试
# ============================================================


class TestExplanationGeneration:
    """解释生成测试."""

    def test_explanation_contains_symbol(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试解释包含合约代码."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        assert "rb2501" in result.explanation

    def test_explanation_contains_loss_indicator(
        self, engine: RiskAttributionEngine, loss_features: np.ndarray
    ) -> None:
        """测试解释包含亏损指示."""
        result = engine.attribute_loss("T001", "rb2501", 500.0, loss_features)
        assert "亏损" in result.explanation

    def test_explanation_contains_profit_indicator(
        self, engine: RiskAttributionEngine, profit_features: np.ndarray
    ) -> None:
        """测试解释包含盈利指示."""
        result = engine.attribute_trade("T001", "rb2501", 500.0, profit_features)
        assert "盈利" in result.explanation

    def test_explanation_contains_primary_factor(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试解释包含主因子."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        assert "主要归因" in result.explanation


# ============================================================
# FactorContribution 测试
# ============================================================


class TestFactorContribution:
    """因子贡献测试."""

    def test_factor_contribution_frozen(self) -> None:
        """测试因子贡献不可变."""
        fc = FactorContribution(
            factor_type=FactorType.MOMENTUM,
            contribution=0.5,
            importance=0.3,
        )

        with pytest.raises(AttributeError):
            fc.contribution = 0.8  # type: ignore[misc]

    def test_factor_contribution_with_shap(self) -> None:
        """测试带SHAP值的因子贡献."""
        fc = FactorContribution(
            factor_type=FactorType.MOMENTUM,
            contribution=0.5,
            importance=0.3,
            shap_value=0.123,
            description="测试描述",
        )

        assert fc.shap_value == 0.123
        assert fc.description == "测试描述"


# ============================================================
# AttributionResult 测试
# ============================================================


class TestAttributionResult:
    """归因结果测试."""

    def test_to_audit_dict_format(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试审计字典格式正确."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        audit = result.to_audit_dict()

        # 验证数值精度
        assert isinstance(audit["primary_contribution"], float)
        assert isinstance(audit["confidence"], float)

        # 验证因子格式
        for factor in audit["factors"]:
            assert "type" in factor
            assert "contribution" in factor
            assert "importance" in factor


# ============================================================
# 便捷函数测试
# ============================================================


class TestConvenienceFunctions:
    """便捷函数测试."""

    def test_create_attribution_engine(self) -> None:
        """测试创建归因引擎."""
        engine = create_attribution_engine(window=30, use_shap=False)
        assert engine.window == 30
        assert engine._use_shap is False

    def test_attribute_trade_loss_function(self, loss_features: np.ndarray) -> None:
        """测试亏损归因便捷函数."""
        result = attribute_trade_loss(
            trade_id="T001",
            symbol="rb2501",
            loss_amount=500.0,
            features=loss_features,
        )

        assert result.is_loss is True
        assert result.pnl == -500.0
        assert len(result.factors) > 0

    def test_get_factor_summary(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试获取因子摘要."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        summary = get_factor_summary(result)

        assert "MOMENTUM" in summary
        assert "VOLUME" in summary
        assert "VOLATILITY" in summary


# ============================================================
# 边界条件测试
# ============================================================


class TestEdgeCases:
    """边界条件测试."""

    def test_zero_features(self, engine: RiskAttributionEngine) -> None:
        """测试零特征向量."""
        zero_features = np.zeros(180, dtype=np.float32)
        result = engine.attribute_trade("T001", "rb2501", -100.0, zero_features)

        # 应该能处理零特征
        assert result is not None
        assert result.trade_id == "T001"

    def test_very_small_pnl(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试极小盈亏."""
        result = engine.attribute_trade("T001", "rb2501", -0.01, sample_features)
        assert result.is_loss is True
        assert result.pnl == -0.01

    def test_very_large_pnl(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试极大盈亏."""
        result = engine.attribute_trade("T001", "rb2501", -1000000.0, sample_features)
        assert result.is_loss is True
        assert "1000000" in result.explanation or "¥" in result.explanation

    def test_custom_window_features(self) -> None:
        """测试自定义窗口特征."""
        engine = RiskAttributionEngine(window=30)
        features = np.random.randn(90).astype(np.float32)  # 30*3 = 90

        result = engine.attribute_trade("T001", "rb2501", -100.0, features)
        assert result is not None
        assert len(result.factors) == 3


# ============================================================
# 多合约测试
# ============================================================


class TestMultipleSymbols:
    """多合约测试."""

    def test_different_symbols(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试不同合约."""
        result1 = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        result2 = engine.attribute_trade("T002", "hc2501", -200.0, sample_features)
        result3 = engine.attribute_trade("T003", "i2501", -300.0, sample_features)

        assert result1.symbol == "rb2501"
        assert result2.symbol == "hc2501"
        assert result3.symbol == "i2501"

        assert engine.attribution_count == 3
        assert engine.loss_attribution_count == 3


# ============================================================
# 时间戳测试
# ============================================================


class TestTimestamp:
    """时间戳测试."""

    def test_timestamp_format(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试时间戳格式."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)

        # ISO 格式时间戳
        assert result.timestamp != ""
        assert "T" in result.timestamp  # ISO格式包含T
        assert "-" in result.timestamp  # 日期分隔符

    def test_audit_dict_timestamp(
        self, engine: RiskAttributionEngine, sample_features: np.ndarray
    ) -> None:
        """测试审计字典时间戳."""
        result = engine.attribute_trade("T001", "rb2501", -100.0, sample_features)
        audit = result.to_audit_dict()

        assert "timestamp" in audit
        assert audit["timestamp"] != ""
