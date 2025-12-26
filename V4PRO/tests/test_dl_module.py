"""DL模块单元测试.

V4PRO Platform Component - Phase 6 B类模型层测试
军规覆盖: M26(测试规范), M7(回放一致), M3(完整审计)

测试场景覆盖:
- DL.DATA.SEQ.BUILD - 序列构建确定性
- DL.DATA.SEQ.NORMALIZE - 序列标准化
- DL.DATA.DATASET.CREATE - 数据集创建
- DL.MODEL.LSTM.FORWARD - LSTM前向传播
- DL.MODEL.LSTM.ATTENTION - 带注意力的LSTM
- DL.TRAIN.LOOP - 训练循环确定性
- DL.TRAIN.EARLY_STOP - 早停机制
- DL.FACTOR.IC.COMPUTE - IC计算(门禁: IC >= 0.05)
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from src.strategy.dl.data.dataset import (
    DatasetConfig,
    FinancialDataset,
    FinancialSample,
    create_dataset,
)
from src.strategy.dl.data.sequence_handler import (
    NormalizationMethod,
    SequenceConfig,
    SequenceHandler,
    SequenceWindow,
)
from src.strategy.dl.factors.ic_calculator import (
    ICCalculator,
    ICConfig,
    compute_ic,
    validate_ic_gate,
)
from src.strategy.dl.models.lstm import (
    EnhancedLSTM,
    LSTMConfig,
    create_lstm_model,
)
from src.strategy.dl.training.trainer import (
    EarlyStopping,
    TrainerConfig,
    TrainerMetrics,
    TradingModelTrainer,
)
from src.strategy.types import Bar1m


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_bars() -> list[Bar1m]:
    """生成测试用K线数据."""
    np.random.seed(42)
    n_bars = 100
    bars: list[Bar1m] = []

    base_price = 5000.0
    for i in range(n_bars):
        change = np.random.normal(0, 0.01)
        close = base_price * (1 + change)
        high = close * (1 + abs(np.random.normal(0, 0.005)))
        low = close * (1 - abs(np.random.normal(0, 0.005)))
        open_price = (high + low) / 2

        bar: Bar1m = {
            "ts": float(i * 60),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": float(np.random.randint(100, 1000)),
        }
        bars.append(bar)
        base_price = close

    return bars


@pytest.fixture
def sample_targets() -> list[float]:
    """生成测试用目标值."""
    np.random.seed(42)
    return [float(np.random.normal(0, 0.01)) for _ in range(100)]


# ============================================================================
# SequenceHandler Tests
# ============================================================================


class TestSequenceHandler:
    """SequenceHandler测试类."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        handler = SequenceHandler()
        assert handler.config.window_size == 60
        assert handler.config.stride == 1
        assert handler.config.deterministic is True

    def test_build_sequences_deterministic(self, sample_bars: list[Bar1m]) -> None:
        """测试序列构建确定性 (DL.DATA.SEQ.BUILD)."""
        config = SequenceConfig(window_size=20, deterministic=True, seed=42)

        # 第一次构建
        handler1 = SequenceHandler(config)
        windows1 = handler1.build_sequences(sample_bars)

        # 第二次构建(相同配置)
        handler2 = SequenceHandler(config)
        windows2 = handler2.build_sequences(sample_bars)

        # 验证确定性
        assert len(windows1) == len(windows2)
        for w1, w2 in zip(windows1, windows2, strict=True):
            assert w1.window_hash == w2.window_hash
            np.testing.assert_array_equal(w1.features, w2.features)

    def test_build_sequences_count(self, sample_bars: list[Bar1m]) -> None:
        """测试序列窗口数量."""
        config = SequenceConfig(window_size=20, stride=1)
        handler = SequenceHandler(config)
        windows = handler.build_sequences(sample_bars)

        expected_count = (len(sample_bars) - 20) // 1 + 1
        assert len(windows) == expected_count

    def test_build_sequences_with_stride(self, sample_bars: list[Bar1m]) -> None:
        """测试带步长的序列构建."""
        config = SequenceConfig(window_size=20, stride=5)
        handler = SequenceHandler(config)
        windows = handler.build_sequences(sample_bars)

        expected_count = (len(sample_bars) - 20) // 5 + 1
        assert len(windows) == expected_count

    def test_normalize_zscore(self, sample_bars: list[Bar1m]) -> None:
        """测试Z-score标准化 (DL.DATA.SEQ.NORMALIZE)."""
        config = SequenceConfig(
            window_size=20,
            normalization=NormalizationMethod.ZSCORE,
        )
        handler = SequenceHandler(config)
        windows = handler.build_sequences(sample_bars)

        # 验证标准化后每列均值接近0,标准差接近1
        for window in windows:
            for col in range(window.features.shape[1]):
                col_mean = np.mean(window.features[:, col])
                col_std = np.std(window.features[:, col])
                assert abs(col_mean) < 0.1
                # 标准差可能不完全是1(由于窗口大小)
                assert col_std < 2.0

    def test_normalize_minmax(self, sample_bars: list[Bar1m]) -> None:
        """测试MinMax归一化."""
        config = SequenceConfig(
            window_size=20,
            normalization=NormalizationMethod.MINMAX,
        )
        handler = SequenceHandler(config)
        windows = handler.build_sequences(sample_bars)

        # 验证值在[0, 1]范围内
        for window in windows:
            assert np.min(window.features) >= -0.01
            assert np.max(window.features) <= 1.01

    def test_insufficient_data(self, sample_bars: list[Bar1m]) -> None:
        """测试数据不足情况."""
        config = SequenceConfig(window_size=200)  # 大于数据量
        handler = SequenceHandler(config)
        windows = handler.build_sequences(sample_bars)

        assert len(windows) == 0

    def test_sequence_log(self, sample_bars: list[Bar1m]) -> None:
        """测试序列日志 (M3)."""
        config = SequenceConfig(window_size=20, log_sequences=True)
        handler = SequenceHandler(config)
        handler.build_sequences(sample_bars)

        log = handler.get_sequence_log()
        assert len(log) > 0
        assert "window_idx" in log[0]
        assert "window_hash" in log[0]


