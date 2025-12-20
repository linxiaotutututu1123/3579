# V4PRO 行情模块 (market/)

> **版本**: v4.0.0 军规级
> **军规覆盖**: M3, M15, M20

---

## 模块职责

行情模块是V4PRO系统的**数据入口**，负责：
- 行情订阅和分发
- 六大交易所配置管理（M20）
- 夜盘/节假日日历（M15）
- 行情质量监控

---

## 文件清单

| 文件 | 功能 | 军规覆盖 |
|------|------|----------|
| `subscriber.py` | 行情订阅器 | M3 |
| `quote_cache.py` | 行情缓存 | M3 |
| `bar_builder.py` | K线构建 | - |
| `trading_calendar.py` | 交易日历(夜盘) | M15 |
| `exchange_config.py` | 交易所配置 | M20 |
| `config_loader.py` | 配置加载器 | M20 |
| `instrument_cache.py` | 合约缓存 | M20 |
| `main_contract_tracker.py` | 主力合约跟踪 | M15 |
| `universe_selector.py` | 标的选择 | - |
| `quality.py` | 行情质量监控 | M3 |

---

## 核心概念

### 六大交易所 (M20)
| 交易所 | 代码 | 配置文件 |
|--------|------|----------|
| 上海期货交易所 | SHFE | `config/exchanges/shfe.yml` |
| 大连商品交易所 | DCE | `config/exchanges/dce.yml` |
| 郑州商品交易所 | CZCE | `config/exchanges/czce.yml` |
| 中国金融期货交易所 | CFFEX | `config/exchanges/cffex.yml` |
| 广州期货交易所 | GFEX | `config/exchanges/gfex.yml` |
| 上海国际能源交易中心 | INE | `config/exchanges/ine.yml` |

### 夜盘日历 (M15)
```python
from src.market import TradingCalendar

calendar = TradingCalendar()

# 检查是否夜盘时间
is_night = calendar.is_night_session()

# 获取下一个交易日
next_day = calendar.next_trading_day()

# 检查节假日
is_holiday = calendar.is_holiday("2024-10-01")
```

---

## 使用示例

```python
from src.market import (
    QuoteSubscriber,
    QuoteCache,
    load_exchange_config
)

# 1. 加载交易所配置
shfe_config = load_exchange_config("shfe")

# 2. 创建订阅器
subscriber = QuoteSubscriber(config)

# 3. 订阅合约
subscriber.subscribe(["rb2405", "rb2410"])

# 4. 获取行情
cache = QuoteCache()
tick = cache.get_latest("rb2405")
```

---

## 行情数据结构

```python
@dataclass
class Tick:
    symbol: str           # 合约代码
    exchange: str         # 交易所
    last_price: float     # 最新价
    bid_price: float      # 买一价
    ask_price: float      # 卖一价
    bid_volume: int       # 买一量
    ask_volume: int       # 卖一量
    volume: int           # 成交量
    open_interest: float  # 持仓量
    timestamp: datetime   # 时间戳
```

---

## 依赖关系

```
market/
    │
    ├──▶ strategy/   (提供行情)
    ├──▶ execution/  (提供行情)
    ├──▶ risk/       (提供行情)
    └──▶ audit/      (行情记录)
```

---

**军规级别国家伟大工程 - 行情模块规范**
