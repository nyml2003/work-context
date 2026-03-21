from __future__ import annotations

from typing import Any

from .application.workspace_service import WorkspaceService
from .config import WorkbenchConfig
from .core import Result
from .domain.errors import AppError
from .domain.workspace import DEFAULT_CHECK_COMMANDS, Workspace, build_remote_url, is_safe_check_command, normalize_remote_url

__all__ = [
    "DEFAULT_CHECK_COMMANDS",
    "Workspace",
    "add_workspace",
    "build_remote_url",
    "check_workspaces",
    "initialize_workspace_remote",
    "is_safe_check_command",
    "load_workspaces",
    "normalize_remote_url",
    "register_workspace",
]


def workspace_service(config: WorkbenchConfig) -> WorkspaceService:
    return WorkspaceService(config)


def load_workspaces(config: WorkbenchConfig) -> Result[list[Workspace], AppError]:
    return workspace_service(config).load_workspaces()


def register_workspace(
    config: WorkbenchConfig,
    name: str,
    path: str | None = None,
    *,
    default_branch: str = "main",
    check_commands: list[str] | None = None,
    remote_name: str | None = None,
    repo_slug: str | None = None,
) -> Result[Any, AppError]:
    return workspace_service(config).register_workspace(
        name,
        path,
        default_branch=default_branch,
        check_commands=check_commands,
        remote_name=remote_name,
        repo_slug=repo_slug,
    )


def add_workspace(
    config: WorkbenchConfig,
    name: str,
    path: str | None = None,
    *,
    default_branch: str = "main",
    check_commands: list[str] | None = None,
    remote_name: str | None = None,
    repo_slug: str | None = None,
) -> Result[Any, AppError]:
    return register_workspace(
        config,
        name,
        path,
        default_branch=default_branch,
        check_commands=check_commands,
        remote_name=remote_name,
        repo_slug=repo_slug,
    )


def check_workspaces(config: WorkbenchConfig, name: str | None = None) -> Result[dict[str, Any], AppError]:
    return workspace_service(config).check_workspaces(name)


def initialize_workspace_remote(
    config: WorkbenchConfig, name: str, *, reset_existing: bool = False
) -> Result[dict[str, Any], AppError]:
    return workspace_service(config).initialize_remote(name, reset_existing=reset_existing)
