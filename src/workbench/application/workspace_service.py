from __future__ import annotations

from typing import Any

from ..config import WorkbenchConfig
from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from ..domain.workspace import (
    Workspace,
    build_remote_url,
    is_safe_check_command,
    normalize_remote_url,
    parse_check_command,
    resolve_workspace_target,
)
from ..fs import short_path
from ..infrastructure import CommandRunner, GitClient, WorkspaceRegistry


class WorkspaceService:
    def __init__(
        self,
        config: WorkbenchConfig,
        *,
        registry: WorkspaceRegistry | None = None,
        git_client: GitClient | None = None,
        runner: CommandRunner | None = None,
    ) -> None:
        self.config = config
        self.runner = runner or CommandRunner()
        self.registry = registry or WorkspaceRegistry(
            config.workspace_registry,
            root=config.root,
            default_remote_name=config.default_remote_name,
        )
        self.git_client = git_client or GitClient(self.runner)

    def load_workspaces(self) -> Result[list[Workspace], AppError]:
        return self.registry.load_workspaces()

    def register_workspace(
        self,
        name: str,
        path: str | None = None,
        *,
        default_branch: str = "main",
        check_commands: list[str] | None = None,
        remote_name: str | None = None,
        repo_slug: str | None = None,
    ) -> Result[Any, AppError]:
        target = resolve_workspace_target(self.config.root, self.config.managed_repos_dir, name, path)
        workspace = Workspace(
            name=name,
            path=short_path(target, self.config.root).replace("\\", "/"),
            default_branch=default_branch,
            check_commands=list(check_commands or []),
            remote_name=remote_name or self.config.default_remote_name,
            repo_slug=repo_slug or name,
        )
        if not workspace.check_commands:
            workspace.check_commands = ["git status --short", "git branch --show-current"]
        return self.registry.save_workspace(workspace)

    def add_workspace(self, *args: Any, **kwargs: Any) -> Result[Any, AppError]:
        return self.register_workspace(*args, **kwargs)

    def get_workspace(self, name: str) -> Result[Workspace, AppError]:
        loaded = self.load_workspaces()
        if loaded.is_err:
            return Result.err(loaded.error)
        workspace = next((item for item in loaded.value if item.name == name), None)
        if workspace is None:
            return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Workspace not found: {name}", workspace=name))
        return Result.ok(workspace)

    def _remote_status(self, workspace: Workspace, git_ok: bool) -> Result[dict[str, Any], AppError]:
        expected_url = workspace.expected_remote_url(self.config.github_remote_prefix)
        result: dict[str, Any] = {
            "remote_name": workspace.remote_name,
            "repo_slug": workspace.repo_slug,
        }
        if expected_url.is_some:
            result["expected_url"] = expected_url.value
        if not git_ok:
            result["status"] = "not_git"
            return Result.ok(result)
        target = workspace.resolved_path(self.config.root)
        actual_url = self.git_client.remote_url(target, workspace.remote_name)
        if actual_url.is_err:
            return Result.err(actual_url.error)
        if actual_url.value.is_some:
            result["actual_url"] = actual_url.value.value
        if actual_url.value.is_none and expected_url.is_none:
            result["status"] = "unconfigured"
        elif actual_url.value.is_none and expected_url.is_some:
            result["status"] = "missing"
        elif actual_url.value.is_some and expected_url.is_none:
            result["status"] = "present"
        elif actual_url.value.is_some and expected_url.is_some and normalize_remote_url(actual_url.value.value) == normalize_remote_url(
            expected_url.value
        ):
            result["status"] = "ok"
        else:
            result["status"] = "mismatch"
        return Result.ok(result)

    def check_workspaces(self, name: str | None = None) -> Result[dict[str, Any], AppError]:
        loaded = self.load_workspaces()
        if loaded.is_err:
            return Result.err(loaded.error)
        results: list[dict[str, Any]] = []
        for workspace in loaded.value:
            if name is not None and workspace.name != name:
                continue
            target = workspace.resolved_path(self.config.root)
            if not target.exists():
                results.append(
                    {
                        "workspace": workspace.name,
                        "status": "missing",
                        "path": str(target),
                        "default_branch": workspace.default_branch,
                        "remote_name": workspace.remote_name,
                        "repo_slug": workspace.repo_slug,
                        "git": {"status": "missing_path"},
                        "remote": {
                            "status": "missing_path",
                            "remote_name": workspace.remote_name,
                            "repo_slug": workspace.repo_slug,
                        },
                        "checks": [],
                    }
                )
                continue

            git_ok = self.git_client.is_repository(target)
            command_results = []
            for command in workspace.check_commands:
                safe = is_safe_check_command(command)
                if safe.is_err:
                    command_results.append({"command": command, "status": "blocked", "reason": safe.error.message})
                    continue
                parsed = parse_check_command(command)
                if parsed.is_err:
                    command_results.append({"command": command, "status": "blocked", "reason": parsed.error.message})
                    continue
                completed = self.runner.run_args(parsed.value, cwd=target)
                if completed.is_err:
                    command_results.append({"command": command, "status": "failed", "reason": completed.error.message})
                    continue
                process = completed.value
                command_results.append(
                    {
                        "command": command,
                        "status": "ok" if process.returncode == 0 else "failed",
                        "returncode": process.returncode,
                        "stdout": process.stdout.strip(),
                        "stderr": process.stderr.strip(),
                    }
                )

            remote = self._remote_status(workspace, git_ok)
            if remote.is_err:
                return Result.err(remote.error.with_context(workspace=workspace.name))
            results.append(
                {
                    "workspace": workspace.name,
                    "status": "ok" if git_ok else "not_git",
                    "path": short_path(target, self.config.root),
                    "default_branch": workspace.default_branch,
                    "remote_name": workspace.remote_name,
                    "repo_slug": workspace.repo_slug,
                    "git": {"status": "ok" if git_ok else "not_git"},
                    "remote": remote.value,
                    "checks": command_results,
                }
            )
        return Result.ok({"workspace_count": len(results), "results": results})

    def initialize_remote(self, name: str, *, reset_existing: bool = False) -> Result[dict[str, Any], AppError]:
        workspace = self.get_workspace(name)
        if workspace.is_err:
            return Result.err(workspace.error)
        entry = workspace.value
        target = entry.resolved_path(self.config.root)
        if not target.exists():
            return Result.err(
                app_error(AppErrorCode.NOT_FOUND, f"Workspace path does not exist: {target}", workspace=name, path=str(target))
            )
        if not self.git_client.is_repository(target):
            return Result.err(
                app_error(
                    AppErrorCode.NOT_A_GIT_REPOSITORY,
                    f"Workspace is not a git repository: {target}",
                    workspace=name,
                    path=str(target),
                )
            )

        expected_url = build_remote_url(self.config.github_remote_prefix, entry.repo_slug)
        if expected_url.is_err:
            return Result.err(expected_url.error.with_context(workspace=name))
        actual_url = self.git_client.remote_url(target, entry.remote_name)
        if actual_url.is_err:
            return Result.err(actual_url.error.with_context(workspace=name))
        payload = {
            "workspace": entry.name,
            "path": short_path(target, self.config.root),
            "remote_name": entry.remote_name,
            "expected_url": expected_url.value,
        }
        if actual_url.value.is_none:
            added = self.git_client.add_remote(target, entry.remote_name, expected_url.value)
            if added.is_err:
                return Result.err(added.error.with_context(workspace=name))
            payload["status"] = "added"
            return Result.ok(payload)
        if normalize_remote_url(actual_url.value.value) == normalize_remote_url(expected_url.value):
            payload["status"] = "unchanged"
            payload["actual_url"] = actual_url.value.value
            return Result.ok(payload)
        payload["status"] = "conflict"
        payload["actual_url"] = actual_url.value.value
        if not reset_existing:
            return Result.ok(payload)
        updated = self.git_client.set_remote_url(target, entry.remote_name, expected_url.value)
        if updated.is_err:
            return Result.err(updated.error.with_context(workspace=name))
        payload["status"] = "updated"
        payload["actual_url"] = expected_url.value
        return Result.ok(payload)
