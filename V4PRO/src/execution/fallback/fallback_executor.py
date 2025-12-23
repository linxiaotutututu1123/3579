"""
FallbackExecutor - 降级执行器.

V4PRO Platform Component - Phase 8
V4 SPEC: 降级兜底机制
V2 Scenarios: EXEC.FALLBACK.EXECUTOR

军规级要求:
- M4: 降级执行策略完整
- M3: 审计日志完整
- M6: 与熔断保护联动

执行模式:
1. NORMAL: 正常执行
2. GRACEFUL: 使用备用算法
3. REDUCED: 减量执行
4. QUEUED: 进入人工队列
5. CLOSE_ONLY: 仅平仓
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

from src.execution.fallback.fallback_manager import (
    FallbackConfig,
    FallbackLevel,
    FallbackManager,
    FallbackResult,
)

if TYPE_CHECKING:
    from src.execution.broker import Broker


class ExecutionMode(Enum):
    """执行模式."""

    NORMAL = "normal"
    GRACEFUL = "graceful"
    REDUCED = "reduced"
    QUEUED = "queued"
    CLOSE_ONLY = "close_only"


@dataclass
class ExecutionRequest:
    """执行请求.

    Attributes:
        order_id: 订单ID
        symbol: 合约代码
        direction: 方向 (BUY/SELL)
        offset: 开平 (OPEN/CLOSE)
        volume: 数量
        price: 价格
        algorithm: 算法 (TWAP/VWAP/ICEBERG)
        urgency: 紧急度 (high/normal/low)
        extra: 额外参数
    """

    order_id: str
    symbol: str
    direction: str
    offset: str
    volume: int
    price: float
    algorithm: str = "TWAP"
    urgency: str = "normal"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "offset": self.offset,
            "volume": self.volume,
            "price": self.price,
            "algorithm": self.algorithm,
            "urgency": self.urgency,
            "extra": self.extra,
        }


@dataclass
class ExecutionResponse:
    """执行响应.

    Attributes:
        success: 是否成功
        order_id: 订单ID
        mode: 执行模式
        adjusted_volume: 调整后数量
        adjusted_algorithm: 调整后算法
        message: 消息
        queued: 是否进入队列
        requires_confirmation: 是否需要确认
    """

    success: bool
    order_id: str
    mode: ExecutionMode
    adjusted_volume: int = 0
    adjusted_algorithm: str = ""
    message: str = ""
    queued: bool = False
    requires_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "success": self.success,
            "order_id": self.order_id,
            "mode": self.mode.value,
            "adjusted_volume": self.adjusted_volume,
            "adjusted_algorithm": self.adjusted_algorithm,
            "message": self.message,
            "queued": self.queued,
            "requires_confirmation": self.requires_confirmation,
        }


class ManualQueue:
    """人工处理队列."""

    def __init__(self, max_size: int = 100) -> None:
        """初始化队列."""
        self._queue: list[ExecutionRequest] = []
        self._max_size = max_size

    def enqueue(self, request: ExecutionRequest) -> bool:
        """入队."""
        if len(self._queue) >= self._max_size:
            return False
        self._queue.append(request)
        return True

    def dequeue(self) -> ExecutionRequest | None:
        """出队."""
        if not self._queue:
            return None
        return self._queue.pop(0)

    def peek(self) -> ExecutionRequest | None:
        """查看队首."""
        if not self._queue:
            return None
        return self._queue[0]

    def size(self) -> int:
        """获取队列大小."""
        return len(self._queue)

    def clear(self) -> int:
        """清空队列."""
        count = len(self._queue)
        self._queue.clear()
        return count

    def get_all(self) -> list[ExecutionRequest]:
        """获取所有请求."""
        return self._queue.copy()


class FallbackExecutor:
    """降级执行器.

    V4 SPEC M4: 降级兜底执行

    功能:
    1. 根据降级级别调整执行策略
    2. 管理人工处理队列
    3. 提供备用执行路径
    4. 与FallbackManager联动

    使用示例:
        executor = FallbackExecutor(fallback_manager)

        request = ExecutionRequest(
            order_id="ORD001",
            symbol="rb2501",
            direction="BUY",
            offset="OPEN",
            volume=10,
            price=3850.0,
        )

        response = executor.execute(request)
        if response.queued:
            # 进入人工队列
            pass
    """

    # 算法降级映射
    ALGORITHM_FALLBACK: dict[str, str] = {
        "AGGRESSIVE": "TWAP",
        "VWAP": "TWAP",
        "TWAP": "ICEBERG",
        "ICEBERG": "ICEBERG",  # 已经是最保守
    }

    def __init__(
        self,
        fallback_manager: FallbackManager,
        broker: Broker | None = None,
        audit_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        """初始化执行器.

        Args:
            fallback_manager: 降级管理器
            broker: 经纪商接口
            audit_callback: 审计日志回调
        """
        self._manager = fallback_manager
        self._broker = broker
        self._audit_callback = audit_callback
        self._manual_queue = ManualQueue()
        self._execution_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "queued": 0,
            "rejected": 0,
        }

    @property
    def manual_queue(self) -> ManualQueue:
        """获取人工队列."""
        return self._manual_queue

    @property
    def stats(self) -> dict[str, int]:
        """获取执行统计."""
        return self._execution_stats.copy()

    def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """执行交易请求.

        根据当前降级级别调整执行策略。

        Args:
            request: 执行请求

        Returns:
            执行响应
        """
        self._execution_stats["total"] += 1
        level = self._manager.current_level

        self._audit("fallback.execute.start", {
            "order_id": request.order_id,
            "level": level.value,
            "original_volume": request.volume,
        })

        # 根据级别选择执行模式
        if level == FallbackLevel.NORMAL:
            return self._execute_normal(request)
        elif level == FallbackLevel.GRACEFUL:
            return self._execute_graceful(request)
        elif level == FallbackLevel.REDUCED:
            return self._execute_reduced(request)
        elif level == FallbackLevel.MANUAL:
            return self._execute_manual(request)
        else:  # EMERGENCY
            return self._execute_emergency(request)

    def _execute_normal(self, request: ExecutionRequest) -> ExecutionResponse:
        """正常模式执行."""
        try:
            if self._broker:
                # 实际执行
                self._broker.submit_order(request.to_dict())

            self._execution_stats["success"] += 1
            self._manager.report_success()

            return ExecutionResponse(
                success=True,
                order_id=request.order_id,
                mode=ExecutionMode.NORMAL,
                adjusted_volume=request.volume,
                adjusted_algorithm=request.algorithm,
                message="Executed in normal mode",
            )
        except Exception as e:
            self._execution_stats["failed"] += 1
            self._manager.report_failure(str(e), request.to_dict())

            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=ExecutionMode.NORMAL,
                message=f"Execution failed: {e}",
            )

    def _execute_graceful(self, request: ExecutionRequest) -> ExecutionResponse:
        """优雅降级模式执行."""
        # 获取调整参数
        params = self._manager.get_adjusted_params(request.to_dict())

        # 调整算法
        adjusted_algorithm = self.ALGORITHM_FALLBACK.get(
            request.algorithm, "TWAP"
        )

        # 调整数量
        adjusted_volume = params.get("volume", request.volume)

        self._audit("fallback.execute.graceful", {
            "order_id": request.order_id,
            "original_algorithm": request.algorithm,
            "adjusted_algorithm": adjusted_algorithm,
            "original_volume": request.volume,
            "adjusted_volume": adjusted_volume,
        })

        try:
            if self._broker:
                adjusted_request = {
                    **request.to_dict(),
                    "algorithm": adjusted_algorithm,
                    "volume": adjusted_volume,
                }
                self._broker.submit_order(adjusted_request)

            self._execution_stats["success"] += 1
            self._manager.report_success()

            return ExecutionResponse(
                success=True,
                order_id=request.order_id,
                mode=ExecutionMode.GRACEFUL,
                adjusted_volume=adjusted_volume,
                adjusted_algorithm=adjusted_algorithm,
                message="Executed in graceful fallback mode",
            )
        except Exception as e:
            self._execution_stats["failed"] += 1
            self._manager.report_failure(str(e), request.to_dict())

            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=ExecutionMode.GRACEFUL,
                message=f"Graceful execution failed: {e}",
            )

    def _execute_reduced(self, request: ExecutionRequest) -> ExecutionResponse:
        """减量模式执行."""
        params = self._manager.get_adjusted_params(request.to_dict())

        adjusted_volume = params.get("volume", request.volume)
        adjusted_algorithm = "ICEBERG"  # 使用冰山算法

        # 检查是否允许新开仓
        if request.offset == "OPEN" and not self._manager.is_operation_allowed("new_order"):
            self._execution_stats["rejected"] += 1
            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=ExecutionMode.REDUCED,
                message="New orders not allowed in reduced mode",
            )

        self._audit("fallback.execute.reduced", {
            "order_id": request.order_id,
            "adjusted_volume": adjusted_volume,
            "max_participation_rate": params.get("max_participation_rate", 0.05),
        })

        try:
            if self._broker:
                adjusted_request = {
                    **request.to_dict(),
                    "algorithm": adjusted_algorithm,
                    "volume": adjusted_volume,
                    "max_participation_rate": params.get("max_participation_rate", 0.05),
                }
                self._broker.submit_order(adjusted_request)

            self._execution_stats["success"] += 1
            self._manager.report_success()

            return ExecutionResponse(
                success=True,
                order_id=request.order_id,
                mode=ExecutionMode.REDUCED,
                adjusted_volume=adjusted_volume,
                adjusted_algorithm=adjusted_algorithm,
                message="Executed in reduced mode",
            )
        except Exception as e:
            self._execution_stats["failed"] += 1
            self._manager.report_failure(str(e), request.to_dict())

            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=ExecutionMode.REDUCED,
                message=f"Reduced execution failed: {e}",
            )

    def _execute_manual(self, request: ExecutionRequest) -> ExecutionResponse:
        """人工接管模式."""
        # 只允许平仓操作直接执行
        if request.offset == "CLOSE":
            return self._execute_close_only(request, ExecutionMode.QUEUED)

        # 新开仓进入队列
        if self._manual_queue.enqueue(request):
            self._execution_stats["queued"] += 1

            self._audit("fallback.execute.queued", {
                "order_id": request.order_id,
                "queue_size": self._manual_queue.size(),
            })

            return ExecutionResponse(
                success=True,
                order_id=request.order_id,
                mode=ExecutionMode.QUEUED,
                queued=True,
                requires_confirmation=True,
                message=f"Queued for manual review, position: {self._manual_queue.size()}",
            )
        else:
            self._execution_stats["rejected"] += 1
            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=ExecutionMode.QUEUED,
                message="Manual queue is full",
            )

    def _execute_emergency(self, request: ExecutionRequest) -> ExecutionResponse:
        """紧急模式 - 仅允许平仓."""
        if request.offset != "CLOSE":
            self._execution_stats["rejected"] += 1
            self._audit("fallback.execute.rejected", {
                "order_id": request.order_id,
                "reason": "only_close_allowed_in_emergency",
            })
            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=ExecutionMode.CLOSE_ONLY,
                message="Only close positions allowed in emergency mode",
            )

        return self._execute_close_only(request, ExecutionMode.CLOSE_ONLY)

    def _execute_close_only(
        self,
        request: ExecutionRequest,
        mode: ExecutionMode,
    ) -> ExecutionResponse:
        """执行平仓操作."""
        try:
            if self._broker:
                self._broker.submit_order(request.to_dict())

            self._execution_stats["success"] += 1

            return ExecutionResponse(
                success=True,
                order_id=request.order_id,
                mode=mode,
                adjusted_volume=request.volume,
                message="Close position executed",
            )
        except Exception as e:
            self._execution_stats["failed"] += 1

            return ExecutionResponse(
                success=False,
                order_id=request.order_id,
                mode=mode,
                message=f"Close position failed: {e}",
            )

    def process_manual_queue(
        self,
        confirm_callback: Callable[[ExecutionRequest], bool] | None = None,
    ) -> list[ExecutionResponse]:
        """处理人工队列.

        Args:
            confirm_callback: 确认回调，返回True则执行

        Returns:
            执行结果列表
        """
        results = []

        while True:
            request = self._manual_queue.dequeue()
            if request is None:
                break

            # 如果有确认回调，先确认
            if confirm_callback and not confirm_callback(request):
                self._audit("fallback.manual.rejected", {
                    "order_id": request.order_id,
                })
                results.append(ExecutionResponse(
                    success=False,
                    order_id=request.order_id,
                    mode=ExecutionMode.QUEUED,
                    message="Rejected by manual confirmation",
                ))
                continue

            # 使用减量模式执行
            response = self._execute_reduced(request)
            results.append(response)

        return results

    def _audit(self, event: str, data: dict[str, Any]) -> None:
        """记录审计日志."""
        if self._audit_callback:
            self._audit_callback(event, {
                **data,
                "timestamp": time.time(),
                "module": "FallbackExecutor",
            })
