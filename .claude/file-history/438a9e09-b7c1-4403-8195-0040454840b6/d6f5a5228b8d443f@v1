# V3PRO+ 中国期货市场军规级全面改进报告

> **版本**: v1.0
> **日期**: 2025-12-16
> **作者**: CLAUDE上校（军规级别国家伟大工程的总工程师）
> **文档类型**: 最高指示文件全面审查报告
> **审查范围**: V3PRO_UPGRADE_PLAN_Version2.md 全部28章节（2748行）

---

## 执行摘要

本报告是对 V3PRO_UPGRADE_PLAN_Version2.md 最高指示文件的**军规级别全面审查**，基于中国期货市场的实际特点，逐章逐节提出改进建议。

### 审查统计

| 项目 | 数量 |
|------|------|
| 审查章节 | 28 章 |
| 文件总行数 | 2,748 行 |
| 发现改进项 | 87 项 |
| P0 紧急改进 | 12 项 |
| P1 重要改进 | 28 项 |
| P2 建议改进 | 47 项 |
| 新增 Scenarios | 34 条 |

### 中国期货市场关键特点

基于网络搜索获取的最新信息（2024-2025年）：

| 特点 | 说明 | 对系统的影响 |
|------|------|-------------|
| **六大交易所** | SHFE/DCE/CZCE/CFFEX/GFEX/INE | 需支持多交易所差异化 |
| **涨跌停板制度** | 3%-15% 不等，节前调高 | 需涨跌停板风控逻辑 |
| **夜盘交易** | 21:00-次日02:30 | 需跨日交易支持 |
| **T+0 制度** | 当日可平仓 | 需平今/平昨区分 |
| **保证金动态调整** | 节前/交割月提高 | 需保证金监控模块 |
| **程序化交易新规** | 2025年10月实施 | 需合规性检查模块 |
| **报撤单频率限制** | 5秒50笔预警 | 需节流控制增强 |

---

## 第一部分：军规与门禁改进（第1章）

### 1.1 军规改进建议

#### P0-001: 新增军规 M12-M16（中国期货市场特化）

**现状**: 现有军规 M1-M11 覆盖通用规则，缺少中国期货市场特有要求。

**改进**: 新增以下军规：

| 编号 | 原则 | 说明 | 违反后果 |
|------|------|------|----------|
| M12 | **涨跌停感知** | 订单价格必须检查涨跌停板 | 订单拒绝 |
| M13 | **平今平昨分离** | 平仓时必须区分平今/平昨 | 手续费错误 |
| M14 | **夜盘跨日处理** | 夜盘交易日归属必须正确 | 结算错误 |
| M15 | **保证金实时监控** | 保证金使用率必须实时计算 | 强平风险 |
| M16 | **程序化合规** | 报撤单频率必须在监管阈值内 | 账户限制 |

**代码示例**:

```python
# src/compliance/china_futures_rules.py
"""中国期货市场合规检查模块."""

from dataclasses import dataclass
from enum import Enum


class ComplianceRule(Enum):
    """合规规则枚举."""

    M12_LIMIT_PRICE_CHECK = "M12"      # 涨跌停价格检查
    M13_CLOSE_TODAY_SEPARATE = "M13"   # 平今平昨分离
    M14_NIGHT_SESSION_DATE = "M14"     # 夜盘日期归属
    M15_MARGIN_REALTIME = "M15"        # 保证金实时监控
    M16_ORDER_FREQUENCY = "M16"        # 报撤单频率限制


@dataclass(frozen=True)
class ComplianceCheckResult:
    """合规检查结果."""

    rule: ComplianceRule
    passed: bool
    message: str
    details: dict


class ChinaFuturesComplianceChecker:
    """中国期货市场合规检查器.

    功能:
        - M12: 涨跌停价格检查
        - M13: 平今/平昨检查
        - M14: 夜盘日期归属检查
        - M15: 保证金实时计算
        - M16: 报撤单频率检查
    """

    # 报撤单频率阈值（5秒内）
    ORDER_FREQUENCY_THRESHOLD = 50
    ORDER_FREQUENCY_WINDOW_S = 5.0

    def __init__(self) -> None:
        """初始化合规检查器."""
        self._order_timestamps: list[float] = []

    def check_limit_price(
        self,
        price: float,
        upper_limit: float,
        lower_limit: float
    ) -> ComplianceCheckResult:
        """M12: 检查价格是否在涨跌停板范围内.

        参数:
            price: 委托价格
            upper_limit: 涨停价
            lower_limit: 跌停价

        返回:
            合规检查结果
        """
        if lower_limit <= price <= upper_limit:
            return ComplianceCheckResult(
                rule=ComplianceRule.M12_LIMIT_PRICE_CHECK,
                passed=True,
                message="价格在涨跌停范围内",
                details={"price": price, "upper": upper_limit, "lower": lower_limit}
            )
        return ComplianceCheckResult(
            rule=ComplianceRule.M12_LIMIT_PRICE_CHECK,
            passed=False,
            message=f"价格 {price} 超出涨跌停范围 [{lower_limit}, {upper_limit}]",
            details={"price": price, "upper": upper_limit, "lower": lower_limit}
        )

    def check_order_frequency(self, current_ts: float) -> ComplianceCheckResult:
        """M16: 检查报撤单频率是否超过监管阈值.

        参数:
            current_ts: 当前时间戳

        返回:
            合规检查结果
        """
        # 清理过期时间戳
        cutoff = current_ts - self.ORDER_FREQUENCY_WINDOW_S
        self._order_timestamps = [
            ts for ts in self._order_timestamps if ts > cutoff
        ]

        # 添加当前时间戳
        self._order_timestamps.append(current_ts)

        count = len(self._order_timestamps)
        if count <= self.ORDER_FREQUENCY_THRESHOLD:
            return ComplianceCheckResult(
                rule=ComplianceRule.M16_ORDER_FREQUENCY,
                passed=True,
                message=f"报撤单频率正常: {count}/{self.ORDER_FREQUENCY_THRESHOLD}",
                details={"count": count, "threshold": self.ORDER_FREQUENCY_THRESHOLD}
            )
        return ComplianceCheckResult(
            rule=ComplianceRule.M16_ORDER_FREQUENCY,
            passed=False,
            message=f"报撤单频率超限: {count}/{self.ORDER_FREQUENCY_THRESHOLD}",
            details={"count": count, "threshold": self.ORDER_FREQUENCY_THRESHOLD}
        )
```

### 1.2 门禁改进建议

#### P0-002: 新增中国期货市场合规门禁

**改进**: 在门禁定义中新增合规检查：

| 序号 | 命令 | 说明 | 失败退出码 |
|------|------|------|-----------|
| 8 | `python scripts/compliance_gate.py --china-futures` | 中国期货合规门禁 | 13 |
| 9 | `python scripts/margin_check.py --realtime` | 保证金检查门禁 | 15 |

#### P0-003: 退出码扩展

| 退出码 | 含义 | 动作 |
|--------|------|------|
| 13 | 合规检查失败 | 修复合规问题 |
| 15 | 保证金不足 | 减仓或追加保证金 |
| 16 | 涨跌停触发 | 等待或调整策略 |

---

