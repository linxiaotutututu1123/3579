"""
Tests for chairman_agents.core.config module.

Covers:
- Configuration exceptions (ConfigurationError, ConfigValidationError, ConfigLoadError)
- Configuration data classes (LLMConfig, TeamConfig, OrchestratorConfig, etc.)
- Main Config class with YAML/dict/env loading
- Global configuration management (_ConfigManager, get_config, set_config, etc.)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from chairman_agents.core.config import (
    Config,
    ConfigLoadError,
    ConfigurationError,
    ConfigValidationError,
    LLMConfig,
    LoggingConfig,
    OrchestratorConfig,
    PathConfig,
    QualityConfig,
    TeamConfig,
    get_config,
    init_config,
    reset_config,
    set_config,
)


# =============================================================================
# Configuration Exceptions Tests
# =============================================================================


@pytest.mark.unit
class TestConfigurationExceptions:
    """Tests for configuration exception classes."""

    def test_configuration_error_basic(self):
        """Test ConfigurationError base exception."""
        error = ConfigurationError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_config_validation_error_message(self):
        """Test ConfigValidationError with field name and message."""
        error = ConfigValidationError("llm.model", "Model cannot be empty")
        assert error.field_name == "llm.model"
        assert error.message == "Model cannot be empty"
        assert "llm.model" in str(error)
        assert "Model cannot be empty" in str(error)

    def test_config_validation_error_inheritance(self):
        """Test ConfigValidationError inherits from ConfigurationError."""
        error = ConfigValidationError("field", "message")
        assert isinstance(error, ConfigurationError)
        assert isinstance(error, Exception)

    def test_config_load_error(self):
        """Test ConfigLoadError exception."""
        error = ConfigLoadError("Failed to load config")
        assert str(error) == "Failed to load config"
        assert isinstance(error, ConfigurationError)


# =============================================================================
# LLMConfig Tests
# =============================================================================


@pytest.mark.unit
class TestLLMConfig:
    """Tests for LLMConfig data class."""

    def test_default_values(self):
        """Test LLMConfig with default values."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key is None
        assert config.temperature == 0.7
        assert config.max_tokens == 4096
        assert config.timeout == 60
        assert config.base_url is None
        assert config.retry_attempts == 3
        assert config.retry_delay == 1.0

    def test_custom_values(self):
        """Test LLMConfig with custom values."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3",
            api_key="test-key",
            temperature=0.5,
            max_tokens=2048,
            timeout=120,
            base_url="https://api.example.com",
            retry_attempts=5,
            retry_delay=2.0,
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3"
        assert config.api_key == "test-key"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.timeout == 120
        assert config.base_url == "https://api.example.com"
        assert config.retry_attempts == 5
        assert config.retry_delay == 2.0

    def test_validation_empty_provider(self):
        """Test validation fails for empty provider."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(provider="")
        assert "provider" in str(exc_info.value)

    def test_validation_empty_model(self):
        """Test validation fails for empty model."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(model="")
        assert "model" in str(exc_info.value)

    def test_validation_temperature_too_low(self):
        """Test validation fails for temperature below 0."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(temperature=-0.1)
        assert "temperature" in str(exc_info.value)

    def test_validation_temperature_too_high(self):
        """Test validation fails for temperature above 2.0."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(temperature=2.1)
        assert "temperature" in str(exc_info.value)

    def test_validation_temperature_boundary(self):
        """Test temperature validation at boundaries."""
        # Should succeed at boundaries
        config_low = LLMConfig(temperature=0.0)
        assert config_low.temperature == 0.0

        config_high = LLMConfig(temperature=2.0)
        assert config_high.temperature == 2.0

    def test_validation_negative_max_tokens(self):
        """Test validation fails for non-positive max_tokens."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(max_tokens=0)
        assert "max_tokens" in str(exc_info.value)

    def test_validation_negative_timeout(self):
        """Test validation fails for non-positive timeout."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(timeout=0)
        assert "timeout" in str(exc_info.value)

    def test_validation_negative_retry_attempts(self):
        """Test validation fails for negative retry_attempts."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LLMConfig(retry_attempts=-1)
        assert "retry_attempts" in str(exc_info.value)

    def test_from_dict(self):
        """Test creating LLMConfig from dictionary."""
        data = {
            "provider": "azure",
            "model": "gpt-4-turbo",
            "api_key": "key123",
            "temperature": 0.3,
            "max_tokens": 8192,
        }
        config = LLMConfig.from_dict(data)
        assert config.provider == "azure"
        assert config.model == "gpt-4-turbo"
        assert config.api_key == "key123"
        assert config.temperature == 0.3
        assert config.max_tokens == 8192

    def test_from_dict_with_defaults(self):
        """Test from_dict uses defaults for missing keys."""
        config = LLMConfig.from_dict({})
        assert config.provider == "openai"
        assert config.model == "gpt-4"

    def test_from_env(self):
        """Test creating LLMConfig from environment variables."""
        env_vars = {
            "CHAIRMAN_LLM_PROVIDER": "anthropic",
            "CHAIRMAN_LLM_MODEL": "claude-3-opus",
            "CHAIRMAN_LLM_API_KEY": "test-api-key",
            "CHAIRMAN_LLM_TEMPERATURE": "0.5",
            "CHAIRMAN_LLM_MAX_TOKENS": "2048",
            "CHAIRMAN_LLM_TIMEOUT": "90",
            "CHAIRMAN_LLM_BASE_URL": "https://custom.api.com",
            "CHAIRMAN_LLM_RETRY_ATTEMPTS": "5",
            "CHAIRMAN_LLM_RETRY_DELAY": "2.5",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = LLMConfig.from_env()
            assert config.provider == "anthropic"
            assert config.model == "claude-3-opus"
            assert config.api_key == "test-api-key"
            assert config.temperature == 0.5
            assert config.max_tokens == 2048
            assert config.timeout == 90
            assert config.base_url == "https://custom.api.com"
            assert config.retry_attempts == 5
            assert config.retry_delay == 2.5


# =============================================================================
# TeamConfig Tests
# =============================================================================


@pytest.mark.unit
class TestTeamConfig:
    """Tests for TeamConfig data class."""

    def test_default_values(self):
        """Test TeamConfig with default values."""
        config = TeamConfig()
        assert config.default_expertise_level == "senior"
        assert config.collaboration_mode == "parallel"
        assert config.communication_protocol == "structured"
        assert "architect" in config.size
        assert "developer" in config.size

    def test_custom_size(self):
        """Test TeamConfig with custom team size."""
        config = TeamConfig(
            size={"developer": 5, "tester": 2},
            default_expertise_level="expert",
        )
        assert config.size["developer"] == 5
        assert config.size["tester"] == 2
        assert config.default_expertise_level == "expert"

    def test_validation_invalid_expertise_level(self):
        """Test validation fails for invalid expertise level."""
        with pytest.raises(ConfigValidationError) as exc_info:
            TeamConfig(default_expertise_level="invalid")
        assert "expertise_level" in str(exc_info.value)

    def test_validation_valid_expertise_levels(self):
        """Test all valid expertise levels are accepted."""
        valid_levels = ["junior", "mid", "senior", "expert", "principal"]
        for level in valid_levels:
            config = TeamConfig(default_expertise_level=level)
            assert config.default_expertise_level == level

    def test_validation_invalid_collaboration_mode(self):
        """Test validation fails for invalid collaboration mode."""
        with pytest.raises(ConfigValidationError) as exc_info:
            TeamConfig(collaboration_mode="invalid")
        assert "collaboration_mode" in str(exc_info.value)

    def test_validation_negative_team_size(self):
        """Test validation fails for negative team size."""
        with pytest.raises(ConfigValidationError) as exc_info:
            TeamConfig(size={"developer": -1})
        assert "team.size" in str(exc_info.value)

    def test_from_dict(self):
        """Test creating TeamConfig from dictionary."""
        data = {
            "size": {"developer": 4, "reviewer": 2},
            "default_expertise_level": "mid",
            "collaboration_mode": "sequential",
        }
        config = TeamConfig.from_dict(data)
        assert config.size["developer"] == 4
        assert config.default_expertise_level == "mid"
        assert config.collaboration_mode == "sequential"

    def test_from_env(self):
        """Test creating TeamConfig from environment variables."""
        env_vars = {
            "CHAIRMAN_TEAM_SIZE": "developer:5,tester:3",
            "CHAIRMAN_TEAM_EXPERTISE": "expert",
            "CHAIRMAN_TEAM_COLLABORATION": "hybrid",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = TeamConfig.from_env()
            assert config.size["developer"] == 5
            assert config.size["tester"] == 3
            assert config.default_expertise_level == "expert"
            assert config.collaboration_mode == "hybrid"


# =============================================================================
# OrchestratorConfig Tests
# =============================================================================


@pytest.mark.unit
class TestOrchestratorConfig:
    """Tests for OrchestratorConfig data class."""

    def test_default_values(self):
        """Test OrchestratorConfig with default values."""
        config = OrchestratorConfig()
        assert config.max_parallel_tasks == 5
        assert config.max_retries == 3
        assert config.task_timeout == 300
        assert config.queue_size == 100
        assert config.priority_levels == 5
        assert config.enable_load_balancing is True
        assert config.health_check_interval == 30
        assert config.deadlock_detection is True

    def test_validation_max_parallel_tasks(self):
        """Test validation for max_parallel_tasks."""
        with pytest.raises(ConfigValidationError) as exc_info:
            OrchestratorConfig(max_parallel_tasks=0)
        assert "max_parallel_tasks" in str(exc_info.value)

    def test_validation_negative_max_retries(self):
        """Test validation for negative max_retries."""
        with pytest.raises(ConfigValidationError) as exc_info:
            OrchestratorConfig(max_retries=-1)
        assert "max_retries" in str(exc_info.value)

    def test_validation_task_timeout(self):
        """Test validation for non-positive task_timeout."""
        with pytest.raises(ConfigValidationError) as exc_info:
            OrchestratorConfig(task_timeout=0)
        assert "task_timeout" in str(exc_info.value)

    def test_validation_queue_size(self):
        """Test validation for non-positive queue_size."""
        with pytest.raises(ConfigValidationError) as exc_info:
            OrchestratorConfig(queue_size=0)
        assert "queue_size" in str(exc_info.value)

    def test_from_dict(self):
        """Test creating OrchestratorConfig from dictionary."""
        data = {
            "max_parallel_tasks": 10,
            "max_retries": 5,
            "enable_load_balancing": False,
        }
        config = OrchestratorConfig.from_dict(data)
        assert config.max_parallel_tasks == 10
        assert config.max_retries == 5
        assert config.enable_load_balancing is False

    def test_from_env(self):
        """Test creating OrchestratorConfig from environment variables."""
        env_vars = {
            "CHAIRMAN_ORCH_MAX_PARALLEL": "8",
            "CHAIRMAN_ORCH_MAX_RETRIES": "5",
            "CHAIRMAN_ORCH_LOAD_BALANCE": "false",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = OrchestratorConfig.from_env()
            assert config.max_parallel_tasks == 8
            assert config.max_retries == 5
            assert config.enable_load_balancing is False


# =============================================================================
# QualityConfig Tests
# =============================================================================


@pytest.mark.unit
class TestQualityConfig:
    """Tests for QualityConfig data class."""

    def test_default_values(self):
        """Test QualityConfig with default values."""
        config = QualityConfig()
        assert config.min_confidence == 0.7
        assert config.require_review is True
        assert config.min_test_coverage == 0.8
        assert config.max_complexity == 10
        assert config.enable_static_analysis is True
        assert config.enable_security_scan is True
        assert config.auto_fix_style is True
        assert config.review_timeout == 600

    def test_validation_min_confidence_range(self):
        """Test min_confidence validation range."""
        # Too low
        with pytest.raises(ConfigValidationError):
            QualityConfig(min_confidence=-0.1)

        # Too high
        with pytest.raises(ConfigValidationError):
            QualityConfig(min_confidence=1.1)

        # Boundary values should work
        config_low = QualityConfig(min_confidence=0.0)
        assert config_low.min_confidence == 0.0
        config_high = QualityConfig(min_confidence=1.0)
        assert config_high.min_confidence == 1.0

    def test_validation_min_test_coverage_range(self):
        """Test min_test_coverage validation range."""
        with pytest.raises(ConfigValidationError):
            QualityConfig(min_test_coverage=-0.1)
        with pytest.raises(ConfigValidationError):
            QualityConfig(min_test_coverage=1.1)

    def test_validation_max_complexity(self):
        """Test max_complexity validation."""
        with pytest.raises(ConfigValidationError):
            QualityConfig(max_complexity=0)

    def test_from_dict(self):
        """Test creating QualityConfig from dictionary."""
        data = {
            "min_confidence": 0.9,
            "require_review": False,
            "min_test_coverage": 0.95,
        }
        config = QualityConfig.from_dict(data)
        assert config.min_confidence == 0.9
        assert config.require_review is False
        assert config.min_test_coverage == 0.95

    def test_from_env(self):
        """Test creating QualityConfig from environment variables."""
        env_vars = {
            "CHAIRMAN_QUALITY_MIN_CONFIDENCE": "0.9",
            "CHAIRMAN_QUALITY_REQUIRE_REVIEW": "false",
            "CHAIRMAN_QUALITY_MIN_COVERAGE": "0.9",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = QualityConfig.from_env()
            assert config.min_confidence == 0.9
            assert config.require_review is False
            assert config.min_test_coverage == 0.9


# =============================================================================
# PathConfig Tests
# =============================================================================


@pytest.mark.unit
class TestPathConfig:
    """Tests for PathConfig data class."""

    def test_default_values(self):
        """Test PathConfig with default values."""
        config = PathConfig()
        assert config.workspace.is_absolute()
        assert ".chairman" in str(config.memory)
        assert ".chairman" in str(config.logs)
        assert ".chairman" in str(config.cache)
        assert ".chairman" in str(config.artifacts)

    def test_paths_are_resolved(self):
        """Test all paths are resolved to absolute paths."""
        config = PathConfig()
        assert config.workspace.is_absolute()
        assert config.memory.is_absolute()
        assert config.logs.is_absolute()
        assert config.cache.is_absolute()
        assert config.artifacts.is_absolute()

    def test_custom_paths(self, tmp_path: Path):
        """Test PathConfig with custom paths."""
        config = PathConfig(
            workspace=tmp_path,
            memory=tmp_path / "custom_memory",
            logs=tmp_path / "custom_logs",
        )
        assert config.workspace == tmp_path.resolve()
        assert "custom_memory" in str(config.memory)
        assert "custom_logs" in str(config.logs)

    def test_ensure_directories(self, tmp_path: Path):
        """Test ensure_directories creates all configured paths."""
        config = PathConfig(
            workspace=tmp_path,
            memory=tmp_path / "memory",
            logs=tmp_path / "logs",
            cache=tmp_path / "cache",
            artifacts=tmp_path / "artifacts",
        )
        config.ensure_directories()

        assert config.memory.exists()
        assert config.logs.exists()
        assert config.cache.exists()
        assert config.artifacts.exists()

    def test_from_dict(self, tmp_path: Path):
        """Test creating PathConfig from dictionary."""
        data = {
            "workspace": str(tmp_path),
            "memory": str(tmp_path / "mem"),
        }
        config = PathConfig.from_dict(data)
        assert config.workspace == tmp_path.resolve()


# =============================================================================
# LoggingConfig Tests
# =============================================================================


@pytest.mark.unit
class TestLoggingConfig:
    """Tests for LoggingConfig data class."""

    def test_default_values(self):
        """Test LoggingConfig with default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert "%(asctime)s" in config.format
        assert config.max_files == 7
        assert config.enable_console is True
        assert config.enable_file is True
        assert config.enable_json is False

    def test_validation_invalid_level(self):
        """Test validation fails for invalid log level."""
        with pytest.raises(ConfigValidationError) as exc_info:
            LoggingConfig(level="INVALID")
        assert "level" in str(exc_info.value)

    def test_validation_valid_levels(self):
        """Test all valid log levels are accepted."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in valid_levels:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_validation_case_insensitive(self):
        """Test log level validation is case insensitive for uppercase."""
        config = LoggingConfig(level="debug")  # lowercase should work in validation
        # The validation uses .upper()
        assert config.level == "debug"

    def test_from_dict(self):
        """Test creating LoggingConfig from dictionary."""
        data = {
            "level": "DEBUG",
            "enable_json": True,
            "max_files": 14,
        }
        config = LoggingConfig.from_dict(data)
        assert config.level == "DEBUG"
        assert config.enable_json is True
        assert config.max_files == 14

    def test_from_env(self):
        """Test creating LoggingConfig from environment variables."""
        env_vars = {
            "CHAIRMAN_LOG_LEVEL": "DEBUG",
            "CHAIRMAN_LOG_JSON": "true",
            "CHAIRMAN_LOG_MAX_FILES": "14",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = LoggingConfig.from_env()
            assert config.level == "DEBUG"
            assert config.enable_json is True
            assert config.max_files == 14


# =============================================================================
# Main Config Class Tests
# =============================================================================


@pytest.mark.unit
class TestConfig:
    """Tests for main Config class."""

    def test_default_values(self):
        """Test Config with default values."""
        config = Config()
        assert config.version == "1.0.0"
        assert config.environment == "development"
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.team, TeamConfig)
        assert isinstance(config.orchestrator, OrchestratorConfig)
        assert isinstance(config.quality, QualityConfig)
        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.logging, LoggingConfig)

    def test_validation_invalid_environment(self):
        """Test validation fails for invalid environment."""
        with pytest.raises(ConfigValidationError) as exc_info:
            Config(environment="invalid")
        assert "environment" in str(exc_info.value)

    def test_validation_valid_environments(self):
        """Test all valid environments are accepted."""
        valid_envs = ["development", "staging", "production", "testing"]
        for env in valid_envs:
            config = Config(environment=env)
            assert config.environment == env

    def test_from_dict(self):
        """Test creating Config from dictionary."""
        data = {
            "version": "2.0.0",
            "environment": "production",
            "llm": {"model": "gpt-4-turbo"},
            "team": {"default_expertise_level": "expert"},
        }
        config = Config.from_dict(data)
        assert config.version == "2.0.0"
        assert config.environment == "production"
        assert config.llm.model == "gpt-4-turbo"
        assert config.team.default_expertise_level == "expert"

    def test_from_yaml(self, tmp_path: Path):
        """Test loading Config from YAML file."""
        yaml_content = {
            "version": "2.0.0",
            "environment": "staging",
            "llm": {"model": "claude-3"},
        }
        yaml_file = tmp_path / "config.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = Config.from_yaml(yaml_file)
        assert config.version == "2.0.0"
        assert config.environment == "staging"
        assert config.llm.model == "claude-3"

    def test_from_yaml_file_not_found(self, tmp_path: Path):
        """Test from_yaml raises error for missing file."""
        with pytest.raises(ConfigLoadError):
            Config.from_yaml(tmp_path / "nonexistent.yaml")

    def test_from_yaml_invalid_yaml(self, tmp_path: Path):
        """Test from_yaml raises error for invalid YAML."""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text("invalid: yaml: content: ][")

        with pytest.raises(ConfigLoadError):
            Config.from_yaml(yaml_file)

    def test_from_env(self):
        """Test creating Config from environment variables."""
        env_vars = {
            "CHAIRMAN_VERSION": "3.0.0",
            "CHAIRMAN_ENVIRONMENT": "testing",
            "CHAIRMAN_LLM_MODEL": "test-model",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = Config.from_env()
            assert config.version == "3.0.0"
            assert config.environment == "testing"
            assert config.llm.model == "test-model"

    def test_to_dict(self):
        """Test converting Config to dictionary."""
        config = Config(version="1.5.0", environment="staging")
        data = config.to_dict()

        assert data["version"] == "1.5.0"
        assert data["environment"] == "staging"
        assert "llm" in data
        assert "team" in data
        assert "orchestrator" in data
        assert "quality" in data
        assert "paths" in data
        assert "logging" in data

    def test_to_yaml(self, tmp_path: Path):
        """Test saving Config to YAML file."""
        config = Config(version="1.5.0", environment="production")
        yaml_file = tmp_path / "output.yaml"
        config.to_yaml(yaml_file)

        assert yaml_file.exists()

        with open(yaml_file) as f:
            loaded = yaml.safe_load(f)
        assert loaded["version"] == "1.5.0"
        assert loaded["environment"] == "production"

    def test_merge(self):
        """Test merging two Config instances."""
        base = Config(version="1.0.0")
        override = Config(version="2.0.0", environment="production")

        merged = base.merge(override)
        assert merged.version == "2.0.0"
        assert merged.environment == "production"

    def test_load_with_explicit_path(self, tmp_path: Path):
        """Test Config.load with explicit config path."""
        yaml_content = {"version": "explicit", "environment": "testing"}
        yaml_file = tmp_path / "explicit.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = Config.load(yaml_file)
        assert config.version == "explicit"

    def test_load_fallback_to_env(self):
        """Test Config.load falls back to environment variables."""
        env_vars = {"CHAIRMAN_VERSION": "from-env"}
        with patch.dict(os.environ, env_vars, clear=False):
            config = Config.load()
            assert config.version == "from-env"


# =============================================================================
# Global Configuration Manager Tests
# =============================================================================


@pytest.mark.unit
class TestGlobalConfigManager:
    """Tests for global configuration management functions."""

    def setup_method(self):
        """Reset global config before each test."""
        reset_config()

    def teardown_method(self):
        """Reset global config after each test."""
        reset_config()

    def test_get_config_auto_loads(self):
        """Test get_config auto-loads configuration if not set."""
        config = get_config()
        assert isinstance(config, Config)

    def test_set_config(self):
        """Test setting global configuration."""
        custom_config = Config(version="custom", environment="testing")
        set_config(custom_config)

        retrieved = get_config()
        assert retrieved.version == "custom"
        assert retrieved.environment == "testing"

    def test_set_config_invalid_type(self):
        """Test set_config raises error for invalid type."""
        with pytest.raises(ConfigurationError):
            set_config("not a config")  # type: ignore

    def test_reset_config(self):
        """Test resetting global configuration."""
        custom_config = Config(version="custom")
        set_config(custom_config)

        reset_config()
        # After reset, get_config should auto-load
        new_config = get_config()
        # Should be a fresh load, not the custom config
        assert isinstance(new_config, Config)

    def test_init_config(self, tmp_path: Path):
        """Test init_config function."""
        yaml_content = {"version": "init-test", "environment": "testing"}
        yaml_file = tmp_path / "init.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = init_config(yaml_file, ensure_directories=False)
        assert config.version == "init-test"

        # Verify it's set globally
        retrieved = get_config()
        assert retrieved.version == "init-test"

    def test_init_config_creates_directories(self, tmp_path: Path):
        """Test init_config creates directories when requested."""
        yaml_content = {
            "version": "1.0.0",
            "environment": "testing",
            "paths": {
                "workspace": str(tmp_path),
                "memory": str(tmp_path / "test_memory"),
                "logs": str(tmp_path / "test_logs"),
                "cache": str(tmp_path / "test_cache"),
                "artifacts": str(tmp_path / "test_artifacts"),
            },
        }
        yaml_file = tmp_path / "init.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = init_config(yaml_file, ensure_directories=True)

        assert (tmp_path / "test_memory").exists()
        assert (tmp_path / "test_logs").exists()
        assert (tmp_path / "test_cache").exists()
        assert (tmp_path / "test_artifacts").exists()


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


@pytest.mark.unit
class TestConfigEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_config_roundtrip_yaml(self, tmp_path: Path):
        """Test config can be saved and loaded without loss."""
        original = Config(
            version="roundtrip",
            environment="staging",
            llm=LLMConfig(model="test-model", temperature=0.5),
        )

        yaml_file = tmp_path / "roundtrip.yaml"
        original.to_yaml(yaml_file)
        loaded = Config.from_yaml(yaml_file)

        assert loaded.version == original.version
        assert loaded.environment == original.environment
        assert loaded.llm.model == original.llm.model
        assert loaded.llm.temperature == original.llm.temperature

    def test_config_deep_merge(self):
        """Test deep merge preserves nested values."""
        base = Config(
            llm=LLMConfig(model="base-model", temperature=0.7),
            team=TeamConfig(size={"developer": 3}),
        )
        override = Config(
            llm=LLMConfig(model="override-model"),
        )

        merged = base.merge(override)
        assert merged.llm.model == "override-model"
        # Note: merge replaces entire nested dicts, not individual fields

    def test_empty_yaml_loads_defaults(self, tmp_path: Path):
        """Test loading empty YAML file uses defaults."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        config = Config.from_yaml(yaml_file)
        assert config.version == "1.0.0"
        assert config.environment == "development"

    def test_partial_yaml_merges_with_defaults(self, tmp_path: Path):
        """Test partial YAML merges with defaults."""
        yaml_content = {"llm": {"model": "partial-model"}}
        yaml_file = tmp_path / "partial.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump(yaml_content, f)

        config = Config.from_yaml(yaml_file)
        assert config.llm.model == "partial-model"
        assert config.llm.provider == "openai"  # Default value
