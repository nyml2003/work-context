from __future__ import annotations

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class LocalCommandGroup(CommandGroup):
    name = "local"
    order = 20

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="local",
            help="Local filesystem commands within the current working directory",
            subcommand_dest="local_command",
            subcommands=(
                CommandSpec(
                    name="read",
                    help="Read a file",
                    arguments=(
                        ArgumentSpec(("path",), {}),
                        ArgumentSpec(("--start-line",), {"type": int}),
                        ArgumentSpec(("--end-line",), {"type": int}),
                        ArgumentSpec(("--encoding",), {"default": "utf-8"}),
                    ),
                ),
                CommandSpec(
                    name="list",
                    help="List a path",
                    arguments=(
                        ArgumentSpec(("path",), {}),
                        ArgumentSpec(("--recursive",), {"action": "store_true"}),
                        ArgumentSpec(("--kind",), {"default": "all", "choices": ["file", "dir", "all"]}),
                        ArgumentSpec(("--pattern",), {}),
                    ),
                ),
                CommandSpec(
                    name="grep",
                    help="Search text under a path",
                    arguments=(
                        ArgumentSpec(("path",), {}),
                        ArgumentSpec(("--pattern",), {"required": True}),
                        ArgumentSpec(("--glob",), {}),
                        ArgumentSpec(("--ignore-case",), {"action": "store_true"}),
                        ArgumentSpec(("--encoding",), {"default": "utf-8"}),
                    ),
                ),
                CommandSpec(
                    name="write",
                    help="Write a file",
                    arguments=(
                        ArgumentSpec(("path",), {}),
                        ArgumentSpec(("--content",), {"required": True}),
                        ArgumentSpec(("--encoding",), {"default": "utf-8"}),
                        ArgumentSpec(("--overwrite",), {"action": "store_true"}),
                    ),
                ),
                CommandSpec(
                    name="append",
                    help="Append to a file",
                    arguments=(
                        ArgumentSpec(("path",), {}),
                        ArgumentSpec(("--content",), {"required": True}),
                        ArgumentSpec(("--encoding",), {"default": "utf-8"}),
                    ),
                ),
                CommandSpec(
                    name="mkdir",
                    help="Create a directory",
                    arguments=(
                        ArgumentSpec(("path",), {}),
                        ArgumentSpec(("--parents",), {"action": "store_true"}),
                    ),
                ),
                CommandSpec(name="stat", help="Show path metadata", arguments=(ArgumentSpec(("path",), {}),)),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        service = runtime.local()
        if args.local_command == "read":
            payload = service.read_file(args.path, start_line=args.start_line, end_line=args.end_line, encoding=args.encoding)
        elif args.local_command == "list":
            payload = service.list_path(args.path, recursive=args.recursive, kind=args.kind, pattern=args.pattern)
        elif args.local_command == "grep":
            payload = service.grep_path(
                args.path,
                pattern=args.pattern,
                glob=args.glob,
                ignore_case=args.ignore_case,
                encoding=args.encoding,
            )
        elif args.local_command == "write":
            payload = service.write_file(args.path, content=args.content, encoding=args.encoding, overwrite=args.overwrite)
        elif args.local_command == "append":
            payload = service.append_file(args.path, content=args.content, encoding=args.encoding)
        elif args.local_command == "mkdir":
            payload = service.make_dir(args.path, parents=args.parents)
        elif args.local_command == "stat":
            payload = service.stat_path(args.path)
        else:
            return Result.err(app_error(AppErrorCode.UNSUPPORTED_COMMAND, f"Unsupported local command: {args.local_command}"))

        if payload.is_err:
            return Result.err(payload.error)
        return Result.ok(CommandResult(0, payload.value))


COMMAND_GROUP = LocalCommandGroup()
