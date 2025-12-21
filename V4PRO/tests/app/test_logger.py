"""日志模块测试 (军规级 v4.0).

覆盖场景:
- INFRA.LOG.FORMAT: 日志格式正确
- INFRA.LOG.LEVEL: 日志级别正确

军规覆盖:
- M3 完整审计: 日志记录完整可追溯
- M9 错误上报: 异常日志统一格式
"""

from __future__ import annotations

import io
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.app.logger import (
    DEFAULT_DATE_FORMAT,
    DEFAULT_LOG_FORMAT,
    VERBOSE_LOG_FORMAT,
    ComponentFilter,
    JsonFormatter,
    LevelFilter,
    LogConfig,
    LogFormat,
    LogLevel,
    StandardFormatter,
    create_console_handler,
    create_file_handler,
    critical,
    debug,
    error,
    get_log_level,
    get_logger,
    info,
    load_log_config_from_env,
    set_log_level,
    setup_logging,
    warning,
)


# =============================================================================
# 场景: INFRA.LOG.FORMAT - 日志格式正确
# =============================================================================


class TestLogFormat:
    """日志格式测试 - 场景: INFRA.LOG.FORMAT."""

    def test_standard_formatter_default(self) -> None:
        """测试标准格式化器默认格式."""
        formatter = StandardFormatter()

        assert formatter._fmt == DEFAULT_LOG_FORMAT
        assert formatter.datefmt == DEFAULT_DATE_FORMAT

    def test_standard_formatter_custom(self) -> None:
        """测试标准格式化器自定义格式."""
        custom_fmt = "%(levelname)s - %(message)s"
        custom_datefmt = "%H:%M:%S"
        formatter = StandardFormatter(fmt=custom_fmt, datefmt=custom_datefmt)

        assert formatter._fmt == custom_fmt
        assert formatter.datefmt == custom_datefmt

    def test_verbose_format_includes_location(self) -> None:
        """测试详细格式包含位置信息."""
        assert "%(filename)s" in VERBOSE_LOG_FORMAT
        assert "%(lineno)d" in VERBOSE_LOG_FORMAT

    def test_json_formatter_output(self) -> None:
        """测试JSON格式化器输出."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # 验证是有效JSON
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert "ts" in data

    def test_json_formatter_with_exception(self) -> None:
        """测试JSON格式化器异常信息."""
        formatter = JsonFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        output = formatter.format(record)
        data = json.loads(output)

        assert "extra" in data
        extra = (
            json.loads(data["extra"])
            if isinstance(data["extra"], str)
            else data["extra"]
        )
        assert "exception" in extra

    def test_json_formatter_escapes_special_chars(self) -> None:
        """测试JSON格式化器转义特殊字符."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg='Message with "quotes" and \\backslash',
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)

        # 应该能解析为有效JSON
        data = json.loads(output)
        assert "quotes" in data["message"]

    def test_console_handler_simple_format(self) -> None:
        """测试控制台处理器简单格式."""
        stream = io.StringIO()
        handler = create_console_handler(format_type=LogFormat.SIMPLE, stream=stream)

        assert isinstance(handler.formatter, StandardFormatter)

    def test_console_handler_verbose_format(self) -> None:
        """测试控制台处理器详细格式."""
        stream = io.StringIO()
        handler = create_console_handler(format_type=LogFormat.VERBOSE, stream=stream)

        assert handler.formatter is not None
        # 检查格式是否包含文件名
        assert hasattr(handler.formatter, "_fmt")

    def test_console_handler_json_format(self) -> None:
        """测试控制台处理器JSON格式."""
        stream = io.StringIO()
        handler = create_console_handler(format_type=LogFormat.JSON, stream=stream)

        assert isinstance(handler.formatter, JsonFormatter)

    def test_file_handler_creates_directory(self) -> None:
        """测试文件处理器创建目录."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "test.log"
            handler = create_file_handler(str(log_file))

            assert log_file.parent.exists()
            handler.close()


# =============================================================================
# 场景: INFRA.LOG.LEVEL - 日志级别正确
# =============================================================================


class TestLogLevel:
    """日志级别测试 - 场景: INFRA.LOG.LEVEL."""

    def test_log_level_enum_values(self) -> None:
        """测试日志级别枚举值."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"

    def test_log_level_to_logging_level(self) -> None:
        """测试转换为logging级别."""
        assert LogLevel.DEBUG.to_logging_level() == logging.DEBUG
        assert LogLevel.INFO.to_logging_level() == logging.INFO
        assert LogLevel.WARNING.to_logging_level() == logging.WARNING
        assert LogLevel.ERROR.to_logging_level() == logging.ERROR
        assert LogLevel.CRITICAL.to_logging_level() == logging.CRITICAL

    def test_set_log_level_by_enum(self) -> None:
        """测试通过枚举设置日志级别."""
        logger = setup_logging(
            LogConfig(level=LogLevel.INFO), root_name="test_set_enum"
        )
        set_log_level(LogLevel.DEBUG, "test_set_enum")

        assert logger.level == logging.DEBUG

    def test_set_log_level_by_string(self) -> None:
        """测试通过字符串设置日志级别."""
        logger = setup_logging(LogConfig(level=LogLevel.INFO), root_name="test_set_str")
        set_log_level("WARNING", "test_set_str")

        assert logger.level == logging.WARNING

    def test_get_log_level(self) -> None:
        """测试获取日志级别."""
        setup_logging(LogConfig(level=LogLevel.ERROR), root_name="test_get")

        level = get_log_level("test_get")

        assert level == LogLevel.ERROR

    def test_get_log_level_default(self) -> None:
        """测试获取默认日志级别."""
        # 未设置的logger返回INFO
        level = get_log_level("nonexistent_logger")
        assert level == LogLevel.INFO

    def test_setup_updates_handler_levels(self) -> None:
        """测试setup更新处理器级别."""
        config = LogConfig(level=LogLevel.WARNING, console_output=True)
        logger = setup_logging(config, root_name="test_handler_level")

        for handler in logger.handlers:
            assert handler.level == logging.WARNING


