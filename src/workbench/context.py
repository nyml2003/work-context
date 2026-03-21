from __future__ import annotations

from pathlib import Path
from typing import Any

from .application.context_service import ContextService
from .config import WorkbenchConfig
from .core import Result
from .domain.errors import AppError

__all__ = ["build_context_file", "build_context_payload"]


def context_service(config: WorkbenchConfig) -> ContextService:
    return ContextService(config)


def build_context_payload(
    config: WorkbenchConfig, skill_name: str, workspace_name: str | None = None
) -> Result[dict[str, Any], AppError]:
    return context_service(config).build_context_payload(skill_name, workspace_name)


def build_context_file(
    config: WorkbenchConfig,
    skill_name: str,
    *,
    workspace_name: str | None = None,
    output_path: Path | None = None,
    format_name: str = "md",
) -> Result[Path, AppError]:
    return context_service(config).build_context_file(
        skill_name,
        workspace_name=workspace_name,
        output_path=output_path,
        format_name=format_name,
    )