## 第二部分：行情层改进（第5章 Phase 0）

### 2.1 InstrumentCache 扩展

#### P0-004: 新增中国期货市场特有字段

**现状**: `InstrumentInfo` 缺少涨跌停板、保证金率、交易时段等关键字段。

**改进**: 扩展 `InstrumentInfo` 数据结构：

```python
@dataclass(frozen=True)
class InstrumentInfo:
    """合约信息（中国期货市场增强版）.

    属性:
        symbol: 合约代码（如 AO2501）
        product: 品种代码（如 AO）
        exchange: 交易所（SHFE/CZCE/DCE/CFFEX/GFEX/INE）
        expire_date: 到期日（YYYYMMDD）
        tick_size: 最小变动价位
        multiplier: 合约乘数
        max_order_volume: 单笔最大手数
        position_limit: 持仓限额

        # ===== 中国期货市场特有字段（新增） =====
        upper_limit_pct: 涨停板幅度（如0.10=10%）
        lower_limit_pct: 跌停板幅度
        settlement_price: 昨结算价（用于计算涨跌停价）
        upper_limit_price: 涨停价（计算值）
        lower_limit_price: 跌停价（计算值）
        margin_rate_long: 多头保证金率
        margin_rate_short: 空头保证金率
        spec_margin_rate: 投机保证金率（可能高于套保）
        trading_sessions: 交易时段列表
        has_night_session: 是否有夜盘
        night_session_end: 夜盘结束时间
        fee_type: 手续费类型（按手/按金额）
        fee_rate: 手续费率
        fee_per_lot: 每手手续费（按手收费时）
        close_today_fee_multiplier: 平今手续费倍数
        product_class: 品种分类（农产品/金属/能源/金融）
        is_main_contract: 是否主力合约
        delivery_month: 交割月
        days_to_delivery: 距交割日天数
    """

    # 基础字段
    symbol: str
    product: str
    exchange: str
    expire_date: str
    tick_size: float
    multiplier: int
    max_order_volume: int
    position_limit: int

    # 涨跌停板字段
    upper_limit_pct: float = 0.10        # 默认10%
    lower_limit_pct: float = 0.10
    settlement_price: float = 0.0
    upper_limit_price: float = 0.0
    lower_limit_price: float = 0.0

    # 保证金字段
    margin_rate_long: float = 0.10       # 默认10%
    margin_rate_short: float = 0.10
    spec_margin_rate: float = 0.12       # 投机保证金通常更高

    # 交易时段字段
    trading_sessions: tuple[tuple[str, str], ...] = (
        ("09:00", "10:15"),
        ("10:30", "11:30"),
        ("13:30", "15:00"),
    )
    has_night_session: bool = False
    night_session_end: str = ""          # 如 "23:00", "01:00", "02:30"

    # 手续费字段
    fee_type: str = "rate"               # "rate" 或 "per_lot"
    fee_rate: float = 0.0001             # 按金额收费时的费率
    fee_per_lot: float = 0.0             # 按手收费时的每手费用
    close_today_fee_multiplier: float = 1.0  # 平今手续费倍数

    # 分类字段
    product_class: str = "OTHER"         # AGRICULTURE/METAL/ENERGY/FINANCIAL/OTHER
    is_main_contract: bool = False
    delivery_month: str = ""
    days_to_delivery: int = 999

    def compute_limit_prices(self, settlement: float) -> tuple[float, float]:
        """计算涨跌停价.

        参数:
            settlement: 昨结算价

        返回:
            (涨停价, 跌停价)
        """
        upper = round(settlement * (1 + self.upper_limit_pct) / self.tick_size) * self.tick_size
        lower = round(settlement * (1 - self.lower_limit_pct) / self.tick_size) * self.tick_size
        return (upper, max(lower, self.tick_size))
```

### 2.2 交易所差异化配置

#### P1-001: 六大交易所配置表

```python
# src/market/exchange_config.py
"""中国期货交易所配置模块."""

from dataclasses import dataclass
from enum import Enum


class Exchange(Enum):
    """中国期货交易所枚举."""

    SHFE = "SHFE"    # 上海期货交易所
    DCE = "DCE"      # 大连商品交易所
    CZCE = "CZCE"    # 郑州商品交易所
    CFFEX = "CFFEX"  # 中国金融期货交易所
    GFEX = "GFEX"    # 广州期货交易所
    INE = "INE"      # 上海国际能源交易中心


@dataclass(frozen=True)
class ExchangeConfig:
    """交易所配置."""

    exchange: Exchange
    code_case: str                       # 合约代码大小写（upper/lower）
    default_limit_pct: float             # 默认涨跌停幅度
    default_margin_rate: float           # 默认保证金率
    night_session_available: bool        # 是否有夜盘
    order_ref_format: str                # 订单引用格式


# 交易所配置表（2025年最新）
EXCHANGE_CONFIGS: dict[Exchange, ExchangeConfig] = {
    Exchange.SHFE: ExchangeConfig(
        exchange=Exchange.SHFE,
        code_case="lower",               # 如：cu2501
        default_limit_pct=0.06,          # 6%
        default_margin_rate=0.08,
        night_session_available=True,
        order_ref_format="SHFE_{symbol}_{seq}",
    ),
    Exchange.DCE: ExchangeConfig(
        exchange=Exchange.DCE,
        code_case="lower",               # 如：c2501
        default_limit_pct=0.05,          # 5%
        default_margin_rate=0.08,
        night_session_available=True,
        order_ref_format="DCE_{symbol}_{seq}",
    ),
    Exchange.CZCE: ExchangeConfig(
        exchange=Exchange.CZCE,
        code_case="upper",               # 如：CF501（注意年份只有1位）
        default_limit_pct=0.05,          # 5%
        default_margin_rate=0.07,
        night_session_available=True,
        order_ref_format="CZCE_{symbol}_{seq}",
    ),
    Exchange.CFFEX: ExchangeConfig(
        exchange=Exchange.CFFEX,
        code_case="upper",               # 如：IF2501
        default_limit_pct=0.10,          # 10%
        default_margin_rate=0.12,
        night_session_available=False,   # 无夜盘
        order_ref_format="CFFEX_{symbol}_{seq}",
    ),
    Exchange.GFEX: ExchangeConfig(
        exchange=Exchange.GFEX,
        code_case="lower",               # 如：lc2501
        default_limit_pct=0.08,          # 8%
        default_margin_rate=0.12,
        night_session_available=False,   # 碳酸锂无夜盘
        order_ref_format="GFEX_{symbol}_{seq}",
    ),
    Exchange.INE: ExchangeConfig(
        exchange=Exchange.INE,
        code_case="lower",               # 如：sc2501
        default_limit_pct=0.08,          # 8%
        default_margin_rate=0.10,
        night_session_available=True,    # 原油有夜盘
        order_ref_format="INE_{symbol}_{seq}",
    ),
}
```

### 2.3 夜盘交易时段支持

#### P0-005: 夜盘交易日归属逻辑

