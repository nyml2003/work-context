from __future__ import annotations

"""通用文件系统辅助能力。"""

import json
import subprocess
import sys
from pathlib import Path

from ..core.serialization import JsonValue, to_plain_data


def normalized_path(path: Path) -> Path:
    """返回展开后的稳定绝对路径。"""

    return path.expanduser().resolve()

def ensure_dir(path: Path) -> Path:
    """确保目录存在。"""

    path.mkdir(parents=True, exist_ok=True)
    return path


def write_text(path: Path, content: str, *, overwrite: bool = False) -> bool:
    """写入 UTF-8 文本，按需创建父目录。"""

    if path.exists() and not overwrite:
        return False
    ensure_dir(path.parent)
    path.write_text(content, encoding="utf-8")
    return True


def write_json(path: Path, payload: object) -> None:
    """写入格式化 JSON。"""

    ensure_dir(path.parent)
    path.write_text(json.dumps(to_plain_data(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> JsonValue:
    """读取 UTF-8 JSON 文件。"""

    return json.loads(path.read_text(encoding="utf-8-sig"))


def short_path(path: Path, root: Path) -> str:
    """尽量返回相对根目录的短路径。"""

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def same_directory_link_target(link_path: Path, source: Path) -> bool:
    """判断现有目录链接是否已经指向目标目录。"""

    if not link_path.exists():
        return False
    try:
        return link_path.resolve() == normalized_path(source)
    except OSError:
        return False


def create_windows_junction(source: Path, destination: Path) -> None:
    """在 Windows 上回退到目录 junction，避免 symlink 特权要求。"""

    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise OSError(completed.stderr.strip() or completed.stdout.strip() or "mklink /J failed")


def ensure_directory_symlink(source: Path, destination: Path) -> str:
    """创建目录链接，已存在且同源时保持幂等。"""

    resolved_source = normalized_path(source)
    if not resolved_source.exists():
        raise FileNotFoundError(f"Path does not exist: {resolved_source}")
    if not resolved_source.is_dir():
        raise NotADirectoryError(f"Expected a directory path: {resolved_source}")
    destination = destination.expanduser()
    if destination.exists() or destination.is_symlink():
        if same_directory_link_target(destination, resolved_source):
            return "unchanged"
        raise FileExistsError(f"Destination already exists: {destination}")
    ensure_dir(destination.parent)
    try:
        destination.symlink_to(resolved_source, target_is_directory=True)
    except OSError as exc:
        if sys.platform != "win32":
            raise
        if getattr(exc, "winerror", None) != 1314:
            raise
        create_windows_junction(resolved_source, destination)
    return "linked"


__all__ = [
    "ensure_dir",
    "ensure_directory_symlink",
    "normalized_path",
    "read_json",
    "same_directory_link_target",
    "short_path",
    "write_json",
    "write_text",
]
