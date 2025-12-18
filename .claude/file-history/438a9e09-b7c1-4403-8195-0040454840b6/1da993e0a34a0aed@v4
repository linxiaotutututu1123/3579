# Phase 7 中国期货市场特化实施计划

## 概述

| 项目 | 值 |
|------|-----|
| **任务** | 实施Phase 7中国期货市场特化模块 |
| **军规覆盖** | M13涨跌停感知, M14平今平昨分离, M15夜盘跨日, M16保证金监控, M17程序化合规, M20跨所一致 |
| **预计工时** | 90h |
| **新增文件** | 10个 |
| **新增场景** | 23条 |
| **日期** | 2025-12-16 |

---

## 1. 实施文件清单

| 序号 | 文件路径 | 功能 | 军规 | 预计行数 |
|------|----------|------|------|----------|
| 1 | `src/market/exchange_config.py` | 六大交易所配置 | M20 | ~300 |
| 2 | `src/market/trading_calendar.py` | 夜盘交易日历 | M15 | ~250 |
| 3 | `src/cost/china_fee_calculator.py` | 中国期货手续费 | M5, M14 | ~300 |
| 4 | `src/execution/protection/limit_price.py` | 涨跌停保护 | M13 | ~200 |
| 5 | `src/execution/protection/margin_monitor.py` | 保证金监控 | M16 | ~250 |
| 6 | `src/guardian/triggers_china.py` | 中国期货触发器 | M6, M13, M16 | ~300 |
| 7 | `src/risk/stress_test_china.py` | 中国期货压力测试 | M6 | ~350 |
| 8 | `src/strategy/calendar_arb/delivery_aware.py` | 交割感知套利 | M15 | ~250 |
| 9 | `src/compliance/china_futures_rules.py` | 合规规则 | M17 | ~200 |
| 10 | `src/compliance/programmatic_trading.py` | 程序化交易合规 | M17 | ~300 |

---

## 2. 实施步骤

### Step 1: 六大交易所配置 (14h)
**文件**: `src/market/exchange_config.py`

```python
# 核心功能:
- Exchange 枚举 (SHFE/DCE/CZCE/CFFEX/GFEX/INE)
- EXCHANGE_CONFIG 字典 (交易时段/夜盘/品种列表)
- PRODUCT_CATEGORIES 品种分类
- get_exchange_for_product() 品种->交易所映射
- get_trading_sessions() 获取交易时段
- has_night_session() 是否有夜盘
```

**测试场景**:
- `CHINA.EXCHANGE.CONFIG_LOAD`: 配置加载正确
- `CHINA.EXCHANGE.PRODUCT_MAP`: 品种映射正确

### Step 2: 夜盘交易日历 (10h)
**文件**: `src/market/trading_calendar.py`

```python
# 核心功能:
- ChinaTradingCalendar 类
- get_trading_day(timestamp) 根据时间戳获取交易日
- is_trading_time(timestamp) 判断是否交易时间
- get_next_trading_day(date) 获取下一个交易日
- 节假日处理 (春节/国庆等)
```

**测试场景**:
- `CHINA.CALENDAR.NIGHT_SESSION`: 夜盘时段正确
- `CHINA.CALENDAR.TRADING_DAY`: 交易日计算正确
- `CHINA.CALENDAR.HOLIDAY`: 节假日处理正确

### Step 3: 中国期货手续费计算器 (14h)
**文件**: `src/cost/china_fee_calculator.py`

```python
# 核心功能:
- FeeType 枚举 (RATIO/FIXED/MIXED)
- FeeConfig dataclass
- ChinaFeeCalculator 类
  - calculate(instrument, price, volume, direction)
  - _calc_by_ratio() 按金额计算
  - _calc_by_fixed() 按手计算
  - _calc_close_today() 平今手续费
```

