"""
自适应VaR调度器 (军规级 v4.3).

V4PRO Platform Component - Phase 10 VaR频率优化
V4 SPEC: D8 动态VaR频率优化

功能特性:
- 自适应更新频率机制 (200ms-5s)
- 基于市场状态动态切换计算方法
- 事件触发器 (position_change, price_gap_3pct, margin_warning, limit_price_hit)
- 性能优化 (CPU占用<=10%)

军规覆盖:
- M6: 熔断保护 - 极端市场加速计算
- M13: 涨跌停感知 - 涨跌停触发立即重算
- M16: 保证金监控 - 保证金告警触发

示例:
    >>> from src.risk.adaptive_var import AdaptiveVaRScheduler, MarketRegime
    >>> scheduler = AdaptiveVaRScheduler()
    >>> scheduler.update_market_regime(MarketRegime.VOLATILE)
    >>> result = scheduler.calculate_if_needed(returns)
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from src.risk.dynamic_var import DynamicVaREngine, DynamicVaRResult, VaRMethod

if TYPE_CHECKING:
    from collections.abc import Callable


class MarketRegime(Enum):
    """市场状态枚举.

    用于分类当前市场环境，决定VaR计算频率和方法。

    属性:
        CALM: 平静市场 - 低波动，长间隔更新
        NORMAL: 正常市场 - 中等波动，标准更新
        VOLATILE: 波动市场 - 高波动，频繁更新
        EXTREME: 极端市场 - 极端波动，最高频更新
    """

    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    EXTREME = "extreme"


class EventType(Enum):
    """事件触发器类型.

    触发立即VaR重算的事件类型 (M6/M13/M16).
    """

    POSITION_CHANGE = "position_change"  # 持仓变动
    PRICE_GAP_3PCT = "price_gap_3pct"  # 价格跳空>3%
    MARGIN_WARNING = "margin_warning"  # 保证金告警
    LIMIT_PRICE_HIT = "limit_price_hit"  # 涨跌停触发


@dataclass
class AdaptiveVaRConfig:
    """自适应VaR配置.

    D8设计规范: 动态VaR频率优化

    属性:
        base_interval_ms: 基础更新间隔 (毫秒)
        adaptive_rules: 市场状态对应的更新间隔
        calculation_strategy: 市场状态对应的计算方法
        event_triggers: 事件触发器列表
        cpu_limit_pct: CPU占用上限百分比
    """

    # 基础更新间隔 (从100ms调整为1000ms)
    BASE_INTERVAL_MS: ClassVar[int] = 1000

    # 自适应规则: 市场状态 -> 更新间隔(毫秒)
    ADAPTIVE_RULES: ClassVar[dict[str, int]] = {
        "calm": 5000,  # 平静市场: 5秒
        "normal": 1000,  # 正常市场: 1秒
        "volatile": 500,  # 波动市场: 500ms
        "extreme": 200,  # 极端市场: 200ms
    }

    # 计算策略: 市场状态 -> VaR计算方法
    CALCULATION_STRATEGY: ClassVar[dict[str, str]] = {
        "calm": "parametric",  # 参数法 (快速)
        "normal": "historical",  # 历史模拟法 (标准)
        "volatile": "historical",  # 历史模拟法 (准确)
        "extreme": "monte_carlo",  # 蒙特卡洛 (精确)
    }

    # 事件触发器 (立即重算)
    EVENT_TRIGGERS: ClassVar[list[str]] = [
        "position_change",
        "price_gap_3pct",
        "margin_warning",
        "limit_price_hit",
    ]

    # 性能限制
    CPU_LIMIT_PCT: ClassVar[float] = 10.0  # CPU占用上限 10%

    # 实例配置
    base_interval_ms: int = BASE_INTERVAL_MS
    cpu_limit_pct: float = CPU_LIMIT_PCT


@dataclass
class VaRScheduleState:
    """VaR调度状态.

    追踪调度器的当前状态和性能指标。

    属性:
        current_regime: 当前市场状态
        last_calculation_time: 上次计算时间
        calculation_count: 计算次数
        event_trigger_count: 事件触发次数
        cpu_usage_samples: CPU使用率样本
        skipped_calculations: 跳过的计算次数 (性能保护)
    """

    current_regime: MarketRegime = MarketRegime.NORMAL
    last_calculation_time: float = 0.0
    calculation_count: int = 0
    event_trigger_count: int = 0
    cpu_usage_samples: list[float] = field(default_factory=list)
    skipped_calculations: int = 0

    def get_avg_cpu_usage(self) -> float:
        """获取平均CPU使用率."""
        if not self.cpu_usage_samples:
            return 0.0
        return sum(self.cpu_usage_samples) / len(self.cpu_usage_samples)


@dataclass
class PerformanceMetrics:
    """性能指标.

    追踪VaR计算的性能表现。

    属性:
        avg_calculation_time_ms: 平均计算时间(毫秒)
        max_calculation_time_ms: 最大计算时间(毫秒)
        calculations_per_second: 每秒计算次数
        cpu_usage_pct: CPU使用率百分比
        throttled: 是否被节流
    """

    avg_calculation_time_ms: float = 0.0
    max_calculation_time_ms: float = 0.0
    calculations_per_second: float = 0.0
    cpu_usage_pct: float = 0.0
    throttled: bool = False


class AdaptiveVaRScheduler:
    """自适应VaR调度器 (D8设计实现).

    基于市场状态动态调整VaR计算频率和方法。

    功能:
    - 根据市场状态自动调整更新间隔 (200ms-5s)
    - 动态切换计算方法 (parametric/historical/monte_carlo)
    - 事件触发器支持立即重算
    - CPU使用率限制 (<=10%)

    示例:
        >>> scheduler = AdaptiveVaRScheduler()
        >>> scheduler.update_market_regime(MarketRegime.VOLATILE)
        >>> result = scheduler.calculate_if_needed(returns)
    """

    # 性能追踪常量
    MAX_CPU_SAMPLES: ClassVar[int] = 100
    MIN_INTERVAL_MS: ClassVar[int] = 100  # 最小间隔保护
    MAX_CALC_TIME_SAMPLES: ClassVar[int] = 50

    def __init__(
        self,
        config: AdaptiveVaRConfig | None = None,
        var_engine: DynamicVaREngine | None = None,
        confidence: float = 0.95,
    ) -> None:
        """初始化自适应VaR调度器.

        参数:
            config: 自适应VaR配置
            var_engine: VaR计算引擎
            confidence: 默认置信水平
        """
        self._config = config or AdaptiveVaRConfig()
        self._engine = var_engine or DynamicVaREngine(default_confidence=confidence)
        self._confidence = confidence

        # 状态
        self._state = VaRScheduleState()
        self._lock = threading.Lock()

        # 性能追踪
        self._calc_times: list[float] = []
        self._last_result: DynamicVaRResult | None = None

        # 回调
        self._event_callbacks: list[Callable[[EventType, DynamicVaRResult], None]] = []

        # 波动率追踪
        self._volatility_history: list[float] = []
        self._price_history: list[float] = []

    @property
    def current_regime(self) -> MarketRegime:
        """获取当前市场状态."""
        return self._state.current_regime

    @property
    def last_result(self) -> DynamicVaRResult | None:
        """获取上次VaR结果."""
        return self._last_result

    def update_market_regime(self, regime: MarketRegime) -> None:
        """更新市场状态.

        参数:
            regime: 新的市场状态
        """
        with self._lock:
            old_regime = self._state.current_regime
            self._state.current_regime = regime

            # 如果从平静切换到波动/极端，立即触发计算
            if old_regime == MarketRegime.CALM and regime in (
                MarketRegime.VOLATILE,
                MarketRegime.EXTREME,
            ):
                self._state.last_calculation_time = 0  # 强制下次计算

    def detect_market_regime(
        self,
        returns: list[float],
        lookback: int = 20,
    ) -> MarketRegime:
        """自动检测市场状态.

        基于近期收益率波动性判断市场状态。

        参数:
            returns: 收益率序列
            lookback: 回看窗口

        返回:
            检测到的市场状态
        """
        if len(returns) < 5:
            return MarketRegime.NORMAL

        # 计算近期波动率
        recent = returns[-lookback:] if len(returns) >= lookback else returns
        n = len(recent)
        if n < 2:
            return MarketRegime.NORMAL

        mean = sum(recent) / n
        variance = sum((r - mean) ** 2 for r in recent) / (n - 1)
        volatility = variance**0.5

        # 年化波动率 (假设日频数据)
        annual_vol = volatility * (252**0.5)

        # 检测极端收益
        max_abs_return = max(abs(r) for r in recent)

        # 分类阈值
        if max_abs_return >= 0.05 or annual_vol >= 0.50:
            return MarketRegime.EXTREME
        if annual_vol >= 0.30:
            return MarketRegime.VOLATILE
        if annual_vol >= 0.15:
            return MarketRegime.NORMAL
        return MarketRegime.CALM

    def get_update_interval_ms(self) -> int:
        """获取当前更新间隔 (毫秒).

        根据市场状态返回相应的更新间隔。

        返回:
            更新间隔 (毫秒)
        """
        regime_value = self._state.current_regime.value
        return AdaptiveVaRConfig.ADAPTIVE_RULES.get(
            regime_value, self._config.base_interval_ms
        )

    def get_calculation_method(self) -> VaRMethod:
        """获取当前计算方法.

        根据市场状态返回相应的VaR计算方法。

        返回:
            VaR计算方法
        """
        regime_value = self._state.current_regime.value
        method_str = AdaptiveVaRConfig.CALCULATION_STRATEGY.get(
            regime_value, "historical"
        )

        method_map = {
            "parametric": VaRMethod.PARAMETRIC,
            "historical": VaRMethod.HISTORICAL,
            "monte_carlo": VaRMethod.MONTE_CARLO,
        }
        return method_map.get(method_str, VaRMethod.HISTORICAL)

    def should_calculate(self) -> bool:
        """判断是否应该计算VaR.

        基于时间间隔和性能约束判断。

        返回:
            是否应该计算
        """
        current_time = time.time() * 1000  # 毫秒
        interval = self.get_update_interval_ms()
        elapsed = current_time - self._state.last_calculation_time

        # 检查时间间隔
        if elapsed < interval:
            return False

        # 检查CPU使用率限制
        avg_cpu = self._state.get_avg_cpu_usage()
        if avg_cpu >= self._config.cpu_limit_pct:
            self._state.skipped_calculations += 1
            return False

        return True

    def trigger_event(
        self,
        event_type: EventType,
        returns: list[float],
        **kwargs: Any,
    ) -> DynamicVaRResult | None:
        """触发事件立即重算VaR.

        事件类型 (M6/M13/M16):
        - position_change: 持仓变动
        - price_gap_3pct: 价格跳空>3%
        - margin_warning: 保证金告警
        - limit_price_hit: 涨跌停触发

        参数:
            event_type: 事件类型
            returns: 收益率序列
            **kwargs: 额外参数

        返回:
            VaR计算结果 (如果触发)
        """
        with self._lock:
            self._state.event_trigger_count += 1

            # 极端事件强制使用蒙特卡洛
            force_method: VaRMethod | None = None
            if event_type in (EventType.MARGIN_WARNING, EventType.LIMIT_PRICE_HIT):
                force_method = VaRMethod.MONTE_CARLO

            result = self._perform_calculation(returns, force_method, **kwargs)

            # 通知回调
            for callback in self._event_callbacks:
                try:
                    callback(event_type, result)
                except Exception:
                    pass  # 回调错误不影响主流程

            return result

    def calculate_if_needed(
        self,
        returns: list[float],
        **kwargs: Any,
    ) -> DynamicVaRResult | None:
        """按需计算VaR.

        如果满足时间间隔和性能约束，执行VaR计算。

        参数:
            returns: 收益率序列
            **kwargs: 额外参数

        返回:
            VaR计算结果 (如果执行) 或 None
        """
        if not self.should_calculate():
            return self._last_result

        with self._lock:
            # 自动检测市场状态
            detected_regime = self.detect_market_regime(returns)
            if detected_regime != self._state.current_regime:
                self._state.current_regime = detected_regime

            return self._perform_calculation(returns, **kwargs)

    def force_calculate(
        self,
        returns: list[float],
        method: VaRMethod | None = None,
        **kwargs: Any,
    ) -> DynamicVaRResult:
        """强制计算VaR.

        忽略时间间隔约束，立即执行计算。

        参数:
            returns: 收益率序列
            method: 指定计算方法
            **kwargs: 额外参数

        返回:
            VaR计算结果
        """
        with self._lock:
            return self._perform_calculation(returns, method, **kwargs)

    def _perform_calculation(
        self,
        returns: list[float],
        method: VaRMethod | None = None,
        **kwargs: Any,
    ) -> DynamicVaRResult:
        """执行VaR计算.

        内部方法，执行实际的VaR计算并追踪性能。

        参数:
            returns: 收益率序列
            method: 计算方法 (None=自动选择)
            **kwargs: 额外参数

        返回:
            VaR计算结果
        """
        start_time = time.time()

        # 选择计算方法
        calc_method = method or self.get_calculation_method()

        # 执行计算
        result = self._engine.calculate_var(
            returns,
            method=calc_method,
            confidence=self._confidence,
            **kwargs,
        )

        # 记录性能
        elapsed_ms = (time.time() - start_time) * 1000
        self._calc_times.append(elapsed_ms)
        if len(self._calc_times) > self.MAX_CALC_TIME_SAMPLES:
            self._calc_times.pop(0)

        # 更新状态
        self._state.last_calculation_time = time.time() * 1000
        self._state.calculation_count += 1
        self._last_result = result

        # 估算CPU使用率 (简化模型)
        cpu_estimate = min(elapsed_ms / self.get_update_interval_ms() * 100, 100.0)
        self._state.cpu_usage_samples.append(cpu_estimate)
        if len(self._state.cpu_usage_samples) > self.MAX_CPU_SAMPLES:
            self._state.cpu_usage_samples.pop(0)

        return result

    def register_event_callback(
        self, callback: Callable[[EventType, DynamicVaRResult], None]
    ) -> None:
        """注册事件回调.

        参数:
            callback: 回调函数 (event_type, result) -> None
        """
        self._event_callbacks.append(callback)

    def get_performance_metrics(self) -> PerformanceMetrics:
        """获取性能指标.

        返回:
            性能指标数据类
        """
        avg_time = sum(self._calc_times) / len(self._calc_times) if self._calc_times else 0
        max_time = max(self._calc_times) if self._calc_times else 0

        interval_s = self.get_update_interval_ms() / 1000
        calc_per_sec = 1 / interval_s if interval_s > 0 else 0

        return PerformanceMetrics(
            avg_calculation_time_ms=avg_time,
            max_calculation_time_ms=max_time,
            calculations_per_second=calc_per_sec,
            cpu_usage_pct=self._state.get_avg_cpu_usage(),
            throttled=self._state.skipped_calculations > 0,
        )

    def get_statistics(self) -> dict[str, Any]:
        """获取调度器统计信息.

        返回:
            统计信息字典
        """
        perf = self.get_performance_metrics()
        return {
            "current_regime": self._state.current_regime.value,
            "update_interval_ms": self.get_update_interval_ms(),
            "calculation_method": self.get_calculation_method().value,
            "calculation_count": self._state.calculation_count,
            "event_trigger_count": self._state.event_trigger_count,
            "skipped_calculations": self._state.skipped_calculations,
            "avg_cpu_usage_pct": round(perf.cpu_usage_pct, 2),
            "avg_calculation_time_ms": round(perf.avg_calculation_time_ms, 2),
            "max_calculation_time_ms": round(perf.max_calculation_time_ms, 2),
            "cpu_limit_pct": self._config.cpu_limit_pct,
            "performance_throttled": perf.throttled,
        }

    def reset(self) -> None:
        """重置调度器状态."""
        with self._lock:
            self._state = VaRScheduleState()
            self._calc_times = []
            self._last_result = None
            self._engine.reset()

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式.

        返回:
            审计日志字典
        """
        return {
            "event_type": "ADAPTIVE_VAR_SCHEDULER",
            "timestamp": datetime.now().isoformat(),  # noqa: DTZ005
            "regime": self._state.current_regime.value,
            "interval_ms": self.get_update_interval_ms(),
            "method": self.get_calculation_method().value,
            "calculation_count": self._state.calculation_count,
            "event_trigger_count": self._state.event_trigger_count,
            "cpu_usage_pct": round(self._state.get_avg_cpu_usage(), 2),
            "last_var": round(self._last_result.var, 6) if self._last_result else None,
        }


