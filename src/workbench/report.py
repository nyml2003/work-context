from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def to_json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def write_markdown_report(path: Path, title: str, sections: list[tuple[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    for heading, body in sections:
        lines.extend([f"## {heading}", "", body.strip(), ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

