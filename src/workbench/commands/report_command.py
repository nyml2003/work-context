from __future__ import annotations

from pathlib import Path

from ..core import Result
from ..domain.errors import AppError
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class ReportCommandGroup(CommandGroup):
    name = "report"
    order = 60

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="report",
            help="Report generation commands",
            subcommand_dest="report_command",
            subcommands=(
                CommandSpec(
                    name="generate",
                    help="Generate a repository report",
                    arguments=(ArgumentSpec(("--output",), {}),),
                ),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        services = runtime.services()
        if services.is_err:
            return Result.err(services.error)
        output = Path(args.output).resolve() if args.output else None
        payload = services.value.report.generate_report(output=output)
        if payload.is_err:
            return Result.err(payload.error)
        return Result.ok(CommandResult(0, payload.value))


COMMAND_GROUP = ReportCommandGroup()
