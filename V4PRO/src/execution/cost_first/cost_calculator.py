"""成本先行机制模块 (军规级 v4.0).

本模块提供交易成本预估与验证功能，确保在执行交易前完成成本评估。

军规覆盖:
- M5: 成本先行 - 交易执行前必须完成成本预估
- M3: 审计日志 - 所有成本计算结果必须可追溯

场景覆盖:
- EXEC.COST.FEE_CALC: 手续费计算
- EXEC.COST.SLIPPAGE_EST: 滑点估算
- EXEC.COST.IMPACT_EST: 冲击成本估算
- EXEC.COST.TOTAL_CHECK: 总成本预检
- EXEC.COST.THRESHOLD_CHECK: 成本阈值检查
- EXEC.COST.RR_VALIDATION: 盈亏比验证

示例:
    >>> from src.execution.cost_first.cost_calculator import CostFirstCalculator
    >>> calc = CostFirstCalculator()
    >>> estimate = calc.estimate_total_cost(
    ...     instrument="rb2501",
    ...     price=3500.0,
    ...     volume=10,
    ...     direction="buy",
    ...     market_depth=MarketDepth(bid_volume=100, ask_volume=120)
    ... )
    >>> print(estimate)
    CostEstimate(total_cost=156.50, fee=35.00, slippage=70.00, impact=51.50, ...)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from src.cost.china_fee_calculator import ChinaFeeCalculator, TradeDirection


class CostCheckResult(Enum):
    """成本检查结果枚举.

    属性:
        PASS: 通过所有检查
        FEE_EXCEEDED: 手续费超限
        SLIPPAGE_EXCEEDED: 滑点超限
        IMPACT_EXCEEDED: 冲击成本超限
        TOTAL_EXCEEDED: 总成本超限
        RR_RATIO_LOW: 盈亏比过低
        INVALID_INPUT: 无效输入
    """

    PASS = "PASS"
    FEE_EXCEEDED = "FEE_EXCEEDED"
    SLIPPAGE_EXCEEDED = "SLIPPAGE_EXCEEDED"
    IMPACT_EXCEEDED = "IMPACT_EXCEEDED"
    TOTAL_EXCEEDED = "TOTAL_EXCEEDED"
    RR_RATIO_LOW = "RR_RATIO_LOW"
    INVALID_INPUT = "INVALID_INPUT"


class CostAlertLevel(Enum):
    """成本告警级别枚举.

    属性:
        NORMAL: 正常
        WARNING: 警告 (成本偏高但可接受)
        CRITICAL: 严重 (成本过高，建议拒绝)
        BLOCK: 阻断 (成本超限，必须拒绝)
    """

    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    BLOCK = "BLOCK"


# 告警级别严重程度映射 (值越大越严重)
_ALERT_LEVEL_SEVERITY: dict[CostAlertLevel, int] = {
    CostAlertLevel.NORMAL: 0,
    CostAlertLevel.WARNING: 1,
    CostAlertLevel.CRITICAL: 2,
    CostAlertLevel.BLOCK: 3,
}


def _max_alert_level(level1: CostAlertLevel, level2: CostAlertLevel) -> CostAlertLevel:
    """比较两个告警级别，返回更严重的级别.

    参数:
        level1: 第一个告警级别
        level2: 第二个告警级别

    返回:
        更严重的告警级别
    """
    if _ALERT_LEVEL_SEVERITY[level1] >= _ALERT_LEVEL_SEVERITY[level2]:
        return level1
    return level2


@dataclass(frozen=True)
class MarketDepth:
    """市场深度数据.

    属性:
        bid_volume: 买一量 (手)
        ask_volume: 卖一量 (手)
        bid_price: 买一价 (可选)
        ask_price: 卖一价 (可选)
        total_bid_depth: 买盘总深度 (可选，五档总量)
        total_ask_depth: 卖盘总深度 (可选，五档总量)
    """

    bid_volume: int
    ask_volume: int
    bid_price: float = 0.0
    ask_price: float = 0.0
    total_bid_depth: int = 0
    total_ask_depth: int = 0


@dataclass(frozen=True)
class CostThresholds:
    """成本阈值配置.

    属性:
        max_fee_ratio: 最大手续费比率 (占成交金额)
        max_slippage_ratio: 最大滑点比率
        max_impact_ratio: 最大冲击成本比率
        max_total_ratio: 最大总成本比率
        min_rr_ratio: 最小盈亏比
        warning_ratio: 警告阈值 (触发WARNING级别)
        critical_ratio: 严重阈值 (触发CRITICAL级别)
    """

    max_fee_ratio: float = 0.001  # 0.1%
    max_slippage_ratio: float = 0.002  # 0.2%
    max_impact_ratio: float = 0.005  # 0.5%
    max_total_ratio: float = 0.01  # 1%
    min_rr_ratio: float = 2.0  # 最小盈亏比2:1
    warning_ratio: float = 0.7  # 达到阈值70%触发警告
    critical_ratio: float = 0.9  # 达到阈值90%触发严重


@dataclass
class CostEstimate:
    """成本估算结果.

    属性:
        instrument: 合约代码
        price: 成交价格
        volume: 成交手数
        direction: 交易方向
        notional: 名义金额
        fee: 手续费
        slippage: 预估滑点成本
        impact: 预估冲击成本
        total_cost: 总成本
        fee_ratio: 手续费比率
        slippage_ratio: 滑点比率
        impact_ratio: 冲击成本比率
        total_ratio: 总成本比率
        timestamp: 计算时间戳
        market_depth: 市场深度快照
    """

    instrument: str
    price: float
    volume: int
    direction: str
    notional: float
    fee: float
    slippage: float
    impact: float
    total_cost: float
    fee_ratio: float
    slippage_ratio: float
    impact_ratio: float
    total_ratio: float
    timestamp: float = field(default_factory=time.time)
    market_depth: MarketDepth | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        result = {
            "instrument": self.instrument,
            "price": self.price,
            "volume": self.volume,
            "direction": self.direction,
            "notional": round(self.notional, 2),
            "fee": round(self.fee, 2),
            "slippage": round(self.slippage, 2),
            "impact": round(self.impact, 2),
            "total_cost": round(self.total_cost, 2),
            "fee_ratio": round(self.fee_ratio, 6),
            "slippage_ratio": round(self.slippage_ratio, 6),
            "impact_ratio": round(self.impact_ratio, 6),
            "total_ratio": round(self.total_ratio, 6),
            "timestamp": self.timestamp,
        }
        if self.market_depth:
            result["market_depth"] = {
                "bid_volume": self.market_depth.bid_volume,
                "ask_volume": self.market_depth.ask_volume,
            }
        return result


@dataclass
class CostValidationResult:
    """成本验证结果.

    属性:
        result: 检查结果
        alert_level: 告警级别
        estimate: 成本估算
        expected_profit: 预期盈利
        expected_loss: 预期亏损
        rr_ratio: 盈亏比
        messages: 详细信息
        passed: 是否通过验证
    """

    result: CostCheckResult
    alert_level: CostAlertLevel
    estimate: CostEstimate
    expected_profit: float = 0.0
    expected_loss: float = 0.0
    rr_ratio: float = 0.0
    messages: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """是否通过验证."""
        return self.result == CostCheckResult.PASS

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "result": self.result.value,
            "alert_level": self.alert_level.value,
            "passed": self.passed,
            "estimate": self.estimate.to_dict(),
            "expected_profit": round(self.expected_profit, 2),
            "expected_loss": round(self.expected_loss, 2),
            "rr_ratio": round(self.rr_ratio, 4),
            "messages": self.messages,
        }


@dataclass
class CostAuditEvent:
    """成本审计事件.

    V2 Scenario: EXEC.COST.AUDIT

    军规 M3: 审计日志 - 所有成本计算结果必须记录。

    属性:
        ts: 时间戳
        event_type: 事件类型
        run_id: 运行ID
        exec_id: 执行ID
        instrument: 合约代码
        estimate: 成本估算
        validation: 验证结果 (可选)
    """

    ts: float
    event_type: str
    run_id: str
    exec_id: str
    instrument: str
    estimate: dict[str, Any]
    validation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        result = {
            "ts": self.ts,
            "event_type": self.event_type,
            "run_id": self.run_id,
            "exec_id": self.exec_id,
            "instrument": self.instrument,
            "estimate": self.estimate,
        }
        if self.validation:
            result["validation"] = self.validation
        return result


class CostFirstCalculator:
    """交易成本预估计算器.

    V2 Scenario: EXEC.COST.FIRST_CHECK

    军规 M5: 成本先行 - 交易执行前必须完成成本预估。

    提供:
    - 手续费计算 (按品种)
    - 滑点估算 (基于市场深度)
    - 冲击成本估算 (基于订单大小)
    - 总成本预检

    属性:
        fee_calculator: 手续费计算器
        default_slippage_ticks: 默认滑点跳数
        default_multiplier: 默认合约乘数

    示例:
        >>> calc = CostFirstCalculator()
        >>> estimate = calc.estimate_total_cost(
        ...     instrument="rb2501",
        ...     price=3500.0,
        ...     volume=10,
        ...     direction="buy"
        ... )
    """

    # 默认合约乘数表 (与 china_fee_calculator 保持一致)
    DEFAULT_MULTIPLIERS: ClassVar[dict[str, int]] = {
        "rb": 10,
        "hc": 10,
        "i": 100,
        "j": 100,
        "jm": 60,
        "IF": 300,
        "IH": 300,
        "IC": 200,
        "IM": 200,
        "au": 1000,
        "ag": 15,
        "cu": 5,
        "al": 5,
        "zn": 5,
        "sc": 1000,
    }

    # 默认最小价格变动单位
    DEFAULT_TICK_SIZES: ClassVar[dict[str, float]] = {
        "rb": 1.0,
        "hc": 1.0,
        "i": 0.5,
        "j": 0.5,
        "jm": 0.5,
        "IF": 0.2,
        "IH": 0.2,
        "IC": 0.2,
        "IM": 0.2,
        "au": 0.02,
        "ag": 1.0,
        "cu": 10.0,
        "al": 5.0,
        "zn": 5.0,
        "sc": 0.1,
    }

    def __init__(
        self,
        fee_calculator: ChinaFeeCalculator | None = None,
        default_slippage_ticks: int = 1,
        default_multiplier: int = 10,
    ) -> None:
        """初始化成本计算器.

        参数:
            fee_calculator: 手续费计算器 (可选，默认创建新实例)
            default_slippage_ticks: 默认滑点跳数
            default_multiplier: 默认合约乘数
        """
        self._fee_calculator = fee_calculator or ChinaFeeCalculator()
        self._default_slippage_ticks = default_slippage_ticks
        self._default_multiplier = default_multiplier
        self._calc_count = 0

    @property
    def fee_calculator(self) -> ChinaFeeCalculator:
        """手续费计算器."""
        return self._fee_calculator

    @property
    def calc_count(self) -> int:
        """计算次数."""
        return self._calc_count

    def estimate_fee(
        self,
        instrument: str,
        price: float,
        volume: int,
        direction: str,
        is_close_today: bool = False,
    ) -> float:
        """估算手续费.

        V2 Scenario: EXEC.COST.FEE_CALC

        参数:
            instrument: 合约代码
            price: 成交价格
            volume: 成交手数
            direction: 交易方向 (buy/sell)
            is_close_today: 是否平今

        返回:
            手续费金额
        """
        # 确定交易方向
        if is_close_today:
            trade_dir = "close_today"
        elif direction.lower() in ("buy", "long", "open"):
            trade_dir = "open"
        else:
            trade_dir = "close"

        result = self._fee_calculator.calculate(
            instrument=instrument,
            price=price,
            volume=volume,
            direction=trade_dir,
        )
        return result.fee

    def estimate_slippage(
        self,
        instrument: str,
        price: float,
        volume: int,
        direction: str,
        market_depth: MarketDepth | None = None,
    ) -> float:
        """估算滑点成本.

        V2 Scenario: EXEC.COST.SLIPPAGE_EST

        基于市场深度估算滑点:
        - 如果订单量小于对手盘一档量的50%，预估1个tick滑点
        - 如果订单量大于对手盘一档量，预估2-3个tick滑点
        - 如果订单量远大于五档总量，预估更高滑点

        参数:
            instrument: 合约代码
            price: 成交价格
            volume: 成交手数
            direction: 交易方向
            market_depth: 市场深度 (可选)

        返回:
            滑点成本金额
        """
        product = self._extract_product(instrument)
        tick_size = self.DEFAULT_TICK_SIZES.get(product, 1.0)
        multiplier = self.DEFAULT_MULTIPLIERS.get(product, self._default_multiplier)

        # 基础滑点跳数
        slippage_ticks = self._default_slippage_ticks

        if market_depth:
            # 根据交易方向确定对手盘
            is_buy = direction.lower() in ("buy", "long")
            opponent_volume = (
                market_depth.ask_volume if is_buy else market_depth.bid_volume
            )
            total_depth = (
                market_depth.total_ask_depth
                if is_buy
                else market_depth.total_bid_depth
            )

            if opponent_volume > 0:
                volume_ratio = volume / opponent_volume

                if volume_ratio <= 0.5:
                    slippage_ticks = 1
                elif volume_ratio <= 1.0:
                    slippage_ticks = 2
                elif volume_ratio <= 2.0:
                    slippage_ticks = 3
                else:
                    slippage_ticks = 4

                # 如果超过五档总量，增加额外滑点
                if total_depth > 0 and volume > total_depth:
                    slippage_ticks += 2

        # 计算滑点成本
        slippage_cost = slippage_ticks * tick_size * volume * multiplier
        return slippage_cost

    def estimate_impact(
        self,
        instrument: str,
        price: float,
        volume: int,
        market_depth: MarketDepth | None = None,
    ) -> float:
        """估算市场冲击成本.

        V2 Scenario: EXEC.COST.IMPACT_EST

        基于订单大小和市场深度估算冲击成本:
        - 小单 (< 对手盘20%): 冲击成本忽略不计
        - 中单 (20%-50%): 轻微冲击
        - 大单 (50%-100%): 明显冲击
        - 巨单 (> 100%): 严重冲击

        参数:
            instrument: 合约代码
            price: 成交价格
            volume: 成交手数
            market_depth: 市场深度 (可选)

        返回:
            冲击成本金额
        """
        product = self._extract_product(instrument)
        multiplier = self.DEFAULT_MULTIPLIERS.get(product, self._default_multiplier)
        notional = price * volume * multiplier

        # 基础冲击系数 (0.01% - 0.1%)
        base_impact_ratio = 0.0001  # 0.01%

        if market_depth:
            # 计算相对深度
            total_depth = market_depth.total_ask_depth + market_depth.total_bid_depth
            if total_depth == 0:
                total_depth = market_depth.ask_volume + market_depth.bid_volume

            if total_depth > 0:
                depth_ratio = volume / total_depth

                if depth_ratio <= 0.05:
                    impact_ratio = base_impact_ratio * 0.5
                elif depth_ratio <= 0.2:
                    impact_ratio = base_impact_ratio * 1.0
                elif depth_ratio <= 0.5:
                    impact_ratio = base_impact_ratio * 2.0
                elif depth_ratio <= 1.0:
                    impact_ratio = base_impact_ratio * 5.0
                else:
                    impact_ratio = base_impact_ratio * 10.0
            else:
                impact_ratio = base_impact_ratio * 3.0
        else:
            # 无深度信息，使用保守估计
            impact_ratio = base_impact_ratio * 2.0

        impact_cost = notional * impact_ratio
        return impact_cost

    def estimate_total_cost(
        self,
        instrument: str,
        price: float,
        volume: int,
        direction: str,
        market_depth: MarketDepth | None = None,
        is_close_today: bool = False,
    ) -> CostEstimate:
        """估算总交易成本.

        V2 Scenario: EXEC.COST.TOTAL_CHECK

        军规 M5: 成本先行 - 综合估算所有成本项。

        参数:
            instrument: 合约代码
            price: 成交价格
            volume: 成交手数
            direction: 交易方向
            market_depth: 市场深度 (可选)
            is_close_today: 是否平今

        返回:
            成本估算结果
        """
        self._calc_count += 1

        product = self._extract_product(instrument)
        multiplier = self.DEFAULT_MULTIPLIERS.get(product, self._default_multiplier)
        notional = price * volume * multiplier

        # 估算各项成本
        fee = self.estimate_fee(instrument, price, volume, direction, is_close_today)
        slippage = self.estimate_slippage(
            instrument, price, volume, direction, market_depth
        )
        impact = self.estimate_impact(instrument, price, volume, market_depth)

        total_cost = fee + slippage + impact

        # 计算成本比率
        fee_ratio = fee / notional if notional > 0 else 0.0
        slippage_ratio = slippage / notional if notional > 0 else 0.0
        impact_ratio = impact / notional if notional > 0 else 0.0
        total_ratio = total_cost / notional if notional > 0 else 0.0

        return CostEstimate(
            instrument=instrument,
            price=price,
            volume=volume,
            direction=direction,
            notional=notional,
            fee=fee,
            slippage=slippage,
            impact=impact,
            total_cost=total_cost,
            fee_ratio=fee_ratio,
            slippage_ratio=slippage_ratio,
            impact_ratio=impact_ratio,
            total_ratio=total_ratio,
            market_depth=market_depth,
        )

    def estimate_round_trip_cost(
        self,
        instrument: str,
        entry_price: float,
        exit_price: float,
        volume: int,
        direction: str,
        market_depth: MarketDepth | None = None,
        is_intraday: bool = True,
    ) -> CostEstimate:
        """估算往返交易成本.

        参数:
            instrument: 合约代码
            entry_price: 入场价格
            exit_price: 出场价格
            volume: 成交手数
            direction: 入场方向
            market_depth: 市场深度 (可选)
            is_intraday: 是否日内交易

        返回:
            往返成本估算结果
        """
        # 入场成本
        entry_estimate = self.estimate_total_cost(
            instrument=instrument,
            price=entry_price,
            volume=volume,
            direction=direction,
            market_depth=market_depth,
            is_close_today=False,
        )

        # 出场成本
        exit_direction = "sell" if direction.lower() in ("buy", "long") else "buy"
        exit_estimate = self.estimate_total_cost(
            instrument=instrument,
            price=exit_price,
            volume=volume,
            direction=exit_direction,
            market_depth=market_depth,
            is_close_today=is_intraday,
        )

        # 合并成本
        product = self._extract_product(instrument)
        multiplier = self.DEFAULT_MULTIPLIERS.get(product, self._default_multiplier)
        avg_price = (entry_price + exit_price) / 2
        notional = avg_price * volume * multiplier

        total_fee = entry_estimate.fee + exit_estimate.fee
        total_slippage = entry_estimate.slippage + exit_estimate.slippage
        total_impact = entry_estimate.impact + exit_estimate.impact
        total_cost = total_fee + total_slippage + total_impact

        return CostEstimate(
            instrument=instrument,
            price=avg_price,
            volume=volume,
            direction=f"{direction}_round_trip",
            notional=notional,
            fee=total_fee,
            slippage=total_slippage,
            impact=total_impact,
            total_cost=total_cost,
            fee_ratio=total_fee / notional if notional > 0 else 0.0,
            slippage_ratio=total_slippage / notional if notional > 0 else 0.0,
            impact_ratio=total_impact / notional if notional > 0 else 0.0,
            total_ratio=total_cost / notional if notional > 0 else 0.0,
            market_depth=market_depth,
        )

    def _extract_product(self, instrument: str) -> str:
        """从合约代码提取品种代码.

        参数:
            instrument: 合约代码

        返回:
            品种代码
        """
        result = ""
        for char in instrument:
            if char.isalpha():
                result += char
            else:
                break
        return result if result else instrument


class CostValidator:
    """成本验证器.

    V2 Scenarios:
    - EXEC.COST.THRESHOLD_CHECK: 成本阈值检查
    - EXEC.COST.RR_VALIDATION: 盈亏比验证
    - EXEC.COST.ALERT: 成本超限告警

    军规 M5: 成本先行 - 验证成本是否在可接受范围内。

    属性:
        calculator: 成本计算器
        thresholds: 成本阈值配置
        validation_count: 验证次数
        reject_count: 拒绝次数

    示例:
        >>> validator = CostValidator()
        >>> result = validator.validate(
        ...     instrument="rb2501",
        ...     price=3500.0,
        ...     volume=10,
        ...     direction="buy",
        ...     expected_profit=200.0,
        ...     expected_loss=100.0
        ... )
        >>> if result.passed:
        ...     print("成本验证通过")
    """

    def __init__(
        self,
        calculator: CostFirstCalculator | None = None,
        thresholds: CostThresholds | None = None,
    ) -> None:
        """初始化成本验证器.

        参数:
            calculator: 成本计算器 (可选)
            thresholds: 成本阈值配置 (可选)
        """
        self._calculator = calculator or CostFirstCalculator()
        self._thresholds = thresholds or CostThresholds()
        self._validation_count = 0
        self._reject_count = 0

    @property
    def calculator(self) -> CostFirstCalculator:
        """成本计算器."""
        return self._calculator

    @property
    def thresholds(self) -> CostThresholds:
        """成本阈值配置."""
        return self._thresholds

    @property
    def validation_count(self) -> int:
        """验证次数."""
        return self._validation_count

    @property
    def reject_count(self) -> int:
        """拒绝次数."""
        return self._reject_count

    def validate(
        self,
        instrument: str,
        price: float,
        volume: int,
        direction: str,
        expected_profit: float = 0.0,
        expected_loss: float = 0.0,
        market_depth: MarketDepth | None = None,
        is_close_today: bool = False,
    ) -> CostValidationResult:
        """验证交易成本.

        V2 Scenarios:
        - EXEC.COST.THRESHOLD_CHECK: 成本阈值检查
        - EXEC.COST.RR_VALIDATION: 盈亏比验证

        参数:
            instrument: 合约代码
            price: 成交价格
            volume: 成交手数
            direction: 交易方向
            expected_profit: 预期盈利 (用于盈亏比计算)
            expected_loss: 预期亏损 (用于盈亏比计算)
            market_depth: 市场深度 (可选)
            is_close_today: 是否平今

        返回:
            成本验证结果
        """
        self._validation_count += 1
        messages: list[str] = []

        # 估算成本
        estimate = self._calculator.estimate_total_cost(
            instrument=instrument,
            price=price,
            volume=volume,
            direction=direction,
            market_depth=market_depth,
            is_close_today=is_close_today,
        )

        # 确定告警级别和检查结果
        result = CostCheckResult.PASS
        alert_level = CostAlertLevel.NORMAL

        # 检查手续费
        fee_check = self._check_threshold(
            estimate.fee_ratio,
            self._thresholds.max_fee_ratio,
            "fee",
        )
        if fee_check:
            result, level, msg = fee_check
            alert_level = max(alert_level, level, key=lambda x: x.value)
            messages.append(msg)
            if result != CostCheckResult.PASS:
                self._reject_count += 1
                return CostValidationResult(
                    result=result,
                    alert_level=alert_level,
                    estimate=estimate,
                    expected_profit=expected_profit,
                    expected_loss=expected_loss,
                    messages=messages,
                )

        # 检查滑点
        slippage_check = self._check_threshold(
            estimate.slippage_ratio,
            self._thresholds.max_slippage_ratio,
            "slippage",
        )
        if slippage_check:
            result, level, msg = slippage_check
            alert_level = max(alert_level, level, key=lambda x: x.value)
            messages.append(msg)
            if result != CostCheckResult.PASS:
                self._reject_count += 1
                return CostValidationResult(
                    result=result,
                    alert_level=alert_level,
                    estimate=estimate,
                    expected_profit=expected_profit,
                    expected_loss=expected_loss,
                    messages=messages,
                )

        # 检查冲击成本
        impact_check = self._check_threshold(
            estimate.impact_ratio,
            self._thresholds.max_impact_ratio,
            "impact",
        )
        if impact_check:
            result, level, msg = impact_check
            alert_level = max(alert_level, level, key=lambda x: x.value)
            messages.append(msg)
            if result != CostCheckResult.PASS:
                self._reject_count += 1
                return CostValidationResult(
                    result=result,
                    alert_level=alert_level,
                    estimate=estimate,
                    expected_profit=expected_profit,
                    expected_loss=expected_loss,
                    messages=messages,
                )

        # 检查总成本
        total_check = self._check_threshold(
            estimate.total_ratio,
            self._thresholds.max_total_ratio,
            "total",
        )
        if total_check:
            result, level, msg = total_check
            alert_level = max(alert_level, level, key=lambda x: x.value)
            messages.append(msg)
            if result != CostCheckResult.PASS:
                self._reject_count += 1
                return CostValidationResult(
                    result=result,
                    alert_level=alert_level,
                    estimate=estimate,
                    expected_profit=expected_profit,
                    expected_loss=expected_loss,
                    messages=messages,
                )

        # 检查盈亏比 (如果提供了预期盈亏)
        rr_ratio = 0.0
        if expected_loss > 0:
            # 将成本纳入亏损计算
            total_loss = expected_loss + estimate.total_cost
            rr_ratio = expected_profit / total_loss if total_loss > 0 else 0.0

            if rr_ratio < self._thresholds.min_rr_ratio:
                ratio_pct = rr_ratio / self._thresholds.min_rr_ratio
                if ratio_pct < self._thresholds.warning_ratio:
                    result = CostCheckResult.RR_RATIO_LOW
                    alert_level = CostAlertLevel.BLOCK
                    messages.append(
                        f"RR ratio {rr_ratio:.2f} < min {self._thresholds.min_rr_ratio:.2f}"
                    )
                    self._reject_count += 1
                elif ratio_pct < self._thresholds.critical_ratio:
                    alert_level = max(alert_level, CostAlertLevel.CRITICAL)
                    messages.append(
                        f"RR ratio {rr_ratio:.2f} approaching min threshold"
                    )
                else:
                    alert_level = max(alert_level, CostAlertLevel.WARNING)
                    messages.append(f"RR ratio {rr_ratio:.2f} slightly below optimal")

        if not messages:
            messages.append("Cost validation passed")

        return CostValidationResult(
            result=result,
            alert_level=alert_level,
            estimate=estimate,
            expected_profit=expected_profit,
            expected_loss=expected_loss,
            rr_ratio=rr_ratio,
            messages=messages,
        )

    def _check_threshold(
        self,
        actual_ratio: float,
        max_ratio: float,
        cost_type: str,
    ) -> tuple[CostCheckResult, CostAlertLevel, str] | None:
        """检查成本阈值.

        参数:
            actual_ratio: 实际比率
            max_ratio: 最大允许比率
            cost_type: 成本类型

        返回:
            (检查结果, 告警级别, 消息) 或 None (无问题)
        """
        if max_ratio <= 0:
            return None

        ratio_pct = actual_ratio / max_ratio

        result_map = {
            "fee": CostCheckResult.FEE_EXCEEDED,
            "slippage": CostCheckResult.SLIPPAGE_EXCEEDED,
            "impact": CostCheckResult.IMPACT_EXCEEDED,
            "total": CostCheckResult.TOTAL_EXCEEDED,
        }

        if ratio_pct >= 1.0:
            return (
                result_map.get(cost_type, CostCheckResult.TOTAL_EXCEEDED),
                CostAlertLevel.BLOCK,
                f"{cost_type} ratio {actual_ratio:.4%} >= max {max_ratio:.4%}",
            )
        elif ratio_pct >= self._thresholds.critical_ratio:
            return (
                CostCheckResult.PASS,
                CostAlertLevel.CRITICAL,
                f"{cost_type} ratio {actual_ratio:.4%} approaching max {max_ratio:.4%}",
            )
        elif ratio_pct >= self._thresholds.warning_ratio:
            return (
                CostCheckResult.PASS,
                CostAlertLevel.WARNING,
                f"{cost_type} ratio {actual_ratio:.4%} elevated",
            )

        return None

    def validate_batch(
        self,
        orders: list[dict[str, Any]],
    ) -> list[CostValidationResult]:
        """批量验证订单成本.

        参数:
            orders: 订单列表，每个订单包含:
                - instrument: 合约代码
                - price: 价格
                - volume: 数量
                - direction: 方向
                - expected_profit: 预期盈利 (可选)
                - expected_loss: 预期亏损 (可选)

        返回:
            验证结果列表
        """
        results = []
        for order in orders:
            result = self.validate(
                instrument=order["instrument"],
                price=order["price"],
                volume=order["volume"],
                direction=order["direction"],
                expected_profit=order.get("expected_profit", 0.0),
                expected_loss=order.get("expected_loss", 0.0),
                market_depth=order.get("market_depth"),
                is_close_today=order.get("is_close_today", False),
            )
            results.append(result)
        return results

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计字典
        """
        return {
            "validation_count": self._validation_count,
            "reject_count": self._reject_count,
            "pass_rate": (
                (self._validation_count - self._reject_count) / self._validation_count
                if self._validation_count > 0
                else 0.0
            ),
        }


def create_cost_audit_event(
    estimate: CostEstimate,
    validation: CostValidationResult | None,
    run_id: str,
    exec_id: str,
) -> CostAuditEvent:
    """创建成本审计事件.

    V2 Scenario: EXEC.COST.AUDIT

    军规 M3: 审计日志

    参数:
        estimate: 成本估算
        validation: 验证结果 (可选)
        run_id: 运行ID
        exec_id: 执行ID

    返回:
        成本审计事件
    """
    return CostAuditEvent(
        ts=time.time(),
        event_type="COST_ESTIMATE",
        run_id=run_id,
        exec_id=exec_id,
        instrument=estimate.instrument,
        estimate=estimate.to_dict(),
        validation=validation.to_dict() if validation else None,
    )
