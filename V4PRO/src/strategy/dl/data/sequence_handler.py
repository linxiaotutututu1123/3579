"""序列数据处理模块.

V4PRO Platform Component - Phase 6 B类模型层
军规覆盖: M7(回放一致), M3(完整审计)

V4PRO Scenarios:
- DL.DATA.SEQ.BUILD - 序列构建确定性
- DL.DATA.SEQ.NORMALIZE - 序列标准化
- DL.DATA.SEQ.WINDOW - 滑动窗口生成
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence as PySequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray

from src.strategy.types import Bar1m


class NormalizationMethod(Enum):
    """标准化方法枚举."""

    NONE = "none"  # 无标准化
    ZSCORE = "zscore"  # Z-score标准化
    MINMAX = "minmax"  # Min-Max归一化
    LOG_RETURN = "log_return"  # 对数收益率
    ROBUST = "robust"  # 鲁棒标准化(使用中位数和IQR)


@dataclass
class SequenceConfig:
    """序列配置 (带军规约束).

    Attributes:
        window_size: 窗口大小
        stride: 滑动步长
        features: 特征列表
        normalization: 标准化方法
        deterministic: 是否确定性(M7)
        seed: 随机种子
        log_sequences: 是否记录日志(M3)
    """

    window_size: int = 60
    stride: int = 1
    features: tuple[str, ...] = ("returns", "volume", "range")
    normalization: NormalizationMethod = NormalizationMethod.ZSCORE
    deterministic: bool = True
    seed: int = 42
    log_sequences: bool = True

    def __post_init__(self) -> None:
        """验证配置参数."""
        if self.window_size < 1:
            raise ValueError("window_size must be positive")
        if self.stride < 1:
            raise ValueError("stride must be positive")


@dataclass
class SequenceWindow:
    """序列窗口结果.

    Attributes:
        features: 特征矩阵 (window_size, n_features)
        target: 目标值(可选)
        timestamp: 时间戳
        window_idx: 窗口索引
        window_hash: 窗口哈希(M7)
    """

    features: NDArray[np.float32]
    target: float | None = None
    timestamp: float = 0.0
    window_idx: int = 0
    window_hash: str = ""

    def __post_init__(self) -> None:
        """计算窗口哈希."""
        if not self.window_hash:
            self.window_hash = hashlib.sha256(
                self.features.tobytes()
            ).hexdigest()[:16]


class SequenceHandler:
    """序列数据处理器 (军规级).

    负责将原始K线数据转换为模型可用的序列特征。

    军规覆盖:
    - M7: 确定性窗口生成
    - M3: 完整审计日志

    Example:
        >>> config = SequenceConfig(window_size=60)
        >>> handler = SequenceHandler(config)
        >>> windows = handler.build_sequences(bars)
    """

    def __init__(self, config: SequenceConfig | None = None) -> None:
        """初始化序列处理器.

        Args:
            config: 序列配置，默认使用默认配置
        """
        self.config = config or SequenceConfig()

        # M7: 确定性随机数
        if self.config.deterministic:
            self._rng = np.random.RandomState(self.config.seed)
        else:
            self._rng = np.random.RandomState()

        # M3: 审计日志
        self._sequence_log: list[dict[str, Any]] = []

        # 标准化统计量缓存
        self._norm_stats: dict[str, dict[str, float]] = {}

    def build_sequences(
        self,
        bars: PySequence[Bar1m],
        targets: PySequence[float] | None = None,
    ) -> list[SequenceWindow]:
        """构建序列窗口 (DL.DATA.SEQ.BUILD).

        从原始K线数据构建滑动窗口序列。

        Args:
            bars: K线数据列表
            targets: 目标值列表(可选)

        Returns:
            SequenceWindow列表
        """
        n_bars = len(bars)
        window_size = self.config.window_size
        stride = self.config.stride

        if n_bars < window_size:
            return []

        # 预处理原始数据
        raw_features = self._extract_raw_features(bars)

        # 构建窗口
        windows: list[SequenceWindow] = []
        n_windows = (n_bars - window_size) // stride + 1

        for i in range(n_windows):
            start_idx = i * stride
            end_idx = start_idx + window_size

            # 提取窗口特征
            window_features = raw_features[start_idx:end_idx]

            # 标准化
            normalized = self._normalize_window(window_features)

            # 目标值
            target = targets[end_idx - 1] if targets else None

            # 时间戳(使用窗口最后一个bar的时间)
            timestamp = float(bars[end_idx - 1].get("ts", 0))

            window = SequenceWindow(
                features=normalized.astype(np.float32),
                target=target,
                timestamp=timestamp,
                window_idx=i,
            )
            windows.append(window)

            # M3: 记录日志
            if self.config.log_sequences:
                self._log_window(window, start_idx, end_idx)

        return windows

    def _extract_raw_features(
        self,
        bars: PySequence[Bar1m],
    ) -> NDArray[np.float64]:
        """提取原始特征.

        Args:
            bars: K线数据

        Returns:
            原始特征矩阵 (n_bars, n_features)
        """
        n_bars = len(bars)
        n_features = len(self.config.features)
        raw = np.zeros((n_bars, n_features), dtype=np.float64)

        closes = np.array(
            [float(b.get("close", 0)) for b in bars],
            dtype=np.float64,
        )
        volumes = np.array(
            [float(b.get("volume", 0)) for b in bars],
            dtype=np.float64,
        )
        highs = np.array(
            [float(b.get("high", 0)) for b in bars],
            dtype=np.float64,
        )
        lows = np.array(
            [float(b.get("low", 0)) for b in bars],
            dtype=np.float64,
        )
        opens = np.array(
            [float(b.get("open", 0)) for b in bars],
            dtype=np.float64,
        )

        for feat_idx, feat_name in enumerate(self.config.features):
            if feat_name == "returns":
                # 对数收益率
                returns = np.zeros(n_bars, dtype=np.float64)
                for i in range(1, n_bars):
                    if closes[i - 1] > 0:
                        returns[i] = np.log(closes[i] / closes[i - 1])
                raw[:, feat_idx] = returns

            elif feat_name == "volume":
                raw[:, feat_idx] = volumes

            elif feat_name == "range":
                # (high - low) / close
                with np.errstate(divide="ignore", invalid="ignore"):
                    ranges = np.where(
                        closes > 0,
                        (highs - lows) / closes,
                        0.0,
                    )
                raw[:, feat_idx] = ranges

            elif feat_name == "momentum":
                # 动量 (当前收盘 - N期前收盘) / N期前收盘
                momentum = np.zeros(n_bars, dtype=np.float64)
                lookback = 10
                for i in range(lookback, n_bars):
                    if closes[i - lookback] > 0:
                        momentum[i] = (closes[i] - closes[i - lookback]) / closes[
                            i - lookback
                        ]
                raw[:, feat_idx] = momentum

            elif feat_name == "volatility":
                # 滚动波动率
                window = 20
                vol = np.zeros(n_bars, dtype=np.float64)
                returns = np.zeros(n_bars, dtype=np.float64)
                for i in range(1, n_bars):
                    if closes[i - 1] > 0:
                        returns[i] = np.log(closes[i] / closes[i - 1])
                for i in range(window, n_bars):
                    vol[i] = np.std(returns[i - window : i])
                raw[:, feat_idx] = vol

            elif feat_name == "vwap_deviation":
                # VWAP偏离度
                with np.errstate(divide="ignore", invalid="ignore"):
                    typical_price = (highs + lows + closes) / 3
                    vwap = np.cumsum(typical_price * volumes) / np.cumsum(volumes)
                    vwap = np.nan_to_num(vwap, nan=0.0, posinf=0.0, neginf=0.0)
                    deviation = np.where(
                        vwap > 0,
                        (closes - vwap) / vwap,
                        0.0,
                    )
                raw[:, feat_idx] = deviation

            elif feat_name == "body_ratio":
                # 实体比例 (close - open) / (high - low)
                with np.errstate(divide="ignore", invalid="ignore"):
                    body = np.abs(closes - opens)
                    shadow = highs - lows
                    ratio = np.where(shadow > 0, body / shadow, 0.0)
                raw[:, feat_idx] = ratio

        return raw

    def _normalize_window(
        self,
        window: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """标准化窗口数据 (DL.DATA.SEQ.NORMALIZE).

        Args:
            window: 窗口特征矩阵

        Returns:
            标准化后的特征矩阵
        """
        method = self.config.normalization

        if method == NormalizationMethod.NONE:
            return window

        elif method == NormalizationMethod.ZSCORE:
            mean = np.mean(window, axis=0, keepdims=True)
            std = np.std(window, axis=0, keepdims=True)
            std = np.where(std < 1e-8, 1.0, std)
            return (window - mean) / std

        elif method == NormalizationMethod.MINMAX:
            min_val = np.min(window, axis=0, keepdims=True)
            max_val = np.max(window, axis=0, keepdims=True)
            range_val = max_val - min_val
            range_val = np.where(range_val < 1e-8, 1.0, range_val)
            return (window - min_val) / range_val

        elif method == NormalizationMethod.ROBUST:
            median = np.median(window, axis=0, keepdims=True)
            q75 = np.percentile(window, 75, axis=0, keepdims=True)
            q25 = np.percentile(window, 25, axis=0, keepdims=True)
            iqr = q75 - q25
            iqr = np.where(iqr < 1e-8, 1.0, iqr)
            return (window - median) / iqr

        else:
            return window

    def fit_normalizer(
        self,
        bars: PySequence[Bar1m],
    ) -> None:
        """拟合标准化器参数.

        用于保存全局标准化统计量，用于在线推理。

        Args:
            bars: 训练数据
        """
        raw_features = self._extract_raw_features(bars)

        for feat_idx, feat_name in enumerate(self.config.features):
            feat_data = raw_features[:, feat_idx]
            self._norm_stats[feat_name] = {
                "mean": float(np.mean(feat_data)),
                "std": float(np.std(feat_data)),
                "min": float(np.min(feat_data)),
                "max": float(np.max(feat_data)),
                "median": float(np.median(feat_data)),
                "q25": float(np.percentile(feat_data, 25)),
                "q75": float(np.percentile(feat_data, 75)),
            }

    def get_norm_stats(self) -> dict[str, dict[str, float]]:
        """获取标准化统计量.

        Returns:
            特征名称到统计量的映射
        """
        return self._norm_stats.copy()

    def _log_window(
        self,
        window: SequenceWindow,
        start_idx: int,
        end_idx: int,
    ) -> None:
        """记录窗口日志 (M3).

        Args:
            window: 窗口对象
            start_idx: 起始索引
            end_idx: 结束索引
        """
        log_entry = {
            "window_idx": window.window_idx,
            "start_idx": start_idx,
            "end_idx": end_idx,
            "timestamp": window.timestamp,
            "window_hash": window.window_hash,
            "target": window.target,
            "feature_shape": window.features.shape,
        }
        self._sequence_log.append(log_entry)

    def get_sequence_log(self) -> list[dict[str, Any]]:
        """获取序列日志 (M3).

        Returns:
            序列日志列表
        """
        return self._sequence_log.copy()

    def reset(self) -> None:
        """重置处理器状态."""
        if self.config.deterministic:
            self._rng = np.random.RandomState(self.config.seed)
        self._sequence_log.clear()
        self._norm_stats.clear()

    def get_feature_dim(self) -> int:
        """获取特征维度.

        Returns:
            window_size * n_features
        """
        return self.config.window_size * len(self.config.features)
