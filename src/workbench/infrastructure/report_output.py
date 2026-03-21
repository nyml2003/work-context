from __future__ import annotations

"""报告序列化与文件输出工具。"""

import json
from datetime import datetime, timezone
from pathlib import Path

from ..core import Result
from ..core.serialization import to_plain_data
from ..domain.errors import AppError, AppErrorCode, app_error


def timestamp_slug() -> str:
    """生成 UTC 时间戳片段，用于报告文件名。"""

    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def to_json_text(payload: object) -> str:
    """输出适合 CLI 展示的 JSON 文本。"""

    return json.dumps(to_plain_data(payload), indent=2, ensure_ascii=False)


def write_markdown_report(path: Path, title: str, sections: list[tuple[str, str]]) -> Result[Path, AppError]:
    """把多个 section 写成 Markdown 报告。"""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# {title}", ""]
        for heading, body in sections:
            lines.extend([f"## {heading}", "", body.strip(), ""])
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(path)))
    return Result.ok(path)


__all__ = ["timestamp_slug", "to_json_text", "write_markdown_report"]
