"""
Configuration management module for Chairman Agents system.

Provides structured configuration with support for:
- YAML file loading
- Environment variable loading
- Global configuration access
- Configuration validation
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml


# =============================================================================
# Configuration Exceptions
# =============================================================================


class ConfigurationError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigValidationError(ConfigurationError):
    """Exception raised when configuration validation fails."""

    def __init__(self, field_name: str, message: str) -> None:
        self.field_name = field_name
        self.message = message
        super().__init__(f"Configuration validation failed for '{field_name}': {message}")


class ConfigLoadError(ConfigurationError):
    """Exception raised when configuration loading fails."""

    pass


# =============================================================================
# Configuration Data Classes
# =============================================================================


@dataclass
class LLMConfig:
    """Configuration for Large Language Model integration."""

    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    base_url: str | None = None
    retry_attempts: int = 3
    retry_delay: float = 1.0

    def __post_init__(self) -> None:
        """Validate LLM configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate LLM configuration values."""
        if not self.provider:
            raise ConfigValidationError("llm.provider", "Provider cannot be empty")

        if not self.model:
            raise ConfigValidationError("llm.model", "Model cannot be empty")

        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigValidationError(
                "llm.temperature", f"Temperature must be between 0.0 and 2.0, got {self.temperature}"
            )

        if self.max_tokens < 1:
            raise ConfigValidationError(
                "llm.max_tokens", f"Max tokens must be positive, got {self.max_tokens}"
            )

        if self.timeout < 1:
            raise ConfigValidationError("llm.timeout", f"Timeout must be positive, got {self.timeout}")

        if self.retry_attempts < 0:
            raise ConfigValidationError(
                "llm.retry_attempts", f"Retry attempts must be non-negative, got {self.retry_attempts}"
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMConfig:
        """Create LLMConfig from dictionary."""
        return cls(
            provider=data.get("provider", "openai"),
            model=data.get("model", "gpt-4"),
            api_key=data.get("api_key"),
            temperature=float(data.get("temperature", 0.7)),
            max_tokens=int(data.get("max_tokens", 4096)),
            timeout=int(data.get("timeout", 60)),
            base_url=data.get("base_url"),
            retry_attempts=int(data.get("retry_attempts", 3)),
            retry_delay=float(data.get("retry_delay", 1.0)),
        )

    @classmethod
    def from_env(cls) -> LLMConfig:
        """Create LLMConfig from environment variables."""
        return cls(
            provider=os.getenv("CHAIRMAN_LLM_PROVIDER", "openai"),
            model=os.getenv("CHAIRMAN_LLM_MODEL", "gpt-4"),
            api_key=os.getenv("CHAIRMAN_LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
            temperature=float(os.getenv("CHAIRMAN_LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("CHAIRMAN_LLM_MAX_TOKENS", "4096")),
            timeout=int(os.getenv("CHAIRMAN_LLM_TIMEOUT", "60")),
            base_url=os.getenv("CHAIRMAN_LLM_BASE_URL"),
            retry_attempts=int(os.getenv("CHAIRMAN_LLM_RETRY_ATTEMPTS", "3")),
            retry_delay=float(os.getenv("CHAIRMAN_LLM_RETRY_DELAY", "1.0")),
        )


@dataclass
class TeamConfig:
    """Configuration for agent team composition."""

    size: dict[str, int] = field(default_factory=lambda: {
        "architect": 1,
        "developer": 3,
        "reviewer": 1,
        "tester": 1,
        "security": 1,
    })
    default_expertise_level: str = "senior"
    collaboration_mode: str = "parallel"  # parallel, sequential, hybrid
    communication_protocol: str = "structured"  # structured, natural, hybrid

    def __post_init__(self) -> None:
        """Validate team configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate team configuration values."""
        valid_expertise_levels = {"junior", "mid", "senior", "expert", "principal"}
        if self.default_expertise_level not in valid_expertise_levels:
            raise ConfigValidationError(
                "team.default_expertise_level",
                f"Must be one of {valid_expertise_levels}, got '{self.default_expertise_level}'",
            )

        valid_collaboration_modes = {"parallel", "sequential", "hybrid"}
        if self.collaboration_mode not in valid_collaboration_modes:
            raise ConfigValidationError(
                "team.collaboration_mode",
                f"Must be one of {valid_collaboration_modes}, got '{self.collaboration_mode}'",
            )

        for role, count in self.size.items():
            if count < 0:
                raise ConfigValidationError(
                    f"team.size.{role}", f"Team size must be non-negative, got {count}"
                )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamConfig:
        """Create TeamConfig from dictionary."""
        return cls(
            size=data.get("size", {
                "architect": 1,
                "developer": 3,
                "reviewer": 1,
                "tester": 1,
                "security": 1,
            }),
            default_expertise_level=data.get("default_expertise_level", "senior"),
            collaboration_mode=data.get("collaboration_mode", "parallel"),
            communication_protocol=data.get("communication_protocol", "structured"),
        )

    @classmethod
    def from_env(cls) -> TeamConfig:
        """Create TeamConfig from environment variables."""
        size_str = os.getenv("CHAIRMAN_TEAM_SIZE", "")
        size = {}
        if size_str:
            for pair in size_str.split(","):
                if ":" in pair:
                    role, count = pair.split(":", 1)
                    size[role.strip()] = int(count.strip())

        if not size:
            size = {
                "architect": 1,
                "developer": 3,
                "reviewer": 1,
                "tester": 1,
                "security": 1,
            }

        return cls(
            size=size,
            default_expertise_level=os.getenv("CHAIRMAN_TEAM_EXPERTISE", "senior"),
            collaboration_mode=os.getenv("CHAIRMAN_TEAM_COLLABORATION", "parallel"),
            communication_protocol=os.getenv("CHAIRMAN_TEAM_PROTOCOL", "structured"),
        )


@dataclass
class OrchestratorConfig:
    """Configuration for task orchestration."""

    max_parallel_tasks: int = 5
    max_retries: int = 3
    task_timeout: int = 300
    queue_size: int = 100
    priority_levels: int = 5
    enable_load_balancing: bool = True
    health_check_interval: int = 30
    deadlock_detection: bool = True

    def __post_init__(self) -> None:
        """Validate orchestrator configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate orchestrator configuration values."""
        if self.max_parallel_tasks < 1:
            raise ConfigValidationError(
                "orchestrator.max_parallel_tasks",
                f"Must be at least 1, got {self.max_parallel_tasks}",
            )

        if self.max_retries < 0:
            raise ConfigValidationError(
                "orchestrator.max_retries",
                f"Must be non-negative, got {self.max_retries}",
            )

        if self.task_timeout < 1:
            raise ConfigValidationError(
                "orchestrator.task_timeout",
                f"Must be at least 1 second, got {self.task_timeout}",
            )

        if self.queue_size < 1:
            raise ConfigValidationError(
                "orchestrator.queue_size",
                f"Must be at least 1, got {self.queue_size}",
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrchestratorConfig:
        """Create OrchestratorConfig from dictionary."""
        return cls(
            max_parallel_tasks=int(data.get("max_parallel_tasks", 5)),
            max_retries=int(data.get("max_retries", 3)),
            task_timeout=int(data.get("task_timeout", 300)),
            queue_size=int(data.get("queue_size", 100)),
            priority_levels=int(data.get("priority_levels", 5)),
            enable_load_balancing=bool(data.get("enable_load_balancing", True)),
            health_check_interval=int(data.get("health_check_interval", 30)),
            deadlock_detection=bool(data.get("deadlock_detection", True)),
        )

    @classmethod
    def from_env(cls) -> OrchestratorConfig:
        """Create OrchestratorConfig from environment variables."""
        return cls(
            max_parallel_tasks=int(os.getenv("CHAIRMAN_ORCH_MAX_PARALLEL", "5")),
            max_retries=int(os.getenv("CHAIRMAN_ORCH_MAX_RETRIES", "3")),
            task_timeout=int(os.getenv("CHAIRMAN_ORCH_TIMEOUT", "300")),
            queue_size=int(os.getenv("CHAIRMAN_ORCH_QUEUE_SIZE", "100")),
            priority_levels=int(os.getenv("CHAIRMAN_ORCH_PRIORITY_LEVELS", "5")),
            enable_load_balancing=os.getenv("CHAIRMAN_ORCH_LOAD_BALANCE", "true").lower() == "true",
            health_check_interval=int(os.getenv("CHAIRMAN_ORCH_HEALTH_INTERVAL", "30")),
            deadlock_detection=os.getenv("CHAIRMAN_ORCH_DEADLOCK_DETECT", "true").lower() == "true",
        )


@dataclass
class QualityConfig:
    """Configuration for quality assurance."""

    min_confidence: float = 0.7
    require_review: bool = True
    min_test_coverage: float = 0.8
    max_complexity: int = 10
    enable_static_analysis: bool = True
    enable_security_scan: bool = True
    auto_fix_style: bool = True
    review_timeout: int = 600

    def __post_init__(self) -> None:
        """Validate quality configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate quality configuration values."""
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ConfigValidationError(
                "quality.min_confidence",
                f"Must be between 0.0 and 1.0, got {self.min_confidence}",
            )

        if not 0.0 <= self.min_test_coverage <= 1.0:
            raise ConfigValidationError(
                "quality.min_test_coverage",
                f"Must be between 0.0 and 1.0, got {self.min_test_coverage}",
            )

        if self.max_complexity < 1:
            raise ConfigValidationError(
                "quality.max_complexity",
                f"Must be at least 1, got {self.max_complexity}",
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityConfig:
        """Create QualityConfig from dictionary."""
        return cls(
            min_confidence=float(data.get("min_confidence", 0.7)),
            require_review=bool(data.get("require_review", True)),
            min_test_coverage=float(data.get("min_test_coverage", 0.8)),
            max_complexity=int(data.get("max_complexity", 10)),
            enable_static_analysis=bool(data.get("enable_static_analysis", True)),
            enable_security_scan=bool(data.get("enable_security_scan", True)),
            auto_fix_style=bool(data.get("auto_fix_style", True)),
            review_timeout=int(data.get("review_timeout", 600)),
        )

    @classmethod
    def from_env(cls) -> QualityConfig:
        """Create QualityConfig from environment variables."""
        return cls(
            min_confidence=float(os.getenv("CHAIRMAN_QUALITY_MIN_CONFIDENCE", "0.7")),
            require_review=os.getenv("CHAIRMAN_QUALITY_REQUIRE_REVIEW", "true").lower() == "true",
            min_test_coverage=float(os.getenv("CHAIRMAN_QUALITY_MIN_COVERAGE", "0.8")),
            max_complexity=int(os.getenv("CHAIRMAN_QUALITY_MAX_COMPLEXITY", "10")),
            enable_static_analysis=os.getenv("CHAIRMAN_QUALITY_STATIC_ANALYSIS", "true").lower() == "true",
            enable_security_scan=os.getenv("CHAIRMAN_QUALITY_SECURITY_SCAN", "true").lower() == "true",
            auto_fix_style=os.getenv("CHAIRMAN_QUALITY_AUTO_FIX", "true").lower() == "true",
            review_timeout=int(os.getenv("CHAIRMAN_QUALITY_REVIEW_TIMEOUT", "600")),
        )


@dataclass
class PathConfig:
    """Configuration for file system paths."""

    workspace: Path = field(default_factory=lambda: Path.cwd())
    memory: Path = field(default_factory=lambda: Path.cwd() / ".chairman" / "memory")
    logs: Path = field(default_factory=lambda: Path.cwd() / ".chairman" / "logs")
    cache: Path = field(default_factory=lambda: Path.cwd() / ".chairman" / "cache")
    artifacts: Path = field(default_factory=lambda: Path.cwd() / ".chairman" / "artifacts")

    def __post_init__(self) -> None:
        """Validate and normalize paths after initialization."""
        self.workspace = Path(self.workspace).resolve()
        self.memory = Path(self.memory).resolve()
        self.logs = Path(self.logs).resolve()
        self.cache = Path(self.cache).resolve()
        self.artifacts = Path(self.artifacts).resolve()

    def ensure_directories(self) -> None:
        """Create all configured directories if they don't exist."""
        for path in [self.memory, self.logs, self.cache, self.artifacts]:
            path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PathConfig:
        """Create PathConfig from dictionary."""
        base = Path(data.get("workspace", Path.cwd()))
        return cls(
            workspace=base,
            memory=Path(data.get("memory", base / ".chairman" / "memory")),
            logs=Path(data.get("logs", base / ".chairman" / "logs")),
            cache=Path(data.get("cache", base / ".chairman" / "cache")),
            artifacts=Path(data.get("artifacts", base / ".chairman" / "artifacts")),
        )

    @classmethod
    def from_env(cls) -> PathConfig:
        """Create PathConfig from environment variables."""
        workspace = Path(os.getenv("CHAIRMAN_WORKSPACE", str(Path.cwd())))
        return cls(
            workspace=workspace,
            memory=Path(os.getenv("CHAIRMAN_MEMORY_PATH", str(workspace / ".chairman" / "memory"))),
            logs=Path(os.getenv("CHAIRMAN_LOGS_PATH", str(workspace / ".chairman" / "logs"))),
            cache=Path(os.getenv("CHAIRMAN_CACHE_PATH", str(workspace / ".chairman" / "cache"))),
            artifacts=Path(os.getenv("CHAIRMAN_ARTIFACTS_PATH", str(workspace / ".chairman" / "artifacts"))),
        )


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_rotation: str = "1 day"
    max_files: int = 7
    enable_console: bool = True
    enable_file: bool = True
    enable_json: bool = False

    def __post_init__(self) -> None:
        """Validate logging configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate logging configuration values."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.level.upper() not in valid_levels:
            raise ConfigValidationError(
                "logging.level",
                f"Must be one of {valid_levels}, got '{self.level}'",
            )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoggingConfig:
        """Create LoggingConfig from dictionary."""
        return cls(
            level=data.get("level", "INFO"),
            format=data.get("format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"),
            date_format=data.get("date_format", "%Y-%m-%d %H:%M:%S"),
            file_rotation=data.get("file_rotation", "1 day"),
            max_files=int(data.get("max_files", 7)),
            enable_console=bool(data.get("enable_console", True)),
            enable_file=bool(data.get("enable_file", True)),
            enable_json=bool(data.get("enable_json", False)),
        )

    @classmethod
    def from_env(cls) -> LoggingConfig:
        """Create LoggingConfig from environment variables."""
        return cls(
            level=os.getenv("CHAIRMAN_LOG_LEVEL", "INFO"),
            format=os.getenv(
                "CHAIRMAN_LOG_FORMAT",
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            ),
            date_format=os.getenv("CHAIRMAN_LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
            file_rotation=os.getenv("CHAIRMAN_LOG_ROTATION", "1 day"),
            max_files=int(os.getenv("CHAIRMAN_LOG_MAX_FILES", "7")),
            enable_console=os.getenv("CHAIRMAN_LOG_CONSOLE", "true").lower() == "true",
            enable_file=os.getenv("CHAIRMAN_LOG_FILE", "true").lower() == "true",
            enable_json=os.getenv("CHAIRMAN_LOG_JSON", "false").lower() == "true",
        )


# =============================================================================
# Main Configuration Class
# =============================================================================


@dataclass
class Config:
    """
    Main configuration class for Chairman Agents system.

    Aggregates all component configurations and provides factory methods
    for loading configuration from various sources.
    """

    llm: LLMConfig = field(default_factory=LLMConfig)
    team: TeamConfig = field(default_factory=TeamConfig)
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Configuration metadata
    version: str = "1.0.0"
    environment: str = "development"

    def __post_init__(self) -> None:
        """Validate overall configuration after initialization."""
        valid_environments = {"development", "staging", "production", "testing"}
        if self.environment not in valid_environments:
            raise ConfigValidationError(
                "environment",
                f"Must be one of {valid_environments}, got '{self.environment}'",
            )

    @classmethod
    def from_yaml(cls, path: Path) -> Config:
        """
        Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file.

        Returns:
            Config instance populated from the YAML file.

        Raises:
            ConfigLoadError: If the file cannot be read or parsed.
        """
        try:
            path = Path(path).resolve()
            if not path.exists():
                raise ConfigLoadError(f"Configuration file not found: {path}")

            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            return cls.from_dict(data)

        except yaml.YAMLError as e:
            raise ConfigLoadError(f"Failed to parse YAML configuration: {e}") from e
        except OSError as e:
            raise ConfigLoadError(f"Failed to read configuration file: {e}") from e

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """
        Create configuration from a dictionary.

        Args:
            data: Dictionary containing configuration values.

        Returns:
            Config instance populated from the dictionary.
        """
        return cls(
            llm=LLMConfig.from_dict(data.get("llm", {})),
            team=TeamConfig.from_dict(data.get("team", {})),
            orchestrator=OrchestratorConfig.from_dict(data.get("orchestrator", {})),
            quality=QualityConfig.from_dict(data.get("quality", {})),
            paths=PathConfig.from_dict(data.get("paths", {})),
            logging=LoggingConfig.from_dict(data.get("logging", {})),
            version=data.get("version", "1.0.0"),
            environment=data.get("environment", "development"),
        )

    @classmethod
    def from_env(cls) -> Config:
        """
        Load configuration from environment variables.

        Environment variables use the CHAIRMAN_ prefix.

        Returns:
            Config instance populated from environment variables.
        """
        return cls(
            llm=LLMConfig.from_env(),
            team=TeamConfig.from_env(),
            orchestrator=OrchestratorConfig.from_env(),
            quality=QualityConfig.from_env(),
            paths=PathConfig.from_env(),
            logging=LoggingConfig.from_env(),
            version=os.getenv("CHAIRMAN_VERSION", "1.0.0"),
            environment=os.getenv("CHAIRMAN_ENVIRONMENT", "development"),
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> Config:
        """
        Load configuration with fallback strategy.

        Priority order:
        1. Specified config file path
        2. CHAIRMAN_CONFIG environment variable
        3. ./chairman.yaml in current directory
        4. ~/.chairman/config.yaml in user home
        5. Environment variables only

        Args:
            config_path: Optional explicit path to configuration file.

        Returns:
            Config instance loaded from the best available source.
        """
        # Priority 1: Explicit path
        if config_path is not None:
            path = Path(config_path)
            if path.exists():
                return cls.from_yaml(path)

        # Priority 2: Environment variable
        env_path = os.getenv("CHAIRMAN_CONFIG")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return cls.from_yaml(path)

        # Priority 3: Current directory
        local_path = Path.cwd() / "chairman.yaml"
        if local_path.exists():
            return cls.from_yaml(local_path)

        # Priority 4: User home directory
        home_path = Path.home() / ".chairman" / "config.yaml"
        if home_path.exists():
            return cls.from_yaml(home_path)

        # Priority 5: Environment variables only
        return cls.from_env()

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary representation."""
        return {
            "version": self.version,
            "environment": self.environment,
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout,
                "base_url": self.llm.base_url,
                "retry_attempts": self.llm.retry_attempts,
                "retry_delay": self.llm.retry_delay,
            },
            "team": {
                "size": self.team.size,
                "default_expertise_level": self.team.default_expertise_level,
                "collaboration_mode": self.team.collaboration_mode,
                "communication_protocol": self.team.communication_protocol,
            },
            "orchestrator": {
                "max_parallel_tasks": self.orchestrator.max_parallel_tasks,
                "max_retries": self.orchestrator.max_retries,
                "task_timeout": self.orchestrator.task_timeout,
                "queue_size": self.orchestrator.queue_size,
                "priority_levels": self.orchestrator.priority_levels,
                "enable_load_balancing": self.orchestrator.enable_load_balancing,
                "health_check_interval": self.orchestrator.health_check_interval,
                "deadlock_detection": self.orchestrator.deadlock_detection,
            },
            "quality": {
                "min_confidence": self.quality.min_confidence,
                "require_review": self.quality.require_review,
                "min_test_coverage": self.quality.min_test_coverage,
                "max_complexity": self.quality.max_complexity,
                "enable_static_analysis": self.quality.enable_static_analysis,
                "enable_security_scan": self.quality.enable_security_scan,
                "auto_fix_style": self.quality.auto_fix_style,
                "review_timeout": self.quality.review_timeout,
            },
            "paths": {
                "workspace": str(self.paths.workspace),
                "memory": str(self.paths.memory),
                "logs": str(self.paths.logs),
                "cache": str(self.paths.cache),
                "artifacts": str(self.paths.artifacts),
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
                "date_format": self.logging.date_format,
                "file_rotation": self.logging.file_rotation,
                "max_files": self.logging.max_files,
                "enable_console": self.logging.enable_console,
                "enable_file": self.logging.enable_file,
                "enable_json": self.logging.enable_json,
            },
        }

    def to_yaml(self, path: Path) -> None:
        """
        Save configuration to a YAML file.

        Args:
            path: Path where the YAML file will be written.
        """
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, sort_keys=False)

    def merge(self, other: Config) -> Config:
        """
        Merge another configuration into this one.

        Values from 'other' take precedence.

        Args:
            other: Configuration to merge from.

        Returns:
            New Config instance with merged values.
        """
        merged_dict = self.to_dict()
        other_dict = other.to_dict()

        def deep_merge(base: dict, override: dict) -> dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        return Config.from_dict(deep_merge(merged_dict, other_dict))


