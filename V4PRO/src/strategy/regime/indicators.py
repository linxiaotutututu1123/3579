"""
市场状态指标计算模块 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: D7-P0 市场状态引擎

功能特性:
- 波动率指标 (ATR, 历史波动率)
- 趋势指标 (ADX, 移动平均)
- 成交量指标 (成交量比率)
- 价格模式指标 (区间宽度, 突破检测)

示例:
    >>> from src.strategy.regime.indicators import RegimeIndicators
    >>> indicators = RegimeIndicators()
    >>> result = indicators.calculate(prices, volumes)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np


@dataclass(frozen=True, slots=True)
class IndicatorResult:
    """指标计算结果 (不可变).

    属性:
        atr: 平均真实波幅
        atr_percentile: ATR百分位 (相对历史)
        historical_volatility: 历史波动率
        volatility_percentile: 波动率百分位
        adx: 平均方向指数
        plus_di: +DI方向指标
        minus_di: -DI方向指标
        trend_strength: 趋势强度 (0-1)
        trend_direction: 趋势方向 (-1, 0, 1)
        volume_ratio: 成交量比率 (当前/均值)
        volume_percentile: 成交量百分位
        price_range_ratio: 价格区间比率
        breakout_score: 突破得分 (-1到1)
    """

    # 波动率指标
    atr: float = 0.0
    atr_percentile: float = 50.0
    historical_volatility: float = 0.0
    volatility_percentile: float = 50.0

    # 趋势指标
    adx: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    trend_strength: float = 0.0
    trend_direction: int = 0  # -1: 下跌, 0: 中性, 1: 上涨

    # 成交量指标
    volume_ratio: float = 1.0
    volume_percentile: float = 50.0

    # 价格模式指标
    price_range_ratio: float = 0.0
    breakout_score: float = 0.0

    # 元数据
    is_valid: bool = True
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "atr": round(self.atr, 6),
            "atr_percentile": round(self.atr_percentile, 2),
            "historical_volatility": round(self.historical_volatility, 6),
            "volatility_percentile": round(self.volatility_percentile, 2),
            "adx": round(self.adx, 2),
            "plus_di": round(self.plus_di, 2),
            "minus_di": round(self.minus_di, 2),
            "trend_strength": round(self.trend_strength, 4),
            "trend_direction": self.trend_direction,
            "volume_ratio": round(self.volume_ratio, 4),
            "volume_percentile": round(self.volume_percentile, 2),
            "price_range_ratio": round(self.price_range_ratio, 4),
            "breakout_score": round(self.breakout_score, 4),
            "is_valid": self.is_valid,
        }


@dataclass
class IndicatorConfig:
    """指标计算配置.

    属性:
        atr_period: ATR计算周期
        volatility_period: 波动率计算周期
        adx_period: ADX计算周期
        volume_ma_period: 成交量均线周期
        percentile_lookback: 百分位计算回溯期
        ema_smoothing: EMA平滑系数
    """

    atr_period: int = 14
    volatility_period: int = 20
    adx_period: int = 14
    volume_ma_period: int = 20
    percentile_lookback: int = 100
    ema_smoothing: float = 0.1

    # 趋势判定阈值
    trend_adx_threshold: float = 25.0  # ADX>25判定有趋势
    strong_trend_adx_threshold: float = 40.0  # ADX>40判定强趋势

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "atr_period": self.atr_period,
            "volatility_period": self.volatility_period,
            "adx_period": self.adx_period,
            "volume_ma_period": self.volume_ma_period,
            "percentile_lookback": self.percentile_lookback,
            "ema_smoothing": self.ema_smoothing,
            "trend_adx_threshold": self.trend_adx_threshold,
            "strong_trend_adx_threshold": self.strong_trend_adx_threshold,
        }


class RegimeIndicators:
    """市场状态指标计算器.

    V4 SPEC D7-P0: 指标计算模块

    计算以下指标:
    - 波动率: ATR, 历史波动率
    - 趋势: ADX, DI
    - 成交量: 成交量比率
    - 价格模式: 区间比率, 突破得分
    """

    # 最小数据长度
    MIN_DATA_LENGTH: ClassVar[int] = 30

    def __init__(self, config: IndicatorConfig | None = None) -> None:
        """初始化指标计算器.

        Args:
            config: 指标配置
        """
        self._config = config or IndicatorConfig()
        self._atr_history: list[float] = []
        self._volatility_history: list[float] = []
        self._volume_history: list[float] = []

    @property
    def config(self) -> IndicatorConfig:
        """获取配置."""
        return self._config

    def calculate(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray | None = None,
    ) -> IndicatorResult:
        """计算所有指标.

        Args:
            high: 最高价数组
            low: 最低价数组
            close: 收盘价数组
            volume: 成交量数组 (可选)

        Returns:
            指标计算结果
        """
        # 验证输入
        if len(close) < self.MIN_DATA_LENGTH:
            return IndicatorResult(
                is_valid=False,
                error_message=f"数据长度不足: {len(close)} < {self.MIN_DATA_LENGTH}",
            )

        try:
            # 计算波动率指标
            atr = self._calculate_atr(high, low, close)
            historical_vol = self._calculate_historical_volatility(close)

            # 更新历史记录
            self._update_history(self._atr_history, atr)
            self._update_history(self._volatility_history, historical_vol)

            # 计算百分位
            atr_percentile = self._calculate_percentile(
                atr, self._atr_history
            )
            volatility_percentile = self._calculate_percentile(
                historical_vol, self._volatility_history
            )

            # 计算趋势指标
            adx, plus_di, minus_di = self._calculate_adx(high, low, close)
            trend_strength = self._calculate_trend_strength(adx, plus_di, minus_di)
            trend_direction = self._determine_trend_direction(
                close, plus_di, minus_di, adx
            )

            # 计算成交量指标
            volume_ratio = 1.0
            volume_percentile = 50.0
            if volume is not None and len(volume) > 0:
                volume_ratio = self._calculate_volume_ratio(volume)
                self._update_history(self._volume_history, volume[-1])
                volume_percentile = self._calculate_percentile(
                    volume[-1], self._volume_history
                )

            # 计算价格模式指标
            price_range_ratio = self._calculate_price_range_ratio(high, low, close)
            breakout_score = self._calculate_breakout_score(high, low, close)

            return IndicatorResult(
                atr=atr,
                atr_percentile=atr_percentile,
                historical_volatility=historical_vol,
                volatility_percentile=volatility_percentile,
                adx=adx,
                plus_di=plus_di,
                minus_di=minus_di,
                trend_strength=trend_strength,
                trend_direction=trend_direction,
                volume_ratio=volume_ratio,
                volume_percentile=volume_percentile,
                price_range_ratio=price_range_ratio,
                breakout_score=breakout_score,
                is_valid=True,
            )

        except Exception as e:
            return IndicatorResult(
                is_valid=False,
                error_message=f"计算错误: {e!s}",
            )

    def _calculate_atr(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> float:
        """计算平均真实波幅 (ATR).

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价

        Returns:
            ATR值
        """
        period = self._config.atr_period

        # 真实波幅 = max(H-L, |H-C_prev|, |L-C_prev|)
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))

        if len(true_range) < period:
            return float(np.mean(true_range)) if len(true_range) > 0 else 0.0

        # EMA平滑
        atr = np.zeros(len(true_range))
        atr[period - 1] = np.mean(true_range[:period])

        multiplier = 2.0 / (period + 1)
        for i in range(period, len(true_range)):
            atr[i] = true_range[i] * multiplier + atr[i - 1] * (1 - multiplier)

        return float(atr[-1])

    def _calculate_historical_volatility(self, close: np.ndarray) -> float:
        """计算历史波动率.

        Args:
            close: 收盘价

        Returns:
            历史波动率 (年化)
        """
        period = self._config.volatility_period

        if len(close) < period + 1:
            return 0.0

        # 对数收益率
        log_returns = np.log(close[1:] / close[:-1])

        # 取最近period期
        recent_returns = log_returns[-period:]

        # 标准差 * sqrt(252) 年化
        volatility = float(np.std(recent_returns) * np.sqrt(252))

        return volatility

    def _calculate_adx(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> tuple[float, float, float]:
        """计算ADX (平均方向指数).

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价

        Returns:
            (ADX, +DI, -DI) 元组
        """
        period = self._config.adx_period

        if len(close) < period + 1:
            return 0.0, 0.0, 0.0

        # 计算+DM和-DM
        high_diff = np.diff(high)
        low_diff = -np.diff(low)

        plus_dm = np.where(
            (high_diff > low_diff) & (high_diff > 0),
            high_diff,
            0.0
        )
        minus_dm = np.where(
            (low_diff > high_diff) & (low_diff > 0),
            low_diff,
            0.0
        )

        # 计算真实波幅
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))

        # EMA平滑
        smoothed_tr = self._ema(true_range, period)
        smoothed_plus_dm = self._ema(plus_dm, period)
        smoothed_minus_dm = self._ema(minus_dm, period)

        # 计算+DI和-DI
        plus_di = 100 * smoothed_plus_dm / (smoothed_tr + 1e-10)
        minus_di = 100 * smoothed_minus_dm / (smoothed_tr + 1e-10)

        # 计算DX
        di_diff = np.abs(plus_di - minus_di)
        di_sum = plus_di + minus_di + 1e-10
        dx = 100 * di_diff / di_sum

        # 计算ADX (DX的EMA)
        adx = self._ema(dx, period)

        return float(adx[-1]), float(plus_di[-1]), float(minus_di[-1])

    def _calculate_trend_strength(
        self,
        adx: float,
        plus_di: float,
        minus_di: float,
    ) -> float:
        """计算趋势强度.

        Args:
            adx: ADX值
            plus_di: +DI值
            minus_di: -DI值

        Returns:
            趋势强度 (0-1)
        """
        # 归一化ADX (0-100 -> 0-1)
        normalized_adx = min(adx / 100.0, 1.0)

        # DI差异因子
        di_diff = abs(plus_di - minus_di)
        di_factor = min(di_diff / 50.0, 1.0)

        # 综合趋势强度
        trend_strength = (normalized_adx * 0.6 + di_factor * 0.4)

        return min(max(trend_strength, 0.0), 1.0)

    def _determine_trend_direction(
        self,
        close: np.ndarray,
        plus_di: float,
        minus_di: float,
        adx: float,
    ) -> int:
        """判定趋势方向.

        Args:
            close: 收盘价
            plus_di: +DI值
            minus_di: -DI值
            adx: ADX值

        Returns:
            -1: 下跌, 0: 中性, 1: 上涨
        """
        # ADX不足表示无明显趋势
        if adx < self._config.trend_adx_threshold:
            return 0

        # 基于DI判断方向
        if plus_di > minus_di:
            return 1
        elif minus_di > plus_di:
            return -1

        return 0

    def _calculate_volume_ratio(self, volume: np.ndarray) -> float:
        """计算成交量比率.

        Args:
            volume: 成交量数组

        Returns:
            当前成交量/均值比率
        """
        period = self._config.volume_ma_period

        if len(volume) < period:
            return 1.0

        current_volume = volume[-1]
        avg_volume = np.mean(volume[-period:])

        if avg_volume <= 0:
            return 1.0

        return float(current_volume / avg_volume)

    def _calculate_price_range_ratio(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> float:
        """计算价格区间比率.

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价

        Returns:
            当前区间/历史区间比率
        """
        lookback = min(20, len(close) - 1)

        if lookback < 5:
            return 0.0

        # 当前K线区间
        current_range = high[-1] - low[-1]

        # 历史平均区间
        historical_ranges = high[-lookback:-1] - low[-lookback:-1]
        avg_range = np.mean(historical_ranges)

        if avg_range <= 0:
            return 0.0

        return float(current_range / avg_range)

    def _calculate_breakout_score(
        self,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
    ) -> float:
        """计算突破得分.

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价

        Returns:
            突破得分 (-1到1)
        """
        lookback = min(20, len(close) - 1)

        if lookback < 5:
            return 0.0

        # 历史高低点
        period_high = np.max(high[-lookback:-1])
        period_low = np.min(low[-lookback:-1])

        current_close = close[-1]
        price_range = period_high - period_low

        if price_range <= 0:
            return 0.0

        # 计算相对位置
        relative_position = (current_close - period_low) / price_range

        # 转换为-1到1范围
        breakout_score = 2 * relative_position - 1

        # 检测突破
        if current_close > period_high:
            breakout_score = min(1.0, breakout_score + 0.3)
        elif current_close < period_low:
            breakout_score = max(-1.0, breakout_score - 0.3)

        return float(np.clip(breakout_score, -1.0, 1.0))

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算指数移动平均.

        Args:
            data: 数据数组
            period: 周期

        Returns:
            EMA数组
        """
        if len(data) < period:
            return data

        ema = np.zeros(len(data))
        ema[period - 1] = np.mean(data[:period])

        multiplier = 2.0 / (period + 1)
        for i in range(period, len(data)):
            ema[i] = data[i] * multiplier + ema[i - 1] * (1 - multiplier)

        return ema

    def _update_history(self, history: list[float], value: float) -> None:
        """更新历史记录.

        Args:
            history: 历史记录列表
            value: 新值
        """
        history.append(value)
        max_len = self._config.percentile_lookback
        if len(history) > max_len:
            history.pop(0)

    def _calculate_percentile(self, value: float, history: list[float]) -> float:
        """计算百分位.

        Args:
            value: 当前值
            history: 历史数据

        Returns:
            百分位 (0-100)
        """
        if len(history) < 10:
            return 50.0

        sorted_history = sorted(history)
        position = 0
        for h in sorted_history:
            if h <= value:
                position += 1
            else:
                break

        percentile = 100.0 * position / len(sorted_history)
        return float(min(100.0, max(0.0, percentile)))

    def reset(self) -> None:
        """重置历史记录."""
        self._atr_history.clear()
        self._volatility_history.clear()
        self._volume_history.clear()


