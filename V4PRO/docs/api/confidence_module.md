# 置信度评估模块 API 文档

> V4PRO Platform - 置信度评估系统 v4.3
>
> 军规覆盖: M3 (完整审计), M19 (风险归因)

## 概述

置信度评估模块提供预执行置信度检查和信号置信度评估功能，集成 superclaude ConfidenceChecker 模式与 V4PRO 信号系统，确保交易决策具有充分的置信度支持。

### 核心功能

| 功能 | 场景代码 | 说明 |
|------|----------|------|
| 预执行检查 | K50 | 策略执行前的置信度验证 |
| 信号评估 | K51 | 交易信号的置信度评估 |
| 审计追踪 | K52 | 置信度评估的完整审计日志 |

### 置信度等级

| 等级 | 分数范围 | 行动建议 |
|------|----------|----------|
| HIGH | ≥90% | 可直接执行 |
| MEDIUM | 70-89% | 需要确认或替代方案 |
| LOW | <70% | 停止并调查 |

---

## 快速开始

### 基础用法

```python
from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceContext,
    TaskType,
)

# 创建评估器
assessor = ConfidenceAssessor()

# 创建评估上下文
context = ConfidenceContext(
    task_type=TaskType.STRATEGY_EXECUTION,
    task_name="kalman_arbitrage",
    duplicate_check_complete=True,
    architecture_verified=True,
    has_official_docs=True,
    has_oss_reference=True,
    root_cause_identified=True,
)

# 执行评估
result = assessor.assess(context)

# 检查是否可以继续
if result.can_proceed:
    execute_strategy()
else:
    print(f"置信度不足: {result.recommendation}")
```

### 便捷函数

```python
from src.risk.confidence import assess_pre_execution, assess_signal

# 预执行评估
result = assess_pre_execution(
    "my_strategy",
    duplicate_check=True,
    architecture_verified=True,
    has_docs=True,
    has_oss=True,
    root_cause=True,
)

# 信号评估
result = assess_signal(
    symbol="rb2501",
    strategy_id="kalman_arb",
    strength=0.8,
    consistency=0.85,
    market_condition="NORMAL",
    risk_ok=True,
)
```

---

## API 参考

### TaskType 枚举

任务类型定义。

```python
class TaskType(Enum):
    STRATEGY_EXECUTION = "STRATEGY_EXECUTION"   # 策略执行
    SIGNAL_GENERATION = "SIGNAL_GENERATION"     # 信号生成
    RISK_ASSESSMENT = "RISK_ASSESSMENT"         # 风险评估
    ORDER_PLACEMENT = "ORDER_PLACEMENT"         # 下单操作
    POSITION_ADJUSTMENT = "POSITION_ADJUSTMENT" # 仓位调整
```

### ConfidenceLevel 枚举

置信度等级定义。

```python
class ConfidenceLevel(Enum):
    HIGH = "HIGH"     # ≥90% - 可直接执行
    MEDIUM = "MEDIUM" # 70-89% - 需要确认
    LOW = "LOW"       # <70% - 停止并调查
```

---

### ConfidenceContext 数据类

评估上下文，包含所有检查项的输入数据。

#### 属性

##### 基础属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `task_type` | `TaskType` | 必填 | 任务类型 |
| `task_name` | `str` | `""` | 任务名称 |
| `symbol` | `str` | `""` | 合约代码 |
| `strategy_id` | `str` | `""` | 策略ID |

##### 预执行检查项 (superclaude 模式)

| 属性 | 类型 | 默认值 | 权重 | 说明 |
|------|------|--------|------|------|
| `duplicate_check_complete` | `bool` | `False` | 25% | 是否完成重复检查 |
| `architecture_verified` | `bool` | `False` | 25% | 是否验证架构合规 |
| `has_official_docs` | `bool` | `False` | 20% | 是否有官方文档 |
| `has_oss_reference` | `bool` | `False` | 15% | 是否有OSS参考 |
| `root_cause_identified` | `bool` | `False` | 15% | 是否识别根因 |

##### 信号检查项 (V4PRO 模式)

| 属性 | 类型 | 默认值 | 权重 | 说明 |
|------|------|--------|------|------|
| `signal_strength` | `float` | `0.0` | 30% | 信号强度 (0.0-1.0) |
| `signal_consistency` | `float` | `0.0` | 25% | 信号一致性 (0.0-1.0) |
| `market_condition` | `str` | `"NORMAL"` | 25% | 市场状态 |
| `risk_within_limits` | `bool` | `True` | 20% | 风险是否在限制内 |

