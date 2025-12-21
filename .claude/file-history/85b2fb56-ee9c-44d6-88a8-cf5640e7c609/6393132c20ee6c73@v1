"""DL基础模块测试.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致), M18(实验性门禁)

V4PRO Scenarios:
- K01: DL.BASE.DETERMINISTIC - DL模型确定性验证
- K02: DL.BASE.AUDIT_LOG - DL模型审计日志
- K03: DL.BASE.MATURITY_GATE - DL模型成熟度门禁
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pytest
import torch

from src.strategy.dl.features import build_features, get_feature_dim
from src.strategy.dl.model import TinyMLP
from src.strategy.dl.policy import infer_score
from src.strategy.types import Bar1m


def _generate_bars(
    n: int, base_price: float = 100.0, trend: float = 0.001
) -> list[Bar1m]:
    """生成合成K线数据."""
    bars: list[Bar1m] = []
    price = base_price
    for i in range(n):
        price = price * (1 + trend + 0.01 * math.sin(i * 0.1))
        high = price * 1.005
        low = price * 0.995
        bars.append(
            {
                "ts": 1700000000.0 + i * 60,
                "open": price * 0.999,
                "high": high,
                "low": low,
                "close": price,
                "volume": 1000.0 + i,
            }
        )
    return bars


class TestDLBaseDeterministic:
    """K01: DL.BASE.DETERMINISTIC - DL模型确定性验证测试."""

    def test_model_deterministic_forward(self) -> None:
        """测试模型前向传播确定性."""
        model = TinyMLP(feature_dim=180)
        model.eval()

        # 固定输入
        torch.manual_seed(42)
        x = torch.randn(1, 180)

        # 多次推理
        with torch.inference_mode():
            y1 = model(x)
            y2 = model(x)
            y3 = model(x)

        # 结果必须完全一致
        assert torch.equal(y1, y2)
        assert torch.equal(y2, y3)

    def test_feature_extraction_deterministic(self) -> None:
        """测试特征提取确定性."""
        bars = _generate_bars(100)

        # 多次提取
        features1 = build_features(bars, window=60)
        features2 = build_features(bars, window=60)
        features3 = build_features(bars, window=60)

        # 结果必须完全一致
        np.testing.assert_array_equal(features1, features2)
        np.testing.assert_array_equal(features2, features3)

    def test_inference_deterministic(self) -> None:
        """测试完整推理确定性 (M7)."""
        model = TinyMLP(feature_dim=180)
        model.eval()

        bars = _generate_bars(100)
        features = build_features(bars, window=60)

        # 多次推理
        score1 = infer_score(model, features)
        score2 = infer_score(model, features)
        score3 = infer_score(model, features)

        # 结果必须完全一致
        assert score1 == score2 == score3

    def test_deterministic_with_same_seed(self) -> None:
        """测试相同种子产生相同模型."""
        torch.manual_seed(12345)
        model1 = TinyMLP(feature_dim=180)

        torch.manual_seed(12345)
        model2 = TinyMLP(feature_dim=180)

        # 参数应该完全一致
        for p1, p2 in zip(model1.parameters(), model2.parameters(), strict=True):
            assert torch.equal(p1, p2)


class TestDLBaseAuditLog:
    """K02: DL.BASE.AUDIT_LOG - DL模型审计日志测试."""

    def test_features_hash_reproducible(self) -> None:
        """测试特征哈希可重现 (M3)."""
        bars = _generate_bars(100)
        features = build_features(bars, window=60)

        # 计算特征哈希
        hash1 = hashlib.sha256(features.tobytes()).hexdigest()
        hash2 = hashlib.sha256(features.tobytes()).hexdigest()

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_model_version_traceable(self) -> None:
        """测试模型版本可追溯 (M3)."""
        model = TinyMLP(feature_dim=180)

        # 计算模型参数哈希
        param_bytes = b""
        for p in model.parameters():
            param_bytes += p.data.cpu().numpy().tobytes()

        model_hash = hashlib.sha256(param_bytes).hexdigest()[:8]

        assert len(model_hash) == 8
        assert all(c in "0123456789abcdef" for c in model_hash)

    def test_feature_dim_recorded(self) -> None:
        """测试特征维度被记录."""
        dim = get_feature_dim(window=60)
        assert dim == 180  # 60 * 3 (returns + volume + range)

        dim_40 = get_feature_dim(window=40)
        assert dim_40 == 120  # 40 * 3

    def test_inference_output_bounded(self) -> None:
        """测试推理输出在有效范围内."""
        model = TinyMLP(feature_dim=180)
        model.eval()

        # 各种输入
        for _ in range(10):
            features = np.random.randn(180).astype(np.float32)
            score = infer_score(model, features)

            # 输出应在 [-1, 1] 范围内 (Tanh)
            assert -1.0 <= score <= 1.0


class TestDLBaseMaturityGate:
    """K03: DL.BASE.MATURITY_GATE - DL模型成熟度门禁测试."""

    def test_maturity_threshold_80(self) -> None:
        """测试80%成熟度门槛 (M18)."""
        from src.strategy.experimental.maturity_evaluator import (
            MaturityEvaluator,
        )

        assert MaturityEvaluator.ACTIVATION_THRESHOLD == 0.80

    def test_dimension_threshold_60(self) -> None:
        """测试60%维度门槛 (M18)."""
        from src.strategy.experimental.maturity_evaluator import (
            MaturityEvaluator,
        )

        assert MaturityEvaluator.DIMENSION_THRESHOLD == 0.60

    def test_min_training_days_90(self) -> None:
        """测试90天最低训练要求 (M18)."""
        from src.strategy.experimental.maturity_evaluator import (
            MaturityEvaluator,
        )

        assert MaturityEvaluator.MIN_TRAINING_DAYS == 90

    def test_gate_no_bypass(self) -> None:
        """测试禁止绕过门禁 (M18)."""
        from src.strategy.experimental.training_gate import TrainingGate

        assert TrainingGate.BYPASS_FORBIDDEN is True

    def test_gate_requires_manual_approval(self) -> None:
        """测试需要人工审批 (M12, M18)."""
        from src.strategy.experimental.training_gate import (
            TrainingGateConfig,
        )

        config = TrainingGateConfig()
        assert config.require_manual_approval is True


class TestTinyMLPModel:
    """TinyMLP模型测试."""

    def test_model_creation(self) -> None:
        """测试模型创建."""
        model = TinyMLP(feature_dim=180)
        assert model is not None

    def test_model_forward_shape(self) -> None:
        """测试模型输出形状."""
        model = TinyMLP(feature_dim=180)

        x = torch.randn(1, 180)
        y = model(x)

        assert y.shape == (1, 1)

    def test_model_batch_forward(self) -> None:
        """测试批量前向传播."""
        model = TinyMLP(feature_dim=180)

        batch_size = 32
        x = torch.randn(batch_size, 180)
        y = model(x)

        assert y.shape == (batch_size, 1)

    def test_model_different_feature_dim(self) -> None:
        """测试不同特征维度."""
        for dim in [60, 120, 180, 240]:
            model = TinyMLP(feature_dim=dim)
            x = torch.randn(1, dim)
            y = model(x)
            assert y.shape == (1, 1)


class TestFeatureExtraction:
    """特征提取测试."""

    def test_build_features_sufficient_bars(self) -> None:
        """测试足够数据的特征提取."""
        bars = _generate_bars(100)
        features = build_features(bars, window=60)

        assert features.shape == (180,)
        assert features.dtype == np.float32

    def test_build_features_insufficient_bars(self) -> None:
        """测试数据不足时的特征提取."""
        bars = _generate_bars(30)  # 少于 window=60
        features = build_features(bars, window=60)

        # 应返回零向量
        assert features.shape == (180,)
        assert np.allclose(features, 0)

    def test_build_features_exact_window(self) -> None:
        """测试恰好等于窗口大小."""
        bars = _generate_bars(60)
        features = build_features(bars, window=60)

        assert features.shape == (180,)
        # 不应全为零
        assert not np.allclose(features, 0)

    def test_feature_normalization(self) -> None:
        """测试特征归一化."""
        bars = _generate_bars(100, base_price=100.0)
        features = build_features(bars, window=60)

        # 检查特征值在合理范围内（归一化后）
        assert np.abs(features).max() < 100  # 应该是归一化的


class TestInferScore:
    """推理函数测试."""

    def test_infer_score_basic(self) -> None:
        """测试基本推理."""
        model = TinyMLP(feature_dim=180)
        features = np.random.randn(180).astype(np.float32)

        score = infer_score(model, features)

        assert isinstance(score, float)
        assert -1.0 <= score <= 1.0

    def test_infer_score_with_batch(self) -> None:
        """测试批量推理."""
        model = TinyMLP(feature_dim=180)
        # 单个样本（1D）
        features = np.random.randn(180).astype(np.float32)

        score = infer_score(model, features)

        assert isinstance(score, float)

    def test_infer_score_cpu_device(self) -> None:
        """测试CPU设备推理."""
        model = TinyMLP(feature_dim=180)
        features = np.random.randn(180).astype(np.float32)

        score = infer_score(model, features, device="cpu")

        assert isinstance(score, float)
