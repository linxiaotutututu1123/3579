"""
主力合约追踪器模块 (军规级 v4.1).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §25 主力合约追踪, §26 合约切换机制

军规覆盖:
- M20: 主力合约追踪 - 基于成交量+持仓量自动识别

功能特性:
- 主力合约自动检测 (基于成交量/持仓量)
- 合约切换事件通知
- 历史切换记录
- 审计日志支持

示例:
    >>> from src.market.main_contract_tracker import (
    ...     MainContractTracker,
    ...     ContractSwitchEvent,
    ... )
    >>> tracker = MainContractTracker()
    >>> tracker.update("rb2501", "rb", volume=100000, open_interest=50000)
    >>> main = tracker.get_main_contract("rb")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable


class SwitchReason(Enum):
    """切换原因枚举."""

    VOLUME_DOMINANCE = "VOLUME_DOMINANCE"  # 成交量主导
    OI_DOMINANCE = "OI_DOMINANCE"  # 持仓量主导
    COMBINED_DOMINANCE = "COMBINED_DOMINANCE"  # 综合主导
    EXPIRY_APPROACHING = "EXPIRY_APPROACHING"  # 到期临近
    MANUAL = "MANUAL"  # 手动切换
    INITIAL = "INITIAL"  # 初始设置


@dataclass(frozen=True)
class ContractSwitchEvent:
    """合约切换事件 (不可变).

    属性:
        product: 品种代码 (如 "rb")
        old_contract: 原主力合约 (如 "rb2501")
        new_contract: 新主力合约 (如 "rb2505")
        reason: 切换原因
        volume_ratio: 成交量比率 (新/旧)
        oi_ratio: 持仓量比率 (新/旧)
        timestamp: 切换时间戳
    """

    product: str
    old_contract: str | None
    new_contract: str
    reason: SwitchReason
    volume_ratio: float = 0.0
    oi_ratio: float = 0.0
    timestamp: str = ""

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式.

        返回:
            符合审计要求的字典
        """
        return {
            "event_type": "CONTRACT_SWITCH",
            "product": self.product,
            "old_contract": self.old_contract,
            "new_contract": self.new_contract,
            "reason": self.reason.value,
            "volume_ratio": round(self.volume_ratio, 4),
            "oi_ratio": round(self.oi_ratio, 4),
            "timestamp": self.timestamp,
        }


@dataclass
class ContractMetrics:
    """合约指标.

    属性:
        symbol: 合约代码
        volume: 当日成交量
        open_interest: 持仓量
        last_update: 最后更新时间
    """

    symbol: str
    volume: int = 0
    open_interest: int = 0
    last_update: str = ""


@dataclass
class ProductState:
    """品种状态.

    属性:
        product: 品种代码
        main_contract: 当前主力合约
        contracts: 合约指标字典
        switch_history: 切换历史
    """

    product: str
    main_contract: str | None = None
    contracts: dict[str, ContractMetrics] = field(default_factory=dict)
    switch_history: list[ContractSwitchEvent] = field(default_factory=list)


