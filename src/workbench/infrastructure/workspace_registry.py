from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.workspace import Workspace, workspace_from_record, workspace_to_record
from ..simple_toml import dump, load


class WorkspaceRegistry:
    def __init__(self, path: Path, *, root: Path, default_remote_name: str) -> None:
        self.path = path
        self.root = root
        self.default_remote_name = default_remote_name

    def _load_raw(self) -> Result[dict[str, Any], AppError]:
        if not self.path.exists():
            return Result.ok({"workspaces": {}})
        loaded = load(self.path)
        if loaded.is_err:
            return Result.err(loaded.error)
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

    def _store_raw(self, data: dict[str, Any]) -> Result[Path, AppError]:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, str(exc), path=str(self.path)))
        return dump(self.path, data).map_err(lambda error: error.with_context(path=str(self.path)))

    def load_workspaces(self) -> Result[list[Workspace], AppError]:
        loaded = self._load_raw()
        if loaded.is_err:
            return Result.err(loaded.error)
        data = loaded.value
        return Result.ok([
            workspace_from_record(name, payload, default_remote_name=self.default_remote_name)
            for name, payload in sorted(data.get("workspaces", {}).items())
        ])

    def save_workspace(self, workspace: Workspace) -> Result[Path, AppError]:
        loaded = self._load_raw()
        if loaded.is_err:
            return Result.err(loaded.error)
        data = loaded.value
        workspaces = data.setdefault("workspaces", {})
        workspaces[workspace.name] = workspace_to_record(workspace, self.root)
        stored = self._store_raw(data)
        if stored.is_err:
            return Result.err(stored.error)
        return Result.ok(self.path)