##### 扩展检查项 (v4.3 增强)

| 属性 | 类型 | 默认值 | 权重 | 说明 |
|------|------|--------|------|------|
| `volatility` | `float` | `0.0` | 15% | 市场波动率 (0.0-1.0) |
| `liquidity_score` | `float` | `1.0` | 15% | 流动性评分 (0.0-1.0) |
| `historical_win_rate` | `float` | `0.5` | 10% | 策略历史胜率 |
| `position_concentration` | `float` | `0.0` | 10% | 持仓集中度 |

##### 元数据

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `metadata` | `dict[str, Any]` | `{}` | 附加元数据 |

#### 示例

```python
# 预执行评估上下文
pre_exec_context = ConfidenceContext(
    task_type=TaskType.STRATEGY_EXECUTION,
    task_name="trend_following",
    duplicate_check_complete=True,
    architecture_verified=True,
    has_official_docs=True,
    has_oss_reference=True,
    root_cause_identified=True,
)

# 信号评估上下文
signal_context = ConfidenceContext(
    task_type=TaskType.SIGNAL_GENERATION,
    symbol="rb2501",
    strategy_id="kalman_arb",
    signal_strength=0.85,
    signal_consistency=0.80,
    market_condition="NORMAL",
    risk_within_limits=True,
)

# 完整上下文 (组合评估)
full_context = ConfidenceContext(
    task_type=TaskType.RISK_ASSESSMENT,
    # 预执行检查项
    duplicate_check_complete=True,
    architecture_verified=True,
    has_official_docs=True,
    has_oss_reference=True,
    root_cause_identified=True,
    # 信号检查项
    signal_strength=0.8,
    signal_consistency=0.85,
    risk_within_limits=True,
    # 扩展检查项
    volatility=0.15,
    liquidity_score=0.9,
    historical_win_rate=0.62,
    position_concentration=0.25,
)
```

---

### ConfidenceResult 数据类

评估结果 (不可变)。

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `score` | `float` | 置信度分数 (0.0-1.0) |
| `level` | `ConfidenceLevel` | 置信度等级 |
| `can_proceed` | `bool` | 是否可以继续 |
| `checks` | `tuple[ConfidenceCheck, ...]` | 各项检查结果 |
| `recommendation` | `str` | 建议操作 |
| `timestamp` | `str` | ISO格式时间戳 |
| `context_summary` | `dict[str, Any]` | 上下文摘要 |

#### 属性方法

```python
@property
def passed_checks(self) -> list[ConfidenceCheck]:
    """获取通过的检查项."""

@property
def failed_checks(self) -> list[ConfidenceCheck]:
    """获取失败的检查项."""
```

#### 方法

##### `to_audit_dict() -> dict[str, Any]`

转换为审计日志格式 (M3 军规)。

```python
result = assessor.assess(context)
audit_log = result.to_audit_dict()

# 输出示例:
# {
#     "event_type": "CONFIDENCE_ASSESSMENT",
#     "score": 0.9500,
#     "level": "HIGH",
#     "can_proceed": True,
#     "checks": [...],
#     "recommendation": "✅ 高置信度 (≥90%) - 可直接执行",
#     "timestamp": "2025-12-21T10:30:00",
#     "context_summary": {...}
# }
```

---

### ConfidenceAssessor 类

置信度评估器 (军规 M3/M19)。

#### 构造函数

```python
def __init__(
    self,
    high_threshold: float = 0.90,
    medium_threshold: float = 0.70,
    adaptive_mode: bool = False,
) -> None:
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `high_threshold` | `float` | `0.90` | 高置信度阈值 |
| `medium_threshold` | `float` | `0.70` | 中等置信度阈值 |
| `adaptive_mode` | `bool` | `False` | 是否启用自适应阈值模式 |

#### 核心方法

##### `assess(context: ConfidenceContext) -> ConfidenceResult`

执行置信度评估。

```python
assessor = ConfidenceAssessor()
result = assessor.assess(context)

print(f"置信度: {result.score:.0%}")
print(f"等级: {result.level.value}")
print(f"可继续: {result.can_proceed}")
```

##### `get_statistics() -> dict[str, Any]`

获取统计信息。

```python
stats = assessor.get_statistics()

