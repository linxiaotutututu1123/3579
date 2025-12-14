"""Export project context for AI assistants (Claude/Copilot).

Supports 3 levels:
- lite:  Minimal context (README, tree, pyproject, key specs)
- dev:   Development context (+ interfaces, types, runner, orchestrator)
- debug: Debug context (+ recent test failures, audit summaries)

Security: Automatically filters sensitive files (.env, secrets, CTP accounts).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


# =============================================================================
# 分层文件列表
# =============================================================================

# Lite: 最小上下文
INCLUDE_LITE: list[str] = [
    "README.md",
    "pyproject.toml",
    "SPEC_RISK.md",
    "docs/SPEC_CONTRACT_AUTOORDER.md",
]

# Dev: 开发上下文 (Lite + 接口/类型/核心模块)
INCLUDE_DEV: list[str] = [
    *INCLUDE_LITE,
    "requirements.txt",
    "requirements-dev.txt",
    "src/config.py",
    "src/runner.py",
    "src/orchestrator.py",
    "src/strategy/types.py",
    "src/execution/broker.py",
    "src/execution/order_types.py",
    "src/risk/manager.py",
    "src/risk/state.py",
    "src/trading/live_guard.py",
    "src/trading/ci_gate.py",
]

# Debug: 调试上下文 (Dev + 日志/审计)
INCLUDE_DEBUG: list[str] = [
    *INCLUDE_DEV,
    "src/main.py",
    "src/execution/ctp_broker.py",
    "src/execution/order_tracker.py",
]

LEVEL_MAP: dict[str, list[str]] = {
    "lite": INCLUDE_LITE,
    "dev": INCLUDE_DEV,
    "debug": INCLUDE_DEBUG,
}

# =============================================================================
# 安全过滤：这些文件/模式永远不导出
# =============================================================================

BLOCKED_PATTERNS: list[str] = [
    ".env",
    ".env.*",
    "*.env",
    "secrets.*",
    "*secret*",
    "*password*",
    "*token*",
    "*ctp_*account*",
    "*broker_config*",
    "*credentials*",
    "*.pem",
    "*.key",
    "*.p12",
    "__pycache__/*",
    ".git/*",
    ".venv/*",
    "node_modules/*",
]


def is_blocked(filepath: str) -> bool:
    """Check if a file matches any blocked pattern."""
    path = Path(filepath)
    name = path.name
    for pattern in BLOCKED_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(filepath, pattern):
            return True
        if fnmatch.fnmatch(str(path), pattern):
            return True
    return False


def safe_read_file(filepath: str, max_lines: int = 500) -> str | None:
    """Read file content safely, with line limit and security check."""
    if is_blocked(filepath):
        return None

    path = Path(filepath)
    if not path.exists():
        return None

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines.append(f"\n... (truncated, {len(lines)} of {len(content.splitlines())} lines)")
        return "\n".join(lines)
    except Exception:
        return None


def get_tree_output() -> str:
    """Get directory tree (safe, no sensitive paths)."""
    try:
        # Windows tree command
        result = subprocess.run(
            ["tree", "/F", "/A"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=".",
        )
        lines = result.stdout.splitlines()
        # Filter out sensitive directories
        filtered = []
        skip_depth = -1
        for line in lines:
            # Skip .venv, .git, __pycache__, node_modules
            if any(s in line for s in [".venv", ".git", "__pycache__", "node_modules"]):
                # Calculate depth to skip children
                skip_depth = len(line) - len(line.lstrip())
                continue
            current_depth = len(line) - len(line.lstrip())
            if skip_depth >= 0 and current_depth > skip_depth:
                continue
            skip_depth = -1
            filtered.append(line)
        return "\n".join(filtered[:200])  # Limit lines
    except Exception:
        return "(tree unavailable)"


def get_git_info() -> dict[str, str]:
    """Get git commit and status info."""
    info: dict[str, str] = {}
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        info["commit"] = result.stdout.strip()[:12]
    except Exception:
        info["commit"] = "unknown"

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        info["branch"] = result.stdout.strip()
    except Exception:
        info["branch"] = "unknown"

    return info


def get_recent_test_failures() -> str:
    """Get recent test failure summary (for debug level)."""
    # Look for pytest cache or recent logs
    cache_path = Path(".pytest_cache/v/cache/lastfailed")
    if cache_path.exists():
        try:
            content = cache_path.read_text(encoding="utf-8")
            data = json.loads(content)
            if data:
                failures = list(data.keys())[:10]
                return "Recent test failures:\n" + "\n".join(f"  - {f}" for f in failures)
        except Exception:
            pass
    return "(no recent test failures)"


def get_audit_summary() -> str:
    """Get recent audit log summary (for debug level)."""
    audit_dir = Path("artifacts/audit")
    if not audit_dir.exists():
        return "(no audit logs)"

    jsonl_files = sorted(audit_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not jsonl_files:
        return "(no audit logs)"

    # Read last 5 lines from most recent file
    try:
        recent_file = jsonl_files[0]
        audit_lines = recent_file.read_text(encoding="utf-8").splitlines()[-5:]
        return f"Recent audit ({recent_file.name}):\n" + "\n".join(
            f"  {line[:100]}..." for line in audit_lines
        )
    except Exception:
        return "(audit read error)"


def main() -> None:
    ap = argparse.ArgumentParser(description="Export project context for AI assistants")
    ap.add_argument("--out", required=True, help="Output markdown path")
    ap.add_argument(
        "--level",
        choices=["lite", "dev", "debug"],
        default="lite",
        help="Context level: lite, dev, or debug",
    )
    args = ap.parse_args()

    out: Path = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    level: str = args.level
    include_files = LEVEL_MAP[level]

    # Build context
    lines: list[str] = []
    timestamp = datetime.now(UTC).isoformat()
    git_info = get_git_info()

    lines.append("# Project Context (for Claude/Copilot)\n")
    lines.append(f"Generated: {timestamp}")
    lines.append(f"Level: {level}")
    lines.append(f"Git: {git_info['branch']}@{git_info['commit']}\n")

    # Quality gate
    lines.append("## Quality Gate\n")
    lines.append("```")
    lines.append("make ci   # Runs: format-check + lint + type + test (85% coverage)")
    lines.append("```")
    lines.append("- Exit codes: 0=pass, 2=format/lint, 3=type, 4=test, 5=coverage\n")

    # Directory tree (lite and up)
    lines.append("## Directory Structure\n")
    lines.append("```")
    lines.append(get_tree_output())
    lines.append("```\n")

    # Included files
    lines.append(f"## Included Files ({len(include_files)} files)\n")
    for f in include_files:
        if is_blocked(f):
            continue
        content = safe_read_file(f)
        if content:
            lines.append(f"### {f}\n")
            ext = Path(f).suffix.lstrip(".")
            lang = {"py": "python", "md": "markdown", "toml": "toml", "yml": "yaml"}.get(ext, "")
            lines.append(f"```{lang}")
            lines.append(content)
            lines.append("```\n")

    # Debug-specific content
    if level == "debug":
        lines.append("## Debug Info\n")
        lines.append("### Recent Test Failures\n")
        lines.append("```")
        lines.append(get_recent_test_failures())
        lines.append("```\n")
        lines.append("### Audit Summary\n")
        lines.append("```")
        lines.append(get_audit_summary())
        lines.append("```\n")

    # Security notice
    lines.append("---")
    lines.append("*Security: .env, secrets, credentials, CTP accounts are auto-filtered.*\n")

    # Write output
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Context exported: {out} (level={level}, files={len(include_files)})")


if __name__ == "__main__":
    main()
