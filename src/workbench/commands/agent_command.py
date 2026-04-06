from __future__ import annotations

from pathlib import Path

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class AgentCommandGroup(CommandGroup):
    name = "agent"
    order = 35

    @property
    def spec(self) -> CommandSpec:
        return CommandSpec(
            name="agent",
            help="Multi-agent orchestration commands",
            subcommand_dest="agent_command",
            subcommands=(
                CommandSpec(
                    name="plan",
                    help="Plan subtasks for a frontend task file",
                    arguments=(ArgumentSpec(("task_file",), {}),),
                ),
                CommandSpec(
                    name="resolve",
                    help="Resolve the skills for one subtask",
                    arguments=(ArgumentSpec(("task_file",), {}), ArgumentSpec(("subtask_id",), {})),
                ),
                CommandSpec(
                    name="assemble",
                    help="Assemble minimal context for one subtask",
                    arguments=(ArgumentSpec(("task_file",), {}), ArgumentSpec(("subtask_id",), {})),
                ),
                CommandSpec(
                    name="handoff-validate",
                    help="Validate a handoff payload JSON file",
                    arguments=(ArgumentSpec(("handoff_file",), {}),),
                ),
                CommandSpec(
                    name="trace",
                    help="Read a stored orchestration trace",
                    arguments=(ArgumentSpec(("task_id",), {}),),
                ),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        services = runtime.services()
        if services.is_err:
            return Result.err(services.error)
        service = services.value.agent
        if args.agent_command == "plan":
            payload = service.plan_from_file(Path(args.task_file).resolve())
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(0, payload.value))
        if args.agent_command == "resolve":
            payload = service.resolve_from_file(Path(args.task_file).resolve(), args.subtask_id)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(0, payload.value))
        if args.agent_command == "assemble":
            payload = service.assemble_from_file(Path(args.task_file).resolve(), args.subtask_id)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(0, payload.value))
        if args.agent_command == "handoff-validate":
            payload = service.validate_handoff_file(Path(args.handoff_file).resolve())
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(0, payload.value))
        if args.agent_command == "trace":
            payload = service.read_trace(args.task_id)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(0, payload.value))
        return Result.err(app_error(AppErrorCode.UNSUPPORTED_COMMAND, f"Unsupported agent command: {args.agent_command}"))


COMMAND_GROUP = AgentCommandGroup()
