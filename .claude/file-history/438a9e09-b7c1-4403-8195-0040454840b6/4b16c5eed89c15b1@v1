# V3PRO+ 中国期货市场军规级改进报告

> **版本**: v1.0
> **日期**: 2025-12-16
> **作者**: CLAUDE上校 (军规级别国家伟大工程的总工程师)
> **状态**: 分析完成，待实施

---

## 目录

1. [执行摘要](#1-执行摘要)
2. [VaR 模块深度分析与改进](#2-var-模块深度分析与改进)
3. [中国期货市场特性分析](#3-中国期货市场特性分析)
4. [全项目模块改进清单](#4-全项目模块改进清单)
5. [Required Scenarios 新增](#5-required-scenarios-新增)
6. [实施优先级与工时估计](#6-实施优先级与工时估计)
7. [代码实现规范](#7-代码实现规范)

---

## 1. 执行摘要

### 1.1 现状评估

| 模块 | 现状 | 问题 | 改进优先级 |
|------|------|------|------------|
| VaR Calculator | 基础三法 (历史/参数/MC) | 未考虑尾部风险、涨跌停截断 | **P0** |
| Risk Manager | 回撤控制为主 | 缺少中国特色风控规则 | **P0** |
| Cost Estimator | 基础手续费模型 | 未考虑交易所差异化费率 | **P1** |
| Instrument Cache | 基础字段 | 缺少涨跌停、保证金率等 | **P1** |
| Guardian | 状态机+触发器 | 缺少交易时段感知 | **P2** |

### 1.2 改进目标

1. **VaR 模块**: 引入极值理论 (EVT) + 半参数模型，精准捕捉尾部风险
2. **风控模块**: 适配中国期货市场涨跌停、保证金、交易时段规则
3. **成本模块**: 支持各交易所差异化费率结构
4. **全局**: 所有注释使用中文，符合最高指示要求

---

## 2. VaR 模块深度分析与改进

### 2.1 现有实现分析

**文件位置**: `src/risk/var_calculator.py` (362 行)

**现有方法**:
| 方法 | 原理 | 缺陷 |
|------|------|------|
| `historical_var()` | 经验分位数 | 样本依赖，尾部不稳定 |
| `parametric_var()` | 正态假设 | 低估尾部风险 (中国期货肥尾明显) |
| `monte_carlo_var()` | 正态模拟 | 假设相同，无法捕捉跳跃 |

**核心问题**:
```python
# 现有代码：var_calculator.py:141-145
# 问题：假设收益率服从正态分布
z = self._norm_ppf(confidence)
var = -mean + z * std
# 正态分布的 z_{0.99} = 2.326
# 但中国期货市场收益率 kurtosis > 3，尾部更肥
```

### 2.2 极值理论 (EVT) 增强方案

#### 2.2.1 理论基础

**POT (Peaks Over Threshold) 方法**:
- 对超过阈值 u 的极端损失建模
- 超额分布服从广义帕累托分布 (GPD)

**GPD 分布函数**:
```
G(x; ξ, β) = 1 - (1 + ξx/β)^(-1/ξ)  当 ξ ≠ 0
           = 1 - exp(-x/β)          当 ξ = 0
```

其中:
- ξ (xi): 形状参数，决定尾部厚度
- β (beta): 尺度参数
- 当 ξ > 0: 重尾分布 (适合中国期货)
- 当 ξ = 0: 指数尾
- 当 ξ < 0: 有界尾

#### 2.2.2 EVT-VaR 计算公式

```
VaR_α = u + (β/ξ) * [(n/N_u * (1-α))^(-ξ) - 1]
ES_α  = (VaR_α + β - ξu) / (1 - ξ)
```

其中:
- u: 阈值 (建议取 90% 或 95% 分位数)
- n: 总样本数
- N_u: 超过阈值的样本数

#### 2.2.3 新增代码设计

```python
# src/risk/var_calculator.py 新增方法

def evt_var(
    self,
    returns: list[float],
    confidence: float | None = None,
    threshold_quantile: float = 0.95,
) -> VaRResult:
    """基于极值理论 (EVT) 的 VaR 计算.

    使用 POT (Peaks Over Threshold) 方法，对尾部损失建模。
    适用于中国期货市场的肥尾分布特征。

    参数:
        returns: 历史收益率序列
        confidence: 置信水平 (默认 0.99)
        threshold_quantile: 阈值分位数 (默认 0.95)

    返回:
        VaR 结果，包含 GPD 参数
    """
    confidence = confidence or 0.99

    # 1. 计算阈值
    sorted_losses = sorted([-r for r in returns])  # 转换为损失
    n = len(sorted_losses)
    threshold_idx = int(threshold_quantile * n)
    u = sorted_losses[threshold_idx]

    # 2. 提取超额损失
    excesses = [x - u for x in sorted_losses if x > u]
    n_u = len(excesses)

    if n_u < 10:
        # 样本不足，回退到历史法
        return self.historical_var(returns, confidence)

    # 3. 估计 GPD 参数 (矩估计法)
    xi, beta = self._estimate_gpd_params(excesses)

    # 4. 计算 EVT-VaR
    p = 1 - confidence
    var = u + (beta / xi) * ((n / n_u * p) ** (-xi) - 1)

    # 5. 计算 EVT-ES
    if xi < 1:
        es = (var + beta - xi * u) / (1 - xi)
    else:
        es = float('inf')  # 期望不存在

    return VaRResult(
        var=var,
        confidence=confidence,
        method="evt_pot",
        expected_shortfall=es,
        sample_size=n,
        metadata={
            "threshold": u,
            "excesses_count": n_u,
            "xi": xi,
            "beta": beta,
            "threshold_quantile": threshold_quantile,
        },
    )

def _estimate_gpd_params(self, excesses: list[float]) -> tuple[float, float]:
    """估计 GPD 参数 (矩估计法).

    使用 Hill 估计器估计形状参数 xi。

    参数:
        excesses: 超额损失列表

    返回:
        (xi, beta) GPD 参数
    """
    n = len(excesses)
    if n < 2:
        return 0.0, 1.0

    # 矩估计
    mean_excess = sum(excesses) / n
    var_excess = sum((x - mean_excess) ** 2 for x in excesses) / (n - 1)

    # 避免除零
    if var_excess <= 0:
        return 0.0, mean_excess

    # GPD 矩估计
    # E[X] = beta / (1 - xi)
    # Var[X] = beta^2 / ((1 - xi)^2 * (1 - 2*xi))

    # 使用比率估计 xi
    ratio = var_excess / (mean_excess ** 2)
    xi = 0.5 * (1 - 1 / ratio) if ratio > 1 else 0.1

    # 限制 xi 范围 (避免数值不稳定)
    xi = max(-0.5, min(xi, 0.5))

    # 计算 beta
    beta = mean_excess * (1 - xi)

    return xi, beta
```

### 2.3 半参数模型方案

#### 2.3.1 设计思路

**混合分布模型**:
- 中心部分: 核密度估计 (非参数)
- 尾部: GPD 分布 (参数)

```
f(x) = {
    核密度估计(x)           当 x_l < x < x_r
    GPD_left(x)            当 x ≤ x_l
    GPD_right(x)           当 x ≥ x_r
}
```

#### 2.3.2 新增代码设计

```python
def semiparametric_var(
    self,
    returns: list[float],
    confidence: float | None = None,
    tail_fraction: float = 0.10,
) -> VaRResult:
    """半参数 VaR 计算.

    中心部分使用核密度估计，尾部使用 GPD。
    适用于中国期货市场的非对称分布特征。

    参数:
        returns: 历史收益率序列
        confidence: 置信水平 (默认 0.99)
        tail_fraction: 尾部占比 (默认 10%)

    返回:
        VaR 结果
    """
    confidence = confidence or 0.99
    n = len(returns)

    if n < 50:
        return self.historical_var(returns, confidence)

    # 1. 分离尾部
    sorted_returns = sorted(returns)
    left_tail_idx = int(tail_fraction * n)

    # 2. 左尾 (损失方向) GPD 建模
    left_tail = [-r for r in sorted_returns[:left_tail_idx]]

    if left_tail:
        # 计算 GPD 参数
        u_left = -sorted_returns[left_tail_idx]
        excesses_left = [x - u_left for x in left_tail if x > u_left]

        if len(excesses_left) >= 5:
            xi_left, beta_left = self._estimate_gpd_params(excesses_left)

            # 计算 VaR
            p = 1 - confidence
            var = u_left + (beta_left / xi_left) * (
                (n / len(excesses_left) * p) ** (-xi_left) - 1
            )
        else:
            var = -sorted_returns[int((1 - confidence) * n)]
    else:
        var = -sorted_returns[int((1 - confidence) * n)]

    # 3. 计算 ES
    tail_losses = [-r for r in sorted_returns if -r > var]
    es = sum(tail_losses) / len(tail_losses) if tail_losses else var

    return VaRResult(
        var=var,
        confidence=confidence,
        method="semiparametric",
        expected_shortfall=es,
        sample_size=n,
        metadata={"tail_fraction": tail_fraction},
    )
```

### 2.4 涨跌停板截断 VaR

#### 2.4.1 问题描述

中国期货市场特有的涨跌停板制度导致:
- 收益率分布在涨跌停位置被截断
- 传统 VaR 方法低估极端风险
- 连续涨跌停时风险敞口无法平仓

#### 2.4.2 截断效应修正公式

```
VaR_adjusted = VaR_raw + Pr(停板) × (预期停板损失)
```

其中预期停板损失需考虑:
- 停板次日低开/高开的概率
- 平均停板持续天数

#### 2.4.3 新增代码设计

```python
@dataclass
class LimitPriceConfig:
    """涨跌停板配置.

    属性:
        upper_limit_pct: 涨停板幅度 (如 0.10 = 10%)
        lower_limit_pct: 跌停板幅度 (如 0.10 = 10%)
        avg_limit_days: 平均停板持续天数
        gap_after_limit: 停板后平均跳空幅度
    """
    upper_limit_pct: float = 0.10
    lower_limit_pct: float = 0.10
    avg_limit_days: float = 1.5
    gap_after_limit: float = 0.03  # 停板后平均跳空 3%


def limit_adjusted_var(
    self,
    returns: list[float],
    confidence: float | None = None,
    limit_config: LimitPriceConfig | None = None,
) -> VaRResult:
    """涨跌停板调整的 VaR.

    考虑中国期货市场涨跌停板截断效应。

    参数:
        returns: 历史收益率序列
        confidence: 置信水平
        limit_config: 涨跌停板配置

    返回:
        调整后的 VaR 结果
    """
    confidence = confidence or 0.99
    limit_config = limit_config or LimitPriceConfig()

    # 1. 计算基础 VaR
    base_result = self.historical_var(returns, confidence)

    # 2. 统计停板事件
    limit_down_count = sum(1 for r in returns if r <= -limit_config.lower_limit_pct * 0.99)
    limit_up_count = sum(1 for r in returns if r >= limit_config.upper_limit_pct * 0.99)

    n = len(returns)
    prob_limit_down = limit_down_count / n if n > 0 else 0

    # 3. 计算停板风险溢价
    # 假设停板后次日继续下跌的概率
    continuation_prob = 0.4  # 经验值
    expected_additional_loss = (
        limit_config.avg_limit_days
        * limit_config.gap_after_limit
        * continuation_prob
    )

    # 4. 调整 VaR
    adjustment = prob_limit_down * expected_additional_loss
    adjusted_var = base_result.var + adjustment

    return VaRResult(
        var=adjusted_var,
        confidence=confidence,
        method="limit_adjusted",
        expected_shortfall=base_result.expected_shortfall + adjustment * 1.5,
        sample_size=n,
        metadata={
            "base_var": base_result.var,
            "adjustment": adjustment,
            "limit_down_count": limit_down_count,
            "limit_up_count": limit_up_count,
            "prob_limit_down": prob_limit_down,
        },
    )
```

### 2.5 流动性调整 VaR (LVaR)

```python
def liquidity_adjusted_var(
    self,
    returns: list[float],
    position_size: float,
    avg_daily_volume: float,
    bid_ask_spread: float,
    confidence: float | None = None,
) -> VaRResult:
    """流动性调整的 VaR.

    考虑平仓时的流动性成本和市场冲击。

    参数:
        returns: 历史收益率序列
        position_size: 持仓规模 (手数)
        avg_daily_volume: 日均成交量 (手数)
        bid_ask_spread: 买卖价差率
        confidence: 置信水平

    返回:
        流动性调整后的 VaR
    """
    confidence = confidence or 0.99

    # 1. 计算基础 VaR
    base_result = self.evt_var(returns, confidence)

    # 2. 计算流动性成本
    # 买卖价差成本
    spread_cost = bid_ask_spread / 2

    # 市场冲击成本 (Almgren-Chriss 模型简化版)
    participation_rate = position_size / avg_daily_volume if avg_daily_volume > 0 else 1.0
    impact_cost = 0.1 * math.sqrt(participation_rate)  # 经验系数

    # 3. 计算紧急平仓成本
    # 假设需要在 1 天内平仓
    liquidation_cost = spread_cost + impact_cost

    # 4. 调整 VaR
    adjusted_var = base_result.var + liquidation_cost

    return VaRResult(
        var=adjusted_var,
        confidence=confidence,
        method="liquidity_adjusted",
        expected_shortfall=base_result.expected_shortfall + liquidation_cost,
        sample_size=base_result.sample_size,
        metadata={
            "base_var": base_result.var,
            "spread_cost": spread_cost,
            "impact_cost": impact_cost,
            "liquidation_cost": liquidation_cost,
            "participation_rate": participation_rate,
        },
    )
```

---

## 3. 中国期货市场特性分析

### 3.1 交易所差异

| 交易所 | 代码 | 主要品种 | 涨跌停板 | 手续费特点 |
|--------|------|----------|----------|------------|
| 上期所 | SHFE | 铜/铝/锌/镍/金/银/螺纹/热卷 | 4-8% | 按金额万分比 |
| 郑商所 | CZCE | 白糖/棉花/PTA/甲醇/菜油 | 4-7% | 按手或按金额 |
| 大商所 | DCE | 豆粕/玉米/铁矿/焦炭/焦煤 | 4-8% | 按手或按金额 |
| 中金所 | CFFEX | 股指期货/国债期货 | 10%/2% | 按金额万分比 |
| 广期所 | GFEX | 工业硅/碳酸锂 | 8-13% | 按金额万分比 |
| 能源中心 | INE | 原油/20号胶/低硫燃油 | 6-10% | 按金额万分比 |

### 3.2 交易时段

```
┌─────────────────────────────────────────────────────────────┐
│                    中国期货交易时段                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   日盘:                                                     │
│   09:00 ─────────── 10:15 │ 10:30 ─────────── 11:30        │
│          早盘第一节          │        早盘第二节            │
│                                                             │
│   13:30 ─────────── 15:00                                   │
│          午盘                                               │
│                                                             │
│   夜盘 (部分品种):                                          │
│   21:00 ─────────── 23:00 (贵金属/有色)                    │
│   21:00 ─────────── 01:00 (原油/国际化品种)                │
│   21:00 ─────────── 23:30 (黑色/化工)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 保证金制度

| 品种类型 | 交易所保证金 | 期货公司加收 | 总保证金 |
|----------|--------------|--------------|----------|
| 股指期货 | 12% | 2-3% | 14-15% |
| 国债期货 | 2% | 1% | 3% |
| 商品期货 | 5-10% | 2-5% | 7-15% |
| 特殊品种 (交割月) | +5-10% | - | 提高 |

---

## 4. 全项目模块改进清单

### 4.1 src/risk/var_calculator.py 改进

| 改进项 | 现状 | 目标 | 优先级 |
|--------|------|------|--------|
| EVT VaR | 无 | 新增 `evt_var()` 方法 | **P0** |
| 半参数 VaR | 无 | 新增 `semiparametric_var()` 方法 | **P0** |
| 涨跌停调整 | 无 | 新增 `limit_adjusted_var()` 方法 | **P0** |
| 流动性调整 | 无 | 新增 `liquidity_adjusted_var()` 方法 | **P1** |
| 跳跃扩散模型 | 无 | 新增 `jump_diffusion_var()` 方法 | **P2** |
| 中文 docstring | 部分 | 全部类/方法改为中文 | **P0** |

### 4.2 src/market/instrument_cache.py 改进

| 改进项 | 现状 | 目标 | 优先级 |
|--------|------|------|--------|
| 涨跌停板字段 | 无 | `upper_limit_pct`, `lower_limit_pct` | **P0** |
| 保证金率字段 | 无 | `margin_rate`, `spec_margin_rate` | **P0** |
| 交易时段字段 | 无 | `trading_sessions` | **P1** |
| 交割日字段 | 有 `expire_date` | 增加 `first_notice_day`, `last_trading_day` | **P1** |
| 品种分类字段 | 无 | `product_class` (农产品/金属/能化/金融) | **P2** |

```python
# 改进后的 InstrumentInfo
@dataclass(frozen=True)
class InstrumentInfo:
    """合约元数据 (军规级 v3.1).

    属性:
        symbol: 合约代码 (如 rb2501)
        product: 品种代码 (如 rb)
        exchange: 交易所 (SHFE/CZCE/DCE/CFFEX/GFEX/INE)
        expire_date: 到期日 (YYYYMMDD)
        tick_size: 最小变动价位
        multiplier: 合约乘数

        # 新增字段 (中国期货市场特化)
        upper_limit_pct: 涨停板幅度 (0.10 = 10%)
        lower_limit_pct: 跌停板幅度 (0.10 = 10%)
        margin_rate: 交易所保证金率
        spec_margin_rate: 特殊保证金率 (交割月等)
        trading_sessions: 交易时段列表 [("09:00", "10:15"), ...]
        first_notice_day: 首次交割通知日
        last_trading_day: 最后交易日
        product_class: 品种分类 (AGRICULTURE/METAL/ENERGY/FINANCIAL)
        max_order_volume: 单笔最大手数
        position_limit: 持仓限额
    """
    symbol: str
    product: str
    exchange: str
    expire_date: str
    tick_size: float
    multiplier: int

    # 中国期货市场特化字段
    upper_limit_pct: float = 0.10
    lower_limit_pct: float = 0.10
    margin_rate: float = 0.10
    spec_margin_rate: float | None = None
    trading_sessions: tuple[tuple[str, str], ...] = (
        ("09:00", "10:15"),
        ("10:30", "11:30"),
        ("13:30", "15:00"),
    )
    first_notice_day: str | None = None
    last_trading_day: str | None = None
    product_class: str = "COMMODITY"
    max_order_volume: int = 500
    position_limit: int = 10000
```

### 4.3 src/cost/estimator.py 改进

| 改进项 | 现状 | 目标 | 优先级 |
|--------|------|------|--------|
| 交易所费率配置 | 单一默认值 | 按交易所/品种差异化配置 | **P0** |
| 按手收费支持 | 仅按金额 | 支持按手/按金额混合 | **P0** |
| 平今优惠品种 | 统一倍率 | 支持免平今品种 | **P1** |
| 申报费 | 无 | 支持撤单/申报费 | **P2** |

```python
# 改进后的费率配置
@dataclass
class FeeConfig:
    """手续费配置 (中国期货市场).

    属性:
        rate: 手续费率 (按金额) 或 每手费用 (按手)
        fee_type: 收费方式 (RATE=按金额比例, FIXED=按手固定)
        close_today_rate: 平今手续费率 (None=同开仓, 0=免平今)
        exchange: 交易所
    """
    rate: float
    fee_type: str = "RATE"  # RATE | FIXED
    close_today_rate: float | None = None  # None=同开仓
    exchange: str = "SHFE"


# 中国期货手续费配置示例
CHINA_FUTURES_FEES: dict[str, FeeConfig] = {
    # 上期所
    "cu": FeeConfig(rate=0.00005, fee_type="RATE"),  # 铜 万分之0.5
    "al": FeeConfig(rate=3.0, fee_type="FIXED"),     # 铝 3元/手
    "rb": FeeConfig(rate=0.0001, fee_type="RATE", close_today_rate=0.0001),  # 螺纹
    "au": FeeConfig(rate=10.0, fee_type="FIXED"),    # 黄金 10元/手

    # 大商所
    "m": FeeConfig(rate=1.5, fee_type="FIXED"),      # 豆粕 1.5元/手
    "i": FeeConfig(rate=0.0001, fee_type="RATE", close_today_rate=0.0001),   # 铁矿
    "jm": FeeConfig(rate=0.0001, fee_type="RATE", close_today_rate=0),       # 焦煤 (免平今)

    # 郑商所
    "CF": FeeConfig(rate=4.3, fee_type="FIXED"),     # 棉花 4.3元/手
    "SR": FeeConfig(rate=3.0, fee_type="FIXED"),     # 白糖 3元/手
    "TA": FeeConfig(rate=3.0, fee_type="FIXED"),     # PTA 3元/手

    # 中金所
    "IF": FeeConfig(rate=0.000023, fee_type="RATE", close_today_rate=0.000345),  # 沪深300
    "IC": FeeConfig(rate=0.000023, fee_type="RATE", close_today_rate=0.000345),  # 中证500
    "T": FeeConfig(rate=3.0, fee_type="FIXED"),      # 10年期国债
}
```

### 4.4 src/risk/manager.py 改进

| 改进项 | 现状 | 目标 | 优先级 |
|--------|------|------|--------|
| VaR 集成 | 无 | 集成 VaRCalculator，按 VaR 限额风控 | **P0** |
| 交易时段检查 | 无 | 非交易时段禁止下单 | **P0** |
| 保证金预警 | 仅 margin_ratio | 按绝对保证金/可用资金比例 | **P1** |
| 临近交割风控 | 无 | 交割月前强制减仓提醒 | **P1** |

### 4.5 src/guardian/triggers.py 改进

| 改进项 | 现状 | 目标 | 优先级 |
|--------|------|------|--------|
| 涨跌停触发器 | 无 | `LimitPriceTrigger` 检测涨跌停 | **P0** |
| 交易时段触发器 | 无 | `TradingSessionTrigger` 检测非交易时段 | **P1** |
| 交割月触发器 | 无 | `DeliveryMonthTrigger` 检测临近交割 | **P1** |
| 大户报告触发器 | 无 | `LargePositionTrigger` 检测持仓限额 | **P2** |

### 4.6 src/strategy/calendar_arb/strategy.py 改进

| 改进项 | 现状 | 目标 | 优先级 |
|--------|------|------|--------|
| 移仓换月逻辑 | 基础 | 添加主力合约切换检测 | **P1** |
| 跨期套利成本 | 基础 | 考虑仓储费/交割费差异 | **P1** |
| 季节性因子 | 无 | 农产品季节性价差模型 | **P2** |

---

## 5. Required Scenarios 新增

### 5.1 VaR 模块场景 (6 条新增)

| rule_id | component | 描述 | category |
|---------|-----------|------|----------|
| `RISK.VAR.EVT_CALCULATE` | var_calculator | EVT VaR 计算正确 | unit |
| `RISK.VAR.SEMIPARAMETRIC` | var_calculator | 半参数 VaR 计算正确 | unit |
| `RISK.VAR.LIMIT_ADJUSTED` | var_calculator | 涨跌停调整 VaR 正确 | unit |
| `RISK.VAR.LIQUIDITY_ADJUSTED` | var_calculator | 流动性调整 VaR 正确 | unit |
| `RISK.VAR.GPD_PARAMS` | var_calculator | GPD 参数估计合理 | unit |
| `RISK.VAR.TAIL_CAPTURE` | var_calculator | 尾部风险捕捉优于正态 | integration |

### 5.2 市场模块场景 (4 条新增)

| rule_id | component | 描述 | category |
|---------|-----------|------|----------|
| `MKT.INST.LIMIT_PRICE` | instrument_cache | 涨跌停字段正确 | unit |
| `MKT.INST.MARGIN_RATE` | instrument_cache | 保证金率字段正确 | unit |
| `MKT.INST.TRADING_SESSION` | instrument_cache | 交易时段字段正确 | unit |
| `MKT.INST.DELIVERY_DATE` | instrument_cache | 交割日期字段正确 | unit |

### 5.3 成本模块场景 (3 条新增)

| rule_id | component | 描述 | category |
|---------|-----------|------|----------|
| `COST.FEE.EXCHANGE_DIFF` | cost_estimator | 交易所差异化费率正确 | unit |
| `COST.FEE.FIXED_PER_LOT` | cost_estimator | 按手收费计算正确 | unit |
| `COST.FEE.CLOSE_TODAY` | cost_estimator | 平今优惠计算正确 | unit |

### 5.4 守护模块场景 (3 条新增)

| rule_id | component | 描述 | category |
|---------|-----------|------|----------|
| `GUARD.TRIGGER.LIMIT_PRICE` | triggers | 涨跌停触发正确 | unit |
| `GUARD.TRIGGER.TRADING_SESSION` | triggers | 非交易时段触发正确 | unit |
| `GUARD.TRIGGER.DELIVERY_MONTH` | triggers | 交割月触发正确 | unit |

---

## 6. 实施优先级与工时估计

### 6.1 Phase 实施计划

| Phase | 内容 | 文件数 | 场景数 | 估计工时 |
|-------|------|--------|--------|----------|
| **P0** | VaR EVT + 涨跌停调整 | 2 | 6 | 16h |
| **P1** | InstrumentCache 扩展 | 1 | 4 | 8h |
| **P2** | CostEstimator 中国化 | 1 | 3 | 6h |
| **P3** | Guardian 触发器扩展 | 1 | 3 | 6h |
| **P4** | RiskManager VaR 集成 | 1 | 2 | 4h |
| **总计** | - | **6** | **18** | **40h** |

### 6.2 依赖关系

```
P0 VaR 增强
    │
    ▼
P1 InstrumentCache ──────┐
    │                    │
    ▼                    ▼
P2 CostEstimator    P3 Guardian
    │                    │
    └────────┬───────────┘
             ▼
        P4 RiskManager 集成
```

---

## 7. 代码实现规范

### 7.1 中文注释规范

```python
# 模块级 docstring
"""模块名称 (军规级 v3.x).

功能描述。

功能特性:
- 特性1
- 特性2

示例:
    使用示例代码
"""

# 类级 docstring
class ClassName:
    """类名称.

    类功能描述。

    属性:
        attr1: 属性1描述
        attr2: 属性2描述
    """

# 方法级 docstring
def method_name(self, param1: Type1, param2: Type2) -> ReturnType:
    """方法功能描述.

    详细描述（可选）。

    参数:
        param1: 参数1描述
        param2: 参数2描述

    返回:
        返回值描述

    异常:
        ExceptionType: 异常描述
    """
```

### 7.2 Required Scenario 测试规范

```python
class TestVaREVT:
    """V2 Scenario: RISK.VAR.EVT_CALCULATE - EVT VaR 计算正确."""

    RULE_ID = "RISK.VAR.EVT_CALCULATE"
    COMPONENT = "var_calculator"

    def test_evt_var_heavy_tail(self) -> None:
        """EVT VaR 能捕捉重尾分布."""
        # 准备：生成肥尾分布样本
        returns = self._generate_heavy_tail_returns(n=500)

        calculator = VaRCalculator()

        # 执行
        evt_result = calculator.evt_var(returns, confidence=0.99)
        param_result = calculator.parametric_var(returns, confidence=0.99)

        # 验证：EVT VaR 应大于参数法 VaR (因为能捕捉尾部)
        assert evt_result.var > param_result.var, (
            f"[{self.RULE_ID}] EVT VaR ({evt_result.var:.4f}) 应大于 "
            f"参数法 VaR ({param_result.var:.4f})"
        )

        # 验证：GPD 参数合理
        assert evt_result.metadata is not None
        xi = evt_result.metadata.get("xi", 0)
        assert 0 < xi < 0.5, f"[{self.RULE_ID}] xi={xi} 应在 (0, 0.5) 范围"
```

---

## 附录 A: 中国期货市场常用参数

### A.1 涨跌停板幅度 (2024年)

| 品种 | 交易所 | 涨跌停 | 备注 |
|------|--------|--------|------|
| 螺纹钢 | SHFE | ±7% | |
| 热卷 | SHFE | ±7% | |
| 铜 | SHFE | ±7% | |
| 黄金 | SHFE | ±8% | |
| 铁矿石 | DCE | ±9% | |
| 焦炭 | DCE | ±8% | |
| 豆粕 | DCE | ±5% | |
| 棉花 | CZCE | ±5% | |
| PTA | CZCE | ±5% | |
| 沪深300 | CFFEX | ±10% | |
| 国债期货 | CFFEX | ±2% | |
| 原油 | INE | ±8% | |

### A.2 主要品种手续费 (参考值)

| 品种 | 开仓 | 平今 | 备注 |
|------|------|------|------|
| rb | 万分之1 | 万分之1 | |
| hc | 万分之1 | 万分之1 | |
| i | 万分之1 | 万分之1 | |
| m | 1.5元/手 | 1.5元/手 | |
| jm | 万分之0.6 | 0 | 免平今 |
| IF | 万分之0.23 | 万分之3.45 | 平今15倍 |
| T | 3元/手 | 0 | 免平今 |

---

**报告完毕！CLAUDE上校敬礼！** 🎖️

> 本报告遵循军规 M2 (场景驱动)、M3 (全量实现)、M8 (审计完整) 要求。
> 所有改进均需通过门禁检查后方可合并。
