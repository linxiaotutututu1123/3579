# V4PRO 配置目录说明 (Config Directory)

> **版本**: v4.0 军规级
> **军规覆盖**: M8 (环境隔离)

---

## 目录结构

```
config/
├── environments/           # 环境配置 (M8)
│   ├── dev.yml            # 开发环境
│   ├── sim.yml            # 仿真环境
│   └── live.yml           # 实盘环境 ⚠️ 敏感
│
├── exchanges/             # 交易所配置 (M20)
│   ├── shfe.yml           # 上海期货交易所
│   ├── dce.yml            # 大连商品交易所
│   ├── czce.yml           # 郑州商品交易所
│   ├── cffex.yml          # 中国金融期货交易所
│   ├── gfex.yml           # 广州期货交易所
│   └── ine.yml            # 上海国际能源交易中心
│
├── risk/                  # 风控配置 (M6/M16)
│   └── limits.yml         # 风控限额
│
├── strategies/            # 策略配置
│   └── calendar_arb.yml   # 日历套利策略
│
└── README.md              # 本文件
```

---

## 环境配置说明

### 开发环境 (dev.yml)
- **用途**: 本地开发、单元测试
- **CHECK_MODE**: 强制启用
- **Broker**: Mock
- **数据源**: 回放数据

### 仿真环境 (sim.yml)
- **用途**: 策略验证、门禁检查
- **CHECK_MODE**: 强制启用
- **Broker**: SimNow
- **数据源**: SimNow行情

### 实盘环境 (live.yml)
- **用途**: 真实交易
- **CHECK_MODE**: 禁用
- **Broker**: CTP
- **安全**: 敏感信息从环境变量读取

---

## 军规要求

| 军规 | 配置文件 | 要求 |
|------|----------|------|
| M6 | `risk/limits.yml` | 熔断保护必须配置 |
| M8 | `environments/*.yml` | 环境严格隔离 |
| M16 | `risk/limits.yml` | 保证金监控必须配置 |
| M20 | `exchanges/*.yml` | 六大交易所配置一致 |

---

## 使用方式

```python
from src.market import load_exchange_config

# 加载交易所配置
shfe_config = load_exchange_config("shfe")

# 加载环境配置
import yaml
with open("config/environments/dev.yml") as f:
    env_config = yaml.safe_load(f)
```

---

## 注意事项

1. **实盘配置** (`live.yml`) 敏感信息必须使用环境变量
2. **修改实盘配置** 需要双人审批 (M12)
3. **风控限额** 未配置将导致 Exit 6 (RISK_CONFIG_FAIL)

---

**军规级别国家伟大工程 - 配置管理规范**
