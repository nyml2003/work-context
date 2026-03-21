from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.workspace import Workspace, WorkspaceRecord, workspace_from_record, workspace_to_record
from .filesystem import ensure_dir

ROOT_KEYS = {"workspaces"}
WORKSPACE_RECORD_KEYS = {"path", "default_branch", "check_commands", "remote_name", "repo_slug"}
BARE_TOML_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


class WorkspaceRegistry:
    """workspace 注册表的 TOML 持久化适配器。"""

    def __init__(self, path: Path, *, root: Path, default_remote_name: str) -> None:
        self.path = path
        self.root = root
        self.default_remote_name = default_remote_name

    def ensure_mapping(self, value: object, *, label: str) -> Result[Mapping[str, object], AppError]:
        if not isinstance(value, Mapping):
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, f"{label} must be a TOML table", path=str(self.path)))
        return Result.ok(value)

    def reject_unknown_keys(self, payload: Mapping[str, object], *, label: str, allowed: set[str]) -> Result[None, AppError]:
        unknown = sorted(key for key in payload if key not in allowed)
        if unknown:
            return Result.err(
                app_error(
                    AppErrorCode.REGISTRY_INVALID,
                    f"{label} contains unknown keys: {', '.join(unknown)}",
                    path=str(self.path),
                )
            )
        return Result.ok(None)

    def read_optional_string(
        self,
        payload: Mapping[str, object],
        *,
        key: str,
        default: str,
        label: str,
    ) -> Result[str, AppError]:
        if key not in payload:
            return Result.ok(default)
        value = payload[key]
        if not isinstance(value, str):
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, f"{label}.{key} must be a string", path=str(self.path)))
        return Result.ok(value)

    def read_check_commands(self, payload: Mapping[str, object], *, label: str) -> Result[list[str], AppError]:
        value = payload.get("check_commands")
        if value is None:
            return Result.ok([])
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return Result.err(
                app_error(
                    AppErrorCode.REGISTRY_INVALID,
                    f"{label}.check_commands must be an array of strings",
                    path=str(self.path),
                )
            )
        return Result.ok(list(value))

    def parse_workspace_record(self, name: str, payload: object) -> Result[WorkspaceRecord, AppError]:
        table = self.ensure_mapping(payload, label=f"workspaces.{name}")
        if table.is_err:
            return Result.err(table.error)
        unknown = self.reject_unknown_keys(table.value, label=f"workspaces.{name}", allowed=WORKSPACE_RECORD_KEYS)
        if unknown.is_err:
            return Result.err(unknown.error)
        path = self.read_optional_string(table.value, key="path", default="", label=f"workspaces.{name}")
        if path.is_err:
            return Result.err(path.error)
        if not path.value:
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, f"workspaces.{name}.path must not be empty", path=str(self.path)))
        default_branch = self.read_optional_string(
            table.value,
            key="default_branch",
            default="main",
            label=f"workspaces.{name}",
        )
        if default_branch.is_err:
            return Result.err(default_branch.error)
        remote_name = self.read_optional_string(
            table.value,
            key="remote_name",
            default=self.default_remote_name,
            label=f"workspaces.{name}",
        )
        if remote_name.is_err:
            return Result.err(remote_name.error)
        repo_slug = self.read_optional_string(
            table.value,
            key="repo_slug",
            default=name,
            label=f"workspaces.{name}",
        )
        if repo_slug.is_err:
            return Result.err(repo_slug.error)
        check_commands = self.read_check_commands(table.value, label=f"workspaces.{name}")
        if check_commands.is_err:
            return Result.err(check_commands.error)
        return Result.ok(
            WorkspaceRecord(
                name=name,
                path=path.value,
                default_branch=default_branch.value,
                check_commands=check_commands.value,
                remote_name=remote_name.value,
                repo_slug=repo_slug.value,
            )
        )

    def load_records(self) -> Result[list[WorkspaceRecord], AppError]:
        if not self.path.exists():
            return Result.ok([])
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(self.path)))
        try:
            document = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, str(exc), path=str(self.path)))
        root_unknown = self.reject_unknown_keys(document, label="workspace registry", allowed=ROOT_KEYS)
        if root_unknown.is_err:
            return Result.err(root_unknown.error)
        workspaces = self.ensure_mapping(document.get("workspaces", {}), label="workspaces")
        if workspaces.is_err:
            return Result.err(workspaces.error)
        records: list[WorkspaceRecord] = []
        for name in sorted(workspaces.value):
            record = self.parse_workspace_record(name, workspaces.value[name])
            if record.is_err:
                return Result.err(record.error)
            records.append(record.value)
        return Result.ok(records)

    def quote_toml_string(self, value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    def quote_toml_array(self, values: list[str]) -> str:
        return "[" + ", ".join(self.quote_toml_string(value) for value in values) + "]"

    def table_key(self, name: str) -> str:
        return name if BARE_TOML_KEY.fullmatch(name) else self.quote_toml_string(name)

    def dump_records(self, records: list[WorkspaceRecord]) -> str:
        lines = ["[workspaces]"]
        for record in sorted(records, key=lambda item: item.name):
            lines.extend(
                [
                    "",
                    f"[workspaces.{self.table_key(record.name)}]",
                    f"path = {self.quote_toml_string(record.path)}",
                    f"default_branch = {self.quote_toml_string(record.default_branch)}",
                    f"check_commands = {self.quote_toml_array(record.check_commands)}",
                    f"remote_name = {self.quote_toml_string(record.remote_name)}",
                    f"repo_slug = {self.quote_toml_string(record.repo_slug)}",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def store_records(self, records: list[WorkspaceRecord]) -> Result[Path, AppError]:
        try:
            ensure_dir(self.path.parent)
            self.path.write_text(self.dump_records(records), encoding="utf-8")
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.REGISTRY_INVALID, str(exc), path=str(self.path)))
        return Result.ok(self.path)

    def load_workspaces(self) -> Result[list[Workspace], AppError]:
        loaded = self.load_records()
        if loaded.is_err:
            return Result.err(loaded.error)
        return Result.ok(
            [workspace_from_record(record, default_remote_name=self.default_remote_name) for record in loaded.value]
        )

    def save_workspace(self, workspace: Workspace) -> Result[Path, AppError]:
        loaded = self.load_records()
        if loaded.is_err:
            return Result.err(loaded.error)
        records = [record for record in loaded.value if record.name != workspace.name]
        records.append(workspace_to_record(workspace, self.root))
        stored = self.store_records(records)
        if stored.is_err:
            return Result.err(stored.error)
        return Result.ok(self.path)
