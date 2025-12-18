"""CV基础模块测试.

V4PRO Platform Component - Phase K B类模型层
军规覆盖: M3(完整审计), M7(回放一致), M19(风险归因)

V4PRO Scenarios:
- K37: CV.BASE.DETERMINISTIC - CV分割确定性
- K38: CV.BASE.AUDIT_LOG - CV验证审计
- K39: CV.BASE.NO_LEAKAGE - 数据泄露检测
- K40: CV.WALK.EXPANDING - 扩展窗口验证
- K41: CV.WALK.ROLLING - 滚动窗口验证
- K42: CV.WALK.ANCHORED - 锚定窗口验证
- K43: CV.PURGED.BASIC - 基础净化K折
- K44: CV.PURGED.EMBARGO - 禁运期净化
- K45: CV.PURGED.COMBINATORIAL - 组合净化
- K46: CV.METRICS.SHARPE - 夏普比率验证
- K47: CV.METRICS.DRAWDOWN - 最大回撤验证
- K48: CV.METRICS.STABILITY - 稳定性验证
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from src.strategy.cv.base import CVConfig, CVSplit, CrossValidator
from src.strategy.cv.walk_forward import (
    WalkForwardConfig,
    WalkForwardCV,
    WindowType,
)
from src.strategy.cv.purged_kfold import (
    PurgedKFoldConfig,
    PurgedKFoldCV,
)
from src.strategy.cv.metrics import (
    CVMetrics,
    compute_cv_metrics,
    compute_sharpe_ratio,
    compute_max_drawdown,
    compute_sortino_ratio,
    compute_var,
    compute_cvar,
    compute_stability_score,
    compute_win_rate,
    compute_profit_factor,
)


class SimpleCrossValidator(CrossValidator):
    """简单CV实现(用于测试)."""

    def split(self, n_samples: int):
        """生成简单分割."""
        fold_size = n_samples // self.config.n_splits
        for i in range(self.config.n_splits):
            test_start = i * fold_size
            test_end = (i + 1) * fold_size if i < self.config.n_splits - 1 else n_samples

            test_indices = np.arange(test_start, test_end, dtype=np.int64)
            train_indices = np.concatenate([
                np.arange(0, test_start, dtype=np.int64),
                np.arange(test_end, n_samples, dtype=np.int64),
            ])

            split = CVSplit(
                fold_idx=i,
                train_indices=train_indices,
                test_indices=test_indices,
            )
            self.log_split(split)
            yield split

    def get_n_splits(self):
        """获取分割数量."""
        return self.config.n_splits


class TestCVBaseDeterministic:
    """K37: CV.BASE.DETERMINISTIC - CV分割确定性测试."""

    def test_split_deterministic(self) -> None:
        """测试分割确定性."""
        config = CVConfig(n_splits=5, seed=42, deterministic=True)

        cv1 = SimpleCrossValidator(config)
        cv2 = SimpleCrossValidator(config)

        splits1 = list(cv1.split(100))
        splits2 = list(cv2.split(100))

        assert len(splits1) == len(splits2)
        for s1, s2 in zip(splits1, splits2, strict=True):
            assert s1.split_hash == s2.split_hash

    def test_split_hash_reproducible(self) -> None:
        """测试分割哈希可重现."""
        train_indices = np.arange(0, 80, dtype=np.int64)
        test_indices = np.arange(80, 100, dtype=np.int64)

        split1 = CVSplit(
            fold_idx=0,
            train_indices=train_indices,
            test_indices=test_indices,
        )
        split2 = CVSplit(
            fold_idx=0,
            train_indices=train_indices.copy(),
            test_indices=test_indices.copy(),
        )

        assert split1.split_hash == split2.split_hash
        assert len(split1.split_hash) == 16

    def test_reset_deterministic(self) -> None:
        """测试重置后确定性."""
        config = CVConfig(n_splits=3, seed=42, deterministic=True)
        cv = SimpleCrossValidator(config)

        splits1 = list(cv.split(60))
        cv.reset()
        splits2 = list(cv.split(60))

        for s1, s2 in zip(splits1, splits2, strict=True):
            assert s1.split_hash == s2.split_hash


class TestCVBaseAuditLog:
    """K38: CV.BASE.AUDIT_LOG - CV验证审计测试."""

    def test_split_logging(self) -> None:
        """测试分割日志记录 (M3)."""
        config = CVConfig(n_splits=5, log_splits=True)
        cv = SimpleCrossValidator(config)

        list(cv.split(100))

        log = cv.get_split_log()
        assert len(log) == 5
        assert all("fold_idx" in entry for entry in log)
        assert all("split_hash" in entry for entry in log)

    def test_log_contains_period(self) -> None:
        """测试日志包含时间段."""
        config = CVConfig(n_splits=3, log_splits=True)
        cv = SimpleCrossValidator(config)

        list(cv.split(90))

        log = cv.get_split_log()
        for entry in log:
            assert "train_period" in entry
            assert "test_period" in entry
            assert "train_size" in entry
            assert "test_size" in entry

    def test_log_no_leakage_check(self) -> None:
        """测试日志包含泄露检查."""
        config = CVConfig(n_splits=3, log_splits=True)
        cv = SimpleCrossValidator(config)

        list(cv.split(90))

        log = cv.get_split_log()
        for entry in log:
            assert "no_leakage" in entry
            assert entry["no_leakage"] is True  # 简单CV无泄露


class TestCVBaseNoLeakage:
    """K39: CV.BASE.NO_LEAKAGE - 数据泄露检测测试."""

    def test_no_overlap_detection(self) -> None:
        """测试无重叠检测."""
        config = CVConfig(n_splits=3)
        cv = SimpleCrossValidator(config)

        # 正常分割
        split = CVSplit(
            fold_idx=0,
            train_indices=np.arange(0, 60, dtype=np.int64),
            test_indices=np.arange(60, 90, dtype=np.int64),
        )

        assert cv.validate_no_leakage(split)

    def test_overlap_detection(self) -> None:
        """测试重叠检测."""
        config = CVConfig(n_splits=3)
        cv = SimpleCrossValidator(config)

        # 有重叠的分割
        split = CVSplit(
            fold_idx=0,
            train_indices=np.arange(0, 70, dtype=np.int64),  # 包含60-70
            test_indices=np.arange(60, 90, dtype=np.int64),  # 包含60-70
        )

        assert not cv.validate_no_leakage(split)

    def test_gap_validation(self) -> None:
        """测试间隔验证."""
        config = CVConfig(n_splits=3, gap=5)
        cv = SimpleCrossValidator(config)

        # 无间隔 - 应检测为泄露
        split_no_gap = CVSplit(
            fold_idx=0,
            train_indices=np.arange(0, 60, dtype=np.int64),
            test_indices=np.arange(60, 90, dtype=np.int64),
        )

        # 有间隔 - 应无泄露
        split_with_gap = CVSplit(
            fold_idx=0,
            train_indices=np.arange(0, 55, dtype=np.int64),  # 训练到55
            test_indices=np.arange(60, 90, dtype=np.int64),  # 测试从60开始
        )

        assert not cv.validate_no_leakage(split_no_gap)  # gap=5但实际gap=0
        assert cv.validate_no_leakage(split_with_gap)  # 实际gap=5


class TestWalkForwardExpanding:
    """K40: CV.WALK.EXPANDING - 扩展窗口验证测试."""

    def test_expanding_window(self) -> None:
        """测试扩展窗口分割."""
        config = WalkForwardConfig(
            window_type=WindowType.EXPANDING,
            min_train_size=50,
            test_size_int=20,
            step_size=20,
        )
        cv = WalkForwardCV(config)

        splits = list(cv.split(150))

        # 验证训练集递增
        train_sizes = [len(s.train_indices) for s in splits]
        for i in range(1, len(train_sizes)):
            assert train_sizes[i] >= train_sizes[i - 1]

    def test_expanding_no_leakage(self) -> None:
        """测试扩展窗口无泄露."""
        config = WalkForwardConfig(
            window_type=WindowType.EXPANDING,
            min_train_size=50,
            test_size_int=20,
            step_size=20,
        )
        cv = WalkForwardCV(config)

        for split in cv.split(150):
            assert cv.validate_no_leakage(split)
            # 训练集应在测试集之前
            assert split.train_end < split.test_start


class TestWalkForwardRolling:
    """K41: CV.WALK.ROLLING - 滚动窗口验证测试."""

    def test_rolling_window(self) -> None:
        """测试滚动窗口分割."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_size=50,
            test_size_int=20,
            step_size=20,
        )
        cv = WalkForwardCV(config)

        splits = list(cv.split(150))

        # 验证训练集大小固定
        train_sizes = [len(s.train_indices) for s in splits]
        assert all(size == 50 for size in train_sizes)

    def test_rolling_window_moves(self) -> None:
        """测试滚动窗口移动."""
        config = WalkForwardConfig(
            window_type=WindowType.ROLLING,
            train_size=50,
            test_size_int=20,
            step_size=20,
        )
        cv = WalkForwardCV(config)

        splits = list(cv.split(150))

        # 验证窗口向前移动
        if len(splits) >= 2:
            assert splits[1].train_start > splits[0].train_start
            assert splits[1].test_start > splits[0].test_start