# ============================================================
# 便捷函数
# ============================================================


def calculate_indicators(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    volume: np.ndarray | None = None,
    config: IndicatorConfig | None = None,
) -> IndicatorResult:
    """计算市场状态指标.

    Args:
        high: 最高价数组
        low: 最低价数组
        close: 收盘价数组
        volume: 成交量数组 (可选)
        config: 指标配置

    Returns:
        指标计算结果
    """
    calculator = RegimeIndicators(config)
    return calculator.calculate(high, low, close, volume)


def calculate_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    period: int = 14,
) -> float:
    """计算ATR.

    Args:
        high: 最高价
        low: 最低价
        close: 收盘价
        period: 计算周期

    Returns:
        ATR值
    """
    config = IndicatorConfig(atr_period=period)
    calculator = RegimeIndicators(config)
    result = calculator.calculate(high, low, close)
    return result.atr


def calculate_volatility(
    close: np.ndarray,
    period: int = 20,
) -> float:
    """计算历史波动率.

    Args:
        close: 收盘价
        period: 计算周期

    Returns:
        历史波动率 (年化)
    """
    if len(close) < period + 1:
        return 0.0

    log_returns = np.log(close[1:] / close[:-1])
    recent_returns = log_returns[-period:]
    return float(np.std(recent_returns) * np.sqrt(252))