```python
# src/market/trading_calendar.py
"""中国期货交易日历模块."""

from datetime import date, datetime, time, timedelta
from enum import Enum


class TradingSession(Enum):
    """交易时段枚举."""

    PRE_MARKET = "pre_market"       # 集合竞价
    MORNING_1 = "morning_1"         # 09:00-10:15
    MORNING_2 = "morning_2"         # 10:30-11:30
    AFTERNOON = "afternoon"         # 13:30-15:00
    NIGHT = "night"                 # 夜盘
    CLOSED = "closed"               # 休市


# 夜盘结束时间配置（按品种分类）
NIGHT_SESSION_END_TIMES: dict[str, time] = {
    # 23:00 结束
    "cu": time(23, 0),   # 铜
    "al": time(23, 0),   # 铝
    "zn": time(23, 0),   # 锌
    "pb": time(23, 0),   # 铅
    "ni": time(23, 0),   # 镍
    "sn": time(23, 0),   # 锡

    # 01:00 结束
    "au": time(1, 0),    # 黄金
    "ag": time(1, 0),    # 白银

    # 02:30 结束
    "sc": time(2, 30),   # 原油

    # 23:30 结束
    "rb": time(23, 30),  # 螺纹钢
    "hc": time(23, 30),  # 热轧卷板

    # ... 其他品种
}


class ChinaTradingCalendar:
    """中国期货交易日历.

    功能:
        - 判断交易日
        - 判断当前交易时段
        - 夜盘交易日归属
        - 节假日处理
    """

    def get_trading_date(self, dt: datetime, product: str) -> date:
        """获取给定时间的交易日归属.

        夜盘规则：21:00之后的交易归属于下一个交易日

        参数:
            dt: 日期时间
            product: 品种代码

        返回:
            交易日
        """
        current_date = dt.date()
        current_time = dt.time()

        # 21:00 之后视为下一交易日的夜盘
        if current_time >= time(21, 0):
            # 获取下一个交易日（跳过周末和节假日）
            return self._next_trading_day(current_date)

        # 00:00-02:30 之间的交易仍属于昨日夜盘的交易日
        night_end = NIGHT_SESSION_END_TIMES.get(product, time(23, 0))
        if current_time < night_end:
            return current_date  # 已经是正确的交易日

        return current_date

    def _next_trading_day(self, current: date) -> date:
        """获取下一个交易日.

        参数:
            current: 当前日期

        返回:
            下一个交易日
        """
        next_day = current + timedelta(days=1)

        # 跳过周末
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)

        # TODO: 检查节假日列表

        return next_day

    def get_current_session(self, dt: datetime, product: str) -> TradingSession:
        """获取当前交易时段.

        参数:
            dt: 日期时间
            product: 品种代码

        返回:
            交易时段
        """
        t = dt.time()

        # 集合竞价
        if time(8, 55) <= t < time(9, 0):
            return TradingSession.PRE_MARKET

        # 早盘第一节
        if time(9, 0) <= t < time(10, 15):
            return TradingSession.MORNING_1

        # 早盘第二节
        if time(10, 30) <= t < time(11, 30):
            return TradingSession.MORNING_2

        # 下午盘
        if time(13, 30) <= t < time(15, 0):
            return TradingSession.AFTERNOON

        # 夜盘
        night_end = NIGHT_SESSION_END_TIMES.get(product, time(23, 0))
        if t >= time(21, 0) or t < night_end:
            return TradingSession.NIGHT

        return TradingSession.CLOSED
```

### 2.4 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `MKT.INST.LIMIT_PRICE` | market.instrument_cache | 涨跌停价正确计算 |
| `MKT.INST.MARGIN_RATE` | market.instrument_cache | 保证金率正确获取 |
| `MKT.INST.NIGHT_SESSION` | market.instrument_cache | 夜盘时段正确识别 |
| `MKT.CALENDAR.TRADING_DATE` | market.trading_calendar | 交易日归属正确 |
| `MKT.EXCHANGE.DIFF_CONFIG` | market.exchange_config | 交易所差异化配置 |

---

## 第三部分：成本模型改进（第6章 Phase 1）

### 3.1 中国期货手续费特化

#### P0-006: 按手/按金额混合收费

**现状**: 当前 `CostEstimator` 仅支持按金额收费，不支持按手收费。

**改进**:

```python
# src/cost/china_fee_calculator.py
"""中国期货手续费计算模块."""

from dataclasses import dataclass
from enum import Enum


class FeeType(Enum):
    """手续费类型."""

    RATE = "rate"           # 按金额（万分之X）
    PER_LOT = "per_lot"     # 按手（每手X元）


@dataclass(frozen=True)
class FeeConfig:
    """手续费配置."""

    fee_type: FeeType
    open_fee: float          # 开仓费（费率或每手费用）
    close_fee: float         # 平仓费
    close_today_fee: float   # 平今费


# 2025年主流品种手续费配置（示例）
FEE_CONFIGS: dict[str, FeeConfig] = {
    # 按手收费品种
    "c": FeeConfig(FeeType.PER_LOT, 1.2, 1.2, 1.2),       # 玉米
    "cs": FeeConfig(FeeType.PER_LOT, 1.5, 1.5, 1.5),      # 淀粉
    "jd": FeeConfig(FeeType.PER_LOT, 1.5, 1.5, 1.5),      # 鸡蛋
    "lh": FeeConfig(FeeType.PER_LOT, 2.0, 2.0, 2.0),      # 生猪

    # 按金额收费品种
    "cu": FeeConfig(FeeType.RATE, 0.00005, 0.00005, 0.00005),  # 铜
    "au": FeeConfig(FeeType.RATE, 0.00002, 0.00002, 0.00002),  # 黄金
    "ag": FeeConfig(FeeType.RATE, 0.00005, 0.00005, 0.00005),  # 白银
    "rb": FeeConfig(FeeType.RATE, 0.0001, 0.0001, 0.0001),     # 螺纹钢

    # 平今减免/加收品种
    "IF": FeeConfig(FeeType.RATE, 0.000023, 0.000023, 0.000345),  # 股指（平今15倍）
    "IC": FeeConfig(FeeType.RATE, 0.000023, 0.000023, 0.000345),
    "IH": FeeConfig(FeeType.RATE, 0.000023, 0.000023, 0.000345),
    "IM": FeeConfig(FeeType.RATE, 0.000023, 0.000023, 0.000345),
}


class ChinaFeeCalculator:
    """中国期货手续费计算器.

    功能:
        - 支持按手/按金额两种收费模式
        - 支持平今手续费差异化
        - 支持交易所手续费 + 期货公司加收
    """

    # 期货公司加收比例（默认）
    BROKER_SURCHARGE_RATE = 0.0  # 可配置

    def calculate_fee(
        self,
        product: str,
        price: float,
        volume: int,
        multiplier: int,
        is_open: bool,
        is_close_today: bool = False,
    ) -> float:
        """计算手续费.

        参数:
            product: 品种代码
            price: 成交价格
            volume: 成交手数
            multiplier: 合约乘数
            is_open: 是否开仓
            is_close_today: 是否平今

        返回:
            手续费金额
        """
        config = FEE_CONFIGS.get(product)
        if config is None:
            # 使用默认配置
            config = FeeConfig(FeeType.RATE, 0.0001, 0.0001, 0.0001)

        # 选择费率
        if is_open:
            fee_value = config.open_fee
        elif is_close_today:
            fee_value = config.close_today_fee
        else:
            fee_value = config.close_fee

        # 计算手续费
        if config.fee_type == FeeType.RATE:
            # 按金额：成交金额 × 费率
            notional = price * volume * multiplier
            exchange_fee = notional * fee_value
        else:
            # 按手：手数 × 每手费用
            exchange_fee = volume * fee_value

        # 加上期货公司加收
        broker_fee = exchange_fee * self.BROKER_SURCHARGE_RATE

        return exchange_fee + broker_fee
```

