from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core import Result
from ..domain.errors import AppError
from ..localops import (
    append_local_file,
    grep_local_path,
    list_local_path,
    mkdir_local_path,
    read_local_file,
    stat_local_path,
    write_local_file,
)


class LocalService:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def read_file(
        self,
        path: str,
        *,
        start_line: int | None = None,
        end_line: int | None = None,
        encoding: str = "utf-8",
    ) -> Result[dict[str, Any], AppError]:
        return read_local_file(self.root, path, start_line=start_line, end_line=end_line, encoding=encoding)

    def list_path(
        self,
        path: str,
        *,
        recursive: bool = False,
        kind: str = "all",
        pattern: str | None = None,
    ) -> Result[dict[str, Any], AppError]:
        return list_local_path(self.root, path, recursive=recursive, kind=kind, pattern=pattern)

    def grep_path(
        self,
        path: str,
        *,
        pattern: str,
        glob: str | None = None,
        ignore_case: bool = False,
        encoding: str = "utf-8",
    ) -> Result[dict[str, Any], AppError]:
        return grep_local_path(
            self.root,
            path,
            pattern=pattern,
            glob=glob,
            ignore_case=ignore_case,
            encoding=encoding,
        )

    def write_file(
        self, path: str, *, content: str, encoding: str = "utf-8", overwrite: bool = False
    ) -> Result[dict[str, Any], AppError]:
        return write_local_file(self.root, path, content=content, encoding=encoding, overwrite=overwrite)

    def append_file(self, path: str, *, content: str, encoding: str = "utf-8") -> Result[dict[str, Any], AppError]:
        return append_local_file(self.root, path, content=content, encoding=encoding)

    def make_dir(self, path: str, *, parents: bool = False) -> Result[dict[str, Any], AppError]:
        return mkdir_local_path(self.root, path, parents=parents)

    def stat_path(self, path: str) -> Result[dict[str, Any], AppError]:
        return stat_local_path(self.root, path)
