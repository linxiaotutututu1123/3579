"""置信度ML预测模块 (军规级 v4.4).

V4PRO Platform Component - 置信度ML预测系统
军规覆盖: M3(完整审计), M19(风险归因), M24(模型可解释性)

V4PRO Scenarios:
- K59: CONFIDENCE.ML.PREDICT - ML预测置信度
- K60: CONFIDENCE.ML.TRAIN - 模型训练
- K61: CONFIDENCE.ML.ENHANCE - 增强评估器

基于历史模式使用ML预测置信度。

示例:
    >>> from src.risk.confidence_ml import ConfidenceMLPredictor, MLEnhancedAssessor
    >>> predictor = ConfidenceMLPredictor()
    >>> assessor = MLEnhancedAssessor(predictor)
    >>> result = assessor.assess(context)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import torch
from torch import nn

from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceCheck,
    ConfidenceContext,
    ConfidenceLevel,
    ConfidenceResult,
    TaskType,
)

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# =============================================================================
# 模型定义
# =============================================================================


class ConfidenceMLP(nn.Module):
    """置信度预测MLP模型.

    架构:
    - 输入: feature_dim (上下文特征)
    - 隐藏层1: 32 units + ReLU + Dropout
    - 隐藏层2: 16 units + ReLU
    - 输出: 1 (置信度分数)

    输出使用Sigmoid确保分数在[0, 1]范围内。
    """

    def __init__(
        self,
        feature_dim: int = 20,
        dropout: float = 0.2,
    ) -> None:
        """初始化模型.

        参数:
            feature_dim: 输入特征维度
            dropout: Dropout比例
        """
        super().__init__()
        self.feature_dim = feature_dim
        self.net = nn.Sequential(
            nn.Linear(feature_dim, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),  # 输出在[0, 1]范围
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """前向传播.

        参数:
            x: 输入特征张量

        返回:
            预测置信度分数
        """
        result: torch.Tensor = self.net(x)
        return result


# =============================================================================
# 特征提取
# =============================================================================


@dataclass
class FeatureConfig:
    """特征配置.

    属性:
        include_pre_exec: 是否包含预执行检查特征
        include_signal: 是否包含信号特征
        include_extended: 是否包含扩展特征
        include_advanced: 是否包含高级特征
        normalize: 是否归一化特征
    """

    include_pre_exec: bool = True
    include_signal: bool = True
    include_extended: bool = True
    include_advanced: bool = True
    normalize: bool = True


def extract_features(
    context: ConfidenceContext,
    config: FeatureConfig | None = None,
) -> torch.Tensor:
    """从上下文提取特征.

    参数:
        context: 置信度评估上下文
        config: 特征配置

    返回:
        特征张量
    """
    if config is None:
        config = FeatureConfig()

    features: list[float] = []

    # 预执行检查特征 (5维)
    if config.include_pre_exec:
        features.extend([
            float(context.duplicate_check_complete),
            float(context.architecture_verified),
            float(context.has_official_docs),
            float(context.has_oss_reference),
            float(context.root_cause_identified),
        ])

    # 信号特征 (5维)
    if config.include_signal:
        market_normal = context.market_condition in {"NORMAL", "TRENDING", "RANGE"}
        features.extend([
            context.signal_strength,
            context.signal_consistency,
            float(market_normal),
            float(context.risk_within_limits),
            _encode_market_condition(context.market_condition),
        ])

    # 扩展特征 (4维)
    if config.include_extended:
        features.extend([
            1.0 - context.volatility,  # 反转: 低波动=高分
            context.liquidity_score,
            context.historical_win_rate,
            1.0 - context.position_concentration,  # 反转: 低集中=高分
        ])

    # 高级特征 (6维)
    if config.include_advanced:
        backtest_score = min(1.0, context.backtest_sample_size / 200.0)
        sharpe_score = min(1.0, max(0.0, context.backtest_sharpe / 2.0))
        features.extend([
            backtest_score,
            sharpe_score,
            float(context.external_signal_valid) * context.external_signal_correlation,
            float(context.regime_alignment),
            1.0 - context.cross_asset_correlation,  # 反转: 低相关=高分
            _encode_regime(context.current_regime),
        ])

    tensor = torch.tensor(features, dtype=torch.float32)

    # 归一化
    if config.normalize:
        tensor = torch.clamp(tensor, 0.0, 1.0)

    return tensor


def _encode_market_condition(condition: str) -> float:
    """编码市场状态为数值."""
    encoding = {
        "NORMAL": 1.0,
        "TRENDING": 0.9,
        "RANGE": 0.8,
        "VOLATILE": 0.3,
        "CRISIS": 0.1,
        "LIMIT_UP": 0.2,
        "LIMIT_DOWN": 0.2,
    }
    return encoding.get(condition, 0.5)


def _encode_regime(regime: str) -> float:
    """编码市场体制为数值."""
    encoding = {
        "TRENDING": 0.8,
        "RANGE": 0.7,
        "VOLATILE": 0.4,
        "UNKNOWN": 0.5,
    }
    return encoding.get(regime, 0.5)


def get_feature_dim(config: FeatureConfig | None = None) -> int:
    """获取特征维度.

    参数:
        config: 特征配置

    返回:
        特征维度
    """
    if config is None:
        config = FeatureConfig()

    dim = 0
    if config.include_pre_exec:
        dim += 5
    if config.include_signal:
        dim += 5
    if config.include_extended:
        dim += 4
    if config.include_advanced:
        dim += 6

    return dim


# =============================================================================
# ML预测器
# =============================================================================


@dataclass
class TrainingConfig:
    """训练配置.

    属性:
        learning_rate: 学习率
        epochs: 训练轮数
        batch_size: 批次大小
        validation_split: 验证集比例
        early_stopping_patience: 早停耐心值
    """

    learning_rate: float = 0.001
    epochs: int = 100
    batch_size: int = 32
    validation_split: float = 0.2
    early_stopping_patience: int = 10


@dataclass
class TrainingResult:
    """训练结果.

    属性:
        final_loss: 最终损失
        best_loss: 最佳损失
        epochs_trained: 实际训练轮数
        validation_loss: 验证损失
        training_time_seconds: 训练时间
    """

    final_loss: float
    best_loss: float
    epochs_trained: int
    validation_loss: float
    training_time_seconds: float

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "final_loss": self.final_loss,
            "best_loss": self.best_loss,
            "epochs_trained": self.epochs_trained,
            "validation_loss": self.validation_loss,
            "training_time_seconds": self.training_time_seconds,
        }


class ConfidenceMLPredictor:
    """置信度ML预测器.

    使用MLP模型基于历史模式预测置信度。

    功能:
    - 特征提取
    - 模型训练
    - 置信度预测
    - 模型持久化

    示例:
        >>> predictor = ConfidenceMLPredictor()
        >>> score = predictor.predict_confidence(context)
        >>> print(f"ML预测置信度: {score:.0%}")
    """

    DEFAULT_MODEL_PATH: ClassVar[str] = "models/confidence_ml.pt"

    def __init__(
        self,
        model_path: str | Path | None = None,
        feature_config: FeatureConfig | None = None,
    ) -> None:
        """初始化预测器.

        参数:
            model_path: 模型文件路径 (可选，用于加载已训练模型)
            feature_config: 特征配置
        """
        self._feature_config = feature_config or FeatureConfig()
        self._feature_dim = get_feature_dim(self._feature_config)
        self._model = ConfidenceMLP(feature_dim=self._feature_dim)
        self._is_trained = False
        self._training_history: list[TrainingResult] = []

        if model_path and Path(model_path).exists():
            self.load_model(model_path)

    @property
    def is_trained(self) -> bool:
        """是否已训练."""
        return self._is_trained

    @property
    def model(self) -> ConfidenceMLP:
        """获取模型."""
        return self._model

    def predict_confidence(self, context: ConfidenceContext) -> float:
        """预测置信度.

        参数:
            context: 评估上下文

        返回:
            预测的置信度分数 (0.0-1.0)

        场景: K59
        """
        self._model.eval()
        with torch.no_grad():
            features = extract_features(context, self._feature_config)
            features = features.unsqueeze(0)  # 添加批次维度
            output = self._model(features)
            score: float = output.item()
        return score

    def predict_batch(
        self, contexts: list[ConfidenceContext]
    ) -> list[float]:
        """批量预测置信度.

        参数:
            contexts: 上下文列表

        返回:
            预测分数列表
        """
        if not contexts:
            return []

        self._model.eval()
        with torch.no_grad():
            features = torch.stack([
                extract_features(ctx, self._feature_config)
                for ctx in contexts
            ])
            outputs = self._model(features)
            scores: list[float] = outputs.squeeze().tolist()

        # 处理单个元素的情况
        if isinstance(scores, float):
            scores = [scores]

        return scores

    def train(
        self,
        history: list[tuple[ConfidenceContext, ConfidenceResult]],
        config: TrainingConfig | None = None,
    ) -> TrainingResult:
        """训练模型.

        参数:
            history: 历史数据 (上下文, 结果) 对列表
            config: 训练配置

        返回:
            训练结果

        场景: K60
        """
        import time

        if config is None:
            config = TrainingConfig()

        if len(history) < 10:
            raise ValueError("训练数据不足 (至少需要10条)")

        start_time = time.time()

        # 准备数据
        features = torch.stack([
            extract_features(ctx, self._feature_config)
            for ctx, _ in history
        ])
        labels = torch.tensor(
            [result.score for _, result in history],
            dtype=torch.float32,
        ).unsqueeze(1)

        # 划分训练集和验证集
        n_samples = len(history)
        n_val = int(n_samples * config.validation_split)
        n_train = n_samples - n_val

        indices = torch.randperm(n_samples)
        train_indices = indices[:n_train]
        val_indices = indices[n_train:]

        train_features = features[train_indices]
        train_labels = labels[train_indices]
        val_features = features[val_indices]
        val_labels = labels[val_indices]

        # 训练
        self._model.train()
        optimizer = torch.optim.Adam(
            self._model.parameters(),
            lr=config.learning_rate,
        )
        criterion = nn.MSELoss()

        best_val_loss = float("inf")
        patience_counter = 0
        epochs_trained = 0

        for epoch in range(config.epochs):
            # 训练步骤
            optimizer.zero_grad()
            train_output = self._model(train_features)
            train_loss = criterion(train_output, train_labels)
            train_loss.backward()
            optimizer.step()

            # 验证步骤
            self._model.eval()
            with torch.no_grad():
                val_output = self._model(val_features)
                val_loss = criterion(val_output, val_labels).item()
            self._model.train()

            epochs_trained = epoch + 1

            # 早停检查
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= config.early_stopping_patience:
                    logger.info(
                        "早停于第 %d 轮, 最佳验证损失: %.4f",
                        epoch + 1,
                        best_val_loss,
                    )
                    break

        training_time = time.time() - start_time
        self._is_trained = True

        result = TrainingResult(
            final_loss=train_loss.item(),
            best_loss=best_val_loss,
            epochs_trained=epochs_trained,
            validation_loss=val_loss,
            training_time_seconds=training_time,
        )
        self._training_history.append(result)

        logger.info(
            "模型训练完成: 轮数=%d, 最佳损失=%.4f, 耗时=%.2fs",
            epochs_trained,
            best_val_loss,
            training_time,
        )

        return result

    def save_model(self, path: str | Path) -> None:
        """保存模型.

        参数:
            path: 保存路径
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "model_state_dict": self._model.state_dict(),
            "feature_dim": self._feature_dim,
            "is_trained": self._is_trained,
            "saved_at": datetime.now().isoformat(),  # noqa: DTZ005
        }
        torch.save(state, path)
        logger.info("模型已保存: %s", path)

    def load_model(self, path: str | Path) -> None:
        """加载模型.

        参数:
            path: 模型文件路径
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"模型文件不存在: {path}")

        state = torch.load(path, weights_only=True)
        self._model.load_state_dict(state["model_state_dict"])
        self._is_trained = state.get("is_trained", True)
        logger.info("模型已加载: %s", path)

    def get_training_history(self) -> list[TrainingResult]:
        """获取训练历史."""
        return list(self._training_history)


# =============================================================================
# 增强评估器
# =============================================================================


class MLEnhancedAssessor(ConfidenceAssessor):
    """ML增强置信度评估器.

    在标准评估基础上增加ML预测作为额外检查项。

    功能:
    - 继承标准评估逻辑
    - 添加ML预测检查
    - 可配置ML权重

    示例:
        >>> predictor = ConfidenceMLPredictor()
        >>> assessor = MLEnhancedAssessor(predictor, ml_weight=0.15)
        >>> result = assessor.assess(context)

    场景: K61
    """

    WEIGHT_ML_PREDICTION: ClassVar[float] = 0.15

    def __init__(
        self,
        predictor: ConfidenceMLPredictor,
        ml_weight: float = 0.15,
        high_threshold: float = 0.90,
        medium_threshold: float = 0.70,
        adaptive_mode: bool = False,
    ) -> None:
        """初始化增强评估器.

        参数:
            predictor: ML预测器
            ml_weight: ML检查权重
            high_threshold: 高置信度阈值
            medium_threshold: 中等置信度阈值
            adaptive_mode: 是否启用自适应模式
        """
        super().__init__(
            high_threshold=high_threshold,
            medium_threshold=medium_threshold,
            adaptive_mode=adaptive_mode,
        )
        self._predictor = predictor
        self._ml_weight = ml_weight

    @property
    def predictor(self) -> ConfidenceMLPredictor:
        """获取预测器."""
        return self._predictor

    @property
    def ml_weight(self) -> float:
        """获取ML权重."""
        return self._ml_weight

    def _assess_ml(self, context: ConfidenceContext) -> ConfidenceCheck:
        """ML预测检查.

        参数:
            context: 评估上下文

        返回:
            ML检查结果
        """
        try:
            ml_score = self._predictor.predict_confidence(context)
            ml_passed = ml_score >= 0.5  # ML预测≥50%视为通过

            return ConfidenceCheck(
                name="ml_prediction",
                passed=ml_passed,
                weight=self._ml_weight if ml_passed else 0.0,
                message=(
                    f"ML: ML预测置信度: {ml_score:.0%}"
                    if ml_passed
                    else f"ML: ML预测置信度偏低: {ml_score:.0%}"
                ),
                details={
                    "ml_score": ml_score,
                    "is_trained": self._predictor.is_trained,
                },
            )
        except Exception as e:
            logger.warning("ML预测失败: %s", e)
            return ConfidenceCheck(
                name="ml_prediction",
                passed=False,
                weight=0.0,
                message=f"ML: ML预测失败: {e}",
                details={"error": str(e)},
            )

    def _assess_combined(self, context: ConfidenceContext) -> list[ConfidenceCheck]:
        """组合评估 (包含ML检查).

        重写父类方法以包含ML检查。
        """
        # 获取标准检查
        checks = super()._assess_combined(context)

        # 添加ML检查
        ml_check = self._assess_ml(context)
        checks.append(ml_check)

        return checks


# =============================================================================
# 便捷函数
# =============================================================================


def create_ml_predictor(
    model_path: str | Path | None = None,
) -> ConfidenceMLPredictor:
    """创建ML预测器.

    参数:
        model_path: 模型文件路径 (可选)

    返回:
        ML预测器实例
    """
    return ConfidenceMLPredictor(model_path=model_path)


def create_ml_enhanced_assessor(
    predictor: ConfidenceMLPredictor | None = None,
    ml_weight: float = 0.15,
) -> MLEnhancedAssessor:
    """创建ML增强评估器.

    参数:
        predictor: ML预测器 (可选)
        ml_weight: ML检查权重

    返回:
        增强评估器实例
    """
    if predictor is None:
        predictor = ConfidenceMLPredictor()

    return MLEnhancedAssessor(predictor, ml_weight=ml_weight)


def quick_ml_predict(context: ConfidenceContext) -> float:
    """快速ML预测.

    参数:
        context: 评估上下文

    返回:
        预测的置信度分数
    """
    predictor = ConfidenceMLPredictor()
    return predictor.predict_confidence(context)