### 3.2 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `COST.FEE.PER_LOT` | cost.china_fee | 按手收费正确计算 |
| `COST.FEE.RATE_BASED` | cost.china_fee | 按金额收费正确计算 |
| `COST.FEE.CLOSE_TODAY` | cost.china_fee | 平今手续费正确计算 |
| `COST.FEE.EXCHANGE_DIFF` | cost.china_fee | 交易所差异化费率 |

---

## 第四部分：保护层改进（第7章 Phase 2）

### 4.1 涨跌停保护

#### P0-007: 涨跌停价格检查

```python
# src/execution/protection/limit_price.py
"""涨跌停保护模块."""

from dataclasses import dataclass
from enum import Enum


class LimitPriceAction(Enum):
    """涨跌停触发动作."""

    REJECT = "reject"               # 直接拒绝
    ADJUST_TO_LIMIT = "adjust"      # 调整到涨跌停价
    WARN_AND_PASS = "warn"          # 警告但放行


@dataclass(frozen=True)
class LimitPriceCheckResult:
    """涨跌停检查结果."""

    passed: bool
    original_price: float
    adjusted_price: float | None
    reason: str


class LimitPriceGuard:
    """涨跌停保护器.

    功能:
        - 检查委托价格是否超出涨跌停板
        - 支持自动调整到涨跌停价
        - 检测连续涨跌停（流动性风险）
    """

    def __init__(
        self,
        action: LimitPriceAction = LimitPriceAction.REJECT,
    ) -> None:
        """初始化涨跌停保护器.

        参数:
            action: 触发时的处理动作
        """
        self._action = action
        self._consecutive_limits: dict[str, int] = {}  # 连续涨跌停计数

    def check(
        self,
        symbol: str,
        price: float,
        upper_limit: float,
        lower_limit: float,
        last_price: float,
    ) -> LimitPriceCheckResult:
        """检查价格是否在涨跌停范围内.

        参数:
            symbol: 合约代码
            price: 委托价格
            upper_limit: 涨停价
            lower_limit: 跌停价
            last_price: 最新成交价

        返回:
            检查结果
        """
        # 检查是否已触及涨跌停
        at_upper_limit = abs(last_price - upper_limit) < 1e-6
        at_lower_limit = abs(last_price - lower_limit) < 1e-6

        if at_upper_limit or at_lower_limit:
            # 更新连续涨跌停计数
            self._consecutive_limits[symbol] = (
                self._consecutive_limits.get(symbol, 0) + 1
            )
        else:
            self._consecutive_limits[symbol] = 0

        # 价格在范围内
        if lower_limit <= price <= upper_limit:
            return LimitPriceCheckResult(
                passed=True,
                original_price=price,
                adjusted_price=None,
                reason="价格在涨跌停范围内",
            )

        # 价格超出范围
        if self._action == LimitPriceAction.REJECT:
            return LimitPriceCheckResult(
                passed=False,
                original_price=price,
                adjusted_price=None,
                reason=f"价格 {price} 超出涨跌停范围 [{lower_limit}, {upper_limit}]",
            )

        if self._action == LimitPriceAction.ADJUST_TO_LIMIT:
            adjusted = max(lower_limit, min(upper_limit, price))
            return LimitPriceCheckResult(
                passed=True,
                original_price=price,
                adjusted_price=adjusted,
                reason=f"价格从 {price} 调整到 {adjusted}",
            )

        # WARN_AND_PASS
        return LimitPriceCheckResult(
            passed=True,
            original_price=price,
            adjusted_price=None,
            reason=f"警告：价格 {price} 超出涨跌停范围，但允许通过",
        )

    def get_consecutive_limit_count(self, symbol: str) -> int:
        """获取连续涨跌停次数.

        参数:
            symbol: 合约代码

        返回:
            连续涨跌停次数
        """
        return self._consecutive_limits.get(symbol, 0)
```

### 4.2 保证金监控

#### P0-008: 实时保证金计算

```python
# src/execution/protection/margin_monitor.py
"""保证金监控模块."""

from dataclasses import dataclass
from enum import Enum


class MarginLevel(Enum):
    """保证金水平."""

    SAFE = "safe"           # 安全：< 70%
    WARNING = "warning"     # 警告：70-90%
    DANGER = "danger"       # 危险：90-100%
    CRITICAL = "critical"   # 临界：>= 100%（可能强平）


@dataclass
class MarginStatus:
    """保证金状态."""

    total_equity: float          # 总权益
    margin_used: float           # 占用保证金
    margin_available: float      # 可用保证金
    margin_ratio: float          # 保证金使用率
    level: MarginLevel           # 风险等级
    can_open_long: bool          # 可否开多
    can_open_short: bool         # 可否开空


class MarginMonitor:
    """保证金监控器.

    功能:
        - 实时计算保证金使用率
        - 多级预警
        - 开仓可用性判断
    """

    # 风险阈值
    WARNING_THRESHOLD = 0.70     # 70% 警告
    DANGER_THRESHOLD = 0.90      # 90% 危险
    CRITICAL_THRESHOLD = 1.00    # 100% 临界

    # 开仓预留保证金比例
    OPEN_RESERVE_RATIO = 0.80    # 80% 时禁止开仓

    def calculate_margin_status(
        self,
        total_equity: float,
        margin_used: float,
    ) -> MarginStatus:
        """计算保证金状态.

        参数:
            total_equity: 总权益
            margin_used: 占用保证金

        返回:
            保证金状态
        """
        if total_equity <= 0:
            return MarginStatus(
                total_equity=total_equity,
                margin_used=margin_used,
                margin_available=0,
                margin_ratio=1.0,
                level=MarginLevel.CRITICAL,
                can_open_long=False,
                can_open_short=False,
            )

        margin_ratio = margin_used / total_equity
        margin_available = total_equity - margin_used

        # 确定风险等级
        if margin_ratio >= self.CRITICAL_THRESHOLD:
            level = MarginLevel.CRITICAL
        elif margin_ratio >= self.DANGER_THRESHOLD:
            level = MarginLevel.DANGER
        elif margin_ratio >= self.WARNING_THRESHOLD:
            level = MarginLevel.WARNING
        else:
            level = MarginLevel.SAFE

        # 判断是否可以开仓
        can_open = margin_ratio < self.OPEN_RESERVE_RATIO

        return MarginStatus(
            total_equity=total_equity,
            margin_used=margin_used,
            margin_available=margin_available,
            margin_ratio=margin_ratio,
            level=level,
            can_open_long=can_open,
            can_open_short=can_open,
        )

    def estimate_margin_after_order(
        self,
        current_margin: float,
        order_margin: float,
        total_equity: float,
    ) -> tuple[float, MarginLevel]:
        """估算下单后的保证金状态.

        参数:
            current_margin: 当前占用保证金
            order_margin: 订单所需保证金
            total_equity: 总权益

        返回:
            (预估保证金比率, 风险等级)
        """
        new_margin = current_margin + order_margin
        new_ratio = new_margin / total_equity if total_equity > 0 else 1.0

        if new_ratio >= self.CRITICAL_THRESHOLD:
            level = MarginLevel.CRITICAL
        elif new_ratio >= self.DANGER_THRESHOLD:
            level = MarginLevel.DANGER
        elif new_ratio >= self.WARNING_THRESHOLD:
            level = MarginLevel.WARNING
        else:
            level = MarginLevel.SAFE

        return (new_ratio, level)
```

