from __future__ import annotations

import argparse
from pathlib import Path

INCLUDE_FILES = [
    "README.md",
    "SPEC_RISK.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "src/risk/manager.py",
    "src/risk/state.py",
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output markdown path")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append("# Project Context (for Claude)\n")
    lines.append("## Quality gate\n")
    lines.append(
        "- GitHub Actions runs: ruff format --check, ruff check, mypy, pytest\n"
        "- Keep CI green after each feature\n"
    )
    lines.append("\n## Locked risk spec\n")
    lines.append("- See SPEC_RISK.md\n")

    lines.append("\n## Included files\n")
    for f in INCLUDE_FILES:
        if Path(f).exists():
            lines.append(f"- {f}")

    out.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()