# V4PRO 执行模块 (execution/)

> **版本**: v4.0.0 军规级
> **军规覆盖**: M1, M4, M13

---

## 模块职责

执行模块是V4PRO系统的**订单执行引擎**，负责：
- 订单生成和发送
- 保护层（涨跌停、胖手指、节流）
- 配对执行（套利腿）
- Broker抽象和工厂

---

## 目录结构

```
execution/
├── broker.py            # Broker抽象基类
├── broker_factory.py    # Broker工厂
├── ctp_broker.py        # CTP实现
├── order_types.py       # 订单类型定义
├── order_tracker.py     # 订单追踪
├── events.py            # 执行事件
├── flatten_plan.py      # 平仓计划
├── flatten_executor.py  # 平仓执行
│
├── auto/                # 自动执行引擎
│   ├── engine.py        # 执行引擎
│   ├── state_machine.py # 状态机
│   ├── retry.py         # 重试逻辑
│   ├── timeout.py       # 超时处理
│   ├── position_tracker.py
│   ├── order_context.py
│   └── exec_context.py
│
├── pair/                # 配对执行
│   ├── pair_executor.py # 配对执行器
│   └── leg_manager.py   # 腿管理
│
└── protection/          # 保护层 (M1,M13)
    ├── limit_price.py   # 涨跌停感知
    ├── fat_finger.py    # 胖手指检查
    ├── throttle.py      # 报撤单节流
    ├── liquidity.py     # 流动性检查
    └── margin_monitor.py # 保证金监控
```

---

## 核心概念

### 保护层 (M13)
```python
from src.execution.protection import (
    LimitPriceChecker,
    FatFingerChecker,
    OrderThrottle
)

# 涨跌停检查
limit_checker = LimitPriceChecker()
if limit_checker.is_limit_up(symbol, price):
    return None  # 不下单

# 胖手指检查
fat_finger = FatFingerChecker(max_value=500000)
if not fat_finger.check(order):
    raise FatFingerError("订单金额过大")

# 报撤单节流
throttle = OrderThrottle(limit_5s=50)
if not throttle.allow():
    return None  # 等待
```

### Broker工厂
```python
from src.execution import BrokerFactory

# 根据环境创建Broker
broker = BrokerFactory.create(
    broker_type="ctp",      # 实盘
    # broker_type="mock",   # 测试
    config=broker_config
)
```

---

## 订单类型

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| LIMIT | 限价单 | 常规下单 |
| MARKET | 市价单 | 紧急平仓 |
| FAK | Fill And Kill | 部分成交 |
| FOK | Fill Or Kill | 全成或撤 |

---

## 使用示例

```python
from src.execution import (
    Broker,
    Order,
    OrderType
)
from src.execution.auto import ExecutionEngine

# 1. 创建订单
order = Order(
    symbol="rb2405",
    direction="BUY",
    offset="OPEN",
    price=3850.0,
    quantity=10,
    order_type=OrderType.LIMIT
)

# 2. 执行引擎
engine = ExecutionEngine(broker, protection_config)

# 3. 提交订单
result = engine.submit(order)

# 4. 等待成交
fills = engine.wait_fills(order.id, timeout=30)
```

---

## 配对执行 (套利)

```python
from src.execution.pair import PairExecutor

# 创建配对执行器
pair_exec = PairExecutor(broker)

# 执行套利腿
result = pair_exec.execute_spread(
    near_leg=Order(...),  # 近月腿
    far_leg=Order(...),   # 远月腿
    max_slippage=2        # 最大滑点
)
```

---

## 依赖关系

```
execution/
    │
    ├──◀ strategy/   (接收订单)
    ├──▶ broker/     (发送到交易所)
    ├──▶ risk/       (风控检查)
    └──▶ audit/      (订单记录)
```

---

**军规级别国家伟大工程 - 执行模块规范**