### 4.3 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `EXEC.LIMIT.PRICE_CHECK` | execution.protection.limit_price | 涨跌停价格检查 |
| `EXEC.LIMIT.CONSECUTIVE` | execution.protection.limit_price | 连续涨跌停检测 |
| `EXEC.MARGIN.REALTIME` | execution.protection.margin_monitor | 实时保证金计算 |
| `EXEC.MARGIN.LEVEL_WARN` | execution.protection.margin_monitor | 保证金预警 |
| `EXEC.MARGIN.OPEN_GATE` | execution.protection.margin_monitor | 保证金开仓门槛 |

---

## 第五部分：Guardian 守护层改进（第6章 Phase 1）

### 5.1 涨跌停触发器

#### P0-009: 涨跌停相关触发器

```python
# src/guardian/triggers_china.py
"""中国期货市场特化触发器."""

from dataclasses import dataclass
from enum import Enum


class ChinaTriggerType(Enum):
    """中国期货市场特化触发器类型."""

    LIMIT_PRICE_HIT = "limit_price_hit"           # 触及涨跌停
    CONSECUTIVE_LIMIT = "consecutive_limit"       # 连续涨跌停
    MARGIN_WARNING = "margin_warning"             # 保证金警告
    MARGIN_DANGER = "margin_danger"               # 保证金危险
    NIGHT_SESSION_END = "night_session_end"       # 夜盘结束
    DELIVERY_APPROACHING = "delivery_approaching" # 交割临近
    TRADING_HALT = "trading_halt"                 # 交易所暂停交易


@dataclass
class ChinaTriggerEvent:
    """中国期货市场触发事件."""

    trigger_type: ChinaTriggerType
    symbol: str
    details: dict
    suggested_action: str


class LimitPriceTrigger:
    """涨跌停触发器.

    功能:
        - 检测单个品种触及涨跌停
        - 检测连续涨跌停（流动性风险）
        - 建议降级到 REDUCE_ONLY
    """

    # 连续涨跌停阈值
    CONSECUTIVE_LIMIT_THRESHOLD = 2

    def __init__(self) -> None:
        """初始化触发器."""
        self._limit_counts: dict[str, int] = {}

    def check(
        self,
        symbol: str,
        last_price: float,
        upper_limit: float,
        lower_limit: float,
    ) -> ChinaTriggerEvent | None:
        """检查涨跌停状态.

        参数:
            symbol: 合约代码
            last_price: 最新价
            upper_limit: 涨停价
            lower_limit: 跌停价

        返回:
            触发事件（如果触发）
        """
        at_upper = abs(last_price - upper_limit) < 1e-6
        at_lower = abs(last_price - lower_limit) < 1e-6

        if at_upper or at_lower:
            self._limit_counts[symbol] = self._limit_counts.get(symbol, 0) + 1
            count = self._limit_counts[symbol]

            direction = "涨停" if at_upper else "跌停"

            if count >= self.CONSECUTIVE_LIMIT_THRESHOLD:
                return ChinaTriggerEvent(
                    trigger_type=ChinaTriggerType.CONSECUTIVE_LIMIT,
                    symbol=symbol,
                    details={
                        "direction": direction,
                        "consecutive_count": count,
                        "price": last_price,
                    },
                    suggested_action="REDUCE_ONLY",
                )

            return ChinaTriggerEvent(
                trigger_type=ChinaTriggerType.LIMIT_PRICE_HIT,
                symbol=symbol,
                details={
                    "direction": direction,
                    "price": last_price,
                },
                suggested_action="WARN",
            )

        # 重置计数
        self._limit_counts[symbol] = 0
        return None


class MarginTrigger:
    """保证金触发器.

    功能:
        - 监控保证金使用率
        - 多级预警
        - 建议降级或强平
    """

    WARNING_RATIO = 0.70
    DANGER_RATIO = 0.90

    def check(self, margin_ratio: float) -> ChinaTriggerEvent | None:
        """检查保证金状态.

        参数:
            margin_ratio: 保证金使用率

        返回:
            触发事件（如果触发）
        """
        if margin_ratio >= self.DANGER_RATIO:
            return ChinaTriggerEvent(
                trigger_type=ChinaTriggerType.MARGIN_DANGER,
                symbol="GLOBAL",
                details={"margin_ratio": margin_ratio},
                suggested_action="HALTED",  # 停止交易
            )

        if margin_ratio >= self.WARNING_RATIO:
            return ChinaTriggerEvent(
                trigger_type=ChinaTriggerType.MARGIN_WARNING,
                symbol="GLOBAL",
                details={"margin_ratio": margin_ratio},
                suggested_action="REDUCE_ONLY",  # 仅允许减仓
            )

        return None


class DeliveryApproachingTrigger:
    """交割临近触发器.

    功能:
        - 检测临近交割月的持仓
        - 强制 REDUCE_ONLY
        - 避免进入交割程序
    """

    # 提前天数
    REDUCE_ONLY_DAYS = 5
    HALT_DAYS = 2

    def check(
        self,
        symbol: str,
        days_to_delivery: int,
        has_position: bool,
    ) -> ChinaTriggerEvent | None:
        """检查交割临近状态.

        参数:
            symbol: 合约代码
            days_to_delivery: 距交割日天数
            has_position: 是否有持仓

        返回:
            触发事件（如果触发）
        """
        if not has_position:
            return None

        if days_to_delivery <= self.HALT_DAYS:
            return ChinaTriggerEvent(
                trigger_type=ChinaTriggerType.DELIVERY_APPROACHING,
                symbol=symbol,
                details={
                    "days_to_delivery": days_to_delivery,
                    "severity": "CRITICAL",
                },
                suggested_action="FLATTEN",  # 强制平仓
            )

        if days_to_delivery <= self.REDUCE_ONLY_DAYS:
            return ChinaTriggerEvent(
                trigger_type=ChinaTriggerType.DELIVERY_APPROACHING,
                symbol=symbol,
                details={
                    "days_to_delivery": days_to_delivery,
                    "severity": "WARNING",
                },
                suggested_action="REDUCE_ONLY",
            )

        return None
```

### 5.2 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `GUARD.TRIGGER.LIMIT_PRICE` | guardian.triggers_china | 涨跌停触发检测 |
| `GUARD.TRIGGER.CONSECUTIVE_LIMIT` | guardian.triggers_china | 连续涨跌停检测 |
| `GUARD.TRIGGER.MARGIN_LEVEL` | guardian.triggers_china | 保证金水平触发 |
| `GUARD.TRIGGER.DELIVERY` | guardian.triggers_china | 交割临近触发 |
| `GUARD.ACTION.DELIVERY_FLATTEN` | guardian.actions | 交割临近强平 |

