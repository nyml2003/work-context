from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core import Option, Result
from .errors import AppError, AppErrorCode, app_error


DEFAULT_CHECK_COMMANDS = ["git status --short", "git branch --show-current"]

_DANGEROUS_TOKENS = {
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
class Workspace:
    name: str
    path: str
    default_branch: str = "main"
    check_commands: list[str] = field(default_factory=lambda: list(DEFAULT_CHECK_COMMANDS))
    remote_name: str = "origin"
    repo_slug: str = ""

    def __post_init__(self) -> None:
        if not self.repo_slug:
            self.repo_slug = self.name

    def resolved_path(self, root: Path) -> Path:
        raw = Path(self.path)
        return raw if raw.is_absolute() else (root / raw).resolve()

    def expected_remote_url(self, github_remote_prefix: str) -> Option[str]:
        if not github_remote_prefix:
            return Option.none()
        return Option.some(build_remote_url(github_remote_prefix, self.repo_slug).value)


def normalize_remote_url(url: str) -> str:
    text = url.strip()
    if text.endswith(".git"):
        text = text[:-4]
    return text.rstrip("/").casefold()


def build_remote_url(prefix: str, repo_slug: str) -> Result[str, AppError]:
    normalized = prefix.strip()
    if not normalized:
        return Result.err(app_error(AppErrorCode.CONFIG_ERROR, "github_remote_prefix is not configured"))
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    normalized = normalized.rstrip("/")
    return Result.ok(f"{normalized}/{repo_slug}.git")


def parse_check_command(command: str) -> Result[list[str], AppError]:
    try:
        return Result.ok(shlex.split(command, posix=False))
    except ValueError as exc:
        return Result.err(app_error(AppErrorCode.INVALID_ARGUMENT, f"Invalid command syntax: {exc}", command=command))


def is_safe_check_command(command: str) -> Result[None, AppError]:
    tokens = parse_check_command(command)
    if tokens.is_err:
        return Result.err(tokens.error)
    lowered = [token.lower() for token in tokens.value]
    for token in lowered:
        if token in _DANGEROUS_TOKENS:
            return Result.err(
                app_error(
                    AppErrorCode.COMMAND_BLOCKED,
                    f"Command contains blocked token '{token}'",
                    command=command,
                    token=token,
                )
            )
    return Result.ok(None)


def stored_workspace_path(target: Path, root: Path) -> str:
    try:
        return target.relative_to(root).as_posix()
    except ValueError:
        return str(target)


def resolve_workspace_target(root: Path, managed_repos_dir: Path, name: str, path: str | None) -> Path:
    if path is None:
        return (managed_repos_dir / name).resolve()
    raw = Path(path)
    return raw if raw.is_absolute() else (root / raw).resolve()


def workspace_from_record(name: str, payload: dict[str, Any], *, default_remote_name: str) -> Workspace:
    return Workspace(
        name=name,
        path=payload["path"],
        default_branch=payload.get("default_branch", "main"),
        check_commands=list(payload.get("check_commands", DEFAULT_CHECK_COMMANDS)),
        remote_name=payload.get("remote_name", default_remote_name),
        repo_slug=payload.get("repo_slug", name),
    )


def workspace_to_record(workspace: Workspace, root: Path) -> dict[str, Any]:
    target = workspace.resolved_path(root)
    return {
        "path": stored_workspace_path(target, root),
        "default_branch": workspace.default_branch,
        "check_commands": list(workspace.check_commands),
        "remote_name": workspace.remote_name,
        "repo_slug": workspace.repo_slug,
    }
