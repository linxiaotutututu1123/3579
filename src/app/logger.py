"""日志配置模块 (军规级 v4.0).

提供应用级日志配置，包括:
- 日志格式配置
- 日志级别管理
- 日志处理器配置
- 日志过滤器
- 审计日志集成

军规覆盖:
- M3 完整审计: 日志记录完整可追溯
- M9 错误上报: 异常日志统一格式

场景覆盖:
- INFRA.LOG.FORMAT: 日志格式正确
- INFRA.LOG.LEVEL: 日志级别正确
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, TextIO


# =============================================================================
# 常量定义
# =============================================================================

# 默认日志格式
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

# 详细日志格式 (包含文件和行号)
VERBOSE_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)

# JSON日志格式模板
JSON_LOG_TEMPLATE = (
    '{{"ts": "{ts}", "level": "{level}", "logger": "{logger}", '
    '"message": "{message}", "extra": {extra}}}'
)

# 默认日期格式
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ISO8601日期格式
ISO8601_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"


# =============================================================================
# 枚举定义
# =============================================================================


class LogLevel(str, Enum):
    """日志级别枚举.

    对应Python logging级别。
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    def to_logging_level(self) -> int:
        """转换为logging模块的级别值."""
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL,
        }
        return level_map[self]


class LogFormat(str, Enum):
    """日志格式枚举."""

    SIMPLE = "simple"  # 简单格式
    VERBOSE = "verbose"  # 详细格式
    JSON = "json"  # JSON格式


# =============================================================================
# 数据类
# =============================================================================


@dataclass
class LogConfig:
    """日志配置.

    属性:
        level: 日志级别
        format: 日志格式
        log_dir: 日志目录
        console_output: 是否输出到控制台
        file_output: 是否输出到文件
        max_file_size: 最大文件大小 (MB)
        backup_count: 备份文件数量
        encoding: 文件编码
    """

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.SIMPLE
    log_dir: str = "logs"
    console_output: bool = True
    file_output: bool = False
    max_file_size: int = 10
    backup_count: int = 5
    encoding: str = "utf-8"
    extra_fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "level": self.level.value,
            "format": self.format.value,
            "log_dir": self.log_dir,
            "console_output": self.console_output,
            "file_output": self.file_output,
            "max_file_size": self.max_file_size,
            "backup_count": self.backup_count,
            "encoding": self.encoding,
            "extra_fields": self.extra_fields,
        }


# =============================================================================
# 日志格式化器
# =============================================================================


class StandardFormatter(logging.Formatter):
    """标准日志格式化器.

    支持简单和详细两种格式。
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
    ) -> None:
        """初始化格式化器.

        参数:
            fmt: 日志格式
            datefmt: 日期格式
        """
        super().__init__(fmt or DEFAULT_LOG_FORMAT, datefmt or DEFAULT_DATE_FORMAT)


class JsonFormatter(logging.Formatter):
    """JSON日志格式化器.

    将日志记录格式化为JSON字符串。
    """

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录.

        参数:
            record: 日志记录

        返回:
            JSON格式的日志字符串
        """
        # 获取时间戳
        ts = datetime.now(UTC).strftime(ISO8601_DATE_FORMAT)

        # 获取额外字段
        extra: dict[str, Any] = {}
        for key in dir(record):
            if not key.startswith("_") and key not in (
                "args",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "message",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "getMessage",
            ):
                value = getattr(record, key)
                if not callable(value):
                    extra[key] = value

        # 处理异常信息
        if record.exc_info:
            extra["exception"] = self.formatException(record.exc_info)

        # 格式化消息
        message = record.getMessage()

        # 转义特殊字符
        message = message.replace("\\", "\\\\").replace('"', '\\"')

        # 构建JSON
        import json

        extra_str = json.dumps(extra, ensure_ascii=False, default=str)

        return JSON_LOG_TEMPLATE.format(
            ts=ts,
            level=record.levelname,
            logger=record.name,
            message=message,
            extra=extra_str,
        )