class TestWalkForwardAnchored:
    """K42: CV.WALK.ANCHORED - 锚定窗口验证测试."""

    def test_anchored_window(self) -> None:
        """测试锚定窗口分割."""
        config = WalkForwardConfig(
            window_type=WindowType.ANCHORED,
            n_splits=3,
            min_train_size=30,
            test_size_int=20,
            step_size=20,
        )
        cv = WalkForwardCV(config)

        splits = list(cv.split(150))

        # 验证测试集在最后
        for split in splits:
            assert split.test_end == 150


class TestPurgedKFoldBasic:
    """K43: CV.PURGED.BASIC - 基础净化K折测试."""

    def test_purged_kfold_splits(self) -> None:
        """测试净化K折分割."""
        config = PurgedKFoldConfig(n_splits=5, purge_gap=5)
        cv = PurgedKFoldCV(config)

        splits = list(cv.split(100))

        assert len(splits) == 5
        for split in splits:
            assert len(split.train_indices) > 0
            assert len(split.test_indices) > 0

    def test_purge_gap_applied(self) -> None:
        """测试净化间隔应用."""
        config = PurgedKFoldConfig(n_splits=5, purge_gap=10)
        cv = PurgedKFoldCV(config)

        splits = list(cv.split(100))

        for split in splits:
            # 训练集不应包含测试集前purge_gap个样本
            train_set = set(split.train_indices.tolist())
            test_min = int(split.test_indices.min())

            for i in range(max(0, test_min - 10), test_min):
                assert i not in train_set

    def test_no_overlap(self) -> None:
        """测试无重叠."""
        config = PurgedKFoldConfig(n_splits=5)
        cv = PurgedKFoldCV(config)

        splits = list(cv.split(100))

        for split in splits:
            train_set = set(split.train_indices.tolist())
            test_set = set(split.test_indices.tolist())
            assert len(train_set & test_set) == 0


