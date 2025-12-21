"""
程序化交易监管报送模块 - Reporter (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.REPORT: 监管报送
- CHINA.COMPLIANCE.AUDIT_INTEGRATION: 审计集成

军规覆盖:
- M3: 审计日志完整 - 报送记录必须完整保存
- M7: 场景回放 - 支持报送场景回放
- M17: 程序化合规 - 程序化交易报送必须及时

功能特性:
- 日报送 (Daily Report)
- 异常报送 (Exception Report)
- 变更报送 (Change Report)
- 多格式导出 (JSON/XML/CSV)
- 审计日志集成

报送规则 (2025年《期货市场程序化交易管理规定》):
- 每日交易结束后1小时内完成日报送
- 异常情况发生后15分钟内完成报送
- 策略变更24小时内完成报送

示例:
    >>> from src.compliance.registration.reporter import (
    ...     RegulatoryReporter,
    ...     ReportType,
    ... )
    >>> reporter = RegulatoryReporter(registry, validator)
    >>> report = reporter.generate_daily_report()
    >>> reporter.submit_report(report)
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class ReportType(Enum):
    """报送类型枚举."""

    DAILY = "DAILY"  # 日报送
    EXCEPTION = "EXCEPTION"  # 异常报送
    CHANGE = "CHANGE"  # 变更报送
    REGISTRATION = "REGISTRATION"  # 备案报送
    QUERY = "QUERY"  # 查询报送


class ReportFormat(Enum):
    """报告格式枚举."""

    JSON = "JSON"
    XML = "XML"
    CSV = "CSV"
    TEXT = "TEXT"


class ReportStatus(Enum):
    """报送状态枚举."""

    PENDING = "PENDING"  # 待发送
    SUBMITTED = "SUBMITTED"  # 已提交
    ACCEPTED = "ACCEPTED"  # 已接收
    REJECTED = "REJECTED"  # 已拒绝
    FAILED = "FAILED"  # 发送失败


@dataclass
class ReportRecord:
    """报送记录.

    属性:
        report_id: 报告ID
        report_type: 报告类型
        report_date: 报告日期
        created_at: 创建时间
        submitted_at: 提交时间
        status: 报送状态
        status_message: 状态消息
        content: 报告内容
        content_hash: 内容哈希
        account_id: 账户ID
        exchange: 交易所
        retry_count: 重试次数
        metadata: 元数据
    """

    report_id: str
    report_type: ReportType
    report_date: date
    created_at: str
    submitted_at: str = ""
    status: ReportStatus = ReportStatus.PENDING
    status_message: str = ""
    content: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    account_id: str = ""
    exchange: str = ""
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "report_id": self.report_id,
            "report_type": self.report_type.value,
            "report_date": self.report_date.isoformat(),
            "created_at": self.created_at,
            "submitted_at": self.submitted_at,
            "status": self.status.value,
            "status_message": self.status_message,
            "content": self.content,
            "content_hash": self.content_hash,
            "account_id": self.account_id,
            "exchange": self.exchange,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class DailyReportContent:
    """日报送内容.

    属性:
        report_date: 报告日期
        account_id: 账户ID
        strategy_count: 策略数量
        total_orders: 总订单数
        total_cancels: 总撤单数
        total_trades: 总成交数
        cancel_ratio: 报撤单比例
        max_cancel_freq: 最大撤单频率
        max_orders_per_sec: 最大订单频率
        min_order_interval_ms: 最小订单间隔
        max_audit_delay_sec: 最大审计延迟
        violations: 违规列表
        warnings: 预警列表
        is_hft: 是否高频交易
        strategies_summary: 策略摘要
    """

    report_date: date
    account_id: str
    strategy_count: int = 0
    total_orders: int = 0
    total_cancels: int = 0
    total_trades: int = 0
    cancel_ratio: float = 0.0
    max_cancel_freq: float = 0.0
    max_orders_per_sec: float = 0.0
    min_order_interval_ms: float = 0.0
    max_audit_delay_sec: float = 0.0
    violations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    is_hft: bool = False
    strategies_summary: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExceptionReportContent:
    """异常报送内容.

    属性:
        exception_type: 异常类型
        exception_time: 异常时间
        account_id: 账户ID
        strategy_id: 策略ID
        description: 异常描述
        impact: 影响范围
        action_taken: 采取措施
        is_resolved: 是否已解决
        related_orders: 相关订单
    """

    exception_type: str
    exception_time: str
    account_id: str
    strategy_id: str = ""
    description: str = ""
    impact: str = ""
    action_taken: str = ""
    is_resolved: bool = False
    related_orders: list[str] = field(default_factory=list)


class RegulatoryReporter:
    """监管报送器 (军规 M3, M7, M17).

    功能:
    - 生成日报送
    - 生成异常报送
    - 生成变更报送
    - 多格式导出
    - 报送状态追踪
    - 审计日志集成

    示例:
        >>> reporter = RegulatoryReporter(registry, validator)
        >>> daily_report = reporter.generate_daily_report("acc_001")
        >>> reporter.submit_report(daily_report)
    """

    VERSION = "4.0"

    def __init__(
        self,
        registry: Any = None,
        validator: Any = None,
        storage_path: str | Path | None = None,
        audit_callback: Callable[[dict[str, Any]], None] | None = None,
        submit_callback: Callable[[ReportRecord], bool] | None = None,
    ) -> None:
        """初始化监管报送器.

        参数:
            registry: 备案登记中心 (可选)
            validator: 合规验证器 (可选)
            storage_path: 存储路径 (可选)
            audit_callback: 审计回调函数 (可选)
            submit_callback: 报送回调函数 (可选)
        """
        self._registry = registry
        self._validator = validator
        self._storage_path = Path(storage_path) if storage_path else None
        self._audit_callback = audit_callback
        self._submit_callback = submit_callback

        # 报送记录
        self._reports: dict[str, ReportRecord] = {}
        self._daily_reports: dict[str, str] = {}  # date -> report_id

        # 统计
        self._report_count: int = 0
        self._submit_count: int = 0
        self._success_count: int = 0
        self._failure_count: int = 0

    @property
    def report_count(self) -> int:
        """获取报告数量."""
        return len(self._reports)

    def generate_daily_report(
        self,
        account_id: str,
        report_date: date | None = None,
        timestamp: datetime | None = None,
    ) -> ReportRecord:
        """生成日报送.

        参数:
            account_id: 账户ID
            report_date: 报告日期 (None使用今天)
            timestamp: 生成时间

        返回:
            报送记录

        异常:
            ValueError: 账户不存在
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005
        if report_date is None:
            report_date = timestamp.date()

        # 获取备案信息
        registration = None
        strategies = []
        if self._registry:
            registration = self._registry.get_registration(account_id)
            if registration is None:
                raise ValueError(f"账户 {account_id} 不存在备案记录")
            strategies = self._registry.get_account_strategies(account_id)

        # 获取合规指标
        metrics = None
        validator_stats = {}
        if self._validator:
            metrics = self._validator.get_current_metrics()
            validator_stats = self._validator.get_statistics()

        # 构建报告内容
        content = DailyReportContent(
            report_date=report_date,
            account_id=account_id,
            strategy_count=len(strategies),
            total_orders=validator_stats.get("total_orders", 0),
            total_cancels=validator_stats.get("total_cancels", 0),
            cancel_ratio=metrics.cancel_ratio if metrics else 0.0,
            max_cancel_freq=metrics.cancel_freq_per_sec if metrics else 0.0,
            max_orders_per_sec=metrics.orders_per_sec if metrics else 0.0,
            min_order_interval_ms=metrics.avg_order_interval_ms if metrics else 0.0,
            max_audit_delay_sec=metrics.max_audit_delay_sec if metrics else 0.0,
            is_hft=metrics.is_hft if metrics else False,
            strategies_summary=[
                {
                    "strategy_id": s.strategy_id,
                    "strategy_type": s.strategy_type,
                    "version": s.version,
                    "is_active": s.is_active,
                }
                for s in strategies
            ],
        )

        # 生成报告ID
        report_id = self._generate_report_id(
            ReportType.DAILY, account_id, report_date, timestamp
        )

        # 计算内容哈希
        content_dict = self._content_to_dict(content)
        content_hash = self._compute_hash(content_dict)

        # 创建报送记录
        report = ReportRecord(
            report_id=report_id,
            report_type=ReportType.DAILY,
            report_date=report_date,
            created_at=timestamp.isoformat(),
            content=content_dict,
            content_hash=content_hash,
            account_id=account_id,
            metadata={
                "registration_id": registration.registration_id if registration else "",
                "reporter_version": self.VERSION,
            },
        )

        # 存储
        self._reports[report_id] = report
        self._daily_reports[report_date.isoformat()] = report_id
        self._report_count += 1

        # 审计日志
        self._emit_audit_event(
            event_type="DAILY_REPORT_GENERATED",
            report_id=report_id,
            account_id=account_id,
            details={"report_date": report_date.isoformat()},
            timestamp=timestamp,
        )

        # 持久化
        self._save_report(report)

        logger.info(f"日报送生成: {report_id} for {account_id}")
        return report

    def generate_exception_report(
        self,
        account_id: str,
        exception_type: str,
        description: str,
        strategy_id: str = "",
        impact: str = "",
        action_taken: str = "",
        related_orders: list[str] | None = None,
        timestamp: datetime | None = None,
    ) -> ReportRecord:
        """生成异常报送.

        参数:
            account_id: 账户ID
            exception_type: 异常类型
            description: 异常描述
            strategy_id: 策略ID
            impact: 影响范围
            action_taken: 采取措施
            related_orders: 相关订单
            timestamp: 生成时间

        返回:
            报送记录
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        # 构建报告内容
        content = ExceptionReportContent(
            exception_type=exception_type,
            exception_time=timestamp.isoformat(),
            account_id=account_id,
            strategy_id=strategy_id,
            description=description,
            impact=impact,
            action_taken=action_taken,
            is_resolved=False,
            related_orders=related_orders or [],
        )

        # 生成报告ID
        report_id = self._generate_report_id(
            ReportType.EXCEPTION, account_id, timestamp.date(), timestamp
        )

        # 计算内容哈希
        content_dict = self._exception_content_to_dict(content)
        content_hash = self._compute_hash(content_dict)

        # 创建报送记录
        report = ReportRecord(
            report_id=report_id,
            report_type=ReportType.EXCEPTION,
            report_date=timestamp.date(),
            created_at=timestamp.isoformat(),
            content=content_dict,
            content_hash=content_hash,
            account_id=account_id,
            metadata={
                "exception_type": exception_type,
                "reporter_version": self.VERSION,
            },
        )

        # 存储
        self._reports[report_id] = report
        self._report_count += 1

        # 审计日志
        self._emit_audit_event(
            event_type="EXCEPTION_REPORT_GENERATED",
            report_id=report_id,
            account_id=account_id,
            details={
                "exception_type": exception_type,
                "description": description,
            },
            timestamp=timestamp,
        )

        # 持久化
        self._save_report(report)

        logger.warning(f"异常报送生成: {report_id} - {exception_type}")
        return report

    def generate_change_report(
        self,
        account_id: str,
        change_type: str,
        old_value: str,
        new_value: str,
        reason: str = "",
        changed_by: str = "",
        timestamp: datetime | None = None,
    ) -> ReportRecord:
        """生成变更报送.

        参数:
            account_id: 账户ID
            change_type: 变更类型
            old_value: 原值
            new_value: 新值
            reason: 变更原因
            changed_by: 变更人
            timestamp: 生成时间

        返回:
            报送记录
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        # 生成报告ID
        report_id = self._generate_report_id(
            ReportType.CHANGE, account_id, timestamp.date(), timestamp
        )

        # 构建内容
        content = {
            "change_type": change_type,
            "change_time": timestamp.isoformat(),
            "account_id": account_id,
            "old_value": old_value,
            "new_value": new_value,
            "reason": reason,
            "changed_by": changed_by,
        }

        # 计算内容哈希
        content_hash = self._compute_hash(content)

        # 创建报送记录
        report = ReportRecord(
            report_id=report_id,
            report_type=ReportType.CHANGE,
            report_date=timestamp.date(),
            created_at=timestamp.isoformat(),
            content=content,
            content_hash=content_hash,
            account_id=account_id,
            metadata={
                "change_type": change_type,
                "reporter_version": self.VERSION,
            },
        )

        # 存储
        self._reports[report_id] = report
        self._report_count += 1

        # 审计日志
        self._emit_audit_event(
            event_type="CHANGE_REPORT_GENERATED",
            report_id=report_id,
            account_id=account_id,
            details={"change_type": change_type, "old_value": old_value, "new_value": new_value},
            timestamp=timestamp,
        )

        # 持久化
        self._save_report(report)

        logger.info(f"变更报送生成: {report_id} - {change_type}")
        return report

    def submit_report(
        self,
        report: ReportRecord,
        timestamp: datetime | None = None,
    ) -> bool:
        """提交报送.

        参数:
            report: 报送记录
            timestamp: 提交时间

        返回:
            是否成功
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        self._submit_count += 1

        # 使用回调提交
        if self._submit_callback:
            try:
                success = self._submit_callback(report)
            except Exception as e:
                logger.error(f"报送回调失败: {e}")
                success = False
        else:
            # 模拟提交成功
            success = True

        # 更新状态
        if success:
            report.status = ReportStatus.SUBMITTED
            report.submitted_at = timestamp.isoformat()
            report.status_message = "提交成功"
            self._success_count += 1
        else:
            report.status = ReportStatus.FAILED
            report.status_message = "提交失败"
            report.retry_count += 1
            self._failure_count += 1

        # 更新存储
        self._reports[report.report_id] = report

        # 审计日志
        self._emit_audit_event(
            event_type="REPORT_SUBMITTED" if success else "REPORT_SUBMIT_FAILED",
            report_id=report.report_id,
            account_id=report.account_id,
            details={
                "report_type": report.report_type.value,
                "status": report.status.value,
                "retry_count": report.retry_count,
            },
            timestamp=timestamp,
        )

        # 持久化
        self._save_report(report)

        if success:
            logger.info(f"报送提交成功: {report.report_id}")
        else:
            logger.error(f"报送提交失败: {report.report_id}")

        return success

    def export_report(
        self,
        report: ReportRecord,
        format_type: ReportFormat = ReportFormat.JSON,
    ) -> str:
        """导出报告.

        参数:
            report: 报送记录
            format_type: 导出格式

        返回:
            导出内容
        """
        if format_type == ReportFormat.JSON:
            return self._export_json(report)
        if format_type == ReportFormat.XML:
            return self._export_xml(report)
        if format_type == ReportFormat.CSV:
            return self._export_csv(report)
        if format_type == ReportFormat.TEXT:
            return self._export_text(report)
        raise ValueError(f"不支持的导出格式: {format_type}")

    def get_report(self, report_id: str) -> ReportRecord | None:
        """获取报送记录.

        参数:
            report_id: 报告ID

        返回:
            报送记录 (不存在返回None)
        """
        return self._reports.get(report_id)

    def get_daily_report(
        self,
        account_id: str,
        report_date: date,
    ) -> ReportRecord | None:
        """获取日报送.

        参数:
            account_id: 账户ID
            report_date: 报告日期

        返回:
            报送记录 (不存在返回None)
        """
        report_id = self._daily_reports.get(report_date.isoformat())
        if report_id:
            report = self._reports.get(report_id)
            if report and report.account_id == account_id:
                return report
        return None

    def get_pending_reports(self) -> list[ReportRecord]:
        """获取待提交报送.

        返回:
            待提交报送列表
        """
        return [r for r in self._reports.values() if r.status == ReportStatus.PENDING]

    def get_failed_reports(self) -> list[ReportRecord]:
        """获取失败报送.

        返回:
            失败报送列表
        """
        return [r for r in self._reports.values() if r.status == ReportStatus.FAILED]

    def retry_failed_reports(self, timestamp: datetime | None = None) -> int:
        """重试失败报送.

        参数:
            timestamp: 重试时间

        返回:
            成功数量
        """
        failed_reports = self.get_failed_reports()
        success_count = 0

        for report in failed_reports:
            if report.retry_count < 3:  # 最多重试3次
                if self.submit_report(report, timestamp):
                    success_count += 1

        return success_count

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        status_counts = {}
        for status in ReportStatus:
            status_counts[status.value] = sum(
                1 for r in self._reports.values() if r.status == status
            )

        type_counts = {}
        for report_type in ReportType:
            type_counts[report_type.value] = sum(
                1 for r in self._reports.values() if r.report_type == report_type
            )

        return {
            "total_reports": len(self._reports),
            "submit_count": self._submit_count,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "success_rate": (
                self._success_count / self._submit_count
                if self._submit_count > 0
                else 0.0
            ),
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "reporter_version": self.VERSION,
        }

    def _generate_report_id(
        self,
        report_type: ReportType,
        account_id: str,
        report_date: date,
        timestamp: datetime,
    ) -> str:
        """生成报告ID."""
        data = f"{report_type.value}:{account_id}:{report_date.isoformat()}:{timestamp.isoformat()}"
        return f"RPT-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def _compute_hash(self, content: dict[str, Any]) -> str:
        """计算内容哈希."""
        data = json.dumps(content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(data.encode()).hexdigest()

    def _content_to_dict(self, content: DailyReportContent) -> dict[str, Any]:
        """转换日报送内容为字典."""
        return {
            "report_date": content.report_date.isoformat(),
            "account_id": content.account_id,
            "strategy_count": content.strategy_count,
            "total_orders": content.total_orders,
            "total_cancels": content.total_cancels,
            "total_trades": content.total_trades,
            "cancel_ratio": content.cancel_ratio,
            "max_cancel_freq": content.max_cancel_freq,
            "max_orders_per_sec": content.max_orders_per_sec,
            "min_order_interval_ms": content.min_order_interval_ms,
            "max_audit_delay_sec": content.max_audit_delay_sec,
            "violations": content.violations,
            "warnings": content.warnings,
            "is_hft": content.is_hft,
            "strategies_summary": content.strategies_summary,
        }

    def _exception_content_to_dict(self, content: ExceptionReportContent) -> dict[str, Any]:
        """转换异常报送内容为字典."""
        return {
            "exception_type": content.exception_type,
            "exception_time": content.exception_time,
            "account_id": content.account_id,
            "strategy_id": content.strategy_id,
            "description": content.description,
            "impact": content.impact,
            "action_taken": content.action_taken,
            "is_resolved": content.is_resolved,
            "related_orders": content.related_orders,
        }

    def _export_json(self, report: ReportRecord) -> str:
        """导出为JSON格式."""
        return json.dumps(report.to_dict(), ensure_ascii=False, indent=2)

    def _export_xml(self, report: ReportRecord) -> str:
        """导出为XML格式."""
        def dict_to_xml(d: dict[str, Any], root: str = "report") -> str:
            xml = [f"<{root}>"]
            for key, value in d.items():
                if isinstance(value, dict):
                    xml.append(dict_to_xml(value, key))
                elif isinstance(value, list):
                    xml.append(f"<{key}>")
                    for item in value:
                        if isinstance(item, dict):
                            xml.append(dict_to_xml(item, "item"))
                        else:
                            xml.append(f"<item>{item}</item>")
                    xml.append(f"</{key}>")
                else:
                    xml.append(f"<{key}>{value}</{key}>")
            xml.append(f"</{root}>")
            return "\n".join(xml)

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + dict_to_xml(report.to_dict())

    def _export_csv(self, report: ReportRecord) -> str:
        """导出为CSV格式."""
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入头部
        flat_data = self._flatten_dict(report.to_dict())
        writer.writerow(flat_data.keys())
        writer.writerow(flat_data.values())

        return output.getvalue()

    def _export_text(self, report: ReportRecord) -> str:
        """导出为文本格式."""
        lines = [
            "=" * 60,
            f"报告ID: {report.report_id}",
            f"报告类型: {report.report_type.value}",
            f"报告日期: {report.report_date.isoformat()}",
            f"账户ID: {report.account_id}",
            f"创建时间: {report.created_at}",
            f"状态: {report.status.value}",
            "=" * 60,
            "报告内容:",
            json.dumps(report.content, ensure_ascii=False, indent=2),
            "=" * 60,
        ]
        return "\n".join(lines)

    def _flatten_dict(
        self,
        d: dict[str, Any],
        parent_key: str = "",
        sep: str = "_",
    ) -> dict[str, Any]:
        """扁平化字典."""
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                items.append((new_key, json.dumps(v, ensure_ascii=False)))
            else:
                items.append((new_key, v))
        return dict(items)

    def _save_report(self, report: ReportRecord) -> None:
        """保存报告到存储."""
        if not self._storage_path:
            return

        try:
            report_dir = self._storage_path / "reports"
            report_dir.mkdir(parents=True, exist_ok=True)

            report_file = report_dir / f"{report.report_id}.json"
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存报告失败: {e}")

    def _emit_audit_event(
        self,
        event_type: str,
        report_id: str,
        account_id: str,
        details: dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """发送审计事件."""
        if self._audit_callback:
            event = {
                "event_type": event_type,
                "report_id": report_id,
                "account_id": account_id,
                "details": details,
                "timestamp": timestamp.isoformat(),
                "module": "compliance.registration.reporter",
                "military_rules": ["M3", "M7", "M17"],
            }
            try:
                self._audit_callback(event)
            except Exception as e:
                logger.error(f"审计回调失败: {e}")


# ============================================================
# 便捷函数
# ============================================================


def create_regulatory_reporter(
    registry: Any = None,
    validator: Any = None,
    storage_path: str | Path | None = None,
    audit_callback: Callable[[dict[str, Any]], None] | None = None,
) -> RegulatoryReporter:
    """创建监管报送器.

    参数:
        registry: 备案登记中心 (可选)
        validator: 合规验证器 (可选)
        storage_path: 存储路径 (可选)
        audit_callback: 审计回调函数 (可选)

    返回:
        监管报送器实例
    """
    return RegulatoryReporter(registry, validator, storage_path, audit_callback)


# ============================================================
# 合规报告模板
# ============================================================


DAILY_REPORT_TEMPLATE = """
================================================================================
                     程序化交易日报送
