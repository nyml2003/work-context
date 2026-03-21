from __future__ import annotations

from pathlib import Path

from ..core import Result
from ..domain.context import ContextBuildResult
from ..domain.errors import AppError
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class ContextCommandGroup(CommandGroup):
    name = "context"
    order = 50

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="context",
            help="Context bundle commands",
            subcommand_dest="context_command",
            subcommands=(
                CommandSpec(
                    name="build",
                    help="Build a context bundle from a skill",
                    arguments=(
                        ArgumentSpec(("skill",), {}),
                        ArgumentSpec(("--workspace",), {}),
                        ArgumentSpec(("--output",), {}),
                        ArgumentSpec(("--format",), {"choices": ["md", "json"], "default": "md"}),
                    ),
                ),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        services = runtime.services()
        if services.is_err:
            return Result.err(services.error)
        output = Path(args.output).resolve() if args.output else None
        target = services.value.context.build_context_file(
            args.skill,
            workspace_name=args.workspace,
            output_path=output,
            format_name=args.format,
        )
        if target.is_err:
            return Result.err(target.error)
        return Result.ok(CommandResult(0, ContextBuildResult(context=str(target.value), format=args.format)))


COMMAND_GROUP = ContextCommandGroup()
