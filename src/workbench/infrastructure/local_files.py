from __future__ import annotations

"""受根目录边界约束的本地文件基础设施能力。"""

import fnmatch
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.local import (
    LocalAppendPayload,
    LocalGrepMatch,
    LocalGrepPayload,
    LocalListEntry,
    LocalListPayload,
    LocalMkdirPayload,
    LocalPathRecord,
    LocalReadPayload,
    LocalSkippedFile,
    LocalStatPayload,
    LocalWritePayload,
)

PayloadT = TypeVar("PayloadT")


def normalized_root(root: Path) -> Path:
    """标准化边界根目录，统一后续相对路径判断。"""

    return root.resolve()


def path_label(path: Path, root: Path) -> str:
    """优先返回相对边界根目录的展示路径。"""

    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def path_record(path: Path, root: Path) -> LocalPathRecord:
    """为 CLI 输出构造统一的路径字段。"""

    return LocalPathRecord(
        path=path_label(path, root),
        resolved_path=str(path),
    )


def result_from_path_exception(raw_path: str, exc: Exception) -> Result[PayloadT, AppError]:
    """把常见路径异常收敛为统一的 AppError。"""

    if isinstance(exc, ValueError):
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    if isinstance(exc, FileExistsError):
        return Result.err(app_error(AppErrorCode.ALREADY_EXISTS, str(exc), path=raw_path))
    if isinstance(exc, FileNotFoundError):
        return Result.err(app_error(AppErrorCode.NOT_FOUND, str(exc), path=raw_path))
    if isinstance(exc, IsADirectoryError):
        return Result.err(app_error(AppErrorCode.NOT_A_FILE, str(exc), path=raw_path))
    if isinstance(exc, OSError):
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    raise exc


def resolve_local_path(root: Path, raw_path: str, *, must_exist: bool = False) -> Path:
    """将任意输入路径解析到边界内。

    这里统一使用 resolve 后的绝对路径做 boundary 判断，避免 `..`、符号链接等绕过。
    """

    boundary_root = normalized_root(root)
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = boundary_root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(boundary_root)
    except ValueError:
        raise ValueError(f"Path escapes the current working directory boundary: {resolved} (root: {boundary_root})")
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved}")
    return resolved


def ensure_text_file(path: Path) -> None:
    """确保目标存在且是文件。"""

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Expected a file path: {path}")


def validate_line_range(start_line: int | None, end_line: int | None) -> None:
    """校验读取文件时的行范围参数。"""

    if start_line is not None and start_line < 1:
        raise ValueError("--start-line must be >= 1")
    if end_line is not None and end_line < 1:
        raise ValueError("--end-line must be >= 1")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ValueError("--end-line must be >= --start-line")


def sorted_paths(paths: list[Path]) -> list[Path]:
    """按大小写无关的稳定顺序排序路径。"""

    return sorted(paths, key=lambda item: item.as_posix().lower())


def matches_glob(path: Path, match_root: Path, pattern: str) -> bool:
    """同时支持文件名和相对路径两种 glob 匹配方式。"""

    relative = path.relative_to(match_root) if path != match_root else Path(path.name)
    candidates = {path.name, relative.as_posix()}
    return any(fnmatch.fnmatchcase(candidate, pattern) for candidate in candidates)