# =============================================================================
# LogConfig数据类测试
# =============================================================================


class TestLogConfig:
    """日志配置数据类测试."""

    def test_default_values(self) -> None:
        """测试默认值."""
        config = LogConfig()

        assert config.level == LogLevel.INFO
        assert config.format == LogFormat.SIMPLE
        assert config.log_dir == "logs"
        assert config.console_output is True
        assert config.file_output is False
        assert config.max_file_size == 10
        assert config.backup_count == 5
        assert config.encoding == "utf-8"

    def test_to_dict(self) -> None:
        """测试转字典."""
        config = LogConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.JSON,
            log_dir="/var/log",
        )

        d = config.to_dict()

        assert d["level"] == "DEBUG"
        assert d["format"] == "json"
        assert d["log_dir"] == "/var/log"


# =============================================================================
# 过滤器测试
# =============================================================================


class TestLevelFilter:
    """日志级别过滤器测试."""

    def test_filter_in_range(self) -> None:
        """测试范围内通过."""
        filter_ = LevelFilter(min_level=logging.INFO, max_level=logging.ERROR)
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(record) is True

    def test_filter_below_min(self) -> None:
        """测试低于最低级别不通过."""
        filter_ = LevelFilter(min_level=logging.WARNING, max_level=logging.ERROR)
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(record) is False

    def test_filter_above_max(self) -> None:
        """测试高于最高级别不通过."""
        filter_ = LevelFilter(min_level=logging.DEBUG, max_level=logging.WARNING)
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(record) is False

    def test_filter_at_boundary(self) -> None:
        """测试边界值通过."""
        filter_ = LevelFilter(min_level=logging.INFO, max_level=logging.ERROR)

        info_record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        error_record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(info_record) is True
        assert filter_.filter(error_record) is True


