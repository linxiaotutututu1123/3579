"""金融数据集模块.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计)

V4PRO Scenarios:
- DL.DATA.DATASET.CREATE - 数据集创建
- DL.DATA.DATASET.SPLIT - 数据集分割
- DL.DATA.DATASET.SHUFFLE - 确定性打乱
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence as PySequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    import torch
    from torch.utils.data import Dataset

from src.strategy.dl.data.sequence_handler import (
    SequenceConfig,
    SequenceHandler,
    SequenceWindow,
)
from src.strategy.types import Bar1m


@dataclass
class FinancialSample:
    """金融数据样本.

    Attributes:
        features: 特征张量 (window_size, n_features)
        target: 目标值
        timestamp: 时间戳
        sample_idx: 样本索引
        sample_hash: 样本哈希(M7)
    """

    features: NDArray[np.float32]
    target: float
    timestamp: float = 0.0
    sample_idx: int = 0
    sample_hash: str = ""

    def __post_init__(self) -> None:
        """计算样本哈希."""
        if not self.sample_hash:
            combined = np.concatenate([
                self.features.flatten(),
                np.array([self.target], dtype=np.float32),
            ])
            self.sample_hash = hashlib.sha256(
                combined.tobytes()
            ).hexdigest()[:16]


@dataclass
class DatasetConfig:
    """数据集配置.

    Attributes:
        sequence_config: 序列配置
        train_ratio: 训练集比例
        val_ratio: 验证集比例
        test_ratio: 测试集比例
        shuffle: 是否打乱
        seed: 随机种子
        gap: 训练/验证/测试间隔
    """

    sequence_config: SequenceConfig = field(default_factory=SequenceConfig)
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    shuffle: bool = True
    seed: int = 42
    gap: int = 0  # 集合间隔，防止数据泄露

    def __post_init__(self) -> None:
        """验证配置参数."""
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")


class FinancialDataset:
    """金融数据集 (军规级).

    支持时序分割、确定性打乱和审计日志。

    军规覆盖:
    - M7: 确定性数据处理
    - M3: 完整审计日志

    Example:
        >>> config = DatasetConfig()
        >>> dataset = FinancialDataset(config)
        >>> dataset.fit(bars, targets)
        >>> train, val, test = dataset.get_splits()
    """

    def __init__(self, config: DatasetConfig | None = None) -> None:
        """初始化数据集.

        Args:
            config: 数据集配置
        """
        self.config = config or DatasetConfig()
        self.sequence_handler = SequenceHandler(self.config.sequence_config)

        # M7: 确定性随机数
        self._rng = np.random.RandomState(self.config.seed)

        # 数据存储
        self._samples: list[FinancialSample] = []
        self._train_indices: NDArray[np.int64] = np.array([], dtype=np.int64)
        self._val_indices: NDArray[np.int64] = np.array([], dtype=np.int64)
        self._test_indices: NDArray[np.int64] = np.array([], dtype=np.int64)

        # M3: 审计
        self._fitted = False
        self._dataset_hash = ""

    def fit(
        self,
        bars: PySequence[Bar1m],
        targets: PySequence[float],
    ) -> None:
        """构建数据集 (DL.DATA.DATASET.CREATE).

        Args:
            bars: K线数据
            targets: 目标值列表
        """
        # 构建序列窗口
        windows = self.sequence_handler.build_sequences(bars, list(targets))

        # 转换为样本
        self._samples = []
        for i, window in enumerate(windows):
            if window.target is not None:
                sample = FinancialSample(
                    features=window.features,
                    target=window.target,
                    timestamp=window.timestamp,
                    sample_idx=i,
                )
                self._samples.append(sample)

        # 分割数据集
        self._split_dataset()

        # 计算数据集哈希
        self._compute_dataset_hash()

        self._fitted = True

    def _split_dataset(self) -> None:
        """分割数据集 (DL.DATA.DATASET.SPLIT).

        时序分割，确保训练集在前，验证集在中，测试集在后。
        """
        n_samples = len(self._samples)
        gap = self.config.gap

        # 计算各集合大小
        train_size = int(n_samples * self.config.train_ratio)
        val_size = int(n_samples * self.config.val_ratio)

        # 考虑间隔
        train_end = train_size
        val_start = train_end + gap
        val_end = val_start + val_size
        test_start = val_end + gap

        # 创建索引
        self._train_indices = np.arange(0, train_end, dtype=np.int64)
        self._val_indices = np.arange(
            val_start, min(val_end, n_samples), dtype=np.int64
        )
        self._test_indices = np.arange(test_start, n_samples, dtype=np.int64)

        # 打乱训练集(验证集和测试集保持时序)
        if self.config.shuffle:
            self._rng.shuffle(self._train_indices)

    def _compute_dataset_hash(self) -> None:
        """计算数据集哈希 (M7)."""
        hasher = hashlib.sha256()
        for sample in self._samples:
            hasher.update(sample.features.tobytes())
            hasher.update(np.array([sample.target], dtype=np.float32).tobytes())
        self._dataset_hash = hasher.hexdigest()[:32]

    def get_splits(
        self,
    ) -> tuple[list[FinancialSample], list[FinancialSample], list[FinancialSample]]:
        """获取训练/验证/测试集.

        Returns:
            (train_samples, val_samples, test_samples)
        """
        if not self._fitted:
            raise RuntimeError("Dataset not fitted. Call fit() first.")

        train = [self._samples[i] for i in self._train_indices]
        val = [self._samples[i] for i in self._val_indices]
        test = [self._samples[i] for i in self._test_indices]

        return train, val, test

    def get_all_samples(self) -> list[FinancialSample]:
        """获取所有样本.

        Returns:
            所有样本列表
        """
        return self._samples.copy()

    def get_dataset_hash(self) -> str:
        """获取数据集哈希 (M7).

        Returns:
            数据集哈希值
        """
        return self._dataset_hash

    def get_split_info(self) -> dict[str, int]:
        """获取分割信息.

        Returns:
            分割统计信息
        """
        return {
            "total": len(self._samples),
            "train": len(self._train_indices),
            "val": len(self._val_indices),
            "test": len(self._test_indices),
        }

    def reset(self) -> None:
        """重置数据集状态."""
        self._rng = np.random.RandomState(self.config.seed)
        self._samples.clear()
        self._train_indices = np.array([], dtype=np.int64)
        self._val_indices = np.array([], dtype=np.int64)
        self._test_indices = np.array([], dtype=np.int64)
        self._fitted = False
        self._dataset_hash = ""
        self.sequence_handler.reset()


def create_dataset(
    bars: PySequence[Bar1m],
    targets: PySequence[float],
    config: DatasetConfig | None = None,
) -> FinancialDataset:
    """创建数据集的便捷函数.

    Args:
        bars: K线数据
        targets: 目标值
        config: 数据集配置

    Returns:
        拟合好的数据集
    """
    dataset = FinancialDataset(config)
    dataset.fit(bars, targets)
    return dataset


class TorchFinancialDataset:
    """PyTorch兼容的金融数据集.

    将FinancialSample转换为PyTorch张量。

    Example:
        >>> samples = dataset.get_all_samples()
        >>> torch_dataset = TorchFinancialDataset(samples)
        >>> loader = DataLoader(torch_dataset, batch_size=32)
    """

    def __init__(self, samples: list[FinancialSample]) -> None:
        """初始化PyTorch数据集.

        Args:
            samples: 样本列表
        """
        self._samples = samples

    def __len__(self) -> int:
        """获取数据集大小."""
        return len(self._samples)

    def __getitem__(self, idx: int) -> tuple["torch.Tensor", "torch.Tensor"]:
        """获取单个样本.

        Args:
            idx: 样本索引

        Returns:
            (features, target) 张量元组
        """
        import torch

        sample = self._samples[idx]
        features = torch.from_numpy(sample.features)
        target = torch.tensor([sample.target], dtype=torch.float32)
        return features, target


def create_torch_dataloaders(
    dataset: FinancialDataset,
    batch_size: int = 32,
    num_workers: int = 0,
) -> tuple["torch.utils.data.DataLoader", "torch.utils.data.DataLoader", "torch.utils.data.DataLoader"]:
    """创建PyTorch DataLoader.

    Args:
        dataset: 金融数据集
        batch_size: 批大小
        num_workers: 工作进程数

    Returns:
        (train_loader, val_loader, test_loader)
    """
    from torch.utils.data import DataLoader

    train_samples, val_samples, test_samples = dataset.get_splits()

    train_loader = DataLoader(
        TorchFinancialDataset(train_samples),
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
    )
    val_loader = DataLoader(
        TorchFinancialDataset(val_samples),
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )
    test_loader = DataLoader(
        TorchFinancialDataset(test_samples),
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    return train_loader, val_loader, test_loader
