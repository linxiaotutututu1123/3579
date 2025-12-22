# 性能监控工作流

> **类型**: 辅助工作流 | **等级**: SUPREME

```yaml
工作流: PerformanceMonitoringWorkflow
参与Agent: 性能调优师, DevOps大师, 量化架构师
触发条件: 持续运行/性能告警
```

## 监控维度

```python
MONITORING_DIMENSIONS = {
    "系统性能": {
        "CPU": "使用率/负载",
        "内存": "使用率/泄漏",
        "IO": "读写延迟",
        "网络": "带宽/延迟",
    },
    "应用性能": {
        "响应时间": "P50/P95/P99",
        "吞吐量": "QPS/TPS",
        "错误率": "4xx/5xx",
    },
    "业务性能": {
        "策略延迟": "信号→执行",
        "执行延迟": "下单→成交",
        "滑点": "实际vs预期",
    },
}

ALERT_THRESHOLDS = {
    "warning": "性能下降20%",
    "critical": "性能下降50%",
    "emergency": "服务不可用",
}
```