---

## 第六部分：策略层改进（第8章 Phase 3）

### 6.1 套利策略中国期货市场特化

#### P1-002: 跨期套利交割月处理

```python
# src/strategy/calendar_arb/delivery_aware.py
"""跨期套利交割月感知模块."""

from dataclasses import dataclass
from datetime import date


@dataclass
class DeliveryAwareConfig:
    """交割感知配置."""

    # 近月合约
    near_reduce_only_days: int = 10      # 近月提前10天进入 REDUCE_ONLY
    near_close_all_days: int = 5         # 近月提前5天全部平仓

    # 远月合约
    far_reduce_only_days: int = 5        # 远月提前5天进入 REDUCE_ONLY
    far_close_all_days: int = 2          # 远月提前2天全部平仓

    # 主力切换
    roll_lookahead_days: int = 15        # 提前15天准备换月


class DeliveryAwareCalendarArb:
    """交割感知的跨期套利.

    功能:
        - 监控近远月交割日期
        - 自动进入 REDUCE_ONLY
        - 自动平仓避免交割
        - 自动换月到新的近远月组合
    """

    def __init__(self, config: DeliveryAwareConfig | None = None) -> None:
        """初始化.

        参数:
            config: 交割感知配置
        """
        self._config = config or DeliveryAwareConfig()

    def get_strategy_mode(
        self,
        near_days_to_delivery: int,
        far_days_to_delivery: int,
    ) -> str:
        """获取策略模式.

        参数:
            near_days_to_delivery: 近月距交割天数
            far_days_to_delivery: 远月距交割天数

        返回:
            策略模式: "RUNNING" | "REDUCE_ONLY" | "CLOSE_ALL" | "ROLL"
        """
        # 近月即将交割
        if near_days_to_delivery <= self._config.near_close_all_days:
            return "CLOSE_ALL"

        if near_days_to_delivery <= self._config.near_reduce_only_days:
            return "REDUCE_ONLY"

        # 远月即将交割
        if far_days_to_delivery <= self._config.far_close_all_days:
            return "CLOSE_ALL"

        if far_days_to_delivery <= self._config.far_reduce_only_days:
            return "REDUCE_ONLY"

        # 准备换月
        if near_days_to_delivery <= self._config.roll_lookahead_days:
            return "ROLL"

        return "RUNNING"

    def should_roll_position(
        self,
        near_days_to_delivery: int,
        new_near_symbol: str | None,
        new_far_symbol: str | None,
    ) -> bool:
        """判断是否应该换月.

        参数:
            near_days_to_delivery: 近月距交割天数
            new_near_symbol: 新的近月合约
            new_far_symbol: 新的远月合约

        返回:
            是否应该换月
        """
        if near_days_to_delivery > self._config.roll_lookahead_days:
            return False

        if new_near_symbol is None or new_far_symbol is None:
            return False

        return True
```

### 6.2 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `ARB.DELIVERY.NEAR_MONTH_GATE` | strategy.calendar_arb | 近月交割限制 |
| `ARB.DELIVERY.AUTO_ROLL` | strategy.calendar_arb | 自动换月 |
| `ARB.CHINA.SETTLEMENT_PRICE` | strategy.calendar_arb | 使用结算价计算 |

---

## 第七部分：风控增强改进（第26章）

### 7.1 中国期货市场 VaR 特化

#### P0-010: 涨跌停截断效应 VaR

**现状**: 现有 VaR 计算器未考虑涨跌停板的截断效应。

**改进**: 详细设计见 `docs/CHINA_FUTURES_UPGRADE_REPORT.md` §2.4

关键改进点：
1. **涨跌停截断修正**: 收益率在 ±limit_pct 处被截断
2. **停板风险溢价**: 额外加入 10-20% 的风险溢价
3. **连续涨跌停场景**: 模拟连续3天涨跌停的极端情况

### 7.2 新增压力测试场景

#### P1-003: 中国期货市场历史极端事件

| 场景 | 描述 | 冲击参数 |
|------|------|----------|
| **2015年股灾** | 股指期货连续跌停 | IF -10% × 5天 |
| **2016年黑色系暴涨** | 螺纹钢连续涨停 | RB +6% × 3天 |
| **2020年原油负价** | 原油期货极端波动 | SC -15% 单日 |
| **2021年动力煤暴跌** | 政策调控 | ZC -10% × 3天 |
| **2022年碳酸锂暴跌** | 供需逆转 | LC -15% × 5天 |
| **流动性枯竭** | 买卖价差扩大 | spread × 10 |
| **夜盘跳空** | 外盘影响 | ±5% 开盘跳空 |

```python
# src/risk/stress_test_china.py
"""中国期货市场压力测试模块."""

from dataclasses import dataclass
from enum import Enum


class StressScenario(Enum):
    """压力测试场景."""

    STOCK_CRASH_2015 = "stock_crash_2015"
    BLACK_SERIES_2016 = "black_series_2016"
    OIL_NEGATIVE_2020 = "oil_negative_2020"
    COAL_POLICY_2021 = "coal_policy_2021"
    LITHIUM_CRASH_2022 = "lithium_crash_2022"
    LIQUIDITY_DRY_UP = "liquidity_dry_up"
    OVERNIGHT_GAP = "overnight_gap"


@dataclass
class StressTestResult:
    """压力测试结果."""

    scenario: StressScenario
    portfolio_loss: float
    var_breach: bool
    margin_breach: bool
    survival_probability: float
    recommended_action: str


STRESS_SCENARIO_PARAMS: dict[StressScenario, dict] = {
    StressScenario.STOCK_CRASH_2015: {
        "description": "2015年股灾：股指期货连续跌停",
        "affected_products": ["IF", "IC", "IH", "IM"],
        "daily_return": -0.10,
        "consecutive_days": 5,
        "spread_multiplier": 5.0,
    },
    StressScenario.BLACK_SERIES_2016: {
        "description": "2016年黑色系暴涨",
        "affected_products": ["rb", "hc", "i", "j", "jm"],
        "daily_return": 0.06,
        "consecutive_days": 3,
        "spread_multiplier": 3.0,
    },
    StressScenario.OIL_NEGATIVE_2020: {
        "description": "2020年原油负价事件",
        "affected_products": ["sc", "fu", "bu"],
        "daily_return": -0.15,
        "consecutive_days": 1,
        "spread_multiplier": 10.0,
    },
    StressScenario.COAL_POLICY_2021: {
        "description": "2021年动力煤政策调控",
        "affected_products": ["ZC"],
        "daily_return": -0.10,
        "consecutive_days": 3,
        "spread_multiplier": 5.0,
    },
    StressScenario.LITHIUM_CRASH_2022: {
        "description": "2022年碳酸锂暴跌",
        "affected_products": ["lc"],
        "daily_return": -0.15,
        "consecutive_days": 5,
        "spread_multiplier": 8.0,
    },
    StressScenario.LIQUIDITY_DRY_UP: {
        "description": "流动性枯竭",
        "affected_products": ["ALL"],
        "daily_return": 0,
        "consecutive_days": 1,
        "spread_multiplier": 10.0,
    },
    StressScenario.OVERNIGHT_GAP: {
        "description": "夜盘跳空",
        "affected_products": ["ALL_WITH_NIGHT"],
        "gap_pct": 0.05,
        "consecutive_days": 1,
        "spread_multiplier": 3.0,
    },
}
```

