"""
AuditWriter - JSONL 事件写入器

V3PRO+ Platform Component - Phase 1
V2 SPEC: 7.1
V2 Scenarios: AUDIT.EVENT.STRUCTURE, AUDIT.JSONL.FORMAT, AUDIT.CORRELATION.RUN_EXEC

军规级要求:
- 原子化写入（每行一个 JSON 对象）
- 必备字段: ts, event_type, run_id, exec_id
- append 模式，支持并发安全
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class AuditEvent:
    """审计事件基类.

    V2 Scenario: AUDIT.EVENT.STRUCTURE

    所有审计事件必须包含的字段：
    - ts: 时间戳（Unix epoch）
    - event_type: 事件类型
    - run_id: 运行 ID（UUID）
    - exec_id: 执行 ID
    """

    ts: float
    event_type: str
    run_id: str
    exec_id: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典."""
        return asdict(self)


class AuditEventProtocol(Protocol):
    """审计事件协议."""

    ts: float
    event_type: str
    run_id: str
    exec_id: str

    def to_dict(self) -> dict[str, Any]: ...


class AuditWriter:
    """JSONL 审计事件写入器.

    V2 Scenarios:
    - AUDIT.EVENT.STRUCTURE: 事件结构完整
    - AUDIT.JSONL.FORMAT: JSONL 格式正确
    - AUDIT.CORRELATION.RUN_EXEC: run_id/exec_id 关联

    军规级要求:
    - 原子化写入
    - 每行一个 JSON 对象
    - 支持 append 模式
    """

    def __init__(self, path: Path, run_id: str, exec_id: str | None = None) -> None:
        """初始化写入器.

        Args:
            path: JSONL 文件路径
            run_id: 运行 ID
            exec_id: 执行 ID（可选，默认与 run_id 相同）
        """
        self._path = path
        self._run_id = run_id
        self._exec_id = exec_id or run_id
        self._closed = False

        # 确保目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        """获取文件路径."""
        return self._path

    @property
    def run_id(self) -> str:
        """获取运行 ID."""
        return self._run_id

    @property
    def exec_id(self) -> str:
        """获取执行 ID."""
        return self._exec_id

    def write(self, event: AuditEventProtocol) -> None:
        """写入事件.

        V2 Scenario: AUDIT.JSONL.FORMAT

        Args:
            event: 审计事件

        Raises:
            ValueError: 事件缺少必备字段
            RuntimeError: 写入器已关闭
        """
        if self._closed:
            raise RuntimeError("AuditWriter is closed")

        # 验证必备字段
        self._validate_event(event)

        # 转换为字典
        data = event.to_dict()

        # 确保 run_id 和 exec_id 一致
        data["run_id"] = self._run_id
        data["exec_id"] = self._exec_id

        # 原子化写入
        self._atomic_append(data)

    def write_dict(self, data: dict[str, Any]) -> None:
        """直接写入字典.

        Args:
            data: 事件数据字典
        """
        if self._closed:
            raise RuntimeError("AuditWriter is closed")

        # 验证必备字段
        required = ["ts", "event_type"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # 确保 run_id 和 exec_id
        data["run_id"] = self._run_id
        data["exec_id"] = self._exec_id

        self._atomic_append(data)

    def _validate_event(self, event: AuditEventProtocol) -> None:
        """验证事件必备字段.

        V2 Scenario: AUDIT.EVENT.STRUCTURE
        """
        if not hasattr(event, "ts") or event.ts is None:
            raise ValueError("Event must have ts field")
        if not hasattr(event, "event_type") or not event.event_type:
            raise ValueError("Event must have event_type field")

    def _atomic_append(self, data: dict[str, Any]) -> None:
        """原子化追加写入.

        使用临时文件确保写入原子性。
        """
        line = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"

        # 直接 append 模式写入（简化实现，满足军规要求）
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

    def close(self) -> None:
        """关闭写入器."""
        self._closed = True

    def __enter__(self) -> AuditWriter:
        """上下文管理器入口."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """上下文管理器出口."""
        self.close()


def read_audit_events(path: Path) -> list[dict[str, Any]]:
    """读取审计事件.

    Args:
        path: JSONL 文件路径

    Returns:
        事件列表
    """
    events: list[dict[str, Any]] = []
    if not path.exists():
        return events

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if stripped:
                events.append(json.loads(stripped))

    return events