# 返回:
# {
#     "total_assessments": 100,
#     "high_confidence_count": 75,
#     "medium_confidence_count": 20,
#     "low_confidence_count": 5,
#     "high_rate": 0.75,
#     "medium_rate": 0.20,
#     "low_rate": 0.05,
# }
```

##### `reset_statistics() -> None`

重置统计信息和历史记录。

```python
assessor.reset_statistics()
```

#### 自适应阈值方法 (v4.3)

##### `get_adaptive_thresholds(context: ConfidenceContext) -> tuple[float, float]`

根据市场状态获取动态调整的阈值。

**调整规则:**

| 条件 | 高阈值调整 | 中阈值调整 |
|------|-----------|-----------|
| 波动率 > 0.3 | +5% (最大) | +5% (最大) |
| 流动性 < 0.6 | +3% (最大) | +3% (最大) |
| 异常市场状态 | +5% | +5% |

**异常市场状态:** `VOLATILE`, `CRISIS`, `LIMIT_UP`, `LIMIT_DOWN`

```python
assessor = ConfidenceAssessor(adaptive_mode=True)

context = ConfidenceContext(
    task_type=TaskType.STRATEGY_EXECUTION,
    volatility=0.5,
    market_condition="VOLATILE",
)

high_thresh, medium_thresh = assessor.get_adaptive_thresholds(context)
# high_thresh ≈ 0.95+ (因高波动和异常市场)
```

#### 趋势分析方法 (v4.3)

##### `get_trend_analysis() -> dict[str, Any]`

分析置信度历史趋势，提供预警信息。

```python
assessor = ConfidenceAssessor()

# 执行多次评估后...
trend = assessor.get_trend_analysis()

# 返回:
# {
#     "trend": "STABLE" | "IMPROVING" | "DECLINING" | "INSUFFICIENT_DATA",
#     "message": "趋势: STABLE | 方向: NEUTRAL",
#     "recent_avg": 0.8500,
#     "overall_avg": 0.8200,
#     "direction": "UP" | "DOWN" | "NEUTRAL",
#     "alert": False,
#     "alert_message": "",
#     "history_count": 50,
# }
```

**预警触发条件:**

| 条件 | 预警消息 |
|------|----------|
| 连续3次下降 | ⚠️ 置信度连续下降 |
| 近期平均 < 70% | ❌ 近期置信度持续偏低 |

---

## 便捷函数

### `assess_pre_execution()`

快速预执行置信度评估。

```python
def assess_pre_execution(
    task_name: str,
    *,
    duplicate_check: bool = False,
    architecture_verified: bool = False,
    has_docs: bool = False,
    has_oss: bool = False,
    root_cause: bool = False,
) -> ConfidenceResult:
```

### `assess_signal()`

快速信号置信度评估。

```python
def assess_signal(
    symbol: str,
    strategy_id: str,
    *,
    strength: float = 0.0,
    consistency: float = 0.0,
    market_condition: str = "NORMAL",
    risk_ok: bool = True,
) -> ConfidenceResult:
```

### `format_confidence_report()`

格式化置信度报告。

```python
def format_confidence_report(result: ConfidenceResult) -> str:
```

**输出示例:**

```
📋 置信度评估报告
========================================

   ✅ 无重复实现
   ✅ 架构合规
   ✅ 官方文档已验证
   ✅ OSS参考已找到
   ✅ 根因已识别

📊 置信度: 100%
✅ 高置信度 (≥90%) - 可直接执行
```

---

## 评估模式

### 预执行模式

适用于 `STRATEGY_EXECUTION` 和 `ORDER_PLACEMENT` 任务类型。

**检查项权重分配:**

| 检查项 | 权重 | 通过条件 |
|--------|------|----------|
| 无重复实现 | 25% | `duplicate_check_complete = True` |
| 架构合规 | 25% | `architecture_verified = True` |
| 官方文档 | 20% | `has_official_docs = True` |
| OSS参考 | 15% | `has_oss_reference = True` |
| 根因识别 | 15% | `root_cause_identified = True` |

### 信号模式

适用于 `SIGNAL_GENERATION` 任务类型。

**检查项权重分配:**

| 检查项 | 权重 | 通过条件 |
|--------|------|----------|
| 信号强度 | 30% | `signal_strength ≥ 0.5` |
| 信号一致性 | 25% | `signal_consistency ≥ 0.6` |
| 市场状态 | 25% | `market_condition ∈ {NORMAL, TRENDING, RANGE}` |
| 风险限制 | 20% | `risk_within_limits = True` |

### 组合模式

适用于 `RISK_ASSESSMENT` 和 `POSITION_ADJUSTMENT` 任务类型。

**权重分配:** 预执行 40% + 信号 40% + 扩展 20%

### 扩展检查模式 (v4.3)

**检查项权重分配:**

| 检查项 | 权重 | 通过条件 |
|--------|------|----------|
| 波动率 | 15% | `volatility ≤ 0.3` |
| 流动性 | 15% | `liquidity_score ≥ 0.6` |
| 历史胜率 | 10% | `historical_win_rate ≥ 0.5` |
| 持仓集中度 | 10% | `position_concentration ≤ 0.5` |

---

## 使用场景

### 场景1: 策略执行前检查

```python
from src.risk.confidence import ConfidenceAssessor, ConfidenceContext, TaskType

