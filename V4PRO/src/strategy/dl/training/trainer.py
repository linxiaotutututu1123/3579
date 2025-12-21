"""模型训练器.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计), M26(测试规范)

V4PRO Scenarios:
- DL.TRAIN.LOOP - 训练循环确定性
- DL.TRAIN.EARLY_STOP - 早停机制
- DL.TRAIN.CHECKPOINT - 检查点保存
- DL.TRAIN.AUDIT - 训练审计日志
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader


@dataclass
class TrainerConfig:
    """训练器配置 (带军规约束).

    Attributes:
        epochs: 最大训练轮数
        learning_rate: 初始学习率
        weight_decay: 权重衰减
        grad_clip: 梯度裁剪阈值
        early_stopping_patience: 早停耐心值
        early_stopping_min_delta: 早停最小改善阈值
        checkpoint_dir: 检查点保存目录
        save_best_only: 是否只保存最佳模型
        deterministic: 是否确定性训练(M7)
        seed: 随机种子
        log_interval: 日志打印间隔
        device: 训练设备
    """

    epochs: int = 100
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    grad_clip: float = 1.0
    early_stopping_patience: int = 10
    early_stopping_min_delta: float = 1e-4
    checkpoint_dir: str | Path = "checkpoints"
    save_best_only: bool = True
    deterministic: bool = True
    seed: int = 42
    log_interval: int = 10
    device: str = "cpu"

    def __post_init__(self) -> None:
        """验证配置参数."""
        if self.epochs < 1:
            raise ValueError("epochs must be positive")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")


@dataclass
class TrainerMetrics:
    """训练指标.

    Attributes:
        epoch: 当前轮数
        train_loss: 训练损失
        val_loss: 验证损失
        train_ic: 训练IC值
        val_ic: 验证IC值
        learning_rate: 当前学习率
        epoch_time: 轮次耗时(秒)
    """

    epoch: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    train_ic: float = 0.0
    val_ic: float = 0.0
    learning_rate: float = 0.0
    epoch_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "epoch": self.epoch,
            "train_loss": self.train_loss,
            "val_loss": self.val_loss,
            "train_ic": self.train_ic,
            "val_ic": self.val_ic,
            "learning_rate": self.learning_rate,
            "epoch_time": self.epoch_time,
        }


@dataclass
class EarlyStopping:
    """早停机制 (DL.TRAIN.EARLY_STOP).

    监控验证损失，在连续多轮无改善时停止训练。

    Attributes:
        patience: 耐心值
        min_delta: 最小改善阈值
        best_loss: 最佳损失
        counter: 无改善计数
        should_stop: 是否应该停止
    """

    patience: int = 10
    min_delta: float = 1e-4
    best_loss: float = float("inf")
    counter: int = 0
    should_stop: bool = False

    def step(self, val_loss: float) -> bool:
        """更新早停状态.

        Args:
            val_loss: 验证损失

        Returns:
            是否应该停止
        """
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True

        return self.should_stop

    def reset(self) -> None:
        """重置状态."""
        self.best_loss = float("inf")
        self.counter = 0
        self.should_stop = False


@dataclass
class TrainingHistory:
    """训练历史记录 (M3).

    Attributes:
        metrics: 每轮指标列表
        best_epoch: 最佳轮数
        best_val_loss: 最佳验证损失
        total_time: 总训练时间
        model_hash: 最终模型哈希
    """

    metrics: list[TrainerMetrics] = field(default_factory=list)
    best_epoch: int = 0
    best_val_loss: float = float("inf")
    total_time: float = 0.0
    model_hash: str = ""

    def add_metrics(self, m: TrainerMetrics) -> None:
        """添加指标."""
        self.metrics.append(m)
        if m.val_loss < self.best_val_loss:
            self.best_val_loss = m.val_loss
            self.best_epoch = m.epoch


class TradingModelTrainer:
    """交易模型训练器 (军规级).

    支持确定性训练、早停、检查点保存和完整审计。

    军规覆盖:
    - M7: 确定性训练
    - M3: 完整审计日志
    - M26: 测试规范

    Example:
        >>> config = TrainerConfig(epochs=100)
        >>> trainer = TradingModelTrainer(model, config)
        >>> history = trainer.fit(train_loader, val_loader)
    """

    def __init__(
        self,
        model: nn.Module,
        config: TrainerConfig | None = None,
        loss_fn: nn.Module | None = None,
        optimizer: torch.optim.Optimizer | None = None,
        scheduler: torch.optim.lr_scheduler.LRScheduler | None = None,
    ) -> None:
        """初始化训练器.

        Args:
            model: PyTorch模型
            config: 训练配置
            loss_fn: 损失函数
            optimizer: 优化器
            scheduler: 学习率调度器
        """
        self.config = config or TrainerConfig()
        self.model = model.to(self.config.device)

        # M7: 设置确定性
        if self.config.deterministic:
            self._set_deterministic()

        # 损失函数
        self.loss_fn = loss_fn or nn.MSELoss()

        # 优化器
        if optimizer is None:
            self.optimizer = torch.optim.AdamW(
                model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )
        else:
            self.optimizer = optimizer

        # 学习率调度器
        self.scheduler = scheduler

        # 早停
        self.early_stopping = EarlyStopping(
            patience=self.config.early_stopping_patience,
            min_delta=self.config.early_stopping_min_delta,
        )

        # 训练历史
        self.history = TrainingHistory()

        # 检查点目录
        self.checkpoint_dir = Path(self.config.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 回调
        self._callbacks: list[Callable[[TrainerMetrics], None]] = []

    def _set_deterministic(self) -> None:
        """设置确定性训练 (M7)."""
        torch.manual_seed(self.config.seed)
        np.random.seed(self.config.seed)

        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(self.config.seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
    ) -> TrainingHistory:
        """训练模型 (DL.TRAIN.LOOP).

        Args:
            train_loader: 训练数据加载器
            val_loader: 验证数据加载器

        Returns:
            训练历史记录
        """
        start_time = time.time()
        best_val_loss = float("inf")

        for epoch in range(1, self.config.epochs + 1):
            epoch_start = time.time()

            # 训练
            train_loss, train_preds, train_targets = self._train_epoch(train_loader)

            # 验证
            val_loss, val_preds, val_targets = self._validate_epoch(val_loader)

            # 计算IC
            train_ic = self._compute_ic(train_preds, train_targets)
            val_ic = self._compute_ic(val_preds, val_targets)

            # 获取当前学习率
            current_lr = self.optimizer.param_groups[0]["lr"]

            # 更新学习率调度器
            if self.scheduler is not None:
                self.scheduler.step(val_loss)

            # 记录指标
            metrics = TrainerMetrics(
                epoch=epoch,
                train_loss=train_loss,
                val_loss=val_loss,
                train_ic=train_ic,
                val_ic=val_ic,
                learning_rate=current_lr,
                epoch_time=time.time() - epoch_start,
            )
            self.history.add_metrics(metrics)

            # 回调
            for callback in self._callbacks:
                callback(metrics)

            # 保存检查点
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                if self.config.save_best_only:
                    self._save_checkpoint(epoch, "best")

            # 早停检查
            if self.early_stopping.step(val_loss):
                break

        # 保存最终模型
        self._save_checkpoint(epoch, "final")

        # 记录总时间
        self.history.total_time = time.time() - start_time

        # 计算最终模型哈希
        self.history.model_hash = self._compute_model_hash()

        return self.history

    def _train_epoch(
        self,
        loader: DataLoader,
    ) -> tuple[float, list[float], list[float]]:
        """训练单轮.

        Args:
            loader: 数据加载器

        Returns:
            (平均损失, 预测值列表, 目标值列表)
        """
        self.model.train()
        total_loss = 0.0
        all_preds: list[float] = []
        all_targets: list[float] = []

        for batch_idx, (features, targets) in enumerate(loader):
            features = features.to(self.config.device)
            targets = targets.to(self.config.device)

            self.optimizer.zero_grad()

            # 前向传播
            if hasattr(self.model, "forward") and "hidden" in str(
                self.model.forward.__code__.co_varnames
            ):
                outputs, _ = self.model(features)
            else:
                outputs = self.model(features)

            # 计算损失
            loss = self.loss_fn(outputs, targets)

            # 反向传播
            loss.backward()

            # 梯度裁剪
            if self.config.grad_clip > 0:
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config.grad_clip,
                )

            self.optimizer.step()

            total_loss += loss.item()

            # 收集预测和目标
            with torch.no_grad():
                preds = outputs.squeeze().cpu().numpy()
                tgts = targets.squeeze().cpu().numpy()
                if preds.ndim == 0:
                    all_preds.append(float(preds))
                    all_targets.append(float(tgts))
                else:
                    all_preds.extend(preds.tolist())
                    all_targets.extend(tgts.tolist())

        avg_loss = total_loss / len(loader) if len(loader) > 0 else 0.0
        return avg_loss, all_preds, all_targets

    def _validate_epoch(
        self,
        loader: DataLoader,
    ) -> tuple[float, list[float], list[float]]:
        """验证单轮.

        Args:
            loader: 数据加载器

        Returns:
            (平均损失, 预测值列表, 目标值列表)
        """
        self.model.eval()
        total_loss = 0.0
        all_preds: list[float] = []
        all_targets: list[float] = []

        with torch.no_grad():
            for features, targets in loader:
                features = features.to(self.config.device)
                targets = targets.to(self.config.device)

                # 前向传播
                if hasattr(self.model, "forward") and "hidden" in str(
                    self.model.forward.__code__.co_varnames
                ):
                    outputs, _ = self.model(features)
                else:
                    outputs = self.model(features)

                # 计算损失
                loss = self.loss_fn(outputs, targets)
                total_loss += loss.item()

                # 收集预测和目标
                preds = outputs.squeeze().cpu().numpy()
                tgts = targets.squeeze().cpu().numpy()
                if preds.ndim == 0:
                    all_preds.append(float(preds))
                    all_targets.append(float(tgts))
                else:
                    all_preds.extend(preds.tolist())
                    all_targets.extend(tgts.tolist())

        avg_loss = total_loss / len(loader) if len(loader) > 0 else 0.0
        return avg_loss, all_preds, all_targets

    def _compute_ic(
        self,
        predictions: list[float],
        targets: list[float],
    ) -> float:
        """计算Information Coefficient.

        Args:
            predictions: 预测值
            targets: 目标值

        Returns:
            IC值(Spearman相关系数)
        """
        if len(predictions) < 2:
            return 0.0

        preds = np.array(predictions)
        tgts = np.array(targets)

        # Spearman相关系数
        from scipy.stats import spearmanr

        try:
            ic, _ = spearmanr(preds, tgts)
            return float(ic) if not np.isnan(ic) else 0.0
        except Exception:
            return 0.0

    def _save_checkpoint(self, epoch: int, tag: str) -> None:
        """保存检查点 (DL.TRAIN.CHECKPOINT).

        Args:
            epoch: 轮数
            tag: 标签(best/final)
        """
        checkpoint = {
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "config": self.config,
            "history": self.history,
        }

        if self.scheduler is not None:
            checkpoint["scheduler_state_dict"] = self.scheduler.state_dict()

        path = self.checkpoint_dir / f"model_{tag}.pt"
        torch.save(checkpoint, path)

    def _compute_model_hash(self) -> str:
        """计算模型参数哈希 (M7).

        Returns:
            模型哈希值
        """
        hasher = hashlib.sha256()
        for param in self.model.parameters():
            hasher.update(param.data.cpu().numpy().tobytes())
        return hasher.hexdigest()[:32]

    def add_callback(self, callback: Callable[[TrainerMetrics], None]) -> None:
        """添加回调函数.

        Args:
            callback: 回调函数
        """
        self._callbacks.append(callback)

    def load_checkpoint(self, path: str | Path) -> None:
        """加载检查点.

        Args:
            path: 检查点路径
        """
        checkpoint = torch.load(path, map_location=self.config.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        if "scheduler_state_dict" in checkpoint and self.scheduler is not None:
            self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

    def get_training_summary(self) -> dict[str, Any]:
        """获取训练摘要 (M3).

        Returns:
            训练摘要字典
        """
        return {
            "epochs_trained": len(self.history.metrics),
            "best_epoch": self.history.best_epoch,
            "best_val_loss": self.history.best_val_loss,
            "final_train_loss": (
                self.history.metrics[-1].train_loss
                if self.history.metrics
                else 0.0
            ),
            "final_val_loss": (
                self.history.metrics[-1].val_loss if self.history.metrics else 0.0
            ),
            "final_val_ic": (
                self.history.metrics[-1].val_ic if self.history.metrics else 0.0
            ),
            "total_time": self.history.total_time,
            "model_hash": self.history.model_hash,
            "early_stopped": self.early_stopping.should_stop,
        }


def create_trainer(
    model: nn.Module,
    epochs: int = 100,
    learning_rate: float = 1e-3,
    **kwargs: Any,
) -> TradingModelTrainer:
    """创建训练器的便捷函数.

    Args:
        model: PyTorch模型
        epochs: 训练轮数
        learning_rate: 学习率
        **kwargs: 其他配置参数

    Returns:
        创建的训练器
    """
    config = TrainerConfig(
        epochs=epochs,
        learning_rate=learning_rate,
        **kwargs,
    )
    return TradingModelTrainer(model, config)
