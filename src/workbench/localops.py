from __future__ import annotations

import fnmatch
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import Result
from .domain.errors import AppError, AppErrorCode, app_error


def _normalized_root(root: Path) -> Path:
    return root.resolve()


def _path_label(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _path_record(path: Path, root: Path) -> dict[str, str]:
    return {
        "path": _path_label(path, root),
        "resolved_path": str(path),
    }


def resolve_local_path(root: Path, raw_path: str, *, must_exist: bool = False) -> Path:
    boundary_root = _normalized_root(root)
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


def _ensure_text_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"Expected a file path: {path}")


def _validate_line_range(start_line: int | None, end_line: int | None) -> None:
    if start_line is not None and start_line < 1:
        raise ValueError("--start-line must be >= 1")
    if end_line is not None and end_line < 1:
        raise ValueError("--end-line must be >= 1")
    if start_line is not None and end_line is not None and end_line < start_line:
        raise ValueError("--end-line must be >= --start-line")


def _sorted_paths(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=lambda item: item.as_posix().lower())


def _matches_glob(path: Path, match_root: Path, pattern: str) -> bool:
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
) -> Result[dict[str, Any], AppError]:
    try:
        _validate_line_range(start_line, end_line)
        path = resolve_local_path(root, raw_path, must_exist=True)
        _ensure_text_file(path)
        text = path.read_text(encoding=encoding)
        lines = text.splitlines(keepends=True)
        start_index = 0 if start_line is None else start_line - 1
        end_index = len(lines) if end_line is None else min(end_line, len(lines))
        content = "".join(lines[start_index:end_index])
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except FileExistsError as exc:
        return Result.err(app_error(AppErrorCode.ALREADY_EXISTS, str(exc), path=raw_path))
    except FileNotFoundError as exc:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, str(exc), path=raw_path))
    except IsADirectoryError as exc:
        return Result.err(app_error(AppErrorCode.NOT_A_FILE, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            **_path_record(path, root),
            "encoding": encoding,
            "line_count": len(lines),
            "start_line": start_line or (1 if lines else 0),
            "end_line": end_line if end_line is not None else len(lines),
            "content": content,
        }
    )


def list_local_path(
    root: Path,
    raw_path: str,
    *,
    recursive: bool = False,
    kind: str = "all",
    pattern: str | None = None,
) -> Result[dict[str, Any], AppError]:
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
        entries: list[dict[str, Any]] = []
        for item in _sorted_paths(iterated):
            entry_type = "dir" if item.is_dir() else "file" if item.is_file() else "other"
            if kind != "all" and entry_type != kind:
                continue
            if pattern and not _matches_glob(item, match_root, pattern):
                continue
            entry: dict[str, Any] = {
                **_path_record(item, root),
                "type": entry_type,
            }
            if item.is_file():
                entry["size"] = item.stat().st_size
            entries.append(entry)
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except FileNotFoundError as exc:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            "target": _path_record(target, root),
            "recursive": recursive,
            "kind": kind,
            "pattern": pattern,
            "count": len(entries),
            "entries": entries,
        }
    )


def grep_local_path(
    root: Path,
    raw_path: str,
    *,
    pattern: str,
    glob: str | None = None,
    ignore_case: bool = False,
    encoding: str = "utf-8",
) -> Result[dict[str, Any], AppError]:
    try:
        target = resolve_local_path(root, raw_path, must_exist=True)
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
        if target.is_dir():
            files = _sorted_paths([path for path in target.rglob("*") if path.is_file()])
            match_root = target
        else:
            _ensure_text_file(target)
            files = [target]
            match_root = target.parent
        matches: list[dict[str, Any]] = []
        skipped_files: list[dict[str, str]] = []
        files_scanned = 0
        for file_path in files:
            if glob and not _matches_glob(file_path, match_root, glob):
                continue
            files_scanned += 1
            try:
                lines = file_path.read_text(encoding=encoding).splitlines()
            except UnicodeDecodeError as exc:
                skipped_files.append({"path": _path_label(file_path, root), "reason": str(exc)})
                continue
            for line_number, line in enumerate(lines, start=1):
                if regex.search(line):
                    matches.append(
                        {
                            "path": _path_label(file_path, root),
                            "line_number": line_number,
                            "line": line,
                        }
                    )
    except re.error as exc:
        return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, str(exc), pattern=pattern))
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except FileNotFoundError as exc:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, str(exc), path=raw_path))
    except IsADirectoryError as exc:
        return Result.err(app_error(AppErrorCode.NOT_A_FILE, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            "target": _path_record(target, root),
            "pattern": pattern,
            "glob": glob,
            "ignore_case": ignore_case,
            "encoding": encoding,
            "files_scanned": files_scanned,
            "match_count": len(matches),
            "matches": matches,
            "skipped_files": skipped_files,
        }
    )