class TestPurgedKFoldEmbargo:
    """K44: CV.PURGED.EMBARGO - 禁运期净化测试."""

    def test_embargo_applied(self) -> None:
        """测试禁运期应用."""
        config = PurgedKFoldConfig(n_splits=5, embargo_pct=0.05)
        cv = PurgedKFoldCV(config)

        splits = list(cv.split(100))

        for split in splits:
            # 训练集不应包含测试集后embargo_pct的样本
            train_set = set(split.train_indices.tolist())
            test_max = int(split.test_indices.max())
            embargo_size = 5  # 100 * 0.05

            for i in range(test_max + 1, min(100, test_max + 1 + embargo_size)):
                assert i not in train_set

    def test_purge_info(self) -> None:
        """测试净化信息."""
        config = PurgedKFoldConfig(n_splits=5, purge_gap=5, embargo_pct=0.02)
        cv = PurgedKFoldCV(config)

        info = cv.get_purge_info(0, 100)

        assert "purge_start" in info
        assert "purge_end" in info
        assert "embargo_start" in info
        assert "embargo_end" in info
        assert info["purge_samples"] <= config.purge_gap


class TestPurgedKFoldCombinatorial:
    """K45: CV.PURGED.COMBINATORIAL - 组合净化测试."""

    def test_group_based_split(self) -> None:
        """测试基于组的分割."""
        config = PurgedKFoldConfig(n_splits=3, purge_gap=1, embargo_pct=0.1)
        cv = PurgedKFoldCV(config)

        # 创建组标签 (每10个样本一组)
        groups = np.repeat(np.arange(10), 10).astype(np.int64)  # 100样本,10组

        splits = list(cv.split_with_groups(100, groups))

        # 验证每个分割
        for split in splits:
            train_groups = set(groups[split.train_indices].tolist())
            test_groups = set(groups[split.test_indices].tolist())

            # 训练组和测试组不应重叠
            assert len(train_groups & test_groups) == 0


class TestCVMetricsSharpe:
    """K46: CV.METRICS.SHARPE - 夏普比率验证测试."""

    def test_sharpe_positive(self) -> None:
        """测试正收益夏普比率."""
        # 模拟正收益序列
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)  # 日均0.1%,波动1%

        sharpe = compute_sharpe_ratio(returns)

        assert sharpe > 0

    def test_sharpe_negative(self) -> None:
        """测试负收益夏普比率."""
        np.random.seed(42)
        returns = np.random.normal(-0.001, 0.01, 252)  # 日均-0.1%

        sharpe = compute_sharpe_ratio(returns)

        assert sharpe < 0

    def test_sharpe_with_risk_free(self) -> None:
        """测试带无风险利率的夏普."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)

        sharpe_no_rf = compute_sharpe_ratio(returns, risk_free_rate=0.0)
        sharpe_with_rf = compute_sharpe_ratio(returns, risk_free_rate=0.03)  # 3%年化

        # 有无风险利率时夏普应更低
        assert sharpe_with_rf < sharpe_no_rf

    def test_sortino_ratio(self) -> None:
        """测试索提诺比率."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.01, 252)

        sortino = compute_sortino_ratio(returns)

        # 索提诺只考虑下行风险,通常比夏普高
        assert sortino != 0


