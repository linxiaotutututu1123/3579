"""Replay validation entry point.

Usage:
    python -m src.trading.replay [options]

This module provides a unified entry point for replay validation that:
- Automatically enables CHECK_MODE (blocks broker operations)
- Outputs JSON report to artifacts/replay/report.json (军规级分目录)
- Returns fixed exit codes (0=pass, 8=fail)
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import subprocess
import sys
import time

from src.trading.ci_gate import enable_check_mode, is_check_mode
from src.trading.sim_gate import SimExitCode, SimGate


logger = logging.getLogger(__name__)

# 军规级：replay 产物写入独立目录 artifacts/replay/
DEFAULT_OUTPUT = "artifacts/replay/report.json"


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def run_replay_tests(
    python_exe: str,
    pattern: str = "replay",
    verbose: bool = False,
) -> tuple[bool, str, int]:  # pragma: no cover
    """
    Run replay tests via pytest.

    Args:
        python_exe: Path to Python executable
        pattern: Test pattern to match
        verbose: Enable verbose output

    Returns:
        Tuple of (passed, output, duration_ms)
    """
    start = time.time()

    cmd = [
        python_exe,
        "-m",
        "pytest",
        "tests/",
        "-k",
        pattern,
        "-q",
        "--tb=short",
    ]
    if verbose:
        cmd.append("-v")

    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        duration_ms = int((time.time() - start) * 1000)
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return passed, output, duration_ms

    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        return False, "Timeout after 300 seconds", duration_ms


def parse_test_output(output: str) -> tuple[int, int, list[str]]:
    """
    Parse pytest output for pass/fail counts.

    Returns:
        Tuple of (passed_count, failed_count, failure_names)
    """
    passed = 0
    failed = 0
    failures: list[str] = []

    for line in output.split("\n"):
        # Look for summary line like "10 passed" or "3 failed, 7 passed"
        if "passed" in line.lower() or "failed" in line.lower():
            # Strip punctuation for comparison (handles "failed," case)
            parts = line.split()
            for i, part in enumerate(parts):
                clean_part = part.rstrip(",")
                if clean_part == "passed" and i > 0:
                    with contextlib.suppress(ValueError):
                        passed = int(parts[i - 1])
                if clean_part == "failed" and i > 0:
                    with contextlib.suppress(ValueError):
                        failed = int(parts[i - 1])

        # Collect FAILED test names
        if "FAILED" in line:
            # Format: FAILED tests/test_foo.py::test_bar
            parts = line.split()
            if len(parts) >= 2:
                test_name = parts[1].split("::")[-1] if "::" in parts[1] else parts[1]
                failures.append(test_name)

    return passed, failed, failures


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    """
    Main entry point for replay validation.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0=pass, 8=fail)
    """
    parser = argparse.ArgumentParser(
        description="Run replay validation with CHECK_MODE enabled",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m src.trading.replay                    # Run all replay tests
    python -m src.trading.replay -p deterministic   # Run deterministic tests only
    python -m src.trading.replay -v                 # Verbose output
    python -m src.trading.replay -o custom.json     # Custom output path
        """,
    )
    parser.add_argument(
        "-p",
        "--pattern",
        default="replay",
        help="Test pattern to match (default: replay)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON report path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--python",
        default=".venv/Scripts/python.exe",
        help="Path to Python executable",
    )

    args = parser.parse_args(argv)

    setup_logging(args.verbose)

    # CRITICAL: Enable CHECK_MODE before any operations
    enable_check_mode()
    logger.info("CHECK_MODE enabled: %s", is_check_mode())

    # Initialize gate - Military-Grade v3.0: check_mode MUST be True
    gate = SimGate(sim_type="replay", check_mode=True)

    # Run replay tests
    logger.info("Running replay tests (pattern: %s)...", args.pattern)
    passed, output, duration_ms = run_replay_tests(
        python_exe=args.python,
        pattern=args.pattern,
        verbose=args.verbose,
    )

    # Parse results
    passed_count, failed_count, failures = parse_test_output(output)

    # Record results
    if passed:
        gate.record_pass("replay_tests")
        logger.info("All replay tests passed")
    else:
        for failure in failures:
            gate.record_failure(
                scenario=failure,
                tick=0,
                expected={"status": "pass"},
                actual={"status": "fail"},
                error=f"Test {failure} failed",
            )
        if not failures:
            # Fallback if we couldn't parse failures
            gate.record_failure(
                scenario="replay_tests",
                tick=0,
                expected={"status": "pass"},
                actual={"status": "fail"},
                error=output[-500:] if len(output) > 500 else output,
            )

    # Set metrics
    gate.set_metrics(
        total_ticks=passed_count + failed_count,
        avg_tick_duration_ms=duration_ms / max(passed_count + failed_count, 1),
    )

    # Save report
    gate.save_report(args.output)
    logger.info("Report saved to %s", args.output)

    # Print summary
    report = gate.report
    print(f"\n{'=' * 60}")
    print(f"Replay Validation: {report.overall.value}")
    print(f"  Passed: {report.scenarios_passed}")
    print(f"  Failed: {report.scenarios_failed}")
    print(f"  Duration: {duration_ms}ms")
    print(f"  Report: {args.output}")
    print(f"{'=' * 60}\n")

    if report.failures:
        print("Failures:")
        for f in report.failures:
            print(f"  - {f.scenario}: {f.error}")
        print()

    return SimExitCode.SUCCESS if passed else SimExitCode.REPLAY_FAIL


if __name__ == "__main__":
    sys.exit(main())
