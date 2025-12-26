# 程序化交易合规报告模板 (D7-P1)

V4PRO Platform - Phase 9 合规监控
适用: 2025年《期货市场程序化交易管理规定》

---

## 1. 日报送模板 (Daily Report)

### 1.1 报告头

| 字段 | 说明 | 必填 |
|------|------|------|
| report_id | 报告唯一标识 (格式: RPT-XXXXXXXXXXXX) | Y |
| report_type | 报告类型 (DAILY) | Y |
| report_date | 报告日期 (YYYY-MM-DD) | Y |
| created_at | 创建时间 (ISO 8601) | Y |
| account_id | 账户ID | Y |
| exchange | 交易所代码 | Y |
| version | 报告版本 | Y |

### 1.2 交易概况

| 字段 | 说明 | 单位 |
|------|------|------|
| strategy_count | 策略数量 | 个 |
| total_orders | 总订单数 | 笔 |
| total_cancels | 总撤单数 | 笔 |
| total_trades | 总成交数 | 笔 |
| total_volume | 总成交量 | 手 |
| total_turnover | 总成交额 | 元 |

### 1.3 合规指标 (D7-P1 阈值)

| 字段 | 说明 | 阈值 | 单位 |
|------|------|------|------|
| cancel_ratio | 报撤单比例 | <=50% | 百分比 |
| max_cancel_freq | 最大撤单频率 | <=500 | 次/秒 |
| min_order_interval | 最小订单间隔 | >=100 | ms |
| max_audit_delay | 最大审计延迟 | <=1 | 秒 |
| max_orders_per_sec | 最大订单频率 | - | 笔/秒 |
| is_hft | 高频交易判定 | - | 布尔 |

### 1.4 违规记录

| 字段 | 说明 |
|------|------|
| violation_type | 违规类型 |
| violation_level | 违规级别 (INFO/WARNING/VIOLATION/CRITICAL) |
| message | 违规描述 |
| threshold | 阈值 |
| actual_value | 实际值 |
| timestamp | 发生时间 |
| military_rule | 关联军规 |

### 1.5 策略摘要

| 字段 | 说明 |
|------|------|
| strategy_id | 策略ID |
| strategy_type | 策略类型 |
| version | 策略版本 |
| is_active | 是否激活 |
| order_count | 订单数 |
| cancel_count | 撤单数 |

---

## 2. 异常报送模板 (Exception Report)

### 2.1 报告头

| 字段 | 说明 | 必填 |
|------|------|------|
| report_id | 报告唯一标识 | Y |
| report_type | 报告类型 (EXCEPTION) | Y |
| exception_time | 异常时间 | Y |
| account_id | 账户ID | Y |

### 2.2 异常详情

| 字段 | 说明 |
|------|------|
| exception_type | 异常类型 (SYSTEM_ERROR/COMPLIANCE_VIOLATION/NETWORK_ISSUE等) |
| strategy_id | 相关策略ID |
| description | 异常描述 |
| impact | 影响范围 |
| action_taken | 采取措施 |
| is_resolved | 是否已解决 |
| related_orders | 相关订单ID列表 |

### 2.3 异常类型编码

| 编码 | 类型 | 说明 |
|------|------|------|
| E001 | SYSTEM_ERROR | 系统错误 |
| E002 | NETWORK_ISSUE | 网络问题 |
| E003 | COMPLIANCE_VIOLATION | 合规违规 |
| E004 | STRATEGY_ERROR | 策略错误 |
| E005 | DATA_ANOMALY | 数据异常 |
| E006 | SECURITY_ALERT | 安全告警 |

---

## 3. 变更报送模板 (Change Report)

### 3.1 报告头

| 字段 | 说明 | 必填 |
|------|------|------|
| report_id | 报告唯一标识 | Y |
| report_type | 报告类型 (CHANGE) | Y |
| change_time | 变更时间 | Y |
| account_id | 账户ID | Y |

