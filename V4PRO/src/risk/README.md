# V4PRO 风控模块 (risk/)

> **版本**: v4.3.0 军规级
> **军规覆盖**: M3, M6, M16, M19, M31

---

## 模块职责

风控模块是V4PRO系统的**风险防线**，负责：
- VaR/ES计算
- 压力测试（中国市场特化）
- 保证金监控（M16核心）
- 风险归因分析
- **置信度评估** (v4.3 新增)

---

## 文件清单

| 文件 | 功能 | 军规覆盖 |
|------|------|----------|
| `manager.py` | 风控管理器 | M6,M16 |
| `var_calculator.py` | VaR计算器 | M6 |
| `dynamic_var.py` | 动态VaR | M6 |
| `stress_test_china.py` | 中国市场压力测试 | M19 |
| `attribution.py` | 风险归因 | M19 |
| `confidence.py` | 置信度评估 (v4.3) | M3,M19 |
| `state.py` | 风控状态管理 | M6 |
| `events.py` | 风控事件 | M6 |

---

## 核心概念

### VaR计算 (M6)
```python
from src.risk import VaRCalculator

# 创建VaR计算器
var_calc = VaRCalculator(
    confidence=0.99,    # 99%置信度
    horizon_days=1      # 1日VaR
)

# 计算VaR
var = var_calc.calculate(positions, returns)
es = var_calc.expected_shortfall(positions, returns)
```

### 保证金监控 (M16)
```python
from src.risk import RiskManager

manager = RiskManager(config)

# 检查保证金
margin_ratio = manager.check_margin()
if margin_ratio > 0.8:  # 80%临界线
    manager.trigger_reduce_position()
if margin_ratio > 0.9:  # 90%强平线
    manager.trigger_force_close()
```

---

## 风控阈值

| 指标 | 预警线 | 临界线 | 熔断线 |
|------|--------|--------|--------|
| 单日亏损 | 50,000 | 80,000 | 100,000 |
| 保证金占用 | 60% | 80% | 90% |
| VaR | - | - | 100,000 |
| ES | - | - | 150,000 |

---

## 压力测试 (M19)

```python
from src.risk import ChinaStressTest

stress_test = ChinaStressTest()

# 执行压力测试场景
results = stress_test.run_scenarios([
    "limit_down_3days",      # 连续3日跌停
    "margin_increase_50pct", # 保证金上调50%
    "liquidity_crisis",      # 流动性危机
])

# 检查是否通过
if not results.all_passed:
    raise RiskError("压力测试未通过")
```

---

## 使用示例

```python
from src.risk import (
    RiskManager,
    VaRCalculator,
    RiskState
)

# 1. 初始化风控管理器
manager = RiskManager(risk_config)

# 2. 注册风控检查
manager.register_check("var", var_calculator)
manager.register_check("margin", margin_monitor)

# 3. 执行风控检查
state = manager.check_all(positions, market_data)

# 4. 根据状态决策
if state == RiskState.CRITICAL:
    # 触发减仓
    pass
elif state == RiskState.CIRCUIT_BREAK:
    # 触发熔断
    sys.exit(ExitCode.RISK_BREACH.value)
```

---

## 风险归因

```python
from src.risk import RiskAttribution

attribution = RiskAttribution()

# 计算风险贡献
contrib = attribution.calculate(
    portfolio=portfolio,
    factor_returns=factor_returns
)

# 输出因子贡献
print(f"市场风险: {contrib.market}")
print(f"行业风险: {contrib.sector}")
print(f"特质风险: {contrib.idiosyncratic}")
```

---

## 置信度评估 (v4.3 新增)

**集成 superclaude ConfidenceChecker 与 V4PRO 信号置信度系统**

### 预执行置信度检查
```python
from src.risk import assess_pre_execution, ConfidenceLevel

# 预执行检查 (防止错误方向执行)
result = assess_pre_execution(
    "implement_feature",
    duplicate_check=True,
    architecture_verified=True,
    has_docs=True,
    has_oss=True,
    root_cause=True,
)

if result.level == ConfidenceLevel.HIGH:
    # ≥90% 置信度 - 可直接执行
    execute_task()
elif result.level == ConfidenceLevel.MEDIUM:
    # 70-89% - 需要确认
    request_confirmation()
else:
    # <70% - 停止并调查
    stop_and_investigate()
```

### 信号置信度评估
```python
from src.risk import assess_signal

# 交易信号置信度评估
result = assess_signal(
    "rb2501",
    "kalman_arb",
    strength=0.8,
    consistency=0.85,
    market_condition="NORMAL",
    risk_ok=True,
)

print(f"置信度: {result.score:.0%}")  # → 100%
print(f"等级: {result.level.value}")  # → HIGH
```

### 置信度阈值

| 等级 | 阈值 | 操作 |
|------|------|------|
| HIGH | ≥90% | 可直接执行 |
| MEDIUM | 70-89% | 需要确认/替代方案 |
| LOW | <70% | 停止并调查 |

### 评估标准

**预执行模式** (superclaude):
| 检查项 | 权重 |
|--------|------|
| 无重复实现 | 25% |
| 架构合规 | 25% |
| 官方文档验证 | 20% |
| OSS参考实现 | 15% |
| 根因识别 | 15% |

**信号模式** (V4PRO):
| 检查项 | 权重 |
|--------|------|
| 信号强度 (≥0.5) | 30% |
| 信号一致性 (≥0.6) | 25% |
| 市场状态 | 25% |
| 风险限制 | 20% |

---

## 依赖关系

```
risk/
    │
    ├──◀ trading/    (风控检查)
    ├──◀ strategy/   (策略约束)
    ├──◀ execution/  (订单风控)
    ├──▶ market/     (行情数据)
    └──▶ audit/      (风控记录)
```

---

**军规级别国家伟大工程 - 风控模块规范**
