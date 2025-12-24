"""结构化日志模块 - 统一的日志记录和管理.

提供结构化日志功能:
- StructuredLogger: 结构化日志记录器
- 支持上下文绑定
- 支持JSON格式输出
- 支持多种日志级别

使用示例:
    >>> logger = StructuredLogger("my-service")
    >>> logger.info("用户登录", user_id="12345", ip="192.168.1.1")
    >>> with logger.with_context(request_id="abc123"):
    ...     logger.info("处理请求")
"""

from __future__ import annotations

import json
import logging
import sys
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from threading import local
from typing import Any, Generator, TextIO, TypeAlias

# =============================================================================
# 类型别名
# =============================================================================

LogContext: TypeAlias = dict[str, Any]
"""日志上下文类型."""


# =============================================================================
# 枚举定义
# =============================================================================


class LogLevel(Enum):
    """日志级别枚举.

    从低到高:
    - DEBUG: 调试信息
    - INFO: 一般信息
    - WARNING: 警告信息
    - ERROR: 错误信息
    - CRITICAL: 严重错误
    """

    DEBUG = "debug"
    """调试信息"""

    INFO = "info"
    """一般信息"""

    WARNING = "warning"
    """警告信息"""

    ERROR = "error"
    """错误信息"""

    CRITICAL = "critical"
    """严重错误"""

    def to_logging_level(self) -> int:
        """转换为logging模块的级别.

        Returns:
            logging模块的级别常量
        """
        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return mapping[self]


class LogFormat(Enum):
    """日志格式枚举.

    支持的格式:
    - TEXT: 人类可读的文本格式
    - JSON: JSON格式(便于日志分析系统处理)
    """

    TEXT = "text"
    """文本格式"""

    JSON = "json"
    """JSON格式"""


# =============================================================================
# 日志数据类
# =============================================================================


@dataclass
class LogRecord:
    """日志记录.

    表示单条日志:
    - level: 日志级别
    - message: 日志消息
    - context: 上下文信息
    - timestamp: 时间戳
    - logger_name: 记录器名称
    - exception_info: 异常信息(如果有)
    """

    level: LogLevel
    """日志级别"""

    message: str
    """日志消息"""

    logger_name: str
    """记录器名称"""

    context: LogContext = field(default_factory=dict)
    """上下文信息"""

    timestamp: datetime = field(default_factory=datetime.now)
    """时间戳"""

    exception_info: str | None = None
    """异常信息"""

    source_file: str | None = None
    """源文件"""

    source_line: int | None = None
    """源代码行号"""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典表示.

        Returns:
            包含日志信息的字典
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value.upper(),
            "logger": self.logger_name,
            "message": self.message,
            "context": self.context,
            "exception": self.exception_info,
            "source": {
                "file": self.source_file,
                "line": self.source_line,
            } if self.source_file else None,
        }

    def to_json(self) -> str:
        """转换为JSON字符串.

        Returns:
            JSON格式的日志字符串
        """
        data = self.to_dict()
        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, ensure_ascii=False, default=str)

    def to_text(self) -> str:
        """转换为文本格式.

        Returns:
            人类可读的文本格式
        """
        parts = [
            self.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            f"[{self.level.value.upper():8}]",
            f"[{self.logger_name}]",
            self.message,
        ]

        # 添加上下文
        if self.context:
            context_str = " ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"| {context_str}")

        # 添加源信息
        if self.source_file:
            parts.append(f"({self.source_file}:{self.source_line})")

        text = " ".join(parts)

        # 添加异常信息
        if self.exception_info:
            text += f"\n{self.exception_info}"

        return text


# =============================================================================
# 日志处理器
# =============================================================================


class LogHandler:
    """日志处理器基类.

    定义日志处理器的接口.
    """

    def handle(self, record: LogRecord) -> None:
        """处理日志记录.

        Args:
            record: 日志记录
        """
        raise NotImplementedError


class StreamHandler(LogHandler):
    """流处理器.

    将日志输出到流(如stdout, stderr).
    """

    def __init__(
        self,
        stream: TextIO | None = None,
        format: LogFormat = LogFormat.TEXT,
    ) -> None:
        """初始化流处理器.

        Args:
            stream: 输出流(默认为stdout)
            format: 输出格式
        """
        self.stream = stream or sys.stdout
        self.format = format

    def handle(self, record: LogRecord) -> None:
        """处理日志记录.

        Args:
            record: 日志记录
        """
        if self.format == LogFormat.JSON:
            output = record.to_json()
        else:
            output = record.to_text()

        self.stream.write(output + "\n")
        self.stream.flush()


