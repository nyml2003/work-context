from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .core import Result
from .domain.errors import AppError, AppErrorCode, app_error
from .fs import ensure_dir
from .simple_toml import dump, load


DEFAULT_CONFIG: dict[str, Any] = {
    "paths": {
        "skills": "skills",
        "templates": "templates",
        "reports": "reports",
        "workspace_config": "workspace-config",
    },
    "files": {
        "workspace_registry": "workspace-config/workspaces.toml",
    },
    "workspace": {
        "managed_subdir": "repos",
        "default_remote_name": "origin",
        "github_remote_prefix": "",
    },
    "codex": {
        "install_root": "~/.codex/skills",
    },
    "tool": {
        "name": "workbench",
        "version": __version__,
    },
}


@dataclass
class WorkbenchConfig:
    root: Path
    data: dict[str, Any]
    skills_dir: Path
    templates_dir: Path
    reports_dir: Path
    workspace_config_dir: Path
    workspace_registry: Path
    managed_subdir: str
    managed_repos_dir: Path
    default_remote_name: str
    github_remote_prefix: str
    codex_install_root: Path


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged


def load_config(root: Path) -> Result[WorkbenchConfig, AppError]:
    config_path = root / "workbench.toml"
    data = dict(DEFAULT_CONFIG)
    if config_path.exists():
        loaded = load(config_path)
        if loaded.is_err:
            return Result.err(loaded.error)
        data = _merge_dicts(DEFAULT_CONFIG, loaded.value)
    paths = data["paths"]
    files = data["files"]
    workspace = data["workspace"]
    codex = data["codex"]
    return Result.ok(
        WorkbenchConfig(
        root=root,
        data=data,
        skills_dir=root / paths["skills"],
        templates_dir=root / paths["templates"],
        reports_dir=root / paths["reports"],
        workspace_config_dir=root / paths["workspace_config"],
        workspace_registry=root / files["workspace_registry"],
        managed_subdir=workspace["managed_subdir"],
        managed_repos_dir=root / workspace["managed_subdir"],
        default_remote_name=workspace["default_remote_name"],
        github_remote_prefix=workspace["github_remote_prefix"],
        codex_install_root=Path(codex["install_root"]).expanduser(),
        )
    )


def ensure_base_layout(config: WorkbenchConfig) -> Result[None, AppError]:
    try:
        for path in [
            config.skills_dir,
            config.templates_dir,
            config.reports_dir,
            config.workspace_config_dir,
            config.managed_repos_dir,
        ]:
            ensure_dir(path)
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), root=str(config.root)))
    return Result.ok(None)


def write_default_config(root: Path, *, overwrite: bool = False) -> Result[bool, AppError]:
    path = root / "workbench.toml"
    if path.exists() and not overwrite:
        return Result.ok(False)
    dumped = dump(path, DEFAULT_CONFIG)
    if dumped.is_err:
        return Result.err(dumped.error.with_context(root=str(root)))
    return Result.ok(True)
