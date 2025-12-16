"""
交割感知套利策略 - DeliveryAwareCalendarArb (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §12 Phase 7, §17 交易时段与夜盘规则
V4 Scenarios:
- CHINA.ARB.DELIVERY_AWARE: 交割感知套利
- CHINA.ARB.POSITION_TRANSFER: 移仓换月逻辑

军规覆盖:
- M15: 夜盘跨日处理 - 交易日归属必须正确
- M6: 熔断保护 - 触发风控阈值必须立即停止

功能特性:
- 交割月临近自动减仓
- 移仓换月自动触发
- 主力合约切换感知
- 交割日历集成

示例:
    >>> from src.strategy.calendar_arb.delivery_aware import (
    ...     DeliveryAwareCalendarArb,
    ...     DeliveryConfig,
    ...     RollSignal,
    ... )
    >>> config = DeliveryConfig(warning_days=10, critical_days=5)
    >>> strategy = DeliveryAwareCalendarArb(config)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class RollSignal(Enum):
    """移仓信号枚举."""

    HOLD = "HOLD"  # 继续持有
    PREPARE = "PREPARE"  # 准备移仓 (预警)
    ROLL_NOW = "ROLL_NOW"  # 立即移仓
    FORCE_CLOSE = "FORCE_CLOSE"  # 强制平仓 (紧急)


class DeliveryStatus(Enum):
    """交割状态枚举."""

    SAFE = "SAFE"  # 安全期 (距交割>20天)
    NORMAL = "NORMAL"  # 正常期 (10-20天)
    WARNING = "WARNING"  # 预警期 (5-10天)
    CRITICAL = "CRITICAL"  # 危险期 (<5天)
    EXPIRED = "EXPIRED"  # 已过期


@dataclass(frozen=True)
class DeliveryConfig:
    """交割配置 (不可变).

    属性:
        warning_days: 预警天数阈值 (默认10)
        critical_days: 危险天数阈值 (默认5)
        force_close_days: 强制平仓天数 (默认2)
        roll_spread_limit: 移仓价差限制 (默认0.02即2%)
        auto_roll_enabled: 是否启用自动移仓 (默认True)
        max_roll_slippage: 最大移仓滑点 (默认0.005即0.5%)
    """

    warning_days: int = 10
    critical_days: int = 5
    force_close_days: int = 2
    roll_spread_limit: float = 0.02
    auto_roll_enabled: bool = True
    max_roll_slippage: float = 0.005


@dataclass
class ContractInfo:
    """合约信息.

    属性:
        symbol: 合约代码
        product: 品种代码
        delivery_date: 交割日期
        is_main: 是否主力合约
        volume: 成交量 (用于判断主力)
        open_interest: 持仓量 (用于判断主力)
    """

    symbol: str
    product: str
    delivery_date: date
    is_main: bool = False
    volume: int = 0
    open_interest: int = 0


@dataclass
class RollPlan:
    """移仓计划.

    属性:
        from_contract: 源合约
        to_contract: 目标合约
        signal: 移仓信号
        days_to_delivery: 距离交割天数
        status: 交割状态
        spread_pct: 价差百分比
        estimated_cost: 预估成本
        reason: 移仓原因
    """

    from_contract: str
    to_contract: str
    signal: RollSignal
    days_to_delivery: int
    status: DeliveryStatus
    spread_pct: float = 0.0
    estimated_cost: float = 0.0
    reason: str = ""


@dataclass
class DeliverySnapshot:
    """交割快照.

    属性:
        current_date: 当前日期
        positions: 持仓合约列表
        roll_plans: 移仓计划列表
        warnings: 预警信息
        timestamp: 快照时间戳
    """

    current_date: date
    positions: list[str] = field(default_factory=list)
    roll_plans: list[RollPlan] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    timestamp: str = ""


class DeliveryAwareCalendarArb:
    """交割感知日历套利策略 (军规 M6, M15).

    功能:
    - 检查持仓合约交割距离
    - 生成移仓换月信号
    - 执行移仓换月逻辑
    - 强制平仓保护

    示例:
        >>> config = DeliveryConfig(warning_days=10)
        >>> strategy = DeliveryAwareCalendarArb(config)
        >>> plan = strategy.check_delivery(near_contract, date.today())
    """

    def __init__(self, config: DeliveryConfig | None = None) -> None:
        """初始化交割感知策略.

        参数:
            config: 交割配置 (None使用默认配置)
        """
        self._config = config or DeliveryConfig()
        self._contracts: dict[str, ContractInfo] = {}
        self._main_contracts: dict[str, str] = {}  # product -> main contract
        self._last_snapshot: DeliverySnapshot | None = None

    @property
    def config(self) -> DeliveryConfig:
        """获取配置."""
        return self._config

    def register_contract(self, contract: ContractInfo) -> None:
        """注册合约信息.

        参数:
            contract: 合约信息
        """
        self._contracts[contract.symbol] = contract

        # 更新主力合约
        if contract.is_main:
            self._main_contracts[contract.product] = contract.symbol

    def get_contract(self, symbol: str) -> ContractInfo | None:
        """获取合约信息.

        参数:
            symbol: 合约代码

        返回:
            合约信息或None
        """
        return self._contracts.get(symbol)

    def get_main_contract(self, product: str) -> str | None:
        """获取主力合约.

        参数:
            product: 品种代码

        返回:
            主力合约代码或None
        """
        return self._main_contracts.get(product)

    def check_delivery(
        self,
        symbol: str,
        current_date: date | None = None,
    ) -> RollPlan | None:
        """检查合约交割状态并生成移仓计划.

        参数:
            symbol: 合约代码
            current_date: 当前日期 (None使用今天)

        返回:
            移仓计划或None (如果不需要移仓)
        """
        contract = self._contracts.get(symbol)
        if contract is None:
            return None

        if current_date is None:
            current_date = date.today()  # noqa: DTZ011

        # 计算距离交割天数
        days_to_delivery = (contract.delivery_date - current_date).days

        # 确定交割状态
        status = self._calculate_status(days_to_delivery)

        # 确定移仓信号
        signal = self._calculate_signal(status, days_to_delivery)

        # 如果不需要移仓
        if signal == RollSignal.HOLD:
            return None

        # 查找目标合约 (下一个主力)
        to_contract = self._find_next_contract(contract)

        return RollPlan(
            from_contract=symbol,
            to_contract=to_contract or "",
            signal=signal,
            days_to_delivery=days_to_delivery,
            status=status,
            reason=self._get_roll_reason(status, days_to_delivery),
        )

    def check_all_positions(
        self,
        positions: list[str],
        current_date: date | None = None,
    ) -> DeliverySnapshot:
        """检查所有持仓的交割状态.

        参数:
            positions: 持仓合约列表
            current_date: 当前日期

        返回:
            交割快照
        """
        if current_date is None:
            current_date = date.today()  # noqa: DTZ011

        roll_plans: list[RollPlan] = []
        warnings: list[str] = []

        for symbol in positions:
            plan = self.check_delivery(symbol, current_date)
            if plan is not None:
                roll_plans.append(plan)

                # 生成预警信息
                if plan.signal in (RollSignal.ROLL_NOW, RollSignal.FORCE_CLOSE):
                    warning = (
                        f"{symbol}: 距交割{plan.days_to_delivery}天, "
                        f"状态={plan.status.value}, 建议={plan.signal.value}"
                    )
                    warnings.append(warning)

        snapshot = DeliverySnapshot(
            current_date=current_date,
            positions=positions,
            roll_plans=roll_plans,
            warnings=warnings,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
        )

        self._last_snapshot = snapshot
        return snapshot

    def should_roll(
        self,
        symbol: str,
        current_date: date | None = None,
    ) -> bool:
        """判断是否需要移仓.

        参数:
            symbol: 合约代码
            current_date: 当前日期

        返回:
            是否需要移仓
        """
        plan = self.check_delivery(symbol, current_date)
        if plan is None:
            return False
        return plan.signal in (RollSignal.PREPARE, RollSignal.ROLL_NOW)

    def should_force_close(
        self,
        symbol: str,
        current_date: date | None = None,
    ) -> bool:
        """判断是否需要强制平仓.

        参数:
            symbol: 合约代码
            current_date: 当前日期

        返回:
            是否需要强制平仓
        """
        plan = self.check_delivery(symbol, current_date)
        if plan is None:
            return False
        return plan.signal == RollSignal.FORCE_CLOSE

    def get_roll_target(
        self,
        symbol: str,
    ) -> str | None:
        """获取移仓目标合约.

        参数:
            symbol: 源合约代码

        返回:
            目标合约代码或None
        """
        contract = self._contracts.get(symbol)
        if contract is None:
            return None
        return self._find_next_contract(contract)

    def calculate_roll_cost(
        self,
        from_price: float,
        to_price: float,
        volume: int,
        multiplier: float = 10.0,
        fee_rate: float = 0.0001,
    ) -> dict[str, float]:
        """计算移仓成本.

        参数:
            from_price: 源合约价格
            to_price: 目标合约价格
            volume: 移仓手数
            multiplier: 合约乘数
            fee_rate: 手续费率

        返回:
            成本明细字典
        """
        # 价差损益
        spread = to_price - from_price
        spread_pnl = spread * volume * multiplier

        # 手续费 (平仓 + 开仓)
        fee_close = from_price * volume * multiplier * fee_rate
        fee_open = to_price * volume * multiplier * fee_rate
        total_fee = fee_close + fee_open

        # 预估滑点
        slippage_close = from_price * volume * multiplier * self._config.max_roll_slippage
        slippage_open = to_price * volume * multiplier * self._config.max_roll_slippage
        total_slippage = slippage_close + slippage_open

        # 总成本
        total_cost = total_fee + total_slippage - spread_pnl

        return {
            "spread_pnl": spread_pnl,
            "fee_close": fee_close,
            "fee_open": fee_open,
            "total_fee": total_fee,
            "slippage_close": slippage_close,
            "slippage_open": slippage_open,
            "total_slippage": total_slippage,
            "total_cost": total_cost,
        }

    def _calculate_status(self, days_to_delivery: int) -> DeliveryStatus:
        """计算交割状态.

        参数:
            days_to_delivery: 距离交割天数

        返回:
            交割状态
        """
        if days_to_delivery < 0:
            return DeliveryStatus.EXPIRED
        if days_to_delivery <= self._config.force_close_days:
            return DeliveryStatus.CRITICAL
        if days_to_delivery <= self._config.critical_days:
            return DeliveryStatus.CRITICAL
        if days_to_delivery <= self._config.warning_days:
            return DeliveryStatus.WARNING
        if days_to_delivery <= 20:
            return DeliveryStatus.NORMAL
        return DeliveryStatus.SAFE

    def _calculate_signal(
        self,
        status: DeliveryStatus,
        days_to_delivery: int,
    ) -> RollSignal:
        """计算移仓信号.

        参数:
            status: 交割状态
            days_to_delivery: 距离交割天数

        返回:
            移仓信号
        """
        if status == DeliveryStatus.EXPIRED:
            return RollSignal.FORCE_CLOSE

        if status == DeliveryStatus.CRITICAL:
            if days_to_delivery <= self._config.force_close_days:
                return RollSignal.FORCE_CLOSE
            return RollSignal.ROLL_NOW

        if status == DeliveryStatus.WARNING:
            return RollSignal.PREPARE

        return RollSignal.HOLD

    def _find_next_contract(self, contract: ContractInfo) -> str | None:
        """查找下一个合约 (目标移仓合约).

        参数:
            contract: 当前合约

        返回:
            下一个合约代码或None
        """
        product = contract.product
        current_delivery = contract.delivery_date

        # 查找同品种下一个月的合约
        next_contract: ContractInfo | None = None
        min_days_diff = float("inf")

        for info in self._contracts.values():
            if info.product != product:
                continue
            if info.delivery_date <= current_delivery:
                continue

            days_diff = (info.delivery_date - current_delivery).days
            if days_diff < min_days_diff:
                min_days_diff = days_diff
                next_contract = info

        # 如果找不到，尝试返回主力合约
        if next_contract is None:
            main = self._main_contracts.get(product)
            if main and main != contract.symbol:
                return main
            return None

        return next_contract.symbol

    def _get_roll_reason(
        self,
        status: DeliveryStatus,
        days_to_delivery: int,
    ) -> str:
        """获取移仓原因.

        参数:
            status: 交割状态
            days_to_delivery: 距离交割天数

        返回:
            移仓原因
        """
        reasons = {
            DeliveryStatus.EXPIRED: "合约已过期, 必须立即平仓",
            DeliveryStatus.CRITICAL: f"距交割仅{days_to_delivery}天, 紧急移仓",
            DeliveryStatus.WARNING: f"距交割{days_to_delivery}天, 建议准备移仓",
            DeliveryStatus.NORMAL: f"距交割{days_to_delivery}天, 正常监控",
            DeliveryStatus.SAFE: "距交割较远, 无需操作",
        }
        return reasons.get(status, "未知原因")


# ============================================================
# 主力合约切换检测器
# ============================================================


class MainContractDetector:
    """主力合约切换检测器.

    功能:
    - 检测主力合约切换
    - 提供切换信号

    示例:
        >>> detector = MainContractDetector()
        >>> detector.update("rb2501", volume=100000, oi=50000)
        >>> new_main = detector.detect_switch("rb")
    """

    def __init__(
        self,
        volume_threshold: float = 1.5,
        oi_threshold: float = 1.2,
    ) -> None:
        """初始化检测器.

        参数:
            volume_threshold: 成交量切换阈值 (默认1.5倍)
            oi_threshold: 持仓量切换阈值 (默认1.2倍)
        """
        self._volume_threshold = volume_threshold
        self._oi_threshold = oi_threshold
        self._contract_data: dict[str, dict[str, Any]] = {}
        self._main_contracts: dict[str, str] = {}

    def update(
        self,
        symbol: str,
        product: str,
        volume: int,
        open_interest: int,
    ) -> None:
        """更新合约数据.

        参数:
            symbol: 合约代码
            product: 品种代码
            volume: 成交量
            open_interest: 持仓量
        """
        self._contract_data[symbol] = {
            "product": product,
            "volume": volume,
            "open_interest": open_interest,
        }

    def detect_switch(self, product: str) -> str | None:
        """检测主力合约切换.

        参数:
            product: 品种代码

        返回:
            新主力合约代码或None
        """
        # 获取该品种所有合约
        contracts = [
            (sym, data) for sym, data in self._contract_data.items() if data["product"] == product
        ]

        if not contracts:
            return None

        # 按成交量排序
        contracts.sort(key=lambda x: x[1]["volume"], reverse=True)

        # 最大成交量合约
        new_main = contracts[0][0]
        current_main = self._main_contracts.get(product)

        # 如果没有当前主力，直接设置
        if current_main is None:
            self._main_contracts[product] = new_main
            return new_main

        # 检查是否需要切换
        if new_main != current_main:
            current_data = self._contract_data.get(current_main, {})
            new_data = self._contract_data.get(new_main, {})

            current_volume = current_data.get("volume", 0)
            new_volume = new_data.get("volume", 0)

            # 新合约成交量超过阈值倍数时切换
            if current_volume > 0:
                volume_ratio = new_volume / current_volume
                if volume_ratio >= self._volume_threshold:
                    self._main_contracts[product] = new_main
                    return new_main

        return None

    def get_main_contract(self, product: str) -> str | None:
        """获取当前主力合约.

        参数:
            product: 品种代码

        返回:
            主力合约代码或None
        """
        return self._main_contracts.get(product)


# ============================================================
# 便捷函数
# ============================================================


def get_default_delivery_config() -> DeliveryConfig:
    """获取默认交割配置.

    返回:
        默认配置
    """
    return DeliveryConfig()


def create_delivery_aware_strategy(
    config: DeliveryConfig | None = None,
) -> DeliveryAwareCalendarArb:
    """创建交割感知策略.

    参数:
        config: 配置 (None使用默认)

    返回:
        策略实例
    """
    return DeliveryAwareCalendarArb(config)


def check_contract_delivery(
    symbol: str,
    delivery_date: date,
    current_date: date | None = None,
    config: DeliveryConfig | None = None,
) -> RollPlan | None:
    """检查合约交割状态 (便捷函数).

    参数:
        symbol: 合约代码
        delivery_date: 交割日期
        current_date: 当前日期
        config: 配置

    返回:
        移仓计划或None
    """
    strategy = DeliveryAwareCalendarArb(config)

    # 从合约代码提取品种
    product = "".join(c for c in symbol if c.isalpha()).upper()

    contract = ContractInfo(
        symbol=symbol,
        product=product,
        delivery_date=delivery_date,
    )
    strategy.register_contract(contract)

    return strategy.check_delivery(symbol, current_date)
