from __future__ import annotations

"""面向 CLI 的本地文件操作应用层。"""

from pathlib import Path
from typing import Any

from ..core import Result
from ..domain.errors import AppError
from ..infrastructure.local_files import (
    append_local_file,
    grep_local_path,
    list_local_path,
    mkdir_local_path,
    read_local_file,
    stat_local_path,
    write_local_file,
)


class LocalService:
    """对外暴露受边界约束的本地文件能力。"""

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
        """读取文本文件，可选按行截取。"""

        return read_local_file(self.root, path, start_line=start_line, end_line=end_line, encoding=encoding)

    def list_path(
        self,
        path: str,
        *,
        recursive: bool = False,
        kind: str = "all",
        pattern: str | None = None,
    ) -> Result[dict[str, Any], AppError]:
        """列出边界内路径内容。"""

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
        """在边界内执行文本 grep。"""

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
        """写入文本文件。"""

        return write_local_file(self.root, path, content=content, encoding=encoding, overwrite=overwrite)

    def append_file(self, path: str, *, content: str, encoding: str = "utf-8") -> Result[dict[str, Any], AppError]:
        """向文本文件追加内容。"""

        return append_local_file(self.root, path, content=content, encoding=encoding)

    def make_dir(self, path: str, *, parents: bool = False) -> Result[dict[str, Any], AppError]:
        """创建目录。"""

        return mkdir_local_path(self.root, path, parents=parents)

    def stat_path(self, path: str) -> Result[dict[str, Any], AppError]:
        """读取路径元数据。"""

        return stat_local_path(self.root, path)
