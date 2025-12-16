"""
AuditWriter 测试.

V2 Scenarios:
- AUDIT.EVENT.STRUCTURE: 事件结构完整
- AUDIT.JSONL.FORMAT: JSONL 格式正确
- AUDIT.CORRELATION.RUN_EXEC: run_id/exec_id 关联
"""

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from src.audit.writer import AuditEvent, AuditWriter, read_audit_events


class TestAuditWriter:
    """AuditWriter 测试类."""

    def test_audit_event_structure(self) -> None:
        """AUDIT.EVENT.STRUCTURE: 事件结构完整."""
        event = AuditEvent(
            ts=1234567890.123,
            event_type="TEST",
            run_id="run-001",
            exec_id="exec-001",
        )

        data = event.to_dict()

        assert data["ts"] == 1234567890.123
        assert data["event_type"] == "TEST"
        assert data["run_id"] == "run-001"
        assert data["exec_id"] == "exec-001"

    def test_audit_jsonl_format(self) -> None:
        """AUDIT.JSONL.FORMAT: JSONL 格式正确."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            with AuditWriter(path, run_id="run-001", exec_id="exec-001") as writer:
                event1 = AuditEvent(
                    ts=1.0,
                    event_type="EVENT1",
                    run_id="",
                    exec_id="",
                )
                event2 = AuditEvent(
                    ts=2.0,
                    event_type="EVENT2",
                    run_id="",
                    exec_id="",
                )
                writer.write(event1)
                writer.write(event2)

            # 读取并验证 JSONL 格式
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 2
            for line in lines:
                data = json.loads(line.strip())
                assert "ts" in data
                assert "event_type" in data

    def test_audit_correlation_run_exec(self) -> None:
        """AUDIT.CORRELATION.RUN_EXEC: run_id/exec_id 关联."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            run_id = "run-correlation-001"
            exec_id = "exec-correlation-001"

            with AuditWriter(path, run_id=run_id, exec_id=exec_id) as writer:
                event = AuditEvent(
                    ts=1.0,
                    event_type="TEST",
                    run_id="ignored",
                    exec_id="ignored",
                )
                writer.write(event)

            events = read_audit_events(path)
            assert len(events) == 1
            # Writer 强制覆盖 run_id 和 exec_id
            assert events[0]["run_id"] == run_id
            assert events[0]["exec_id"] == exec_id

    def test_writer_properties(self) -> None:
        """测试写入器属性."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            writer = AuditWriter(path, run_id="run-001", exec_id="exec-001")

            assert writer.path == path
            assert writer.run_id == "run-001"
            assert writer.exec_id == "exec-001"

            writer.close()

    def test_writer_write_after_close(self) -> None:
        """测试关闭后写入."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            writer = AuditWriter(path, run_id="run-001")
            writer.close()

            event = AuditEvent(ts=1.0, event_type="TEST", run_id="", exec_id="")
            with pytest.raises(RuntimeError, match="closed"):
                writer.write(event)

    def test_writer_validate_event_missing_ts(self) -> None:
        """测试事件验证 - 缺少 ts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            writer = AuditWriter(path, run_id="run-001")

            class BadEvent:
                ts = None
                event_type = "TEST"
                run_id = ""
                exec_id = ""

                def to_dict(self) -> dict:
                    return {}

            with pytest.raises(ValueError, match="ts"):
                writer.write(BadEvent())  # type: ignore[arg-type]

            writer.close()

    def test_writer_validate_event_missing_event_type(self) -> None:
        """测试事件验证 - 缺少 event_type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            writer = AuditWriter(path, run_id="run-001")

            class BadEvent:
                ts = 1.0
                event_type = ""
                run_id = ""
                exec_id = ""

                def to_dict(self) -> dict:
                    return {"ts": 1.0}

            with pytest.raises(ValueError, match="event_type"):
                writer.write(BadEvent())  # type: ignore[arg-type]

            writer.close()

    def test_write_dict(self) -> None:
        """测试直接写入字典."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            with AuditWriter(path, run_id="run-001", exec_id="exec-001") as writer:
                writer.write_dict({"ts": 1.0, "event_type": "DICT_EVENT"})

            events = read_audit_events(path)
            assert len(events) == 1
            assert events[0]["event_type"] == "DICT_EVENT"
            assert events[0]["run_id"] == "run-001"

    def test_write_dict_missing_required(self) -> None:
        """测试字典写入缺少必备字段."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            with (
                AuditWriter(path, run_id="run-001") as writer,
                pytest.raises(ValueError, match="ts"),
            ):
                writer.write_dict({"event_type": "TEST"})

    def test_read_empty_file(self) -> None:
        """测试读取空文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.jsonl"
            events = read_audit_events(path)
            assert events == []

    def test_context_manager(self) -> None:
        """测试上下文管理器."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            with AuditWriter(path, run_id="run-001") as writer:
                event = AuditEvent(ts=1.0, event_type="TEST", run_id="", exec_id="")
                writer.write(event)

            # 退出后写入应失败
            with pytest.raises(RuntimeError):
                writer.write(event)

    def test_exec_id_defaults_to_run_id(self) -> None:
        """测试 exec_id 默认值."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            writer = AuditWriter(path, run_id="run-only")
            assert writer.exec_id == "run-only"
            writer.close()
