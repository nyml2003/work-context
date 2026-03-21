from __future__ import annotations

"""通用文件系统辅助能力。"""

import json
from pathlib import Path

from ..core.serialization import JsonValue, to_plain_data

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

    return json.loads(path.read_text(encoding="utf-8"))


def short_path(path: Path, root: Path) -> str:
    """尽量返回相对根目录的短路径。"""

    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


__all__ = ["ensure_dir", "read_json", "short_path", "write_json", "write_text"]
