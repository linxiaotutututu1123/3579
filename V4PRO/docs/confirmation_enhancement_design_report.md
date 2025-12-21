# 分层确认机制增强设计报告

## 1. 概述

### 1.1 背景
根据 V4PRO_IMPROVEMENT_DESIGN_v1.2.md 中的 D2 设计要求，需要实现分层确认机制来解决 M12（双重确认）与全自动矛盾的问题。

### 1.2 设计目标
- 解决 M12 与全自动矛盾：分层确认机制
- 夜盘时段无人值守：降级处理
- 高频套利秒级决策：AUTO 级别豁免
- 极端行情：快速响应与确认并存
- 熔断集成：与 CircuitBreaker 状态机联动

## 2. 架构设计

### 2.1 确认级别定义

```python
class ConfirmationLevel(str, Enum):
    AUTO = "全自动"           # 无需确认
    SOFT_CONFIRM = "软确认"   # 系统二次校验
    HARD_CONFIRM = "硬确认"   # 人工介入
```

### 2.2 订单金额阈值

| 级别 | 金额范围 | 处理方式 |
|------|----------|----------|
| AUTO | < 50万 | 全自动执行 |
| SOFT_CONFIRM | 50万 - 200万 | 系统二次校验 |
| HARD_CONFIRM | > 200万 | 人工介入确认 |

### 2.3 时段规则

| 时段 | 确认级别 | 说明 |
|------|----------|------|
| 日盘 (09:00-15:00) | AUTO | 正常交易时段 |
| 夜盘 (21:00-02:30) | SOFT_CONFIRM | 无人值守时段 |
| 波动时段 (开盘/收盘) | HARD_CONFIRM | 高风险时段 |

### 2.4 策略规则

| 策略类型 | 确认级别 | 说明 |
|----------|----------|------|
| HIGH_FREQUENCY | AUTO | 高频策略豁免 |
| PRODUCTION | SOFT_CONFIRM | 生产策略 |
| EXPERIMENTAL | HARD_CONFIRM | 实验策略 |

## 3. 增强功能实现

### 3.1 熔断器集成

#### 3.1.1 熔断状态检查
确认流程开始前检查熔断器状态：
- CLOSED: 正常执行确认流程
- OPEN: 阻止新订单确认（除高频策略豁免）
- HALF_OPEN: 允许确认但自动升级确认级别

```python
def _check_circuit_breaker_state(self) -> tuple[bool, str]:
    if current_state == CircuitBreakerState.OPEN:
        if self._cb_config.block_on_circuit_break:
            return False, "熔断器已触发,阻止新确认"
    return True, "允许确认"
```

#### 3.1.2 硬确认超时触发熔断
日盘硬确认超时自动触发熔断器：

```python
async def _trigger_circuit_breaker(self, confirmation_id, context, reason):
    if self._circuit_breaker_trigger:
        await self._circuit_breaker_trigger(reason, metadata)
```

### 3.2 高频策略豁免

#### 3.2.1 豁免条件
```python
@dataclass
class HighFrequencyExemptionConfig:
    enable_exemption: bool = True
    max_order_value_for_exemption: float = 100_000  # 10万
    max_position_ratio: float = 0.05  # 5%
    allowed_symbols: list[str] = field(default_factory=list)
    min_strategy_score: int = 80
```

#### 3.2.2 豁免逻辑
1. 策略类型必须是 HIGH_FREQUENCY
2. 订单金额不超过豁免上限（10万）
3. 合约必须在白名单中（如果配置了白名单）

### 3.3 恢复期确认升级

熔断器处于 HALF_OPEN 状态时，自动升级确认级别：
- AUTO -> SOFT_CONFIRM
- SOFT_CONFIRM -> HARD_CONFIRM

```python
def _upgrade_confirmation_level_for_recovery(self, level, reasons):
    if self._is_in_recovery_period():
        if level == ConfirmationLevel.AUTO:
            return ConfirmationLevel.SOFT_CONFIRM
        elif level == ConfirmationLevel.SOFT_CONFIRM:
            return ConfirmationLevel.HARD_CONFIRM
    return level
```