class TestCVMetricsDrawdown:
    """K47: CV.METRICS.DRAWDOWN - 最大回撤验证测试."""

    def test_max_drawdown_basic(self) -> None:
        """测试基本最大回撤计算."""
        # 简单序列: 上涨后下跌
        returns = np.array([0.1, 0.1, -0.15, -0.1, 0.05])

        mdd = compute_max_drawdown(returns)

        assert mdd > 0
        assert mdd < 1

    def test_max_drawdown_no_loss(self) -> None:
        """测试无亏损时的最大回撤."""
        returns = np.array([0.01, 0.02, 0.01, 0.03, 0.02])

        mdd = compute_max_drawdown(returns)

        # 只上涨应有微小回撤或0
        assert mdd >= 0
        assert mdd < 0.1

    def test_var_cvar(self) -> None:
        """测试VaR和CVaR."""
        np.random.seed(42)
        returns = np.random.normal(0, 0.02, 1000)

        var = compute_var(returns, confidence=0.95)
        cvar = compute_cvar(returns, confidence=0.95)

        # CVaR应大于等于VaR
        assert cvar >= var
        assert var > 0  # 正数表示损失


class TestCVMetricsStability:
    """K48: CV.METRICS.STABILITY - 稳定性验证测试."""

    def test_stability_score_consistent(self) -> None:
        """测试一致分数的稳定性."""
        # 非常一致的分数
        consistent_scores = [0.5, 0.51, 0.49, 0.5, 0.5]

        stability = compute_stability_score(consistent_scores)

        assert stability > 0.8

    def test_stability_score_inconsistent(self) -> None:
        """测试不一致分数的稳定性."""
        # 变化大的分数
        inconsistent_scores = [0.1, 0.9, 0.2, 0.8, 0.3]

        stability = compute_stability_score(inconsistent_scores)

        assert stability < 0.5

    def test_win_rate(self) -> None:
        """测试胜率计算."""
        returns = np.array([0.01, -0.01, 0.02, -0.02, 0.01, 0.01])

        win_rate = compute_win_rate(returns)

        assert win_rate == 4 / 6  # 4胜2负

    def test_profit_factor(self) -> None:
        """测试盈亏比计算."""
        returns = np.array([0.02, -0.01, 0.03, -0.01])

        pf = compute_profit_factor(returns)

        # (0.02 + 0.03) / (0.01 + 0.01) = 2.5
        assert abs(pf - 2.5) < 0.01


class TestCVMetricsComplete:
    """CV完整指标测试."""

    def test_compute_cv_metrics(self) -> None:
        """测试完整指标计算."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.015, 252)
        fold_scores = [0.52, 0.48, 0.51, 0.49, 0.50]

        metrics = compute_cv_metrics(returns, fold_scores)

        assert isinstance(metrics, CVMetrics)
        assert metrics.sharpe_ratio != 0
        assert metrics.max_drawdown > 0
        assert 0 <= metrics.win_rate <= 1
        assert metrics.n_folds == 5
        assert metrics.stability_score > 0

    def test_metrics_empty_returns(self) -> None:
        """测试空收益的指标."""
        returns = np.array([], dtype=np.float64)

        metrics = compute_cv_metrics(returns)

        assert metrics.mean_return == 0.0
        assert metrics.sharpe_ratio == 0.0


class TestCVIntegration:
    """CV集成测试."""

    def test_walk_forward_with_metrics(self) -> None:
        """测试Walk-Forward与指标集成."""
        config = WalkForwardConfig(
            window_type=WindowType.EXPANDING,
            min_train_size=50,
            test_size_int=20,
            step_size=20,
        )
        cv = WalkForwardCV(config)

        splits = list(cv.split(150))
        fold_scores = []

        for split in splits:
            # 模拟每折评估
            np.random.seed(split.fold_idx)
            score = np.random.uniform(0.45, 0.55)
            fold_scores.append(score)

        # 计算指标
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, 252)
        metrics = compute_cv_metrics(returns, fold_scores)

        assert metrics.n_folds == len(splits)
        assert len(metrics.fold_scores) == len(splits)

    def test_purged_kfold_with_metrics(self) -> None:
        """测试Purged K-Fold与指标集成."""
        config = PurgedKFoldConfig(n_splits=5, purge_gap=5)
        cv = PurgedKFoldCV(config)

        splits = list(cv.split(100))

        # 验证所有分割
        for split in splits:
            log = cv.get_split_log()
            entry = [e for e in log if e["fold_idx"] == split.fold_idx][0]
            assert entry["no_leakage"] is True
