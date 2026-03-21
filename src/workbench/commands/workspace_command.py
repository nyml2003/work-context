from __future__ import annotations

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


def workspace_register_arguments() -> tuple[ArgumentSpec, ...]:
    """复用 workspace register / add 的参数声明。"""

    return (
        ArgumentSpec(("name",), {}),
        ArgumentSpec(("path",), {"nargs": "?"}),
        ArgumentSpec(("--default-branch",), {"default": "main"}),
        ArgumentSpec(("--check-command",), {"action": "append", "default": []}),
        ArgumentSpec(("--remote-name",), {}),
        ArgumentSpec(("--repo-slug",), {}),
    )


def workspace_check_has_failures(entry: dict[str, object]) -> bool:
    """根据 check 输出判断命令是否需要返回非零退出码。"""

    if entry.get("status") in {"missing", "not_git"}:
        return True
    git_status = entry.get("git", {}).get("status") if isinstance(entry.get("git"), dict) else None
    if git_status not in {None, "ok"}:
        return True
    remote = entry.get("remote")
    remote_status = remote.get("status") if isinstance(remote, dict) else None
    if remote_status in {"missing", "mismatch", "missing_path", "not_git"}:
        return True
    checks = entry.get("checks")
    if not isinstance(checks, list):
        return False
    return any(isinstance(check, dict) and check.get("status") in {"failed", "blocked"} for check in checks)


class WorkspaceCommandGroup(CommandGroup):
    name = "workspace"
    order = 40

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="workspace",
            help="Registered workspace commands",
            subcommand_dest="workspace_command",
            subcommands=(
                CommandSpec(name="register", help="Register a workspace", arguments=workspace_register_arguments()),
                CommandSpec(name="add", help="Alias for workspace register", arguments=workspace_register_arguments()),
                CommandSpec(name="check", help="Run safe checks in registered workspaces", arguments=(ArgumentSpec(("name",), {"nargs": "?"}),)),
                CommandSpec(
                    name="remote-init",
                    help="Initialize or repair a workspace remote",
                    arguments=(ArgumentSpec(("name",), {}), ArgumentSpec(("--reset-existing",), {"action": "store_true"})),
                ),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        services = runtime.services()
        if services.is_err:
            return Result.err(services.error)
        service = services.value.workspace
        if args.workspace_command in {"register", "add"}:
            registry = service.register_workspace(
                args.name,
                args.path,
                default_branch=args.default_branch,
                check_commands=args.check_command or None,
                remote_name=args.remote_name,
                repo_slug=args.repo_slug,
            )
            if registry.is_err:
                return Result.err(registry.error)
            return Result.ok(CommandResult(0, {"registry": str(registry.value), "workspace": args.name}))
        if args.workspace_command == "check":
            payload = service.check_workspaces(args.name)
            if payload.is_err:
                return Result.err(payload.error)
            exit_code = 1 if any(workspace_check_has_failures(entry) for entry in payload.value["results"]) else 0
            return Result.ok(CommandResult(exit_code, payload.value))
        if args.workspace_command == "remote-init":
            payload = service.initialize_remote(args.name, reset_existing=args.reset_existing)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(1 if payload.value["status"] == "conflict" else 0, payload.value))
        return Result.err(
            app_error(AppErrorCode.UNSUPPORTED_COMMAND, f"Unsupported workspace command: {args.workspace_command}")
        )


COMMAND_GROUP = WorkspaceCommandGroup()