def write_local_file(
    root: Path,
    raw_path: str,
    *,
    content: str,
    encoding: str = "utf-8",
    overwrite: bool = False,
) -> Result[dict[str, Any], AppError]:
    try:
        path = resolve_local_path(root, raw_path, must_exist=False)
        existed = path.exists()
        if existed and not path.is_file():
            raise IsADirectoryError(f"Expected a file path: {path}")
        if existed and not overwrite:
            raise FileExistsError(f"Path already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except FileExistsError as exc:
        return Result.err(app_error(AppErrorCode.ALREADY_EXISTS, str(exc), path=raw_path))
    except IsADirectoryError as exc:
        return Result.err(app_error(AppErrorCode.NOT_A_FILE, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            **_path_record(path, root),
            "encoding": encoding,
            "created": not existed,
            "overwrote": existed,
            "size": path.stat().st_size,
        }
    )


def append_local_file(
    root: Path,
    raw_path: str,
    *,
    content: str,
    encoding: str = "utf-8",
) -> Result[dict[str, Any], AppError]:
    try:
        path = resolve_local_path(root, raw_path, must_exist=False)
        existed = path.exists()
        if existed and not path.is_file():
            raise IsADirectoryError(f"Expected a file path: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding=encoding) as handle:
            handle.write(content)
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except IsADirectoryError as exc:
        return Result.err(app_error(AppErrorCode.NOT_A_FILE, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            **_path_record(path, root),
            "encoding": encoding,
            "created": not existed,
            "appended_characters": len(content),
            "size": path.stat().st_size,
        }
    )


def mkdir_local_path(root: Path, raw_path: str, *, parents: bool = False) -> Result[dict[str, Any], AppError]:
    try:
        path = resolve_local_path(root, raw_path, must_exist=False)
        existed = path.exists()
        if existed and not path.is_dir():
            raise FileExistsError(f"Path already exists and is not a directory: {path}")
        path.mkdir(parents=parents, exist_ok=True)
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except FileExistsError as exc:
        return Result.err(app_error(AppErrorCode.ALREADY_EXISTS, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            **_path_record(path, root),
            "parents": parents,
            "created": not existed,
        }
    )


def stat_local_path(root: Path, raw_path: str) -> Result[dict[str, Any], AppError]:
    try:
        path = resolve_local_path(root, raw_path, must_exist=True)
        stat_result = path.stat()
        entry_type = "dir" if path.is_dir() else "file" if path.is_file() else "other"
    except ValueError as exc:
        code = AppErrorCode.PATH_OUT_OF_BOUNDARY if "boundary" in str(exc) else AppErrorCode.INVALID_ARGUMENT
        return Result.err(app_error(code, str(exc), path=raw_path))
    except FileNotFoundError as exc:
        return Result.err(app_error(AppErrorCode.NOT_FOUND, str(exc), path=raw_path))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=raw_path))
    return Result.ok(
        {
            **_path_record(path, root),
            "type": entry_type,
            "size": stat_result.st_size,
            "is_symlink": path.is_symlink(),
            "modified_at": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat(),
            "created_at": datetime.fromtimestamp(stat_result.st_ctime, tz=timezone.utc).isoformat(),
        }
    )