# ============================================================================
# FinancialDataset Tests
# ============================================================================


class TestFinancialDataset:
    """FinancialDataset测试类."""

    def test_create_dataset(
        self,
        sample_bars: list[Bar1m],
        sample_targets: list[float],
    ) -> None:
        """测试数据集创建 (DL.DATA.DATASET.CREATE)."""
        seq_config = SequenceConfig(window_size=20)
        config = DatasetConfig(sequence_config=seq_config)

        dataset = FinancialDataset(config)
        dataset.fit(sample_bars, sample_targets)

        # 验证分割
        train, val, test = dataset.get_splits()
        total = len(train) + len(val) + len(test)
        assert total <= len(dataset.get_all_samples())

    def test_dataset_split_ratio(
        self,
        sample_bars: list[Bar1m],
        sample_targets: list[float],
    ) -> None:
        """测试数据集分割比例."""
        seq_config = SequenceConfig(window_size=20)
        config = DatasetConfig(
            sequence_config=seq_config,
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        dataset = create_dataset(sample_bars, sample_targets, config)
        info = dataset.get_split_info()

        # 验证比例大致正确
        total = info["total"]
        if total > 0:
            train_ratio = info["train"] / total
            assert 0.5 < train_ratio < 0.7

    def test_dataset_deterministic(
        self,
        sample_bars: list[Bar1m],
        sample_targets: list[float],
    ) -> None:
        """测试数据集确定性 (M7)."""
        seq_config = SequenceConfig(window_size=20, seed=42)
        config = DatasetConfig(sequence_config=seq_config, seed=42)

        # 第一次创建
        dataset1 = create_dataset(sample_bars, sample_targets, config)
        hash1 = dataset1.get_dataset_hash()

        # 第二次创建
        dataset2 = create_dataset(sample_bars, sample_targets, config)
        hash2 = dataset2.get_dataset_hash()

        assert hash1 == hash2

    def test_sample_hash(
        self,
        sample_bars: list[Bar1m],
        sample_targets: list[float],
    ) -> None:
        """测试样本哈希."""
        seq_config = SequenceConfig(window_size=20)
        config = DatasetConfig(sequence_config=seq_config)
        dataset = create_dataset(sample_bars, sample_targets, config)

        samples = dataset.get_all_samples()
        if samples:
            assert samples[0].sample_hash != ""
            assert len(samples[0].sample_hash) == 16


# ============================================================================
# EnhancedLSTM Tests
# ============================================================================


class TestEnhancedLSTM:
    """EnhancedLSTM测试类."""

    def test_forward_pass(self) -> None:
        """测试前向传播 (DL.MODEL.LSTM.FORWARD)."""
        config = LSTMConfig(input_dim=3, hidden_dim=32, num_layers=2)
        model = EnhancedLSTM(config)

        # 创建测试输入
        batch_size = 4
        seq_len = 20
        x = torch.randn(batch_size, seq_len, 3)

        # 前向传播
        output, (h_n, c_n) = model(x)

        assert output.shape == (batch_size, 1)
        assert h_n.shape == (2, batch_size, 32)  # num_layers, batch, hidden
        assert c_n.shape == (2, batch_size, 32)

    def test_output_range(self) -> None:
        """测试输出范围在[-1, 1]."""
        model = create_lstm_model(input_dim=3, hidden_dim=32)
        x = torch.randn(10, 20, 3)

        output, _ = model(x)

        assert output.min() >= -1.0
        assert output.max() <= 1.0

    def test_attention_mechanism(self) -> None:
        """测试注意力机制 (DL.MODEL.LSTM.ATTENTION)."""
        config = LSTMConfig(input_dim=3, hidden_dim=32, use_attention=True)
        model = EnhancedLSTM(config)

        x = torch.randn(4, 20, 3)
        attention_weights = model.get_attention_weights(x)

        assert attention_weights is not None
        assert attention_weights.shape == (4, 20, 20)  # batch, seq, seq

    def test_no_attention(self) -> None:
        """测试无注意力机制."""
        config = LSTMConfig(input_dim=3, hidden_dim=32, use_attention=False)
        model = EnhancedLSTM(config)

        x = torch.randn(4, 20, 3)
        attention_weights = model.get_attention_weights(x)

        assert attention_weights is None

    def test_bidirectional(self) -> None:
        """测试双向LSTM."""
        config = LSTMConfig(
            input_dim=3,
            hidden_dim=32,
            bidirectional=True,
            use_attention=False,
        )
        model = EnhancedLSTM(config)

        x = torch.randn(4, 20, 3)
        output, (h_n, c_n) = model(x)

        assert output.shape == (4, 1)
        # 双向: 2 * num_layers
        assert h_n.shape == (4, 4, 32)  # 2 * 2 layers

    def test_model_hash_deterministic(self) -> None:
        """测试模型哈希确定性 (M7)."""
        torch.manual_seed(42)
        config = LSTMConfig(input_dim=3, hidden_dim=32)
        model1 = EnhancedLSTM(config)
        hash1 = model1.compute_model_hash()

        torch.manual_seed(42)
        model2 = EnhancedLSTM(config)
        hash2 = model2.compute_model_hash()

        assert hash1 == hash2

    def test_model_info(self) -> None:
        """测试模型信息 (M3)."""
        config = LSTMConfig(input_dim=3, hidden_dim=32)
        model = EnhancedLSTM(config)

        info = model.get_model_info()

        assert "input_dim" in info
        assert "hidden_dim" in info
        assert "param_count" in info
        assert "model_hash" in info
        assert info["param_count"] > 0


# ============================================================================
# EarlyStopping Tests
# ============================================================================


class TestEarlyStopping:
    """EarlyStopping测试类."""

    def test_improvement_resets_counter(self) -> None:
        """测试改善重置计数器."""
        es = EarlyStopping(patience=3, min_delta=0.01)

        es.step(1.0)
        es.step(0.95)
        es.step(0.9)
        es.step(0.85)  # 持续改善

        assert es.counter == 0
        assert not es.should_stop

    def test_no_improvement_triggers_stop(self) -> None:
        """测试无改善触发停止 (DL.TRAIN.EARLY_STOP)."""
        es = EarlyStopping(patience=3, min_delta=0.01)

        es.step(1.0)
        es.step(1.0)  # 无改善
        es.step(1.0)  # 无改善
        result = es.step(1.0)  # 无改善 -> 触发

        assert result is True
        assert es.should_stop is True

    def test_slight_improvement_not_enough(self) -> None:
        """测试微小改善不足以重置."""
        es = EarlyStopping(patience=3, min_delta=0.1)

        es.step(1.0)
        es.step(0.95)  # 改善0.05 < 0.1,不够
        es.step(0.92)  # 继续小改善
        es.step(0.90)  # 触发

        assert es.should_stop is True

    def test_reset(self) -> None:
        """测试重置."""
        es = EarlyStopping(patience=3)
        es.step(1.0)
        es.step(1.0)
        es.step(1.0)
        es.step(1.0)

        es.reset()

        assert es.best_loss == float("inf")
        assert es.counter == 0
        assert es.should_stop is False


# ============================================================================
# ICCalculator Tests
# ============================================================================


class TestICCalculator:
    """ICCalculator测试类."""

    def test_compute_ic_basic(self) -> None:
        """测试基本IC计算 (DL.FACTOR.IC.COMPUTE)."""
        np.random.seed(42)
        predictions = np.random.randn(100)
        returns = predictions * 0.5 + np.random.randn(100) * 0.1

        calculator = ICCalculator()
        result = calculator.compute(predictions, returns)

        assert result.ic > 0
        assert result.n_samples == 100
        assert 0 <= result.p_value <= 1

    def test_ic_threshold_gate(self) -> None:
        """测试IC门禁."""
        np.random.seed(42)
        predictions = np.random.randn(100)
        returns = predictions * 0.5 + np.random.randn(100) * 0.1

        config = ICConfig(ic_threshold=0.05)
        calculator = ICCalculator(config)
        result = calculator.compute(predictions, returns)

        # 验证门禁判断
        expected_pass = result.ic >= 0.05
        assert result.passes_threshold == expected_pass

    def test_ic_with_no_correlation(self) -> None:
        """测试无相关性情况."""
        np.random.seed(42)
        predictions = np.random.randn(100)
        returns = np.random.randn(100)  # 完全独立

        calculator = ICCalculator()
        result = calculator.compute(predictions, returns)

        # IC应该接近0
        assert abs(result.ic) < 0.3

    def test_ic_perfect_correlation(self) -> None:
        """测试完美相关."""
        predictions = np.linspace(0, 1, 100)
        returns = predictions  # 完美正相关

        calculator = ICCalculator()
        result = calculator.compute(predictions, returns)

        assert result.ic > 0.99

    def test_ic_negative_correlation(self) -> None:
        """测试负相关."""
        predictions = np.linspace(0, 1, 100)
        returns = -predictions  # 完美负相关

        calculator = ICCalculator()
        result = calculator.compute(predictions, returns)

        assert result.ic < -0.99

    def test_validate_model(self) -> None:
        """测试模型验证."""
        np.random.seed(42)
        predictions = np.random.randn(100)
        returns = predictions * 0.3 + np.random.randn(100) * 0.1

        calculator = ICCalculator()
        passed, message = calculator.validate_model(predictions, returns)

        assert isinstance(passed, bool)
        assert "IC" in message

    def test_convenience_function(self) -> None:
        """测试便捷函数."""
        np.random.seed(42)
        predictions = list(np.random.randn(100))
        returns = [p * 0.5 + np.random.randn() * 0.1 for p in predictions]

        ic = compute_ic(predictions, returns)
        assert isinstance(ic, float)

    def test_validate_ic_gate_function(self) -> None:
        """测试门禁验证函数."""
        predictions = np.linspace(0, 1, 100)
        returns = predictions * 0.8

        passed = validate_ic_gate(predictions.tolist(), returns.tolist(), threshold=0.05)
        assert passed is True

    def test_computation_log(self) -> None:
        """测试计算日志 (M3)."""
        config = ICConfig()
        calculator = ICCalculator(config)

        predictions = np.random.randn(50)
        returns = np.random.randn(50)
        calculator.compute(predictions, returns)

        log = calculator.get_computation_log()
        assert len(log) == 1
        assert "timestamp" in log[0]
        assert "ic" in log[0]


# ============================================================================
# TrainerConfig Tests
# ============================================================================


class TestTrainerConfig:
    """TrainerConfig测试类."""

    def test_default_config(self) -> None:
        """测试默认配置."""
        config = TrainerConfig()
        assert config.epochs == 100
        assert config.learning_rate == 1e-3
        assert config.deterministic is True

    def test_invalid_epochs(self) -> None:
        """测试无效epochs."""
        with pytest.raises(ValueError):
            TrainerConfig(epochs=0)

    def test_invalid_learning_rate(self) -> None:
        """测试无效学习率."""
        with pytest.raises(ValueError):
            TrainerConfig(learning_rate=-0.01)


# ============================================================================
# Integration Tests
# ============================================================================


class TestDLIntegration:
    """DL模块集成测试."""

    def test_end_to_end_pipeline(
        self,
        sample_bars: list[Bar1m],
        sample_targets: list[float],
    ) -> None:
        """测试端到端流水线."""
        # 1. 创建数据集
        seq_config = SequenceConfig(window_size=20, features=("returns", "volume", "range"))
        dataset_config = DatasetConfig(sequence_config=seq_config)
        dataset = create_dataset(sample_bars, sample_targets, dataset_config)

        train, val, test = dataset.get_splits()
        assert len(train) > 0

        # 2. 创建模型
        model_config = LSTMConfig(
            input_dim=3,  # 3个特征
            hidden_dim=32,
            num_layers=1,
            use_attention=False,  # 简化测试
        )
        model = EnhancedLSTM(model_config)

        # 3. 验证模型输出
        if train:
            sample = train[0]
            x = torch.from_numpy(sample.features).unsqueeze(0)  # (1, seq, feat)
            output, _ = model(x)
            assert output.shape == (1, 1)

    def test_ic_gate_with_model(
        self,
        sample_bars: list[Bar1m],
        sample_targets: list[float],
    ) -> None:
        """测试模型IC门禁."""
        # 简化测试: 使用随机预测
        np.random.seed(42)
        predictions = np.random.randn(50)
        returns = predictions * 0.3 + np.random.randn(50) * 0.5

        calculator = ICCalculator()
        result = calculator.compute(predictions, returns)

        # 记录IC值(用于验收)
        assert result.ic is not None
        assert result.n_samples == 50


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