class MainContractTracker:
    """主力合约追踪器 (军规 M20).

    功能:
    - 基于成交量+持仓量自动检测主力合约
    - 支持切换事件回调
    - 维护切换历史记录
    - 提供审计日志

    示例:
        >>> tracker = MainContractTracker(
        ...     volume_threshold=1.5,
        ...     oi_threshold=1.2,
        ... )
        >>> tracker.update("rb2501", "rb", 100000, 50000)
        >>> tracker.update("rb2505", "rb", 180000, 70000)
        >>> main = tracker.get_main_contract("rb")
        >>> print(main)  # "rb2505"
    """

    # 默认阈值
    DEFAULT_VOLUME_THRESHOLD: ClassVar[float] = 1.5  # 成交量需超过1.5倍
    DEFAULT_OI_THRESHOLD: ClassVar[float] = 1.2  # 持仓量需超过1.2倍
    DEFAULT_COMBINED_THRESHOLD: ClassVar[float] = 1.3  # 综合指标阈值

    def __init__(
        self,
        volume_threshold: float = 1.5,
        oi_threshold: float = 1.2,
        combined_threshold: float = 1.3,
        volume_weight: float = 0.6,
        oi_weight: float = 0.4,
    ) -> None:
        """初始化追踪器.

        参数:
            volume_threshold: 成交量切换阈值 (默认1.5倍)
            oi_threshold: 持仓量切换阈值 (默认1.2倍)
            combined_threshold: 综合指标切换阈值 (默认1.3倍)
            volume_weight: 成交量权重 (默认0.6)
            oi_weight: 持仓量权重 (默认0.4)
        """
        self._volume_threshold = volume_threshold
        self._oi_threshold = oi_threshold
        self._combined_threshold = combined_threshold
        self._volume_weight = volume_weight
        self._oi_weight = oi_weight

        # 品种状态
        self._products: dict[str, ProductState] = {}

        # 回调函数
        self._on_switch_callbacks: list[Callable[[ContractSwitchEvent], None]] = []

        # 统计
        self._update_count: int = 0
        self._switch_count: int = 0

    @property
    def volume_threshold(self) -> float:
        """获取成交量阈值."""
        return self._volume_threshold

    @property
    def oi_threshold(self) -> float:
        """获取持仓量阈值."""
        return self._oi_threshold

    @property
    def update_count(self) -> int:
        """获取更新次数."""
        return self._update_count

    @property
    def switch_count(self) -> int:
        """获取切换次数."""
        return self._switch_count

    def register_callback(
        self, callback: Callable[[ContractSwitchEvent], None]
    ) -> None:
        """注册切换回调.

        参数:
            callback: 切换事件回调函数
        """
        self._on_switch_callbacks.append(callback)

    def unregister_callback(
        self, callback: Callable[[ContractSwitchEvent], None]
    ) -> None:
        """注销切换回调.

        参数:
            callback: 要注销的回调函数
        """
        if callback in self._on_switch_callbacks:
            self._on_switch_callbacks.remove(callback)

    def update(
        self,
        symbol: str,
        product: str,
        volume: int,
        open_interest: int,
    ) -> ContractSwitchEvent | None:
        """更新合约数据.

        参数:
            symbol: 合约代码 (如 "rb2501")
            product: 品种代码 (如 "rb")
            volume: 当日成交量
            open_interest: 持仓量

        返回:
            如果发生切换,返回切换事件; 否则返回None
        """
        self._update_count += 1
        timestamp = datetime.now().isoformat()  # noqa: DTZ005

        # 获取或创建品种状态
        if product not in self._products:
            self._products[product] = ProductState(product=product)

        state = self._products[product]

        # 更新合约指标
        if symbol not in state.contracts:
            state.contracts[symbol] = ContractMetrics(symbol=symbol)

        metrics = state.contracts[symbol]
        # 由于ContractMetrics不是frozen,可以直接更新
        state.contracts[symbol] = ContractMetrics(
            symbol=symbol,
            volume=volume,
            open_interest=open_interest,
            last_update=timestamp,
        )

        # 检测主力合约切换
        switch_event = self._detect_switch(product, timestamp)

        if switch_event is not None:
            self._switch_count += 1
            state.switch_history.append(switch_event)
            self._notify_switch(switch_event)

        return switch_event

    def _detect_switch(
        self, product: str, timestamp: str
    ) -> ContractSwitchEvent | None:
        """检测主力合约切换.

        参数:
            product: 品种代码
            timestamp: 时间戳

        返回:
            切换事件或None
        """
        state = self._products.get(product)
        if state is None or not state.contracts:
            return None

        # 找出成交量最大的合约
        contracts = list(state.contracts.values())
        if not contracts:
            return None

        # 计算综合得分
        best_contract: ContractMetrics | None = None
        best_score = 0.0

        for contract in contracts:
            score = (
                contract.volume * self._volume_weight
                + contract.open_interest * self._oi_weight
            )
            if score > best_score:
                best_score = score
                best_contract = contract

        if best_contract is None:
            return None

        # 首次设置主力合约
        if state.main_contract is None:
            state.main_contract = best_contract.symbol
            return ContractSwitchEvent(
                product=product,
                old_contract=None,
                new_contract=best_contract.symbol,
                reason=SwitchReason.INITIAL,
                timestamp=timestamp,
            )

        # 检查是否需要切换
        if best_contract.symbol == state.main_contract:
            return None

        # 获取当前主力合约指标
        current_metrics = state.contracts.get(state.main_contract)
        if current_metrics is None:
            # 当前主力合约不存在,直接切换
            old_contract = state.main_contract
            state.main_contract = best_contract.symbol
            return ContractSwitchEvent(
                product=product,
                old_contract=old_contract,
                new_contract=best_contract.symbol,
                reason=SwitchReason.COMBINED_DOMINANCE,
                timestamp=timestamp,
            )

        # 计算比率
        volume_ratio = (
            best_contract.volume / current_metrics.volume
            if current_metrics.volume > 0
            else float("inf")
        )
        oi_ratio = (
            best_contract.open_interest / current_metrics.open_interest
            if current_metrics.open_interest > 0
            else float("inf")
        )

        # 判断切换原因和是否切换
        switch_reason: SwitchReason | None = None

        # 成交量主导切换
        if volume_ratio >= self._volume_threshold:
            switch_reason = SwitchReason.VOLUME_DOMINANCE

        # 持仓量主导切换
        elif oi_ratio >= self._oi_threshold:
            switch_reason = SwitchReason.OI_DOMINANCE

        # 综合指标切换
        else:
            combined_ratio = (
                volume_ratio * self._volume_weight + oi_ratio * self._oi_weight
            )
            if combined_ratio >= self._combined_threshold:
                switch_reason = SwitchReason.COMBINED_DOMINANCE

        if switch_reason is None:
            return None

        # 执行切换
        old_contract = state.main_contract
        state.main_contract = best_contract.symbol

        return ContractSwitchEvent(
            product=product,
            old_contract=old_contract,
            new_contract=best_contract.symbol,
            reason=switch_reason,
            volume_ratio=volume_ratio,
            oi_ratio=oi_ratio,
            timestamp=timestamp,
        )

    def _notify_switch(self, event: ContractSwitchEvent) -> None:
        """通知切换事件.

        参数:
            event: 切换事件
        """
        for callback in self._on_switch_callbacks:
            try:
                callback(event)
            except Exception:
                # 回调错误不影响主流程
                pass

    def get_main_contract(self, product: str) -> str | None:
        """获取主力合约.

        参数:
            product: 品种代码

        返回:
            主力合约代码或None
        """
        state = self._products.get(product)
        if state is None:
            return None
        return state.main_contract

    def is_main_contract(self, symbol: str, product: str) -> bool:
        """检查是否为主力合约.

        参数:
            symbol: 合约代码
            product: 品种代码

        返回:
            是否为主力合约
        """
        main = self.get_main_contract(product)
        return main is not None and main == symbol

    def get_switch_history(self, product: str) -> list[ContractSwitchEvent]:
        """获取切换历史.

        参数:
            product: 品种代码

        返回:
            切换事件列表
        """
        state = self._products.get(product)
        if state is None:
            return []
        return list(state.switch_history)

    def get_all_contracts(self, product: str) -> list[str]:
        """获取品种所有合约.

        参数:
            product: 品种代码

        返回:
            合约代码列表
        """
        state = self._products.get(product)
        if state is None:
            return []
        return list(state.contracts.keys())

    def get_contract_metrics(self, symbol: str, product: str) -> ContractMetrics | None:
        """获取合约指标.

        参数:
            symbol: 合约代码
            product: 品种代码

        返回:
            合约指标或None
        """
        state = self._products.get(product)
        if state is None:
            return None
        return state.contracts.get(symbol)

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        return {
            "update_count": self._update_count,
            "switch_count": self._switch_count,
            "product_count": len(self._products),
            "volume_threshold": self._volume_threshold,
            "oi_threshold": self._oi_threshold,
            "combined_threshold": self._combined_threshold,
            "products": {
                product: {
                    "main_contract": state.main_contract,
                    "contract_count": len(state.contracts),
                    "switch_count": len(state.switch_history),
                }
                for product, state in self._products.items()
            },
        }

    def reset(self) -> None:
        """重置追踪器状态."""
        self._products.clear()
        self._update_count = 0
        self._switch_count = 0

    def set_main_contract(
        self, product: str, symbol: str, reason: SwitchReason = SwitchReason.MANUAL
    ) -> ContractSwitchEvent:
        """手动设置主力合约.

        参数:
            product: 品种代码
            symbol: 合约代码
            reason: 切换原因 (默认手动)

        返回:
            切换事件
        """
        timestamp = datetime.now().isoformat()  # noqa: DTZ005

        if product not in self._products:
            self._products[product] = ProductState(product=product)

        state = self._products[product]
        old_contract = state.main_contract
        state.main_contract = symbol

        event = ContractSwitchEvent(
            product=product,
            old_contract=old_contract,
            new_contract=symbol,
            reason=reason,
            timestamp=timestamp,
        )

        self._switch_count += 1
        state.switch_history.append(event)
        self._notify_switch(event)

        return event


