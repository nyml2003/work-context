from __future__ import annotations

from pathlib import Path

from ..application import initialize_repo
from ..core import Result
from ..domain.command_output import InitializationPayload
from ..domain.errors import AppError
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class InitCommandGroup(CommandGroup):
    name = "init"
    order = 10

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="init",
            help="Initialize the repository layout",
            arguments=(
                ArgumentSpec(("path",), {"nargs": "?", "default": "."}),
                ArgumentSpec(("--with-samples",), {"action": "store_true"}),
                ArgumentSpec(("--force",), {"action": "store_true"}),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        root = Path(args.path).resolve()
        created = initialize_repo(root, include_samples=args.with_samples, overwrite=args.force)
        if created.is_err:
            return Result.err(created.error)
        return Result.ok(
            CommandResult(
                0,
                InitializationPayload(created=[str(path) for path in created.value], root=str(root)),
            )
        )


COMMAND_GROUP = InitCommandGroup()