# =============================================================================
# Global Configuration Management
# =============================================================================


class _ConfigManager:
    """
    Singleton manager for global configuration access.

    Provides thread-safe access to a shared configuration instance.
    """

    _instance: ClassVar[_ConfigManager | None] = None
    _config: Config | None = None

    def __new__(cls) -> _ConfigManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get(self) -> Config:
        """
        Get the current global configuration.

        Returns:
            The current Config instance.

        Raises:
            ConfigurationError: If no configuration has been set.
        """
        if self._config is None:
            # Auto-load configuration on first access
            self._config = Config.load()
        return self._config

    def set(self, config: Config) -> None:
        """
        Set the global configuration.

        Args:
            config: The Config instance to use globally.
        """
        if not isinstance(config, Config):
            raise ConfigurationError(f"Expected Config instance, got {type(config).__name__}")
        self._config = config

    def reset(self) -> None:
        """Reset the global configuration to None."""
        self._config = None

    def is_initialized(self) -> bool:
        """Check if global configuration has been initialized."""
        return self._config is not None


# Global manager instance
_config_manager = _ConfigManager()


def get_config() -> Config:
    """
    Get the global configuration instance.

    If no configuration has been explicitly set, this will auto-load
    configuration using the Config.load() fallback strategy.

    Returns:
        The current global Config instance.

    Example:
        >>> config = get_config()
        >>> print(config.llm.model)
        'gpt-4'
    """
    return _config_manager.get()


