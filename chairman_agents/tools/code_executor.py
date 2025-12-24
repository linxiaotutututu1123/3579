"""代码执行器模块 - 安全执行代码片段."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Language(Enum):
    """支持的编程语言."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    BASH = "bash"
    SHELL = "shell"


@dataclass
class ExecutionResult:
    """执行结果."""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration: float = 0.0
    language: Language | None = None
    timed_out: bool = False
    error: str | None = None


@dataclass
class ExecutionConfig:
    """执行配置."""
    timeout: float = 30.0
    max_output: int = 100000
    working_dir: Path | None = None
    env: dict[str, str] = field(default_factory=dict)
    allow_network: bool = False
    allow_file_write: bool = True


class CodeExecutor:
    """代码执行器."""

    LANGUAGE_COMMANDS: dict[Language, list[str]] = {
        Language.PYTHON: [sys.executable, "-c"],
        Language.JAVASCRIPT: ["node", "-e"],
        Language.TYPESCRIPT: ["npx", "ts-node", "-e"],
        Language.BASH: ["bash", "-c"],
        Language.SHELL: ["sh", "-c"],
    }

    LANGUAGE_EXTENSIONS: dict[Language, str] = {
        Language.PYTHON: ".py",
        Language.JAVASCRIPT: ".js",
        Language.TYPESCRIPT: ".ts",
        Language.BASH: ".sh",
        Language.SHELL: ".sh",
    }

    def __init__(self, config: ExecutionConfig | None = None) -> None:
        self._config = config or ExecutionConfig()
        self._execution_count = 0

    @property
    def config(self) -> ExecutionConfig:
        return self._config

    def _detect_language(self, code: str) -> Language:
        """自动检测代码语言."""
        code_lower = code.lower().strip()

        if code_lower.startswith("#!/usr/bin/env python") or \
           code_lower.startswith("#!/usr/bin/python") or \
           "import " in code or "def " in code or "class " in code:
            return Language.PYTHON

        if "console.log" in code or "const " in code or "let " in code or \
           "function " in code or "=>" in code:
            if ": " in code and ("interface " in code or "type " in code):
                return Language.TYPESCRIPT
            return Language.JAVASCRIPT

        if code_lower.startswith("#!/bin/bash"):
            return Language.BASH

        return Language.BASH

    async def execute(
        self,
        code: str,
        language: Language | str | None = None,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """执行代码."""
        start_time = time.perf_counter()

        # 解析语言
        if language is None:
            lang = self._detect_language(code)
        elif isinstance(language, str):
            lang = Language(language.lower())
        else:
            lang = language

        # 获取执行命令
        cmd_template = self.LANGUAGE_COMMANDS.get(lang)
        if not cmd_template:
            return ExecutionResult(
                error=f"Unsupported language: {lang}",
                exit_code=-1,
                language=lang,
            )

        # 构建环境变量
        exec_env = os.environ.copy()
        exec_env.update(self._config.env)
        if env:
            exec_env.update(env)

        # 执行超时
        exec_timeout = timeout or self._config.timeout

        try:
            result = await self._run_process(
                cmd_template + [code],
                exec_env,
                exec_timeout,
            )
            result.language = lang
            result.duration = time.perf_counter() - start_time
            self._execution_count += 1
            return result

        except asyncio.TimeoutError:
            return ExecutionResult(
                stderr="Execution timed out",
                exit_code=-1,
                duration=time.perf_counter() - start_time,
                language=lang,
                timed_out=True,
            )
        except Exception as e:
            return ExecutionResult(
                error=str(e),
                exit_code=-1,
                duration=time.perf_counter() - start_time,
                language=lang,
            )

    async def execute_file(
        self,
        file_path: Path | str,
        language: Language | str | None = None,
        args: list[str] | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """执行文件."""
        path = Path(file_path)
        if not path.exists():
            return ExecutionResult(
                error=f"File not found: {path}",
                exit_code=-1,
            )

        # 检测语言
        if language is None:
            ext = path.suffix.lower()
            ext_map = {v: k for k, v in self.LANGUAGE_EXTENSIONS.items()}
            lang = ext_map.get(ext, Language.BASH)
        elif isinstance(language, str):
            lang = Language(language.lower())
        else:
            lang = language

        # 构建命令
        if lang == Language.PYTHON:
            cmd = [sys.executable, str(path)]
        elif lang == Language.JAVASCRIPT:
            cmd = ["node", str(path)]
        elif lang == Language.TYPESCRIPT:
            cmd = ["npx", "ts-node", str(path)]
        else:
            cmd = ["bash", str(path)]

        if args:
            cmd.extend(args)

        exec_env = os.environ.copy()
        exec_env.update(self._config.env)
        exec_timeout = timeout or self._config.timeout

        start_time = time.perf_counter()
        try:
            result = await self._run_process(cmd, exec_env, exec_timeout)
            result.language = lang
            result.duration = time.perf_counter() - start_time
            return result
        except asyncio.TimeoutError:
            return ExecutionResult(
                stderr="Execution timed out",
                exit_code=-1,
                duration=time.perf_counter() - start_time,
                language=lang,
                timed_out=True,
            )

    async def _run_process(
        self,
        cmd: list[str],
        env: dict[str, str],
        timeout: float,
    ) -> ExecutionResult:
        """运行进程."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=self._config.working_dir,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        # 截断过长输出
        max_out = self._config.max_output
        stdout_str = stdout.decode("utf-8", errors="replace")[:max_out]
        stderr_str = stderr.decode("utf-8", errors="replace")[:max_out]

        return ExecutionResult(
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=proc.returncode or 0,
        )

    async def execute_with_input(
        self,
        code: str,
        stdin: str,
        language: Language | str | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """执行代码并提供输入."""
        start_time = time.perf_counter()

        if language is None:
            lang = self._detect_language(code)
        elif isinstance(language, str):
            lang = Language(language.lower())
        else:
            lang = language

        cmd_template = self.LANGUAGE_COMMANDS.get(lang)
        if not cmd_template:
            return ExecutionResult(error=f"Unsupported: {lang}", exit_code=-1)

        exec_timeout = timeout or self._config.timeout
        exec_env = os.environ.copy()
        exec_env.update(self._config.env)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_template, code,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=exec_env,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(stdin.encode()),
                timeout=exec_timeout,
            )

            return ExecutionResult(
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=proc.returncode or 0,
                duration=time.perf_counter() - start_time,
                language=lang,
            )

        except asyncio.TimeoutError:
            return ExecutionResult(
                stderr="Timeout",
                exit_code=-1,
                timed_out=True,
                duration=time.perf_counter() - start_time,
                language=lang,
            )

    def validate_code(self, code: str, language: Language) -> tuple[bool, str]:
        """验证代码语法(同步)."""
        if language == Language.PYTHON:
            try:
                compile(code, "<string>", "exec")
                return True, ""
            except SyntaxError as e:
                return False, f"Syntax error: {e}"
        return True, ""  # 其他语言暂不验证


__all__ = ["Language", "ExecutionResult", "ExecutionConfig", "CodeExecutor"]
