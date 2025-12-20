# V4PRO 交易控制模块 (trading/)

> **版本**: v4.0.0 军规级
> **军规覆盖**: M1-M9

---

## 模块职责

交易控制模块是V4PRO系统的**CI门禁和运行时控制中心**，负责：
- CHECK_MODE强制执行（M1核心）
- 退出码标准化管理
- 仿真/实盘环境隔离
- 交易生命周期编排

---

## 文件清单

| 文件 | 功能 | 军规覆盖 |
|------|------|----------|
| `ci_gate.py` | CI门禁核心，CHECK_MODE阻止实盘 | M1 |
| `sim_gate.py` | 仿真环境门禁 | M1,M8 |
| `live_guard.py` | 实盘保护层 | M1,M6 |
| `orchestrator.py` | 交易编排器，生命周期管理 | M9 |
| `serial_exec.py` | 串行执行引擎 | M1 |
| `controls.py` | 控制参数管理 | M4 |
| `events.py` | 交易事件定义 | M3 |
| `reconcile.py` | 对账模块 | M7 |
| `replay.py` | 回放接口 | M7 |
| `sim.py` | 仿真交易逻辑 | M8 |
| `utils.py` | 工具函数 | - |

---

## 核心概念

### CHECK_MODE (M1)
```python
from src.trading import enable_check_mode, is_check_mode

# CI/仿真环境必须启用
enable_check_mode()

# 检查当前模式
if is_check_mode():
    # 阻止实盘交易
    pass
```

### 退出码系统
| 退出码 | 常量 | 含义 |
|--------|------|------|
| 0 | SUCCESS | 正常退出 |
| 1 | GENERAL_ERROR | 通用错误 |
| 2 | CHECK_MODE_VIOLATION | CHECK_MODE被绕过 |
| 3 | CONFIG_ERROR | 配置错误 |
| 4 | STRATEGY_ERROR | 策略错误 |
| 5 | EXECUTION_ERROR | 执行错误 |
| 6 | RISK_CONFIG_FAIL | 风控配置失败 |

---

## 使用示例

```python
from src.trading import (
    ExitCode,
    enable_check_mode,
    is_check_mode,
    Orchestrator
)

# 1. 启用CHECK_MODE
enable_check_mode()

# 2. 创建编排器
orchestrator = Orchestrator(config)

# 3. 运行交易循环
exit_code = orchestrator.run()

# 4. 标准化退出
sys.exit(exit_code.value)
```

---

## 依赖关系

```
trading/
    │
    ├──▶ audit/      (事件记录)
    ├──▶ risk/       (风控检查)
    └──▶ execution/  (订单执行)
```

---

**军规级别国家伟大工程 - 交易控制模块规范**
