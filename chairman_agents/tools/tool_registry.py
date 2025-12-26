"""工具注册表模块 - 统一管理和调用工具."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable


class ToolCategory(Enum):
    """工具类别."""
    CODE = "code"
    FILE = "file"
    SEARCH = "search"
    WEB = "web"
    DATABASE = "database"
    SYSTEM = "system"


@dataclass
class ToolParameter:
    """工具参数定义."""
    name: str
    type: str
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """工具定义."""
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = "Any"
    examples: list[str] = field(default_factory=list)


@dataclass
class ToolResult:
    """工具执行结果."""
    success: bool
    data: Any = None
    error: str | None = None
    duration: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """工具调用记录."""
    tool_name: str
    arguments: dict[str, Any]
    result: ToolResult | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@runtime_checkable
class Tool(Protocol):
    """工具协议."""

    @property
    def definition(self) -> ToolDefinition:
        """返回工具定义."""
        ...

    async def execute(self, **kwargs: Any) -> ToolResult:
        """执行工具."""
        ...


class BaseTool(ABC):
    """工具基类."""

    def __init__(self, definition: ToolDefinition) -> None:
        self._definition = definition

    @property
    def definition(self) -> ToolDefinition:
        return self._definition

    @property
    def name(self) -> str:
        return self._definition.name

    def validate_args(self, kwargs: dict[str, Any]) -> tuple[bool, str]:
        """验证参数."""
        for param in self._definition.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
        return True, ""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """执行工具."""
        ...


class FunctionTool(BaseTool):
    """函数包装工具."""

    def __init__(
        self,
        func: Callable[..., Any],
        definition: ToolDefinition,
    ) -> None:
        super().__init__(definition)
        self._func = func
        self._is_async = asyncio.iscoroutinefunction(func)

    async def execute(self, **kwargs: Any) -> ToolResult:
        valid, err = self.validate_args(kwargs)
        if not valid:
            return ToolResult(success=False, error=err)

        try:
            if self._is_async:
                result = await self._func(**kwargs)
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._func(**kwargs)
                )
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


class ToolRegistry:
    """工具注册表."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._aliases: dict[str, str] = {}
        self._call_history: list[ToolCall] = []
        self._max_history: int = 1000

    def register(
        self,
        tool: Tool,
        aliases: list[str] | None = None,
    ) -> None:
        """注册工具."""
        name = tool.definition.name
        self._tools[name] = tool
        if aliases:
            for alias in aliases:
                self._aliases[alias.lower()] = name

    def register_function(
        self,
        func: Callable[..., Any],
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.SYSTEM,
        parameters: list[ToolParameter] | None = None,
    ) -> None:
        """注册函数为工具."""
        definition = ToolDefinition(
            name=name,
            description=description,
            category=category,
            parameters=parameters or [],
        )
        tool = FunctionTool(func, definition)
        self.register(tool)

    def unregister(self, name: str) -> bool:
        """取消注册."""
        if name not in self._tools:
            return False
        del self._tools[name]
        # 清理别名
        self._aliases = {k: v for k, v in self._aliases.items() if v != name}
        return True

    def get(self, name: str) -> Tool | None:
        """获取工具."""
        if name in self._tools:
            return self._tools[name]
        resolved = self._aliases.get(name.lower())
        return self._tools.get(resolved) if resolved else None

    def list_all(self) -> list[ToolDefinition]:
        """列出所有工具定义."""
        return [t.definition for t in self._tools.values()]

    def list_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """按类别列出."""
        return [
            t.definition for t in self._tools.values()
            if t.definition.category == category
        ]

    async def execute(
        self,
        name: str,
        **kwargs: Any,
    ) -> ToolResult:
        """执行工具."""
        tool = self.get(name)
        if not tool:
            return ToolResult(success=False, error=f"Tool not found: {name}")

        import time
        start = time.perf_counter()
        result = await tool.execute(**kwargs)
        result.duration = time.perf_counter() - start

        # 记录调用
        call = ToolCall(
            tool_name=name,
            arguments=kwargs,
            result=result,
        )
        self._call_history.append(call)
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history:]

        return result

    def get_history(self, limit: int = 100) -> list[ToolCall]:
        """获取调用历史."""
        return self._call_history[-limit:]

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """转换为OpenAI工具格式."""
        tools = []
        for tool in self._tools.values():
            defn = tool.definition
            props = {}
            required = []
            for p in defn.parameters:
                props[p.name] = {
                    "type": p.type,
                    "description": p.description,
                }
                if p.required:
                    required.append(p.name)

            tools.append({
                "type": "function",
                "function": {
                    "name": defn.name,
                    "description": defn.description,
                    "parameters": {
                        "type": "object",
                        "properties": props,
                        "required": required,
                    },
                },
            })
        return tools


_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def tool(
    name: str | None = None,
    description: str = "",
    category: ToolCategory = ToolCategory.SYSTEM,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """工具装饰器."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__
        get_tool_registry().register_function(
            func=func,
            name=tool_name,
            description=description or func.__doc__ or "",
            category=category,
        )
        return func
    return decorator


__all__ = [
    "ToolCategory", "ToolParameter", "ToolDefinition",
    "ToolResult", "ToolCall", "Tool",
    "BaseTool", "FunctionTool", "ToolRegistry",
    "get_tool_registry", "tool",
]
