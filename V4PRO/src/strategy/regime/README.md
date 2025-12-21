# 市场状态引擎设计文档 (D7-P0)

V4PRO Platform Component - Phase 8 策略协同
版本: v4.2
日期: 2024-12-22

## 1. 概述

市场状态引擎是 V4PRO 策略协同系统的核心组件，负责实时识别市场状态并调整策略权重。

### 1.1 设计目标

- **状态识别**: 准确识别四种市场状态
- **权重调整**: 根据市场状态动态调整策略权重
- **熔断联动**: 极端状态触发熔断检查
- **审计追踪**: 完整的状态转换审计日志

### 1.2 军规合规

| 军规 | 要求 | 实现方式 |
|------|------|----------|
| M1 | 单一信号源 | 状态引擎输出为策略权重调整的唯一依据 |
| M6 | 熔断保护 | 极端状态触发熔断检查回调 |
| M3 | 审计日志 | 所有状态转换记录审计日志 |

## 2. 架构设计

```
市场状态引擎
├── 状态定义层 (states.py)
│   ├── MarketRegime - 四种市场状态枚举
│   ├── RegimeStrength - 状态强度枚举
│   ├── RegimeState - 状态快照数据类
│   └── RegimeWeightConfig - 权重配置
│
├── 指标计算层 (indicators.py)
│   ├── RegimeIndicators - 指标计算器
│   ├── ATR计算 - 平均真实波幅
│   ├── ADX计算 - 平均方向指数
│   ├── 波动率计算 - 历史波动率
│   └── 成交量分析 - 成交量比率
│
├── 转换逻辑层 (transitions.py)
│   ├── TransitionEngine - 转换引擎
│   ├── 条件检测 - 波动率/成交量/价格模式
│   ├── 投票机制 - 状态稳定性验证
│   └── 审计日志 - M3军规
│
└── 检测器层 (detector.py)
    ├── MarketRegimeDetector - 核心检测器
    ├── RegimeFederationAdapter - 联邦适配器
    ├── 熔断联动 - M6军规
    └── 权重输出 - M1军规
```

## 3. 状态定义

### 3.1 四种市场状态

| 状态 | 值 | 描述 | 默认权重乘数 |
|------|-----|------|------------|
| TRENDING | 0 | 明确方向性趋势运动 | 1.0 |
| RANGING | 1 | 区间震荡无明确方向 | 0.7 |
| VOLATILE | 2 | 高波动不确定方向 | 0.5 |
| EXTREME | 3 | 异常极端市场条件 | 0.2 |

### 3.2 状态强度

| 强度 | 置信度范围 | 描述 |
|------|-----------|------|
| STRONG | 0.7 - 1.0 | 信号非常明确 |
| MODERATE | 0.4 - 0.7 | 信号较明确 |
| WEAK | 0.0 - 0.4 | 信号不明确 |

## 4. 转换检测

### 4.1 检测指标

```python
# 波动率指标
atr                    # 平均真实波幅
atr_percentile         # ATR百分位
historical_volatility  # 历史波动率
volatility_percentile  # 波动率百分位

# 趋势指标
adx                    # 平均方向指数
plus_di                # +DI方向指标
minus_di               # -DI方向指标
trend_strength         # 趋势强度

# 成交量指标
volume_ratio           # 成交量比率
volume_percentile      # 成交量百分位

# 价格模式指标
price_range_ratio      # 价格区间比率
breakout_score         # 突破得分
```

### 4.2 转换条件

**极端状态 (EXTREME)**:
- 波动率百分位 > 95
- ATR百分位 > 95
- 成交量激增 > 3x
- 价格区间异常 > 2.5x ATR

**高波动状态 (VOLATILE)**:
- 波动率百分位 > 75
- ATR百分位 > 75
- ADX < 25 (无明确趋势)
- 价格区间 > 1.5x ATR

**趋势状态 (TRENDING)**:
- ADX > 25
- DI差值 > 10
- 趋势强度 > 0.5
- 波动率适中 (30-75)

