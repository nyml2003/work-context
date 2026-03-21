from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core import Result
from ..core.toml import dumps as dump_toml
from ..core.toml import loads as load_toml
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.workspace import Workspace, workspace_from_record, workspace_to_record
from .filesystem import ensure_dir


class WorkspaceRegistry:
    def __init__(self, path: Path, *, root: Path, default_remote_name: str) -> None:
        self.path = path
        self.root = root
        self.default_remote_name = default_remote_name

    def load_raw(self) -> Result[dict[str, Any], AppError]:
        if not self.path.exists():
            return Result.ok({"workspaces": {}})
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(self.path)))
        loaded = load_toml(raw)
        if loaded.is_err:
            return Result.err(loaded.error.with_context(path=str(self.path)))
        data = loaded.value
        workspaces = data.get("workspaces", {})
        if not isinstance(workspaces, dict):
            return Result.err(
                app_error(
                    AppErrorCode.REGISTRY_INVALID,
                    "Workspace registry must contain a [workspaces] table",
                    path=str(self.path),
                )
            )
        return Result.ok(data)

    def store_raw(self, data: dict[str, Any]) -> Result[Path, AppError]:
        try:
            ensure_dir(self.path.parent)
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, str(exc), path=str(self.path)))
        dumped = dump_toml(data)
        if dumped.is_err:
            return Result.err(dumped.error.with_context(path=str(self.path)))
        try:
            self.path.write_text(dumped.value, encoding="utf-8")
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, str(exc), path=str(self.path)))
        return Result.ok(self.path)

    def load_workspaces(self) -> Result[list[Workspace], AppError]:
        loaded = self.load_raw()
        if loaded.is_err:
            return Result.err(loaded.error)
        data = loaded.value
        return Result.ok([
            workspace_from_record(name, payload, default_remote_name=self.default_remote_name)
            for name, payload in sorted(data.get("workspaces", {}).items())
        ])

    def save_workspace(self, workspace: Workspace) -> Result[Path, AppError]:
        loaded = self.load_raw()
        if loaded.is_err:
            return Result.err(loaded.error)
        data = loaded.value
        workspaces = data.setdefault("workspaces", {})
        workspaces[workspace.name] = workspace_to_record(workspace, self.root)
        stored = self.store_raw(data)
        if stored.is_err:
            return Result.err(stored.error)
        return Result.ok(self.path)