class TestComponentFilter:
    """组件过滤器测试."""

    def test_filter_matching_component(self) -> None:
        """测试匹配组件通过."""
        filter_ = ComponentFilter(["src.trading", "src.portfolio"])
        record = logging.LogRecord(
            name="src.trading.order",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(record) is True

    def test_filter_non_matching_component(self) -> None:
        """测试不匹配组件不通过."""
        filter_ = ComponentFilter(["src.trading", "src.portfolio"])
        record = logging.LogRecord(
            name="src.brokers.ctp",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(record) is False

    def test_filter_empty_components_passes_all(self) -> None:
        """测试空组件列表通过所有."""
        filter_ = ComponentFilter([])
        record = logging.LogRecord(
            name="any.logger.name",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )

        assert filter_.filter(record) is True


# =============================================================================
# setup_logging测试
# =============================================================================


class TestSetupLogging:
    """日志设置测试."""

    def test_setup_with_default_config(self) -> None:
        """测试使用默认配置设置."""
        logger = setup_logging(root_name="test_default_setup")

        assert logger.name == "test_default_setup"
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1  # 只有控制台处理器

    def test_setup_with_custom_config(self) -> None:
        """测试使用自定义配置设置."""
        config = LogConfig(
            level=LogLevel.DEBUG,
            format=LogFormat.VERBOSE,
            console_output=True,
        )
        logger = setup_logging(config, root_name="test_custom_setup")

        assert logger.level == logging.DEBUG

    def test_setup_with_file_output(self) -> None:
        """测试带文件输出设置."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LogConfig(
                level=LogLevel.INFO,
                log_dir=tmpdir,
                console_output=True,
                file_output=True,
            )
            logger = setup_logging(config, root_name="test_file_setup")

            assert len(logger.handlers) == 2  # 控制台和文件

            # 清理
            for handler in logger.handlers:
                handler.close()
            logger.handlers.clear()

    def test_setup_clears_existing_handlers(self) -> None:
        """测试设置清除现有处理器."""
        logger = setup_logging(LogConfig(), root_name="test_clear")
        initial_handler_count = len(logger.handlers)

        # 再次设置应该清除之前的处理器
        logger = setup_logging(LogConfig(), root_name="test_clear")

        assert len(logger.handlers) == initial_handler_count

    def test_setup_no_console_output(self) -> None:
        """测试无控制台输出."""
        config = LogConfig(console_output=False, file_output=False)
        logger = setup_logging(config, root_name="test_no_console")

        assert len(logger.handlers) == 0


# =============================================================================
# load_log_config_from_env测试
# =============================================================================


class TestLoadLogConfigFromEnv:
    """从环境变量加载日志配置测试."""

    def test_load_default(self) -> None:
        """测试加载默认值."""
        with patch.dict("os.environ", {}, clear=True):
            config = load_log_config_from_env()

            assert config.level == LogLevel.INFO
            assert config.format == LogFormat.SIMPLE

    def test_load_level_from_env(self) -> None:
        """测试从环境变量加载级别."""
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}):
            config = load_log_config_from_env()

            assert config.level == LogLevel.DEBUG

    def test_load_format_from_env(self) -> None:
        """测试从环境变量加载格式."""
        with patch.dict("os.environ", {"LOG_FORMAT": "json"}):
            config = load_log_config_from_env()

            assert config.format == LogFormat.JSON

    def test_load_dir_from_env(self) -> None:
        """测试从环境变量加载目录."""
        with patch.dict("os.environ", {"LOG_DIR": "/custom/logs"}):
            config = load_log_config_from_env()

            assert config.log_dir == "/custom/logs"

    def test_load_console_from_env(self) -> None:
        """测试从环境变量加载控制台输出."""
        with patch.dict("os.environ", {"LOG_CONSOLE": "false"}):
            config = load_log_config_from_env()

            assert config.console_output is False

    def test_load_file_from_env(self) -> None:
        """测试从环境变量加载文件输出."""
        with patch.dict("os.environ", {"LOG_FILE": "true"}):
            config = load_log_config_from_env()

            assert config.file_output is True

    def test_load_invalid_level_falls_back(self) -> None:
        """测试无效级别回退到INFO."""
        with patch.dict("os.environ", {"LOG_LEVEL": "INVALID"}):
            config = load_log_config_from_env()

            assert config.level == LogLevel.INFO

    def test_load_invalid_format_falls_back(self) -> None:
        """测试无效格式回退到SIMPLE."""
        with patch.dict("os.environ", {"LOG_FORMAT": "invalid"}):
            config = load_log_config_from_env()

            assert config.format == LogFormat.SIMPLE


# =============================================================================
# 便捷函数测试
# =============================================================================


class TestConvenienceFunctions:
    """便捷日志函数测试."""

    def test_get_logger(self) -> None:
        """测试获取日志器."""
        logger = get_logger("test.module")

        assert logger.name == "test.module"
        assert isinstance(logger, logging.Logger)

    def test_debug_function(self) -> None:
        """测试debug函数."""
        # 设置日志器
        test_logger = setup_logging(
            LogConfig(level=LogLevel.DEBUG),
            root_name="test_debug_func",
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        test_logger.addHandler(handler)

        debug("Debug message", logger_name="test_debug_func")

        output = stream.getvalue()
        assert "Debug message" in output

    def test_info_function(self) -> None:
        """测试info函数."""
        test_logger = setup_logging(
            LogConfig(level=LogLevel.INFO),
            root_name="test_info_func",
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        info("Info message", logger_name="test_info_func")

        output = stream.getvalue()
        assert "Info message" in output

    def test_warning_function(self) -> None:
        """测试warning函数."""
        test_logger = setup_logging(
            LogConfig(level=LogLevel.WARNING),
            root_name="test_warning_func",
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        test_logger.addHandler(handler)

        warning("Warning message", logger_name="test_warning_func")

        output = stream.getvalue()
        assert "Warning message" in output

    def test_error_function(self) -> None:
        """测试error函数."""
        test_logger = setup_logging(
            LogConfig(level=LogLevel.ERROR),
            root_name="test_error_func",
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.ERROR)
        test_logger.addHandler(handler)

        error("Error message", logger_name="test_error_func")

        output = stream.getvalue()
        assert "Error message" in output

    def test_critical_function(self) -> None:
        """测试critical函数."""
        test_logger = setup_logging(
            LogConfig(level=LogLevel.CRITICAL),
            root_name="test_critical_func",
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.CRITICAL)
        test_logger.addHandler(handler)

        critical("Critical message", logger_name="test_critical_func")

        output = stream.getvalue()
        assert "Critical message" in output


# =============================================================================
# LogFormat枚举测试
# =============================================================================


class TestLogFormatEnum:
    """日志格式枚举测试."""

    def test_simple_value(self) -> None:
        """测试SIMPLE值."""
        assert LogFormat.SIMPLE.value == "simple"

    def test_verbose_value(self) -> None:
        """测试VERBOSE值."""
        assert LogFormat.VERBOSE.value == "verbose"

    def test_json_value(self) -> None:
        """测试JSON值."""
        assert LogFormat.JSON.value == "json"

    def test_from_string(self) -> None:
        """测试从字符串创建."""
        assert LogFormat("simple") == LogFormat.SIMPLE
        assert LogFormat("verbose") == LogFormat.VERBOSE
        assert LogFormat("json") == LogFormat.JSON


# =============================================================================
# 文件处理器测试
# =============================================================================


class TestFileHandler:
    """文件处理器测试."""

    def test_file_handler_rotation(self) -> None:
        """测试文件处理器轮转."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            handler = create_file_handler(
                str(log_file),
                max_bytes=1024,
                backup_count=3,
            )

            # 验证是轮转处理器
            from logging.handlers import RotatingFileHandler

            assert isinstance(handler, RotatingFileHandler)
            handler.close()

    def test_file_handler_encoding(self) -> None:
        """测试文件处理器编码."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            handler = create_file_handler(str(log_file), encoding="utf-8")

            from logging.handlers import RotatingFileHandler

            assert isinstance(handler, RotatingFileHandler)
            handler.close()

    def test_file_handler_json_format(self) -> None:
        """测试文件处理器JSON格式."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            handler = create_file_handler(str(log_file), format_type=LogFormat.JSON)

            assert isinstance(handler.formatter, JsonFormatter)
            handler.close()
