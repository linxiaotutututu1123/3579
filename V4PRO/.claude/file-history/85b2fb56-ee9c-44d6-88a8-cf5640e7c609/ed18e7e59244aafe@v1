"""滚动窗口交叉验证模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致)

V4PRO Scenarios:
- K40: CV.WALK.EXPANDING - 扩展窗口验证
- K41: CV.WALK.ROLLING - 滚动窗口验证
- K42: CV.WALK.ANCHORED - 锚定窗口验证
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterator

import numpy as np
from numpy.typing import NDArray

from src.strategy.cv.base import CVConfig, CVSplit, CrossValidator


class WindowType(Enum):
    """窗口类型."""

    EXPANDING = "expanding"  # 扩展窗口: 起点固定,终点移动
    ROLLING = "rolling"  # 滚动窗口: 固定大小窗口移动
    ANCHORED = "anchored"  # 锚定窗口: 多个起点,共同终点


@dataclass
class WalkForwardConfig(CVConfig):
    """滚动窗口配置."""

    window_type: WindowType = WindowType.EXPANDING

    # 窗口参数
    min_train_size: int = 100  # 最小训练集大小
    train_size: int = 0  # 固定训练集大小(rolling模式)
    test_size_int: int = 50  # 测试集大小(整数)
    step_size: int = 50  # 步进大小

    # 间隔配置
    gap: int = 0  # 训练测试间隔
    purge_gap: int = 0  # 净化间隔


class WalkForwardCV(CrossValidator):
    """滚动窗口交叉验证 (K40-K42).

    支持三种窗口类型:
    - EXPANDING: 扩展窗口,训练集不断增大
    - ROLLING: 滚动窗口,训练集固定大小
    - ANCHORED: 锚定窗口,多个固定起点
    """

    def __init__(self, config: WalkForwardConfig) -> None:
        """初始化滚动窗口验证器.

        Args:
            config: 配置
        """
        super().__init__(config)
        self._wf_config = config

    def split(self, n_samples: int) -> Iterator[CVSplit]:
        """生成分割 (K40-K42).

        Args:
            n_samples: 样本数量

        Yields:
            CVSplit对象
        """
        config = self._wf_config

        if config.window_type == WindowType.EXPANDING:
            yield from self._expanding_split(n_samples)
        elif config.window_type == WindowType.ROLLING:
            yield from self._rolling_split(n_samples)
        elif config.window_type == WindowType.ANCHORED:
            yield from self._anchored_split(n_samples)

    def _expanding_split(self, n_samples: int) -> Iterator[CVSplit]:
        """扩展窗口分割 (K40).

        训练集从min_train_size开始,每次扩展step_size.

        Args:
            n_samples: 样本数量

        Yields:
            CVSplit对象
        """
        config = self._wf_config
        fold_idx = 0

        train_end = config.min_train_size

        while train_end + config.gap + config.test_size_int <= n_samples:
            # 训练索引: [0, train_end)
            train_indices = np.arange(0, train_end, dtype=np.int64)

            # 测试索引: [train_end + gap, train_end + gap + test_size)
            test_start = train_end + config.gap
            test_end = test_start + config.test_size_int
            test_indices = np.arange(test_start, test_end, dtype=np.int64)

            split = CVSplit(
                fold_idx=fold_idx,
                train_indices=train_indices,
                test_indices=test_indices,
            )

            # M3: 记录日志
            self.log_split(split)

            yield split

            fold_idx += 1
            train_end += config.step_size

    def _rolling_split(self, n_samples: int) -> Iterator[CVSplit]:
        """滚动窗口分割 (K41).

        固定大小的训练窗口向前滚动.

        Args:
            n_samples: 样本数量

        Yields:
            CVSplit对象
        """
        config = self._wf_config
        train_size = config.train_size or config.min_train_size
        fold_idx = 0

        train_start = 0

        while train_start + train_size + config.gap + config.test_size_int <= n_samples:
            # 训练索引
            train_end = train_start + train_size
            train_indices = np.arange(train_start, train_end, dtype=np.int64)

            # 测试索引
            test_start = train_end + config.gap
            test_end = test_start + config.test_size_int
            test_indices = np.arange(test_start, test_end, dtype=np.int64)

            split = CVSplit(
                fold_idx=fold_idx,
                train_indices=train_indices,
                test_indices=test_indices,
            )

            self.log_split(split)
            yield split

            fold_idx += 1
            train_start += config.step_size

    def _anchored_split(self, n_samples: int) -> Iterator[CVSplit]:
        """锚定窗口分割 (K42).

        多个固定起点,测试集在最后.

        Args:
            n_samples: 样本数量

        Yields:
            CVSplit对象
        """
        config = self._wf_config

        # 测试集固定在最后
        test_start = n_samples - config.test_size_int
        test_end = n_samples
        test_indices = np.arange(test_start, test_end, dtype=np.int64)

        # 多个训练起点
        for fold_idx in range(config.n_splits):
            # 计算训练起点(均匀分布)
            train_start = (fold_idx * config.step_size) % (
                test_start - config.gap - config.min_train_size
            )
            train_end = test_start - config.gap

            if train_end - train_start < config.min_train_size:
                continue

            train_indices = np.arange(train_start, train_end, dtype=np.int64)

            split = CVSplit(
                fold_idx=fold_idx,
                train_indices=train_indices,
                test_indices=test_indices.copy(),
            )

            self.log_split(split)
            yield split

    def get_n_splits(self) -> int:
        """获取分割数量.

        注意: 实际分割数量取决于数据大小.

        Returns:
            估计分割数量
        """
        return self._wf_config.n_splits