class FileHandler(LogHandler):
    """文件处理器.

    将日志输出到文件.
    """

    def __init__(
        self,
        file_path: Path | str,
        format: LogFormat = LogFormat.TEXT,
        encoding: str = "utf-8",
    ) -> None:
        """初始化文件处理器.

        Args:
            file_path: 日志文件路径
            format: 输出格式
            encoding: 文件编码
        """
        self.file_path = Path(file_path)
        self.format = format
        self.encoding = encoding

        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def handle(self, record: LogRecord) -> None:
        """处理日志记录.

        Args:
            record: 日志记录
        """
        if self.format == LogFormat.JSON:
            output = record.to_json()
        else:
            output = record.to_text()

        with open(self.file_path, "a", encoding=self.encoding) as f:
            f.write(output + "\n")


class MemoryHandler(LogHandler):
    """内存处理器.

    将日志存储在内存中, 便于测试和调试.
    """

    def __init__(self, max_records: int = 1000) -> None:
        """初始化内存处理器.

        Args:
            max_records: 最大记录数量
        """
        self.max_records = max_records
        self._records: list[LogRecord] = []

    def handle(self, record: LogRecord) -> None:
        """处理日志记录.

        Args:
            record: 日志记录
        """
        self._records.append(record)
        if len(self._records) > self.max_records:
            self._records = self._records[-self.max_records:]

    @property
    def records(self) -> list[LogRecord]:
        """获取所有记录.

        Returns:
            记录列表的副本
        """
        return list(self._records)

    def clear(self) -> None:
        """清空记录."""
        self._records.clear()


# =============================================================================
# StructuredLogger类
# =============================================================================


class StructuredLogger:
    """结构化日志记录器.

    提供结构化日志功能:
    - 支持多种日志级别
    - 支持上下文绑定
    - 支持多种输出格式
    - 支持多个处理器

    Attributes:
        name: 记录器名称
        level: 最低日志级别
        handlers: 日志处理器列表

    使用示例:
        >>> logger = StructuredLogger("api-service", level=LogLevel.INFO)
        >>> logger.info("请求开始", method="GET", path="/users")
        >>> logger.error("请求失败", error="Not Found", status=404)

        # 使用上下文
        >>> with logger.with_context(request_id="abc123", user_id="user1"):
        ...     logger.info("处理中")
        ...     logger.info("处理完成")
    """

    def __init__(
        self,
        name: str,
        level: LogLevel = LogLevel.INFO,
        handlers: list[LogHandler] | None = None,
    ) -> None:
        """初始化结构化日志记录器.

        Args:
            name: 记录器名称
            level: 最低日志级别
            handlers: 日志处理器列表(默认添加StreamHandler)
        """
        self.name = name
        self.level = level
        self._handlers = handlers or [StreamHandler()]
        self._context = local()
        self._base_context: LogContext = {}

    @property
    def handlers(self) -> list[LogHandler]:
        """获取处理器列表.

        Returns:
            处理器列表的副本
        """
        return list(self._handlers)

    def add_handler(self, handler: LogHandler) -> None:
        """添加处理器.

        Args:
            handler: 日志处理器
        """
        self._handlers.append(handler)

    def remove_handler(self, handler: LogHandler) -> None:
        """移除处理器.

        Args:
            handler: 日志处理器
        """
        if handler in self._handlers:
            self._handlers.remove(handler)

    def set_level(self, level: LogLevel) -> None:
        """设置日志级别.

        Args:
            level: 日志级别
        """
        self.level = level

    def set_base_context(self, **context: Any) -> None:
        """设置基础上下文.

        基础上下文会添加到所有日志记录中.

        Args:
            **context: 上下文键值对
        """
        self._base_context.update(context)

    def _get_context(self) -> LogContext:
        """获取当前上下文.

        Returns:
            合并后的上下文
        """
        context = dict(self._base_context)
        thread_context = getattr(self._context, "context_stack", None)
        if thread_context:
            for ctx in thread_context:
                context.update(ctx)
        return context

    def _should_log(self, level: LogLevel) -> bool:
        """检查是否应该记录日志.

        Args:
            level: 日志级别

        Returns:
            如果应该记录则返回True
        """
        level_order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        return level_order.index(level) >= level_order.index(self.level)

    def _log(
        self,
        level: LogLevel,
        message: str,
        exc_info: bool = False,
        **context: Any,
    ) -> None:
        """内部日志方法.

        Args:
            level: 日志级别
            message: 日志消息
            exc_info: 是否包含异常信息
            **context: 额外上下文
        """
        if not self._should_log(level):
            return

        # 合并上下文
        merged_context = self._get_context()
        merged_context.update(context)

        # 获取异常信息
        exception_info = None
        if exc_info:
            exception_info = traceback.format_exc()
            if exception_info == "NoneType: None\n":
                exception_info = None

        # 获取调用位置
        source_file = None
        source_line = None
        try:
            # 获取调用堆栈, 跳过 _log 和 info/error 等方法
            frame = sys._getframe(2)
            source_file = frame.f_code.co_filename
            source_line = frame.f_lineno
        except (ValueError, AttributeError):
            pass

        # 创建日志记录
        record = LogRecord(
            level=level,
            message=message,
            logger_name=self.name,
            context=merged_context,
            exception_info=exception_info,
            source_file=source_file,
            source_line=source_line,
        )

        # 发送到所有处理器
        for handler in self._handlers:
            try:
                handler.handle(record)
            except Exception:
                # 处理器失败不应影响应用程序
                pass

    def debug(self, message: str, **context: Any) -> None:
        """记录调试日志.

        Args:
            message: 日志消息
            **context: 上下文键值对
        """
        self._log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """记录信息日志.

        Args:
            message: 日志消息
            **context: 上下文键值对
        """
        self._log(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context: Any) -> None:
        """记录警告日志.

        Args:
            message: 日志消息
            **context: 上下文键值对
        """
        self._log(LogLevel.WARNING, message, **context)

    def warn(self, message: str, **context: Any) -> None:
        """记录警告日志(别名).

        Args:
            message: 日志消息
            **context: 上下文键值对
        """
        self.warning(message, **context)

    def error(self, message: str, exc_info: bool = False, **context: Any) -> None:
        """记录错误日志.

        Args:
            message: 日志消息
            exc_info: 是否包含异常信息
            **context: 上下文键值对
        """
        self._log(LogLevel.ERROR, message, exc_info=exc_info, **context)

    def critical(self, message: str, exc_info: bool = False, **context: Any) -> None:
        """记录严重错误日志.

        Args:
            message: 日志消息
            exc_info: 是否包含异常信息
            **context: 上下文键值对
        """
        self._log(LogLevel.CRITICAL, message, exc_info=exc_info, **context)

    def exception(self, message: str, **context: Any) -> None:
        """记录异常日志.

        自动包含当前异常信息.

        Args:
            message: 日志消息
            **context: 上下文键值对
        """
        self.error(message, exc_info=True, **context)

    @contextmanager
    def with_context(self, **context: Any) -> Generator[StructuredLogger, None, None]:
        """上下文管理器, 临时添加上下文.

        在上下文管理器内记录的所有日志都会包含指定的上下文.

        Args:
            **context: 上下文键值对

        Yields:
            当前logger实例

        使用示例:
            >>> with logger.with_context(request_id="abc123"):
            ...     logger.info("处理请求")  # 自动包含request_id
        """
        if not hasattr(self._context, "context_stack"):
            self._context.context_stack = []

        self._context.context_stack.append(context)
        try:
            yield self
        finally:
            self._context.context_stack.pop()

    def bind(self, **context: Any) -> StructuredLogger:
        """创建带有绑定上下文的新logger.

        返回一个新的logger实例, 所有日志都会包含绑定的上下文.

        Args:
            **context: 上下文键值对

        Returns:
            带有绑定上下文的新logger实例
        """
        new_logger = StructuredLogger(
            name=self.name,
            level=self.level,
            handlers=self._handlers,
        )
        new_logger._base_context = {**self._base_context, **context}
        return new_logger

    def child(self, name: str) -> StructuredLogger:
        """创建子logger.

        Args:
            name: 子logger名称

        Returns:
            子logger实例
        """
        child_name = f"{self.name}.{name}"
        child_logger = StructuredLogger(
            name=child_name,
            level=self.level,
            handlers=self._handlers,
        )
        child_logger._base_context = dict(self._base_context)
        return child_logger


