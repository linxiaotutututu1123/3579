"""净化K折交叉验证模块.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致), M19(风险归因)

V4PRO Scenarios:
- K43: CV.PURGED.BASIC - 基础净化K折
- K44: CV.PURGED.EMBARGO - 禁运期净化
- K45: CV.PURGED.COMBINATORIAL - 组合净化
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np
from numpy.typing import NDArray

from src.strategy.cv.base import CVConfig, CVSplit, CrossValidator


@dataclass
class PurgedKFoldConfig(CVConfig):
    """净化K折配置."""

    # 净化参数
    purge_gap: int = 5  # 净化间隔(防止前瞻偏差)
    embargo_pct: float = 0.01  # 禁运期百分比

    # 分组
    n_splits: int = 5  # K折数量


class PurgedKFoldCV(CrossValidator):
    """净化K折交叉验证 (K43-K45).

    针对金融时间序列的特殊K折验证:
    - 净化(Purge): 移除训练集中与测试集时间重叠的样本
    - 禁运(Embargo): 在测试集后添加禁运期,防止前瞻偏差

    参考: Advances in Financial Machine Learning (Marcos López de Prado)
    """

    def __init__(self, config: PurgedKFoldConfig) -> None:
        """初始化净化K折验证器.

        Args:
            config: 配置
        """
        super().__init__(config)
        self._pk_config = config

    def split(self, n_samples: int) -> Iterator[CVSplit]:
        """生成分割 (K43-K45).

        Args:
            n_samples: 样本数量

        Yields:
            CVSplit对象
        """
        config = self._pk_config
        indices = np.arange(n_samples, dtype=np.int64)

        # 计算每折大小
        fold_size = n_samples // config.n_splits

        for fold_idx in range(config.n_splits):
            # 测试集范围
            test_start = fold_idx * fold_size
            test_end = (fold_idx + 1) * fold_size if fold_idx < config.n_splits - 1 else n_samples

            test_indices = indices[test_start:test_end]

            # 计算禁运期
            embargo_size = int(n_samples * config.embargo_pct)

            # 训练集: 排除测试集、净化区和禁运期
            train_mask = np.ones(n_samples, dtype=bool)

            # 排除测试集
            train_mask[test_start:test_end] = False

            # 排除净化区(测试集前的purge_gap个样本)
            purge_start = max(0, test_start - config.purge_gap)
            train_mask[purge_start:test_start] = False

            # 排除禁运期(测试集后的embargo_size个样本)
            embargo_end = min(n_samples, test_end + embargo_size)
            train_mask[test_end:embargo_end] = False

            train_indices = indices[train_mask]

            split = CVSplit(
                fold_idx=fold_idx,
                train_indices=train_indices,
                test_indices=test_indices,
            )

            # M3: 记录日志
            self.log_split(split)

            yield split

    def get_n_splits(self) -> int:
        """获取分割数量.

        Returns:
            K折数量
        """
        return self._pk_config.n_splits

    def split_with_groups(
        self,
        n_samples: int,
        groups: NDArray[np.int64],
    ) -> Iterator[CVSplit]:
        """按组分割 (K45 组合净化).

        Args:
            n_samples: 样本数量
            groups: 组标签数组

        Yields:
            CVSplit对象
        """
        config = self._pk_config
        unique_groups = np.unique(groups)
        n_groups = len(unique_groups)

        # 按组数量划分K折
        groups_per_fold = n_groups // config.n_splits

        for fold_idx in range(config.n_splits):
            # 测试组
            test_group_start = fold_idx * groups_per_fold
            test_group_end = (
                (fold_idx + 1) * groups_per_fold
                if fold_idx < config.n_splits - 1
                else n_groups
            )
            test_groups = set(unique_groups[test_group_start:test_group_end].tolist())

            # 计算净化和禁运组
            purge_groups: set[int] = set()
            embargo_groups: set[int] = set()

            # 净化: 测试组之前的purge_gap个组
            purge_start = max(0, test_group_start - config.purge_gap)
            for g in unique_groups[purge_start:test_group_start]:
                purge_groups.add(int(g))

            # 禁运: 测试组之后的embargo个组
            embargo_count = max(1, int(n_groups * config.embargo_pct))
            embargo_end = min(n_groups, test_group_end + embargo_count)
            for g in unique_groups[test_group_end:embargo_end]:
                embargo_groups.add(int(g))

            # 构建训练和测试索引
            excluded_groups = test_groups | purge_groups | embargo_groups
            train_mask = ~np.isin(groups, list(excluded_groups))
            test_mask = np.isin(groups, list(test_groups))

            train_indices = np.where(train_mask)[0].astype(np.int64)
            test_indices = np.where(test_mask)[0].astype(np.int64)

            split = CVSplit(
                fold_idx=fold_idx,
                train_indices=train_indices,
                test_indices=test_indices,
            )

            self.log_split(split)
            yield split

    def get_purge_info(
        self,
        fold_idx: int,
        n_samples: int,
    ) -> dict[str, int]:
        """获取净化信息.

        Args:
            fold_idx: 折索引
            n_samples: 样本数量

        Returns:
            净化信息字典
        """
        config = self._pk_config
        fold_size = n_samples // config.n_splits

        test_start = fold_idx * fold_size
        test_end = (fold_idx + 1) * fold_size if fold_idx < config.n_splits - 1 else n_samples

        purge_start = max(0, test_start - config.purge_gap)
        embargo_size = int(n_samples * config.embargo_pct)
        embargo_end = min(n_samples, test_end + embargo_size)

        return {
            "test_start": test_start,
            "test_end": test_end,
            "purge_start": purge_start,
            "purge_end": test_start,
            "embargo_start": test_end,
            "embargo_end": embargo_end,
            "purge_samples": test_start - purge_start,
            "embargo_samples": embargo_end - test_end,
        }