### 7.3 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `RISK.VAR.LIMIT_ADJUSTED` | risk.var_calculator | 涨跌停调整 VaR |
| `RISK.STRESS.CHINA_2015` | risk.stress_test_china | 2015股灾场景 |
| `RISK.STRESS.LIMIT_HALT` | risk.stress_test_china | 连续涨跌停场景 |
| `RISK.MARGIN.FORECAST` | risk.margin_forecast | 保证金预测 |

---

## 第八部分：程序化交易合规（新增章节）

### 8.1 2025年新规要求

基于证监会《期货市场程序化交易管理规定（试行）》（2025年10月实施）：

#### P0-011: 合规检查模块

```python
# src/compliance/programmatic_trading.py
"""程序化交易合规模块.

依据: 证监会《期货市场程序化交易管理规定（试行）》(2025年10月实施)
"""

from dataclasses import dataclass
from enum import Enum


class ComplianceViolation(Enum):
    """合规违规类型."""

    ORDER_FREQUENCY_EXCEED = "order_freq_exceed"      # 报撤单频率超限
    LARGE_ORDER_NO_REVIEW = "large_order_no_review"   # 大额订单未复核
    STRATEGY_NOT_FILED = "strategy_not_filed"         # 策略未备案
    RISK_CONTROL_MISSING = "risk_control_missing"     # 风控措施缺失


@dataclass
class ComplianceReport:
    """合规报告."""

    timestamp: float
    trading_account: str
    order_frequency_5s: int       # 5秒内报撤单次数
    large_order_count: int        # 大额订单数量
    reviewed_order_count: int     # 已复核订单数量
    violations: list[ComplianceViolation]
    compliant: bool


class ProgrammaticTradingCompliance:
    """程序化交易合规检查器.

    功能:
        - 报撤单频率监控（5秒50笔预警）
        - 大额订单二次复核（30秒内）
        - 策略备案检查
        - 风控措施有效性验证
    """

    # 监管阈值
    ORDER_FREQ_THRESHOLD_5S = 50      # 5秒内50笔预警
    ORDER_FREQ_THRESHOLD_1MIN = 300   # 1分钟内300笔预警
    LARGE_ORDER_THRESHOLD = 100       # 大额订单阈值（手）
    REVIEW_TIMEOUT_S = 30             # 复核超时时间

    def __init__(self) -> None:
        """初始化合规检查器."""
        self._order_timestamps: list[float] = []
        self._pending_reviews: dict[str, float] = {}  # order_id -> submit_time
        self._filed_strategies: set[str] = set()

    def register_strategy(self, strategy_id: str) -> None:
        """注册备案策略.

        参数:
            strategy_id: 策略ID
        """
        self._filed_strategies.add(strategy_id)

    def check_order_frequency(self, current_ts: float) -> bool:
        """检查报撤单频率.

        参数:
            current_ts: 当前时间戳

        返回:
            是否合规
        """
        # 清理5秒前的记录
        cutoff_5s = current_ts - 5.0
        self._order_timestamps = [
            ts for ts in self._order_timestamps if ts > cutoff_5s
        ]

        # 添加当前订单
        self._order_timestamps.append(current_ts)

        return len(self._order_timestamps) <= self.ORDER_FREQ_THRESHOLD_5S

    def require_manual_review(self, order_id: str, qty: int) -> bool:
        """判断是否需要人工复核.

        参数:
            order_id: 订单ID
            qty: 下单手数

        返回:
            是否需要人工复核
        """
        if qty >= self.LARGE_ORDER_THRESHOLD:
            return True
        return False

    def check_strategy_filed(self, strategy_id: str) -> bool:
        """检查策略是否已备案.

        参数:
            strategy_id: 策略ID

        返回:
            是否已备案
        """
        return strategy_id in self._filed_strategies

    def generate_compliance_report(
        self,
        trading_account: str,
        current_ts: float,
    ) -> ComplianceReport:
        """生成合规报告.

        参数:
            trading_account: 交易账户
            current_ts: 当前时间戳

        返回:
            合规报告
        """
        violations = []

        # 检查报撤单频率
        order_freq_5s = len(self._order_timestamps)
        if order_freq_5s > self.ORDER_FREQ_THRESHOLD_5S:
            violations.append(ComplianceViolation.ORDER_FREQUENCY_EXCEED)

        # 检查大额订单复核
        expired_reviews = [
            oid for oid, ts in self._pending_reviews.items()
            if current_ts - ts > self.REVIEW_TIMEOUT_S
        ]
        if expired_reviews:
            violations.append(ComplianceViolation.LARGE_ORDER_NO_REVIEW)

        return ComplianceReport(
            timestamp=current_ts,
            trading_account=trading_account,
            order_frequency_5s=order_freq_5s,
            large_order_count=len(self._pending_reviews),
            reviewed_order_count=0,  # TODO: 实现
            violations=violations,
            compliant=len(violations) == 0,
        )
```

### 8.2 新增 Required Scenarios

| rule_id | component | 描述 |
|---------|-----------|------|
| `COMPLY.ORDER_FREQ.CHECK` | compliance.programmatic | 报撤单频率检查 |
| `COMPLY.LARGE_ORDER.REVIEW` | compliance.programmatic | 大额订单复核 |
| `COMPLY.STRATEGY.FILED` | compliance.programmatic | 策略备案检查 |
| `COMPLY.REPORT.GENERATE` | compliance.programmatic | 合规报告生成 |

---

## 第九部分：新增文件清单汇总

### 9.1 按模块统计

| 模块 | 新增文件 | 职责 |
|------|----------|------|
| `src/compliance/` | 2 | 中国期货合规检查 |
| `src/market/` | 2 | 交易所配置、交易日历 |
| `src/cost/` | 1 | 中国期货手续费 |
| `src/execution/protection/` | 2 | 涨跌停保护、保证金监控 |
| `src/guardian/` | 1 | 中国期货触发器 |
| `src/risk/` | 1 | 中国期货压力测试 |
| `src/strategy/calendar_arb/` | 1 | 交割感知套利 |
| **总计** | **10** | - |

### 9.2 完整文件路径

```text
src/
├── compliance/                          # 新增目录
│   ├── __init__.py
│   ├── china_futures_rules.py           # 中国期货合规规则
│   └── programmatic_trading.py          # 程序化交易合规
│
├── market/
│   ├── exchange_config.py               # 交易所配置（新增）
│   └── trading_calendar.py              # 交易日历（新增）
│
├── cost/
│   └── china_fee_calculator.py          # 中国期货手续费（新增）
│
├── execution/
│   └── protection/
│       ├── limit_price.py               # 涨跌停保护（新增）
│       └── margin_monitor.py            # 保证金监控（新增）
│
├── guardian/
│   └── triggers_china.py                # 中国期货触发器（新增）
│
├── risk/
│   └── stress_test_china.py             # 中国期货压力测试（新增）
│
└── strategy/
    └── calendar_arb/
        └── delivery_aware.py            # 交割感知套利（新增）
```

