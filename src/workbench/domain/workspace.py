from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from pathlib import Path

from ..core import Option, Result
from .errors import AppError, AppErrorCode, app_error


DEFAULT_CHECK_COMMANDS = ["git status --short", "git branch --show-current"]

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


@dataclass(slots=True)
class Workspace:
    """运行时 workspace 领域对象。"""

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


@dataclass(frozen=True, slots=True)
class WorkspaceRecord:
    """注册表里的持久化记录。"""

    name: str
    path: str
    default_branch: str = "main"
    check_commands: list[str] = field(default_factory=lambda: list(DEFAULT_CHECK_COMMANDS))
    remote_name: str = "origin"
    repo_slug: str = ""


@dataclass(frozen=True, slots=True)
class WorkspaceGitPayload:
    """workspace git 状态摘要。"""

    status: str


@dataclass(frozen=True, slots=True)
class WorkspaceRemotePayload:
    """workspace 远程仓库状态摘要。"""

    status: str
    remote_name: str
    repo_slug: str
    expected_url: str | None = None
    actual_url: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceCheckCommandPayload:
    """单条检查命令执行结果。"""

    command: str
    status: str
    reason: str | None = None
    returncode: int | None = None
    stdout: str | None = None
    stderr: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceCheckEntry:
    """单个 workspace 的完整检查结果。"""

    workspace: str
    status: str
    path: str
    default_branch: str
    remote_name: str
    repo_slug: str
    git: WorkspaceGitPayload
    remote: WorkspaceRemotePayload
    checks: list[WorkspaceCheckCommandPayload]


@dataclass(frozen=True, slots=True)
class WorkspaceCheckPayload:
    """workspace check 聚合结果。"""

    workspace_count: int
    results: list[WorkspaceCheckEntry]


@dataclass(frozen=True, slots=True)
class WorkspaceRegistrationPayload:
    """workspace 注册结果。"""

    registry: str
    workspace: str


@dataclass(frozen=True, slots=True)
class WorkspaceRemoteInitPayload:
    """workspace remote-init 结果。"""

    workspace: str
    path: str
    remote_name: str
    expected_url: str
    status: str
    actual_url: str | None = None


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
        if token in DANGEROUS_TOKENS:
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


def workspace_from_record(record: WorkspaceRecord, *, default_remote_name: str) -> Workspace:
    return Workspace(
        name=record.name,
        path=record.path,
        default_branch=record.default_branch,
        check_commands=list(record.check_commands),
        remote_name=record.remote_name or default_remote_name,
        repo_slug=record.repo_slug or record.name,
    )


def workspace_to_record(workspace: Workspace, root: Path) -> WorkspaceRecord:
    target = workspace.resolved_path(root)
    return WorkspaceRecord(
        name=workspace.name,
        path=stored_workspace_path(target, root),
        default_branch=workspace.default_branch,
        check_commands=list(workspace.check_commands),
        remote_name=workspace.remote_name,
        repo_slug=workspace.repo_slug,
    )


__all__ = [
    "DEFAULT_CHECK_COMMANDS",
    "Workspace",
    "WorkspaceCheckCommandPayload",
    "WorkspaceCheckEntry",
    "WorkspaceCheckPayload",
    "WorkspaceGitPayload",
    "WorkspaceRecord",
    "WorkspaceRegistrationPayload",
    "WorkspaceRemoteInitPayload",
    "WorkspaceRemotePayload",
    "build_remote_url",
    "is_safe_check_command",
    "normalize_remote_url",
    "parse_check_command",
    "resolve_workspace_target",
    "stored_workspace_path",
    "workspace_from_record",
    "workspace_to_record",
]
