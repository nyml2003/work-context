from __future__ import annotations

"""配置文件加载与仓库基础布局管理。"""

from copy import deepcopy
from pathlib import Path
from typing import Any

from .. import __version__
from ..core import Result
from ..core.toml import dumps as dump_toml
from ..core.toml import loads as load_toml
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error
from .filesystem import ensure_dir

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


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并配置字典，保留 override 的显式值。"""

    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = merge_dicts(existing, value)
        else:
            merged[key] = value
    return merged


def build_workbench_config(root: Path, data: dict[str, Any]) -> WorkbenchConfig:
    """把原始配置字典投影为领域配置对象。"""

    paths = data["paths"]
    files = data["files"]
    workspace = data["workspace"]
    codex = data["codex"]
    return WorkbenchConfig(
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


def load_config(root: Path) -> Result[WorkbenchConfig, AppError]:
    """读取 `workbench.toml` 并返回运行时配置对象。"""

    config_path = root / "workbench.toml"
    data = deepcopy(DEFAULT_CONFIG)
    if config_path.exists():
        try:
            raw = config_path.read_text(encoding="utf-8")
        except OSError as exc:
            return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(config_path)))
        loaded = load_toml(raw)
        if loaded.is_err:
            return Result.err(loaded.error.with_context(path=str(config_path)))
        data = merge_dicts(data, loaded.value)
    return Result.ok(build_workbench_config(root, data))


def ensure_base_layout(config: WorkbenchConfig) -> Result[None, AppError]:
    """确保配置所声明的基础目录存在。"""

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
    """在目标目录写入默认 `workbench.toml`。"""

    path = root / "workbench.toml"
    if path.exists() and not overwrite:
        return Result.ok(False)
    dumped = dump_toml(DEFAULT_CONFIG)
    if dumped.is_err:
        return Result.err(dumped.error.with_context(root=str(root)))
    try:
        ensure_dir(path.parent)
        path.write_text(dumped.value, encoding="utf-8")
    except OSError as exc:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, str(exc), path=str(path), root=str(root)))
    return Result.ok(True)


__all__ = [
    "DEFAULT_CONFIG",
    "build_workbench_config",
    "ensure_base_layout",
    "load_config",
    "merge_dicts",
    "write_default_config",
]