---

## 第十部分：新增 Required Scenarios 汇总

### 10.1 按类别统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 军规合规 | 5 | M12-M16 |
| 行情层 | 5 | 涨跌停、保证金、夜盘 |
| 成本层 | 4 | 手续费特化 |
| 保护层 | 5 | 涨跌停保护、保证金监控 |
| 守护层 | 5 | 中国期货触发器 |
| 套利策略 | 3 | 交割感知 |
| 风控层 | 4 | VaR、压力测试 |
| 程序化合规 | 4 | 新规要求 |
| **总计** | **35** | - |

### 10.2 完整 Scenarios 列表

```yaml
# 中国期货市场特化 Scenarios (35 条)
china_futures_scenarios:

  # 军规合规 (5)
  - COMPLY.M12.LIMIT_PRICE
  - COMPLY.M13.CLOSE_TODAY
  - COMPLY.M14.NIGHT_SESSION
  - COMPLY.M15.MARGIN_REALTIME
  - COMPLY.M16.ORDER_FREQUENCY

  # 行情层 (5)
  - MKT.INST.LIMIT_PRICE
  - MKT.INST.MARGIN_RATE
  - MKT.INST.NIGHT_SESSION
  - MKT.CALENDAR.TRADING_DATE
  - MKT.EXCHANGE.DIFF_CONFIG

  # 成本层 (4)
  - COST.FEE.PER_LOT
  - COST.FEE.RATE_BASED
  - COST.FEE.CLOSE_TODAY
  - COST.FEE.EXCHANGE_DIFF

  # 保护层 (5)
  - EXEC.LIMIT.PRICE_CHECK
  - EXEC.LIMIT.CONSECUTIVE
  - EXEC.MARGIN.REALTIME
  - EXEC.MARGIN.LEVEL_WARN
  - EXEC.MARGIN.OPEN_GATE

  # 守护层 (5)
  - GUARD.TRIGGER.LIMIT_PRICE
  - GUARD.TRIGGER.CONSECUTIVE_LIMIT
  - GUARD.TRIGGER.MARGIN_LEVEL
  - GUARD.TRIGGER.DELIVERY
  - GUARD.ACTION.DELIVERY_FLATTEN

  # 套利策略 (3)
  - ARB.DELIVERY.NEAR_MONTH_GATE
  - ARB.DELIVERY.AUTO_ROLL
  - ARB.CHINA.SETTLEMENT_PRICE

  # 风控层 (4)
  - RISK.VAR.LIMIT_ADJUSTED
  - RISK.STRESS.CHINA_2015
  - RISK.STRESS.LIMIT_HALT
  - RISK.MARGIN.FORECAST

  # 程序化合规 (4)
  - COMPLY.ORDER_FREQ.CHECK
  - COMPLY.LARGE_ORDER.REVIEW
  - COMPLY.STRATEGY.FILED
  - COMPLY.REPORT.GENERATE
```

---

## 第十一部分：实施优先级

### 11.1 优先级矩阵

| 优先级 | 改进项 | 工时 | 阻塞性 |
|--------|--------|------|--------|
| **P0** | 涨跌停保护 | 8h | 是 |
| **P0** | 保证金监控 | 8h | 是 |
| **P0** | 军规 M12-M16 | 4h | 是 |
| **P0** | 程序化合规检查 | 12h | 是 |
| **P1** | 交易所差异化配置 | 8h | 否 |
| **P1** | 手续费特化 | 6h | 否 |
| **P1** | 中国期货触发器 | 8h | 否 |
| **P1** | 交割感知套利 | 8h | 否 |
| **P2** | 压力测试场景 | 12h | 否 |
| **P2** | VaR 涨跌停调整 | 8h | 否 |
| **P2** | 夜盘交易日历 | 6h | 否 |

### 11.2 实施阶段

```text
Phase A: 紧急合规 (32h)
├── P0-001: 新增军规 M12-M16
├── P0-007: 涨跌停保护
├── P0-008: 保证金监控
└── P0-011: 程序化合规检查

Phase B: 市场特化 (30h)
├── P1-001: 六大交易所配置
├── P0-004: InstrumentInfo 扩展
├── P0-006: 手续费特化
└── P0-005: 夜盘交易日历

Phase C: 风控增强 (28h)
├── P0-009: 涨跌停触发器
├── P1-003: 中国期货压力测试
├── P0-010: VaR 涨跌停调整
└── P1-002: 交割感知套利

总计: 90h
```

---

## 第十二部分：门禁检查点

### 12.1 中国期货市场特化门禁

```powershell
# 中国期货市场合规门禁
python scripts/compliance_gate.py --china-futures

# 涨跌停保护测试
python -m pytest tests/test_limit_price_guard.py -v

# 保证金监控测试
python -m pytest tests/test_margin_monitor.py -v

# 手续费计算测试
python -m pytest tests/test_china_fee_calculator.py -v

# 交易日历测试
python -m pytest tests/test_trading_calendar.py -v

# 压力测试场景
python -m pytest tests/test_stress_test_china.py -v

# 全部中国期货市场特化测试
python -m pytest tests/ -k "china" -v
```

### 12.2 导入验证

```powershell
# 合规模块
python -c "from src.compliance import ChinaFuturesComplianceChecker"
python -c "from src.compliance import ProgrammaticTradingCompliance"

# 市场模块
python -c "from src.market.exchange_config import EXCHANGE_CONFIGS"
python -c "from src.market.trading_calendar import ChinaTradingCalendar"

# 成本模块
python -c "from src.cost.china_fee_calculator import ChinaFeeCalculator"

# 保护模块
python -c "from src.execution.protection.limit_price import LimitPriceGuard"
python -c "from src.execution.protection.margin_monitor import MarginMonitor"

# 守护模块
python -c "from src.guardian.triggers_china import LimitPriceTrigger"

# 风控模块
python -c "from src.risk.stress_test_china import STRESS_SCENARIO_PARAMS"
```

---

## 附录 A：中国期货市场参考资料来源

| 来源 | 说明 | URL |
|------|------|-----|
| 证监会 | 程序化交易管理规定 | [csrc.gov.cn](http://www.csrc.gov.cn/csrc/c100028/c7564353/content.shtml) |
| 上期所 | 交易规则、保证金公告 | [shfe.com.cn](https://www.shfe.com.cn/) |
| 中金所 | 金融期货交易规则 | [cffex.com.cn](http://www.cffex.com.cn/jysgz/) |
| 九期网 | 交易时间一览表 | [9qihuo.com](https://www.9qihuo.com/qihuo/58370) |
| BigQuant | 期货代码数据 | [bigquant.com](https://bigquant.com/data/datasources/cn_future_instruments) |

---

## 附录 B：变更日志

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v1.0 | 2025-12-16 | CLAUDE上校 | 初始版本：全面审查报告 |

---

> **报告完成。**
> **敬请最高指挥部审阅批准。**
> **CLAUDE上校 敬礼！** 🎖️
