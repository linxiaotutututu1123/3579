"""置信度ML预测模块测试.

V4PRO Platform - 置信度ML预测系统测试
军规覆盖: M3(完整审计), M19(风险归因), M24(模型可解释性)

测试场景:
- K59: CONFIDENCE.ML.PREDICT - ML预测置信度
- K60: CONFIDENCE.ML.TRAIN - 模型训练
- K61: CONFIDENCE.ML.ENHANCE - 增强评估器
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import torch

from src.risk.confidence import (
    ConfidenceContext,
    ConfidenceLevel,
    ConfidenceResult,
    TaskType,
)
from src.risk.confidence_ml import (
    ConfidenceMLP,
    ConfidenceMLPredictor,
    FeatureConfig,
    MLEnhancedAssessor,
    TrainingConfig,
    create_ml_enhanced_assessor,
    create_ml_predictor,
    extract_features,
    get_feature_dim,
    quick_ml_predict,
)


class TestConfidenceMLP:
    """ConfidenceMLP 测试类."""

    def test_model_creation(self) -> None:
        """测试模型创建."""
        model = ConfidenceMLP(feature_dim=20)

        assert model.feature_dim == 20

    def test_forward_pass(self) -> None:
        """测试前向传播."""
        model = ConfidenceMLP(feature_dim=20)
        x = torch.randn(1, 20)

        output = model(x)

        assert output.shape == (1, 1)
        assert 0 <= output.item() <= 1  # Sigmoid输出

    def test_batch_forward(self) -> None:
        """测试批量前向传播."""
        model = ConfidenceMLP(feature_dim=20)
        x = torch.randn(10, 20)

        output = model(x)

        assert output.shape == (10, 1)


class TestFeatureExtraction:
    """特征提取测试类."""

    def test_extract_features_default(self) -> None:
        """测试默认特征提取."""
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
            signal_strength=0.8,
        )

        features = extract_features(context)

        assert features.dim() == 1
        assert features.shape[0] == 20  # 5 + 5 + 4 + 6

    def test_extract_features_partial(self) -> None:
        """测试部分特征提取."""
        config = FeatureConfig(
            include_pre_exec=True,
            include_signal=False,
            include_extended=False,
            include_advanced=False,
        )
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)

        features = extract_features(context, config)

        assert features.shape[0] == 5

    def test_get_feature_dim(self) -> None:
        """测试获取特征维度."""
        # 全部特征
        dim = get_feature_dim()
        assert dim == 20

        # 部分特征
        config = FeatureConfig(
            include_pre_exec=True,
            include_signal=True,
            include_extended=False,
            include_advanced=False,
        )
        dim = get_feature_dim(config)
        assert dim == 10


class TestConfidenceMLPredictor:
    """ConfidenceMLPredictor 测试类."""

    def test_create_predictor(self) -> None:
        """测试创建预测器."""
        predictor = ConfidenceMLPredictor()

        assert predictor.is_trained is False
        assert predictor.model is not None

    def test_predict_confidence(self) -> None:
        """测试预测置信度 (K59)."""
        predictor = ConfidenceMLPredictor()
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
            architecture_verified=True,
        )

        score = predictor.predict_confidence(context)

        assert 0 <= score <= 1

    def test_predict_batch(self) -> None:
        """测试批量预测."""
        predictor = ConfidenceMLPredictor()
        contexts = [
            ConfidenceContext(
                task_type=TaskType.STRATEGY_EXECUTION,
                duplicate_check_complete=True,
            ),
            ConfidenceContext(
                task_type=TaskType.SIGNAL_GENERATION,
                signal_strength=0.8,
            ),
        ]

        scores = predictor.predict_batch(contexts)

        assert len(scores) == 2
        assert all(0 <= s <= 1 for s in scores)

    def test_train_model(self) -> None:
        """测试模型训练 (K60)."""
        predictor = ConfidenceMLPredictor()

        # 创建模拟训练数据
        history: list[tuple[ConfidenceContext, ConfidenceResult]] = []
        for i in range(20):
            context = ConfidenceContext(
                task_type=TaskType.STRATEGY_EXECUTION,
                duplicate_check_complete=i % 2 == 0,
                architecture_verified=i % 3 == 0,
                signal_strength=i / 20,
            )
            # 模拟结果
            score = 0.5 + (i / 40)  # 分数在0.5-1.0之间
            result = ConfidenceResult(
                score=score,
                level=ConfidenceLevel.HIGH if score >= 0.9 else ConfidenceLevel.MEDIUM,
                can_proceed=score >= 0.9,
                checks=(),
                recommendation="",
                timestamp="",
            )
            history.append((context, result))

        config = TrainingConfig(epochs=10, early_stopping_patience=5)
        result = predictor.train(history, config)

        assert predictor.is_trained is True
        assert result.epochs_trained > 0
        assert result.final_loss >= 0

    def test_train_insufficient_data(self) -> None:
        """测试数据不足时的训练."""
        predictor = ConfidenceMLPredictor()
        history: list[tuple[ConfidenceContext, ConfidenceResult]] = []

        with pytest.raises(ValueError, match="训练数据不足"):
            predictor.train(history)

    def test_save_and_load_model(self) -> None:
        """测试模型保存和加载."""
        predictor = ConfidenceMLPredictor()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_model.pt"

            # 保存
            predictor.save_model(path)
            assert path.exists()

            # 加载到新预测器
            new_predictor = ConfidenceMLPredictor(model_path=path)
            assert new_predictor.model is not None


class TestMLEnhancedAssessor:
    """MLEnhancedAssessor 测试类."""

    def test_create_assessor(self) -> None:
        """测试创建增强评估器 (K61)."""
        predictor = ConfidenceMLPredictor()
        assessor = MLEnhancedAssessor(predictor)

        assert assessor.predictor is predictor
        assert assessor.ml_weight == 0.15

    def test_assess_includes_ml_check(self) -> None:
        """测试评估包含ML检查."""
        predictor = ConfidenceMLPredictor()
        assessor = MLEnhancedAssessor(predictor)

        context = ConfidenceContext(
            task_type=TaskType.RISK_ASSESSMENT,
            duplicate_check_complete=True,
            architecture_verified=True,
        )

        result = assessor.assess(context)

        # 检查是否包含ML检查
        check_names = [c.name for c in result.checks]
        assert "ml_prediction" in check_names

    def test_assess_high_confidence_with_ml(self) -> None:
        """测试高置信度评估 (包含ML)."""
        predictor = ConfidenceMLPredictor()
        assessor = MLEnhancedAssessor(predictor)

        context = ConfidenceContext(
            task_type=TaskType.RISK_ASSESSMENT,
            duplicate_check_complete=True,
            architecture_verified=True,
            has_official_docs=True,
            has_oss_reference=True,
            root_cause_identified=True,
            signal_strength=0.9,
            signal_consistency=0.9,
            risk_within_limits=True,
        )

        result = assessor.assess(context)

        assert result.score > 0
        assert result.level in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)

    def test_custom_ml_weight(self) -> None:
        """测试自定义ML权重."""
        predictor = ConfidenceMLPredictor()
        assessor = MLEnhancedAssessor(predictor, ml_weight=0.25)

        assert assessor.ml_weight == 0.25


class TestConvenienceFunctions:
    """便捷函数测试类."""

    def test_create_ml_predictor(self) -> None:
        """测试创建预测器."""
        predictor = create_ml_predictor()

        assert predictor is not None

    def test_create_ml_enhanced_assessor(self) -> None:
        """测试创建增强评估器."""
        assessor = create_ml_enhanced_assessor()

        assert assessor is not None
        assert assessor.predictor is not None

    def test_quick_ml_predict(self) -> None:
        """测试快速预测."""
        context = ConfidenceContext(
            task_type=TaskType.STRATEGY_EXECUTION,
            duplicate_check_complete=True,
        )

        score = quick_ml_predict(context)

        assert 0 <= score <= 1


class TestEdgeCases:
    """边界情况测试类."""

    def test_empty_batch_predict(self) -> None:
        """测试空批量预测."""
        predictor = ConfidenceMLPredictor()

        scores = predictor.predict_batch([])

        assert scores == []

    def test_single_item_batch(self) -> None:
        """测试单个元素批量预测."""
        predictor = ConfidenceMLPredictor()
        context = ConfidenceContext(task_type=TaskType.STRATEGY_EXECUTION)

        scores = predictor.predict_batch([context])

        assert len(scores) == 1

    def test_model_load_nonexistent(self) -> None:
        """测试加载不存在的模型."""
        predictor = ConfidenceMLPredictor()

        with pytest.raises(FileNotFoundError):
            predictor.load_model("nonexistent_model.pt")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