# ============================================================
# 便捷函数
# ============================================================


def create_tracker(
    volume_threshold: float = 1.5,
    oi_threshold: float = 1.2,
) -> MainContractTracker:
    """创建主力合约追踪器.

    参数:
        volume_threshold: 成交量阈值
        oi_threshold: 持仓量阈值

    返回:
        追踪器实例
    """
    return MainContractTracker(
        volume_threshold=volume_threshold,
        oi_threshold=oi_threshold,
    )


def extract_product(symbol: str) -> str:
    """从合约代码提取品种代码.

    参数:
        symbol: 合约代码 (如 "rb2501")

    返回:
        品种代码 (如 "rb")

    示例:
        >>> extract_product("rb2501")
        "rb"
        >>> extract_product("IF2501")
        "IF"
    """
    # 找到第一个数字的位置
    for i, char in enumerate(symbol):
        if char.isdigit():
            return symbol[:i]
    return symbol


def is_main_month(symbol: str) -> bool:
    """检查是否为主力月份.

    主力月份通常为: 01, 05, 09, 10 (不同品种有差异)

    参数:
        symbol: 合约代码

    返回:
        是否为主力月份
    """
    # 提取月份
    for i, char in enumerate(symbol):
        if char.isdigit():
            month_str = symbol[i:]
            if len(month_str) >= 4:
                month = int(month_str[2:4])
                return month in (1, 5, 9, 10)
            break
    return False