# ============================================================
# 便捷函数
# ============================================================


def create_adaptive_var_scheduler(
    confidence: float = 0.95,
    cpu_limit_pct: float = 10.0,
    seed: int | None = None,
) -> AdaptiveVaRScheduler:
    """创建自适应VaR调度器.

    参数:
        confidence: 默认置信水平
        cpu_limit_pct: CPU占用上限百分比
        seed: 随机种子

    返回:
        自适应VaR调度器实例
    """
    config = AdaptiveVaRConfig(cpu_limit_pct=cpu_limit_pct)
    engine = DynamicVaREngine(default_confidence=confidence, seed=seed)
    return AdaptiveVaRScheduler(config=config, var_engine=engine, confidence=confidence)


def quick_adaptive_var(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    """快速自适应VaR计算.

    自动检测市场状态并选择合适的计算方法。

    参数:
        returns: 收益率序列
        confidence: 置信水平

    返回:
        VaR值
    """
    scheduler = AdaptiveVaRScheduler(confidence=confidence)
    result = scheduler.force_calculate(returns)
    return result.var


def get_regime_from_volatility(annual_volatility: float) -> MarketRegime:
    """根据年化波动率获取市场状态.

    参数:
        annual_volatility: 年化波动率

    返回:
        市场状态
    """
    if annual_volatility >= 0.50:
        return MarketRegime.EXTREME
    if annual_volatility >= 0.30:
        return MarketRegime.VOLATILE
    if annual_volatility >= 0.15:
        return MarketRegime.NORMAL
    return MarketRegime.CALM
