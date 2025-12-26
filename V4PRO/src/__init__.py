"""
V4PRO Trading Platform - 军规级中国期货交易系统 (v4.0).

顶级模块导出:
- trading: CI门禁、退出码、CHECK_MODE
- strategy: 策略框架、降级管理
- audit: 审计事件、JSONL写入
- replay: 回放验证器
- cost: 成本估计、手续费计算
- market: 行情订阅、交易所配置
- risk: 风控模块
- guardian: 守护者模块

Military-Grade Standards (军规级标准):
- M1-M20 全面合规
- 退出码 0-13 完整定义
- Schema v3 报告格式
- CHECK_MODE 强制执行

Usage:
    from src.trading import ExitCode, enable_check_mode
    from src.strategy import Strategy, FallbackManager
    from src.audit import AuditWriter, AuditEvent
"""

# Version
__version__ = "4.0.0"
__version_info__ = (4, 0, 0)

# Top-level exports for convenience
__all__ = [
    "__version__",
    "__version_info__",
]
