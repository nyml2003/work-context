from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
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


def load_config(root: Path) -> WorkbenchConfig:
    config_path = root / "workbench.toml"
    data = dict(DEFAULT_CONFIG)
    if config_path.exists():
        data = _merge_dicts(DEFAULT_CONFIG, load(config_path))
    paths = data["paths"]
    files = data["files"]
    codex = data["codex"]
    return WorkbenchConfig(
        root=root,
        data=data,
        skills_dir=root / paths["skills"],
        templates_dir=root / paths["templates"],
        reports_dir=root / paths["reports"],
        workspace_config_dir=root / paths["workspace_config"],
        workspace_registry=root / files["workspace_registry"],
        codex_install_root=Path(codex["install_root"]).expanduser(),
    )


def ensure_base_layout(config: WorkbenchConfig) -> None:
    for path in [
        config.skills_dir,
        config.templates_dir,
        config.reports_dir,
        config.workspace_config_dir,
    ]:
        ensure_dir(path)


def write_default_config(root: Path, *, overwrite: bool = False) -> bool:
    path = root / "workbench.toml"
    if path.exists() and not overwrite:
        return False
    dump(path, DEFAULT_CONFIG)
    return True
