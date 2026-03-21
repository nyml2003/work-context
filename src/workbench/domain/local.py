from __future__ import annotations

"""本地文件能力的强类型返回模型。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocalPathRecord:
    """统一描述一个受边界约束的路径。"""

    path: str
    resolved_path: str


@dataclass(frozen=True, slots=True)
class LocalReadPayload(LocalPathRecord):
    """文件读取结果。"""

    encoding: str
    line_count: int
    start_line: int
    end_line: int
    content: str


@dataclass(frozen=True, slots=True)
class LocalListEntry(LocalPathRecord):
    """目录遍历结果中的单项。"""

    type: str
    size: int | None = None


@dataclass(frozen=True, slots=True)
class LocalListPayload:
    """路径列表结果。"""

    target: LocalPathRecord
    recursive: bool
    kind: str
    pattern: str | None
    count: int
    entries: list[LocalListEntry]


@dataclass(frozen=True, slots=True)
class LocalGrepMatch:
    """grep 命中的单行记录。"""

    path: str
    line_number: int
    line: str


@dataclass(frozen=True, slots=True)
class LocalSkippedFile:
    """grep 过程中被跳过的文件。"""

    path: str
    reason: str


@dataclass(frozen=True, slots=True)
class LocalGrepPayload:
    """grep 执行结果。"""

    target: LocalPathRecord
    pattern: str
    glob: str | None
    ignore_case: bool
    encoding: str
    files_scanned: int
    match_count: int
    matches: list[LocalGrepMatch]
    skipped_files: list[LocalSkippedFile]


@dataclass(frozen=True, slots=True)
class LocalWritePayload(LocalPathRecord):
    """文件写入结果。"""

    encoding: str
    created: bool
    overwrote: bool
    size: int


@dataclass(frozen=True, slots=True)
class LocalAppendPayload(LocalPathRecord):
    """文件追加结果。"""

    encoding: str
    created: bool
    appended_characters: int
    size: int


@dataclass(frozen=True, slots=True)
class LocalMkdirPayload(LocalPathRecord):
    """目录创建结果。"""

    parents: bool
    created: bool


@dataclass(frozen=True, slots=True)
class LocalStatPayload(LocalPathRecord):
    """路径状态结果。"""

    type: str
    size: int
    is_symlink: bool
    modified_at: str
    created_at: str


__all__ = [
    "LocalAppendPayload",
    "LocalGrepMatch",
    "LocalGrepPayload",
    "LocalListEntry",
    "LocalListPayload",
    "LocalMkdirPayload",
    "LocalPathRecord",
    "LocalReadPayload",
    "LocalSkippedFile",
    "LocalStatPayload",
    "LocalWritePayload",
]