# =============================================================================
# 日志过滤器
# =============================================================================


class LevelFilter(logging.Filter):
    """日志级别过滤器.

    只允许指定级别范围内的日志通过。
    """

    def __init__(
        self,
        min_level: int = logging.DEBUG,
        max_level: int = logging.CRITICAL,
    ) -> None:
        """初始化过滤器.

        参数:
            min_level: 最低级别
            max_level: 最高级别
        """
        super().__init__()
        self.min_level = min_level
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录.

        参数:
            record: 日志记录

        返回:
            是否允许通过
        """
        return self.min_level <= record.levelno <= self.max_level


class ComponentFilter(logging.Filter):
    """组件过滤器.

    只允许指定组件的日志通过。
    """

    def __init__(self, components: list[str]) -> None:
        """初始化过滤器.

        参数:
            components: 允许的组件列表
        """
        super().__init__()
        self.components = components

    def filter(self, record: logging.LogRecord) -> bool:
        """过滤日志记录.

        参数:
            record: 日志记录

        返回:
            是否允许通过
        """
        for comp in self.components:
            if record.name.startswith(comp):
                return True
        return len(self.components) == 0


# =============================================================================
# 日志处理器工厂
# =============================================================================


def create_console_handler(
    level: int = logging.DEBUG,
    format_type: LogFormat = LogFormat.SIMPLE,
    stream: TextIO | None = None,
) -> logging.StreamHandler[TextIO]:
    """创建控制台处理器.

    参数:
        level: 日志级别
        format_type: 日志格式类型
        stream: 输出流

    返回:
        控制台处理器
    """
    handler: logging.StreamHandler[TextIO] = logging.StreamHandler(stream or sys.stderr)
    handler.setLevel(level)

    if format_type == LogFormat.JSON:
        handler.setFormatter(JsonFormatter())
    elif format_type == LogFormat.VERBOSE:
        handler.setFormatter(StandardFormatter(fmt=VERBOSE_LOG_FORMAT))
    else:
        handler.setFormatter(StandardFormatter())

    return handler


def create_file_handler(
    filename: str,
    level: int = logging.DEBUG,
    format_type: LogFormat = LogFormat.SIMPLE,
    encoding: str = "utf-8",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> logging.Handler:
    """创建文件处理器.

    参数:
        filename: 文件名
        level: 日志级别
        format_type: 日志格式类型
        encoding: 文件编码
        max_bytes: 最大文件大小
        backup_count: 备份数量

    返回:
        文件处理器
    """
    from logging.handlers import RotatingFileHandler

    # 确保目录存在
    log_dir = Path(filename).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        filename,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding,
    )
    handler.setLevel(level)

    if format_type == LogFormat.JSON:
        handler.setFormatter(JsonFormatter())
    elif format_type == LogFormat.VERBOSE:
        handler.setFormatter(StandardFormatter(fmt=VERBOSE_LOG_FORMAT))
    else:
        handler.setFormatter(StandardFormatter())

    return handler


# =============================================================================
# 日志配置函数
# =============================================================================


def setup_logging(
    config: LogConfig | None = None,
    root_name: str = "src",
) -> logging.Logger:
    """配置日志系统.

    参数:
        config: 日志配置，为None则使用默认配置
        root_name: 根日志器名称

    返回:
        配置好的日志器

    场景: INFRA.LOG.FORMAT, INFRA.LOG.LEVEL
    """
    config = config or LogConfig()

    # 获取或创建日志器
    logger = logging.getLogger(root_name)
    logger.setLevel(config.level.to_logging_level())

    # 清除现有处理器
    logger.handlers.clear()

    # 添加控制台处理器
    if config.console_output:
        console_handler = create_console_handler(
            level=config.level.to_logging_level(),
            format_type=config.format,
        )
        logger.addHandler(console_handler)

    # 添加文件处理器
    if config.file_output:
        log_file = (
            Path(config.log_dir)
            / f"{root_name}_{datetime.now(UTC).strftime('%Y%m%d')}.log"
        )
        file_handler = create_file_handler(
            str(log_file),
            level=config.level.to_logging_level(),
            format_type=config.format,
            encoding=config.encoding,
            max_bytes=config.max_file_size * 1024 * 1024,
            backup_count=config.backup_count,
        )
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取日志器.

    参数:
        name: 日志器名称

    返回:
        日志器实例
    """
    return logging.getLogger(name)