**测试场景**:
- `CHINA.FEE.BY_VOLUME_CALC`: 按手收费计算
- `CHINA.FEE.BY_VALUE_CALC`: 按金额收费计算
- `CHINA.FEE.CLOSE_TODAY_CALC`: 平今手续费计算

### Step 4: 涨跌停保护 (10h)
**文件**: `src/execution/protection/limit_price.py`

```python
# 核心功能:
- LimitPriceGuard 类
- check_order_price(order, instrument, last_settle) -> (bool, str)
- get_limit_prices(instrument, last_settle) -> (up, down)
- is_at_limit(price, instrument, last_settle) -> bool
```

**测试场景**:
- `CHINA.LIMIT.PRICE_CHECK`: 涨跌停价格检查
- `CHINA.LIMIT.ORDER_REJECT`: 超限订单拒绝

### Step 5: 保证金监控 (14h)
**文件**: `src/execution/protection/margin_monitor.py`

```python
# 核心功能:
- MarginLevel 枚举 (SAFE/NORMAL/WARNING/DANGER/CRITICAL)
- MarginConfig dataclass
- MarginMonitor 类
  - update(equity, margin_used) -> MarginLevel
  - get_available_margin() -> float
  - can_open_position(required_margin) -> (bool, str)
```

**测试场景**:
- `CHINA.MARGIN.RATIO_CHECK`: 保证金率检查
- `CHINA.MARGIN.USAGE_MONITOR`: 保证金使用监控
- `CHINA.MARGIN.WARNING_LEVEL`: 保证金预警等级

### Step 6: 中国期货触发器 (10h)
**文件**: `src/guardian/triggers_china.py`

```python
# 核心功能:
- LimitPriceTrigger 涨跌停触发器
- MarginTrigger 保证金触发器
- DeliveryApproachingTrigger 交割临近触发器
- register_china_triggers() 注册所有中国期货触发器
```

**测试场景**:
- `CHINA.TRIGGER.LIMIT_PRICE`: 涨跌停触发器
- `CHINA.TRIGGER.MARGIN_CALL`: 保证金追缴触发
- `CHINA.TRIGGER.DELIVERY`: 交割月接近触发

### Step 7: 中国期货压力测试 (8h)
**文件**: `src/risk/stress_test_china.py`

```python
# 核心功能:
- StressScenario dataclass
- STRESS_SCENARIOS 历史场景列表
  - CRASH_2015 (2015股灾)
  - OIL_NEGATIVE_2020 (原油负价)
  - LITHIUM_2022 (碳酸锂暴跌)
- run_stress_test(portfolio, scenario) -> StressResult
```

**测试场景**:
- `CHINA.STRESS.2015_CRASH`: 2015股灾场景
- `CHINA.STRESS.2020_OIL`: 2020原油负价场景
- `CHINA.STRESS.2022_LITHIUM`: 2022碳酸锂场景

### Step 8: 交割感知套利 (6h)
**文件**: `src/strategy/calendar_arb/delivery_aware.py`

```python
# 核心功能:
- DeliveryAwareCalendarArb 类
- _check_delivery_distance() 检查交割距离
- _should_roll_position() 是否需要移仓换月
- _execute_roll() 执行移仓
```

**测试场景**:
- `CHINA.ARB.DELIVERY_AWARE`: 交割感知套利
- `CHINA.ARB.POSITION_TRANSFER`: 移仓换月逻辑

### Step 9: 合规模块 (4h)
**文件**: `src/compliance/__init__.py`, `src/compliance/china_futures_rules.py`

```python
# 核心功能:
- ComplianceChecker 类
- check_order_compliance(order) -> (bool, list[str])
- 规则检查: 持仓限额/下单限制/品种限制
```

**测试场景**:
- `CHINA.COMPLIANCE.RULE_CHECK`: 合规规则检查

### Step 10: 程序化交易合规 (10h)
**文件**: `src/compliance/programmatic_trading.py`

