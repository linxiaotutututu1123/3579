"""文件操作模块 - 异步文件读写和搜索."""

from __future__ import annotations

import asyncio
import difflib
import fnmatch
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class FileInfo:
    """文件信息."""
    path: Path
    size: int = 0
    modified: datetime | None = None
    is_dir: bool = False
    encoding: str = "utf-8"


@dataclass
class FileContent:
    """文件内容."""
    path: Path
    content: str
    encoding: str = "utf-8"
    line_count: int = 0


@dataclass
class DiffResult:
    """差异结果."""
    original: str
    modified: str
    unified_diff: str
    added_lines: int = 0
    removed_lines: int = 0


@dataclass
class SearchResult:
    """搜索结果."""
    path: Path
    line_number: int
    line_content: str
    match_start: int = 0
    match_end: int = 0


class FileOperations:
    """异步文件操作类."""

    def __init__(
        self,
        base_dir: Path | None = None,
        default_encoding: str = "utf-8",
    ) -> None:
        self._base_dir = base_dir or Path.cwd()
        self._encoding = default_encoding

    def _resolve(self, path: Path | str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self._base_dir / p
        return p.resolve()

    async def read(
        self,
        path: Path | str,
        encoding: str | None = None,
    ) -> FileContent:
        """读取文件."""
        resolved = self._resolve(path)
        enc = encoding or self._encoding

        def _read() -> str:
            return resolved.read_text(encoding=enc)

        content = await asyncio.get_event_loop().run_in_executor(None, _read)
        return FileContent(
            path=resolved,
            content=content,
            encoding=enc,
            line_count=content.count("\n") + 1,
        )

    async def read_lines(
        self,
        path: Path | str,
        start: int = 0,
        end: int | None = None,
    ) -> list[str]:
        """读取指定行范围."""
        fc = await self.read(path)
        lines = fc.content.splitlines()
        return lines[start:end]

    async def write(
        self,
        path: Path | str,
        content: str,
        encoding: str | None = None,
        create_dirs: bool = True,
    ) -> FileInfo:
        """写入文件."""
        resolved = self._resolve(path)
        enc = encoding or self._encoding

        def _write() -> None:
            if create_dirs:
                resolved.parent.mkdir(parents=True, exist_ok=True)
            resolved.write_text(content, encoding=enc)

        await asyncio.get_event_loop().run_in_executor(None, _write)

        stat = resolved.stat()
        return FileInfo(
            path=resolved,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
        )

    async def append(
        self,
        path: Path | str,
        content: str,
        encoding: str | None = None,
    ) -> FileInfo:
        """追加内容."""
        resolved = self._resolve(path)
        enc = encoding or self._encoding

        def _append() -> None:
            with open(resolved, "a", encoding=enc) as f:
                f.write(content)

        await asyncio.get_event_loop().run_in_executor(None, _append)
        stat = resolved.stat()
        return FileInfo(path=resolved, size=stat.st_size)

    async def delete(self, path: Path | str) -> bool:
        """删除文件."""
        resolved = self._resolve(path)

        def _delete() -> bool:
            if resolved.exists():
                resolved.unlink()
                return True
            return False

        return await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def exists(self, path: Path | str) -> bool:
        """检查文件是否存在."""
        resolved = self._resolve(path)
        return await asyncio.get_event_loop().run_in_executor(
            None, resolved.exists
        )

    async def info(self, path: Path | str) -> FileInfo | None:
        """获取文件信息."""
        resolved = self._resolve(path)

        def _info() -> FileInfo | None:
            if not resolved.exists():
                return None
            stat = resolved.stat()
            return FileInfo(
                path=resolved,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                is_dir=resolved.is_dir(),
            )

        return await asyncio.get_event_loop().run_in_executor(None, _info)

    async def search(
        self,
        pattern: str,
        directory: Path | str | None = None,
        recursive: bool = True,
    ) -> list[Path]:
        """按glob模式搜索文件."""
        base = self._resolve(directory) if directory else self._base_dir

        def _search() -> list[Path]:
            if recursive:
                return list(base.rglob(pattern))
            return list(base.glob(pattern))

        return await asyncio.get_event_loop().run_in_executor(None, _search)

    async def grep(
        self,
        pattern: str,
        path: Path | str,
        case_sensitive: bool = True,
    ) -> list[SearchResult]:
        """在文件中搜索内容."""
        fc = await self.read(path)
        results = []
        search_pattern = pattern if case_sensitive else pattern.lower()

        for i, line in enumerate(fc.content.splitlines(), 1):
            search_line = line if case_sensitive else line.lower()
            idx = search_line.find(search_pattern)
            if idx >= 0:
                results.append(SearchResult(
                    path=fc.path,
                    line_number=i,
                    line_content=line,
                    match_start=idx,
                    match_end=idx + len(pattern),
                ))
        return results

    async def diff(
        self,
        original: str,
        modified: str,
        context_lines: int = 3,
    ) -> DiffResult:
        """生成差异."""
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            orig_lines, mod_lines,
            fromfile="original", tofile="modified",
            n=context_lines,
        ))

        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        return DiffResult(
            original=original,
            modified=modified,
            unified_diff="".join(diff_lines),
            added_lines=added,
            removed_lines=removed,
        )

    async def copy(
        self,
        src: Path | str,
        dst: Path | str,
    ) -> FileInfo:
        """复制文件."""
        fc = await self.read(src)
        return await self.write(dst, fc.content, fc.encoding)

    async def move(
        self,
        src: Path | str,
        dst: Path | str,
    ) -> FileInfo:
        """移动文件."""
        info = await self.copy(src, dst)
        await self.delete(src)
        return info

    async def list_dir(
        self,
        path: Path | str | None = None,
        pattern: str | None = None,
    ) -> list[FileInfo]:
        """列出目录内容."""
        base = self._resolve(path) if path else self._base_dir

        def _list() -> list[FileInfo]:
            results = []
            for item in base.iterdir():
                if pattern and not fnmatch.fnmatch(item.name, pattern):
                    continue
                stat = item.stat()
                results.append(FileInfo(
                    path=item,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    is_dir=item.is_dir(),
                ))
            return results

        return await asyncio.get_event_loop().run_in_executor(None, _list)


__all__ = [
    "FileInfo", "FileContent", "DiffResult", "SearchResult",
    "FileOperations",
]