def execute_with_confidence_check(strategy_name: str) -> bool:
    assessor = ConfidenceAssessor()

    context = ConfidenceContext(
        task_type=TaskType.STRATEGY_EXECUTION,
        task_name=strategy_name,
        duplicate_check_complete=True,
        architecture_verified=True,
        has_official_docs=True,
        has_oss_reference=True,
        root_cause_identified=True,
    )

    result = assessor.assess(context)

    if result.can_proceed:
        # 执行策略
        return True
    else:
        # 记录失败原因
        for check in result.failed_checks:
            logger.warning(f"检查失败: {check.message}")
        return False
```

### 场景2: 高波动市场的自适应评估

```python
assessor = ConfidenceAssessor(adaptive_mode=True)

context = ConfidenceContext(
    task_type=TaskType.SIGNAL_GENERATION,
    symbol="rb2501",
    signal_strength=0.82,
    signal_consistency=0.78,
    volatility=0.45,  # 高波动
    market_condition="VOLATILE",
)

result = assessor.assess(context)

# 自适应模式下，阈值会自动提高
# 原本 82% 可能是 MEDIUM，但高波动下可能变为 LOW
print(f"当前阈值: {result.context_summary['thresholds']}")
```

### 场景3: 置信度趋势监控

```python
assessor = ConfidenceAssessor()

# 模拟多次评估
for signal in signals:
    context = create_context_from_signal(signal)
    result = assessor.assess(context)

# 分析趋势
trend = assessor.get_trend_analysis()

if trend["alert"]:
    send_alert(
        title="置信度预警",
        message=trend["alert_message"],
        recent_avg=trend["recent_avg"],
    )
```

### 场景4: 审计日志集成

```python
import json
from src.risk.confidence import ConfidenceAssessor, ConfidenceContext, TaskType

assessor = ConfidenceAssessor()
context = ConfidenceContext(...)
result = assessor.assess(context)

# 转换为审计格式
audit_entry = result.to_audit_dict()

# 写入审计日志 (M3 军规)
with open("audit.log", "a") as f:
    f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")
```

---

## 故障排除

### 问题: 置信度始终为 LOW

**可能原因:**
1. 未设置必要的上下文字段
2. 使用了错误的任务类型

**解决方案:**

```python
# 检查上下文完整性
context = ConfidenceContext(
    task_type=TaskType.STRATEGY_EXECUTION,
    # 确保设置所有检查项
    duplicate_check_complete=True,  # 不要忘记!
    architecture_verified=True,
    has_official_docs=True,
    has_oss_reference=True,
    root_cause_identified=True,
)
```

### 问题: 自适应阈值未生效

**可能原因:** 未启用 `adaptive_mode`

**解决方案:**

```python
# 正确启用自适应模式
assessor = ConfidenceAssessor(adaptive_mode=True)  # 关键!
```

### 问题: 趋势分析返回 INSUFFICIENT_DATA

**可能原因:** 评估次数不足 (少于3次)

**解决方案:**

```python
# 确保至少执行3次评估
for _ in range(3):
    assessor.assess(context)

trend = assessor.get_trend_analysis()
# 现在应该返回有效趋势
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v4.3 | 2025-12-21 | 新增扩展检查项、自适应阈值、趋势分析 |
| v4.2 | 2025-11-15 | 信号置信度评估 |
| v4.1 | 2025-10-20 | 风险归因集成 |
| v4.0 | 2025-09-01 | 初始版本 |

---

## 相关文档

- [风险管理模块概述](./risk_module.md)
- [VaR 计算器 API](./var_calculator.md)
- [压力测试 API](./stress_test.md)
- [风险归因 API](./attribution.md)