def set_log_level(level: LogLevel | str, logger_name: str = "src") -> None:
    """设置日志级别.

    参数:
        level: 日志级别
        logger_name: 日志器名称

    场景: INFRA.LOG.LEVEL
    """
    if isinstance(level, str):
        level = LogLevel(level.upper())

    logger = logging.getLogger(logger_name)
    logger.setLevel(level.to_logging_level())

    # 同步更新所有处理器级别
    for handler in logger.handlers:
        handler.setLevel(level.to_logging_level())


def get_log_level(logger_name: str = "src") -> LogLevel:
    """获取日志级别.

    参数:
        logger_name: 日志器名称

    返回:
        当前日志级别
    """
    logger = logging.getLogger(logger_name)
    level = logger.level

    level_map = {
        logging.DEBUG: LogLevel.DEBUG,
        logging.INFO: LogLevel.INFO,
        logging.WARNING: LogLevel.WARNING,
        logging.ERROR: LogLevel.ERROR,
        logging.CRITICAL: LogLevel.CRITICAL,
    }

    return level_map.get(level, LogLevel.INFO)


# =============================================================================
# 环境变量加载
# =============================================================================


def load_log_config_from_env() -> LogConfig:
    """从环境变量加载日志配置.

    环境变量:
        LOG_LEVEL: 日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        LOG_FORMAT: 日志格式 (simple/verbose/json)
        LOG_DIR: 日志目录
        LOG_CONSOLE: 是否输出到控制台 (true/false)
        LOG_FILE: 是否输出到文件 (true/false)

    返回:
        日志配置
    """
    level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
    format_str = os.environ.get("LOG_FORMAT", "simple").lower()
    log_dir = os.environ.get("LOG_DIR", "logs")
    console_str = os.environ.get("LOG_CONSOLE", "true").lower()
    file_str = os.environ.get("LOG_FILE", "false").lower()

    try:
        level = LogLevel(level_str)
    except ValueError:
        level = LogLevel.INFO

    try:
        fmt = LogFormat(format_str)
    except ValueError:
        fmt = LogFormat.SIMPLE

    return LogConfig(
        level=level,
        format=fmt,
        log_dir=log_dir,
        console_output=console_str == "true",
        file_output=file_str == "true",
    )


# =============================================================================
# 便捷函数
# =============================================================================


def debug(msg: str, *args: Any, logger_name: str = "src", **kwargs: Any) -> None:
    """记录DEBUG级别日志."""
    logging.getLogger(logger_name).debug(msg, *args, **kwargs)


def info(msg: str, *args: Any, logger_name: str = "src", **kwargs: Any) -> None:
    """记录INFO级别日志."""
    logging.getLogger(logger_name).info(msg, *args, **kwargs)


def warning(msg: str, *args: Any, logger_name: str = "src", **kwargs: Any) -> None:
    """记录WARNING级别日志."""
    logging.getLogger(logger_name).warning(msg, *args, **kwargs)


def error(msg: str, *args: Any, logger_name: str = "src", **kwargs: Any) -> None:
    """记录ERROR级别日志."""
    logging.getLogger(logger_name).error(msg, *args, **kwargs)


def critical(msg: str, *args: Any, logger_name: str = "src", **kwargs: Any) -> None:
    """记录CRITICAL级别日志."""
    logging.getLogger(logger_name).critical(msg, *args, **kwargs)
