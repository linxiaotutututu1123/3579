"""
程序化交易备案登记模块 - Registry (军规级 v4.0).

V4PRO Platform Component - Phase 9 合规监控
V4 SPEC: D7-P1 程序化交易备案
V4 Scenarios:
- CHINA.COMPLIANCE.REGISTRATION: 程序化交易备案登记

军规覆盖:
- M3: 审计日志完整 - 备案操作必须记录审计日志
- M17: 程序化合规 - 程序化交易必须完成备案

功能特性:
- 程序化交易账户备案登记
- 策略信息注册
- 备案状态查询
- 策略变更追踪
- 审计日志集成

示例:
    >>> from src.compliance.registration.registry import (
    ...     RegistrationRegistry,
    ...     StrategyRegistration,
    ... )
    >>> registry = RegistrationRegistry()
    >>> reg_info = registry.register_account(
    ...     account_id="test_account",
    ...     account_type="programmatic",
    ...     responsible_person="Zhang San",
    ... )
    >>> strategy = registry.register_strategy(
    ...     account_id="test_account",
    ...     strategy_id="trend_following_v1",
    ...     strategy_type="trend",
    ...     description="Trend following strategy",
    ... )
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RegistrationStatus(Enum):
    """备案状态枚举."""

    PENDING = "PENDING"  # 待审核
    APPROVED = "APPROVED"  # 已通过
    REJECTED = "REJECTED"  # 已拒绝
    SUSPENDED = "SUSPENDED"  # 已暂停
    EXPIRED = "EXPIRED"  # 已过期
    REVOKED = "REVOKED"  # 已撤销


class AccountType(Enum):
    """账户类型枚举."""

    PROGRAMMATIC = "PROGRAMMATIC"  # 程序化交易账户
    QUANTITATIVE = "QUANTITATIVE"  # 量化交易账户
    HIGH_FREQUENCY = "HIGH_FREQUENCY"  # 高频交易账户
    ALGORITHMIC = "ALGORITHMIC"  # 算法交易账户


class StrategyType(Enum):
    """策略类型枚举."""

    TREND = "TREND"  # 趋势跟踪
    MEAN_REVERSION = "MEAN_REVERSION"  # 均值回归
    ARBITRAGE = "ARBITRAGE"  # 套利策略
    MARKET_MAKING = "MARKET_MAKING"  # 做市策略
    STATISTICAL = "STATISTICAL"  # 统计策略
    MACHINE_LEARNING = "MACHINE_LEARNING"  # 机器学习
    OTHER = "OTHER"  # 其他


@dataclass(frozen=True)
class RegistrationInfo:
    """备案登记信息 (不可变).

    属性:
        registration_id: 备案ID
        account_id: 账户ID
        account_type: 账户类型
        responsible_person: 负责人
        contact_info: 联系方式
        registered_at: 注册时间
        status: 备案状态
        status_reason: 状态原因
        approved_at: 审批时间
        expires_at: 过期时间
        metadata: 元数据
    """

    registration_id: str
    account_id: str
    account_type: str
    responsible_person: str
    contact_info: str = ""
    registered_at: str = ""
    status: RegistrationStatus = RegistrationStatus.PENDING
    status_reason: str = ""
    approved_at: str = ""
    expires_at: str = ""
    metadata: tuple[tuple[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "registration_id": self.registration_id,
            "account_id": self.account_id,
            "account_type": self.account_type,
            "responsible_person": self.responsible_person,
            "contact_info": self.contact_info,
            "registered_at": self.registered_at,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class StrategyRegistration:
    """策略注册信息 (不可变).

    属性:
        strategy_id: 策略ID
        account_id: 所属账户ID
        strategy_type: 策略类型
        strategy_name: 策略名称
        description: 策略描述
        version: 策略版本
        code_hash: 代码哈希
        registered_at: 注册时间
        is_active: 是否激活
        parameters_hash: 参数哈希
        risk_level: 风险等级 (1-5)
        max_position: 最大持仓
        max_order_freq: 最大报单频率 (笔/秒)
    """

    strategy_id: str
    account_id: str
    strategy_type: str
    strategy_name: str = ""
    description: str = ""
    version: str = "1.0.0"
    code_hash: str = ""
    registered_at: str = ""
    is_active: bool = True
    parameters_hash: str = ""
    risk_level: int = 3
    max_position: int = 0
    max_order_freq: int = 100

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return {
            "strategy_id": self.strategy_id,
            "account_id": self.account_id,
            "strategy_type": self.strategy_type,
            "strategy_name": self.strategy_name,
            "description": self.description,
            "version": self.version,
            "code_hash": self.code_hash,
            "registered_at": self.registered_at,
            "is_active": self.is_active,
            "parameters_hash": self.parameters_hash,
            "risk_level": self.risk_level,
            "max_position": self.max_position,
            "max_order_freq": self.max_order_freq,
        }


@dataclass
class RegistrationChange:
    """备案变更记录.

    属性:
        change_id: 变更ID
        registration_id: 备案ID
        change_type: 变更类型
        old_value: 原值
        new_value: 新值
        changed_at: 变更时间
        changed_by: 变更人
        reason: 变更原因
    """

    change_id: str
    registration_id: str
    change_type: str
    old_value: str
    new_value: str
    changed_at: str
    changed_by: str = ""
    reason: str = ""


class RegistrationRegistry:
    """程序化交易备案登记中心 (军规 M3, M17).

    功能:
    - 账户备案登记
    - 策略信息注册
    - 备案状态管理
    - 变更追踪记录
    - 审计日志集成

    示例:
        >>> registry = RegistrationRegistry()
        >>> reg = registry.register_account(
        ...     account_id="acc_001",
        ...     account_type="programmatic",
        ...     responsible_person="Zhang San",
        ... )
        >>> assert reg.status == RegistrationStatus.PENDING
    """

    VERSION = "4.0"

    def __init__(
        self,
        storage_path: str | Path | None = None,
        audit_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        """初始化备案登记中心.

        参数:
            storage_path: 存储路径 (可选)
            audit_callback: 审计回调函数 (可选)
        """
        self._storage_path = Path(storage_path) if storage_path else None
        self._audit_callback = audit_callback

        # 内存存储
        self._registrations: dict[str, RegistrationInfo] = {}
        self._strategies: dict[str, StrategyRegistration] = {}
        self._changes: list[RegistrationChange] = []
        self._account_strategies: dict[str, list[str]] = {}

        # 统计
        self._registration_count: int = 0
        self._strategy_count: int = 0

        # 加载持久化数据
        if self._storage_path and self._storage_path.exists():
            self._load_from_storage()

    @property
    def registration_count(self) -> int:
        """获取备案数量."""
        return len(self._registrations)

    @property
    def strategy_count(self) -> int:
        """获取策略数量."""
        return len(self._strategies)

    def register_account(
        self,
        account_id: str,
        account_type: str,
        responsible_person: str,
        contact_info: str = "",
        metadata: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> RegistrationInfo:
        """注册程序化交易账户.

        参数:
            account_id: 账户ID
            account_type: 账户类型
            responsible_person: 负责人
            contact_info: 联系方式
            metadata: 元数据
            timestamp: 注册时间

        返回:
            备案登记信息

        异常:
            ValueError: 账户已存在
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        # 检查是否已存在
        if account_id in self._registrations:
            raise ValueError(f"账户 {account_id} 已存在备案记录")

        # 生成备案ID
        registration_id = self._generate_registration_id(account_id, timestamp)

        # 创建备案信息
        reg_info = RegistrationInfo(
            registration_id=registration_id,
            account_id=account_id,
            account_type=account_type,
            responsible_person=responsible_person,
            contact_info=contact_info,
            registered_at=timestamp.isoformat(),
            status=RegistrationStatus.PENDING,
            metadata=tuple(metadata.items()) if metadata else (),
        )

        # 存储
        self._registrations[account_id] = reg_info
        self._account_strategies[account_id] = []
        self._registration_count += 1

        # 审计日志
        self._emit_audit_event(
            event_type="REGISTRATION_CREATED",
            registration_id=registration_id,
            account_id=account_id,
            details={"account_type": account_type, "responsible_person": responsible_person},
            timestamp=timestamp,
        )

        # 持久化
        self._save_to_storage()

        logger.info(f"账户备案登记成功: {account_id} -> {registration_id}")
        return reg_info

    def register_strategy(
        self,
        account_id: str,
        strategy_id: str,
        strategy_type: str,
        strategy_name: str = "",
        description: str = "",
        version: str = "1.0.0",
        code_hash: str = "",
        risk_level: int = 3,
        max_position: int = 0,
        max_order_freq: int = 100,
        timestamp: datetime | None = None,
    ) -> StrategyRegistration:
        """注册交易策略.

        参数:
            account_id: 所属账户ID
            strategy_id: 策略ID
            strategy_type: 策略类型
            strategy_name: 策略名称
            description: 策略描述
            version: 策略版本
            code_hash: 代码哈希
            risk_level: 风险等级 (1-5)
            max_position: 最大持仓
            max_order_freq: 最大报单频率 (笔/秒)
            timestamp: 注册时间

        返回:
            策略注册信息

        异常:
            ValueError: 账户不存在或策略已存在
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        # 检查账户是否存在
        if account_id not in self._registrations:
            raise ValueError(f"账户 {account_id} 不存在备案记录, 请先完成账户备案")

        # 检查账户状态
        reg_info = self._registrations[account_id]
        if reg_info.status not in (RegistrationStatus.APPROVED, RegistrationStatus.PENDING):
            raise ValueError(
                f"账户 {account_id} 状态为 {reg_info.status.value}, 无法注册策略"
            )

        # 检查策略是否已存在
        full_strategy_id = f"{account_id}:{strategy_id}"
        if full_strategy_id in self._strategies:
            raise ValueError(f"策略 {strategy_id} 在账户 {account_id} 下已存在")

        # 创建策略注册信息
        strategy_reg = StrategyRegistration(
            strategy_id=strategy_id,
            account_id=account_id,
            strategy_type=strategy_type,
            strategy_name=strategy_name or strategy_id,
            description=description,
            version=version,
            code_hash=code_hash,
            registered_at=timestamp.isoformat(),
            is_active=True,
            risk_level=risk_level,
            max_position=max_position,
            max_order_freq=max_order_freq,
        )

        # 存储
        self._strategies[full_strategy_id] = strategy_reg
        self._account_strategies[account_id].append(strategy_id)
        self._strategy_count += 1

        # 审计日志
        self._emit_audit_event(
            event_type="STRATEGY_REGISTERED",
            registration_id=reg_info.registration_id,
            account_id=account_id,
            details={
                "strategy_id": strategy_id,
                "strategy_type": strategy_type,
                "version": version,
            },
            timestamp=timestamp,
        )

        # 持久化
        self._save_to_storage()

        logger.info(f"策略注册成功: {account_id}/{strategy_id}")
        return strategy_reg

    def update_registration_status(
        self,
        account_id: str,
        new_status: RegistrationStatus,
        reason: str = "",
        changed_by: str = "",
        timestamp: datetime | None = None,
    ) -> RegistrationInfo:
        """更新备案状态.

        参数:
            account_id: 账户ID
            new_status: 新状态
            reason: 变更原因
            changed_by: 变更人
            timestamp: 变更时间

        返回:
            更新后的备案信息

        异常:
            ValueError: 账户不存在
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        if account_id not in self._registrations:
            raise ValueError(f"账户 {account_id} 不存在备案记录")

        old_info = self._registrations[account_id]
        old_status = old_info.status

        # 创建新的备案信息 (不可变)
        new_info = RegistrationInfo(
            registration_id=old_info.registration_id,
            account_id=old_info.account_id,
            account_type=old_info.account_type,
            responsible_person=old_info.responsible_person,
            contact_info=old_info.contact_info,
            registered_at=old_info.registered_at,
            status=new_status,
            status_reason=reason,
            approved_at=timestamp.isoformat() if new_status == RegistrationStatus.APPROVED else old_info.approved_at,
            expires_at=old_info.expires_at,
            metadata=old_info.metadata,
        )

        # 记录变更
        change = RegistrationChange(
            change_id=self._generate_change_id(account_id, timestamp),
            registration_id=old_info.registration_id,
            change_type="STATUS_CHANGE",
            old_value=old_status.value,
            new_value=new_status.value,
            changed_at=timestamp.isoformat(),
            changed_by=changed_by,
            reason=reason,
        )
        self._changes.append(change)

        # 更新存储
        self._registrations[account_id] = new_info

        # 审计日志
        self._emit_audit_event(
            event_type="REGISTRATION_STATUS_CHANGED",
            registration_id=old_info.registration_id,
            account_id=account_id,
            details={
                "old_status": old_status.value,
                "new_status": new_status.value,
                "reason": reason,
                "changed_by": changed_by,
            },
            timestamp=timestamp,
        )

        # 持久化
        self._save_to_storage()

        logger.info(f"备案状态更新: {account_id} {old_status.value} -> {new_status.value}")
        return new_info

    def update_strategy(
        self,
        account_id: str,
        strategy_id: str,
        version: str | None = None,
        code_hash: str | None = None,
        is_active: bool | None = None,
        parameters_hash: str | None = None,
        changed_by: str = "",
        reason: str = "",
        timestamp: datetime | None = None,
    ) -> StrategyRegistration:
        """更新策略信息.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID
            version: 新版本
            code_hash: 新代码哈希
            is_active: 是否激活
            parameters_hash: 参数哈希
            changed_by: 变更人
            reason: 变更原因
            timestamp: 变更时间

        返回:
            更新后的策略信息

        异常:
            ValueError: 策略不存在
        """
        if timestamp is None:
            timestamp = datetime.now()  # noqa: DTZ005

        full_strategy_id = f"{account_id}:{strategy_id}"
        if full_strategy_id not in self._strategies:
            raise ValueError(f"策略 {strategy_id} 在账户 {account_id} 下不存在")

        old_strategy = self._strategies[full_strategy_id]

        # 创建新的策略信息 (不可变)
        new_strategy = StrategyRegistration(
            strategy_id=old_strategy.strategy_id,
            account_id=old_strategy.account_id,
            strategy_type=old_strategy.strategy_type,
            strategy_name=old_strategy.strategy_name,
            description=old_strategy.description,
            version=version or old_strategy.version,
            code_hash=code_hash or old_strategy.code_hash,
            registered_at=old_strategy.registered_at,
            is_active=is_active if is_active is not None else old_strategy.is_active,
            parameters_hash=parameters_hash or old_strategy.parameters_hash,
            risk_level=old_strategy.risk_level,
            max_position=old_strategy.max_position,
            max_order_freq=old_strategy.max_order_freq,
        )

        # 记录变更
        changes = []
        if version and version != old_strategy.version:
            changes.append(f"version: {old_strategy.version} -> {version}")
        if code_hash and code_hash != old_strategy.code_hash:
            changes.append(f"code_hash: {old_strategy.code_hash[:8]}... -> {code_hash[:8]}...")
        if is_active is not None and is_active != old_strategy.is_active:
            changes.append(f"is_active: {old_strategy.is_active} -> {is_active}")

        if changes:
            change = RegistrationChange(
                change_id=self._generate_change_id(full_strategy_id, timestamp),
                registration_id=self._registrations[account_id].registration_id,
                change_type="STRATEGY_UPDATE",
                old_value=str(changes),
                new_value=reason,
                changed_at=timestamp.isoformat(),
                changed_by=changed_by,
                reason=reason,
            )
            self._changes.append(change)

        # 更新存储
        self._strategies[full_strategy_id] = new_strategy

        # 审计日志
        self._emit_audit_event(
            event_type="STRATEGY_UPDATED",
            registration_id=self._registrations[account_id].registration_id,
            account_id=account_id,
            details={
                "strategy_id": strategy_id,
                "changes": changes,
                "reason": reason,
            },
            timestamp=timestamp,
        )

        # 持久化
        self._save_to_storage()

        logger.info(f"策略更新: {account_id}/{strategy_id} - {changes}")
        return new_strategy

    def get_registration(self, account_id: str) -> RegistrationInfo | None:
        """获取备案信息.

        参数:
            account_id: 账户ID

        返回:
            备案信息 (不存在返回None)
        """
        return self._registrations.get(account_id)

    def get_strategy(self, account_id: str, strategy_id: str) -> StrategyRegistration | None:
        """获取策略信息.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID

        返回:
            策略信息 (不存在返回None)
        """
        full_strategy_id = f"{account_id}:{strategy_id}"
        return self._strategies.get(full_strategy_id)

    def get_account_strategies(self, account_id: str) -> list[StrategyRegistration]:
        """获取账户下所有策略.

        参数:
            account_id: 账户ID

        返回:
            策略列表
        """
        if account_id not in self._account_strategies:
            return []

        return [
            self._strategies[f"{account_id}:{sid}"]
            for sid in self._account_strategies[account_id]
            if f"{account_id}:{sid}" in self._strategies
        ]

    def get_all_registrations(
        self,
        status: RegistrationStatus | None = None,
    ) -> list[RegistrationInfo]:
        """获取所有备案信息.

        参数:
            status: 状态过滤 (可选)

        返回:
            备案信息列表
        """
        if status is None:
            return list(self._registrations.values())
        return [r for r in self._registrations.values() if r.status == status]

    def get_changes(
        self,
        account_id: str | None = None,
        limit: int = 100,
    ) -> list[RegistrationChange]:
        """获取变更记录.

        参数:
            account_id: 账户ID过滤 (可选)
            limit: 返回数量限制

        返回:
            变更记录列表
        """
        changes = self._changes
        if account_id:
            reg = self._registrations.get(account_id)
            if reg:
                changes = [c for c in changes if c.registration_id == reg.registration_id]
        return changes[-limit:]

    def is_account_registered(self, account_id: str) -> bool:
        """检查账户是否已备案.

        参数:
            account_id: 账户ID

        返回:
            是否已备案
        """
        return account_id in self._registrations

    def is_account_approved(self, account_id: str) -> bool:
        """检查账户备案是否已通过.

        参数:
            account_id: 账户ID

        返回:
            是否已通过
        """
        reg = self._registrations.get(account_id)
        return reg is not None and reg.status == RegistrationStatus.APPROVED

    def is_strategy_active(self, account_id: str, strategy_id: str) -> bool:
        """检查策略是否激活.

        参数:
            account_id: 账户ID
            strategy_id: 策略ID

        返回:
            是否激活
        """
        strategy = self.get_strategy(account_id, strategy_id)
        return strategy is not None and strategy.is_active

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息.

        返回:
            统计信息字典
        """
        status_counts = {}
        for status in RegistrationStatus:
            status_counts[status.value] = sum(
                1 for r in self._registrations.values() if r.status == status
            )

        return {
            "total_registrations": len(self._registrations),
            "total_strategies": len(self._strategies),
            "total_changes": len(self._changes),
            "status_distribution": status_counts,
            "registry_version": self.VERSION,
        }

    def _generate_registration_id(self, account_id: str, timestamp: datetime) -> str:
        """生成备案ID."""
        data = f"{account_id}:{timestamp.isoformat()}"
        return f"REG-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def _generate_change_id(self, ref_id: str, timestamp: datetime) -> str:
        """生成变更ID."""
        data = f"{ref_id}:{timestamp.isoformat()}"
        return f"CHG-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def _emit_audit_event(
        self,
        event_type: str,
        registration_id: str,
        account_id: str,
        details: dict[str, Any],
        timestamp: datetime,
    ) -> None:
        """发送审计事件."""
        if self._audit_callback:
            event = {
                "event_type": event_type,
                "registration_id": registration_id,
                "account_id": account_id,
                "details": details,
                "timestamp": timestamp.isoformat(),
                "module": "compliance.registration",
                "military_rules": ["M3", "M17"],
            }
            try:
                self._audit_callback(event)
            except Exception as e:
                logger.error(f"审计回调失败: {e}")

    def _save_to_storage(self) -> None:
        """保存到持久化存储."""
        if not self._storage_path:
            return

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "registrations": {
                    k: v.to_dict() for k, v in self._registrations.items()
                },
                "strategies": {
                    k: v.to_dict() for k, v in self._strategies.items()
                },
                "account_strategies": self._account_strategies,
                "version": self.VERSION,
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存备案数据失败: {e}")

    def _load_from_storage(self) -> None:
        """从持久化存储加载."""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, encoding="utf-8") as f:
                data = json.load(f)

            # 加载备案信息
            for account_id, reg_dict in data.get("registrations", {}).items():
                self._registrations[account_id] = RegistrationInfo(
                    registration_id=reg_dict["registration_id"],
                    account_id=reg_dict["account_id"],
                    account_type=reg_dict["account_type"],
                    responsible_person=reg_dict["responsible_person"],
                    contact_info=reg_dict.get("contact_info", ""),
                    registered_at=reg_dict["registered_at"],
                    status=RegistrationStatus(reg_dict["status"]),
                    status_reason=reg_dict.get("status_reason", ""),
                    approved_at=reg_dict.get("approved_at", ""),
                    expires_at=reg_dict.get("expires_at", ""),
                    metadata=tuple(reg_dict.get("metadata", {}).items()),
                )

            # 加载策略信息
            for full_id, strategy_dict in data.get("strategies", {}).items():
                self._strategies[full_id] = StrategyRegistration(
                    strategy_id=strategy_dict["strategy_id"],
                    account_id=strategy_dict["account_id"],
                    strategy_type=strategy_dict["strategy_type"],
                    strategy_name=strategy_dict.get("strategy_name", ""),
                    description=strategy_dict.get("description", ""),
                    version=strategy_dict.get("version", "1.0.0"),
                    code_hash=strategy_dict.get("code_hash", ""),
                    registered_at=strategy_dict["registered_at"],
                    is_active=strategy_dict.get("is_active", True),
                    parameters_hash=strategy_dict.get("parameters_hash", ""),
                    risk_level=strategy_dict.get("risk_level", 3),
                    max_position=strategy_dict.get("max_position", 0),
                    max_order_freq=strategy_dict.get("max_order_freq", 100),
                )

            # 加载账户策略映射
            self._account_strategies = data.get("account_strategies", {})

            logger.info(f"加载备案数据: {len(self._registrations)} 账户, {len(self._strategies)} 策略")
        except Exception as e:
            logger.error(f"加载备案数据失败: {e}")


# ============================================================
# 便捷函数
# ============================================================


def create_registration_registry(
    storage_path: str | Path | None = None,
    audit_callback: Callable[[dict[str, Any]], None] | None = None,
) -> RegistrationRegistry:
    """创建备案登记中心.

    参数:
        storage_path: 存储路径 (可选)
        audit_callback: 审计回调函数 (可选)

    返回:
        备案登记中心实例
    """
    return RegistrationRegistry(storage_path, audit_callback)
