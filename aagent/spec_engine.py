"""Minimal spec engine: generate a design.md file using spec-design template."""
from pathlib import Path

TEMPLATE = """# 设计文档：{feature}

> **版本**: v0.1
> **状态**: 草稿
> **语言**: {lang}

---

## 执行摘要

自动生成的设计文档（演示）。
"""


def render_design(feature: str, lang: str = "zh", output: Path = None):
    content = TEMPLATE.format(feature=feature, lang=lang)
    if output is None:
        output = Path(f".claude/specs/{feature}/design.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output