# =============================================================================
# 全局logger
# =============================================================================

_global_logger: StructuredLogger | None = None


def get_logger(name: str = "default") -> StructuredLogger:
    """获取或创建全局logger.

    Args:
        name: logger名称(仅在创建时使用)

    Returns:
        全局logger实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger


def set_logger(logger: StructuredLogger) -> None:
    """设置全局logger.

    Args:
        logger: logger实例
    """
    global _global_logger
    _global_logger = logger


def reset_logger() -> None:
    """重置全局logger."""
    global _global_logger
    _global_logger = None


# =============================================================================
# 便捷函数
# =============================================================================


def configure_logging(
    name: str = "app",
    level: LogLevel = LogLevel.INFO,
    format: LogFormat = LogFormat.TEXT,
    log_file: Path | str | None = None,
) -> StructuredLogger:
    """配置日志系统.

    便捷函数, 用于快速配置日志.

    Args:
        name: logger名称
        level: 日志级别
        format: 输出格式
        log_file: 日志文件路径(可选)

    Returns:
        配置好的logger实例
    """
    handlers: list[LogHandler] = [StreamHandler(format=format)]

    if log_file:
        handlers.append(FileHandler(log_file, format=format))

    logger = StructuredLogger(name=name, level=level, handlers=handlers)
    set_logger(logger)
    return logger


# =============================================================================
# 模块导出
# =============================================================================

__all__ = [
    # 类型别名
    "LogContext",
    # 枚举
    "LogLevel",
    "LogFormat",
    # 数据类
    "LogRecord",
    # 处理器
    "LogHandler",
    "StreamHandler",
    "FileHandler",
    "MemoryHandler",
    # 主类
    "StructuredLogger",
    # 全局函数
    "get_logger",
    "set_logger",
    "reset_logger",
    "configure_logging",
]