def set_config(config: Config) -> None:
    """
    Set the global configuration instance.

    Args:
        config: The Config instance to use globally.

    Example:
        >>> custom_config = Config(
        ...     llm=LLMConfig(model="gpt-4-turbo"),
        ...     environment="production"
        ... )
        >>> set_config(custom_config)
    """
    _config_manager.set(config)


def reset_config() -> None:
    """
    Reset the global configuration.

    This clears the current configuration, allowing it to be
    reloaded on the next get_config() call.
    """
    _config_manager.reset()


def init_config(
    config_path: Path | None = None,
    *,
    ensure_directories: bool = True,
) -> Config:
    """
    Initialize the global configuration.

    This is a convenience function that loads configuration and
    optionally ensures all required directories exist.

    Args:
        config_path: Optional path to configuration file.
        ensure_directories: Whether to create configured directories.

    Returns:
        The initialized Config instance.

    Example:
        >>> config = init_config(Path("./my-config.yaml"))
        >>> print(config.environment)
        'development'
    """
    config = Config.load(config_path)

    if ensure_directories:
        config.paths.ensure_directories()

    set_config(config)
    return config


# =============================================================================
# Module Exports
# =============================================================================


__all__ = [
    # Exceptions
    "ConfigurationError",
    "ConfigValidationError",
    "ConfigLoadError",
    # Configuration classes
    "LLMConfig",
    "TeamConfig",
    "OrchestratorConfig",
    "QualityConfig",
    "PathConfig",
    "LoggingConfig",
    "Config",
    # Global management functions
    "get_config",
    "set_config",
    "reset_config",
    "init_config",
]