## 4. 军规合规

### 4.1 M5 成本先行
- 软确认包含成本检查（M5_COST_CHECK）
- 超时自动通过保证交易效率

### 4.2 M6 熔断保护
- 硬确认超时触发熔断器
- 熔断状态下阻止新订单确认
- 恢复期自动升级确认级别

### 4.3 M12 双重确认
- 三层确认机制：AUTO/SOFT/HARD
- 大额订单强制硬确认
- 用户确认回调机制

### 4.4 M13 涨跌停感知
- 软确认包含涨跌停检查（M13_LIMIT_CHECK）
- 涨停时禁止买入，跌停时禁止卖出

### 4.5 M15 夜盘规则
- 夜盘时段自动升级为软确认
- 夜盘硬确认超时降级为软确认

### 4.6 M17 程序化合规
- 高频策略豁免机制
- 合约白名单控制
- 订单金额上限控制

## 5. 文件清单

| 文件路径 | 说明 |
|----------|------|
| `src/execution/confirmation.py` | 基础分层确认机制实现 |
| `src/execution/confirmation_enhanced.py` | 熔断器集成增强实现 |
| `tests/execution/test_confirmation.py` | 基础功能测试 |
| `tests/execution/test_confirmation_enhanced.py` | 增强功能测试 |

## 6. 使用示例

### 6.1 基础用法

```python
from src.execution import (
    ConfirmationManager,
    ConfirmationContext,
    ConfirmationConfig,
    SessionType,
    StrategyType,
    MarketCondition,
)
from src.execution.order_types import OrderIntent, Side, Offset

# 创建订单意图
order = OrderIntent(
    symbol="IF2401",
    side=Side.BUY,
    offset=Offset.OPEN,
    price=3800.0,
    qty=10,
)

# 创建确认上下文
context = ConfirmationContext(
    order_intent=order,
    order_value=500_000,  # 50万
    market_condition=MarketCondition(),
    session_type=SessionType.DAY_SESSION,
    strategy_type=StrategyType.PRODUCTION,
)

# 执行确认
manager = ConfirmationManager()
decision = await manager.confirm(context)

if decision.result == ConfirmationResult.APPROVED:
    # 执行订单
    pass
```

### 6.2 熔断器集成

```python
from src.execution import (
    create_enhanced_confirmation_manager,
)
from src.guardian import CircuitBreaker

# 创建熔断器
circuit_breaker = CircuitBreaker()

# 创建增强版确认管理器
manager = create_enhanced_confirmation_manager(
    circuit_breaker=circuit_breaker,
    enable_circuit_breaker_integration=True,
)

# 执行确认（自动检查熔断状态）
decision = await manager.confirm(context)
```

## 7. 测试覆盖

### 7.1 基础测试（test_confirmation.py）
- ConfirmationLevel 枚举测试
- 订单金额阈值测试
- 市场条件阈值测试
- 时段规则测试
- 策略规则测试
- SoftConfirmation 测试
- HardConfirmation 测试
- 审计日志集成测试
- 军规合规测试

### 7.2 增强测试（test_confirmation_enhanced.py）
- 熔断器集成测试
- 熔断状态检查测试
- 硬确认超时触发熔断测试
- 高频策略豁免测试
- 恢复期确认级别升级测试
- 工厂函数测试
- 边界情况测试

## 8. 总结

本次增强实现了 D2 设计规范要求的分层确认机制，并与熔断器状态机完整集成。主要特性：

1. **三层确认机制**：AUTO/SOFT_CONFIRM/HARD_CONFIRM
2. **熔断器集成**：确认前状态检查、超时触发熔断
3. **高频策略豁免**：支持订单金额和合约白名单控制
4. **恢复期级别升级**：自动提升确认级别
5. **完整审计日志**：所有操作可追溯

军规合规覆盖：M5、M6、M12、M13、M15、M17
