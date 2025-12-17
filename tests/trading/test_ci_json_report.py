"""Tests for CI JSON Report (Military-Grade v3.0)."""

from __future__ import annotations

from pathlib import Path

from src.trading.ci_gate import (
    CIJsonReport,
    CIStep,
    CIStepStatus,
    _compute_context_sha,
    _generate_exec_id,
    _generate_run_id,
)


class TestMilitaryGradeHelpers:
    """Tests for military-grade helper functions."""

    def test_generate_run_id_is_uuid(self) -> None:
        """run_id should be valid UUID format."""
        run_id = _generate_run_id()
        assert len(run_id) == 36
        assert run_id.count("-") == 4

    def test_generate_exec_id_format(self) -> None:
        """exec_id should be commit_timestamp format."""
        exec_id = _generate_exec_id()
        assert "_" in exec_id
        parts = exec_id.split("_")
        assert len(parts) == 2
        # Timestamp part should be 14 digits
        assert len(parts[1]) == 14
        assert parts[1].isdigit()

    def test_compute_context_sha_missing_file(self) -> None:
        """SHA of missing file is empty string."""
        sha = _compute_context_sha(Path("nonexistent/file.md"))
        assert sha == ""


class TestCIJsonReport:
    """Tests for CIJsonReport military-grade schema."""

    def test_default_schema_version(self) -> None:
        """Default schema_version is 3."""
        report = CIJsonReport()
        assert report.schema_version == 3

    def test_check_mode_true(self) -> None:
        """check_mode can be set to True."""
        report = CIJsonReport(check_mode=True)
        assert report.check_mode is True

    def test_auto_generates_run_id(self) -> None:
        """run_id is auto-generated if not provided."""
        report = CIJsonReport()
        assert report.run_id
        assert len(report.run_id) == 36

    def test_auto_generates_exec_id(self) -> None:
        """exec_id is auto-generated if not provided."""
        report = CIJsonReport()
        assert report.exec_id
        assert "_" in report.exec_id

    def test_auto_generates_timestamp(self) -> None:
        """timestamp is auto-generated if not provided."""
        report = CIJsonReport()
        assert report.timestamp
        assert "T" in report.timestamp  # ISO format

    def test_all_passed_with_no_steps(self) -> None:
        """all_passed is True when no steps."""
        report = CIJsonReport()
        assert report.all_passed is True

    def test_all_passed_with_passing_steps(self) -> None:
        """all_passed is True when all steps pass."""
        report = CIJsonReport()
        report.add_step(CIStep(name="format-check", status=CIStepStatus.PASS))
        report.add_step(CIStep(name="lint", status=CIStepStatus.PASS))
        assert report.all_passed is True

    def test_not_all_passed_with_failing_step(self) -> None:
        """all_passed is False when any step fails."""
        report = CIJsonReport()
        report.add_step(CIStep(name="format-check", status=CIStepStatus.PASS))
        report.add_step(CIStep(name="lint", status=CIStepStatus.FAIL, exit_code=2))
        assert report.all_passed is False

    def test_overall_pass(self) -> None:
        """overall returns PASS when all passed."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert report.overall == "PASS"

    def test_overall_fail(self) -> None:
        """overall returns FAIL when any failed."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.FAIL, exit_code=4))
        assert report.overall == "FAIL"

    def test_exit_code_zero_on_pass(self) -> None:
        """exit_code is 0 when all passed."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS, exit_code=0))
        assert report.exit_code == 0

    def test_exit_code_from_failed_step(self) -> None:
        """exit_code comes from first failed step."""
        report = CIJsonReport()
        report.add_step(CIStep(name="lint", status=CIStepStatus.FAIL, exit_code=2))
        report.add_step(CIStep(name="test", status=CIStepStatus.FAIL, exit_code=4))
        assert report.exit_code == 2  # First failure

    def test_to_dict_has_required_fields(self) -> None:
        """to_dict includes all military-grade required fields."""
        report = CIJsonReport(check_mode=True)
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        d = report.to_dict()

        # Military-grade required fields
        assert "schema_version" in d
        assert d["schema_version"] == 3
        assert "type" in d
        assert d["type"] == "ci"
        assert "overall" in d
        assert "exit_code" in d
        assert "check_mode" in d
        assert d["check_mode"] is True
        assert "timestamp" in d
        assert "run_id" in d
        assert "exec_id" in d
        assert "artifacts" in d
        assert "steps" in d

    def test_to_dict_artifacts_has_report_path(self) -> None:
        """artifacts includes report_path."""
        report = CIJsonReport()
        d = report.to_dict()
        assert "report_path" in d["artifacts"]

    def test_to_json_is_valid(self) -> None:
        """to_json returns valid JSON string."""
        import json

        report = CIJsonReport()
        json_str = report.to_json()
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == 3

    def test_failed_step_returns_first_failure(self) -> None:
        """failed_step returns first failed step name."""
        report = CIJsonReport()
        report.add_step(CIStep(name="format-check", status=CIStepStatus.PASS))
        report.add_step(CIStep(name="lint", status=CIStepStatus.FAIL, exit_code=2))
        assert report.failed_step == "lint"

    def test_failed_step_none_when_all_pass(self) -> None:
        """failed_step is None when all passed."""
        report = CIJsonReport()
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        assert report.failed_step is None

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save creates JSON file."""
        report = CIJsonReport(check_mode=True)
        report.add_step(CIStep(name="test", status=CIStepStatus.PASS))
        output = tmp_path / "report.json"
        report.save(output)
        assert output.exists()
        import json

        content = json.loads(output.read_text())
        assert content["schema_version"] == 3


class TestCIStep:
    """Tests for CIStep."""

    def test_to_dict_basic(self) -> None:
        """to_dict includes basic fields."""
        step = CIStep(name="test", status=CIStepStatus.PASS, exit_code=0, duration_ms=100)
        d = step.to_dict()
        assert d["name"] == "test"
        assert d["status"] == "PASS"
        assert d["exit_code"] == 0
        assert d["duration_ms"] == 100

    def test_to_dict_skip_includes_reason(self) -> None:
        """SKIP status includes reason."""
        step = CIStep(name="test", status=CIStepStatus.SKIP, reason="previous failed")
        d = step.to_dict()
        assert d["reason"] == "previous failed"

    def test_to_dict_fail_includes_summary(self) -> None:
        """FAIL status includes summary."""
        step = CIStep(name="test", status=CIStepStatus.FAIL, summary="Error output")
        d = step.to_dict()
        assert d["summary"] == "Error output"
