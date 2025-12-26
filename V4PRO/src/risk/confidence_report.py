"""置信度报告生成模块 (军规级 v4.5).

V4PRO Platform Component - 置信度报告生成系统
军规覆盖: M3(完整审计)

V4PRO Scenarios:
- K65: CONFIDENCE.REPORT.MARKDOWN - Markdown报告
- K66: CONFIDENCE.REPORT.JSON - JSON报告
- K67: CONFIDENCE.REPORT.RICH - 终端富文本报告

提供多种格式的置信度评估报告生成功能。

示例:
    >>> from src.risk.confidence import ConfidenceAssessor, ConfidenceContext, TaskType
    >>> from src.risk.confidence_report import ConfidenceReportGenerator, ReportFormat
    >>> assessor = ConfidenceAssessor()
    >>> context = ConfidenceContext(
    ...     task_type=TaskType.STRATEGY_EXECUTION,
    ...     has_official_docs=True,
    ... )
    >>> result = assessor.assess(context)
    >>> generator = ConfidenceReportGenerator()
    >>> print(generator.to_markdown(result))
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar

from src.risk.confidence import ConfidenceCheck, ConfidenceLevel, ConfidenceResult


class ReportFormat(Enum):
    """报告格式枚举."""

    MARKDOWN = "markdown"
    JSON = "json"
    TABLE = "table"
    RICH_TEXT = "rich_text"


# =============================================================================
# ANSI 颜色代码
# =============================================================================


class ANSIColors:
    """ANSI颜色代码常量类."""

    # 重置
    RESET: ClassVar[str] = "\033[0m"

    # 前景色
    RED: ClassVar[str] = "\033[31m"
    GREEN: ClassVar[str] = "\033[32m"
    YELLOW: ClassVar[str] = "\033[33m"
    BLUE: ClassVar[str] = "\033[34m"
    MAGENTA: ClassVar[str] = "\033[35m"
    CYAN: ClassVar[str] = "\033[36m"
    WHITE: ClassVar[str] = "\033[37m"

    # 高亮前景色
    BRIGHT_RED: ClassVar[str] = "\033[91m"
    BRIGHT_GREEN: ClassVar[str] = "\033[92m"
    BRIGHT_YELLOW: ClassVar[str] = "\033[93m"
    BRIGHT_BLUE: ClassVar[str] = "\033[94m"
    BRIGHT_MAGENTA: ClassVar[str] = "\033[95m"
    BRIGHT_CYAN: ClassVar[str] = "\033[96m"

    # 样式
    BOLD: ClassVar[str] = "\033[1m"
    DIM: ClassVar[str] = "\033[2m"
    UNDERLINE: ClassVar[str] = "\033[4m"

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        """为文本添加颜色.

        参数:
            text: 待着色文本
            color: ANSI颜色代码

        返回:
            带颜色的文本
        """
        return f"{color}{text}{cls.RESET}"


# =============================================================================
# 报告配置
# =============================================================================


@dataclass
class ReportConfig:
    """报告配置.

    属性:
        title: 报告标题
        show_timestamp: 是否显示时间戳
        show_context_summary: 是否显示上下文摘要
        show_check_details: 是否显示检查项详情
        show_statistics: 是否显示统计信息
        use_emoji: 是否使用emoji
        locale: 语言区域设置
    """

    title: str = "置信度评估报告"
    show_timestamp: bool = True
    show_context_summary: bool = True
    show_check_details: bool = True
    show_statistics: bool = True
    use_emoji: bool = True
    locale: str = "zh-CN"


# =============================================================================
# 报告生成器
# =============================================================================


class ConfidenceReportGenerator:
    """置信度报告生成器.

    支持多种格式的报告生成:
    - Markdown: 适用于文档和Wiki
    - JSON: 适用于API和数据交换
    - Table: 适用于终端纯文本显示
    - Rich Text: 适用于终端彩色显示

    示例:
        >>> generator = ConfidenceReportGenerator()
        >>> markdown_report = generator.to_markdown(result)
        >>> json_report = generator.to_json(result)
        >>> table_report = generator.to_table(result)
        >>> rich_report = generator.to_rich_text(result)
    """

    # 置信度等级到颜色的映射
    LEVEL_COLORS: ClassVar[dict[ConfidenceLevel, str]] = {
        ConfidenceLevel.HIGH: ANSIColors.BRIGHT_GREEN,
        ConfidenceLevel.MEDIUM: ANSIColors.BRIGHT_YELLOW,
        ConfidenceLevel.LOW: ANSIColors.BRIGHT_RED,
    }

    # 置信度等级到中文描述的映射
    LEVEL_NAMES: ClassVar[dict[ConfidenceLevel, str]] = {
        ConfidenceLevel.HIGH: "高",
        ConfidenceLevel.MEDIUM: "中",
        ConfidenceLevel.LOW: "低",
    }

    # 置信度等级到emoji的映射
    LEVEL_EMOJI: ClassVar[dict[ConfidenceLevel, str]] = {
        ConfidenceLevel.HIGH: "✅",
        ConfidenceLevel.MEDIUM: "⚠️",
        ConfidenceLevel.LOW: "❌",
    }

    def __init__(self, config: ReportConfig | None = None) -> None:
        """初始化报告生成器.

        参数:
            config: 报告配置 (可选)
        """
        self._config = config or ReportConfig()

    @property
    def config(self) -> ReportConfig:
        """获取报告配置."""
        return self._config

    def to_markdown(self, result: ConfidenceResult) -> str:
        """生成 Markdown 格式报告.

        参数:
            result: 置信度评估结果

        返回:
            Markdown格式的报告字符串

        场景: K65
        """
        lines: list[str] = []

        # 标题
        lines.append(f"# {self._config.title}")
        lines.append("")

        # 时间戳
        if self._config.show_timestamp and result.timestamp:
            lines.append(f"**生成时间:** {result.timestamp}")
            lines.append("")

        # 总体结果
        level_emoji = self.LEVEL_EMOJI.get(result.level, "")
        level_name = self.LEVEL_NAMES.get(result.level, result.level.value)

        lines.append("## 评估结果")
        lines.append("")
        lines.append(f"| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 置信度分数 | **{result.score:.1%}** |")
        lines.append(f"| 置信度等级 | {level_emoji} {level_name} |")
        lines.append(f"| 是否可执行 | {'是' if result.can_proceed else '否'} |")
        lines.append("")

        # 建议
        lines.append("## 建议")
        lines.append("")
        lines.append(f"> {result.recommendation}")
        lines.append("")

        # 检查项详情
        if self._config.show_check_details and result.checks:
            lines.append("## 检查项详情")
            lines.append("")
            lines.append("| 检查项 | 状态 | 权重 | 说明 |")
            lines.append("|--------|------|------|------|")

            for check in result.checks:
                status = "✅ 通过" if check.passed else "❌ 未通过"
                lines.append(
                    f"| {check.name} | {status} | {check.weight:.0%} | {check.message} |"
                )
            lines.append("")

        # 上下文摘要
        if self._config.show_context_summary and result.context_summary:
            lines.append("## 上下文信息")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(result.context_summary, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")

        # 统计信息
        if self._config.show_statistics:
            passed_count = len(result.passed_checks)
            failed_count = len(result.failed_checks)
            total_count = len(result.checks)

            lines.append("## 统计")
            lines.append("")
            lines.append(f"- 总检查项: {total_count}")
            lines.append(f"- 通过: {passed_count}")
            lines.append(f"- 未通过: {failed_count}")
            lines.append(f"- 通过率: {passed_count / total_count:.1%}" if total_count > 0 else "- 通过率: N/A")
            lines.append("")

        # 页脚
        lines.append("---")
        lines.append("*V4PRO 置信度评估系统 (军规级 v4.5)*")

        return "\n".join(lines)

    def to_json(self, result: ConfidenceResult, *, indent: int = 2) -> str:
        """生成 JSON 格式报告.

        参数:
            result: 置信度评估结果
            indent: JSON缩进空格数

        返回:
            JSON格式的报告字符串

        场景: K66
        """
        report_data: dict[str, Any] = {
            "report_type": "confidence_assessment",
            "version": "4.5",
            "title": self._config.title,
            "generated_at": datetime.now().isoformat(),  # noqa: DTZ005
            "result": {
                "score": round(result.score, 4),
                "score_percent": f"{result.score:.1%}",
                "level": result.level.value,
                "level_name": self.LEVEL_NAMES.get(result.level, result.level.value),
                "can_proceed": result.can_proceed,
                "recommendation": result.recommendation,
                "timestamp": result.timestamp,
            },
            "checks": [
                {
                    "name": check.name,
                    "passed": check.passed,
                    "weight": round(check.weight, 4),
                    "message": check.message,
                    "details": check.details,
                }
                for check in result.checks
            ],
            "statistics": {
                "total_checks": len(result.checks),
                "passed_checks": len(result.passed_checks),
                "failed_checks": len(result.failed_checks),
                "pass_rate": (
                    round(len(result.passed_checks) / len(result.checks), 4)
                    if result.checks
                    else 0.0
                ),
            },
        }

        # 添加上下文摘要 (如果配置允许)
        if self._config.show_context_summary and result.context_summary:
            report_data["context_summary"] = result.context_summary

        return json.dumps(report_data, ensure_ascii=False, indent=indent)

    def to_table(self, result: ConfidenceResult) -> str:
        """生成表格格式报告.

        参数:
            result: 置信度评估结果

        返回:
            表格格式的报告字符串
        """
        lines: list[str] = []

        # 边框字符
        h_line = "=" * 60
        s_line = "-" * 60

        # 标题
        lines.append(h_line)
        lines.append(f"  {self._config.title}")
        lines.append(h_line)
        lines.append("")

        # 时间戳
        if self._config.show_timestamp and result.timestamp:
            lines.append(f"  生成时间: {result.timestamp}")
            lines.append("")

        # 总体结果
        level_name = self.LEVEL_NAMES.get(result.level, result.level.value)
        can_proceed_str = "是" if result.can_proceed else "否"

        lines.append(s_line)
        lines.append("  评估结果")
        lines.append(s_line)
        lines.append(f"  置信度分数: {result.score:.1%}")
        lines.append(f"  置信度等级: {level_name}")
        lines.append(f"  是否可执行: {can_proceed_str}")
        lines.append("")

        # 建议
        lines.append(s_line)
        lines.append("  建议")
        lines.append(s_line)
        lines.append(f"  {result.recommendation}")
        lines.append("")

        # 检查项详情
        if self._config.show_check_details and result.checks:
            lines.append(s_line)
            lines.append("  检查项详情")
            lines.append(s_line)

            # 表头
            lines.append(f"  {'检查项':<20} {'状态':<8} {'权重':<8} 说明")
            lines.append(f"  {'-'*20} {'-'*8} {'-'*8} {'-'*20}")

            for check in result.checks:
                status = "[PASS]" if check.passed else "[FAIL]"
                # 截断过长的消息
                msg = check.message[:25] + "..." if len(check.message) > 28 else check.message
                lines.append(f"  {check.name:<20} {status:<8} {check.weight:>6.0%}   {msg}")

            lines.append("")

        # 统计信息
        if self._config.show_statistics:
            passed_count = len(result.passed_checks)
            failed_count = len(result.failed_checks)
            total_count = len(result.checks)
            pass_rate = passed_count / total_count if total_count > 0 else 0.0

            lines.append(s_line)
            lines.append("  统计")
            lines.append(s_line)
            lines.append(f"  总检查项: {total_count}")
            lines.append(f"  通过: {passed_count}")
            lines.append(f"  未通过: {failed_count}")
            lines.append(f"  通过率: {pass_rate:.1%}")
            lines.append("")

        # 页脚
        lines.append(h_line)
        lines.append("  V4PRO 置信度评估系统 (军规级 v4.5)")
        lines.append(h_line)

        return "\n".join(lines)

    def to_rich_text(self, result: ConfidenceResult) -> str:
        """生成终端富文本报告 (ANSI颜色).

        参数:
            result: 置信度评估结果

        返回:
            带ANSI颜色代码的报告字符串

        场景: K67
        """
        lines: list[str] = []
        c = ANSIColors  # 简化引用

        # 边框字符
        h_line = c.colorize("=" * 60, c.CYAN)
        s_line = c.colorize("-" * 60, c.DIM)

        # 标题
        lines.append(h_line)
        title = c.colorize(f"  {self._config.title}", c.BOLD + c.BRIGHT_CYAN)
        lines.append(title)
        lines.append(h_line)
        lines.append("")

        # 时间戳
        if self._config.show_timestamp and result.timestamp:
            ts_label = c.colorize("  生成时间:", c.DIM)
            ts_value = c.colorize(result.timestamp, c.WHITE)
            lines.append(f"{ts_label} {ts_value}")
            lines.append("")

        # 总体结果
        level_color = self.LEVEL_COLORS.get(result.level, c.WHITE)
        level_name = self.LEVEL_NAMES.get(result.level, result.level.value)
        level_emoji = self.LEVEL_EMOJI.get(result.level, "")

        lines.append(s_line)
        lines.append(c.colorize("  评估结果", c.BOLD + c.WHITE))
        lines.append(s_line)

        # 置信度分数 (带进度条效果)
        score_bar = self._render_score_bar(result.score, level_color)
        lines.append(f"  置信度分数: {score_bar}")

        # 置信度等级
        level_display = c.colorize(f"{level_emoji} {level_name}", level_color + c.BOLD)
        lines.append(f"  置信度等级: {level_display}")

        # 是否可执行
        if result.can_proceed:
            proceed_str = c.colorize("是 - 可以执行", c.BRIGHT_GREEN)
        else:
            proceed_str = c.colorize("否 - 需要进一步检查", c.BRIGHT_RED)
        lines.append(f"  是否可执行: {proceed_str}")
        lines.append("")

        # 建议
        lines.append(s_line)
        lines.append(c.colorize("  建议", c.BOLD + c.WHITE))
        lines.append(s_line)
        rec_color = level_color
        lines.append(c.colorize(f"  {result.recommendation}", rec_color))
        lines.append("")

        # 检查项详情
        if self._config.show_check_details and result.checks:
            lines.append(s_line)
            lines.append(c.colorize("  检查项详情", c.BOLD + c.WHITE))
            lines.append(s_line)

            for check in result.checks:
                if check.passed:
                    status = c.colorize("[PASS]", c.BRIGHT_GREEN)
                    name_color = c.GREEN
                else:
                    status = c.colorize("[FAIL]", c.BRIGHT_RED)
                    name_color = c.RED

                name = c.colorize(check.name, name_color)
                weight = c.colorize(f"{check.weight:>5.0%}", c.DIM)

                # 消息处理
                msg = check.message
                if len(msg) > 40:
                    msg = msg[:37] + "..."

                lines.append(f"  {status} {name:<25} {weight}  {msg}")

            lines.append("")

        # 统计信息
        if self._config.show_statistics:
            passed_count = len(result.passed_checks)
            failed_count = len(result.failed_checks)
            total_count = len(result.checks)
            pass_rate = passed_count / total_count if total_count > 0 else 0.0

            lines.append(s_line)
            lines.append(c.colorize("  统计", c.BOLD + c.WHITE))
            lines.append(s_line)

            total_label = c.colorize(f"  总检查项: {total_count}", c.WHITE)
            passed_label = c.colorize(f"  通过: {passed_count}", c.BRIGHT_GREEN)
            failed_label = c.colorize(f"  未通过: {failed_count}", c.BRIGHT_RED if failed_count > 0 else c.WHITE)

            # 通过率着色
            if pass_rate >= 0.9:
                rate_color = c.BRIGHT_GREEN
            elif pass_rate >= 0.7:
                rate_color = c.BRIGHT_YELLOW
            else:
                rate_color = c.BRIGHT_RED
            rate_label = c.colorize(f"  通过率: {pass_rate:.1%}", rate_color)

            lines.append(total_label)
            lines.append(passed_label)
            lines.append(failed_label)
            lines.append(rate_label)
            lines.append("")

        # 页脚
        lines.append(h_line)
        footer = c.colorize("  V4PRO 置信度评估系统 (军规级 v4.5)", c.DIM)
        lines.append(footer)
        lines.append(h_line)

        return "\n".join(lines)

    def _render_score_bar(
        self,
        score: float,
        color: str,
        width: int = 20,
    ) -> str:
        """渲染分数进度条.

        参数:
            score: 分数 (0.0-1.0)
            color: ANSI颜色代码
            width: 进度条宽度

        返回:
            带颜色的进度条字符串
        """
        c = ANSIColors
        filled = int(score * width)
        empty = width - filled

        bar = c.colorize("█" * filled, color)
        bar += c.colorize("░" * empty, c.DIM)
        score_str = c.colorize(f" {score:.1%}", color + c.BOLD)

        return f"[{bar}]{score_str}"

    def generate(
        self,
        result: ConfidenceResult,
        format: ReportFormat,  # noqa: A002
    ) -> str:
        """根据格式生成报告.

        参数:
            result: 置信度评估结果
            format: 报告格式

        返回:
            格式化的报告字符串

        异常:
            ValueError: 不支持的报告格式
        """
        format_handlers = {
            ReportFormat.MARKDOWN: self.to_markdown,
            ReportFormat.JSON: self.to_json,
            ReportFormat.TABLE: self.to_table,
            ReportFormat.RICH_TEXT: self.to_rich_text,
        }

        handler = format_handlers.get(format)
        if handler is None:
            raise ValueError(f"不支持的报告格式: {format}")

        return handler(result)

    def generate_all(self, result: ConfidenceResult) -> dict[ReportFormat, str]:
        """生成所有格式的报告.

        参数:
            result: 置信度评估结果

        返回:
            格式到报告内容的字典
        """
        return {fmt: self.generate(result, fmt) for fmt in ReportFormat}


# =============================================================================
# 便捷函数
# =============================================================================


def generate_markdown_report(
    result: ConfidenceResult,
    *,
    title: str = "置信度评估报告",
) -> str:
    """生成 Markdown 格式报告.

    参数:
        result: 置信度评估结果
        title: 报告标题

    返回:
        Markdown格式的报告字符串

    示例:
        >>> report = generate_markdown_report(result)
        >>> print(report)
    """
    config = ReportConfig(title=title)
    generator = ConfidenceReportGenerator(config)
    return generator.to_markdown(result)


def generate_json_report(
    result: ConfidenceResult,
    *,
    indent: int = 2,
) -> str:
    """生成 JSON 格式报告.

    参数:
        result: 置信度评估结果
        indent: JSON缩进空格数

    返回:
        JSON格式的报告字符串

    示例:
        >>> report = generate_json_report(result)
        >>> data = json.loads(report)
    """
    generator = ConfidenceReportGenerator()
    return generator.to_json(result, indent=indent)


def generate_table_report(
    result: ConfidenceResult,
    *,
    title: str = "置信度评估报告",
) -> str:
    """生成表格格式报告.

    参数:
        result: 置信度评估结果
        title: 报告标题

    返回:
        表格格式的报告字符串

    示例:
        >>> report = generate_table_report(result)
        >>> print(report)
    """
    config = ReportConfig(title=title)
    generator = ConfidenceReportGenerator(config)
    return generator.to_table(result)


def generate_rich_report(
    result: ConfidenceResult,
    *,
    title: str = "置信度评估报告",
) -> str:
    """生成终端富文本报告.

    参数:
        result: 置信度评估结果
        title: 报告标题

    返回:
        带ANSI颜色代码的报告字符串

    示例:
        >>> report = generate_rich_report(result)
        >>> print(report)  # 在支持ANSI的终端中显示彩色
    """
    config = ReportConfig(title=title)
    generator = ConfidenceReportGenerator(config)
    return generator.to_rich_text(result)


def quick_report(
    result: ConfidenceResult,
    format: ReportFormat | str = ReportFormat.TABLE,  # noqa: A002
) -> str:
    """快速生成报告.

    参数:
        result: 置信度评估结果
        format: 报告格式 (可以是 ReportFormat 枚举或字符串)

    返回:
        格式化的报告字符串

    示例:
        >>> report = quick_report(result, "markdown")
        >>> report = quick_report(result, ReportFormat.JSON)
    """
    # 支持字符串格式
    if isinstance(format, str):
        format = ReportFormat(format.lower())

    generator = ConfidenceReportGenerator()
    return generator.generate(result, format)


def print_report(
    result: ConfidenceResult,
    format: ReportFormat | str = ReportFormat.RICH_TEXT,  # noqa: A002
) -> None:
    """打印报告到终端.

    参数:
        result: 置信度评估结果
        format: 报告格式

    示例:
        >>> print_report(result)  # 默认使用富文本格式
        >>> print_report(result, "table")  # 使用表格格式
    """
    report = quick_report(result, format)
    print(report)  # noqa: T201


def create_report_generator(
    *,
    title: str = "置信度评估报告",
    show_timestamp: bool = True,
    show_context_summary: bool = True,
    show_check_details: bool = True,
    show_statistics: bool = True,
    use_emoji: bool = True,
) -> ConfidenceReportGenerator:
    """创建报告生成器实例.

    参数:
        title: 报告标题
        show_timestamp: 是否显示时间戳
        show_context_summary: 是否显示上下文摘要
        show_check_details: 是否显示检查项详情
        show_statistics: 是否显示统计信息
        use_emoji: 是否使用emoji

    返回:
        配置好的报告生成器实例

    示例:
        >>> generator = create_report_generator(
        ...     title="策略评估",
        ...     show_context_summary=False,
        ... )
        >>> report = generator.to_markdown(result)
    """
    config = ReportConfig(
        title=title,
        show_timestamp=show_timestamp,
        show_context_summary=show_context_summary,
        show_check_details=show_check_details,
        show_statistics=show_statistics,
        use_emoji=use_emoji,
    )
    return ConfidenceReportGenerator(config)
