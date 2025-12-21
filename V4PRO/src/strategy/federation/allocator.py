"""
策略联邦资源分配器 (军规级 v4.2).

V4PRO Platform Component - Phase 8 策略协同
V4 SPEC: Section 28 Strategy Federation

军规覆盖:
- M3: 审计日志 - 完整的资源分配追踪
- M6: 熔断保护 - 熔断时自动回收资源

功能特性:
- 资源池管理 (持仓限额、保证金配额、订单速率、计算资源)
- 优先级队列分配
- 公平分配算法 (按权重比例分配)
- 资源回收机制
- 审计日志集成

示例:
    >>> from src.strategy.federation.allocator import ResourceAllocator
    >>> from src.strategy.federation.models import ResourceRequest, ResourceType
    >>> allocator = ResourceAllocator()
    >>> request = ResourceRequest(
    ...     strategy_id="kalman_arb",
    ...     resource_type=ResourceType.POSITION_QUOTA,
    ...     amount=100.0,
    ...     priority=5,
    ... )
    >>> allocations = allocator.allocate([request])
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, ClassVar

from src.strategy.federation.models import (
    AuditEntry,
    AuditEventType,
    ResourceAllocation,
    ResourceRequest,
    ResourceType,
    StrategyStatus,
)


if TYPE_CHECKING:
    from collections.abc import Callable

    from src.strategy.federation.registry import StrategyRegistry


@dataclass
class ResourcePool:
    """资源池定义.

    属性:
        resource_type: 资源类型
        total_capacity: 总容量
        available: 可用容量
        reserved: 已预留容量
        allocations: 当前分配记录 (策略ID -> 分配量)
    """

    resource_type: ResourceType
    total_capacity: float
    available: float = 0.0
    reserved: float = 0.0
    allocations: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初始化后处理."""
        if self.available == 0.0:
            self.available = self.total_capacity

    @property
    def used(self) -> float:
        """已使用容量."""
        return self.total_capacity - self.available - self.reserved

    @property
    def utilization(self) -> float:
        """资源利用率 (0-1)."""
        if self.total_capacity == 0:
            return 0.0
        return self.used / self.total_capacity

    def can_allocate(self, amount: float) -> bool:
        """检查是否可分配指定数量."""
        return self.available >= amount

    def allocate(self, strategy_id: str, amount: float) -> bool:
        """分配资源给策略.

        参数:
            strategy_id: 策略ID
            amount: 分配数量

        返回:
            是否分配成功
        """
        if not self.can_allocate(amount):
            return False

        self.available -= amount
        current = self.allocations.get(strategy_id, 0.0)
        self.allocations[strategy_id] = current + amount
        return True

    def release(self, strategy_id: str, amount: float | None = None) -> float:
        """释放策略资源.

        参数:
            strategy_id: 策略ID
            amount: 释放数量 (None表示全部释放)

        返回:
            实际释放的数量
        """
        current = self.allocations.get(strategy_id, 0.0)
        if current == 0:
            return 0.0

        release_amount = min(current, amount) if amount is not None else current
        self.allocations[strategy_id] = current - release_amount
        self.available += release_amount

        # 清理零分配记录
        if self.allocations[strategy_id] <= 0:
            del self.allocations[strategy_id]

        return release_amount

    def get_allocation(self, strategy_id: str) -> float:
        """获取策略当前分配量."""
        return self.allocations.get(strategy_id, 0.0)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "resource_type": self.resource_type.value,
            "total_capacity": self.total_capacity,
            "available": round(self.available, 4),
            "reserved": round(self.reserved, 4),
            "used": round(self.used, 4),
            "utilization": round(self.utilization, 4),
            "allocation_count": len(self.allocations),
        }


@dataclass
class ResourceUsage:
    """策略资源使用情况.

    属性:
        strategy_id: 策略ID
        allocations: 各类型资源分配量
        total_allocated: 总分配价值
        last_allocation_time: 最后分配时间
        allocation_count: 分配次数
    """

    strategy_id: str
    allocations: dict[ResourceType, float] = field(default_factory=dict)
    total_allocated: float = 0.0
    last_allocation_time: float = 0.0
    allocation_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "strategy_id": self.strategy_id,
            "allocations": {
                rt.value: round(amount, 4)
                for rt, amount in self.allocations.items()
            },
            "total_allocated": round(self.total_allocated, 4),
            "last_allocation_time": self.last_allocation_time,
            "last_allocation_iso": (
                datetime.fromtimestamp(
                    self.last_allocation_time, tz=timezone.utc
                ).isoformat()
                if self.last_allocation_time > 0
                else ""
            ),
            "allocation_count": self.allocation_count,
        }


