from __future__ import annotations

"""workspace 相关的 application service。"""

from ..core import Result
from ..domain.config import WorkbenchConfig
from ..domain.errors import AppError, AppErrorCode, app_error, from_exception
from ..domain.workspace import (
    DEFAULT_CHECK_COMMANDS,
    Workspace,
    WorkspaceCheckCommandPayload,
    WorkspaceCheckEntry,
    WorkspaceCheckPayload,
    WorkspaceGitPayload,
    WorkspaceRegistrationPayload,
    WorkspaceRemoteInitPayload,
    WorkspaceRemotePayload,
    WorkspaceScriptsLinkPayload,
    build_remote_url,
    is_safe_check_command,
    normalize_remote_url,
    parse_check_command,
    resolve_workspace_target,
)
from ..infrastructure import CommandRunner, GitClient, WorkspaceRegistry
from ..infrastructure.filesystem import ensure_directory_symlink, short_path


class WorkspaceService:
    """编排 workspace 注册、检查和远程仓库初始化。"""

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
        """读取注册表中的全部 workspace。"""

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
    ) -> Result[WorkspaceRegistrationPayload, AppError]:
        """注册一个 workspace。

        未显式提供路径时，会落到受管目录 `managed_repos_dir` 下。
        """

        target = resolve_workspace_target(self.config.root, self.config.managed_repos_dir, name, path)
        commands = list(check_commands or DEFAULT_CHECK_COMMANDS)
        workspace = Workspace(
            name=name,
            path=short_path(target, self.config.root).replace("\\", "/"),
            default_branch=default_branch,
            check_commands=commands,
            remote_name=remote_name or self.config.default_remote_name,
            repo_slug=repo_slug or name,
        )
        saved = self.registry.save_workspace(workspace)
        if saved.is_err:
            return Result.err(saved.error)
        return Result.ok(WorkspaceRegistrationPayload(registry=str(saved.value), workspace=name))

    def add_workspace(
        self,
        name: str,
        path: str | None = None,
        *,
        default_branch: str = "main",
        check_commands: list[str] | None = None,
        remote_name: str | None = None,
        repo_slug: str | None = None,
    ) -> Result[WorkspaceRegistrationPayload, AppError]:
        """兼容旧命名，实际仍走 `register_workspace`。"""

        return self.register_workspace(
            name,
            path,
            default_branch=default_branch,
            check_commands=check_commands,
            remote_name=remote_name,
            repo_slug=repo_slug,
        )

    def link_scripts(self) -> Result[WorkspaceScriptsLinkPayload, AppError]:
        """创建稳定的 scripts 入口链接。"""

        source = self.config.root / "scripts"
        target = self.config.work_context_scripts_root
        try:
            status = ensure_directory_symlink(source, target)
        except OSError as exc:
            return Result.err(from_exception(exc, default_code=AppErrorCode.INTERNAL_ERROR, path=str(target)))
        return Result.ok(WorkspaceScriptsLinkPayload(source=str(source.resolve()), target=str(target), status=status))

    def get_workspace(self, name: str) -> Result[Workspace, AppError]:
        """按名称读取单个 workspace。"""

        loaded = self.load_workspaces()
        if loaded.is_err:
            return Result.err(loaded.error)
        workspace = next((item for item in loaded.value if item.name == name), None)
        if workspace is None:
            return Result.err(app_error(AppErrorCode.NOT_FOUND, f"Workspace not found: {name}", workspace=name))
        return Result.ok(workspace)

    def resolve_remote_status(self, workspace: Workspace, git_ok: bool) -> Result[WorkspaceRemotePayload, AppError]:
        """比较期望远程地址与实际远程地址，生成状态摘要。"""

        expected_url = workspace.expected_remote_url(self.config.github_remote_prefix)
        if not git_ok:
            return Result.ok(
                WorkspaceRemotePayload(
                    status="not_git",
                    remote_name=workspace.remote_name,
                    repo_slug=workspace.repo_slug,
                    expected_url=expected_url.unwrap_or(None),
                )
            )
        target = workspace.resolved_path(self.config.root)
        actual_url = self.git_client.remote_url(target, workspace.remote_name)
        if actual_url.is_err:
            return Result.err(actual_url.error)
        if actual_url.value.is_none and expected_url.is_none:
            status = "unconfigured"
        elif actual_url.value.is_none and expected_url.is_some:
            status = "missing"
        elif actual_url.value.is_some and expected_url.is_none:
            status = "present"
        elif actual_url.value.is_some and expected_url.is_some and normalize_remote_url(actual_url.value.value) == normalize_remote_url(
            expected_url.value
        ):
            status = "ok"
        else:
            status = "mismatch"
        return Result.ok(
            WorkspaceRemotePayload(
                status=status,
                remote_name=workspace.remote_name,
                repo_slug=workspace.repo_slug,
                expected_url=expected_url.unwrap_or(None),
                actual_url=actual_url.value.unwrap_or(None),
            )
        )

    def build_missing_workspace_entry(self, workspace: Workspace, target: str) -> WorkspaceCheckEntry:
        """为缺失目录的 workspace 构造统一结果。"""

        return WorkspaceCheckEntry(
            workspace=workspace.name,
            status="missing",
            path=target,
            default_branch=workspace.default_branch,
            remote_name=workspace.remote_name,
            repo_slug=workspace.repo_slug,
            git=WorkspaceGitPayload(status="missing_path"),
            remote=WorkspaceRemotePayload(
                status="missing_path",
                remote_name=workspace.remote_name,
                repo_slug=workspace.repo_slug,
            ),
            checks=[],
        )

    def run_workspace_checks(self, workspace: Workspace) -> list[WorkspaceCheckCommandPayload]:
        """执行只读检查命令，并把子进程结果投影为结构化 payload。"""

        target = workspace.resolved_path(self.config.root)
        results: list[WorkspaceCheckCommandPayload] = []
        for command in workspace.check_commands:
            safe = is_safe_check_command(command)
            if safe.is_err:
                results.append(WorkspaceCheckCommandPayload(command=command, status="blocked", reason=safe.error.message))
                continue
            parsed = parse_check_command(command)
            if parsed.is_err:
                results.append(WorkspaceCheckCommandPayload(command=command, status="blocked", reason=parsed.error.message))
                continue
            completed = self.runner.run_args(parsed.value, cwd=target)
            if completed.is_err:
                results.append(WorkspaceCheckCommandPayload(command=command, status="failed", reason=completed.error.message))
                continue
            process = completed.value
            results.append(
                WorkspaceCheckCommandPayload(
                    command=command,
                    status="ok" if process.returncode == 0 else "failed",
                    returncode=process.returncode,
                    stdout=process.stdout.strip(),
                    stderr=process.stderr.strip(),
                )
            )
        return results

    def check_workspaces(self, name: str | None = None) -> Result[WorkspaceCheckPayload, AppError]:
        """执行 workspace 健康检查。"""

        loaded = self.load_workspaces()
        if loaded.is_err:
            return Result.err(loaded.error)
        results: list[WorkspaceCheckEntry] = []
        for workspace in loaded.value:
            if name is not None and workspace.name != name:
                continue
            target = workspace.resolved_path(self.config.root)
            if not target.exists():
                results.append(self.build_missing_workspace_entry(workspace, str(target)))
                continue

            git_ok = self.git_client.is_repository(target)
            remote = self.resolve_remote_status(workspace, git_ok)
            if remote.is_err:
                return Result.err(remote.error.with_context(workspace=workspace.name))
            results.append(
                WorkspaceCheckEntry(
                    workspace=workspace.name,
                    status="ok" if git_ok else "not_git",
                    path=short_path(target, self.config.root),
                    default_branch=workspace.default_branch,
                    remote_name=workspace.remote_name,
                    repo_slug=workspace.repo_slug,
                    git=WorkspaceGitPayload(status="ok" if git_ok else "not_git"),
                    remote=remote.value,
                    checks=self.run_workspace_checks(workspace),
                )
            )
        return Result.ok(WorkspaceCheckPayload(workspace_count=len(results), results=results))

    def initialize_remote(self, name: str, *, reset_existing: bool = False) -> Result[WorkspaceRemoteInitPayload, AppError]:
        """为已注册 workspace 配置远程仓库地址。"""

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
        payload = WorkspaceRemoteInitPayload(
            workspace=entry.name,
            path=short_path(target, self.config.root),
            remote_name=entry.remote_name,
            expected_url=expected_url.value,
            status="pending",
            actual_url=actual_url.value.unwrap_or(None),
        )
        if actual_url.value.is_none:
            added = self.git_client.add_remote(target, entry.remote_name, expected_url.value)
            if added.is_err:
                return Result.err(added.error.with_context(workspace=name))
            return Result.ok(
                WorkspaceRemoteInitPayload(
                    workspace=payload.workspace,
                    path=payload.path,
                    remote_name=payload.remote_name,
                    expected_url=payload.expected_url,
                    status="added",
                )
            )
        if normalize_remote_url(actual_url.value.value) == normalize_remote_url(expected_url.value):
            return Result.ok(
                WorkspaceRemoteInitPayload(
                    workspace=payload.workspace,
                    path=payload.path,
                    remote_name=payload.remote_name,
                    expected_url=payload.expected_url,
                    status="unchanged",
                    actual_url=actual_url.value.value,
                )
            )
        if not reset_existing:
            return Result.ok(
                WorkspaceRemoteInitPayload(
                    workspace=payload.workspace,
                    path=payload.path,
                    remote_name=payload.remote_name,
                    expected_url=payload.expected_url,
                    status="conflict",
                    actual_url=actual_url.value.value,
                )
            )
        updated = self.git_client.set_remote_url(target, entry.remote_name, expected_url.value)
        if updated.is_err:
            return Result.err(updated.error.with_context(workspace=name))
        return Result.ok(
            WorkspaceRemoteInitPayload(
                workspace=payload.workspace,
                path=payload.path,
                remote_name=payload.remote_name,
                expected_url=payload.expected_url,
                status="updated",
                actual_url=expected_url.value,
            )
        )
