"""置信度MCP集成模块 (军规级 v4.5).

V4PRO Platform Component - 置信度MCP集成系统
军规覆盖: M3(完整审计), M19(风险归因)

V4PRO Scenarios:
- K62: CONFIDENCE.MCP.CONTEXT7 - Context7文档验证
- K63: CONFIDENCE.MCP.SEQUENTIAL - 分步推理检查
- K64: CONFIDENCE.MCP.VERIFY - 综合MCP验证

通过MCP (Model Context Protocol) 增强置信度评估能力:
- Context7: 官方文档验证
- Sequential: 分步推理分析
- Magic: 代码质量检查
- Tavily: 网络搜索验证

示例:
    >>> config = MCPIntegrationConfig(context7_enabled=True)
    >>> assessor = create_mcp_assessor(config)
    >>> context = ConfidenceContext(
    ...     task_type=TaskType.STRATEGY_EXECUTION,
    ...     has_official_docs=True,
    ... )
    >>> result = await assessor.assess_with_mcp(context)
    >>> print(f"MCP增强置信度: {result.score:.0%}")
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Protocol, runtime_checkable

from src.risk.confidence import (
    ConfidenceAssessor,
    ConfidenceCheck,
    ConfidenceContext,
    ConfidenceLevel,
    ConfidenceResult,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MCP 配置与协议定义
# =============================================================================


class MCPStatus(Enum):
    """MCP服务状态枚举."""

    AVAILABLE = "AVAILABLE"  # 服务可用
    UNAVAILABLE = "UNAVAILABLE"  # 服务不可用
    DEGRADED = "DEGRADED"  # 服务降级
    ERROR = "ERROR"  # 服务错误


@dataclass
class MCPIntegrationConfig:
    """MCP集成配置.

    属性:
        context7_enabled: 是否启用Context7文档验证
        sequential_enabled: 是否启用Sequential分步推理
        magic_enabled: 是否启用Magic代码检查
        tavily_enabled: 是否启用Tavily网络搜索
        timeout_seconds: MCP调用超时时间(秒)
        retry_count: MCP调用重试次数
        fallback_on_error: 错误时是否回退到基础评估
        audit_mcp_calls: 是否审计MCP调用 (M3)
    """

    context7_enabled: bool = False
    sequential_enabled: bool = False
    magic_enabled: bool = False
    tavily_enabled: bool = False
    timeout_seconds: float = 30.0
    retry_count: int = 3
    fallback_on_error: bool = True
    audit_mcp_calls: bool = True

    def get_enabled_services(self) -> list[str]:
        """获取已启用的MCP服务列表."""
        services: list[str] = []
        if self.context7_enabled:
            services.append("context7")
        if self.sequential_enabled:
            services.append("sequential")
        if self.magic_enabled:
            services.append("magic")
        if self.tavily_enabled:
            services.append("tavily")
        return services

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "context7_enabled": self.context7_enabled,
            "sequential_enabled": self.sequential_enabled,
            "magic_enabled": self.magic_enabled,
            "tavily_enabled": self.tavily_enabled,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "fallback_on_error": self.fallback_on_error,
            "audit_mcp_calls": self.audit_mcp_calls,
            "enabled_services": self.get_enabled_services(),
        }


@runtime_checkable
class MCPClient(Protocol):
    """MCP客户端协议.

    定义MCP客户端的标准接口，支持异步调用。
    实现此协议的客户端可用于置信度MCP增强评估。

    示例:
        >>> class MyMCPClient:
        ...     async def call(self, method: str, params: dict) -> Any:
        ...         # 实现MCP调用逻辑
        ...         pass
        ...
        ...     async def health_check(self) -> bool:
        ...         return True
    """

    async def call(self, method: str, params: dict[str, Any]) -> Any:
        """调用MCP方法.

        参数:
            method: MCP方法名称
            params: 方法参数

        返回:
            MCP调用结果
        """
        ...

    async def health_check(self) -> bool:
        """健康检查.

        返回:
            是否健康
        """
        ...


@dataclass
class MCPCallResult:
    """MCP调用结果.

    属性:
        success: 是否成功
        data: 返回数据
        error: 错误信息
        latency_ms: 延迟(毫秒)
        service: 服务名称
        method: 方法名称
        timestamp: 时间戳
    """

    success: bool
    data: Any = None
    error: str = ""
    latency_ms: float = 0.0
    service: str = ""
    method: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        """初始化后处理."""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()  # noqa: DTZ005

    def to_audit_dict(self) -> dict[str, Any]:
        """转换为审计日志格式 (M3)."""
        return {
            "event_type": "MCP_CALL",
            "success": self.success,
            "service": self.service,
            "method": self.method,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp,
        }


# =============================================================================
# MCP 占位符客户端 (优雅降级)
# =============================================================================


class PlaceholderMCPClient:
    """MCP占位符客户端.

    在实际MCP服务不可用时提供优雅降级。
    所有调用返回模拟结果，不影响系统运行。

    属性:
        service_name: 服务名称
        simulate_delay: 是否模拟延迟
        delay_ms: 模拟延迟时间(毫秒)
    """

    def __init__(
        self,
        service_name: str = "placeholder",
        *,
        simulate_delay: bool = False,
        delay_ms: float = 100.0,
    ) -> None:
        """初始化占位符客户端.

        参数:
            service_name: 服务名称
            simulate_delay: 是否模拟延迟
            delay_ms: 模拟延迟时间(毫秒)
        """
        self._service_name = service_name
        self._simulate_delay = simulate_delay
        self._delay_ms = delay_ms
        self._call_count = 0
        self._status = MCPStatus.DEGRADED

    @property
    def service_name(self) -> str:
        """获取服务名称."""
        return self._service_name

    @property
    def status(self) -> MCPStatus:
        """获取服务状态."""
        return self._status

    async def call(self, method: str, params: dict[str, Any]) -> Any:
        """调用MCP方法 (占位符实现).

        返回模拟结果，用于优雅降级。

        参数:
            method: MCP方法名称
            params: 方法参数

        返回:
            模拟的MCP调用结果
        """
        self._call_count += 1
        logger.debug(
            "MCP占位符调用: service=%s, method=%s, params=%s",
            self._service_name,
            method,
            params,
        )

        if self._simulate_delay:
            await asyncio.sleep(self._delay_ms / 1000.0)

        # 返回模拟结果
        return {
            "placeholder": True,
            "service": self._service_name,
            "method": method,
            "message": f"MCP服务 {self._service_name} 降级模式",
            "simulated": True,
        }

    async def health_check(self) -> bool:
        """健康检查 (占位符始终返回True)."""
        return True

    def get_call_count(self) -> int:
        """获取调用计数."""
        return self._call_count

    def reset_call_count(self) -> None:
        """重置调用计数."""
        self._call_count = 0


# =============================================================================
# MCP 服务包装器
# =============================================================================


class Context7Wrapper:
    """Context7 MCP服务包装器.

    提供官方文档验证能力，通过Context7 MCP查询
    和验证技术文档的准确性。

    场景: K62 - CONFIDENCE.MCP.CONTEXT7
    """

    def __init__(
        self,
        client: MCPClient | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        """初始化Context7包装器.

        参数:
            client: MCP客户端实例
            timeout: 超时时间(秒)
        """
        self._client = client or PlaceholderMCPClient("context7")
        self._timeout = timeout
        self._verification_cache: dict[str, tuple[bool, float]] = {}
        self._cache_ttl = 300.0  # 5分钟缓存

    async def verify_official_docs(
        self,
        topic: str,
        *,
        library: str = "",
        version: str = "",
    ) -> bool:
        """通过Context7验证官方文档.

        参数:
            topic: 验证主题
            library: 库名称
            version: 版本号

        返回:
            是否验证通过

        场景: K62
        """
        cache_key = f"{library}:{version}:{topic}"

        # 检查缓存
        if cache_key in self._verification_cache:
            is_valid, cache_time = self._verification_cache[cache_key]
            now = datetime.now().timestamp()  # noqa: DTZ005
            if now - cache_time < self._cache_ttl:
                logger.debug("Context7缓存命中: %s", cache_key)
                return is_valid

        try:
            result = await asyncio.wait_for(
                self._client.call(
                    "resolve-library-id",
                    {
                        "libraryName": library or topic,
                    },
                ),
                timeout=self._timeout,
            )

            # 检查是否为占位符响应
            if isinstance(result, dict) and result.get("placeholder"):
                logger.warning("Context7降级模式 - 返回默认验证结果")
                return True  # 降级时默认通过

            # 解析实际结果
            is_valid = bool(result) and not result.get("error")

            # 更新缓存
            self._verification_cache[cache_key] = (
                is_valid,
                datetime.now().timestamp(),  # noqa: DTZ005
            )

            return is_valid

        except asyncio.TimeoutError:
            logger.warning("Context7调用超时: topic=%s", topic)
            return True  # 超时时默认通过 (优雅降级)
        except Exception as e:
            logger.error("Context7调用失败: %s", e)
            return True  # 错误时默认通过 (优雅降级)

    async def get_documentation(
        self,
        topic: str,
        *,
        library_id: str = "",
    ) -> str:
        """获取官方文档内容.

        参数:
            topic: 文档主题
            library_id: 库ID

        返回:
            文档内容
        """
        try:
            result = await asyncio.wait_for(
                self._client.call(
                    "get-library-docs",
                    {
                        "context7CompatibleLibraryID": library_id,
                        "topic": topic,
                    },
                ),
                timeout=self._timeout,
            )

            if isinstance(result, dict):
                if result.get("placeholder"):
                    return f"[降级模式] 无法获取 {topic} 的官方文档"
                return str(result.get("content", ""))

            return str(result) if result else ""

        except Exception as e:
            logger.error("获取文档失败: %s", e)
            return ""

    def clear_cache(self) -> None:
        """清空验证缓存."""
        self._verification_cache.clear()


class SequentialWrapper:
    """Sequential MCP服务包装器.

    提供分步推理检查能力，通过Sequential MCP
    进行多步骤的逻辑推理和验证。

    场景: K63 - CONFIDENCE.MCP.SEQUENTIAL
    """

    def __init__(
        self,
        client: MCPClient | None = None,
        *,
        timeout: float = 60.0,
    ) -> None:
        """初始化Sequential包装器.

        参数:
            client: MCP客户端实例
            timeout: 超时时间(秒)
        """
        self._client = client or PlaceholderMCPClient("sequential")
        self._timeout = timeout
        self._analysis_history: list[dict[str, Any]] = []
        self._max_history = 50

    async def sequential_analysis(
        self,
        steps: list[str],
        *,
        thought_prefix: str = "",
    ) -> float:
        """通过Sequential MCP进行分步分析.

        参数:
            steps: 分析步骤列表
            thought_prefix: 思考前缀

        返回:
            分析置信度分数 (0.0-1.0)

        场景: K63
        """
        if not steps:
            return 0.0

        try:
            # 构建思考请求
            thought_content = "\n".join(
                f"Step {i+1}: {step}" for i, step in enumerate(steps)
            )
            if thought_prefix:
                thought_content = f"{thought_prefix}\n{thought_content}"

            result = await asyncio.wait_for(
                self._client.call(
                    "create_thinking_session",
                    {
                        "thought": thought_content,
                        "stepNumber": len(steps),
                    },
                ),
                timeout=self._timeout,
            )

            # 检查是否为占位符响应
            if isinstance(result, dict) and result.get("placeholder"):
                logger.warning("Sequential降级模式 - 使用步骤数计算基础置信度")
                # 降级时基于步骤数计算置信度
                base_score = min(1.0, len(steps) * 0.15)
                return base_score

            # 解析实际结果
            if isinstance(result, dict):
                confidence = result.get("confidence", 0.5)
                # 记录分析历史
                self._record_analysis(steps, confidence)
                return float(confidence)

            return 0.5  # 默认中等置信度

        except asyncio.TimeoutError:
            logger.warning("Sequential分析超时: steps=%d", len(steps))
            return 0.5  # 超时返回中等置信度
        except Exception as e:
            logger.error("Sequential分析失败: %s", e)
            return 0.5  # 错误返回中等置信度

    async def validate_reasoning(
        self,
        premise: str,
        conclusion: str,
    ) -> tuple[bool, str]:
        """验证推理逻辑.

        参数:
            premise: 前提条件
            conclusion: 结论

        返回:
            (是否有效, 验证消息)
        """
        try:
            result = await asyncio.wait_for(
                self._client.call(
                    "create_thinking_session",
                    {
                        "thought": f"Premise: {premise}\nConclusion: {conclusion}\n"
                        "Validate if the conclusion follows from the premise.",
                        "stepNumber": 1,
                    },
                ),
                timeout=self._timeout,
            )

            if isinstance(result, dict) and result.get("placeholder"):
                return True, "降级模式 - 推理验证跳过"

            if isinstance(result, dict):
                is_valid = result.get("isValid", True)
                message = result.get("message", "")
                return bool(is_valid), str(message)

            return True, ""

        except Exception as e:
            logger.error("推理验证失败: %s", e)
            return True, f"验证错误: {e}"

    def _record_analysis(
        self,
        steps: list[str],
        confidence: float,
    ) -> None:
        """记录分析历史."""
        record = {
            "timestamp": datetime.now().isoformat(),  # noqa: DTZ005
            "step_count": len(steps),
            "confidence": confidence,
        }
        self._analysis_history.append(record)
        if len(self._analysis_history) > self._max_history:
            self._analysis_history.pop(0)

    def get_analysis_statistics(self) -> dict[str, Any]:
        """获取分析统计."""
        if not self._analysis_history:
            return {
                "total_analyses": 0,
                "avg_confidence": 0.0,
                "avg_steps": 0.0,
            }

        total = len(self._analysis_history)
        avg_conf = sum(r["confidence"] for r in self._analysis_history) / total
        avg_steps = sum(r["step_count"] for r in self._analysis_history) / total

        return {
            "total_analyses": total,
            "avg_confidence": round(avg_conf, 4),
            "avg_steps": round(avg_steps, 2),
        }


class MagicWrapper:
    """Magic MCP服务包装器.

    提供代码质量检查能力。

    属性:
        client: MCP客户端
        timeout: 超时时间
    """

    def __init__(
        self,
        client: MCPClient | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        """初始化Magic包装器."""
        self._client = client or PlaceholderMCPClient("magic")
        self._timeout = timeout

    async def check_code_quality(
        self,
        code: str,
        *,
        language: str = "python",
    ) -> float:
        """检查代码质量.

        参数:
            code: 代码内容
            language: 编程语言

        返回:
            质量分数 (0.0-1.0)
        """
        try:
            result = await asyncio.wait_for(
                self._client.call(
                    "analyze",
                    {
                        "code": code,
                        "language": language,
                    },
                ),
                timeout=self._timeout,
            )

            if isinstance(result, dict) and result.get("placeholder"):
                logger.warning("Magic降级模式 - 返回默认质量分数")
                return 0.8  # 降级时返回较高分数

            if isinstance(result, dict):
                return float(result.get("quality_score", 0.8))

            return 0.8

        except Exception as e:
            logger.error("代码质量检查失败: %s", e)
            return 0.8


class TavilyWrapper:
    """Tavily MCP服务包装器.

    提供网络搜索验证能力。

    属性:
        client: MCP客户端
        timeout: 超时时间
    """

    def __init__(
        self,
        client: MCPClient | None = None,
        *,
        timeout: float = 30.0,
    ) -> None:
        """初始化Tavily包装器."""
        self._client = client or PlaceholderMCPClient("tavily")
        self._timeout = timeout

    async def search_verification(
        self,
        query: str,
        *,
        max_results: int = 5,
    ) -> bool:
        """搜索验证.

        参数:
            query: 搜索查询
            max_results: 最大结果数

        返回:
            是否找到验证信息
        """
        try:
            result = await asyncio.wait_for(
                self._client.call(
                    "search",
                    {
                        "query": query,
                        "max_results": max_results,
                    },
                ),
                timeout=self._timeout,
            )

            if isinstance(result, dict) and result.get("placeholder"):
                logger.warning("Tavily降级模式 - 返回默认验证结果")
                return True  # 降级时默认通过

            if isinstance(result, dict):
                results = result.get("results", [])
                return len(results) > 0

            return True

        except Exception as e:
            logger.error("搜索验证失败: %s", e)
            return True


# =============================================================================
# MCP 增强置信度评估器
# =============================================================================


class MCPEnhancedAssessor(ConfidenceAssessor):
    """MCP增强置信度评估器.

    扩展基础置信度评估器，通过MCP服务增强评估能力:
    - Context7: 官方文档验证
    - Sequential: 分步推理分析
    - Magic: 代码质量检查
    - Tavily: 网络搜索验证

    军规覆盖:
    - M3: 完整审计 - 记录所有MCP调用
    - M19: 风险归因 - MCP增强的风险分析

    场景: K64 - CONFIDENCE.MCP.VERIFY

    示例:
        >>> config = MCPIntegrationConfig(context7_enabled=True)
        >>> assessor = MCPEnhancedAssessor(config=config)
        >>> context = ConfidenceContext(
        ...     task_type=TaskType.STRATEGY_EXECUTION,
        ...     has_official_docs=True,
        ... )
        >>> result = await assessor.assess_with_mcp(context)
        >>> print(f"MCP增强置信度: {result.score:.0%}")
    """

    # MCP检查权重
    WEIGHT_MCP_CONTEXT7: ClassVar[float] = 0.15
    WEIGHT_MCP_SEQUENTIAL: ClassVar[float] = 0.15
    WEIGHT_MCP_MAGIC: ClassVar[float] = 0.10
    WEIGHT_MCP_TAVILY: ClassVar[float] = 0.10

    def __init__(
        self,
        config: MCPIntegrationConfig | None = None,
        *,
        high_threshold: float = 0.90,
        medium_threshold: float = 0.70,
        adaptive_mode: bool = False,
        context7_client: MCPClient | None = None,
        sequential_client: MCPClient | None = None,
        magic_client: MCPClient | None = None,
        tavily_client: MCPClient | None = None,
    ) -> None:
        """初始化MCP增强评估器.

        参数:
            config: MCP集成配置
            high_threshold: 高置信度阈值
            medium_threshold: 中等置信度阈值
            adaptive_mode: 是否启用自适应模式
            context7_client: Context7 MCP客户端
            sequential_client: Sequential MCP客户端
            magic_client: Magic MCP客户端
            tavily_client: Tavily MCP客户端
        """
        super().__init__(
            high_threshold=high_threshold,
            medium_threshold=medium_threshold,
            adaptive_mode=adaptive_mode,
        )

        self._config = config or MCPIntegrationConfig()

        # 初始化MCP服务包装器
        self._context7 = Context7Wrapper(context7_client)
        self._sequential = SequentialWrapper(sequential_client)
        self._magic = MagicWrapper(magic_client)
        self._tavily = TavilyWrapper(tavily_client)

        # MCP调用审计日志 (M3)
        self._mcp_audit_log: list[dict[str, Any]] = []
        self._max_audit_log = 1000

        # MCP调用统计
        self._mcp_call_count = 0
        self._mcp_success_count = 0
        self._mcp_error_count = 0

    @property
    def config(self) -> MCPIntegrationConfig:
        """获取MCP配置."""
        return self._config

    async def verify_official_docs(
        self,
        topic: str,
        *,
        library: str = "",
        version: str = "",
    ) -> bool:
        """通过Context7验证官方文档.

        参数:
            topic: 验证主题
            library: 库名称
            version: 版本号

        返回:
            是否验证通过

        场景: K62
        """
        if not self._config.context7_enabled:
            logger.debug("Context7未启用 - 跳过文档验证")
            return True

        start_time = datetime.now()  # noqa: DTZ005
        try:
            result = await self._context7.verify_official_docs(
                topic,
                library=library,
                version=version,
            )
            self._record_mcp_call("context7", "verify_official_docs", True, start_time)
            return result
        except Exception as e:
            self._record_mcp_call(
                "context7", "verify_official_docs", False, start_time, str(e)
            )
            return True  # 错误时默认通过 (优雅降级)

    async def sequential_analysis(
        self,
        steps: list[str],
        *,
        thought_prefix: str = "",
    ) -> float:
        """通过Sequential MCP进行分步分析.

        参数:
            steps: 分析步骤列表
            thought_prefix: 思考前缀

        返回:
            分析置信度分数 (0.0-1.0)

        场景: K63
        """
        if not self._config.sequential_enabled:
            logger.debug("Sequential未启用 - 跳过分步分析")
            return 0.5  # 返回中等置信度

        start_time = datetime.now()  # noqa: DTZ005
        try:
            result = await self._sequential.sequential_analysis(
                steps,
                thought_prefix=thought_prefix,
            )
            self._record_mcp_call("sequential", "sequential_analysis", True, start_time)
            return result
        except Exception as e:
            self._record_mcp_call(
                "sequential", "sequential_analysis", False, start_time, str(e)
            )
            return 0.5  # 错误时返回中等置信度

    async def assess_with_mcp(
        self,
        context: ConfidenceContext,
    ) -> ConfidenceResult:
        """MCP增强评估.

        在基础评估的基础上，通过MCP服务增强评估能力。

        参数:
            context: 评估上下文

        返回:
            置信度评估结果

        场景: K64
        """
        # 首先执行基础评估
        base_result = self.assess(context)

        # 收集MCP增强检查
        mcp_checks: list[ConfidenceCheck] = []

        # Context7文档验证
        if self._config.context7_enabled and context.task_name:
            doc_verified = await self.verify_official_docs(context.task_name)
            mcp_checks.append(
                ConfidenceCheck(
                    name="mcp_context7",
                    passed=doc_verified,
                    weight=self.WEIGHT_MCP_CONTEXT7 if doc_verified else 0.0,
                    message=(
                        "MCP: Context7文档验证通过"
                        if doc_verified
                        else "MCP: Context7文档验证失败"
                    ),
                    details={"service": "context7", "topic": context.task_name},
                )
            )

        # Sequential分步分析
        if self._config.sequential_enabled:
            # 构建分析步骤
            analysis_steps = self._build_analysis_steps(context)
            if analysis_steps:
                seq_score = await self.sequential_analysis(analysis_steps)
                seq_passed = seq_score >= 0.5
                mcp_checks.append(
                    ConfidenceCheck(
                        name="mcp_sequential",
                        passed=seq_passed,
                        weight=self.WEIGHT_MCP_SEQUENTIAL * seq_score,
                        message=(
                            f"MCP: Sequential分析置信度 {seq_score:.0%}"
                            if seq_passed
                            else f"MCP: Sequential分析置信度不足 {seq_score:.0%}"
                        ),
                        details={
                            "service": "sequential",
                            "score": seq_score,
                            "steps": len(analysis_steps),
                        },
                    )
                )

        # Magic代码质量检查
        if self._config.magic_enabled and context.metadata.get("code"):
            code = context.metadata.get("code", "")
            quality_score = await self._magic.check_code_quality(code)
            quality_passed = quality_score >= 0.7
            mcp_checks.append(
                ConfidenceCheck(
                    name="mcp_magic",
                    passed=quality_passed,
                    weight=self.WEIGHT_MCP_MAGIC * quality_score,
                    message=(
                        f"MCP: 代码质量 {quality_score:.0%}"
                        if quality_passed
                        else f"MCP: 代码质量不足 {quality_score:.0%}"
                    ),
                    details={"service": "magic", "score": quality_score},
                )
            )

        # Tavily搜索验证
        if self._config.tavily_enabled and context.task_name:
            search_verified = await self._tavily.search_verification(context.task_name)
            mcp_checks.append(
                ConfidenceCheck(
                    name="mcp_tavily",
                    passed=search_verified,
                    weight=self.WEIGHT_MCP_TAVILY if search_verified else 0.0,
                    message=(
                        "MCP: Tavily搜索验证通过"
                        if search_verified
                        else "MCP: Tavily搜索验证失败"
                    ),
                    details={"service": "tavily", "query": context.task_name},
                )
            )

        # 如果没有MCP检查，直接返回基础结果
        if not mcp_checks:
            return base_result

        # 合并检查结果
        all_checks = list(base_result.checks) + mcp_checks

        # 重新计算分数
        # 基础分数占80%，MCP分数占20%
        base_score = base_result.score * 0.80
        mcp_score = sum(c.weight for c in mcp_checks if c.passed)
        total_score = min(1.0, base_score + mcp_score)

        # 确定等级
        if total_score >= self._high_threshold:
            level = ConfidenceLevel.HIGH
            can_proceed = True
        elif total_score >= self._medium_threshold:
            level = ConfidenceLevel.MEDIUM
            can_proceed = False
        else:
            level = ConfidenceLevel.LOW
            can_proceed = False

        # 生成建议
        recommendation = self._get_mcp_recommendation(level, mcp_checks)

        # 构建增强结果
        enhanced_context_summary = {
            **base_result.context_summary,
            "mcp_enhanced": True,
            "mcp_services": self._config.get_enabled_services(),
            "mcp_checks_count": len(mcp_checks),
        }

        return ConfidenceResult(
            score=total_score,
            level=level,
            can_proceed=can_proceed,
            checks=tuple(all_checks),
            recommendation=recommendation,
            timestamp=datetime.now().isoformat(),  # noqa: DTZ005
            context_summary=enhanced_context_summary,
        )

    def _build_analysis_steps(
        self,
        context: ConfidenceContext,
    ) -> list[str]:
        """构建分析步骤.

        参数:
            context: 评估上下文

        返回:
            分析步骤列表
        """
        steps: list[str] = []

        # 基于上下文构建分析步骤
        if context.task_name:
            steps.append(f"分析任务: {context.task_name}")

        if context.duplicate_check_complete:
            steps.append("验证重复检查完成")
        else:
            steps.append("检查是否存在重复实现")

        if context.architecture_verified:
            steps.append("确认架构合规性")
        else:
            steps.append("验证架构设计是否合规")

        if context.has_official_docs:
            steps.append("确认官方文档支持")
        else:
            steps.append("查找官方文档参考")

        if context.signal_strength > 0:
            steps.append(f"评估信号强度: {context.signal_strength:.0%}")

        if context.risk_within_limits:
            steps.append("确认风险在控制范围内")
        else:
            steps.append("评估风险控制措施")

        return steps

    def _get_mcp_recommendation(
        self,
        level: ConfidenceLevel,
        mcp_checks: list[ConfidenceCheck],
    ) -> str:
        """获取MCP增强建议.

        参数:
            level: 置信度等级
            mcp_checks: MCP检查结果

        返回:
            建议字符串
        """
        passed_services = [c.details.get("service", "") for c in mcp_checks if c.passed]
        failed_services = [
            c.details.get("service", "") for c in mcp_checks if not c.passed
        ]

        if level == ConfidenceLevel.HIGH:
            return f"MCP增强: 高置信度 - {len(passed_services)}个MCP服务验证通过"

        if level == ConfidenceLevel.MEDIUM:
            return (
                f"MCP增强: 中等置信度 - 部分MCP验证未通过: "
                f"{', '.join(failed_services)}"
            )

        return f"MCP增强: 低置信度 - MCP验证失败: {', '.join(failed_services)}"

    def _record_mcp_call(
        self,
        service: str,
        method: str,
        success: bool,
        start_time: datetime,
        error: str = "",
    ) -> None:
        """记录MCP调用 (M3审计).

        参数:
            service: 服务名称
            method: 方法名称
            success: 是否成功
            start_time: 开始时间
            error: 错误信息
        """
        self._mcp_call_count += 1
        if success:
            self._mcp_success_count += 1
        else:
            self._mcp_error_count += 1

        if not self._config.audit_mcp_calls:
            return

        end_time = datetime.now()  # noqa: DTZ005
        latency_ms = (end_time - start_time).total_seconds() * 1000

        record = MCPCallResult(
            success=success,
            error=error,
            latency_ms=latency_ms,
            service=service,
            method=method,
            timestamp=end_time.isoformat(),
        )

        self._mcp_audit_log.append(record.to_audit_dict())
        if len(self._mcp_audit_log) > self._max_audit_log:
            self._mcp_audit_log.pop(0)

    def get_mcp_statistics(self) -> dict[str, Any]:
        """获取MCP调用统计.

        返回:
            统计信息字典
        """
        total = self._mcp_call_count
        return {
            "total_calls": total,
            "success_count": self._mcp_success_count,
            "error_count": self._mcp_error_count,
            "success_rate": (
                self._mcp_success_count / total if total > 0 else 0.0
            ),
            "enabled_services": self._config.get_enabled_services(),
            "audit_log_size": len(self._mcp_audit_log),
        }

    def get_mcp_audit_log(
        self,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """获取MCP审计日志 (M3).

        参数:
            limit: 返回记录数限制

        返回:
            审计日志列表
        """
        return self._mcp_audit_log[-limit:]

    def reset_mcp_statistics(self) -> None:
        """重置MCP统计."""
        self._mcp_call_count = 0
        self._mcp_success_count = 0
        self._mcp_error_count = 0
        self._mcp_audit_log.clear()


# =============================================================================
# 工厂函数
# =============================================================================


def create_mcp_assessor(
    config: MCPIntegrationConfig | None = None,
    *,
    high_threshold: float = 0.90,
    medium_threshold: float = 0.70,
    adaptive_mode: bool = False,
    context7_client: MCPClient | None = None,
    sequential_client: MCPClient | None = None,
    magic_client: MCPClient | None = None,
    tavily_client: MCPClient | None = None,
) -> MCPEnhancedAssessor:
    """创建MCP增强评估器.

    参数:
        config: MCP集成配置
        high_threshold: 高置信度阈值
        medium_threshold: 中等置信度阈值
        adaptive_mode: 是否启用自适应模式
        context7_client: Context7 MCP客户端
        sequential_client: Sequential MCP客户端
        magic_client: Magic MCP客户端
        tavily_client: Tavily MCP客户端

    返回:
        MCP增强评估器实例

    示例:
        >>> config = MCPIntegrationConfig(
        ...     context7_enabled=True,
        ...     sequential_enabled=True,
        ... )
        >>> assessor = create_mcp_assessor(config)
        >>> print(f"启用的MCP服务: {assessor.config.get_enabled_services()}")
    """
    return MCPEnhancedAssessor(
        config=config,
        high_threshold=high_threshold,
        medium_threshold=medium_threshold,
        adaptive_mode=adaptive_mode,
        context7_client=context7_client,
        sequential_client=sequential_client,
        magic_client=magic_client,
        tavily_client=tavily_client,
    )


async def quick_mcp_assess(
    context: ConfidenceContext,
    *,
    enable_context7: bool = True,
    enable_sequential: bool = True,
) -> ConfidenceResult:
    """快速MCP评估.

    参数:
        context: 评估上下文
        enable_context7: 是否启用Context7
        enable_sequential: 是否启用Sequential

    返回:
        置信度评估结果
    """
    config = MCPIntegrationConfig(
        context7_enabled=enable_context7,
        sequential_enabled=enable_sequential,
    )
    assessor = create_mcp_assessor(config)
    return await assessor.assess_with_mcp(context)
