from __future__ import annotations

"""落盘和读取 agent 编排 trace。"""

import json
from pathlib import Path

from ..core import Result
from ..core.serialization import to_plain_data
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error


def trace_path(config: WorkbenchConfig, task_id: str) -> Path:
    return config.reports_dir / f"agent-trace-{task_id}.json"


def load_trace_document(config: WorkbenchConfig, task_id: str) -> Result[dict[str, object], AppError]:
    path = trace_path(config, task_id)
    if not path.exists():
        return Result.ok(
            {
                "task_id": task_id,
                "plan": None,
                "resolutions": {},
                "assemblies": {},
            }
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(path)))
    except json.JSONDecodeError as exc:
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, str(exc), path=str(path)))
    if not isinstance(payload, dict):
        return Result.err(app_error(AppErrorCode.PARSE_ERROR, "Trace file must contain a JSON object", path=str(path)))
    return Result.ok(dict(payload))


def write_trace_document(config: WorkbenchConfig, task_id: str, document: dict[str, object]) -> Result[Path, AppError]:
    path = trace_path(config, task_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(to_plain_data(document), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.INTERNAL_ERROR, str(exc), path=str(path)))
    return Result.ok(path)


__all__ = ["load_trace_document", "trace_path", "write_trace_document"]
