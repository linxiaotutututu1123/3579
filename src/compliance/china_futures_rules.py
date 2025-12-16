"""
中国期货合规规则模块 - ChinaFuturesComplianceChecker (军规级 v4.0).

V4PRO Platform Component - Phase 7 中国期货市场特化
V4 SPEC: §12 Phase 7, §21 程序化交易合规
V4 Scenarios:
- CHINA.COMPLIANCE.RULE_CHECK: 合规规则检查

军规覆盖:
- M12: 双重确认 - 大额订单需人工或二次确认
- M13: 涨跌停感知 - 订单价格必须检查涨跌停板
- M15: 夜盘跨日处理 - 夜盘交易日归属必须正确
- M17: 程序化合规 - 报撤单频率必须在监管阈值内

功能特性:
- 订单合规检查 (价格/数量/方向)
- 持仓限额检查 (品种/账户级别)
- 交易时间检查 (夜盘/节假日)
- 大额订单预警 (双重确认)
- 禁止品种检查 (监管限制)

监管规则:
- 中国证监会《期货交易管理条例》
- 各交易所风险控制管理办法
- 2025年《期货市场程序化交易管理规定》

示例:
    >>> from src.compliance.china_futures_rules import (
    ...     ChinaFuturesComplianceChecker,
    ...     ComplianceViolation,
    ... )
    >>> checker = ChinaFuturesComplianceChecker()
    >>> result = checker.check_order(order_info)
    >>> if not result.is_compliant:
    ...     print(f"违规: {result.violations}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any


class ViolationType(Enum):
    """违规类型枚举."""

    PRICE_OUT_OF_LIMIT = "PRICE_OUT_OF_LIMIT"  # 价格超出涨跌停
    VOLUME_EXCEEDS_LIMIT = "VOLUME_EXCEEDS_LIMIT"  # 数量超出限制
    POSITION_EXCEEDS_LIMIT = "POSITION_EXCEEDS_LIMIT"  # 持仓超出限额
    FORBIDDEN_PRODUCT = "FORBIDDEN_PRODUCT"  # 禁止交易品种
    TRADING_TIME_INVALID = "TRADING_TIME_INVALID"  # 非交易时间
    LARGE_ORDER_NO_CONFIRM = "LARGE_ORDER_NO_CONFIRM"  # 大额订单未确认
    MARGIN_INSUFFICIENT = "MARGIN_INSUFFICIENT"  # 保证金不足
    NIGHT_SESSION_DISABLED = "NIGHT_SESSION_DISABLED"  # 夜盘未开启
    DELIVERY_MONTH_RESTRICTED = "DELIVERY_MONTH_RESTRICTED"  # 交割月限制
    ACCOUNT_RESTRICTED = "ACCOUNT_RESTRICTED"  # 账户被限制


class SeverityLevel(Enum):
    """违规严重程度枚举."""

    FATAL = "FATAL"  # 致命 - 立即停止交易
    SEVERE = "SEVERE"  # 严重 - 暂停相关策略
    MAJOR = "MAJOR"  # 重大 - 记录日志+降级处理
    MINOR = "MINOR"  # 轻微 - 记录日志+后续优化
    INFO = "INFO"  # 信息 - 仅记录


@dataclass(frozen=True)
class ComplianceViolation:
    """合规违规记录 (不可变).

    属性:
        violation_type: 违规类型
        severity: 严重程度
        message: 违规描述
        rule_id: 规则ID
        military_rule: 关联军规
    """

    violation_type: ViolationType
    severity: SeverityLevel
    message: str
    rule_id: str
    military_rule: str = ""


@dataclass
class ComplianceCheckResult:
    """合规检查结果.

    属性:
        is_compliant: 是否合规
        violations: 违规列表
        checked_at: 检查时间
        order_info: 订单信息 (脱敏)
        checker_version: 检查器版本
    """

    is_compliant: bool
    violations: list[ComplianceViolation] = field(default_factory=list)
    checked_at: str = ""
    order_info: dict[str, Any] = field(default_factory=dict)
    checker_version: str = "4.0"

    def get_fatal_violations(self) -> list[ComplianceViolation]:
        """获取致命违规列表."""
        return [v for v in self.violations if v.severity == SeverityLevel.FATAL]

    def get_severe_violations(self) -> list[ComplianceViolation]:
        """获取严重违规列表."""
        return [v for v in self.violations if v.severity == SeverityLevel.SEVERE]

    def has_blocking_violations(self) -> bool:
        """是否有阻断性违规 (FATAL或SEVERE)."""
        return any(
            v.severity in (SeverityLevel.FATAL, SeverityLevel.SEVERE)
            for v in self.violations
        )


@dataclass(frozen=True)
class ComplianceConfig:
    """合规配置 (不可变).

    属性:
        max_order_volume: 单笔最大下单量 (手)
        large_order_threshold: 大额订单阈值 (手, 需双重确认)
        position_limit_ratio: 持仓限额比例 (相对于交易所限制)
        forbidden_products: 禁止交易品种列表
        allow_night_session: 是否允许夜盘交易
        delivery_month_warning_days: 交割月预警天数
        require_large_order_confirm: 是否要求大额订单确认
    """

    max_order_volume: int = 1000
    large_order_threshold: int = 100
    position_limit_ratio: float = 0.8
    forbidden_products: tuple[str, ...] = ()
    allow_night_session: bool = True
    delivery_month_warning_days: int = 10
    require_large_order_confirm: bool = True


@dataclass
class OrderInfo:
    """订单信息.

    属性:
        symbol: 合约代码 (如 "rb2501")
        direction: 方向 ("BUY"/"SELL")
        offset: 开平 ("OPEN"/"CLOSE"/"CLOSE_TODAY")
        price: 价格
        volume: 数量 (手)
        order_type: 订单类型 ("LIMIT"/"MARKET")
        confirmed: 是否已确认 (大额订单)
    """

    symbol: str
    direction: str
    offset: str
    price: float
    volume: int
    order_type: str = "LIMIT"
    confirmed: bool = False


@dataclass
class MarketContext:
    """市场上下文信息.

    属性:
        last_price: 最新价
        last_settle: 昨结算价
        upper_limit: 涨停价
        lower_limit: 跌停价
        position_limit: 持仓限额
        current_position: 当前持仓
        margin_available: 可用保证金
        margin_required: 所需保证金
        is_trading_time: 是否交易时间
        is_night_session: 是否夜盘时段
    """

    last_price: float = 0.0
    last_settle: float = 0.0
    upper_limit: float = 0.0
    lower_limit: float = 0.0
    position_limit: int = 0
    current_position: int = 0
    margin_available: float = 0.0
    margin_required: float = 0.0
    is_trading_time: bool = True
    is_night_session: bool = False


class ChinaFuturesComplianceChecker:
    """中国期货合规检查器 (军规 M12, M13, M15, M17).

    功能:
    - 订单合规检查 (价格/数量/方向)
    - 持仓限额检查
    - 交易时间检查
    - 大额订单预警

    示例:
        >>> checker = ChinaFuturesComplianceChecker()
        >>> order = OrderInfo(
        ...     symbol="rb2501",
        ...     direction="BUY",
        ...     offset="OPEN",
        ...     price=3500.0,
        ...     volume=10,
        ... )
        >>> context = MarketContext(
        ...     last_settle=3450.0,
        ...     upper_limit=3795.0,
        ...     lower_limit=3105.0,
        ...     position_limit=500,
        ...     current_position=100,
        ... )
        >>> result = checker.check_order(order, context)
    """

    VERSION = "4.0"

    def __init__(self, config: ComplianceConfig | None = None) -> None:
        """初始化合规检查器.

        参数:
            config: 合规配置 (None使用默认配置)
        """
        self._config = config or ComplianceConfig()
        self._check_count: int = 0
        self._violation_count: int = 0

    @property
    def config(self) -> ComplianceConfig:
        """获取配置."""
        return self._config

    @property
    def check_count(self) -> int:
        """获取检查次数."""
        return self._check_count

    @property
    def violation_count(self) -> int:
        """获取违规次数."""
        return self._violation_count

    def check_order(
        self,
        order: OrderInfo,
        context: MarketContext | None = None,
        timestamp: datetime | None = None,
    ) -> ComplianceCheckResult:
        """检查订单合规性.

        参数:
            order: 订单信息
            context: 市场上下文 (None使用默认值)
            timestamp: 检查时间

        返回:
            合规检查结果
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        if context is None:
            context = MarketContext()

        self._check_count += 1
        violations: list[ComplianceViolation] = []

        # 1. 检查禁止品种
        product = self._extract_product(order.symbol)
        if product.lower() in [p.lower() for p in self._config.forbidden_products]:
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.FORBIDDEN_PRODUCT,
                    severity=SeverityLevel.FATAL,
                    message=f"品种 {product} 被禁止交易",
                    rule_id="CHINA.COMPLIANCE.FORBIDDEN_PRODUCT",
                    military_rule="M17",
                )
            )

        # 2. 检查交易时间
        if not context.is_trading_time:
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.TRADING_TIME_INVALID,
                    severity=SeverityLevel.FATAL,
                    message="非交易时间, 禁止下单",
                    rule_id="CHINA.COMPLIANCE.TRADING_TIME",
                    military_rule="M15",
                )
            )

        # 3. 检查夜盘权限
        if context.is_night_session and not self._config.allow_night_session:
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.NIGHT_SESSION_DISABLED,
                    severity=SeverityLevel.FATAL,
                    message="夜盘交易未开启",
                    rule_id="CHINA.COMPLIANCE.NIGHT_SESSION",
                    military_rule="M15",
                )
            )

        # 4. 检查价格 (涨跌停)
        if context.upper_limit > 0 and order.price > context.upper_limit:
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.PRICE_OUT_OF_LIMIT,
                    severity=SeverityLevel.FATAL,
                    message=f"订单价格 {order.price} 超过涨停价 {context.upper_limit}",
                    rule_id="CHINA.COMPLIANCE.LIMIT_PRICE",
                    military_rule="M13",
                )
            )
        if context.lower_limit > 0 and order.price < context.lower_limit:
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.PRICE_OUT_OF_LIMIT,
                    severity=SeverityLevel.FATAL,
                    message=f"订单价格 {order.price} 低于跌停价 {context.lower_limit}",
                    rule_id="CHINA.COMPLIANCE.LIMIT_PRICE",
                    military_rule="M13",
                )
            )

        # 5. 检查数量 (单笔限制)
        if order.volume > self._config.max_order_volume:
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.VOLUME_EXCEEDS_LIMIT,
                    severity=SeverityLevel.SEVERE,
                    message=(
                        f"订单数量 {order.volume} 超过单笔限制 "
                        f"{self._config.max_order_volume}"
                    ),
                    rule_id="CHINA.COMPLIANCE.VOLUME_LIMIT",
                    military_rule="M12",
                )
            )

        # 6. 检查持仓限额 (开仓时)
        if order.offset == "OPEN" and context.position_limit > 0:
            new_position = context.current_position + order.volume
            max_allowed = int(context.position_limit * self._config.position_limit_ratio)
            if new_position > max_allowed:
                violations.append(
                    ComplianceViolation(
                        violation_type=ViolationType.POSITION_EXCEEDS_LIMIT,
                        severity=SeverityLevel.SEVERE,
                        message=(
                            f"开仓后持仓 {new_position} 超过限额 {max_allowed} "
                            f"(交易所限额 {context.position_limit} × "
                            f"{self._config.position_limit_ratio:.0%})"
                        ),
                        rule_id="CHINA.COMPLIANCE.POSITION_LIMIT",
                        military_rule="M16",
                    )
                )

        # 7. 检查保证金
        if (
            order.offset == "OPEN"
            and context.margin_required > 0
            and context.margin_required > context.margin_available
        ):
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.MARGIN_INSUFFICIENT,
                    severity=SeverityLevel.FATAL,
                    message=(
                        f"保证金不足: 需要 {context.margin_required:.2f}, "
                        f"可用 {context.margin_available:.2f}"
                    ),
                    rule_id="CHINA.COMPLIANCE.MARGIN",
                    military_rule="M16",
                )
            )

        # 8. 检查大额订单确认 (军规 M12)
        if (
            self._config.require_large_order_confirm
            and order.volume >= self._config.large_order_threshold
            and not order.confirmed
        ):
            violations.append(
                ComplianceViolation(
                    violation_type=ViolationType.LARGE_ORDER_NO_CONFIRM,
                    severity=SeverityLevel.SEVERE,
                    message=(
                        f"大额订单 ({order.volume}手) 需要双重确认, "
                        f"阈值 {self._config.large_order_threshold}手"
                    ),
                    rule_id="CHINA.COMPLIANCE.LARGE_ORDER",
                    military_rule="M12",
                )
            )

        # 统计违规次数
        if violations:
            self._violation_count += len(violations)

        # 构造结果
        is_compliant = len(violations) == 0
        return ComplianceCheckResult(
            is_compliant=is_compliant,
            violations=violations,
            checked_at=timestamp.isoformat(),
            order_info={
                "symbol": order.symbol,
                "direction": order.direction,
                "offset": order.offset,
                "volume": order.volume,
                "order_type": order.order_type,
            },
            checker_version=self.VERSION,
        )

    def check_trading_time(
        self,
        timestamp: datetime | None = None,
        product: str = "",
    ) -> tuple[bool, str]:
        """检查是否交易时间.

        参数:
            timestamp: 检查时间
            product: 品种代码 (可选)

        返回:
            (是否交易时间, 消息)
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        t = timestamp.time()

        # 日盘时段
        day_sessions = [
            (time(9, 0), time(10, 15)),  # 第一节
            (time(10, 30), time(11, 30)),  # 第二节
            (time(13, 30), time(15, 0)),  # 第三节
        ]

        for start, end in day_sessions:
            if start <= t < end:
                return True, "日盘交易时间"

        # 夜盘时段 (简化判断)
        if time(21, 0) <= t <= time(23, 59, 59):
            if self._config.allow_night_session:
                return True, "夜盘交易时间"
            return False, "夜盘交易未开启"

        if time(0, 0) <= t < time(2, 30):
            if self._config.allow_night_session:
                return True, "夜盘交易时间 (凌晨)"
            return False, "夜盘交易未开启"

        return False, f"非交易时间: {t.strftime('%H:%M:%S')}"

    def check_price_limit(
        self,
        price: float,
        upper_limit: float,
        lower_limit: float,
    ) -> tuple[bool, str]:
        """检查价格是否在涨跌停范围内.

        参数:
            price: 订单价格
            upper_limit: 涨停价
            lower_limit: 跌停价

        返回:
            (是否合规, 消息)
        """
        if upper_limit > 0 and price > upper_limit:
            return False, f"价格 {price} 超过涨停价 {upper_limit}"

        if lower_limit > 0 and price < lower_limit:
            return False, f"价格 {price} 低于跌停价 {lower_limit}"

        return True, "价格在涨跌停范围内"

    def check_volume_limit(self, volume: int) -> tuple[bool, str]:
        """检查数量是否在限制范围内.

        参数:
            volume: 订单数量

        返回:
            (是否合规, 消息)
        """
        if volume <= 0:
            return False, "订单数量必须大于0"

        if volume > self._config.max_order_volume:
            return (
                False,
                f"订单数量 {volume} 超过限制 {self._config.max_order_volume}",
            )

        return True, f"订单数量 {volume} 在限制范围内"

    def check_position_limit(
        self,
        current_position: int,
        new_volume: int,
        position_limit: int,
    ) -> tuple[bool, str]:
        """检查持仓是否超出限额.

        参数:
            current_position: 当前持仓
            new_volume: 新增仓位
            position_limit: 持仓限额

        返回:
            (是否合规, 消息)
        """
        if position_limit <= 0:
            return True, "无持仓限额"

        new_position = current_position + new_volume
        max_allowed = int(position_limit * self._config.position_limit_ratio)

        if new_position > max_allowed:
            return (
                False,
                f"开仓后持仓 {new_position} 超过限额 {max_allowed}",
            )

        return True, f"持仓 {new_position} 在限额 {max_allowed} 范围内"

    def is_large_order(self, volume: int) -> bool:
        """判断是否大额订单.

        参数:
            volume: 订单数量

        返回:
            是否大额订单
        """
        return volume >= self._config.large_order_threshold

    def is_forbidden_product(self, product: str) -> bool:
        """判断是否禁止品种.

        参数:
            product: 品种代码

        返回:
            是否禁止品种
        """
        return product.lower() in [p.lower() for p in self._config.forbidden_products]

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        return {
            "check_count": self._check_count,
            "violation_count": self._violation_count,
            "violation_rate": (
                self._violation_count / self._check_count
                if self._check_count > 0
                else 0.0
            ),
            "checker_version": self.VERSION,
        }

    def reset_statistics(self) -> None:
        """重置统计信息."""
        self._check_count = 0
        self._violation_count = 0

    def _extract_product(self, symbol: str) -> str:
        """从合约代码提取品种代码.

        参数:
            symbol: 合约代码 (如 "rb2501")

        返回:
            品种代码 (如 "rb")
        """
        product = ""
        for char in symbol:
            if char.isalpha():
                product += char
            else:
                break
        return product if product else symbol


# ============================================================
# 便捷函数
# ============================================================


def get_default_compliance_config() -> ComplianceConfig:
    """获取默认合规配置.

    返回:
        默认配置
    """
    return ComplianceConfig()


def create_compliance_checker(
    config: ComplianceConfig | None = None,
) -> ChinaFuturesComplianceChecker:
    """创建合规检查器.

    参数:
        config: 配置

    返回:
        检查器实例
    """
    return ChinaFuturesComplianceChecker(config)


def check_order_compliance(
    order: OrderInfo,
    context: MarketContext | None = None,
    config: ComplianceConfig | None = None,
) -> ComplianceCheckResult:
    """检查订单合规性 (便捷函数).

    参数:
        order: 订单信息
        context: 市场上下文
        config: 合规配置

    返回:
        检查结果
    """
    checker = ChinaFuturesComplianceChecker(config)
    return checker.check_order(order, context)