class ResourceAllocator:
    """策略联邦资源分配器 (军规 M3/M6).

    功能:
    - 资源池管理: 持仓限额、保证金配额、订单速率、计算资源
    - 优先级队列: 高优先级请求优先分配
    - 公平分配: 按策略权重比例分配
    - 资源回收: 支持主动回收和熔断自动回收
    - 审计日志: 完整记录所有分配操作 (M3)

    示例:
        >>> allocator = ResourceAllocator()
        >>> # 分配资源
        >>> request = ResourceRequest(
        ...     strategy_id="kalman_arb",
        ...     resource_type=ResourceType.POSITION_QUOTA,
        ...     amount=100.0,
        ... )
        >>> results = allocator.allocate([request])
        >>> # 查看使用情况
        >>> usage = allocator.get_usage("kalman_arb")
        >>> # 回收资源
        >>> allocator.reclaim("kalman_arb")
    """

    # 默认资源池容量
    DEFAULT_POOL_CAPACITIES: ClassVar[dict[ResourceType, float]] = {
        ResourceType.POSITION_QUOTA: 1000.0,  # 持仓限额 (手)
        ResourceType.MARGIN_QUOTA: 1000000.0,  # 保证金配额 (元)
        ResourceType.ORDER_RATE: 100.0,  # 订单速率 (笔/秒)
        ResourceType.SIGNAL_PRIORITY: 10.0,  # 信号优先级槽位
        ResourceType.COMPUTE_SLOTS: 8.0,  # 计算资源槽位
    }

    # 最小分配单位
    MIN_ALLOCATION_UNIT: ClassVar[dict[ResourceType, float]] = {
        ResourceType.POSITION_QUOTA: 1.0,
        ResourceType.MARGIN_QUOTA: 100.0,
        ResourceType.ORDER_RATE: 0.1,
        ResourceType.SIGNAL_PRIORITY: 1.0,
        ResourceType.COMPUTE_SLOTS: 1.0,
    }

    # 分配有效期 (秒)
    DEFAULT_ALLOCATION_TTL: ClassVar[float] = 3600.0  # 1小时

    def __init__(
        self,
        pool_capacities: dict[ResourceType, float] | None = None,
        registry: StrategyRegistry | None = None,
        audit_logger: Callable[[AuditEntry], None] | None = None,
        allocation_ttl: float = 3600.0,
    ) -> None:
        """初始化资源分配器.

        参数:
            pool_capacities: 自定义资源池容量
            registry: 策略注册器 (用于获取策略状态)
            audit_logger: 审计日志回调函数
            allocation_ttl: 分配有效期 (秒)
        """
        self._lock = threading.RLock()

        # 初始化资源池
        capacities = pool_capacities or self.DEFAULT_POOL_CAPACITIES
        self._pools: dict[ResourceType, ResourcePool] = {
            rt: ResourcePool(resource_type=rt, total_capacity=cap)
            for rt, cap in capacities.items()
        }

        # 策略注册器引用
        self._registry = registry

        # 审计日志
        self._audit_logger = audit_logger

        # 分配有效期
        self._allocation_ttl = allocation_ttl

        # 分配记录 (allocation_id -> allocation)
        self._active_allocations: dict[str, ResourceAllocation] = {}

        # 策略使用统计
        self._usage_stats: dict[str, ResourceUsage] = {}

        # 统计计数器
        self._total_allocations = 0
        self._successful_allocations = 0
        self._failed_allocations = 0
        self._partial_allocations = 0
        self._reclaim_count = 0

    @property
    def total_allocations(self) -> int:
        """总分配请求数."""
        return self._total_allocations

    @property
    def success_rate(self) -> float:
        """分配成功率."""
        if self._total_allocations == 0:
            return 1.0
        return self._successful_allocations / self._total_allocations

    def allocate(
        self,
        requests: list[ResourceRequest],
        allow_partial: bool = True,
    ) -> list[ResourceAllocation]:
        """分配资源 (M3审计日志).

        分配流程:
        1. 资源池检查 - 验证资源可用性
        2. 优先级排序 - 高优先级请求优先处理
        3. 配额计算 - 按权重比例计算可分配额度
        4. 分配执行 - 实际分配资源
        5. 审计日志 - 记录分配操作 (M3)

        参数:
            requests: 资源请求列表
            allow_partial: 是否允许部分分配

        返回:
            分配结果列表
        """
        if not requests:
            return []

        with self._lock:
            # 步骤1: 验证请求合法性
            validated_requests = self._validate_requests(requests)

            # 步骤2: 优先级排序 (高优先级优先)
            sorted_requests = sorted(
                validated_requests,
                key=lambda r: (-r.priority, r.timestamp),
            )

            # 步骤3&4: 分配执行
            allocations: list[ResourceAllocation] = []
            for request in sorted_requests:
                allocation = self._allocate_single(request, allow_partial)
                allocations.append(allocation)

                # 步骤5: 审计日志 (M3)
                self._log_allocation_audit(request, allocation)

            return allocations

    def _validate_requests(
        self,
        requests: list[ResourceRequest],
    ) -> list[ResourceRequest]:
        """验证请求合法性.

        参数:
            requests: 原始请求列表

        返回:
            有效请求列表
        """
        valid: list[ResourceRequest] = []

        for request in requests:
            # 检查资源类型是否支持
            if request.resource_type not in self._pools:
                continue

            # 检查请求数量是否合法
            if request.amount <= 0:
                continue

            # 检查策略状态 (如果有注册器)
            if self._registry is not None:
                state = self._registry.get_state(request.strategy_id)
                if state is None:
                    continue
                # 熔断状态下不接受新分配 (M6)
                if state.status == StrategyStatus.CIRCUIT_BREAK:
                    continue
                # 禁用状态下不接受新分配
                if state.status == StrategyStatus.DISABLED:
                    continue

            valid.append(request)

        return valid

    def _allocate_single(
        self,
        request: ResourceRequest,
        allow_partial: bool,
    ) -> ResourceAllocation:
        """执行单个分配请求.

        参数:
            request: 资源请求
            allow_partial: 是否允许部分分配

        返回:
            分配结果
        """
        self._total_allocations += 1

        pool = self._pools.get(request.resource_type)
        if pool is None:
            self._failed_allocations += 1
            return ResourceAllocation(
                request=request,
                allocated_amount=0.0,
                success=False,
                message=f"不支持的资源类型: {request.resource_type.value}",
            )

        # 计算实际可分配量
        available = pool.available
        min_unit = self.MIN_ALLOCATION_UNIT.get(request.resource_type, 1.0)
        requested = request.amount

        # 完全满足
        if available >= requested:
            allocated = requested
        # 部分满足
        elif allow_partial and available >= min_unit:
            allocated = (available // min_unit) * min_unit
        # 无法满足
        else:
            self._failed_allocations += 1
            return ResourceAllocation(
                request=request,
                allocated_amount=0.0,
                success=False,
                message=f"资源不足: 可用 {available:.2f}, 需要 {requested:.2f}",
            )

        # 执行分配
        if pool.allocate(request.strategy_id, allocated):
            allocation_id = self._generate_allocation_id()
            expiry_time = time.time() + self._allocation_ttl

            allocation = ResourceAllocation(
                request=request,
                allocated_amount=allocated,
                success=True,
                message="分配成功" if allocated >= requested else "部分分配",
                expiry_time=expiry_time,
                allocation_id=allocation_id,
            )

            # 记录活跃分配
            self._active_allocations[allocation_id] = allocation

            # 更新使用统计
            self._update_usage_stats(request.strategy_id, request.resource_type, allocated)

            if allocated >= requested:
                self._successful_allocations += 1
            else:
                self._partial_allocations += 1

            return allocation

        # 分配失败 (竞态条件)
        self._failed_allocations += 1
        return ResourceAllocation(
            request=request,
            allocated_amount=0.0,
            success=False,
            message="分配执行失败",
        )

    def _update_usage_stats(
        self,
        strategy_id: str,
        resource_type: ResourceType,
        amount: float,
    ) -> None:
        """更新策略使用统计.

        参数:
            strategy_id: 策略ID
            resource_type: 资源类型
            amount: 分配数量
        """
        if strategy_id not in self._usage_stats:
            self._usage_stats[strategy_id] = ResourceUsage(strategy_id=strategy_id)

        usage = self._usage_stats[strategy_id]
        current = usage.allocations.get(resource_type, 0.0)
        usage.allocations[resource_type] = current + amount
        usage.total_allocated += amount
        usage.last_allocation_time = time.time()
        usage.allocation_count += 1

    def reclaim(
        self,
        strategy_id: str,
        resource_type: ResourceType | None = None,
        amount: float | None = None,
    ) -> bool:
        """回收策略资源.

        参数:
            strategy_id: 策略ID
            resource_type: 资源类型 (None表示所有类型)
            amount: 回收数量 (None表示全部回收)

        返回:
            是否有资源被回收
        """
        with self._lock:
            reclaimed = False

            if resource_type is not None:
                # 回收指定类型资源
                pool = self._pools.get(resource_type)
                if pool is not None:
                    released = pool.release(strategy_id, amount)
                    if released > 0:
                        reclaimed = True
                        self._update_usage_after_reclaim(
                            strategy_id, resource_type, released
                        )
            else:
                # 回收所有类型资源
                for rt, pool in self._pools.items():
                    released = pool.release(strategy_id, amount)
                    if released > 0:
                        reclaimed = True
                        self._update_usage_after_reclaim(strategy_id, rt, released)

            if reclaimed:
                self._reclaim_count += 1
                # 清理相关的活跃分配记录
                self._cleanup_allocations(strategy_id, resource_type)
                # 审计日志 (M3)
                self._log_reclaim_audit(strategy_id, resource_type, amount)

            return reclaimed

    def _update_usage_after_reclaim(
        self,
        strategy_id: str,
        resource_type: ResourceType,
        released: float,
    ) -> None:
        """回收后更新使用统计.

        参数:
            strategy_id: 策略ID
            resource_type: 资源类型
            released: 释放数量
        """
        if strategy_id not in self._usage_stats:
            return

        usage = self._usage_stats[strategy_id]
        current = usage.allocations.get(resource_type, 0.0)
        new_amount = max(0.0, current - released)

        if new_amount > 0:
            usage.allocations[resource_type] = new_amount
        elif resource_type in usage.allocations:
            del usage.allocations[resource_type]

        usage.total_allocated = max(0.0, usage.total_allocated - released)

    def _cleanup_allocations(
        self,
        strategy_id: str,
        resource_type: ResourceType | None,
    ) -> None:
        """清理活跃分配记录.

        参数:
            strategy_id: 策略ID
            resource_type: 资源类型 (None表示所有类型)
        """
        to_remove = []
        for alloc_id, alloc in self._active_allocations.items():
            if alloc.request.strategy_id == strategy_id:
                if resource_type is None or alloc.request.resource_type == resource_type:
                    to_remove.append(alloc_id)

        for alloc_id in to_remove:
            del self._active_allocations[alloc_id]

    def reclaim_on_circuit_break(self, strategy_id: str) -> bool:
        """熔断时自动回收资源 (M6).

        当策略触发熔断时，自动回收该策略所有资源，
        确保系统资源不被异常策略占用。

        参数:
            strategy_id: 触发熔断的策略ID

        返回:
            是否有资源被回收
        """
        reclaimed = self.reclaim(strategy_id)

        if reclaimed:
            # 记录熔断回收审计日志 (M3)
            self._log_audit(
                event_type=AuditEventType.CIRCUIT_BREAK_TRIGGERED,
                strategy_id=strategy_id,
                action="reclaim_on_circuit_break",
                result="success",
                details={
                    "reason": "熔断触发，自动回收所有资源",
                    "reclaim_time": time.time(),
                },
            )

        return reclaimed

    def get_usage(self, strategy_id: str) -> ResourceUsage:
        """获取策略资源使用情况.

        参数:
            strategy_id: 策略ID

        返回:
            资源使用情况
        """
        with self._lock:
            if strategy_id in self._usage_stats:
                return self._usage_stats[strategy_id]

            # 返回空使用记录
            return ResourceUsage(strategy_id=strategy_id)

    def get_pool_status(
        self,
        resource_type: ResourceType | None = None,
    ) -> dict[ResourceType, dict[str, Any]] | dict[str, Any]:
        """获取资源池状态.

        参数:
            resource_type: 资源类型 (None表示所有类型)

        返回:
            资源池状态字典
        """
        with self._lock:
            if resource_type is not None:
                pool = self._pools.get(resource_type)
                return pool.to_dict() if pool else {}

            return {rt: pool.to_dict() for rt, pool in self._pools.items()}

    def get_all_allocations(
        self,
        strategy_id: str | None = None,
    ) -> list[ResourceAllocation]:
        """获取所有活跃分配.

        参数:
            strategy_id: 策略ID (None表示所有策略)

        返回:
            分配列表
        """
        with self._lock:
            if strategy_id is None:
                return list(self._active_allocations.values())

            return [
                alloc
                for alloc in self._active_allocations.values()
                if alloc.request.strategy_id == strategy_id
            ]

    def cleanup_expired_allocations(self) -> int:
        """清理过期分配.

        返回:
            清理的分配数量
        """
        with self._lock:
            now = time.time()
            expired_ids = [
                alloc_id
                for alloc_id, alloc in self._active_allocations.items()
                if alloc.expiry_time > 0 and alloc.expiry_time < now
            ]

            for alloc_id in expired_ids:
                alloc = self._active_allocations[alloc_id]
                # 回收过期资源
                pool = self._pools.get(alloc.request.resource_type)
                if pool is not None:
                    pool.release(alloc.request.strategy_id, alloc.allocated_amount)

                del self._active_allocations[alloc_id]

                # 审计日志 (M3)
                self._log_audit(
                    event_type=AuditEventType.RESOURCE_RELEASED,
                    strategy_id=alloc.request.strategy_id,
                    action="cleanup_expired",
                    result="success",
                    details={
                        "allocation_id": alloc_id,
                        "resource_type": alloc.request.resource_type.value,
                        "amount": alloc.allocated_amount,
                        "reason": "allocation_expired",
                    },
                )

            return len(expired_ids)

    def reserve(
        self,
        resource_type: ResourceType,
        amount: float,
    ) -> bool:
        """预留资源 (不分配给特定策略).

        参数:
            resource_type: 资源类型
            amount: 预留数量

        返回:
            是否预留成功
        """
        with self._lock:
            pool = self._pools.get(resource_type)
            if pool is None:
                return False

            if pool.available < amount:
                return False

            pool.available -= amount
            pool.reserved += amount
            return True

    def unreserve(
        self,
        resource_type: ResourceType,
        amount: float,
    ) -> bool:
        """取消资源预留.

        参数:
            resource_type: 资源类型
            amount: 取消预留数量

        返回:
            是否取消成功
        """
        with self._lock:
            pool = self._pools.get(resource_type)
            if pool is None:
                return False

            unreserve_amount = min(pool.reserved, amount)
            pool.reserved -= unreserve_amount
            pool.available += unreserve_amount
            return True

    def adjust_pool_capacity(
        self,
        resource_type: ResourceType,
        new_capacity: float,
    ) -> bool:
        """调整资源池容量.

        参数:
            resource_type: 资源类型
            new_capacity: 新容量

        返回:
            是否调整成功
        """
        with self._lock:
            pool = self._pools.get(resource_type)
            if pool is None:
                return False

            # 计算容量变化
            delta = new_capacity - pool.total_capacity

            # 如果减少容量，检查是否会导致超额分配
            if delta < 0 and pool.available < abs(delta):
                return False

            pool.total_capacity = new_capacity
            pool.available += delta

            # 审计日志 (M3)
            self._log_audit(
                event_type=AuditEventType.RESOURCE_ALLOCATED,
                action="adjust_capacity",
                result="success",
                details={
                    "resource_type": resource_type.value,
                    "old_capacity": pool.total_capacity - delta,
                    "new_capacity": new_capacity,
                    "delta": delta,
                },
            )

            return True

    def get_statistics(self) -> dict[str, Any]:
        """获取分配器统计信息.

        返回:
            统计信息字典
        """
        with self._lock:
            pool_stats = {
                rt.value: {
                    "total": pool.total_capacity,
                    "available": pool.available,
                    "used": pool.used,
                    "reserved": pool.reserved,
                    "utilization": round(pool.utilization, 4),
                    "allocation_count": len(pool.allocations),
                }
                for rt, pool in self._pools.items()
            }

            return {
                "total_allocations": self._total_allocations,
                "successful_allocations": self._successful_allocations,
                "failed_allocations": self._failed_allocations,
                "partial_allocations": self._partial_allocations,
                "success_rate": round(self.success_rate, 4),
                "reclaim_count": self._reclaim_count,
                "active_allocation_count": len(self._active_allocations),
                "strategy_count": len(self._usage_stats),
                "pools": pool_stats,
            }

    def reset(self) -> None:
        """重置分配器状态 (仅用于测试)."""
        with self._lock:
            # 重置资源池
            for pool in self._pools.values():
                pool.available = pool.total_capacity
                pool.reserved = 0.0
                pool.allocations.clear()

            # 清空记录
            self._active_allocations.clear()
            self._usage_stats.clear()

            # 重置计数器
            self._total_allocations = 0
            self._successful_allocations = 0
            self._failed_allocations = 0
            self._partial_allocations = 0
            self._reclaim_count = 0

    def _generate_allocation_id(self) -> str:
        """生成分配ID."""
        return f"alloc_{uuid.uuid4().hex[:12]}"

    def _log_allocation_audit(
        self,
        request: ResourceRequest,
        allocation: ResourceAllocation,
    ) -> None:
        """记录分配审计日志 (M3).

        参数:
            request: 资源请求
            allocation: 分配结果
        """
        event_type = (
            AuditEventType.RESOURCE_ALLOCATED
            if allocation.success
            else AuditEventType.SIGNAL_REJECTED
        )

        self._log_audit(
            event_type=event_type,
            strategy_id=request.strategy_id,
            action="allocate",
            result="success" if allocation.success else "failed",
            details={
                "allocation_id": allocation.allocation_id,
                "resource_type": request.resource_type.value,
                "requested_amount": request.amount,
                "allocated_amount": allocation.allocated_amount,
                "priority": request.priority,
                "reason": request.reason,
                "message": allocation.message,
                "is_partial": allocation.is_partial,
            },
        )

    def _log_reclaim_audit(
        self,
        strategy_id: str,
        resource_type: ResourceType | None,
        amount: float | None,
    ) -> None:
        """记录回收审计日志 (M3).

        参数:
            strategy_id: 策略ID
            resource_type: 资源类型
            amount: 回收数量
        """
        self._log_audit(
            event_type=AuditEventType.RESOURCE_RELEASED,
            strategy_id=strategy_id,
            action="reclaim",
            result="success",
            details={
                "resource_type": resource_type.value if resource_type else "all",
                "amount": amount if amount else "all",
                "reclaim_time": time.time(),
            },
        )

    def _log_audit(
        self,
        event_type: AuditEventType,
        strategy_id: str = "",
        action: str = "",
        result: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录审计日志 (M3).

        参数:
            event_type: 事件类型
            strategy_id: 策略ID
            action: 操作
            result: 结果
            details: 详细信息
        """
        if self._audit_logger is None:
            return

        entry = AuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            timestamp=time.time(),
            strategy_id=strategy_id,
            action=action,
            result=result,
            details=details or {},
            operator="allocator",
        )

        try:
            self._audit_logger(entry)
        except Exception:
            pass  # 忽略审计日志错误，不影响主流程


def create_allocator(
    pool_capacities: dict[ResourceType, float] | None = None,
    registry: StrategyRegistry | None = None,
    audit_logger: Callable[[AuditEntry], None] | None = None,
) -> ResourceAllocator:
    """创建资源分配器.

    参数:
        pool_capacities: 自定义资源池容量
        registry: 策略注册器
        audit_logger: 审计日志回调

    返回:
        资源分配器实例
    """
    return ResourceAllocator(
        pool_capacities=pool_capacities,
        registry=registry,
        audit_logger=audit_logger,
    )


__all__ = [
    "ResourcePool",
    "ResourceUsage",
    "ResourceAllocator",
    "create_allocator",
]
