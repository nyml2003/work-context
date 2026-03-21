from __future__ import annotations

from pathlib import Path

from ..core import Result
from ..domain.errors import AppError, AppErrorCode, app_error
from .base import ArgumentSpec, CommandGroup, CommandResult, CommandSpec, RuntimeContext


class SkillCommandGroup(CommandGroup):
    name = "skill"
    order = 30

    @property
    def spec(self) -> CommandSpec:
        sync_arguments = (
            ArgumentSpec(("name",), {"nargs": "?"}),
            ArgumentSpec(("--target",), {}),
            ArgumentSpec(("--no-overwrite",), {"action": "store_true"}),
        )
        return CommandSpec(
            name="skill",
            help="Codex skill management commands",
            subcommand_dest="skill_command",
            subcommands=(
                CommandSpec(
                    name="new",
                    help="Create a new Codex skill",
                    arguments=(
                        ArgumentSpec(("name",), {}),
                        ArgumentSpec(("--description",), {"default": "Describe what this skill does and when to use it."}),
                        ArgumentSpec(("--resources",), {"nargs": "*", "choices": ["scripts", "references", "assets"], "default": []}),
                        ArgumentSpec(("--examples",), {"action": "store_true"}),
                        ArgumentSpec(("--short-description",), {}),
                        ArgumentSpec(("--default-prompt",), {}),
                    ),
                ),
                CommandSpec(name="lint", help="Validate Codex skill definitions", arguments=(ArgumentSpec(("name",), {"nargs": "?"}),)),
                CommandSpec(name="test", help="Run skill bundle fixtures", arguments=(ArgumentSpec(("name",), {"nargs": "?"}),)),
                CommandSpec(
                    name="pack",
                    help="Package a skill directory as a zip",
                    arguments=(ArgumentSpec(("name",), {}), ArgumentSpec(("--output",), {})),
                ),
                CommandSpec(name="sync", help="Copy skills into a Codex skills directory", arguments=sync_arguments),
                CommandSpec(name="install", help="Copy skills into a Codex skills directory", arguments=sync_arguments),
            ),
        )

    def run(self, args: object, runtime: RuntimeContext) -> Result[CommandResult, AppError]:
        services = runtime.services()
        if services.is_err:
            return Result.err(services.error)
        service = services.value.skill
        if args.skill_command == "new":
            created = service.create_skill(
                args.name,
                description=args.description,
                resources=args.resources,
                include_examples=args.examples,
                short_description=args.short_description,
                default_prompt=args.default_prompt,
            )
            if created.is_err:
                return Result.err(created.error)
            return Result.ok(CommandResult(0, {"created": str(created.value)}))
        if args.skill_command == "lint":
            payload = service.lint_skills(args.name)
            if payload.is_err:
                return Result.err(payload.error)
            exit_code = 1 if any(issue["level"] == "error" for issue in payload.value["issues"]) else 0
            return Result.ok(CommandResult(exit_code, payload.value))
        if args.skill_command == "test":
            payload = service.test_skills(args.name)
            if payload.is_err:
                return Result.err(payload.error)
            return Result.ok(CommandResult(1 if payload.value["failure_count"] else 0, payload.value))
        if args.skill_command == "pack":
            output = Path(args.output).resolve() if args.output else None
            archive = service.pack_skill(args.name, output_path=output)
            if archive.is_err:
                return Result.err(archive.error)
            return Result.ok(CommandResult(0, {"archive": str(archive.value)}))
        if args.skill_command in {"sync", "install"}:
            target = Path(args.target).expanduser().resolve() if args.target else None
            synced = service.sync_skills(name=args.name, target_root=target, overwrite=not args.no_overwrite)
            if synced.is_err:
                return Result.err(synced.error)
            payload = {
                "target": str(target or services.value.config.codex_install_root),
                "synced": synced.value,
            }
            return Result.ok(CommandResult(0, payload))
        return Result.err(app_error(AppErrorCode.UNSUPPORTED_COMMAND, f"Unsupported skill command: {args.skill_command}"))


COMMAND_GROUP = SkillCommandGroup()
