"""交叉验证基础模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致), M19(风险归因)

V4PRO Scenarios:
- K37: CV.BASE.DETERMINISTIC - CV分割确定性
- K38: CV.BASE.AUDIT_LOG - CV验证审计
- K39: CV.BASE.NO_LEAKAGE - 数据泄露检测
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class CVConfig:
    """交叉验证配置 (带军规约束)."""

    # 基础配置
    n_splits: int = 5
    test_size: float = 0.2

    # M7: 确定性配置
    seed: int = 42
    deterministic: bool = True

    # M3: 审计配置
    log_splits: bool = True

    # 数据泄露防护
    gap: int = 0  # 训练集和测试集之间的间隔
    purge_gap: int = 0  # 净化间隔(防止前瞻偏差)


@dataclass
class CVSplit:
    """单次分割结果."""

    fold_idx: int
    train_indices: NDArray[np.int64]
    test_indices: NDArray[np.int64]

    # M3: 审计信息
    train_start: int = 0
    train_end: int = 0
    test_start: int = 0
    test_end: int = 0

    # M7: 分割哈希
    split_hash: str = ""

    def __post_init__(self) -> None:
        """计算分割哈希."""
        if not self.split_hash:
            combined = np.concatenate([
                self.train_indices,
                self.test_indices,
            ])
            self.split_hash = hashlib.sha256(
                combined.tobytes()
            ).hexdigest()[:16]

        # 记录边界
        if len(self.train_indices) > 0:
            self.train_start = int(self.train_indices[0])
            self.train_end = int(self.train_indices[-1])
        if len(self.test_indices) > 0:
            self.test_start = int(self.test_indices[0])
            self.test_end = int(self.test_indices[-1])


@dataclass
class CVResult:
    """交叉验证结果."""

    fold_idx: int
    train_score: float
    test_score: float
    train_size: int
    test_size: int

    # 详细指标
    metrics: dict[str, float] = field(default_factory=dict)

    # M3: 审计信息
    split_hash: str = ""
    train_period: tuple[int, int] = (0, 0)
    test_period: tuple[int, int] = (0, 0)


class CrossValidator(ABC):
    """交叉验证基类 (军规级).

    所有CV方法必须继承此类，确保符合军规要求:
    - M7: 确定性分割 (相同数据相同分割)
    - M3: 完整审计日志
    - M19: 风险归因追踪
    """

    def __init__(self, config: CVConfig) -> None:
        """初始化交叉验证器.

        Args:
            config: CV配置
        """
        self.config = config

        # M7: 确定性随机数
        if config.deterministic:
            self._rng = np.random.RandomState(config.seed)
        else:
            self._rng = np.random.RandomState()

        # M3: 审计日志
        self._split_log: list[dict[str, Any]] = []

    @abstractmethod
    def split(
        self, n_samples: int
    ) -> Iterator[CVSplit]:
        """生成分割 (K37 确定性).

        Args:
            n_samples: 样本数量

        Yields:
            CVSplit对象
        """
        ...

    @abstractmethod
    def get_n_splits(self) -> int:
        """获取分割数量.

        Returns:
            分割数量
        """
        ...

    def validate_no_leakage(self, split: CVSplit) -> bool:
        """验证无数据泄露 (K39).

        Args:
            split: 分割对象

        Returns:
            是否无泄露
        """
        train_set = set(split.train_indices.tolist())
        test_set = set(split.test_indices.tolist())

        # 检查交集
        overlap = train_set & test_set
        if overlap:
            return False

        # 检查时序: 训练集应在测试集之前
        if len(split.train_indices) > 0 and len(split.test_indices) > 0:
            train_max = int(split.train_indices.max())
            test_min = int(split.test_indices.min())

            # 考虑gap
            if train_max + self.config.gap >= test_min:
                return False

        return True

    def log_split(self, split: CVSplit) -> None:
        """记录分割日志 (K38 审计).

        Args:
            split: 分割对象
        """
        if not self.config.log_splits:
            return

        log_entry = {
            "fold_idx": split.fold_idx,
            "train_size": len(split.train_indices),
            "test_size": len(split.test_indices),
            "train_period": (split.train_start, split.train_end),
            "test_period": (split.test_start, split.test_end),
            "split_hash": split.split_hash,
            "no_leakage": self.validate_no_leakage(split),
        }
        self._split_log.append(log_entry)

    def get_split_log(self) -> list[dict[str, Any]]:
        """获取分割日志 (M3).

        Returns:
            分割日志列表
        """
        return self._split_log.copy()

    def compute_split_hash(
        self,
        train_indices: NDArray[np.int64],
        test_indices: NDArray[np.int64],
    ) -> str:
        """计算分割哈希 (M7).

        Args:
            train_indices: 训练索引
            test_indices: 测试索引

        Returns:
            分割哈希值
        """
        combined = np.concatenate([train_indices, test_indices])
        return hashlib.sha256(combined.tobytes()).hexdigest()[:16]

    def reset(self) -> None:
        """重置验证器状态."""
        if self.config.deterministic:
            self._rng = np.random.RandomState(self.config.seed)
        self._split_log.clear()