================================================================================

报告ID: {report_id}
账户ID: {account_id}
报告日期: {report_date}
生成时间: {created_at}

--------------------------------------------------------------------------------
                     交易概况
--------------------------------------------------------------------------------
策略数量: {strategy_count}
总订单数: {total_orders}
总撤单数: {total_cancels}
总成交数: {total_trades}

--------------------------------------------------------------------------------
                     合规指标
--------------------------------------------------------------------------------
报撤单比例: {cancel_ratio:.2%} (限制: <=50%)
最大撤单频率: {max_cancel_freq:.0f} 次/秒 (限制: <=500次/秒)
最大订单频率: {max_orders_per_sec:.0f} 笔/秒
最小订单间隔: {min_order_interval_ms:.0f} ms (限制: >=100ms)
最大审计延迟: {max_audit_delay_sec:.2f} s (限制: <=1s)
高频交易判定: {is_hft}

--------------------------------------------------------------------------------
                     违规记录
--------------------------------------------------------------------------------
{violations}

--------------------------------------------------------------------------------
                     预警记录
--------------------------------------------------------------------------------
{warnings}

--------------------------------------------------------------------------------
                     策略摘要
--------------------------------------------------------------------------------
{strategies_summary}

================================================================================
                     报告结束
================================================================================
"""

EXCEPTION_REPORT_TEMPLATE = """
================================================================================
                     程序化交易异常报送
================================================================================

报告ID: {report_id}
账户ID: {account_id}
异常类型: {exception_type}
异常时间: {exception_time}

--------------------------------------------------------------------------------
                     异常详情
--------------------------------------------------------------------------------
策略ID: {strategy_id}
异常描述: {description}
影响范围: {impact}
采取措施: {action_taken}
是否解决: {is_resolved}

--------------------------------------------------------------------------------
                     相关订单
--------------------------------------------------------------------------------
{related_orders}

================================================================================
                     报告结束
================================================================================
"""