```python
# 核心功能:
- ComplianceThrottle 节流器 (5秒50笔)
- ThrottleLevel 枚举 (NORMAL/WARNING/CRITICAL/EXCEEDED)
- ProgrammaticTradingCompliance 类
  - can_submit() -> (bool, str)
  - record_order() 记录订单
  - get_daily_count() 获取日内报撤单数
  - is_high_frequency() 是否高频交易
```

**测试场景**:
- `CHINA.COMPLIANCE.REPORT_FREQUENCY`: 报撤单频率检查

---

## 3. 执行顺序

```
Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6 → Step 7 → Step 8 → Step 9 → Step 10
  │         │         │         │         │         │
  │         │         │         │         │         └── 依赖 Step 4, 5
  │         │         │         │         └── 独立
  │         │         │         └── 依赖 Step 1
  │         │         └── 依赖 Step 1
  │         └── 依赖 Step 1
  └── 基础依赖
```

---

## 4. 验收标准

### 功能验收
- [ ] 六大交易所配置完整 (SHFE/DCE/CZCE/CFFEX/GFEX/INE)
- [ ] 夜盘交易日归属正确
- [ ] 手续费计算准确 (按手/按金额/平今)
- [ ] 涨跌停价格检查生效
- [ ] 保证金监控预警正常
- [ ] 中国期货触发器工作正常
- [ ] 压力测试场景覆盖历史极端行情
- [ ] 交割感知套利移仓换月正确
- [ ] 程序化合规检查通过 (5秒50笔)

### 门禁验收
- [ ] Ruff Check 通过
- [ ] Ruff Format 通过
- [ ] Mypy 通过
- [ ] Pytest 全部通过
- [ ] 覆盖率 ≥ 85%
- [ ] Policy 验证通过

### 场景验收 (23条)
- [ ] CHINA.EXCHANGE.* (2条)
- [ ] CHINA.CALENDAR.* (3条)
- [ ] CHINA.FEE.* (3条)
- [ ] CHINA.LIMIT.* (2条)
- [ ] CHINA.MARGIN.* (3条)
- [ ] CHINA.TRIGGER.* (3条)
- [ ] CHINA.STRESS.* (3条)
- [ ] CHINA.ARB.* (2条)
- [ ] CHINA.COMPLIANCE.* (2条)

---

## 5. 关键代码参考

### 六大交易所配置结构
```python
EXCHANGE_CONFIG = {
    Exchange.SHFE: {
        "name": "上海期货交易所",
        "trading_hours": [("09:00", "10:15"), ("10:30", "11:30"), ("13:30", "15:00")],
        "night_session": ("21:00", "02:30"),
        "products": ["cu", "al", "zn", "pb", "ni", "sn", "au", "ag", "rb", "hc", ...],
    },
    # ... DCE, CZCE, CFFEX, GFEX, INE
}
```

### 保证金等级阈值
```python
MarginLevel.SAFE      # < 50%
MarginLevel.NORMAL    # 50% - 70%
MarginLevel.WARNING   # 70% - 85%
MarginLevel.DANGER    # 85% - 100%
MarginLevel.CRITICAL  # >= 100%
```

### 程序化合规阈值
```python
REPORT_CANCEL_LIMIT_5S = 50      # 5秒内报撤单上限
HIGH_FREQ_LIMIT_PER_SEC = 300    # 高频交易阈值 (笔/秒)
HIGH_FREQ_LIMIT_DAILY = 20000    # 高频交易阈值 (笔/日)
```

---

## 6. 风险提示

1. **夜盘跨日边界**: 21:00-02:30属于下一交易日，需特别注意
2. **节假日处理**: 春节/国庆前后无夜盘，需正确处理
3. **涨跌停幅度**: 各品种不同，需从合约信息获取
4. **平今手续费**: CFFEX平今费率极高(15倍)，需特别处理
5. **2025年新规**: 10月9日实施，报撤单频率监控是硬性要求

---

**计划完成，请批准后开始实施！**