### 3.2 变更详情

| 字段 | 说明 |
|------|------|
| change_type | 变更类型 |
| old_value | 原值 |
| new_value | 新值 |
| reason | 变更原因 |
| changed_by | 变更人 |
| approved_by | 审批人 |

### 3.3 变更类型编码

| 编码 | 类型 | 说明 |
|------|------|------|
| C001 | STRATEGY_ADD | 新增策略 |
| C002 | STRATEGY_UPDATE | 更新策略 |
| C003 | STRATEGY_REMOVE | 移除策略 |
| C004 | PARAMETER_CHANGE | 参数变更 |
| C005 | RISK_LIMIT_CHANGE | 风控限制变更 |
| C006 | RESPONSIBLE_PERSON_CHANGE | 负责人变更 |

---

## 4. JSON 格式示例

### 4.1 日报送

```json
{
  "report_id": "RPT-A1B2C3D4E5F6",
  "report_type": "DAILY",
  "report_date": "2025-12-22",
  "created_at": "2025-12-22T16:30:00+08:00",
  "account_id": "ACC-001",
  "exchange": "SHFE",
  "content": {
    "strategy_count": 3,
    "total_orders": 1500,
    "total_cancels": 300,
    "total_trades": 1200,
    "cancel_ratio": 0.20,
    "max_cancel_freq": 50.0,
    "min_order_interval": 150.0,
    "max_audit_delay": 0.5,
    "max_orders_per_sec": 25.0,
    "is_hft": false,
    "violations": [],
    "warnings": [],
    "strategies_summary": [
      {
        "strategy_id": "trend_v1",
        "strategy_type": "TREND",
        "version": "1.0.0",
        "is_active": true
      }
    ]
  },
  "content_hash": "sha256:abc123...",
  "status": "SUBMITTED",
  "submitted_at": "2025-12-22T16:31:00+08:00"
}
```

### 4.2 异常报送

```json
{
  "report_id": "RPT-X1Y2Z3W4V5U6",
  "report_type": "EXCEPTION",
  "report_date": "2025-12-22",
  "created_at": "2025-12-22T14:25:30+08:00",
  "account_id": "ACC-001",
  "content": {
    "exception_type": "E003",
    "exception_time": "2025-12-22T14:25:00+08:00",
    "strategy_id": "arb_v2",
    "description": "报撤单比例超过50%阈值",
    "impact": "策略暂停",
    "action_taken": "降低撤单频率",
    "is_resolved": true,
    "related_orders": ["ORD-001", "ORD-002", "ORD-003"]
  },
  "status": "SUBMITTED"
}
```

---

## 5. 报送要求

### 5.1 时限要求

| 报送类型 | 时限 | 说明 |
|----------|------|------|
| 日报送 | T+1小时 | 每日交易结束后1小时内 |
| 异常报送 | T+15分钟 | 异常发生后15分钟内 |
| 变更报送 | T+24小时 | 变更后24小时内 |

### 5.2 军规合规

| 军规 | 要求 | 验证方式 |
|------|------|----------|
| M3 | 审计日志完整 | content_hash 校验 |
| M7 | 场景回放 | 数据可重放 |
| M17 | 程序化合规 | 阈值验证 |

### 5.3 安全要求

- 报告传输需加密 (TLS 1.3)
- 内容需数字签名
- 保留至少3年存档

---

## 6. 附录

### 6.1 交易所代码

| 代码 | 名称 |
|------|------|
| SHFE | 上海期货交易所 |
| DCE | 大连商品交易所 |
| CZCE | 郑州商品交易所 |
| CFFEX | 中国金融期货交易所 |
| INE | 上海国际能源交易中心 |
| GFEX | 广州期货交易所 |

### 6.2 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2025-12-22 | 初始版本 |

---

文档由 V4PRO 合规模块自动生成
军规级: M3, M7, M17