def read_local_file(
    root: Path,
    raw_path: str,
    *,
    start_line: int | None = None,
    end_line: int | None = None,
    encoding: str = "utf-8",
) -> Result[LocalReadPayload, AppError]:
    """读取边界内的文本文件。"""

    try:
        validate_line_range(start_line, end_line)
        path = resolve_local_path(root, raw_path, must_exist=True)
        ensure_text_file(path)
        text = path.read_text(encoding=encoding)
        lines = text.splitlines(keepends=True)
        start_index = 0 if start_line is None else start_line - 1
        end_index = len(lines) if end_line is None else min(end_line, len(lines))
        content = "".join(lines[start_index:end_index])
    except (ValueError, FileExistsError, FileNotFoundError, IsADirectoryError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    record = path_record(path, root)
    return Result.ok(
        LocalReadPayload(
            path=record.path,
            resolved_path=record.resolved_path,
            encoding=encoding,
            line_count=len(lines),
            start_line=start_line or (1 if lines else 0),
            end_line=end_line if end_line is not None else len(lines),
            content=content,
        )
    )


def list_local_path(
    root: Path,
    raw_path: str,
    *,
    recursive: bool = False,
    kind: str = "all",
    pattern: str | None = None,
) -> Result[LocalListPayload, AppError]:
    """列出边界内路径内容。"""

    try:
        if kind not in {"file", "dir", "all"}:
            raise ValueError("kind must be one of: file, dir, all")
        target = resolve_local_path(root, raw_path, must_exist=True)
        if target.is_dir():
            iterated = list(target.rglob("*") if recursive else target.iterdir())
            match_root = target
        else:
            iterated = [target]
            match_root = target.parent
        entries: list[LocalListEntry] = []
        for item in sorted_paths(iterated):
            entry_type = "dir" if item.is_dir() else "file" if item.is_file() else "other"
            if kind != "all" and entry_type != kind:
                continue
            if pattern and not matches_glob(item, match_root, pattern):
                continue
            record = path_record(item, root)
            entries.append(
                LocalListEntry(
                    path=record.path,
                    resolved_path=record.resolved_path,
                    type=entry_type,
                    size=item.stat().st_size if item.is_file() else None,
                )
            )
    except (ValueError, FileNotFoundError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    return Result.ok(
        LocalListPayload(
            target=path_record(target, root),
            recursive=recursive,
            kind=kind,
            pattern=pattern,
            count=len(entries),
            entries=entries,
        )
    )


def grep_local_path(
    root: Path,
    raw_path: str,
    *,
    pattern: str,
    glob: str | None = None,
    ignore_case: bool = False,
    encoding: str = "utf-8",
) -> Result[LocalGrepPayload, AppError]:
    """在边界内对文本文件执行正则搜索。"""

    try:
        target = resolve_local_path(root, raw_path, must_exist=True)
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
        if target.is_dir():
            files = sorted_paths([path for path in target.rglob("*") if path.is_file()])
            match_root = target
        else:
            ensure_text_file(target)
            files = [target]
            match_root = target.parent
        matches: list[LocalGrepMatch] = []
        skipped_files: list[LocalSkippedFile] = []
        files_scanned = 0
        for file_path in files:
            if glob and not matches_glob(file_path, match_root, glob):
                continue
            files_scanned += 1
            try:
                lines = file_path.read_text(encoding=encoding).splitlines()
            except UnicodeDecodeError as exc:
                skipped_files.append(LocalSkippedFile(path=path_label(file_path, root), reason=str(exc)))
                continue
            for line_number, line in enumerate(lines, start=1):
                if regex.search(line):
                    matches.append(
                        LocalGrepMatch(
                            path=path_label(file_path, root),
                            line_number=line_number,
                            line=line,
                        )
                    )
    except re.error as exc:
        return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, str(exc), pattern=pattern))
    except (ValueError, FileNotFoundError, IsADirectoryError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    return Result.ok(
        LocalGrepPayload(
            target=path_record(target, root),
            pattern=pattern,
            glob=glob,
            ignore_case=ignore_case,
            encoding=encoding,
            files_scanned=files_scanned,
            match_count=len(matches),
            matches=matches,
            skipped_files=skipped_files,
        )
    )


def write_local_file(
    root: Path,
    raw_path: str,
    *,
    content: str,
    encoding: str = "utf-8",
    overwrite: bool = False,
) -> Result[LocalWritePayload, AppError]:
    """写入文本文件，默认拒绝覆盖已有文件。"""

    try:
        path = resolve_local_path(root, raw_path, must_exist=False)
        existed = path.exists()
        if existed and not path.is_file():
            raise IsADirectoryError(f"Expected a file path: {path}")
        if existed and not overwrite:
            raise FileExistsError(f"Path already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    except (ValueError, FileExistsError, IsADirectoryError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    record = path_record(path, root)
    return Result.ok(
        LocalWritePayload(
            path=record.path,
            resolved_path=record.resolved_path,
            encoding=encoding,
            created=not existed,
            overwrote=existed,
            size=path.stat().st_size,
        )
    )


def append_local_file(
    root: Path,
    raw_path: str,
    *,
    content: str,
    encoding: str = "utf-8",
) -> Result[LocalAppendPayload, AppError]:
    """向文本文件追加内容。"""

    try:
        path = resolve_local_path(root, raw_path, must_exist=False)
        existed = path.exists()
        if existed and not path.is_file():
            raise IsADirectoryError(f"Expected a file path: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding=encoding) as handle:
            handle.write(content)
    except (ValueError, IsADirectoryError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    record = path_record(path, root)
    return Result.ok(
        LocalAppendPayload(
            path=record.path,
            resolved_path=record.resolved_path,
            encoding=encoding,
            created=not existed,
            appended_characters=len(content),
            size=path.stat().st_size,
        )
    )


def mkdir_local_path(root: Path, raw_path: str, *, parents: bool = False) -> Result[LocalMkdirPayload, AppError]:
    """在边界内创建目录。"""

    try:
        path = resolve_local_path(root, raw_path, must_exist=False)
        existed = path.exists()
        if existed and not path.is_dir():
            raise FileExistsError(f"Path already exists and is not a directory: {path}")
        path.mkdir(parents=parents, exist_ok=True)
    except (ValueError, FileExistsError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    record = path_record(path, root)
    return Result.ok(
        LocalMkdirPayload(
            path=record.path,
            resolved_path=record.resolved_path,
            parents=parents,
            created=not existed,
        )
    )


def stat_local_path(root: Path, raw_path: str) -> Result[LocalStatPayload, AppError]:
    """读取路径元数据。"""

    try:
        path = resolve_local_path(root, raw_path, must_exist=True)
        stat_result = path.stat()
        entry_type = "dir" if path.is_dir() else "file" if path.is_file() else "other"
    except (ValueError, FileNotFoundError, OSError) as exc:
        return result_from_path_exception(raw_path, exc)
    record = path_record(path, root)
    return Result.ok(
        LocalStatPayload(
            path=record.path,
            resolved_path=record.resolved_path,
            type=entry_type,
            size=stat_result.st_size,
            is_symlink=path.is_symlink(),
            modified_at=datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat(),
            created_at=datetime.fromtimestamp(stat_result.st_ctime, tz=timezone.utc).isoformat(),
        )
    )


__all__ = [
    "append_local_file",
    "ensure_text_file",
    "grep_local_path",
    "list_local_path",
    "matches_glob",
    "mkdir_local_path",
    "normalized_root",
    "path_label",
    "path_record",
    "read_local_file",
    "resolve_local_path",
    "result_from_path_exception",
    "sorted_paths",
    "stat_local_path",
    "validate_line_range",
    "write_local_file",
]
