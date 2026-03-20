from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import WorkbenchConfig
from .fs import short_path
from .simple_toml import dump, load


DANGEROUS_TOKENS = {
    "add",
    "am",
    "apply",
    "checkout",
    "clean",
    "clone",
    "commit",
    "fetch",
    "merge",
    "mv",
    "pull",
    "push",
    "rebase",
    "reset",
    "restore",
    "rm",
    "switch",
}


@dataclass
class WorkspaceEntry:
    name: str
    path: str
    default_branch: str
    check_commands: list[str]

    def resolved_path(self, root: Path) -> Path:
        raw = Path(self.path)
        return raw if raw.is_absolute() else (root / raw).resolve()


def _load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"workspaces": {}}
    data = load(path)
    workspaces = data.get("workspaces", {})
    if not isinstance(workspaces, dict):
        raise ValueError("Workspace registry must contain a [workspaces] table")
    return data


def load_workspaces(config: WorkbenchConfig) -> list[WorkspaceEntry]:
    data = _load_registry(config.workspace_registry)
    entries: list[WorkspaceEntry] = []
    for name, payload in sorted(data.get("workspaces", {}).items()):
        entries.append(
            WorkspaceEntry(
                name=name,
                path=payload["path"],
                default_branch=payload.get("default_branch", "main"),
                check_commands=list(payload.get("check_commands", [])),
            )
        )
    return entries


def _store_registry(config: WorkbenchConfig, data: dict[str, Any]) -> None:
    config.workspace_registry.parent.mkdir(parents=True, exist_ok=True)
    dump(config.workspace_registry, data)


def add_workspace(
    config: WorkbenchConfig,
    name: str,
    path: str,
    *,
    default_branch: str = "main",
    check_commands: list[str] | None = None,
) -> Path:
    data = _load_registry(config.workspace_registry)
    workspaces = data.setdefault("workspaces", {})
    target_path = Path(path)
    if target_path.is_absolute():
        stored_path = str(target_path)
    else:
        stored_path = str(Path(path).as_posix())
    workspaces[name] = {
        "path": stored_path,
        "default_branch": default_branch,
        "check_commands": check_commands or ["git status --short", "git branch --show-current"],
    }
    _store_registry(config, data)
    return config.workspace_registry


def _is_safe_command(command: str) -> tuple[bool, str]:
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError as exc:
        return False, f"Invalid command syntax: {exc}"
    lowered = [token.lower() for token in tokens]
    for token in lowered:
        if token in DANGEROUS_TOKENS:
            return False, f"Command contains blocked token '{token}'"
    return True, ""


def check_workspaces(config: WorkbenchConfig, name: str | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for entry in load_workspaces(config):
        if name is not None and entry.name != name:
            continue
        target = entry.resolved_path(config.root)
        if not target.exists():
            results.append({"workspace": entry.name, "status": "missing", "path": str(target)})
            continue
        command_results = []
        for command in entry.check_commands:
            safe, reason = _is_safe_command(command)
            if not safe:
                command_results.append({"command": command, "status": "blocked", "reason": reason})
                continue
            completed = subprocess.run(
                shlex.split(command, posix=False),
                cwd=target,
                capture_output=True,
                text=True,
                check=False,
            )
            command_results.append(
                {
                    "command": command,
                    "status": "ok" if completed.returncode == 0 else "failed",
                    "returncode": completed.returncode,
                    "stdout": completed.stdout.strip(),
                    "stderr": completed.stderr.strip(),
                }
            )
        results.append(
            {
                "workspace": entry.name,
                "path": short_path(target, config.root),
                "default_branch": entry.default_branch,
                "checks": command_results,
            }
        )
    return {"workspace_count": len(results), "results": results}

