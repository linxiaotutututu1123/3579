# V4PRO 策略模块 (strategy/)

> **版本**: v4.0.0 军规级
> **军规覆盖**: M4, M9, M18

---

## 模块职责

策略模块是V4PRO系统的**决策大脑**，负责：
- 策略框架和基类定义
- 降级链管理（M4核心）
- 日历套利策略实现
- AI策略集成

---

## 目录结构

```
strategy/
├── base.py              # 策略基类
├── types.py             # 类型定义
├── factory.py           # 策略工厂
├── fallback.py          # 降级管理器 (M4)
├── explain.py           # 决策解释
│
├── calendar_arb/        # 日历套利策略
│   ├── strategy.py      # 主策略
│   ├── kalman_beta.py   # Kalman滤波
│   └── delivery_aware.py # 交割感知 (M15)
│
├── dl/                  # 深度学习策略
│   ├── model.py         # 模型定义
│   ├── features.py      # 特征工程
│   ├── policy.py        # 策略网络
│   └── weights.py       # 权重管理
│
├── federation/          # 联邦学习
│   └── central_coordinator.py
│
└── experimental/        # 实验性功能
    ├── training_gate.py # 训练门禁
    └── maturity_evaluator.py
```

---

## 核心概念

### 降级链 (M4)
```python
from src.strategy import FallbackManager

# 降级链配置
fallback_chain = [
    "calendar_arb",   # 首选：日历套利
    "linear_ai",      # 降级1：线性AI
    "simple_ai"       # 降级2：简单AI
]

manager = FallbackManager(fallback_chain)
decision = manager.get_decision(market_data)
```

### 策略基类
```python
from src.strategy import Strategy

class MyStrategy(Strategy):
    def on_tick(self, tick):
        # 处理行情
        pass

    def generate_signal(self):
        # 生成信号
        return Signal(...)
```

---

## 策略清单

| 策略 | 文件 | 说明 | 军规 |
|------|------|------|------|
| CalendarArb | `calendar_arb/` | 日历价差套利 | M4,M15 |
| LinearAI | `linear_ai.py` | 线性模型 | M4 |
| SimpleAI | `simple_ai.py` | 简单AI | M4 |
| DLPolicy | `dl_torch_policy.py` | PyTorch策略 | M18 |
| EnsembleMoE | `ensemble_moe.py` | 专家混合 | M18 |
| TrendRiskParity | `top_tier_trend_risk_parity.py` | 趋势风险平价 | M6 |

---

## Kalman滤波 (日历套利)

```python
from src.strategy.calendar_arb import KalmanBetaEstimator

# 创建Kalman滤波器
kalman = KalmanBetaEstimator(
    delta=0.0001,  # 状态转移方差
    r=0.001        # 观测噪声方差
)

# 更新估计
beta, spread = kalman.update(near_price, far_price)
```

---

## 依赖关系

```
strategy/
    │
    ├──▶ market/     (行情数据)
    ├──▶ cost/       (成本估算)
    ├──▶ risk/       (风控检查)
    └──▶ audit/      (决策记录)
```

---

**军规级别国家伟大工程 - 策略模块规范**