**震荡状态 (RANGING)**:
- ADX < 15
- DI差值 < 10
- 波动率正常 (< 60)
- 无突破信号

### 4.3 投票机制

```python
# 状态稳定性验证
MIN_REGIME_DURATION = 3  # 最小持续K线数
VOTE_WINDOW = 3          # 投票窗口

# 需要超过半数投票一致才能转换
# 除非是转向极端状态 (EXTREME)
```

## 5. 策略权重调整

### 5.1 策略类型权重映射

| 策略类型 | TRENDING | RANGING | VOLATILE | EXTREME |
|---------|----------|---------|----------|---------|
| trend_following | 1.2 | 0.5 | 0.7 | 0.3 |
| mean_reversion | 0.5 | 1.2 | 0.8 | 0.3 |
| arbitrage | 0.9 | 1.0 | 1.1 | 0.5 |
| ml | 1.0 | 1.0 | 0.7 | 0.4 |

### 5.2 权重计算

```python
def get_weight_multiplier(strategy_type, regime_state):
    base_weight = RegimeWeightConfig.get_weight(strategy_type, regime_state.regime)
    confidence_factor = 0.5 + 0.5 * regime_state.confidence
    return base_weight * confidence_factor
```

## 6. 与策略联邦集成

### 6.1 适配器模式

```python
class RegimeFederationAdapter:
    """状态-联邦适配器"""

    def __init__(self, detector: MarketRegimeDetector):
        self._detector = detector
        self._strategy_type_mapping = {}

    def register_strategy_type(self, strategy_id: str, strategy_type: str):
        """注册策略类型映射"""
        self._strategy_type_mapping[strategy_id] = strategy_type

    def get_weight_multiplier(self, strategy_id: str) -> float:
        """获取策略权重乘数"""
        strategy_type = self._strategy_type_mapping.get(strategy_id, "ml")
        return self._detector.get_strategy_weight(strategy_type)
```

### 6.2 使用示例

```python
from src.strategy.regime import MarketRegimeDetector, RegimeFederationAdapter
from src.strategy.federation import StrategyFederation

# 创建检测器和适配器
detector = MarketRegimeDetector()
adapter = RegimeFederationAdapter(detector)

# 注册策略类型
adapter.register_strategy_type("kalman_arb", "arbitrage")
adapter.register_strategy_type("lstm_trend", "trend_following")
adapter.register_strategy_type("moe_ensemble", "ml")

# 创建策略联邦
federation = StrategyFederation()
federation.register_strategy("kalman_arb", weight=0.3)
federation.register_strategy("lstm_trend", weight=0.25)

# 检测市场状态
bars = get_market_data()
state = detector.detect_from_bars(bars)

# 获取调整后的权重
for strategy_id in ["kalman_arb", "lstm_trend"]:
    multiplier = adapter.get_weight_multiplier(strategy_id)
    adjusted_weight = federation.get_member(strategy_id).weight * multiplier
    federation.set_weight(strategy_id, adjusted_weight)
```

## 7. 熔断联动

### 7.1 极端状态回调

```python
class CircuitBreakerInterface(Protocol):
    def check_extreme_conditions(self, regime_state: RegimeState) -> bool:
        """检查极端条件"""
        ...

# 检测器配置
detector = MarketRegimeDetector(
    config=DetectorConfig(enable_circuit_breaker_check=True),
    circuit_breaker=circuit_breaker_instance,
)

# 当检测到极端状态时，自动触发熔断检查
```

## 8. 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| 检测延迟 | < 10ms | ~ 5ms |
| 内存占用 | < 10MB | ~ 5MB |
| 状态历史 | 100条 | 可配置 |

## 9. 文件清单

```
src/strategy/regime/
├── __init__.py      # 模块入口
├── states.py        # 状态定义
├── indicators.py    # 指标计算
├── transitions.py   # 转换逻辑
└── detector.py      # 状态检测器

tests/strategy/regime/
├── __init__.py
└── test_regime_detector.py  # 测试用例
```

## 10. 变更历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v4.2 | 2024-12-22 | 初始实现 D7-P0 市场状态引擎 |
